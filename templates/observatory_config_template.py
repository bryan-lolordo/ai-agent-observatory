"""
Observatory Configuration Template - Universal
Location: your-project/observatory_config.py

This template provides the complete Observatory SDK configuration.
Copy this file to your project and customize the PROJECT-SPECIFIC sections.

================================================================================
SETUP INSTRUCTIONS
================================================================================

1. INSTALL THE SDK (from ai-agent-observatory repo):

   Option A - Install from local clone:
       pip install -e /path/to/ai-agent-observatory

   Option B - Add to your requirements.txt:
       -e /path/to/ai-agent-observatory

   Option C - Install from GitHub:
       pip install git+https://github.com/bryan-lolordo/ai-agent-observatory.git

2. INSTALL CHROMADB (optional - for SemanticCache):

   pip install chromadb

   Note: SemanticCache is optional. If chromadb is not installed, the SDK will
   work fine but semantic caching will be disabled.

3. COPY THIS FILE to your project root as observatory_config.py

4. CUSTOMIZE all sections marked with [PROJECT-SPECIFIC]

5. IMPORT AND USE:

   from observatory_config import obs, track_llm_call, judge, cache, router

================================================================================
USAGE EXAMPLE
================================================================================

    from observatory_config import obs, judge, cache, router, track_llm_call

    # In your LLM call code:
    quality = await judge.maybe_evaluate(operation, prompt, response, client)
    track_llm_call(model, tokens, latency, operation=op, quality_evaluation=quality)

================================================================================
PHASES
================================================================================

    OBSERVATORY_PHASE=baseline   (default - detect only, no changes to behavior)
    OBSERVATORY_PHASE=optimized  (apply optimizations: caching, routing, compression)

Set via environment variable: export OBSERVATORY_PHASE=baseline
"""

import os
import re
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =============================================================================
# OBSERVATORY SDK IMPORTS
# =============================================================================

# Core components
from observatory import (
    __version__ as OBSERVATORY_VERSION,
    Observatory,
    ModelProvider,
    AgentRole,
    track_llm_call as _sdk_track_llm_call,
    estimate_tokens,
)

# Optimization components
from observatory import (
    LLMJudge,
    CacheManager,
    PrefixCacheDetector,
    ModelRouter,
    PromptManager,
    PromptOptimizer,
    BatchDetector,
    ParallelDetector,
    StreamingDetector,
)

# Data models (for type hints)
from observatory import (
    LLMCall,
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
    ModelConfig,
    StreamingMetrics,
    ExperimentMetadata,
    ErrorDetails,
    SemanticCacheResult,
)

# Helper functions
from observatory import (
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation,
    create_prompt_metadata,
    create_prompt_breakdown,
    create_semantic_cache_metadata,
)

# Optional: SemanticCache (requires chromadb)
try:
    from observatory import SemanticCache
    SEMANTIC_CACHE_AVAILABLE = True
except ImportError:
    SemanticCache = None
    SEMANTIC_CACHE_AVAILABLE = False
    logger.warning("SemanticCache unavailable - install with: pip install chromadb")

# =============================================================================
# IMPORT VALIDATION
# =============================================================================

MIN_REQUIRED_VERSION = "0.1.0"

REQUIRED_COMPONENTS = {
    'Observatory': Observatory,
    'track_llm_call': _sdk_track_llm_call,
    'ModelProvider': ModelProvider,
    'LLMJudge': LLMJudge,
    'CacheManager': CacheManager,
}

for name, component in REQUIRED_COMPONENTS.items():
    if component is None:
        raise ImportError(f"Critical component '{name}' not available")

try:
    if OBSERVATORY_VERSION < MIN_REQUIRED_VERSION:
        logger.warning(f"Observatory {MIN_REQUIRED_VERSION}+ recommended, found {OBSERVATORY_VERSION}")
except (TypeError, AttributeError):
    logger.warning(f"Could not validate Observatory version")

logger.info(f"Observatory SDK loaded (version: {OBSERVATORY_VERSION})")

# =============================================================================
# PHASE CONFIGURATION
# =============================================================================
# BASELINE MODE (default): Track metrics, detect opportunities, NO behavior changes
# OPTIMIZED MODE: Apply optimizations (caching, routing, compression)
#
# Set via: OBSERVATORY_PHASE=baseline or OBSERVATORY_PHASE=optimized

CURRENT_PHASE = os.getenv("OBSERVATORY_PHASE", "baseline")

if CURRENT_PHASE not in ("baseline", "optimized"):
    logger.warning(f"Invalid OBSERVATORY_PHASE '{CURRENT_PHASE}', defaulting to 'baseline'")
    CURRENT_PHASE = "baseline"

PHASE_DESCRIPTIONS = {
    "baseline": "Tracking metrics and detecting optimization opportunities (no changes applied)",
    "optimized": "Applying optimizations (caching, routing, compression, token efficiency)",
}

logger.info(f"Observatory Phase: {CURRENT_PHASE.upper()}")
logger.info(f"   {PHASE_DESCRIPTIONS[CURRENT_PHASE]}")

# =============================================================================
# [PROJECT-SPECIFIC] PROJECT CONFIGURATION
# =============================================================================

# TODO: Update these for your project
PROJECT_NAME = os.getenv("PROJECT_NAME", "Your Project Name")

# Model configuration
DEFAULT_PROVIDER = ModelProvider(os.getenv("MODEL_PROVIDER", "azure"))  # azure, openai, anthropic
DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# Database configuration
if 'DATABASE_URL' in os.environ:
    OBSERVATORY_DB_PATH = os.environ['DATABASE_URL'].replace('sqlite:///', '')
else:
    db_dir = os.getenv("OBSERVATORY_DB_DIR", os.path.join(os.path.dirname(__file__), "..", "ai-agent-observatory"))
    db_name = os.getenv("OBSERVATORY_DB_NAME", "observatory.db")
    OBSERVATORY_DB_PATH = os.path.abspath(os.path.join(db_dir, db_name))
    os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"

Path(OBSERVATORY_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

logger.info("="*70)
logger.info(f"Observatory Configuration")
logger.info(f"   Project: {PROJECT_NAME}")
logger.info(f"   Provider: {DEFAULT_PROVIDER.value}")
logger.info(f"   Model: {DEFAULT_MODEL}")
logger.info(f"   Database: {OBSERVATORY_DB_PATH}")
logger.info(f"   Phase: {CURRENT_PHASE.upper()}")
logger.info("="*70)

# =============================================================================
# INITIALIZE OBSERVATORY
# =============================================================================

obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=os.getenv("OBSERVATORY_ENABLED", "true").lower() == "true",
)

logger.info(f"Observatory initialized (enabled={obs.collector.enabled})")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE LLM JUDGE
# =============================================================================
# TODO: Update operations and criteria for your domain

judge = LLMJudge(
    observatory=obs,

    # Operations worth evaluating (high-value outputs)
    # TODO: Add your high-value operations here
    operations={
        "generate_response",
        "analyze_document",
        "create_summary",
        # Add your operations...
    },

    # Operations to skip (low-value or simple)
    # TODO: Add operations that don't need quality evaluation
    skip_operations={
        "list_items",
        "get_details",
        # Add your skip operations...
    },

    # Sampling rate (1.0 = evaluate 100% of eligible calls)
    sample_rate=float(os.getenv("JUDGE_SAMPLE_RATE", "1.0")),

    # TODO: Update criteria for your domain (must sum to 1.0)
    criteria={
        "relevance": 0.30,      # How relevant is the response?
        "accuracy": 0.30,       # Is the information correct?
        "helpfulness": 0.25,    # Does it help the user?
        "clarity": 0.15,        # Is it clear and well-structured?
    },

    # TODO: Update domain context
    domain_context="your domain description here",

    judge_model=os.getenv("JUDGE_MODEL", DEFAULT_MODEL),
    track_judge_calls=True,
    enabled=os.getenv("JUDGE_ENABLED", "true").lower() == "true",
)

logger.info(f"LLMJudge configured (enabled={judge.enabled}, sample_rate={judge.sample_rate})")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE CACHE MANAGER
# =============================================================================
# TODO: Update operations with appropriate TTL and clustering

cache = CacheManager(
    observatory=obs,

    # TODO: Add your operations with TTL settings
    operations={
        # "operation_name": {"ttl": seconds, "normalize": bool, "cluster_id": "group_name"},
        "search_items": {"ttl": 3600, "normalize": True, "cluster_id": "searches"},
        "get_details": {"ttl": 1800, "normalize": False, "cluster_id": "details"},
        "generate_response": {"ttl": 1800, "normalize": False, "cluster_id": "responses"},
        # Add your operations...
    },

    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
    max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
    normalize_prompts=os.getenv("CACHE_NORMALIZE", "true").lower() == "true",
    enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"CacheManager configured (enabled={cache.enabled})")

# =============================================================================
# CONFIGURE PREFIX CACHE DETECTOR
# =============================================================================

prefix_cache = PrefixCacheDetector(
    observatory=obs,
    prefix_length=500,
    min_prefix_tokens=100,
    enabled=os.getenv("PREFIX_CACHE_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"PrefixCacheDetector configured (enabled={prefix_cache.enabled})")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE SEMANTIC CACHE
# =============================================================================
# TODO: Update operations with domain-specific similarity thresholds

if SEMANTIC_CACHE_AVAILABLE:
    semantic_cache = SemanticCache(
        observatory=obs,

        # TODO: Add your operations with similarity thresholds
        operations={
            "generate_response": {
                "ttl": 3600,
                "threshold": 0.92,
                "cluster_id": "responses",
            },
            # Add your operations...
        },

        default_ttl=int(os.getenv("SEMANTIC_CACHE_DEFAULT_TTL", "3600")),
        default_threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92")),
        enabled=os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true",
        detection_only=(CURRENT_PHASE == "baseline"),
    )

    logger.info(f"SemanticCache configured (enabled={semantic_cache.enabled})")
else:
    semantic_cache = None
    logger.info("SemanticCache skipped (ChromaDB not available)")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE MODEL ROUTER
# =============================================================================
# TODO: Update routing rules for your operations

router = ModelRouter(
    observatory=obs,
    default_model=DEFAULT_MODEL,
    fallback_model=os.getenv("FALLBACK_MODEL", "gpt-4o-mini"),
    enabled=os.getenv("ROUTER_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),

    # TODO: Define your routing rules (evaluated in order)
    rules=[
        # Simple operations -> cheap model
        {
            "name": "simple_operations",
            "operations": ["list_items", "get_details", "simple_search"],
            "model": "gpt-4o-mini",
            "reason": "Simple retrieval - cheap model sufficient",
        },

        # Complex operations -> premium model
        {
            "name": "complex_operations",
            "operations": ["deep_analysis", "generate_report", "complex_reasoning"],
            "model": "gpt-4o",
            "reason": "Complex analysis requires premium model",
        },

        # High complexity -> premium model
        {
            "name": "high_complexity",
            "min_complexity": 0.7,
            "model": "gpt-4o",
            "reason": "High complexity score detected",
        },

        # Short requests -> cheap model
        {
            "name": "short_requests",
            "max_tokens": 500,
            "model": "gpt-4o-mini",
            "reason": "Short request - cheap model sufficient",
        },
    ],
)

logger.info(f"ModelRouter configured (enabled={router.enabled})")

# =============================================================================
# CONFIGURE PROMPT MANAGER (A/B TESTING)
# =============================================================================

prompts = PromptManager(observatory=obs)

logger.info(f"PromptManager configured")

# =============================================================================
# [PROJECT-SPECIFIC] PROMPT VARIANTS
# =============================================================================
# TODO: Define your prompt variants for compression optimization

PROMPT_VARIANTS = {
    "passthrough": {
        "content": None,  # None = use the default_prompt passed to get_optimized_prompt()
        "max_tokens": None,
        "description": "Passthrough - use the caller's own task-specific prompt"
    },
    "simple": {
        "content": "You are a helpful assistant. Provide concise responses.",
        "max_tokens": 150,
        "description": "Minimal prompt for simple tasks"
    },
    "medium": {
        "content": "You are an experienced assistant specializing in [your domain].",
        "max_tokens": 500,
        "description": "Medium prompt for structured tasks"
    },
    "complex": {
        "content": "REPLACE_WITH_FULL_SYSTEM_PROMPT",  # TODO: Use your actual full system prompt
        "max_tokens": 1000,
        "description": "Full system prompt for complex analysis"
    },
}

# TODO: Map your operations to complexity levels
OPERATION_COMPLEXITY = {
    # Passthrough operations - have their own task-specific prompts
    "generate_analysis": "passthrough",
    "create_report": "passthrough",

    # Simple operations
    "list_items": "simple",
    "get_details": "simple",

    # Complex operations - use full system prompt
    "chat_response": "complex",
    "main_interaction": "complex",
}

logger.info(f"Prompt variants defined")

# =============================================================================
# CONFIGURE PROMPT OPTIMIZER
# =============================================================================

prompt_optimizer = PromptOptimizer(
    observatory=obs,
    prompt_variants=PROMPT_VARIANTS,
    operation_complexity=OPERATION_COMPLEXITY,
    enabled=os.getenv("PROMPT_OPTIMIZER_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"PromptOptimizer configured (enabled={prompt_optimizer.enabled})")

# =============================================================================
# EXECUTION OPTIMIZATION DETECTORS
# =============================================================================

# Batch Detector - Groups rapid sequential calls
batch_detector = BatchDetector(
    observatory=obs,
    time_window_ms=100,
    min_batch_size=2,
    operations=None,  # None = all operations, or {"op1", "op2"} for specific
    enabled=os.getenv("BATCH_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"BatchDetector configured (enabled={batch_detector.enabled})")

# Parallel Detector - Identifies independent operations
parallel_detector = ParallelDetector(
    observatory=obs,
    time_window_s=5.0,
    min_parallel_count=2,
    enabled=os.getenv("PARALLEL_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"ParallelDetector configured (enabled={parallel_detector.enabled})")

# Streaming Detector - Flags high-latency or large-output calls
streaming_detector = StreamingDetector(
    observatory=obs,
    latency_threshold_ms=2000,
    token_threshold=500,
    operations=None,  # None = all operations, or {"op1", "op2"} for specific
    enabled=os.getenv("STREAMING_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"StreamingDetector configured (enabled={streaming_detector.enabled})")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def classify_error(error: Exception, operation: str = None) -> dict:
    """
    Classify errors for tracking. Returns dict with error_type, error_code.

    Categories:
        - authentication: API key, auth token errors
        - throttling: Rate limit, quota errors
        - network: Timeout, connection errors
        - llm_provider: Provider-specific errors
        - database: Database operation errors
        - input_error: Validation, malformed input
        - response_format: Parsing, JSON decode errors
        - unclassified: Unknown errors
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    if any(x in error_str for x in ["api key", "api_key", "unauthorized", "401", "authentication failed"]):
        return {"error_type": error_type, "error_code": "AUTH_ERROR"}

    elif any(x in error_str for x in ["rate limit", "429", "quota exceeded", "too many requests"]):
        return {"error_type": error_type, "error_code": "RATE_LIMIT"}

    elif any(x in error_str for x in ["timeout", "timed out", "connection", "network"]):
        return {"error_type": error_type, "error_code": "TIMEOUT" if "timeout" in error_str else "CONNECTION_ERROR"}

    elif any(x in error_str for x in ["context length", "token limit", "max tokens", "context_length"]):
        return {"error_type": error_type, "error_code": "CONTEXT_LENGTH_EXCEEDED"}

    elif any(x in error_str for x in ["content filter", "content_filter", "policy violation"]):
        return {"error_type": error_type, "error_code": "CONTENT_FILTER"}

    elif any(x in error_str for x in ["model not found", "deployment not found", "invalid model"]):
        return {"error_type": error_type, "error_code": "MODEL_NOT_FOUND"}

    elif any(x in error_str for x in ["no such column", "no such table", "unknown column"]):
        return {"error_type": error_type, "error_code": "SCHEMA_ERROR"}

    elif any(x in error_type.lower() for x in ["sqlite", "psycopg", "mysql", "database"]):
        return {"error_type": error_type, "error_code": "DB_ERROR"}

    elif re.search(r"not found|no .* found|404", error_str):
        return {"error_type": error_type, "error_code": "NOT_FOUND"}

    elif any(x in error_str for x in ["invalid", "validation", "malformed", "bad request", "400"]):
        return {"error_type": error_type, "error_code": "VALIDATION_ERROR"}

    elif any(x in error_str for x in ["json", "parse", "decode", "unmarshal", "serialization"]):
        return {"error_type": error_type, "error_code": "PARSE_ERROR"}

    else:
        return {"error_type": error_type, "error_code": "UNKNOWN"}


def extract_token_breakdown_from_messages(
    messages: List[Dict] = None,
    system_prompt: str = None,
    user_message: str = None,
    chat_history: Any = None,
    conversation_memory: Any = None,
) -> Dict[str, int]:
    """
    Extract token breakdown from various message formats.
    Works with OpenAI/Azure, Anthropic, LangChain, Semantic Kernel formats.
    """
    breakdown = {
        'system_prompt_tokens': 0,
        'user_message_tokens': 0,
        'chat_history_tokens': 0,
        'chat_history_count': 0,
        'conversation_context_tokens': 0,
    }

    if messages:
        user_messages = []
        assistant_messages = []

        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            tokens = estimate_tokens(content) if content else 0

            if role == 'system':
                breakdown['system_prompt_tokens'] += tokens
            elif role == 'user':
                user_messages.append((content, tokens))
            elif role in ['assistant', 'function', 'tool']:
                assistant_messages.append((content, tokens))
                breakdown['chat_history_tokens'] += tokens

        if user_messages:
            breakdown['user_message_tokens'] = user_messages[-1][1]
            for content, tokens in user_messages[:-1]:
                breakdown['chat_history_tokens'] += tokens

        breakdown['chat_history_count'] = (len(user_messages) - 1) + len(assistant_messages)

    else:
        if system_prompt:
            breakdown['system_prompt_tokens'] = estimate_tokens(system_prompt)
        if user_message:
            breakdown['user_message_tokens'] = estimate_tokens(user_message)

    return breakdown


def extract_model_parameters(
    client: Any = None,
    execution_settings: Any = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Extract model parameters from various sources.
    Works with OpenAI, Azure, Anthropic, Semantic Kernel, LangChain.
    """
    params = {
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': top_p,
    }

    if 'model_kwargs' in kwargs:
        model_kwargs = kwargs['model_kwargs']
        if isinstance(model_kwargs, dict):
            params['temperature'] = params['temperature'] or model_kwargs.get('temperature')
            params['max_tokens'] = params['max_tokens'] or model_kwargs.get('max_tokens')
            params['top_p'] = params['top_p'] or model_kwargs.get('top_p')

    if execution_settings and not all(params.values()):
        try:
            if hasattr(execution_settings, 'temperature'):
                params['temperature'] = params['temperature'] or execution_settings.temperature
            if hasattr(execution_settings, 'max_tokens'):
                params['max_tokens'] = params['max_tokens'] or execution_settings.max_tokens
            if hasattr(execution_settings, 'top_p'):
                params['top_p'] = params['top_p'] or execution_settings.top_p
        except Exception:
            pass

    if client and not all(params.values()):
        try:
            if hasattr(client, 'temperature'):
                params['temperature'] = params['temperature'] or client.temperature
            if hasattr(client, 'max_tokens'):
                params['max_tokens'] = params['max_tokens'] or client.max_tokens
            if hasattr(client, 'top_p'):
                params['top_p'] = params['top_p'] or client.top_p
        except Exception:
            pass

    return params


# =============================================================================
# MAIN WRAPPER: track_llm_call()
# =============================================================================

def track_llm_call(
    # TIER 1 - Core metrics (always include)
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

    # Conversation linking
    conversation_id: str = None,
    turn_number: int = None,
    parent_call_id: str = None,
    user_id: str = None,

    # Model configuration
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    model_config: ModelConfig = None,

    # Token breakdown
    system_prompt_tokens: int = None,
    user_message_tokens: int = None,
    chat_history_tokens: int = None,
    chat_history_count: int = None,
    conversation_context_tokens: int = None,
    tool_definitions_tokens: int = None,

    # Tool/function calling
    tool_calls_made: List[Dict[str, Any]] = None,
    tool_call_count: int = None,
    tool_execution_time_ms: float = None,

    # Streaming
    time_to_first_token_ms: float = None,
    streaming_metrics: StreamingMetrics = None,

    # Error details
    error_type: str = None,
    error_code: str = None,
    retry_count: int = None,
    error_details: ErrorDetails = None,

    # Cached tokens
    cached_prompt_tokens: int = None,
    cached_token_savings: float = None,

    # Observability
    trace_id: str = None,
    request_id: str = None,
    environment: str = None,
    prompt_prefix_hash: str = None,

    # Experiment tracking
    experiment_id: str = None,
    control_group: bool = None,
    experiment_metadata: ExperimentMetadata = None,

    # Custom metadata
    metadata: dict = None,
) -> LLMCall:
    """
    Track an LLM call with auto-filled defaults.

    This is your main interface for tracking LLM calls. It automatically:
    - Extracts token breakdown from messages
    - Extracts model parameters from various sources
    - Populates prompt_breakdown for analysis
    - Cleans metadata before storage
    """

    # AUTO-EXTRACT: Token breakdown
    if not system_prompt_tokens and not user_message_tokens and not chat_history_tokens:
        token_breakdown = extract_token_breakdown_from_messages(
            messages=messages,
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=metadata.get('chat_history') if metadata else None,
            conversation_memory=metadata.get('conversation_memory') if metadata else None,
        )

        system_prompt_tokens = system_prompt_tokens or token_breakdown['system_prompt_tokens']
        user_message_tokens = user_message_tokens or token_breakdown['user_message_tokens']
        chat_history_tokens = chat_history_tokens or token_breakdown['chat_history_tokens']
        chat_history_count = chat_history_count or token_breakdown['chat_history_count']
        conversation_context_tokens = conversation_context_tokens or token_breakdown['conversation_context_tokens']

    # AUTO-EXTRACT: Model parameters
    if temperature is None or max_tokens is None or top_p is None:
        model_params = extract_model_parameters(
            client=metadata.get('client') if metadata else None,
            execution_settings=metadata.get('execution_settings') if metadata else None,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

        temperature = temperature if temperature is not None else model_params['temperature']
        max_tokens = max_tokens if max_tokens is not None else model_params['max_tokens']
        top_p = top_p if top_p is not None else model_params['top_p']

    # AUTO-CREATE: prompt_breakdown
    if (system_prompt or user_message) and not prompt_breakdown:
        prompt_breakdown = create_prompt_breakdown(
            system_prompt=system_prompt,
            user_message=user_message,
            system_prompt_tokens=system_prompt_tokens,
            user_message_tokens=user_message_tokens,
            chat_history_tokens=chat_history_tokens,
            chat_history_count=chat_history_count,
            conversation_context_tokens=conversation_context_tokens,
            tool_definitions_tokens=tool_definitions_tokens,
            response_text=response_text,
        )

    # CONVERT: agent_role string to enum
    role_enum = None
    if agent_role:
        try:
            role_enum = AgentRole(agent_role)
        except ValueError:
            if metadata is None:
                metadata = {}
            metadata['agent_role_str'] = agent_role

    # CLEAN: Remove non-serializable objects from metadata
    if metadata:
        metadata.pop('conversation_memory', None)
        metadata.pop('execution_settings', None)
        metadata.pop('client', None)
        metadata.pop('chat_history', None)

    # CALL: SDK track_llm_call
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
        chat_history_count=chat_history_count,
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
        prompt_prefix_hash=prompt_prefix_hash,
        experiment_id=experiment_id,
        control_group=control_group,
        experiment_metadata=experiment_metadata,
        metadata=metadata,
    )


# =============================================================================
# SESSION HELPERS
# =============================================================================

def start_session(operation_type: str = None, **metadata) -> Any:
    """Start a new Observatory session for tracking related LLM calls."""
    return obs.start_session(operation_type=operation_type, **metadata)


def end_session(session: Any, success: bool = True, error: str = None, **metadata) -> None:
    """End an Observatory session."""
    return obs.end_session(session, success=success, error=error, **metadata)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Observatory instance & components
    'obs',
    'judge',
    'cache',
    'prefix_cache',
    'semantic_cache',
    'router',
    'prompts',
    'prompt_optimizer',

    # Execution optimization detectors
    'batch_detector',
    'parallel_detector',
    'streaming_detector',

    # Main interface
    'track_llm_call',

    # Helper functions
    'classify_error',
    'extract_token_breakdown_from_messages',
    'extract_model_parameters',

    # Session management
    'start_session',
    'end_session',

    # Configuration constants
    'PROJECT_NAME',
    'DEFAULT_MODEL',
    'DEFAULT_PROVIDER',
    'CURRENT_PHASE',
    'OBSERVATORY_DB_PATH',
    'PROMPT_VARIANTS',
    'OPERATION_COMPLEXITY',

    # Data models
    'LLMCall',
    'RoutingDecision',
    'CacheMetadata',
    'QualityEvaluation',
    'PromptBreakdown',
    'PromptMetadata',
    'ModelConfig',
    'StreamingMetrics',
    'ExperimentMetadata',
    'ErrorDetails',
    'SemanticCacheResult',

    # Helper functions from SDK
    'create_routing_decision',
    'create_cache_metadata',
    'create_quality_evaluation',
    'create_prompt_metadata',
    'create_prompt_breakdown',
    'create_semantic_cache_metadata',
    'estimate_tokens',

    # Enums
    'ModelProvider',
    'AgentRole',
]
