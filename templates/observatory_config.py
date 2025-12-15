"""
Observatory Configuration Template
Location: <your-project>/observatory_config.py

This is the ONLY file needed in your application to use Observatory.
All logic lives in the observatory package - this just configures it.

SETUP:
1. Copy this file to your project root
2. Customize the sections marked with # 🔧 CUSTOMIZE
3. Import and use: from observatory_config import obs, track_llm_call

Usage:
    from observatory_config import obs, judge, cache, router, prompts, track_llm_call
    
    # In your code
    quality = await judge.maybe_evaluate(operation, prompt, response, client)
    track_llm_call(
        model_name=model,
        prompt_tokens=tokens,
        completion_tokens=completion,
        latency_ms=latency,
        operation=operation,
        agent_name="MyAgent",
        system_prompt=sys_prompt,
        user_message=user_msg,
        quality_evaluation=quality
    )

FEATURES:
- ✅ Tracks all 85 columns (58 original + 27 extracted for fast analytics)
- ✅ Auto-creates prompt_breakdown for Stories 2 & 6
- ✅ Auto-cleans metadata (removes non-serializable objects)
- ✅ Supports baseline and optimized phases
- ✅ Configurable judge, cache, router, prompts
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
    
    # Models for type hints
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
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
# 🔧 CUSTOMIZE: PROJECT CONFIGURATION
# =============================================================================

PROJECT_NAME = "My AI Project"  # 🔧 Change this to your project name

# 🔧 Model configuration - Choose your provider
DEFAULT_PROVIDER = ModelProvider.OPENAI  # Options: OPENAI, AZURE, ANTHROPIC
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 🔧 Your default model

# 🔧 Database path - Adjust to your Observatory location
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
# 🔧 CUSTOMIZE: CONFIGURE LLM JUDGE
# =============================================================================

judge = LLMJudge(
    observatory=obs,
    
    # 🔧 Operations worth evaluating (high-value outputs)
    operations={
        "generate_response",
        "analyze_document",
        "create_summary",
        # Add your important operations here
    },
    
    # 🔧 Operations to skip (low-value or simple)
    skip_operations={
        "simple_query",
        "list_items",
        "get_details",
        # Add operations to skip evaluation
    },
    
    # Evaluate 50% of judge-worthy calls
    sample_rate=0.5,
    
    # 🔧 Domain-specific criteria (must sum to 1.0)
    criteria={
        "accuracy": 0.30,      # Is the information correct?
        "relevance": 0.25,     # Is it relevant to the query?
        "completeness": 0.20,  # Does it fully answer the question?
        "clarity": 0.15,       # Is it clear and well-structured?
        "helpfulness": 0.10,   # Is it actionable/useful?
    },
    
    # 🔧 Your domain context
    domain_context="general AI assistance",  # e.g., "customer support", "code generation", etc.
    
    # Model for judging (same as main)
    judge_model=DEFAULT_MODEL,
    
    # Track judge calls in Observatory
    track_judge_calls=True,
)

# =============================================================================
# 🔧 CUSTOMIZE: CONFIGURE CACHE MANAGER
# =============================================================================

cache = CacheManager(
    observatory=obs,
    
    # 🔧 Operations to cache with TTL settings
    operations={
        # Example: "operation_name": {"ttl": seconds, "normalize": bool, "cluster_id": "group_name"}
        "search_items": {"ttl": 3600, "normalize": True, "cluster_id": "searches"},
        "get_details": {"ttl": 1800, "normalize": False, "cluster_id": "details"},
        "generate_report": {"ttl": 3600, "normalize": True, "cluster_id": "reports"},
        # Add your operations here
    },
    
    # Defaults
    default_ttl=3600,       # 1 hour default
    max_entries=1000,       # Max cache size
    normalize_prompts=True, # Normalize for better cache hits
)

# =============================================================================
# 🔧 CUSTOMIZE: CONFIGURE MODEL ROUTER
# =============================================================================

router = ModelRouter(
    observatory=obs,
    default_model=DEFAULT_MODEL,
    fallback_model="gpt-4o-mini",  # 🔧 Fallback if routing fails
    
    # 🔧 Routing rules (evaluated in order)
    rules=[
        # Example: Simple operations → cheap model
        {
            "name": "simple_operations",
            "operations": ["list_items", "get_details", "simple_query"],
            "model": "gpt-4o-mini",
            "reason": "Simple retrieval - cheap model sufficient",
        },
        
        # Example: Complex analysis → premium model
        {
            "name": "complex_analysis",
            "operations": ["deep_analysis", "generate_report", "complex_reasoning"],
            "model": "gpt-4o",
            "reason": "Complex reasoning requires premium model",
        },
        
        # Example: High complexity → premium model
        {
            "name": "high_complexity",
            "min_complexity": 0.7,
            "model": "gpt-4o",
            "reason": "High complexity score detected",
        },
        
        # Example: Short requests → cheap model
        {
            "name": "short_requests",
            "max_tokens": 500,
            "model": "gpt-4o-mini",
            "reason": "Short request - cheap model sufficient",
        },
        
        # Add your routing rules here
    ],
)

# =============================================================================
# CONFIGURE PROMPT MANAGER (A/B TESTING)
# =============================================================================

prompts = PromptManager(observatory=obs)

# Example: Register system prompt with variants
# prompts.register(
#     template_id="main_system_prompt",
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
# HELPER FUNCTIONS: Token Breakdown & Model Parameters Extraction
# =============================================================================

def extract_token_breakdown_from_messages(
    messages: List[Dict] = None,
    system_prompt: str = None,
    user_message: str = None,
    chat_history: Any = None,
    conversation_memory: Any = None,
) -> Dict[str, int]:
    """
    Extract token breakdown from various message formats.
    
    Auto-populates system_prompt_tokens, user_message_tokens, chat_history_tokens,
    and conversation_context_tokens for comprehensive token tracking.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: Explicit system prompt text
        user_message: Explicit user message text
        chat_history: Chat history object (Semantic Kernel, LangChain, etc.)
        conversation_memory: Custom conversation memory object
    
    Returns:
        Dict with token counts for each component
    """
    breakdown = {
        'system_prompt_tokens': 0,
        'user_message_tokens': 0,
        'chat_history_tokens': 0,
        'conversation_context_tokens': 0,
    }
    
    # Extract from explicit parameters
    if system_prompt:
        breakdown['system_prompt_tokens'] = estimate_tokens(system_prompt)
    
    if user_message:
        breakdown['user_message_tokens'] = estimate_tokens(user_message)
    
    # Extract from messages array
    if messages:
        for msg in messages:
            role = msg.get('role', '').lower()
            content = msg.get('content', '')
            tokens = estimate_tokens(content)
            
            if role == 'system':
                breakdown['system_prompt_tokens'] += tokens
            elif role == 'user':
                breakdown['user_message_tokens'] += tokens
            elif role in ('assistant', 'tool'):
                breakdown['chat_history_tokens'] += tokens
    
    # Extract from chat_history object (Semantic Kernel pattern)
    if chat_history and hasattr(chat_history, 'messages'):
        for msg in chat_history.messages:
            content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            tokens = estimate_tokens(content)
            role = getattr(msg, 'role', 'user').lower()
            
            if role == 'system':
                breakdown['system_prompt_tokens'] += tokens
            elif role in ('assistant', 'tool'):
                breakdown['chat_history_tokens'] += tokens
    
    # Extract from conversation_memory object (custom pattern)
    if conversation_memory:
        if hasattr(conversation_memory, 'chat_history'):
            hist = conversation_memory.chat_history
            if hasattr(hist, 'messages'):
                for msg in hist.messages:
                    content = str(msg.content) if hasattr(msg, 'content') else str(msg)
                    tokens = estimate_tokens(content)
                    breakdown['chat_history_tokens'] += tokens
        
        # Add conversation context tokens (summaries, memory, etc.)
        if hasattr(conversation_memory, 'context'):
            ctx = conversation_memory.context
            if ctx:
                breakdown['conversation_context_tokens'] = estimate_tokens(str(ctx))
    
    return breakdown


def extract_model_parameters(
    execution_settings: Any = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
) -> Dict[str, Any]:
    """
    Extract model parameters from execution settings or use provided values.
    
    Args:
        execution_settings: Framework-specific settings object (Semantic Kernel, LangChain, etc.)
        temperature: Override temperature
        max_tokens: Override max_tokens
        top_p: Override top_p
    
    Returns:
        Dict with model parameters
    """
    params = {
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': top_p,
    }
    
    # Extract from execution_settings if available
    if execution_settings:
        if hasattr(execution_settings, 'temperature'):
            params['temperature'] = params['temperature'] or execution_settings.temperature
        if hasattr(execution_settings, 'max_tokens'):
            params['max_tokens'] = params['max_tokens'] or execution_settings.max_tokens
        if hasattr(execution_settings, 'top_p'):
            params['top_p'] = params['top_p'] or execution_settings.top_p
    
    return params


# =============================================================================
# SESSION MANAGEMENT HELPERS
# =============================================================================

def start_session(operation_type: str = "default", metadata: dict = None):
    """Start a new Observatory session."""
    return obs.start_session(operation_type=operation_type, metadata=metadata)

def end_session(session, success: bool = True, error: str = None):
    """End an Observatory session."""
    return obs.end_session(session, success=success, error=error)


# =============================================================================
# MAIN TRACKING FUNCTION (with 27-column support)
# =============================================================================

def track_llm_call(
    # TIER 1 - Core metrics (always include)
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    model_name: str = None,
    agent_name: str = None,
    agent_role: str = None,
    operation: str = None,
    
    # Status
    success: bool = True,
    error: str = None,
    
    # TIER 2 - Prompt content
    prompt: str = None,
    response_text: str = None,
    prompt_normalized: str = None,
    system_prompt: str = None,
    user_message: str = None,
    messages: List[Dict[str, str]] = None,
    
    # TIER 2 - Optimization tracking
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    prompt_breakdown: PromptBreakdown = None,
    prompt_metadata: PromptMetadata = None,
    
    # TIER 3 - A/B Testing
    prompt_variant_id: str = None,
    test_dataset_id: str = None,
    
    # CONVERSATION LINKING
    conversation_id: str = None,
    turn_number: int = None,
    parent_call_id: str = None,
    user_id: str = None,
    
    # MODEL CONFIGURATION
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    model_config: ModelConfig = None,
    
    # TOKEN BREAKDOWN (Top-level for fast queries)
    system_prompt_tokens: int = None,
    user_message_tokens: int = None,
    chat_history_tokens: int = None,
    conversation_context_tokens: int = None,
    tool_definitions_tokens: int = None,
    
    # TOOL/FUNCTION CALLING
    tool_calls_made: List[Dict[str, Any]] = None,
    tool_call_count: int = None,
    tool_execution_time_ms: float = None,
    
    # STREAMING
    time_to_first_token_ms: float = None,
    streaming_metrics: StreamingMetrics = None,
    
    # ERROR DETAILS
    error_type: str = None,
    error_code: str = None,
    retry_count: int = None,
    error_details: ErrorDetails = None,
    
    # CACHED TOKENS
    cached_prompt_tokens: int = None,
    cached_token_savings: float = None,
    
    # OBSERVABILITY
    trace_id: str = None,
    request_id: str = None,
    environment: str = None,
    
    # EXPERIMENT TRACKING
    experiment_id: str = None,
    control_group: bool = None,
    experiment_metadata: ExperimentMetadata = None,
    
    # CUSTOM METADATA
    metadata: dict = None,
):
    """
    Track an LLM call with auto-filled defaults.
    
    Supports all 85 columns including 27 new extracted columns for fast analytics.
    
    Key Features:
    - Auto-creates prompt_breakdown for Stories 2 & 6 (system_prompt, user_message extraction)
    - Auto-extracts token breakdown from messages
    - Auto-extracts model parameters from execution_settings
    - Auto-cleans metadata (removes non-serializable objects)
    
    Args:
        # TIER 1 - Core (always include)
        prompt_tokens: Input token count
        completion_tokens: Output token count
        latency_ms: Response time in ms
        model_name: Model used (defaults to DEFAULT_MODEL)
        agent_name: Name of agent/plugin
        agent_role: Role (analyst, reviewer, writer, retriever, etc.)
        operation: Operation name
        success: Whether call succeeded
        error: Error message if failed
        
        # PROMPT CONTENT (Tier 2)
        prompt: Combined prompt text
        response_text: Response from model
        prompt_normalized: Normalized prompt for cache key generation
        system_prompt: System prompt (CRITICAL for Stories 2 & 6)
        user_message: User message (CRITICAL for Stories 2 & 6)
        messages: Full conversation as [{role, content}, ...]
        
        # OPTIMIZATION TRACKING (Tier 2-3)
        routing_decision: Routing metadata
        cache_metadata: Cache metadata
        quality_evaluation: Quality evaluation
        prompt_breakdown: Prompt component breakdown
        prompt_metadata: Prompt template metadata
        prompt_variant_id: A/B test variant ID
        test_dataset_id: Test dataset ID
        
        # CONVERSATION LINKING
        conversation_id: Conversation identifier (links multi-turn chats)
        turn_number: Turn number in conversation (1, 2, 3...)
        parent_call_id: Parent call ID (for retries/branches)
        user_id: User identifier
        
        # MODEL CONFIGURATION
        temperature: Model temperature setting
        max_tokens: Max tokens limit
        top_p: Top-p sampling parameter
        model_config: Full ModelConfig object
        
        # TOKEN BREAKDOWN (Top-level for fast queries)
        system_prompt_tokens: System prompt token count
        user_message_tokens: User message token count
        chat_history_tokens: Chat history token count
        conversation_context_tokens: Conversation memory tokens
        tool_definitions_tokens: Function schema tokens
        
        # TOOL/FUNCTION CALLING
        tool_calls_made: List of tool calls
        tool_call_count: Number of tools called
        tool_execution_time_ms: Tool execution time
        
        # STREAMING
        time_to_first_token_ms: TTFT latency
        streaming_metrics: Full streaming details
        
        # ERROR DETAILS
        error_type: Error classification (RATE_LIMIT, TIMEOUT, etc.)
        error_code: Provider error code (429, 500, etc.)
        retry_count: Retry attempts
        error_details: Full error context
        
        # CACHED TOKENS
        cached_prompt_tokens: Tokens from cache
        cached_token_savings: Cost saved
        
        # OBSERVABILITY
        trace_id: OpenTelemetry trace ID
        request_id: Provider request ID
        environment: Deployment environment (dev/staging/prod)
        
        # EXPERIMENT TRACKING
        experiment_id: A/B test ID
        control_group: Control vs treatment
        experiment_metadata: Full experiment details
        
        # CUSTOM METADATA
        metadata: Additional metadata dict
    
    Returns:
        LLMCall object
    """
    # ⭐ AUTO-EXTRACT: Token breakdown and model parameters
    # This ensures ALL calls get comprehensive tracking automatically
    
    # Extract token breakdown if not explicitly provided
    if not system_prompt_tokens and not user_message_tokens and not chat_history_tokens:
        token_breakdown = extract_token_breakdown_from_messages(
            messages=messages,
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=None,
            conversation_memory=metadata.get('conversation_memory') if metadata else None
        )
        
        # Use extracted values
        system_prompt_tokens = system_prompt_tokens or token_breakdown['system_prompt_tokens']
        user_message_tokens = user_message_tokens or token_breakdown['user_message_tokens']
        chat_history_tokens = chat_history_tokens or token_breakdown['chat_history_tokens']
        conversation_context_tokens = conversation_context_tokens or token_breakdown['conversation_context_tokens']
    
    # Extract model parameters if not explicitly provided
    if temperature is None or max_tokens is None or top_p is None:
        model_params = extract_model_parameters(
            execution_settings=metadata.get('execution_settings') if metadata else None,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        
        temperature = temperature if temperature is not None else model_params['temperature']
        max_tokens = max_tokens if max_tokens is not None else model_params['max_tokens']
        top_p = top_p if top_p is not None else model_params['top_p']
    
    # ⭐ CRITICAL: Auto-create prompt_breakdown if system_prompt or user_message provided
    # This ensures these fields get extracted to columns for Stories 2 & 6
    # WITHOUT THIS, Stories 2 & 6 WILL NOT WORK!
    if (system_prompt or user_message) and not prompt_breakdown:
        prompt_breakdown = create_prompt_breakdown(
            system_prompt=system_prompt,
            user_message=user_message,
            system_prompt_tokens=system_prompt_tokens,
            user_message_tokens=user_message_tokens,
            chat_history_tokens=chat_history_tokens,
            chat_history_count=None,
            response_text=response_text,
        )
    
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
    
    # ⭐ CLEAN METADATA: Remove non-serializable objects before saving
    # This prevents JSON serialization errors in the database
    if metadata:
        metadata.pop('conversation_memory', None)
        metadata.pop('execution_settings', None)
        # 🔧 Add any other non-serializable objects from your framework here
    
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
        
        # Conversation linking
        conversation_id=conversation_id,
        turn_number=turn_number,
        parent_call_id=parent_call_id,
        user_id=user_id,
        
        # Model configuration
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        model_config=model_config,
        
        # Token breakdown
        system_prompt_tokens=system_prompt_tokens,
        user_message_tokens=user_message_tokens,
        chat_history_tokens=chat_history_tokens,
        conversation_context_tokens=conversation_context_tokens,
        tool_definitions_tokens=tool_definitions_tokens,
        
        # Tool calling
        tool_calls_made=tool_calls_made,
        tool_call_count=tool_call_count,
        tool_execution_time_ms=tool_execution_time_ms,
        
        # Streaming
        time_to_first_token_ms=time_to_first_token_ms,
        streaming_metrics=streaming_metrics,
        
        # Error details
        error_type=error_type,
        error_code=error_code,
        retry_count=retry_count,
        error_details=error_details,
        
        # Cached tokens
        cached_prompt_tokens=cached_prompt_tokens,
        cached_token_savings=cached_token_savings,
        
        # Observability
        trace_id=trace_id,
        request_id=request_id,
        environment=environment,
        
        # Experiments
        experiment_id=experiment_id,
        control_group=control_group,
        experiment_metadata=experiment_metadata,
        
        # Metadata
        metadata=metadata,
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'obs',
    'judge',
    'cache',
    'router',
    'prompts',
    'track_llm_call',
    'start_session',
    'end_session',
    'CURRENT_PHASE',
    'PROJECT_NAME',
    'DEFAULT_MODEL',
]