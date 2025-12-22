"""
AI Agent Observatory - Complete SDK Package
Location: observatory/__init__.py

Comprehensive monitoring and optimization toolkit for AI/LLM applications.

Core Components:
- Observatory: Main tracking interface
- LLMJudge: Quality evaluation with LLM-as-judge
- CacheManager: Response caching with tracking
- ModelRouter: Intelligent model selection
- PromptManager: Template versioning and A/B testing

Usage:
    from observatory import (
        Observatory,
        LLMJudge,
        CacheManager,
        ModelRouter,
        PromptManager,
    )
    
    # Initialize
    obs = Observatory(project_name="My App")
    judge = LLMJudge(observatory=obs, operations={"chat", "analyze"})
    cache = CacheManager(observatory=obs, operations={"search": {"ttl": 3600}})
    router = ModelRouter(observatory=obs, default_model="gpt-4o-mini")
    prompts = PromptManager(observatory=obs)
"""

__version__ = "0.3.0"  # Updated for comprehensive schema

# =============================================================================
# CORE IMPORTS
# =============================================================================

from observatory.collector import (
    Observatory,
    MetricsCollector,
    calculate_cost,
    generate_prompt_hash,
)

from observatory.storage import Storage

# =============================================================================
# MODEL IMPORTS (UPDATED)
# =============================================================================

from observatory.models import (
    # Core models
    Session,
    LLMCall,
    SessionReport,
    
    # Enums
    ModelProvider,
    AgentRole,
    
    # Tracking metadata (existing)
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
    
    # NEW: Additional tracking models
    ModelConfig,
    StreamingMetrics,
    ExperimentMetadata,
    ErrorDetails,
    
    # Breakdown models
    CostBreakdown,
    LatencyBreakdown,
    TokenBreakdown,
    QualityMetrics,
    RoutingMetrics,
    CacheMetrics,
    OptimizationSuggestion,
)

# =============================================================================
# SDK COMPONENT IMPORTS
# =============================================================================

from observatory.judge import (
    LLMJudge,
    create_quality_evaluation,
)

from observatory.cache import (
    CacheManager,
    CacheEntry,
    create_cache_metadata,
    compute_content_hash,
)

from observatory.router import (
    ModelRouter,
    RoutingRule,
    create_routing_decision,
)

from observatory.prompts import (
    PromptManager,
    PromptTemplate,
    create_prompt_metadata,
    create_prompt_breakdown,
    estimate_tokens,
)

from observatory.semantic_cache import (
    SemanticCache,
    SemanticCacheResult,
    SemanticCacheOperationConfig,
    create_semantic_cache_metadata,
)

# =============================================================================
# CONVENIENCE FUNCTION: track_llm_call (UPDATED)
# =============================================================================

from typing import Optional, Dict, List, Any


def track_llm_call(
    observatory: Observatory,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    provider: ModelProvider = ModelProvider.OPENAI,
    
    # Context
    agent_name: str = None,
    agent_role: AgentRole = None,
    operation: str = None,
    
    # Status
    success: bool = True,
    error: str = None,
    
    # Prompt content
    prompt: str = None,
    response_text: str = None,
    prompt_normalized: str = None,
    
    # Separate prompt components
    system_prompt: str = None,
    user_message: str = None,
    messages: List[Dict[str, str]] = None,
    
    # Optimization tracking
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    
    # Prompt analysis
    prompt_breakdown: PromptBreakdown = None,
    prompt_metadata: PromptMetadata = None,
    
    # A/B Testing
    prompt_variant_id: str = None,
    test_dataset_id: str = None,
    
    # NEW: Conversation linking
    conversation_id: str = None,
    turn_number: int = None,
    parent_call_id: str = None,
    user_id: str = None,
    
    # NEW: Model configuration
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    model_config: ModelConfig = None,
    
    # NEW: Token breakdown (top-level)
    system_prompt_tokens: int = None,
    user_message_tokens: int = None,
    chat_history_tokens: int = None,
    conversation_context_tokens: int = None,
    tool_definitions_tokens: int = None,
    
    # NEW: Tool/function calling
    tool_calls_made: List[Dict] = None,
    tool_call_count: int = None,
    tool_execution_time_ms: float = None,
    
    # NEW: Streaming
    time_to_first_token_ms: float = None,
    streaming_metrics: StreamingMetrics = None,
    
    # NEW: Error details
    error_type: str = None,
    error_code: str = None,
    retry_count: int = None,
    error_details: ErrorDetails = None,
    
    # NEW: Cached tokens
    cached_prompt_tokens: int = None,
    cached_token_savings: float = None,
    
    # NEW: Observability
    trace_id: str = None,
    request_id: str = None,
    environment: str = None,
    
    # NEW: Experiment tracking
    experiment_id: str = None,
    control_group: bool = None,
    experiment_metadata: ExperimentMetadata = None,
    
    # Custom metadata
    metadata: dict = None,
) -> LLMCall:
    """
    Convenience function to track an LLM call.
    
    UPDATED: Added comprehensive tracking for conversation linking, model config,
             tool usage, streaming, error details, experiments, and observability.
    
    Args:
        observatory: Observatory instance
        model_name: Name of the model used
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        latency_ms: Response time in milliseconds
        provider: Model provider (OPENAI, AZURE, ANTHROPIC)
        agent_name: Name of the agent/plugin
        agent_role: Role of the agent (analyst, reviewer, writer, etc.)
        operation: Operation name
        success: Whether call succeeded
        error: Error message if failed
        prompt: Combined prompt text
        response_text: Response text
        prompt_normalized: Normalized prompt for cache key generation
        system_prompt: System prompt text (tracked separately)
        user_message: User message text (tracked separately)
        messages: Full conversation history as list of {role, content} dicts
        routing_decision: Routing metadata
        cache_metadata: Cache metadata
        quality_evaluation: Quality evaluation
        prompt_breakdown: Prompt component breakdown
        prompt_metadata: Prompt template metadata
        prompt_variant_id: A/B test variant ID
        test_dataset_id: Test dataset ID for evaluation
        conversation_id: Conversation identifier (NEW)
        turn_number: Turn number in conversation (NEW)
        parent_call_id: Parent call for retries (NEW)
        user_id: User identifier (NEW)
        temperature: Model temperature (NEW)
        max_tokens: Max tokens limit (NEW)
        top_p: Top-p sampling (NEW)
        model_config: Full model configuration (NEW)
        system_prompt_tokens: System prompt token count (NEW)
        user_message_tokens: User message token count (NEW)
        chat_history_tokens: Chat history token count (NEW)
        conversation_context_tokens: Memory state token count (NEW)
        tool_definitions_tokens: Tool schemas token count (NEW)
        tool_calls_made: List of tool calls (NEW)
        tool_call_count: Number of tools called (NEW)
        tool_execution_time_ms: Tool execution time (NEW)
        time_to_first_token_ms: TTFT for streaming (NEW)
        streaming_metrics: Streaming performance data (NEW)
        error_type: Error classification (NEW)
        error_code: Error code from provider (NEW)
        retry_count: Number of retries (NEW)
        error_details: Full error details (NEW)
        cached_prompt_tokens: Tokens served from cache (NEW)
        cached_token_savings: Cost saved via caching (NEW)
        trace_id: OpenTelemetry trace ID (NEW)
        request_id: Provider request ID (NEW)
        environment: Deployment environment (NEW)
        experiment_id: A/B test experiment ID (NEW)
        control_group: Is this control group (NEW)
        experiment_metadata: Full experiment data (NEW)
        metadata: Additional metadata dict
    
    Returns:
        LLMCall object
    """
    return observatory.record_call(
        provider=provider,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        agent_name=agent_name,
        agent_role=agent_role,
        operation=operation,
        success=success,
        error=error,
        prompt=prompt,
        response_text=response_text,
        prompt_normalized=prompt_normalized,
        system_prompt=system_prompt,
        user_message=user_message,
        messages=messages,
        routing_decision=routing_decision,
        cache_metadata=cache_metadata,
        quality_evaluation=quality_evaluation,
        prompt_breakdown=prompt_breakdown,
        prompt_metadata=prompt_metadata,
        prompt_variant_id=prompt_variant_id,
        test_dataset_id=test_dataset_id,
        # NEW parameters
        conversation_id=conversation_id,
        turn_number=turn_number,
        parent_call_id=parent_call_id,
        user_id=user_id,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        model_config=model_config,
        system_prompt_tokens=system_prompt_tokens,
        user_message_tokens=user_message_tokens,
        chat_history_tokens=chat_history_tokens,
        conversation_context_tokens=conversation_context_tokens,
        tool_definitions_tokens=tool_definitions_tokens,
        tool_calls_made=tool_calls_made,
        tool_call_count=tool_call_count,
        tool_execution_time_ms=tool_execution_time_ms,
        time_to_first_token_ms=time_to_first_token_ms,
        streaming_metrics=streaming_metrics,
        error_type=error_type,
        error_code=error_code,
        retry_count=retry_count,
        error_details=error_details,
        cached_prompt_tokens=cached_prompt_tokens,
        cached_token_savings=cached_token_savings,
        trace_id=trace_id,
        request_id=request_id,
        environment=environment,
        experiment_id=experiment_id,
        control_group=control_group,
        experiment_metadata=experiment_metadata,
        metadata=metadata or {},
    )


# =============================================================================
# EXPORTS (UPDATED)
# =============================================================================

__all__ = [
    # Version
    "__version__",
    
    # Core classes
    "Observatory",
    "MetricsCollector",
    "Storage",
    
    # SDK components
    "LLMJudge",
    "CacheManager",
    "CacheEntry",
    "ModelRouter",
    "RoutingRule",
    "PromptManager",
    "PromptTemplate",
    "SemanticCache",
    "SemanticCacheResult",
    "SemanticCacheOperationConfig",
    
    # Models (existing)
    "Session",
    "LLMCall",
    "SessionReport",
    "ModelProvider",
    "AgentRole",
    "RoutingDecision",
    "CacheMetadata",
    "QualityEvaluation",
    "PromptBreakdown",
    "PromptMetadata",
    "CostBreakdown",
    "LatencyBreakdown",
    "TokenBreakdown",
    "QualityMetrics",
    "RoutingMetrics",
    "CacheMetrics",
    "OptimizationSuggestion",
    
    # NEW: Additional models
    "ModelConfig",
    "StreamingMetrics",
    "ExperimentMetadata",
    "ErrorDetails",
    
    # Convenience functions
    "track_llm_call",
    "create_quality_evaluation",
    "create_cache_metadata",
    "create_routing_decision",
    "create_prompt_metadata",
    "create_prompt_breakdown",
    "create_semantic_cache_metadata",
    "estimate_tokens",
    "calculate_cost",
    "generate_prompt_hash",
    "compute_content_hash",
]