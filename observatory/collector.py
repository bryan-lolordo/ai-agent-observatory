"""
Enhanced Metrics Collector
Location: observatory/collector.py

Collects and manages metrics for AI agent sessions with support for:
- Basic metrics (cost, latency, tokens)
- Routing decisions
- Cache metadata
- Quality evaluations
- Prompt/response tracking
"""

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
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
)
from observatory.storage import Storage
from observatory.analyzers.cost_analyzer import CostAnalyzer
from observatory.analyzers.latency_analyzer import LatencyAnalyzer
from observatory.analyzers.token_analyzer import TokenAnalyzer
from observatory.analyzers.quality_analyzer import QualityAnalyzer


class MetricsCollector:
    """
    Core metrics collection class.
    Tracks sessions and LLM calls with comprehensive metrics.
    """
    
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
        """
        Start a new tracking session.
        
        Args:
            operation_type: Type of operation (e.g., "job_search", "code_review")
            metadata: Additional session metadata
        
        Returns:
            Session object
        """
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

    def end_session(
        self,
        session: Optional[Session] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> Session:
        """
        End a tracking session and finalize metrics.
        
        Args:
            session: Session to end (uses current if None)
            success: Whether session completed successfully
            error: Optional error message
        
        Returns:
            Completed session
        """
        if not self.enabled:
            return session or Session(id="disabled", project_name=self.project_name)
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No active session to end")
        
        target_session.end_time = datetime.utcnow()
        target_session.success = success
        target_session.error = error
        
        # Calculate average quality score if we have quality evaluations
        if target_session.llm_calls:
            quality_scores = [
                call.quality_evaluation.judge_score
                for call in target_session.llm_calls
                if call.quality_evaluation and call.quality_evaluation.judge_score is not None
            ]
            if quality_scores:
                target_session.avg_quality_score = sum(quality_scores) / len(quality_scores)
        
        self.storage.update_session(target_session)
        
        if target_session == self.current_session:
            self.current_session = None
        
        return target_session

    def record_llm_call(
        self,
        # Basic fields (required)
        provider: ModelProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        
        # Context fields (optional)
        agent_name: Optional[str] = None,
        agent_role: Optional[AgentRole] = None,
        operation: Optional[str] = None,
        session: Optional[Session] = None,
        
        # Status fields (optional)
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        
        # Enhanced fields - Prompts (optional)
        prompt: Optional[str] = None,
        prompt_normalized: Optional[str] = None,
        response_text: Optional[str] = None,
        
        # Enhanced fields - Routing (auto-created if None)
        routing_decision: Optional[RoutingDecision] = None,
        
        # Enhanced fields - Caching (auto-created if None)
        cache_metadata: Optional[CacheMetadata] = None,
        
        # Enhanced fields - Quality (optional)
        quality_evaluation: Optional[QualityEvaluation] = None,
        
        # Enhanced fields - A/B Testing (optional)
        prompt_variant_id: Optional[str] = None,
        test_dataset_id: Optional[str] = None,
    ) -> LLMCall:
        """
        Record an LLM API call with comprehensive metrics.
        
        Args:
            provider: Model provider (OPENAI, ANTHROPIC, etc.)
            model_name: Name of the model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            latency_ms: Request latency in milliseconds
            agent_name: Name of the agent making the call
            agent_role: Role of the agent
            operation: Type of operation
            session: Session to attach to (uses current if None)
            success: Whether the call succeeded
            error: Error message if failed
            metadata: Additional metadata
            prompt: Raw prompt text
            prompt_normalized: Normalized/cleaned prompt for caching
            response_text: Response text from the model
            routing_decision: Routing decision metadata (auto-created with defaults if None)
            cache_metadata: Cache hit/miss metadata (auto-created with defaults if None)
            quality_evaluation: Quality/judge evaluation (optional, remains None if not provided)
            prompt_variant_id: ID for A/B testing
            test_dataset_id: Test dataset ID for evaluation
        
        Returns:
            LLMCall object
            
        Note:
            - routing_decision: If not provided, creates default showing "direct model selection"
            - cache_metadata: If not provided, creates default showing cache_hit=False
            - quality_evaluation: Remains None if not provided (expensive to run on every call)
        """
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
        
        # Auto-create routing decision if not provided
        if routing_decision is None:
            routing_decision = RoutingDecision(
                chosen_model=model_name,
                alternative_models=[],
                model_scores={model_name: 1.0},
                reasoning="Direct model selection (no routing logic applied)"
            )
        
        # Auto-create cache metadata if not provided
        if cache_metadata is None:
            cache_metadata = CacheMetadata(
                cache_hit=False,
                cache_key=None,
                cache_cluster_id=None
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
            # Enhanced fields
            prompt=prompt,
            prompt_normalized=prompt_normalized,
            response_text=response_text,
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_variant_id=prompt_variant_id,
            test_dataset_id=test_dataset_id,
        )
        
        # Update session aggregates - Basic metrics
        target_session.total_llm_calls += 1
        target_session.total_tokens += llm_call.total_tokens
        target_session.total_cost += llm_call.total_cost
        target_session.total_latency_ms += llm_call.latency_ms
        
        # Update session aggregates - Routing metrics
        if routing_decision:
            target_session.total_routing_decisions += 1
            if routing_decision.estimated_cost_savings:
                target_session.routing_cost_savings += routing_decision.estimated_cost_savings
        
        # Update session aggregates - Cache metrics
        if cache_metadata:
            if cache_metadata.cache_hit:
                target_session.total_cache_hits += 1
                # Estimate cache savings (full cost of this call)
                target_session.cache_cost_savings += llm_call.total_cost
            else:
                target_session.total_cache_misses += 1
        
        # Update session aggregates - Quality metrics
        if quality_evaluation:
            if quality_evaluation.hallucination_flag:
                target_session.total_hallucinations += 1
            if not success or (quality_evaluation.judge_score and quality_evaluation.judge_score < 5.0):
                target_session.total_errors += 1
        
        target_session.llm_calls.append(llm_call)
        
        # Persist
        self.storage.save_llm_call(llm_call)
        self.storage.update_session(target_session)
        
        return llm_call

    def record_with_routing(
        self,
        chosen_model: str,
        alternative_models: List[str],
        model_scores: Dict[str, float],
        reasoning: str,
        estimated_savings: Optional[float] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with routing decision.
        
        Args:
            chosen_model: Model that was chosen by router
            alternative_models: Models that were considered
            model_scores: Scores for each model
            reasoning: Why this model was chosen
            estimated_savings: Estimated cost savings from routing
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        routing_decision = RoutingDecision(
            chosen_model=chosen_model,
            alternative_models=alternative_models,
            model_scores=model_scores,
            reasoning=reasoning,
            estimated_cost_savings=estimated_savings
        )
        
        return self.record_llm_call(
            routing_decision=routing_decision,
            **kwargs
        )

    def record_with_cache(
        self,
        cache_hit: bool,
        cache_key: Optional[str] = None,
        cache_cluster_id: Optional[str] = None,
        similarity_score: Optional[float] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with cache metadata.
        
        Args:
            cache_hit: Whether this was a cache hit
            cache_key: Cache key used
            cache_cluster_id: Cluster ID for prompt clustering
            similarity_score: Similarity score (0-1)
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        cache_metadata = CacheMetadata(
            cache_hit=cache_hit,
            cache_key=cache_key,
            cache_cluster_id=cache_cluster_id,
            similarity_score=similarity_score
        )
        
        return self.record_llm_call(
            cache_metadata=cache_metadata,
            **kwargs
        )

    def record_with_quality(
        self,
        judge_score: Optional[float] = None,
        hallucination_flag: bool = False,
        error_category: Optional[str] = None,
        reasoning: Optional[str] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with quality evaluation.
        
        Args:
            judge_score: Judge score (0-10)
            hallucination_flag: Whether hallucination detected
            error_category: Category of error if any
            reasoning: Judge's reasoning
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        quality_evaluation = QualityEvaluation(
            judge_score=judge_score,
            hallucination_flag=hallucination_flag,
            error_category=error_category,
            reasoning=reasoning
        )
        
        return self.record_llm_call(
            quality_evaluation=quality_evaluation,
            **kwargs
        )

    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """
        Generate a comprehensive report for a session.
        
        Args:
            session: Session to report on (uses current if None)
        
        Returns:
            SessionReport with all analytics
        """
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

    def _generate_suggestions(
        self,
        session: Session,
        cost_breakdown,
        latency_breakdown,
        token_breakdown,
        quality_metrics
    ) -> List[str]:
        """Generate optimization suggestions based on session metrics."""
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
        
        # Cache optimization
        if session.total_cache_hits + session.total_cache_misses > 0:
            hit_rate = session.total_cache_hits / (session.total_cache_hits + session.total_cache_misses)
            if hit_rate < 0.30:
                suggestions.append(
                    f"💾 Low cache hit rate ({hit_rate:.1%}). Consider improving prompt normalization."
                )
        
        # Routing optimization
        if session.routing_cost_savings > 0:
            suggestions.append(
                f"✅ Routing saved ${session.routing_cost_savings:.4f} this session. Good job!"
            )
        
        # Hallucination warning
        if session.total_hallucinations > 0:
            suggestions.append(
                f"⚠️ Detected {session.total_hallucinations} hallucination(s). Review quality checks."
            )
        
        return suggestions

    @contextmanager
    def track(
        self,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracking a session.
        
        Usage:
            with collector.track("job_search"):
                # Your code here
                collector.record_llm_call(...)
        
        Args:
            operation_type: Type of operation
            metadata: Additional metadata
        
        Yields:
            Session object
        """
        session = self.start_session(operation_type, metadata)
        try:
            yield session
            self.end_session(session, success=True)
        except Exception as e:
            self.end_session(session, success=False, error=str(e))
            raise


class Observatory:
    """
    Main Observatory interface for applications.
    Simplified wrapper around MetricsCollector.
    """
    
    def __init__(
        self,
        project_name: str = "default",
        enabled: Optional[bool] = None,
        storage: Optional[Storage] = None,
    ):
        """
        Initialize Observatory.
        
        Args:
            project_name: Name of the project being tracked
            enabled: Enable/disable tracking (defaults to ENABLE_OBSERVATORY env var)
            storage: Custom storage instance
        """
        if enabled is None:
            enabled = os.getenv("ENABLE_OBSERVATORY", "false").lower() == "true"
        
        self.collector = MetricsCollector(
            project_name=project_name,
            enabled=enabled,
            storage=storage,
        )
    
    def start_session(self, operation_type: Optional[str] = None, **kwargs) -> Session:
        """Start a tracking session."""
        return self.collector.start_session(operation_type, kwargs)
    
    def end_session(self, session: Optional[Session] = None) -> Session:
        """End a tracking session."""
        return self.collector.end_session(session)
    
    def record_call(self, **kwargs) -> LLMCall:
        """Record an LLM call. Accepts all record_llm_call arguments."""
        return self.collector.record_llm_call(**kwargs)
    
    def record_with_routing(self, **kwargs) -> LLMCall:
        """Record a call with routing decision."""
        return self.collector.record_with_routing(**kwargs)
    
    def record_with_cache(self, **kwargs) -> LLMCall:
        """Record a call with cache metadata."""
        return self.collector.record_with_cache(**kwargs)
    
    def record_with_quality(self, **kwargs) -> LLMCall:
        """Record a call with quality evaluation."""
        return self.collector.record_with_quality(**kwargs)
    
    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """Generate session report."""
        return self.collector.get_report(session)
    
    def track(self, operation_type: str, **metadata):
        """Context manager for tracking a session."""
        return self.collector.track(operation_type, metadata)