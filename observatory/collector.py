import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from observatory.models import (
    LLMCall,
    Session,
    SessionReport,
    ModelProvider,
    AgentRole,
)
from observatory.storage import Storage
from observatory.analyzers.cost_analyzer import CostAnalyzer
from observatory.analyzers.latency_analyzer import LatencyAnalyzer
from observatory.analyzers.token_analyzer import TokenAnalyzer
from observatory.analyzers.quality_analyzer import QualityAnalyzer


class MetricsCollector:
    def __init__(
        self,
        project_name: str = "default",
        enabled: bool = True,
        storage: Optional[Storage] = None,
    ):
        self.project_name = project_name
        self.enabled = enabled
        self.storage = storage or Storage()
        self.current_session: Optional[Session] = None
        
        # Analyzers
        self.cost_analyzer = CostAnalyzer()
        self.latency_analyzer = LatencyAnalyzer()
        self.token_analyzer = TokenAnalyzer()
        self.quality_analyzer = QualityAnalyzer()

    def start_session(
        self,
        operation_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        if not self.enabled:
            return Session(
                id="disabled",
                project_name=self.project_name,
                operation_type=operation_type,
            )
        
        session = Session(
            id=str(uuid.uuid4()),
            project_name=self.project_name,
            operation_type=operation_type,
            metadata=metadata or {},
        )
        
        self.current_session = session
        self.storage.save_session(session)
        return session

    def end_session(self, session: Optional[Session] = None, success: bool = True, error: Optional[str] = None) -> Session:
        if not self.enabled:
            return session or Session(id="disabled", project_name=self.project_name)
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No active session to end")
        
        target_session.end_time = datetime.utcnow()
        target_session.success = success
        target_session.error = error
        
        self.storage.update_session(target_session)
        
        if target_session == self.current_session:
            self.current_session = None
        
        return target_session

    def record_llm_call(
        self,
        provider: ModelProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        agent_name: Optional[str] = None,
        agent_role: Optional[AgentRole] = None,
        operation: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None,
    ) -> LLMCall:
        if not self.enabled:
            return LLMCall(
                id="disabled",
                session_id="disabled",
                provider=provider,
                model_name=model_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                prompt_cost=0.0,
                completion_cost=0.0,
                total_cost=0.0,
                latency_ms=0.0,
            )
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No active session. Call start_session() first.")
        
        # Calculate cost
        prompt_cost, completion_cost = self.cost_analyzer.calculate_cost(
            provider, model_name, prompt_tokens, completion_tokens
        )
        
        llm_call = LLMCall(
            id=str(uuid.uuid4()),
            session_id=target_session.id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            latency_ms=latency_ms,
            agent_name=agent_name,
            agent_role=agent_role,
            operation=operation,
            success=success,
            error=error,
            metadata=metadata or {},
        )
        
        # Update session aggregates
        target_session.total_llm_calls += 1
        target_session.total_tokens += llm_call.total_tokens
        target_session.total_cost += llm_call.total_cost
        target_session.total_latency_ms += llm_call.latency_ms
        target_session.llm_calls.append(llm_call)
        
        # Persist
        self.storage.save_llm_call(llm_call)
        self.storage.update_session(target_session)
        
        return llm_call

    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        if not self.enabled:
            return None
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No session to report on")
        
        # Load full session data if needed
        if not target_session.llm_calls:
            target_session = self.storage.get_session(target_session.id)
        
        # Generate report
        cost_breakdown = self.cost_analyzer.analyze(target_session)
        latency_breakdown = self.latency_analyzer.analyze(target_session)
        token_breakdown = self.token_analyzer.analyze(target_session)
        quality_metrics = self.quality_analyzer.analyze(target_session)
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(
            target_session, cost_breakdown, latency_breakdown, token_breakdown, quality_metrics
        )
        
        return SessionReport(
            session=target_session,
            cost_breakdown=cost_breakdown,
            latency_breakdown=latency_breakdown,
            token_breakdown=token_breakdown,
            quality_metrics=quality_metrics,
            optimization_suggestions=suggestions,
        )

    def _generate_suggestions(self, session, cost_breakdown, latency_breakdown, token_breakdown, quality_metrics) -> List[str]:
        suggestions = []
        
        # Cost optimization
        if cost_breakdown.total_cost > 0.10:  # > $0.10 per session
            gpt4_cost = cost_breakdown.by_model.get("gpt-4", 0)
            if gpt4_cost > cost_breakdown.total_cost * 0.5:
                suggestions.append(
                    "💰 High GPT-4 usage detected. Consider using GPT-3.5-turbo for simpler tasks."
                )
        
        # Latency optimization
        if latency_breakdown.avg_latency_ms > 5000:  # > 5s average
            suggestions.append(
                "⚡ High average latency. Consider parallelizing independent agent calls."
            )
        
        # Token optimization
        avg_tokens = quality_metrics.avg_tokens_per_call
        if avg_tokens > 2000:
            suggestions.append(
                "📦 High token usage per call. Review system prompts for compression opportunities."
            )
        
        # Quality
        if quality_metrics.success_rate < 0.95:
            suggestions.append(
                f"🔴 Success rate is {quality_metrics.success_rate:.1%}. Investigate error patterns."
            )
        
        return suggestions

    @contextmanager
    def track(
        self,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        session = self.start_session(operation_type, metadata)
        try:
            yield session
            self.end_session(session, success=True)
        except Exception as e:
            self.end_session(session, success=False, error=str(e))
            raise


class Observatory:
    def __init__(
        self,
        project_name: str = "default",
        enabled: Optional[bool] = None,
        storage: Optional[Storage] = None,
    ):
        if enabled is None:
            enabled = os.getenv("ENABLE_OBSERVATORY", "false").lower() == "true"
        
        self.collector = MetricsCollector(
            project_name=project_name,
            enabled=enabled,
            storage=storage,
        )
    
    def start_session(self, operation_type: Optional[str] = None, **kwargs) -> Session:
        return self.collector.start_session(operation_type, kwargs)
    
    def end_session(self, session: Optional[Session] = None) -> Session:
        return self.collector.end_session(session)
    
    def record_call(self, **kwargs) -> LLMCall:
        return self.collector.record_llm_call(**kwargs)
    
    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        return self.collector.get_report(session)
    
    def track(self, operation_type: str, **metadata):
        return self.collector.track(operation_type, metadata)