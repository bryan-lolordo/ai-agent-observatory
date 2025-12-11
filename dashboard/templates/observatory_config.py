"""
Observatory Configuration Template
Location: your-app/observatory_config.py

Copy this file to your AI application and customize the sections marked with [CUSTOMIZE].
This is the ONLY file needed to integrate with Observatory SDK.

Setup:
    1. Install observatory: pip install -e /path/to/ai-agent-observatory
    2. Copy this file to your project root
    3. Customize the [CUSTOMIZE] sections below
    4. Import and use: from observatory_config import obs, judge, cache, router, prompts

Usage in your code:
    from observatory_config import (
        obs, judge, cache, router, prompts,
        track_call, start_session, end_session,
        create_routing_decision, create_cache_metadata, create_quality_evaluation,
    )
    
    # Track an LLM call
    track_call(
        model_name="gpt-4o-mini",
        prompt_tokens=100,
        completion_tokens=200,
        latency_ms=500,
        agent_name="MyAgent",
        operation="my_operation",
        prompt=user_query,
        response_text=llm_response,
    )
"""

import os
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# [CUSTOMIZE] PROJECT CONFIGURATION
# =============================================================================

# Your project name - appears in dashboard
PROJECT_NAME = "My AI Application"  # [CUSTOMIZE] Change this

# Default model from environment or fallback
DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

# Path to Observatory database
# [CUSTOMIZE] Adjust path to your ai-agent-observatory location
OBSERVATORY_DB_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",  # Adjust relative path as needed
        "ai-agent-observatory",
        "observatory.db"
    )
)


# =============================================================================
# IMPORTS FROM OBSERVATORY SDK
# =============================================================================

# Set database URL before importing (Observatory reads this on init)
os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"

from observatory import (
    # Core
    Observatory,
    ModelProvider,
    
    # SDK Components
    LLMJudge,
    CacheManager,
    ModelRouter,
    PromptManager,
    
    # Convenience functions
    track_llm_call,
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation,
    create_prompt_metadata,
    create_prompt_breakdown,
    estimate_tokens,
)


# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================

# [CUSTOMIZE] Set your provider: OPENAI, AZURE, ANTHROPIC, or OTHER
DEFAULT_PROVIDER = ModelProvider.AZURE

# Provider options:
# - ModelProvider.OPENAI    → Direct OpenAI API
# - ModelProvider.AZURE     → Azure OpenAI
# - ModelProvider.ANTHROPIC → Anthropic Claude
# - ModelProvider.OTHER     → Other providers


# =============================================================================
# STARTUP LOGGING
# =============================================================================

print(f"📦 Observatory initialized: {PROJECT_NAME}")
print(f"   Database: {OBSERVATORY_DB_PATH}")
print(f"   Model: {DEFAULT_MODEL}")
print(f"   Provider: {DEFAULT_PROVIDER.value}")


# =============================================================================
# INITIALIZE OBSERVATORY
# =============================================================================

obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=True,  # Set to False to disable tracking
)


# =============================================================================
# [CUSTOMIZE] LLM JUDGE CONFIGURATION
# =============================================================================

judge = LLMJudge(
    observatory=obs,
    
    # [CUSTOMIZE] Operations to evaluate for quality
    # Add operations that produce user-facing content worth evaluating
    operations={
        # Examples - replace with your operations:
        # "chat_response",
        # "generate_content",
        # "analyze_document",
        # "summarize_text",
    },
    
    # [CUSTOMIZE] Operations to skip (low value for quality evaluation)
    skip_operations={
        # Examples - replace with your operations:
        # "generate_sql",
        # "parse_json",
        # "extract_metadata",
    },
    
    # [CUSTOMIZE] Sampling rate (0.0 to 1.0)
    # Higher = more evaluations = more cost but better coverage
    # Recommended: 0.1-0.3 for production, 0.5-1.0 for testing
    sample_rate=0.5,
    
    # [CUSTOMIZE] Evaluation criteria and weights (must sum to ~1.0)
    # Adjust based on what matters for your application
    criteria={
        "relevance": 0.25,      # Does response address the query?
        "accuracy": 0.25,       # Is information correct?
        "helpfulness": 0.25,    # Is response actionable/useful?
        "clarity": 0.15,        # Is response clear and well-structured?
        "professionalism": 0.10, # Is tone appropriate?
    },
    
    # [CUSTOMIZE] Domain context for judge prompts
    # Describe what your application does so judge can evaluate appropriately
    domain_context="AI assistant responses",  # e.g., "code generation", "customer support", "medical advice"
    
    # Model to use for judging (usually same as main model)
    judge_model=DEFAULT_MODEL,
    
    # Track judge LLM calls in Observatory (recommended)
    track_judge_calls=True,
)


# =============================================================================
# [CUSTOMIZE] CACHE MANAGER CONFIGURATION
# =============================================================================

cache = CacheManager(
    observatory=obs,
    
    # [CUSTOMIZE] Operations to cache
    # Key = operation name
    # Value = config dict with:
    #   - ttl: Time-to-live in seconds
    #   - normalize: Whether to normalize prompts (lowercase, strip whitespace)
    #   - cluster_id: Semantic grouping for cache analysis
    operations={
        # Examples - replace with your operations:
        # "search": {"ttl": 3600, "normalize": True, "cluster_id": "searches"},
        # "get_details": {"ttl": 7200, "normalize": False, "cluster_id": "details"},
        # "list_items": {"ttl": 600, "normalize": False, "cluster_id": "lists"},
    },
    
    # Default TTL for operations not explicitly configured
    default_ttl=3600,  # 1 hour
    
    # Maximum cache entries before eviction
    max_entries=1000,
    
    # Whether to normalize prompts by default
    normalize_prompts=True,
)


# =============================================================================
# [CUSTOMIZE] MODEL ROUTER CONFIGURATION
# =============================================================================

router = ModelRouter(
    observatory=obs,
    
    # Default model when no rules match
    default_model=DEFAULT_MODEL,
    
    # Fallback if selected model fails
    fallback_model="gpt-4o-mini",
    
    # [CUSTOMIZE] Routing rules (evaluated in order, first match wins)
    # Each rule can specify:
    #   - name: Rule identifier
    #   - model: Target model
    #   - reason: Why this rule exists
    #   - operations: List of operations this applies to
    #   - agents: List of agents this applies to
    #   - min_complexity / max_complexity: Complexity score range (0-1)
    #   - min_tokens / max_tokens: Token count range
    rules=[
        # Example rules - replace with your routing logic:
        
        # # Simple operations → cheap model
        # {
        #     "name": "simple_ops",
        #     "operations": ["search", "list", "get"],
        #     "model": "gpt-4o-mini",
        #     "reason": "Simple retrieval - cheap model sufficient",
        # },
        # 
        # # Complex analysis → premium model
        # {
        #     "name": "complex_analysis",
        #     "operations": ["analyze", "evaluate", "critique"],
        #     "model": "gpt-4o",
        #     "reason": "Complex analysis requires premium model",
        # },
        # 
        # # High complexity detected → premium model
        # {
        #     "name": "high_complexity",
        #     "min_complexity": 0.7,
        #     "model": "gpt-4o",
        #     "reason": "High complexity score",
        # },
        # 
        # # Short requests → cheap model
        # {
        #     "name": "short_requests",
        #     "max_tokens": 500,
        #     "model": "gpt-4o-mini",
        #     "reason": "Short request",
        # },
    ],
)


# =============================================================================
# [CUSTOMIZE] PROMPT MANAGER CONFIGURATION (A/B Testing)
# =============================================================================

prompts = PromptManager(observatory=obs)

# [CUSTOMIZE] Register your prompt templates for versioning and A/B testing
# Example:
#
# prompts.register(
#     template_id="system_prompt",
#     version="1.0.0",
#     content=YOUR_SYSTEM_PROMPT,
#     
#     # Optional: Define variants for A/B testing
#     variants={
#         "control": YOUR_SYSTEM_PROMPT,
#         "concise": YOUR_CONCISE_PROMPT,
#         "detailed": YOUR_DETAILED_PROMPT,
#     },
#     
#     # Optional: Set traffic weights (must sum to 1.0)
#     weights={
#         "control": 0.5,
#         "concise": 0.25,
#         "detailed": 0.25,
#     },
#     
#     # Optional: Experiment identifier for analysis
#     experiment_id="system_prompt_test_v1",
#     
#     # Optional: Description
#     description="Testing different system prompt styles",
# )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def track_call(
    model_name: str = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: float = 0,
    agent_name: str = None,
    operation: str = None,
    prompt: str = None,
    response_text: str = None,
    success: bool = True,
    error: str = None,
    routing_decision=None,
    cache_metadata=None,
    quality_evaluation=None,
    prompt_breakdown=None,
    prompt_metadata=None,
    prompt_variant_id: str = None,
    metadata: dict = None,
):
    """
    Track an LLM call with Observatory.
    
    Minimum required:
        track_call(
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=500,
            agent_name="MyAgent",
            operation="my_operation",
        )
    
    Recommended (Tier 2):
        track_call(
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=500,
            agent_name="MyAgent",
            operation="my_operation",
            prompt=user_query,
            response_text=llm_response,
        )
    
    Full tracking (Tier 4):
        track_call(
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=500,
            agent_name="MyAgent",
            operation="my_operation",
            prompt=user_query,
            response_text=llm_response,
            routing_decision=router.last_decision,
            cache_metadata=cache.last_metadata,
            quality_evaluation=quality,
        )
    """
    return track_llm_call(
        observatory=obs,
        model_name=model_name or DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        provider=DEFAULT_PROVIDER,
        agent_name=agent_name,
        operation=operation,
        prompt=prompt,
        response_text=response_text,
        success=success,
        error=error,
        routing_decision=routing_decision,
        cache_metadata=cache_metadata,
        quality_evaluation=quality_evaluation,
        prompt_breakdown=prompt_breakdown,
        prompt_metadata=prompt_metadata,
        prompt_variant_id=prompt_variant_id,
        metadata=metadata,
    )


def start_session(operation_type: str = None, **metadata):
    """
    Start a tracking session for a workflow.
    
    Usage:
        session = start_session("user_chat")
        try:
            # ... your code with track_call() ...
            end_session(session, success=True)
        except Exception as e:
            end_session(session, success=False, error=str(e))
    """
    return obs.start_session(operation_type, **metadata)


def end_session(session, success: bool = True, error: str = None):
    """End a tracking session."""
    if session:
        session.success = success
        session.error = error
    return obs.end_session(session)


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

async def tracked_llm_call(
    llm_client,
    prompt: str,
    agent_name: str,
    operation: str,
    model: str = None,
    use_cache: bool = True,
    use_router: bool = True,
    use_judge: bool = True,
    **llm_kwargs,
):
    """
    Helper function that integrates caching, routing, judging, and tracking.
    
    Usage:
        response = await tracked_llm_call(
            llm_client=your_openai_client,
            prompt="Your prompt here",
            agent_name="MyAgent",
            operation="my_operation",
        )
    
    Args:
        llm_client: OpenAI-style client with chat.completions.create()
        prompt: The prompt to send
        agent_name: Agent/plugin name for tracking
        operation: Operation name for tracking
        model: Override model selection
        use_cache: Whether to check/use cache
        use_router: Whether to use model routing
        use_judge: Whether to evaluate quality
        **llm_kwargs: Additional args for LLM call
    
    Returns:
        Response text
    """
    import time
    
    # 1. Check cache
    cache_meta = None
    if use_cache and cache.is_cacheable(operation):
        cached, cache_meta = cache.get(operation, {"prompt": prompt})
        if cached:
            track_call(
                agent_name=agent_name,
                operation=operation,
                prompt=prompt,
                response_text=cached,
                cache_metadata=cache_meta,
            )
            return cached
    
    # 2. Select model
    routing = None
    if use_router:
        selected_model, routing = router.select(
            operation=operation,
            agent=agent_name,
            prompt=prompt,
        )
        model = model or selected_model
    else:
        model = model or DEFAULT_MODEL
    
    # 3. Make LLM call
    start_time = time.time()
    response = await llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **llm_kwargs,
    )
    latency_ms = (time.time() - start_time) * 1000
    response_text = response.choices[0].message.content
    
    # 4. Cache result
    if use_cache and cache.is_cacheable(operation):
        cache.set(operation, {"prompt": prompt}, response_text)
        cache_meta = cache.last_metadata
    
    # 5. Maybe evaluate quality
    quality = None
    if use_judge:
        quality = await judge.maybe_evaluate(
            operation=operation,
            prompt=prompt,
            response=response_text,
            llm_client=llm_client,
        )
    
    # 6. Track
    track_call(
        model_name=model,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=latency_ms,
        agent_name=agent_name,
        operation=operation,
        prompt=prompt,
        response_text=response_text,
        routing_decision=routing,
        cache_metadata=cache_meta,
        quality_evaluation=quality,
    )
    
    return response_text


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
    'OBSERVATORY_DB_PATH',
    
    # Main functions
    'track_call',
    'start_session',
    'end_session',
    'tracked_llm_call',
    
    # Convenience creators (re-exported from SDK)
    'create_routing_decision',
    'create_cache_metadata',
    'create_quality_evaluation',
    'create_prompt_metadata',
    'create_prompt_breakdown',
    'estimate_tokens',
]


# =============================================================================
# QUICK REFERENCE
# =============================================================================

"""
TRACKING TIERS:

Tier 1 - Baseline (Home, Activity, Cost, Router Discovery):
    track_call(
        prompt_tokens=100,
        completion_tokens=200,
        latency_ms=500,
        agent_name="MyAgent",
        operation="my_operation",
    )

Tier 2 - + Prompts (+ Cache Discovery):
    track_call(
        ...,
        prompt=user_query,
        response_text=llm_response,
    )

Tier 3 - + Quality (+ LLM Judge):
    track_call(
        ...,
        quality_evaluation=await judge.maybe_evaluate(...),
    )

Tier 4 - + Routing & Caching (All pages, Active mode):
    track_call(
        ...,
        routing_decision=router.last_decision,
        cache_metadata=cache.last_metadata,
    )

Tier 5 - + Prompt Analysis (Full Prompt Optimizer):
    track_call(
        ...,
        prompt_breakdown=create_prompt_breakdown(...),
        prompt_metadata=prompts.get_metadata("template_id"),
        prompt_variant_id=variant_id,
    )


COMMON PATTERNS:

1. Simple tracking:
    track_call(tokens, latency, agent_name, operation)

2. With caching:
    cached, meta = cache.get(operation, {"query": q})
    if cached:
        return cached
    # ... make LLM call ...
    cache.set(operation, {"query": q}, response)
    track_call(..., cache_metadata=cache.last_metadata)

3. With routing:
    model, decision = router.select(operation=op, prompt=p)
    # ... make LLM call with selected model ...
    track_call(..., routing_decision=decision)

4. With quality evaluation:
    quality = await judge.maybe_evaluate(op, prompt, response, client)
    track_call(..., quality_evaluation=quality)

5. With A/B testing:
    content, variant_id, meta = prompts.select_variant("template_id")
    # ... use content in LLM call ...
    track_call(..., prompt_variant_id=variant_id, prompt_metadata=meta)
"""