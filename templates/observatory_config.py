"""
Observatory Configuration Template
Location: your-project/observatory_config.py

This is the ONLY file needed in your application to use Observatory.
All logic lives in the observatory package - this just configures it.

SETUP:
1. Copy this file to your project root as observatory_config.py
2. Update PROJECT_NAME and operations for your use case
3. Configure routing rules, cache operations, and judge criteria
4. Import and use: from observatory_config import obs, track_call

Usage:
    from observatory_config import obs, judge, cache, router, prompts, track_llm_call
    
    # In your code
    quality = await judge.maybe_evaluate(operation, prompt, response, client)
    track_llm_call(model, tokens, latency, operation=op, quality_evaluation=quality)

UPDATED: Now supports all 139 fields including conversation linking, model config,
         tool tracking, streaming, error details, experiments, and observability.
"""

import os
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# IMPORT FROM OBSERVATORY SDK
# =============================================================================

from observatory import (
    # Core
    Observatory,
    ModelProvider,
    AgentRole,
    
    # SDK Components
    LLMJudge,
    CacheManager,
    ModelRouter,
    PromptManager,
    
    # Convenience functions (rename to avoid conflict with our wrapper)
    track_llm_call as _sdk_track_llm_call,
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation,
    create_prompt_metadata,
    create_prompt_breakdown,
    estimate_tokens,
    
    # Models for type hints (existing)
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
    
    # NEW: Additional models for complete schema
    ModelConfig,
    StreamingMetrics,
    ExperimentMetadata,
    ErrorDetails,
)

# =============================================================================
# PHASE CONFIGURATION
# =============================================================================

# Set via environment variable or .env file:
#   OBSERVATORY_PHASE=baseline   (Phase 1: Track only, no optimizations)
#   OBSERVATORY_PHASE=optimized  (Phase 2: Routing, caching, quality enabled)
#
# Or run with: OBSERVATORY_PHASE=optimized python your_app.py

CURRENT_PHASE = os.getenv("OBSERVATORY_PHASE", "baseline")

if CURRENT_PHASE not in ("baseline", "optimized"):
    print(f"⚠️ Invalid OBSERVATORY_PHASE '{CURRENT_PHASE}', defaulting to 'baseline'")
    CURRENT_PHASE = "baseline"

# =============================================================================
# PROJECT CONFIGURATION - CUSTOMIZE THESE
# =============================================================================

# TODO: Update for your project
PROJECT_NAME = "My AI Project"

# Model configuration - update for your provider
# Options: ModelProvider.OPENAI, ModelProvider.AZURE, ModelProvider.ANTHROPIC
DEFAULT_PROVIDER = ModelProvider.AZURE
DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

# For OpenAI:
# DEFAULT_PROVIDER = ModelProvider.OPENAI
# DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# For Anthropic:
# DEFAULT_PROVIDER = ModelProvider.ANTHROPIC
# DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet")

# Database path - adjust to your Observatory location
OBSERVATORY_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "ai-agent-observatory", "observatory.db")
)
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"

print(f"📦 Observatory Config: {PROJECT_NAME}")
print(f"   Database: {OBSERVATORY_DB_PATH}")
print(f"   Model: {DEFAULT_MODEL}")
print(f"   Phase: {CURRENT_PHASE}")

# =============================================================================
# INITIALIZE OBSERVATORY
# =============================================================================

obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=True,
)

# =============================================================================
# CONFIGURE LLM JUDGE - CUSTOMIZE FOR YOUR DOMAIN
# =============================================================================

judge = LLMJudge(
    observatory=obs,
    
    # TODO: Operations worth evaluating (high-value outputs)
    operations={
        # "generate_report",
        # "analyze_data",
        # "chat_response",
        # "summarize_document",
    },
    
    # TODO: Operations to skip (low-value or simple)
    skip_operations={
        # "format_output",
        # "parse_input",
        # "validate_data",
    },
    
    # Evaluate X% of judge-worthy calls (0.0 to 1.0)
    sample_rate=0.5,
    
    # TODO: Domain-specific criteria (must sum to 1.0)
    criteria={
        "relevance": 0.25,      # How relevant is the response?
        "accuracy": 0.25,       # Is the information correct?
        "helpfulness": 0.25,    # Does it help the user?
        "clarity": 0.15,        # Is it clear and well-structured?
        "completeness": 0.10,   # Does it fully address the query?
    },
    
    # TODO: Describe your application domain
    domain_context="AI assistant responses",
    
    # Model for judging (can be same as main or different)
    judge_model=DEFAULT_MODEL,
    
    # Track judge calls in Observatory
    track_judge_calls=True,
)

# =============================================================================
# CONFIGURE CACHE MANAGER - CUSTOMIZE FOR YOUR OPERATIONS
# =============================================================================

cache = CacheManager(
    observatory=obs,
    
    # TODO: Operations to cache with TTL settings
    # Format: "operation_name": {"ttl": seconds, "normalize": bool, "cluster_id": "group"}
    operations={
        # "search_query": {"ttl": 3600, "normalize": True, "cluster_id": "searches"},
        # "fetch_data": {"ttl": 300, "normalize": False, "cluster_id": "data_fetches"},
        # "get_details": {"ttl": 7200, "normalize": False, "cluster_id": "details"},
    },
    
    # Defaults
    default_ttl=3600,       # 1 hour default
    max_entries=1000,       # Max cache size
    normalize_prompts=True, # Normalize for better cache hits
)

# =============================================================================
# CONFIGURE MODEL ROUTER - CUSTOMIZE ROUTING RULES
# =============================================================================

router = ModelRouter(
    observatory=obs,
    default_model=DEFAULT_MODEL,
    fallback_model="gpt-4o-mini",
    
    # TODO: Routing rules (evaluated in order, first match wins)
    # Available conditions: operations, agents, min_complexity, max_complexity, min_tokens, max_tokens
    rules=[
        # Example: Simple operations → cheap model
        # {
        #     "name": "simple_tasks",
        #     "operations": ["format", "parse", "validate"],
        #     "model": "gpt-4o-mini",
        #     "reason": "Simple task - cheap model sufficient",
        # },
        
        # Example: Complex analysis → premium model
        # {
        #     "name": "complex_analysis",
        #     "operations": ["analyze", "synthesize", "generate_report"],
        #     "model": "gpt-4o",
        #     "reason": "Complex analysis requires premium model",
        # },
        
        # Example: High complexity score → premium model
        # {
        #     "name": "high_complexity",
        #     "min_complexity": 0.7,
        #     "model": "gpt-4o",
        #     "reason": "High complexity score detected",
        # },
        
        # Example: Short requests → cheap model
        # {
        #     "name": "short_requests",
        #     "max_tokens": 500,
        #     "model": "gpt-4o-mini",
        #     "reason": "Short request - cheap model sufficient",
        # },
        
        # Example: Specific agent → specific model
        # {
        #     "name": "analyst_agent",
        #     "agents": ["DataAnalyst", "ResearchAgent"],
        #     "model": "gpt-4o",
        #     "reason": "Analyst agents need premium model",
        # },
    ],
)

# =============================================================================
# CONFIGURE PROMPT MANAGER (A/B TESTING)
# =============================================================================

prompts = PromptManager(observatory=obs)

# Example: Register a prompt template with A/B test variants
# prompts.register(
#     template_id="system_prompt_v1",
#     version="1.0.0",
#     content=YOUR_SYSTEM_PROMPT,
#     variants={
#         "control": YOUR_SYSTEM_PROMPT,
#         "concise": CONCISE_VARIANT,
#         "detailed": DETAILED_VARIANT,
#     },
#     experiment_id="system_prompt_test",
#     weights={"control": 0.5, "concise": 0.25, "detailed": 0.25},
#     description="Testing different system prompt styles",
# )

# =============================================================================
# WRAPPER: track_llm_call (matches SDK naming)
# UPDATED: Now supports all 139 fields
# =============================================================================

def track_llm_call(
    # =========================================================================
    # CORE METRICS (Tier 1 - Always include)
    # =========================================================================
    model_name: str = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: float = 0,
    
    # Context
    agent_name: str = None,
    agent_role: str = None,
    operation: str = None,
    
    # Status
    success: bool = True,
    error: str = None,
    
    # =========================================================================
    # PROMPT CONTENT (Tier 2)
    # =========================================================================
    prompt: str = None,
    response_text: str = None,
    prompt_normalized: str = None,
    
    # Separate prompt components
    system_prompt: str = None,
    user_message: str = None,
    messages: List[Dict[str, str]] = None,
    
    # =========================================================================
    # OPTIMIZATION TRACKING (Tier 2-3)
    # =========================================================================
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    
    # Prompt analysis
    prompt_breakdown: PromptBreakdown = None,
    prompt_metadata: PromptMetadata = None,
    
    # A/B Testing
    prompt_variant_id: str = None,
    test_dataset_id: str = None,
    
    # =========================================================================
    # NEW: CONVERSATION LINKING
    # =========================================================================
    conversation_id: str = None,
    turn_number: int = None,
    parent_call_id: str = None,
    user_id: str = None,
    
    # =========================================================================
    # NEW: MODEL CONFIGURATION
    # =========================================================================
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    llm_config: ModelConfig = None,
    
    # =========================================================================
    # NEW: TOKEN BREAKDOWN (Top-level for query performance)
    # =========================================================================
    system_prompt_tokens: int = None,
    user_message_tokens: int = None,
    chat_history_tokens: int = None,
    conversation_context_tokens: int = None,
    tool_definitions_tokens: int = None,
    
    # =========================================================================
    # NEW: TOOL/FUNCTION CALLING
    # =========================================================================
    tool_calls_made: List[Dict] = None,
    tool_call_count: int = None,
    tool_execution_time_ms: float = None,
    
    # =========================================================================
    # NEW: STREAMING
    # =========================================================================
    time_to_first_token_ms: float = None,
    streaming_metrics: StreamingMetrics = None,
    
    # =========================================================================
    # NEW: ERROR DETAILS
    # =========================================================================
    error_type: str = None,
    error_code: str = None,
    retry_count: int = None,
    error_details: ErrorDetails = None,
    
    # =========================================================================
    # NEW: CACHED TOKENS
    # =========================================================================
    cached_prompt_tokens: int = None,
    cached_token_savings: float = None,
    
    # =========================================================================
    # NEW: OBSERVABILITY
    # =========================================================================
    trace_id: str = None,
    request_id: str = None,
    environment: str = None,
    
    # =========================================================================
    # NEW: EXPERIMENT TRACKING
    # =========================================================================
    experiment_id: str = None,
    control_group: bool = None,
    experiment_metadata: ExperimentMetadata = None,
    
    # =========================================================================
    # CUSTOM METADATA
    # =========================================================================
    metadata: dict = None,
):
    """
    Track an LLM call with auto-filled defaults for your application.
    
    UPDATED: Now supports all 139 fields for complete observability.
    
    Uses default model and provider from config.
    Passes all parameters through to SDK's track_llm_call.
    
    Args:
        # CORE METRICS (Tier 1 - Always include)
        model_name: Model used (defaults to DEFAULT_MODEL)
        prompt_tokens: Input token count
        completion_tokens: Output token count
        latency_ms: Response time in ms
        agent_name: Name of agent/plugin
        agent_role: Role (analyst, reviewer, writer, retriever, planner, formatter, fixer, orchestrator, custom)
        operation: Operation name
        success: Whether call succeeded
        error: Error message if failed
        
        # PROMPT CONTENT (Tier 2)
        prompt: Combined prompt text
        response_text: Response from model
        prompt_normalized: Normalized prompt for cache key generation
        system_prompt: System prompt (tracked separately)
        user_message: User message (tracked separately)
        messages: Full conversation as [{role, content}, ...]
        
        # OPTIMIZATION TRACKING (Tier 2-3)
        routing_decision: Routing metadata
        cache_metadata: Cache metadata
        quality_evaluation: Quality evaluation
        prompt_breakdown: Prompt component breakdown
        prompt_metadata: Prompt template metadata
        prompt_variant_id: A/B test variant ID
        test_dataset_id: Test dataset ID
        
        # NEW: CONVERSATION LINKING
        conversation_id: Conversation identifier (links multi-turn chats)
        turn_number: Turn number in conversation (1, 2, 3...)
        parent_call_id: Parent call ID (for retries/branches)
        user_id: User identifier
        
        # NEW: MODEL CONFIGURATION
        temperature: Model temperature setting
        max_tokens: Max tokens limit
        top_p: Top-p sampling parameter
        llm_config: Full ModelConfig object with all settings
        
        # NEW: TOKEN BREAKDOWN (Top-level for fast queries)
        system_prompt_tokens: System prompt token count
        user_message_tokens: User message token count
        chat_history_tokens: Chat history token count
        conversation_context_tokens: Conversation memory/state tokens
        tool_definitions_tokens: Function calling schema tokens
        
        # NEW: TOOL/FUNCTION CALLING
        tool_calls_made: List of tool calls with details
        tool_call_count: Number of tools called
        tool_execution_time_ms: Total tool execution time
        
        # NEW: STREAMING
        time_to_first_token_ms: Time to first token (TTFT)
        streaming_metrics: Full StreamingMetrics object
        
        # NEW: ERROR DETAILS
        error_type: Error classification (RATE_LIMIT, TIMEOUT, etc.)
        error_code: Provider error code (429, 500, etc.)
        retry_count: Number of retries attempted
        error_details: Full ErrorDetails object
        
        # NEW: CACHED TOKENS
        cached_prompt_tokens: Tokens served from cache
        cached_token_savings: Cost saved via caching
        
        # NEW: OBSERVABILITY
        trace_id: OpenTelemetry trace ID
        request_id: Provider request ID
        environment: Deployment environment (dev/staging/prod)
        
        # NEW: EXPERIMENT TRACKING
        experiment_id: A/B test experiment ID
        control_group: Is this control group?
        experiment_metadata: Full ExperimentMetadata object
        
        # CUSTOM METADATA
        metadata: Additional metadata dict
    
    Returns:
        LLMCall object
    """
    # Convert string agent_role to AgentRole enum if provided
    role_enum = None
    if agent_role:
        try:
            role_enum = AgentRole(agent_role)
        except ValueError:
            # If not a valid enum value, store in metadata instead
            if metadata is None:
                metadata = {}
            metadata['agent_role_str'] = agent_role
    
    return _sdk_track_llm_call(
        observatory=obs,
        model_name=model_name or DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=max(latency_ms, 0.001),
        provider=DEFAULT_PROVIDER,
        agent_name=agent_name,
        agent_role=role_enum,
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
        
        # NEW: Conversation linking
        conversation_id=conversation_id,
        turn_number=turn_number,
        parent_call_id=parent_call_id,
        user_id=user_id,
        
        # NEW: Model configuration
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        llm_config=llm_config,
        
        # NEW: Token breakdown
        system_prompt_tokens=system_prompt_tokens,
        user_message_tokens=user_message_tokens,
        chat_history_tokens=chat_history_tokens,
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
        
        # NEW: Experiment tracking
        experiment_id=experiment_id,
        control_group=control_group,
        experiment_metadata=experiment_metadata,
        
        metadata=metadata,
    )



# =============================================================================
# SESSION HELPERS
# =============================================================================

def start_session(operation_type: str = None, **metadata):
    """Start a tracking session."""
    return obs.start_session(operation_type, **metadata)


def end_session(session, success: bool = True, error: str = None):
    """End a tracking session."""
    return obs.end_session(session, success=success, error=error)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Configured instances
    'obs',
    'judge',
    'cache',
    'router',
    'prompts',
    
    # Config values
    'PROJECT_NAME',
    'DEFAULT_MODEL',
    'DEFAULT_PROVIDER',
    'CURRENT_PHASE',
    
    # Functions (SDK-matching names)
    'track_llm_call',
    'start_session',
    'end_session',
    
    # Re-exported for convenience
    'create_routing_decision',
    'create_cache_metadata',
    'create_quality_evaluation',
    'create_prompt_metadata',
    'create_prompt_breakdown',
    'estimate_tokens',
    
    # Types for type hints (existing)
    'RoutingDecision',
    'CacheMetadata',
    'QualityEvaluation',
    'PromptBreakdown',
    'PromptMetadata',
    'AgentRole',
    
    # NEW: Additional types
    'ModelConfig',
    'StreamingMetrics',
    'ExperimentMetadata',
    'ErrorDetails',
]