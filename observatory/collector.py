"""
Enhanced Metrics Collector
Location: observatory/collector.py

Collects and manages metrics for AI agent sessions with support for:
- Basic metrics (cost, latency, tokens)
- Routing decisions
- Cache metadata
- Quality evaluations
- Prompt/response tracking
- Prompt breakdown and metadata
- Auto-generated prompt hash for version detection
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from observatory.models import (
    LLMCall,
    Session,
    SessionReport,
    ModelProvider,
    AgentRole,
    CallType,
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
    ModelConfig,
    StreamingMetrics,
    ErrorDetails,
    ExperimentMetadata,
)
from observatory.storage import Storage
from observatory.cache import normalize_prompt, compute_content_hash


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_prompt_hash(prompt: str, prefix_length: int = 500) -> str:
    """
    Generate a short hash from prompt prefix for version detection.
    
    Args:
        prompt: Full prompt text
        prefix_length: Number of characters to hash (default 500)
    
    Returns:
        8-character hex hash
    """
    if not prompt:
        return ""
    return hashlib.md5(prompt[:prefix_length].encode()).hexdigest()[:8]


def calculate_cost(provider: ModelProvider, model_name: str, prompt_tokens: int, completion_tokens: int) -> tuple:
    """Calculate cost for LLM call. Returns (prompt_cost, completion_cost)."""
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
    
    model_lower = model_name.lower()
    prompt_price, completion_price = 0.001 / 1000, 0.002 / 1000  # Default
    
    for key, prices in pricing.items():
        if key in model_lower:
            prompt_price, completion_price = prices
            break
    
    prompt_cost = prompt_tokens * prompt_price
    completion_cost = completion_tokens * completion_price
    
    return prompt_cost, completion_cost


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

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
        """Start a new tracking session."""
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
            start_time=datetime.now(),  # <-- ADD THIS LINE
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
        """End a tracking session and finalize metrics."""
        if not self.enabled:
            return session or Session(id="disabled", project_name=self.project_name)
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No active session to end")
        
        target_session.end_time = datetime.utcnow()
        target_session.success = success
        target_session.error = error
        
        # Calculate average quality score
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

        # Call classification
        call_type: CallType = CallType.LLM,
        
        # Context fields (optional)
        agent_name: Optional[str] = None,
        agent_role: Optional[AgentRole] = None,
        operation: Optional[str] = None,
        session: Optional[Session] = None,
        
        # Status fields (optional)
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        
        # Prompt content (optional)
        prompt: Optional[str] = None,
        prompt_normalized: Optional[str] = None,
        response_text: Optional[str] = None,
        
        # NEW: Separate prompt components for detailed tracking
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        
        # Routing (None in discovery mode)
        routing_decision: Optional[RoutingDecision] = None,
        
        # Caching (None in discovery mode)
        cache_metadata: Optional[CacheMetadata] = None,
        
        # Quality (optional)
        quality_evaluation: Optional[QualityEvaluation] = None,
        
        # Prompt Analysis (optional)
        prompt_breakdown: Optional[PromptBreakdown] = None,
        prompt_metadata: Optional[PromptMetadata] = None,
        
        # A/B Testing (optional)
        prompt_variant_id: Optional[str] = None,
        test_dataset_id: Optional[str] = None,
        
        # NEW: Conversation linking
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        parent_call_id: Optional[str] = None,
        user_id: Optional[str] = None,
        
        # NEW: Model configuration
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        model_config: Optional['ModelConfig'] = None,
        
        # NEW: Token breakdown (top-level)
        system_prompt_tokens: Optional[int] = None,
        user_message_tokens: Optional[int] = None,
        chat_history_tokens: Optional[int] = None,
        chat_history_count: Optional[int] = None, 
        conversation_context_tokens: Optional[int] = None,
        tool_definitions_tokens: Optional[int] = None,
        
        # NEW: Tool/function calling
        tool_calls_made: Optional[List[Dict]] = None,
        tool_call_count: Optional[int] = None,
        tool_execution_time_ms: Optional[float] = None,
        
        # NEW: Streaming
        time_to_first_token_ms: Optional[float] = None,
        streaming_metrics: Optional['StreamingMetrics'] = None,
        
        # NEW: Error details
        error_type: Optional[str] = None,
        error_code: Optional[str] = None,
        retry_count: Optional[int] = None,
        error_details: Optional['ErrorDetails'] = None,
        
        # NEW: Cached tokens
        cached_prompt_tokens: Optional[int] = None,
        cached_token_savings: Optional[float] = None,
        
        # NEW: Observability
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        environment: Optional[str] = None,

        # NEW: Prefix hash for cache detection
        prompt_prefix_hash: Optional[str] = None,
        
        # NEW: Experiment tracking
        experiment_id: Optional[str] = None,
        control_group: Optional[bool] = None,
        experiment_metadata: Optional['ExperimentMetadata'] = None,
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
            agent_role: Role of the agent (analyst, reviewer, writer, etc.)
            operation: Type of operation
            session: Session to attach to (uses current if None)
            success: Whether the call succeeded
            error: Error message if failed
            metadata: Additional metadata dict
            prompt: Raw prompt text (combined)
            prompt_normalized: Normalized prompt for caching
            response_text: Response text from the model
            system_prompt: System prompt text (tracked separately)
            user_message: User message text (tracked separately)
            messages: Full conversation history as list of {role, content} dicts
            routing_decision: Routing decision metadata
            cache_metadata: Cache hit/miss metadata
            quality_evaluation: Quality/judge evaluation
            prompt_breakdown: Structured breakdown of prompt components
            prompt_metadata: Prompt template versioning metadata
            prompt_variant_id: ID for A/B testing
            test_dataset_id: Test dataset ID for evaluation
        
        Returns:
            LLMCall object
        """
        if not self.enabled:
            return LLMCall(
                id="disabled",
                session_id="disabled",
                call_type=call_type,
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
        
        # Auto-start session if needed
        if not target_session:
            target_session = self.start_session(operation_type=operation)
        
        # Calculate costs
        prompt_cost, completion_cost = calculate_cost(
            provider, model_name, prompt_tokens, completion_tokens
        )
        total_cost = prompt_cost + completion_cost
        total_tokens = prompt_tokens + completion_tokens
        
        # Build combined prompt if not provided but components are
        if not prompt and (system_prompt or user_message):
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(f"[SYSTEM]\n{system_prompt}")
            if user_message:
                prompt_parts.append(f"[USER]\n{user_message}")
            prompt = "\n\n".join(prompt_parts)
        elif not prompt and messages:
            prompt = "\n\n".join([
                f"[{m.get('role', 'unknown').upper()}]\n{m.get('content', '')}"
                for m in messages
            ])
        
        # Auto-generate prompt hash
        if prompt and prompt_metadata and not prompt_metadata.prompt_hash:
            prompt_metadata.prompt_hash = generate_prompt_hash(prompt)
        elif prompt and not prompt_metadata:
            prompt_metadata = PromptMetadata(
                prompt_hash=generate_prompt_hash(prompt)
            )
        
        # Build metadata with prompt components
        full_metadata = metadata or {}
        if system_prompt:
            full_metadata['system_prompt'] = system_prompt[:2000]
        if user_message:
            full_metadata['user_message'] = user_message[:1000]
        if messages:
            full_metadata['messages'] = messages
            full_metadata['message_count'] = len(messages)
        
        # ⭐ NEW: Auto-extract judge scores if this is a LLMJudge call
        if agent_name == 'LLMJudge' and response_text and not quality_evaluation:
            try:
                import json
                judge_data = json.loads(response_text)
                
                # Create QualityEvaluation from judge response
                quality_evaluation = QualityEvaluation(
                    judge_score=judge_data.get('score'),
                    reasoning=judge_data.get('reasoning'),
                    hallucination_flag=judge_data.get('hallucination', False),
                    confidence_score=judge_data.get('confidence'),
                    evidence_cited=judge_data.get('evidence_cited', False),
                    factual_error=judge_data.get('factual_error', False),
                    criteria_scores=judge_data.get('criteria_scores'),
                )
            except (json.JSONDecodeError, KeyError) as e:
                # If parsing fails, keep quality_evaluation as None
                pass
        
        # =====================================================================
        # AUTO-GENERATE: prompt_normalized and content_hash for cache analytics
        # =====================================================================
        # If prompt exists but prompt_normalized wasn't provided, auto-generate
        if prompt and not prompt_normalized:
            prompt_normalized = normalize_prompt(prompt)
        
        # Generate content_hash for deduplication detection
        content_hash = None
        if prompt:
            content_hash = compute_content_hash(prompt)
        
        # Auto-extract token breakdown fields from prompt_breakdown if not provided
        if prompt_breakdown:
            if chat_history_count is None:
                chat_history_count = prompt_breakdown.chat_history_count
            
            if chat_history_tokens is None:
                chat_history_tokens = prompt_breakdown.chat_history_tokens
            
            if system_prompt_tokens is None:
                system_prompt_tokens = prompt_breakdown.system_prompt_tokens
            
            if user_message_tokens is None:
                user_message_tokens = prompt_breakdown.user_message_tokens
            
            if conversation_context_tokens is None:
                conversation_context_tokens = prompt_breakdown.conversation_context_tokens
            
            if tool_definitions_tokens is None:
                tool_definitions_tokens = prompt_breakdown.tool_definitions_tokens
        
        # Create the LLM call record
        llm_call = LLMCall(
            id=request_id if request_id else str(uuid.uuid4()),
            session_id=target_session.id,
            timestamp=datetime.utcnow(),
            call_type=call_type,
            provider=provider,
            model_name=model_name,
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
            metadata=full_metadata,
            prompt=prompt,
            prompt_normalized=prompt_normalized,
            content_hash=content_hash,
            response_text=response_text,
            system_prompt=system_prompt,      
            user_message=user_message,       
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            prompt_variant_id=prompt_variant_id,
            test_dataset_id=test_dataset_id,
            # NEW: Conversation linking
            conversation_id=conversation_id,
            turn_number=turn_number,
            parent_call_id=parent_call_id,
            user_id=user_id,
            # NEW: Model configuration
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            llm_config=model_config,
            # NEW: Token breakdown
            system_prompt_tokens=system_prompt_tokens,
            user_message_tokens=user_message_tokens,
            chat_history_tokens=chat_history_tokens,
            chat_history_count=chat_history_count,
            conversation_context_tokens=conversation_context_tokens,
            tool_definitions_tokens=tool_definitions_tokens,
            # NEW: Tool tracking
            tool_calls_made=tool_calls_made,
            tool_call_count=tool_call_count,
            tool_execution_time_ms=tool_execution_time_ms,
            # NEW: Streaming
            time_to_first_token_ms=time_to_first_token_ms,
            streaming_metrics=streaming_metrics,
            # NEW: Error details
            error_type=error_type,
            error_code=error_code,
            retry_count=retry_count,
            error_details=error_details,
            # NEW: Cached tokens
            cached_prompt_tokens=cached_prompt_tokens,
            cached_token_savings=cached_token_savings,
            # NEW: Observability
            trace_id=trace_id,
            request_id=request_id,
            environment=environment,
            # NEW: Prefix hash
            prompt_prefix_hash=prompt_prefix_hash,
            # NEW: Experiment tracking
            experiment_id=experiment_id,
            control_group=control_group,
            experiment_metadata=experiment_metadata,
        )
        
        # Update session metrics
        target_session.llm_calls.append(llm_call)
        target_session.total_llm_calls += 1
        target_session.total_tokens += total_tokens
        target_session.total_cost += total_cost
        target_session.total_latency_ms += latency_ms
        
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
        
        # Update error count
        if not success:
            target_session.total_errors += 1
        
        # Persist
        self.storage.save_llm_call(llm_call)
        self.storage.update_session(target_session)
        
        return llm_call

    # =========================================================================
    # CONVENIENCE RECORDING METHODS
    # =========================================================================

    def record_with_routing(
        self,
        chosen_model: str,
        alternative_models: List[str],
        routing_reason: str,
        complexity_score: Optional[float] = None,
        estimated_cost_savings: Optional[float] = None,
        routing_strategy: Optional[str] = None,
        **kwargs
    ) -> LLMCall:
        """Convenience method for recording a call with routing decision."""
        routing_decision = RoutingDecision(
            chosen_model=chosen_model,
            alternative_models=alternative_models,
            reasoning=routing_reason,
            complexity_score=complexity_score,
            estimated_cost_savings=estimated_cost_savings,
            routing_strategy=routing_strategy,
        )
        
        return self.record_llm_call(routing_decision=routing_decision, **kwargs)

    def record_with_cache(
        self,
        cache_hit: bool,
        cache_key: Optional[str] = None,
        cache_cluster_id: Optional[str] = None,
        similarity_score: Optional[float] = None,
        **kwargs
    ) -> LLMCall:
        """Convenience method for recording a call with cache metadata."""
        cache_metadata = CacheMetadata(
            cache_hit=cache_hit,
            cache_key=cache_key,
            cache_cluster_id=cache_cluster_id,
            similarity_score=similarity_score,
        )
        
        return self.record_llm_call(cache_metadata=cache_metadata, **kwargs)

    def record_with_quality(
        self,
        judge_score: float,
        judge_reasoning: str,
        hallucination_flag: bool = False,
        confidence: Optional[float] = None,
        **kwargs
    ) -> LLMCall:
        """Convenience method for recording a call with quality evaluation."""
        quality_evaluation = QualityEvaluation(
            judge_score=judge_score,
            reasoning=judge_reasoning,
            hallucination_flag=hallucination_flag,
            confidence_score=confidence,  # <-- LINE 429: FIXED
        )
        
        return self.record_llm_call(quality_evaluation=quality_evaluation, **kwargs)

    def record_with_prompt_analysis(
        self,
        system_prompt: Optional[str] = None,
        system_prompt_tokens: Optional[int] = None,
        user_message: Optional[str] = None,
        user_message_tokens: Optional[int] = None,
        chat_history: Optional[List[Dict]] = None,
        chat_history_tokens: Optional[int] = None,
        prompt_template_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        experiment_id: Optional[str] = None,
        compressible_sections: Optional[List[str]] = None,
        optimization_flags: Optional[Dict[str, bool]] = None,
        **kwargs
    ) -> LLMCall:
        """Convenience method for recording a call with prompt analysis."""
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
        if any([prompt_template_id, prompt_version, prompt_hash, experiment_id]):
            prompt_metadata = PromptMetadata(
                prompt_template_id=prompt_template_id,
                prompt_version=prompt_version,
                prompt_hash=prompt_hash,
                experiment_id=experiment_id,
                compressible_sections=compressible_sections,
                optimization_flags=optimization_flags,
            )
        
        return self.record_llm_call(
            system_prompt=system_prompt,
            user_message=user_message,
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            **kwargs
        )

    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """Generate a basic report for a session."""
        if not self.enabled:
            return None
        
        target_session = session or self.current_session
        if not target_session:
            raise ValueError("No session to report on")
        
        if not target_session.llm_calls:
            target_session = self.storage.get_session(target_session.id)
        
        total_cost = target_session.total_cost
        total_tokens = target_session.total_tokens
        total_latency = target_session.total_latency_ms
        num_calls = target_session.total_llm_calls
        
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
        
        suggestions = []
        if total_cost > 1.0:
            suggestions.append("Consider using cheaper models for simple tasks")
        if num_calls > 0 and total_latency / num_calls > 5000:
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
        """Context manager for tracking a session."""
        session = self.start_session(operation_type, metadata)
        try:
            yield session
            self.end_session(session, success=True)
        except Exception as e:
            self.end_session(session, success=False, error=str(e))
            raise


# =============================================================================
# OBSERVATORY WRAPPER
# =============================================================================

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
        if enabled is None:
            enabled = os.getenv("ENABLE_OBSERVATORY", "true").lower() == "true"
        
        self.collector = MetricsCollector(
            project_name=project_name,
            enabled=enabled,
            storage=storage,
        )
    
    def start_session(self, operation_type: Optional[str] = None, **kwargs) -> Session:
        """Start a tracking session."""
        return self.collector.start_session(operation_type, kwargs)
    
    def end_session(self, session: Optional[Session] = None, success: bool = True, error: Optional[str] = None) -> Session:
        """End a tracking session."""
        return self.collector.end_session(session, success=success, error=error)
    
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
        """Record a call with prompt breakdown and metadata."""
        return self.collector.record_with_prompt_analysis(**kwargs)
    
    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """Generate session report."""
        return self.collector.get_report(session)
    
    def track(self, operation_type: str, **metadata):
        """Context manager for tracking a session."""
        return self.collector.track(operation_type, metadata)