"""
Enhanced Metrics Collector
Location: observatory/collector.py

Collects and manages metrics for AI agent sessions with support for:
- Basic metrics (cost, latency, tokens)
- Routing decisions
- Cache metadata
- Quality evaluations
- Prompt/response tracking
- NEW: Prompt breakdown and metadata
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
    PromptBreakdown,  # NEW
    PromptMetadata,   # NEW
)
from observatory.storage import Storage


# Simple cost calculation (replaces cost_analyzer)
def calculate_cost(provider: ModelProvider, model_name: str, prompt_tokens: int, completion_tokens: int) -> tuple:
    """Calculate cost for LLM call. Returns (prompt_cost, completion_cost)."""
    # Simplified pricing (add more models as needed)
    pricing = {
        "gpt-4": (0.03 / 1000, 0.06 / 1000),
        "gpt-4o": (0.0025 / 1000, 0.01 / 1000),
        "gpt-4o-mini": (0.00015 / 1000, 0.0006 / 1000),
        "gpt-3.5-turbo": (0.0005 / 1000, 0.0015 / 1000),
        "claude-4": (0.015 / 1000, 0.075 / 1000),
        "claude-sonnet-4": (0.003 / 1000, 0.015 / 1000),
        "claude-3-5-sonnet": (0.003 / 1000, 0.015 / 1000),
        "claude-opus-4": (0.015 / 1000, 0.075 / 1000),
        "mistral-small": (0.0002 / 1000, 0.0006 / 1000),
    }
    
    # Find pricing (case insensitive, partial match)
    model_lower = model_name.lower()
    prompt_price, completion_price = 0.001 / 1000, 0.002 / 1000  # Default
    
    for key, prices in pricing.items():
        if key in model_lower:
            prompt_price, completion_price = prices
            break
    
    prompt_cost = prompt_tokens * prompt_price
    completion_cost = completion_tokens * completion_price
    
    return prompt_cost, completion_cost


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
        
        # Enhanced fields - Routing (None in discovery mode)
        routing_decision: Optional[RoutingDecision] = None,
        
        # Enhanced fields - Caching (None in discovery mode)
        cache_metadata: Optional[CacheMetadata] = None,
        
        # Enhanced fields - Quality (optional)
        quality_evaluation: Optional[QualityEvaluation] = None,
        
        # NEW: Enhanced fields - Prompt Analysis (optional)
        prompt_breakdown: Optional[PromptBreakdown] = None,
        prompt_metadata: Optional[PromptMetadata] = None,
        
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
            routing_decision: Routing decision metadata (None in discovery mode)
            cache_metadata: Cache hit/miss metadata (None in discovery mode)
            quality_evaluation: Quality/judge evaluation (optional)
            prompt_breakdown: Structured breakdown of prompt components (NEW)
            prompt_metadata: Prompt template versioning metadata (NEW)
            prompt_variant_id: ID for A/B testing
            test_dataset_id: Test dataset ID for evaluation
        
        Returns:
            LLMCall object
            
        Note:
            DISCOVERY MODE: routing_decision and cache_metadata are None by default.
            This enables pattern discovery from observables (tokens, cost, latency, operation).
            Populate these fields once you implement routing/caching logic.
        """
        if not self.enabled:
            return LLMCall(
                id="disabled",
                session_id="disabled",
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                prompt_cost=0.0,
                completion_cost=0.0,
                total_cost=0.0,
                latency_ms=latency_ms,
            )
        
        target_session = session or self.current_session
        if not target_session:
            # Auto-create session if needed
            target_session = self.start_session(operation)
        
        # Calculate costs
        prompt_cost, completion_cost = calculate_cost(
            provider, model_name, prompt_tokens, completion_tokens
        )
        total_tokens = prompt_tokens + completion_tokens
        total_cost = prompt_cost + completion_cost
        
        llm_call = LLMCall(
            id=str(uuid.uuid4()),
            session_id=target_session.id,
            provider=provider,
            model_name=model_name,
            prompt=prompt,
            prompt_normalized=prompt_normalized,
            response_text=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            agent_name=agent_name,
            agent_role=agent_role,
            operation=operation,
            success=success,
            error=error,
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_breakdown=prompt_breakdown,  # NEW
            prompt_metadata=prompt_metadata,    # NEW
            prompt_variant_id=prompt_variant_id,
            test_dataset_id=test_dataset_id,
            metadata=metadata or {},
        )
        
        # Update session aggregates
        target_session.total_llm_calls += 1
        target_session.total_tokens += total_tokens
        target_session.total_cost += total_cost
        target_session.total_latency_ms += latency_ms
        target_session.llm_calls.append(llm_call)
        
        # Update routing metrics
        if routing_decision:
            target_session.total_routing_decisions += 1
            if routing_decision.estimated_cost_savings:
                target_session.routing_cost_savings += routing_decision.estimated_cost_savings
        
        # Update cache metrics
        if cache_metadata:
            if cache_metadata.cache_hit:
                target_session.total_cache_hits += 1
            else:
                target_session.total_cache_misses += 1
        
        # Update quality metrics
        if quality_evaluation:
            if quality_evaluation.hallucination_flag:
                target_session.total_hallucinations += 1
            if not success or (quality_evaluation.judge_score and quality_evaluation.judge_score < 5.0):
                target_session.total_errors += 1
        
        # Persist
        self.storage.save_llm_call(llm_call)
        self.storage.update_session(target_session)
        
        return llm_call

    def record_with_routing(
        self,
        chosen_model: str,
        alternative_models: Optional[List[str]] = None,
        reasoning: str = "",
        complexity_score: Optional[float] = None,
        estimated_cost_savings: Optional[float] = None,
        routing_strategy: Optional[str] = None,  # NEW
        model_scores: Optional[Dict[str, float]] = None,  # NEW
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with routing decision.
        
        Args:
            chosen_model: Model selected for this call
            alternative_models: Other models that could have been used
            reasoning: Why this model was chosen
            complexity_score: Estimated task complexity (0-1)
            estimated_cost_savings: Estimated savings from this routing choice
            routing_strategy: Strategy used for routing (NEW)
            model_scores: Scores for each model considered (NEW)
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        routing_decision = RoutingDecision(
            chosen_model=chosen_model,
            alternative_models=alternative_models or [],
            reasoning=reasoning,
            complexity_score=complexity_score,
            estimated_cost_savings=estimated_cost_savings,
            routing_strategy=routing_strategy,
            model_scores=model_scores or {},
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
        cache_key_candidates: Optional[List[str]] = None,  # NEW
        content_hash: Optional[str] = None,  # NEW
        ttl_seconds: Optional[int] = None,  # NEW
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with cache metadata.
        
        Args:
            cache_hit: Whether this was a cache hit
            cache_key: Cache key used
            cache_cluster_id: Cluster ID for prompt clustering
            similarity_score: Similarity score (0-1)
            cache_key_candidates: Alternative keys considered (NEW)
            content_hash: Hash of cacheable content (NEW)
            ttl_seconds: Time-to-live for cache entry (NEW)
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        cache_metadata = CacheMetadata(
            cache_hit=cache_hit,
            cache_key=cache_key,
            cache_cluster_id=cache_cluster_id,
            similarity_score=similarity_score,
            cache_key_candidates=cache_key_candidates,
            content_hash=content_hash,
            ttl_seconds=ttl_seconds,
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
        confidence_score: Optional[float] = None,
        judge_model: Optional[str] = None,  # NEW
        failure_reason: Optional[str] = None,  # NEW
        improvement_suggestion: Optional[str] = None,  # NEW
        criteria_scores: Optional[Dict[str, float]] = None,  # NEW
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with quality evaluation.
        
        Args:
            judge_score: Judge score (0-10)
            hallucination_flag: Whether hallucination detected
            error_category: Category of error if any
            reasoning: Judge's reasoning
            confidence_score: Judge's confidence (0-1)
            judge_model: Model used for judging (NEW)
            failure_reason: Failure category (NEW)
            improvement_suggestion: How to improve (NEW)
            criteria_scores: Individual criteria scores (NEW)
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        quality_evaluation = QualityEvaluation(
            judge_score=judge_score,
            hallucination_flag=hallucination_flag,
            error_category=error_category,
            reasoning=reasoning,
            confidence_score=confidence_score,
            judge_model=judge_model,
            failure_reason=failure_reason,
            improvement_suggestion=improvement_suggestion,
            criteria_scores=criteria_scores,
        )
        
        return self.record_llm_call(
            quality_evaluation=quality_evaluation,
            **kwargs
        )

    def record_with_prompt_analysis(
        self,
        # Prompt breakdown fields
        system_prompt: Optional[str] = None,
        system_prompt_tokens: Optional[int] = None,
        user_message: Optional[str] = None,
        user_message_tokens: Optional[int] = None,
        chat_history: Optional[List[Dict]] = None,
        chat_history_tokens: Optional[int] = None,
        # Prompt metadata fields
        prompt_template_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        compressible_sections: Optional[List[str]] = None,
        optimization_flags: Optional[Dict[str, bool]] = None,
        **kwargs
    ) -> LLMCall:
        """
        NEW: Convenience method for recording a call with prompt analysis.
        
        Args:
            system_prompt: System prompt text
            system_prompt_tokens: Token count for system prompt
            user_message: User message text
            user_message_tokens: Token count for user message
            chat_history: Chat history list
            chat_history_tokens: Token count for chat history
            prompt_template_id: Template identifier
            prompt_version: Template version
            compressible_sections: Sections that can be compressed
            optimization_flags: Optimization flags
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        prompt_breakdown = None
        if any([system_prompt, user_message, chat_history]):
            prompt_breakdown = PromptBreakdown(
                system_prompt=system_prompt,
                system_prompt_tokens=system_prompt_tokens,
                user_message=user_message,
                user_message_tokens=user_message_tokens,
                chat_history=chat_history,
                chat_history_tokens=chat_history_tokens,
                chat_history_count=len(chat_history) if chat_history else None,
            )
        
        prompt_metadata = None
        if any([prompt_template_id, prompt_version]):
            prompt_metadata = PromptMetadata(
                prompt_template_id=prompt_template_id,
                prompt_version=prompt_version,
                compressible_sections=compressible_sections,
                optimization_flags=optimization_flags,
            )
        
        return self.record_llm_call(
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            **kwargs
        )

    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """
        Generate a basic report for a session.
        
        Note: Dashboard uses aggregators.py for detailed analysis.
        This method provides basic session summary.
        
        Args:
            session: Session to report on (uses current if None)
        
        Returns:
            SessionReport with basic metrics
        """
        if not self.enabled:
            return None
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No session to report on")
        
        # Load full session data if needed
        if not target_session.llm_calls:
            target_session = self.storage.get_session(target_session.id)
        
        # Calculate basic metrics from session
        total_cost = target_session.total_cost
        total_tokens = target_session.total_tokens
        total_latency = target_session.total_latency_ms
        num_calls = target_session.total_llm_calls
        
        # Create basic breakdown dictionaries
        cost_breakdown = {
            'total_cost': total_cost,
            'avg_cost_per_call': total_cost / num_calls if num_calls > 0 else 0
        }
        
        latency_breakdown = {
            'total_latency_ms': total_latency,
            'avg_latency_ms': total_latency / num_calls if num_calls > 0 else 0
        }
        
        token_breakdown = {
            'total_tokens': total_tokens,
            'avg_tokens_per_call': total_tokens / num_calls if num_calls > 0 else 0
        }
        
        quality_metrics = {
            'success_rate': 1.0 if target_session.success else 0.0,
            'total_calls': num_calls
        }
        
        # Basic suggestions
        suggestions = []
        if total_cost > 1.0:
            suggestions.append("Consider using cheaper models for simple tasks")
        if total_latency / num_calls > 5000 if num_calls > 0 else False:
            suggestions.append("High average latency detected")
        
        return SessionReport(
            session=target_session,
            cost_breakdown=cost_breakdown,
            latency_breakdown=latency_breakdown,
            token_breakdown=token_breakdown,
            quality_metrics=quality_metrics,
            optimization_suggestions=suggestions,
        )

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
    
    def record_with_prompt_analysis(self, **kwargs) -> LLMCall:
        """NEW: Record a call with prompt breakdown and metadata."""
        return self.collector.record_with_prompt_analysis(**kwargs)
    
    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """Generate session report."""
        return self.collector.get_report(session)
    
    def track(self, operation_type: str, **metadata):
        """Context manager for tracking a session."""
        return self.collector.track(operation_type, metadata)