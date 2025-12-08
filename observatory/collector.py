"""
Enhanced Metrics Collector
Location: observatory/collector.py

Collects and manages metrics for AI agent sessions with support for:
- Basic metrics (cost, latency, tokens)
- Routing decisions
- Cache metadata
- Quality evaluations
- Prompt breakdown (NEW)
- Enhanced diagnostics fields (NEW)
"""

import os
import uuid
import re
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
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
)
from observatory.storage import Storage


# =============================================================================
# PRICING
# =============================================================================

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
        "mistral-large": (0.002 / 1000, 0.006 / 1000),
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
# HELPER FUNCTIONS FOR PROMPT ANALYSIS
# =============================================================================

def estimate_tokens(text: str) -> int:
    """Rough token count estimate (4 chars ≈ 1 token)."""
    if not text:
        return 0
    return len(text) // 4


def extract_prompt_breakdown(
    messages: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    user_message: Optional[str] = None,
    full_prompt: Optional[str] = None,
) -> PromptBreakdown:
    """
    Extract prompt breakdown from various input formats.
    
    Args:
        messages: List of chat messages [{"role": "user", "content": "..."}]
        system_prompt: Explicit system prompt
        user_message: Explicit user message
        full_prompt: Raw prompt string (will be parsed)
    
    Returns:
        PromptBreakdown with token estimates
    """
    breakdown = PromptBreakdown()
    
    # If we have structured messages
    if messages:
        chat_history = []
        system_content = None
        user_content = None
        
        for msg in messages:
            role = msg.get('role', '').lower()
            content = msg.get('content', '')
            
            if role == 'system':
                system_content = content
            elif role in ('user', 'human'):
                # Last user message is the current one
                user_content = content
                chat_history.append(msg)
            elif role in ('assistant', 'ai'):
                chat_history.append(msg)
        
        # Remove last user message from history (it's the current query)
        if chat_history and chat_history[-1].get('role', '').lower() in ('user', 'human'):
            chat_history = chat_history[:-1]
        
        breakdown.system_prompt = (system_content or system_prompt or '')[:1000]
        breakdown.system_prompt_tokens = estimate_tokens(system_content or system_prompt or '')
        breakdown.chat_history = chat_history if chat_history else None
        breakdown.chat_history_count = len(chat_history)
        breakdown.chat_history_tokens = sum(estimate_tokens(m.get('content', '')) for m in chat_history)
        breakdown.user_message = (user_content or user_message or '')[:500]
        breakdown.user_message_tokens = estimate_tokens(user_content or user_message or '')
    
    # If we only have explicit components
    elif system_prompt or user_message:
        breakdown.system_prompt = (system_prompt or '')[:1000]
        breakdown.system_prompt_tokens = estimate_tokens(system_prompt or '')
        breakdown.user_message = (user_message or '')[:500]
        breakdown.user_message_tokens = estimate_tokens(user_message or '')
    
    # If we only have a raw prompt, try to parse it
    elif full_prompt:
        # Try to detect conversation patterns
        has_history = bool(re.search(r'Human:|User:|Assistant:|AI:', full_prompt, re.I))
        message_count = len(re.findall(r'Human:|User:|Assistant:|AI:', full_prompt, re.I))
        
        total_tokens = estimate_tokens(full_prompt)
        
        if has_history and message_count > 2:
            # Estimate breakdown
            system_pct = 0.25
            history_pct = min(0.60, message_count * 0.08)
            user_pct = 1 - system_pct - history_pct
        else:
            system_pct = 0.30
            history_pct = 0
            user_pct = 0.70
        
        breakdown.system_prompt = full_prompt[:500]
        breakdown.system_prompt_tokens = int(total_tokens * system_pct)
        breakdown.chat_history_count = max(0, message_count - 1)
        breakdown.chat_history_tokens = int(total_tokens * history_pct)
        breakdown.user_message = full_prompt[-300:]
        breakdown.user_message_tokens = int(total_tokens * user_pct)
    
    return breakdown


def compute_content_hash(content: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """
    Compute a stable hash of content, excluding dynamic fields.
    
    Args:
        content: The content to hash
        exclude_patterns: Regex patterns to exclude (timestamps, UUIDs, etc.)
    
    Returns:
        MD5 hash of normalized content
    """
    if not content:
        return ""
    
    normalized = content
    
    # Default patterns to exclude
    default_patterns = [
        r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # ISO timestamps
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',  # UUIDs
        r'session[_-]?id["\']?\s*[:=]\s*["\']?[\w-]+',  # Session IDs
        r'timestamp["\']?\s*[:=]\s*["\']?[\d.]+',  # Numeric timestamps
    ]
    
    patterns = (exclude_patterns or []) + default_patterns
    
    for pattern in patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.I)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    return hashlib.md5(normalized.encode()).hexdigest()


def detect_cache_key_candidates(
    operation: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Detect potential cache key candidates from operation and metadata.
    
    Returns:
        List of field names that could be used in cache key
    """
    candidates = []
    
    # Common ID patterns in metadata
    if metadata:
        id_patterns = ['_id', 'id', 'uuid', 'key', 'hash']
        for key in metadata.keys():
            if any(pattern in key.lower() for pattern in id_patterns):
                candidates.append(key)
    
    # Operation-specific candidates
    if operation:
        op_lower = operation.lower()
        if 'job' in op_lower:
            candidates.extend(['job_id', 'job_url'])
        if 'resume' in op_lower:
            candidates.extend(['resume_id', 'resume_hash'])
        if 'user' in op_lower:
            candidates.extend(['user_id'])
    
    return list(set(candidates))


def detect_dynamic_fields(metadata: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Detect fields that should be excluded from cache keys.
    
    Returns:
        List of field names that are dynamic
    """
    dynamic = []
    
    if metadata:
        dynamic_patterns = ['timestamp', 'time', 'date', 'session', 'request_id', 'trace']
        for key in metadata.keys():
            if any(pattern in key.lower() for pattern in dynamic_patterns):
                dynamic.append(key)
    
    return dynamic


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
        
        # NEW: Structured prompt components
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        
        # Enhanced fields - Routing (None in discovery mode)
        routing_decision: Optional[RoutingDecision] = None,
        
        # Enhanced fields - Caching (None in discovery mode)
        cache_metadata: Optional[CacheMetadata] = None,
        
        # Enhanced fields - Quality (optional)
        quality_evaluation: Optional[QualityEvaluation] = None,
        
        # Enhanced fields - A/B Testing (optional)
        prompt_variant_id: Optional[str] = None,
        test_dataset_id: Optional[str] = None,
        
        # NEW: Pre-built breakdown objects
        prompt_breakdown: Optional[PromptBreakdown] = None,
        prompt_metadata: Optional[PromptMetadata] = None,
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
            messages: Chat messages list (for prompt breakdown)
            system_prompt: Explicit system prompt (for prompt breakdown)
            user_message: Explicit user message (for prompt breakdown)
            routing_decision: Routing decision metadata
            cache_metadata: Cache hit/miss metadata
            quality_evaluation: Quality/judge evaluation
            prompt_variant_id: ID for A/B testing
            test_dataset_id: Test dataset ID for evaluation
            prompt_breakdown: Pre-built PromptBreakdown object
            prompt_metadata: Pre-built PromptMetadata object
        
        Returns:
            LLMCall object
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
                prompt_cost=0,
                completion_cost=0,
                total_cost=0,
                latency_ms=latency_ms,
            )
        
        target_session = session or self.current_session
        if not target_session:
            # Auto-create session if none exists
            target_session = self.start_session(operation_type=operation)
        
        # Calculate costs
        prompt_cost, completion_cost = calculate_cost(
            provider, model_name, prompt_tokens, completion_tokens
        )
        
        # Build prompt breakdown if not provided
        if prompt_breakdown is None and (messages or system_prompt or user_message or prompt):
            prompt_breakdown = extract_prompt_breakdown(
                messages=messages,
                system_prompt=system_prompt,
                user_message=user_message,
                full_prompt=prompt,
            )
            # Add response text to breakdown
            if response_text and prompt_breakdown:
                prompt_breakdown.response_text = response_text[:1000]
        
        # Enhance cache metadata with auto-detected fields
        if cache_metadata is None and metadata:
            # Auto-detect cache key candidates
            key_candidates = detect_cache_key_candidates(operation, metadata)
            dynamic_fields = detect_dynamic_fields(metadata)
            
            if key_candidates or dynamic_fields:
                cache_metadata = CacheMetadata(
                    cache_hit=False,
                    cache_key_candidates=key_candidates if key_candidates else None,
                    dynamic_fields=dynamic_fields if dynamic_fields else None,
                    content_hash=compute_content_hash(prompt) if prompt else None,
                )
        
        # Create LLM call record
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
            total_tokens=prompt_tokens + completion_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            latency_ms=latency_ms,
            agent_name=agent_name,
            agent_role=agent_role,
            operation=operation or target_session.operation_type,
            success=success,
            error=error,
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_variant_id=prompt_variant_id,
            test_dataset_id=test_dataset_id,
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            metadata=metadata or {},
        )
        
        # Update session aggregates
        target_session.total_llm_calls += 1
        target_session.total_tokens += llm_call.total_tokens
        target_session.total_cost += llm_call.total_cost
        target_session.total_latency_ms += llm_call.latency_ms
        
        if routing_decision:
            target_session.total_routing_decisions += 1
            if routing_decision.estimated_cost_savings:
                target_session.routing_cost_savings += routing_decision.estimated_cost_savings
        
        if cache_metadata:
            if cache_metadata.cache_hit:
                target_session.total_cache_hits += 1
            else:
                target_session.total_cache_misses += 1
        
        if quality_evaluation:
            if quality_evaluation.hallucination_flag:
                target_session.total_hallucinations += 1
            if quality_evaluation.factual_error:
                target_session.total_errors += 1
        
        if not success:
            target_session.total_errors += 1
        
        target_session.llm_calls.append(llm_call)
        
        # Save to storage
        self.storage.save_llm_call(llm_call)
        self.storage.update_session(target_session)
        
        return llm_call

    def record_with_breakdown(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with prompt breakdown.
        
        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            system_prompt: System prompt if separate from messages
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        return self.record_llm_call(
            messages=messages,
            system_prompt=system_prompt,
            **kwargs
        )

    def record_with_routing(
        self,
        chosen_model: str,
        alternative_models: Optional[List[str]] = None,
        reasoning: str = "",
        complexity_score: Optional[float] = None,
        estimated_cost_savings: Optional[float] = None,
        routing_strategy: Optional[str] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with routing decision.
        
        Args:
            chosen_model: Model that was selected
            alternative_models: Other models considered
            reasoning: Why this model was chosen
            complexity_score: Query complexity (0-1)
            estimated_cost_savings: Estimated savings from routing
            routing_strategy: Strategy used (complexity, cost, latency)
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
        cache_key_candidates: Optional[List[str]] = None,
        content_hash: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with cache metadata.
        
        Args:
            cache_hit: Whether this was a cache hit
            cache_key: Cache key used
            cache_cluster_id: Cluster ID for prompt clustering
            similarity_score: Similarity score (0-1)
            cache_key_candidates: IDs that form the cache key
            content_hash: Hash of stable content
            ttl_seconds: Time-to-live for cache entry
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
        factual_error: bool = False,
        error_category: Optional[str] = None,
        reasoning: Optional[str] = None,
        failure_reason: Optional[str] = None,
        improvement_suggestion: Optional[str] = None,
        hallucination_details: Optional[str] = None,
        **kwargs
    ) -> LLMCall:
        """
        Convenience method for recording a call with quality evaluation.
        
        Args:
            judge_score: Judge score (0-10)
            hallucination_flag: Whether hallucination detected
            factual_error: Whether factual error detected
            error_category: Category of error if any
            reasoning: Judge's reasoning
            failure_reason: Categorized failure reason
            improvement_suggestion: Suggested fix
            hallucination_details: What was hallucinated
            **kwargs: Other arguments for record_llm_call
        
        Returns:
            LLMCall object
        """
        quality_evaluation = QualityEvaluation(
            judge_score=judge_score,
            hallucination_flag=hallucination_flag,
            factual_error=factual_error,
            error_category=error_category,
            reasoning=reasoning,
            failure_reason=failure_reason,
            improvement_suggestion=improvement_suggestion,
            hallucination_details=hallucination_details,
        )
        
        return self.record_llm_call(
            quality_evaluation=quality_evaluation,
            **kwargs
        )

    def get_report(self, session: Optional[Session] = None) -> SessionReport:
        """Generate a basic report for a session."""
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
                collector.record_llm_call(...)
        """
        session = self.start_session(operation_type, metadata)
        try:
            yield session
            self.end_session(session, success=True)
        except Exception as e:
            self.end_session(session, success=False, error=str(e))
            raise


# =============================================================================
# OBSERVATORY INTERFACE
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
    
    def record_with_breakdown(self, **kwargs) -> LLMCall:
        """Record a call with prompt breakdown."""
        return self.collector.record_with_breakdown(**kwargs)
    
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