"""
Observatory Configuration Template
Location: your-project/observatory_config.py

Setup:
    1. Copy .env.example to your project as .env
    2. Copy this file to your project as observatory_config.py
    3. Customize .env with your API keys and settings
    4. Add @observe to your LLM calls

================================================================================
USAGE
================================================================================

    from observatory_config import observe

    @observe(operation="chat", agent_name="ChatBot")
    async def chat(prompt: str, conversation_id: str = None, turn_number: int = None):
        return await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

    # That's it! All metrics tracked, all optimizations applied automatically.

================================================================================
TWO-PHASE OPTIMIZATION
================================================================================

    Add to your .env file:

        # Phase 1 - Baseline (default)
        OBSERVATORY_PHASE=baseline

        # Phase 2 - Optimized (after adding OPTIMIZATIONS)
        # OBSERVATORY_PHASE=optimized

    BASELINE: Tracks metrics, detects opportunities, NO behavior changes
    OPTIMIZED: Applies your OPTIMIZATIONS, compares to baseline

================================================================================
WORKFLOW
================================================================================

    1. Add @observe to your LLM calls
    2. Run in baseline mode (OBSERVATORY_PHASE=baseline in .env)
    3. Review opportunities in dashboard
    4. Add optimizations to OPTIMIZATIONS section (near end of this file)
    5. Change .env to OBSERVATORY_PHASE=optimized
    6. Compare baseline vs optimized in dashboard

================================================================================
DECORATOR OPTIONS
================================================================================

    @observe(
        operation="chat",           # Required: name for grouping
        agent_name="ChatBot",       # Optional: component name
        agent_role="orchestrator",  # Optional: role type
        conversation_id=None,       # Optional: or pass as function param
        turn_number=None,           # Optional: or pass as function param
        user_id=None,               # Optional: user identifier
        complexity=0.5,             # Optional: 0.0-1.0 for routing
        skip_cache=False,           # Optional: bypass cache check
        skip_quality_eval=False,    # Optional: skip LLM-as-judge
    )
"""

import os
import logging
from functools import partial
from typing import Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =============================================================================
# OBSERVATORY SDK IMPORTS
# =============================================================================

from observatory import (
    __version__ as OBSERVATORY_VERSION,
    Observatory,
    ModelProvider,
    track_llm_call as _sdk_track_llm_call,
    observe as _sdk_observe,
    estimate_tokens,
    calculate_cost,
    classify_error,
    # Components
    LLMJudge,
    CacheManager,
    PersistentCacheManager,
    PrefixCacheDetector,
    ModelRouter,
    PromptManager,
    PromptOptimizer,
    BatchDetector,
    ParallelDetector,
    StreamingDetector,
    SequentialCallDetector,
    ContextGrowthDetector,
    TokenEfficiencyDetector,
    BatchProcessor,
    ParallelExecutor,
    OptimizationTracker,
    create_cache_metadata,
    create_circuit_breaker,
    AsyncWriteQueue,
    observatory_health_check,
)

# Optional: SemanticCache (requires chromadb)
try:
    from observatory import SemanticCache
    SEMANTIC_CACHE_AVAILABLE = True
except ImportError:
    SemanticCache = None
    SEMANTIC_CACHE_AVAILABLE = False

logger.info(f"Observatory SDK v{OBSERVATORY_VERSION}")

# =============================================================================
# [CUSTOMIZE] PROJECT CONFIGURATION
# =============================================================================

PROJECT_NAME = os.getenv("PROJECT_NAME", "My Project")
DEFAULT_PROVIDER = ModelProvider(os.getenv("MODEL_PROVIDER", "azure"))
DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# Database path
if 'DATABASE_URL' in os.environ:
    OBSERVATORY_DB_PATH = os.environ['DATABASE_URL'].replace('sqlite:///', '')
else:
    db_dir = os.getenv("OBSERVATORY_DB_DIR", os.path.join(os.path.dirname(__file__), "..", "ai-agent-observatory"))
    OBSERVATORY_DB_PATH = os.path.abspath(os.path.join(db_dir, "observatory.db"))
    os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"

Path(OBSERVATORY_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# PHASE CONFIGURATION
# =============================================================================

CURRENT_PHASE = os.getenv("OBSERVATORY_PHASE", "baseline")
if CURRENT_PHASE not in ("baseline", "optimized"):
    CURRENT_PHASE = "baseline"

PHASE_DESCRIPTIONS = {
    "baseline": "Detecting opportunities (no behavior changes)",
    "optimized": "Applying optimizations",
}

logger.info(f"Phase: {CURRENT_PHASE.upper()} - {PHASE_DESCRIPTIONS[CURRENT_PHASE]}")

# =============================================================================
# INTERNAL: SDK COMPONENT INITIALIZATION
# =============================================================================
# These components are used internally by @observe. You don't call them directly.

obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=os.getenv("OBSERVATORY_ENABLED", "true").lower() == "true",
)

optimization_tracker = OptimizationTracker(
    observatory=obs,
    enabled=os.getenv("OPTIMIZATION_TRACKER_ENABLED", "true").lower() == "true",
)

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CUSTOMIZE: LLM Judge - Which operations get quality evaluation            │
# └─────────────────────────────────────────────────────────────────────────────┘

judge = LLMJudge(
    observatory=obs,

    # ↓↓↓ UPDATE THESE: Operations worth evaluating for quality ↓↓↓
    operations={
        # "chat",                    # Main chat responses
        # "generate_email",          # Email drafts
        # "analyze_resume",          # Resume analysis
        # "summarize_document",      # Document summaries
        # "answer_question",         # Q&A responses
    },

    # ↓↓↓ UPDATE THESE: Simple operations to skip (not worth evaluating) ↓↓↓
    skip_operations={
        # "list_jobs",               # Simple list retrieval
        # "get_job_details",         # Data lookup
        # "format_date",             # Formatting tasks
        # "extract_keywords",        # Simple extraction
    },

    # ↓↓↓ UPDATE THESE: Evaluation criteria (must sum to 1.0) ↓↓↓
    criteria={
        "relevance": 0.25,         # How relevant is the response?
        "accuracy": 0.25,          # Is the information correct?
        "helpfulness": 0.25,       # Does it help the user?
        "professionalism": 0.15,   # Appropriate tone?
        "clarity": 0.10,           # Easy to understand?
    },

    # ↓↓↓ UPDATE THIS: Describe your domain for better evaluations ↓↓↓
    domain_context="your domain description here",
    # Examples:
    # domain_context="Career coaching chatbot helping job seekers with resumes and interviews",
    # domain_context="Customer support for an e-commerce platform selling electronics",
    # domain_context="Legal document analysis assistant for contract review",

    sample_rate=1.0,
    judge_model=os.getenv("JUDGE_MODEL", DEFAULT_MODEL),
    track_judge_calls=True,
    enabled=os.getenv("JUDGE_ENABLED", "true").lower() == "true",
    min_confidence=0.7,
    max_prompt_chars=2000,
    max_response_chars=3000,
)

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CUSTOMIZE: Cache Manager - Which operations get exact-match caching       │
# └─────────────────────────────────────────────────────────────────────────────┘

cache = CacheManager(
    observatory=obs,

    # ↓↓↓ UPDATE THESE: Operations to cache with TTL in seconds ↓↓↓
    operations={
        # "search_jobs": {"ttl": 3600, "normalize": True},     # 1 hour, normalize whitespace
        # "get_job_details": {"ttl": 1800, "normalize": False}, # 30 min, exact match
        # "list_resumes": {"ttl": 3600, "normalize": False},   # 1 hour
        # "analyze_resume": {"ttl": 7200, "normalize": True},  # 2 hours
    },

    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
    max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
    normalize_prompts=True,
    enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

# -----------------------------------------------------------------------------
# Persistent Cache - SQLite (survives restarts)
# -----------------------------------------------------------------------------

persistent_cache = PersistentCacheManager(
    db_path=os.getenv("PERSISTENT_CACHE_PATH", "./cache/app_cache.db"),
    observatory=obs,
    operations={
        "expensive_analysis": {"ttl": 604800},
        # Add expensive operations...
    },
    default_ttl=604800,
    max_entries=5000,
    enabled=os.getenv("PERSISTENT_CACHE_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

# -----------------------------------------------------------------------------
# Prefix Cache Detector - Azure/Anthropic prefix caching
# -----------------------------------------------------------------------------

prefix_cache = PrefixCacheDetector(
    observatory=obs,
    prefix_length=500,
    min_prefix_tokens=100,
    enabled=os.getenv("PREFIX_CACHE_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CUSTOMIZE: Semantic Cache - Similarity-based caching (requires chromadb)  │
# └─────────────────────────────────────────────────────────────────────────────┘

SEMANTIC_CACHE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data", "semantic_cache")
)

if SEMANTIC_CACHE_AVAILABLE:
    semantic_cache = SemanticCache(
        observatory=obs,
        db_path=SEMANTIC_CACHE_PATH,

        # ↓↓↓ UPDATE THESE: Operations with similarity threshold (0.0-1.0) ↓↓↓
        # Higher threshold = more strict matching (0.95 = very similar)
        # Lower threshold = more lenient matching (0.85 = somewhat similar)
        operations={
            # "chat": {"ttl": 3600, "threshold": 0.92},           # Chat needs high similarity
            # "answer_faq": {"ttl": 7200, "threshold": 0.88},     # FAQs can be more lenient
            # "summarize": {"ttl": 3600, "threshold": 0.90},      # Summaries need good match
        },

        default_ttl=3600,
        default_threshold=0.92,
        enabled=os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true",
        detection_only=(CURRENT_PHASE == "baseline"),
    )
else:
    semantic_cache = None

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CUSTOMIZE: Model Router - Route operations to different models            │
# └─────────────────────────────────────────────────────────────────────────────┘

router = ModelRouter(
    observatory=obs,
    default_model=DEFAULT_MODEL,
    fallback_model=os.getenv("FALLBACK_MODEL", "gpt-4o-mini"),
    enabled=os.getenv("ROUTER_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),

    # ↓↓↓ UPDATE THESE: Rules for routing operations to models ↓↓↓
    rules=[
        # Route by operation name:
        # {
        #     "name": "simple_lookups",
        #     "operations": ["list_jobs", "get_job_details", "list_resumes"],
        #     "model": "gpt-4o-mini",
        #     "reason": "Simple data retrieval - use cheap model",
        # },
        # {
        #     "name": "analysis_tasks",
        #     "operations": ["analyze_resume", "score_match", "generate_cover_letter"],
        #     "model": "gpt-4o",
        #     "reason": "Complex analysis - use premium model",
        # },
        #
        # Route by complexity score (set via @observe(complexity=0.8)):
        # {
        #     "name": "high_complexity",
        #     "min_complexity": 0.7,
        #     "model": "gpt-4o",
        #     "reason": "High complexity score - use premium model",
        # },
    ],
)

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CUSTOMIZE: Prompt Variants - System prompts at different compression levels│
# └─────────────────────────────────────────────────────────────────────────────┘

prompts = PromptManager(observatory=obs)

# ↓↓↓ UPDATE THESE: Your system prompts for different complexity levels ↓↓↓
PROMPT_VARIANTS = {
    "passthrough": {"content": None, "max_tokens": None},
    "simple": {"content": "You are a helpful assistant.", "max_tokens": 150},
    "medium": {"content": "You are an experienced assistant.", "max_tokens": 500},
    "complex": {"content": "REPLACE_WITH_YOUR_SYSTEM_PROMPT", "max_tokens": 1000},
}

# ↓↓↓ UPDATE THESE: Map operations to complexity levels ↓↓↓
OPERATION_COMPLEXITY = {
    "list_items": "simple",
    "get_details": "simple",
    "chat_response": "complex",
}

prompt_optimizer = PromptOptimizer(
    observatory=obs,
    prompt_variants=PROMPT_VARIANTS,
    operation_complexity=OPERATION_COMPLEXITY,
    enabled=os.getenv("PROMPT_OPTIMIZER_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

# -----------------------------------------------------------------------------
# Execution Detectors
# -----------------------------------------------------------------------------

batch_detector = BatchDetector(
    observatory=obs,
    time_window_ms=100,
    min_batch_size=2,
    operations=None,
    enabled=os.getenv("BATCH_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

parallel_detector = ParallelDetector(
    observatory=obs,
    time_window_s=5.0,
    min_parallel_count=2,
    enabled=os.getenv("PARALLEL_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

streaming_detector = StreamingDetector(
    observatory=obs,
    latency_threshold_ms=2000,
    token_threshold=500,
    operations=None,
    enabled=os.getenv("STREAMING_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

sequential_detector = SequentialCallDetector(
    observatory=obs,
    sequence_window_s=60.0,
    min_sequence_count=5,
    operations=None,
    enabled=os.getenv("SEQUENTIAL_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

context_growth_detector = ContextGrowthDetector(
    observatory=obs,
    threshold_percentage=50.0,
    operations=None,
    enabled=os.getenv("CONTEXT_GROWTH_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

token_efficiency_detector = TokenEfficiencyDetector(
    observatory=obs,
    threshold_ratio=50.0,
    operations=None,
    enabled=os.getenv("TOKEN_EFFICIENCY_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

batch_processor = BatchProcessor(
    observatory=obs,
    default_batch_size=3,
    track_batching=True,
    enabled=os.getenv("BATCH_PROCESSOR_ENABLED", "true").lower() == "true",
)

parallel_executor = ParallelExecutor(
    observatory=obs,
    default_max_concurrent=3,
    semaphore_type='count',
    track_parallelism=True,
    enabled=os.getenv("PARALLEL_EXECUTOR_ENABLED", "true").lower() == "true",
)

# -----------------------------------------------------------------------------
# Production Hardening
# -----------------------------------------------------------------------------

storage_circuit_breaker = create_circuit_breaker(
    name="storage",
    failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "5")),
    recovery_timeout=float(os.getenv("CB_RECOVERY_TIMEOUT", "30")),
    enabled=os.getenv("CB_ENABLED", "true").lower() == "true",
)

async_writer = AsyncWriteQueue(
    storage=obs.storage,
    batch_size=int(os.getenv("ASYNC_WRITER_BATCH_SIZE", "10")),
    flush_interval=float(os.getenv("ASYNC_WRITER_FLUSH_INTERVAL", "1.0")),
    max_queue_size=int(os.getenv("ASYNC_WRITER_MAX_QUEUE_SIZE", "1000")),
    enabled=os.getenv("ASYNC_WRITER_ENABLED", "false").lower() == "true",
)

if async_writer.enabled:
    async_writer.start()

# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║                                                                             ║
# ║   CUSTOMIZE: OPTIMIZATIONS                                                  ║
# ║   Add these AFTER reviewing opportunities in dashboard                      ║
# ║                                                                             ║
# ╚═════════════════════════════════════════════════════════════════════════════╝
#
# Available options:
#   cache: {"enabled": True, "ttl": 3600}
#   semantic_cache: {"enabled": True, "threshold": 0.92}
#   route_to: "gpt-4o-mini"
#   streaming: {"enabled": True}
#
# Example:
#
# OPTIMIZATIONS = {
#     "chat": {"cache": {"enabled": True, "ttl": 1800}},
#     "score_resume": {"cache": {"enabled": True}, "route_to": "gpt-4o-mini"},
#     "analyze": {"semantic_cache": {"enabled": True, "threshold": 0.90}},
# }

OPTIMIZATIONS = {
    # ↓↓↓ ADD YOUR OPTIMIZATIONS HERE AFTER REVIEWING DASHBOARD ↓↓↓
}

# =============================================================================
# @observe DECORATOR - THE PRIMARY PUBLIC INTERFACE
# =============================================================================

observe = partial(
    _sdk_observe,
    obs=obs,
    cache=cache,
    semantic_cache=semantic_cache,
    router=router,
    prefix_cache=prefix_cache,
    streaming_detector=streaming_detector,
    batch_detector=batch_detector,
    context_growth_detector=context_growth_detector,
    token_efficiency_detector=token_efficiency_detector,
    judge=judge,
    track_llm_call_fn=partial(_sdk_track_llm_call, observatory=obs, provider=DEFAULT_PROVIDER),
    optimizations=OPTIMIZATIONS,
    current_phase=CURRENT_PHASE,
    default_model=DEFAULT_MODEL,
    estimate_tokens_fn=estimate_tokens,
    calculate_cost_fn=calculate_cost,
    create_cache_metadata_fn=create_cache_metadata,
    classify_error_fn=classify_error,
)

# =============================================================================
# SESSION HELPERS
# =============================================================================

def start_session(operation_type: str = None, **metadata) -> Any:
    """Start a session to group related LLM calls."""
    return obs.start_session(operation_type=operation_type, **metadata)


def end_session(session: Any, success: bool = True, error: str = None) -> None:
    """End an Observatory session."""
    return obs.end_session(session, success=success, error=error)


def get_health(include_details: bool = True) -> dict:
    """Get Observatory health status for /health endpoint."""
    return observatory_health_check(
        storage=obs.storage,
        cache=cache,
        persistent_cache=persistent_cache,
        semantic_cache=semantic_cache,
        judge=judge,
        router=router,
        async_writer=async_writer,
        circuit_breakers={"storage": storage_circuit_breaker},
        include_details=include_details,
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Primary interface
    'observe',
    'start_session',
    'end_session',

    # Configuration
    'OPTIMIZATIONS',
    'CURRENT_PHASE',
    'PROJECT_NAME',
    'DEFAULT_MODEL',

    # Health check
    'get_health',

    # Advanced use only
    'obs',
    'estimate_tokens',
    'calculate_cost',
]
