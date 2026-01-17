"""
Observatory Configuration Template - Universal
Location: your-project/observatory_config.py

This is the ONLY file needed in your application to use Observatory.
All logic lives in the observatory package - this just configures it.

================================================================================
SETUP INSTRUCTIONS
================================================================================

1. INSTALL THE SDK (from ai-agent-observatory repo):

   Option A - Install from local clone:
       pip install -e /path/to/ai-agent-observatory

   Option B - Add to your requirements.txt:
       -e /path/to/ai-agent-observatory

   Option C - Install from GitHub (if published):
       pip install git+https://github.com/YOUR_USERNAME/ai-agent-observatory.git

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

================================================================================
FEATURES
================================================================================

This template supports all Observatory SDK features:
- LLM call tracking with 139-field schema
- Quality evaluation with LLM-as-judge
- Two-tier caching (in-memory + SQLite persistent)
- Semantic similarity caching (requires ChromaDB)
- Model routing based on complexity/operation
- Prompt optimization and compression
- Batch/parallel/streaming detection
- Context growth and token efficiency detection
- Fire-and-forget background judge evaluation
- Azure/Anthropic prefix cache metrics extraction
- Session management for grouping related calls
- TrackedLLMCall context manager for 10-step optimization pattern
"""

import os
import re
import logging
import hashlib
import asyncio
from typing import Optional, Dict, List, Any, Callable
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
    # Version
    __version__ as OBSERVATORY_VERSION,

    # Core classes
    Observatory,
    ModelProvider,
    AgentRole,

    # Main tracking function (renamed to avoid conflict with wrapper)
    track_llm_call as _sdk_track_llm_call,

    # Utilities
    estimate_tokens,
    calculate_cost,
)

# Optimization components
from observatory import (
    LLMJudge,
    CacheManager,
    PersistentCacheManager,  # SQLite-backed cross-session cache
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
)

# Context manager for 10-step optimization pattern
from observatory import (
    TrackedLLMCall,
    TrackedLLMCallResult,
    create_tracked_call,
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

# Validate critical components
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

# Version check (warning only, not blocking)
try:
    if OBSERVATORY_VERSION < MIN_REQUIRED_VERSION:
        logger.warning(f"Observatory {MIN_REQUIRED_VERSION}+ recommended, found {OBSERVATORY_VERSION}")
except (TypeError, AttributeError):
    logger.warning(f"Could not validate Observatory version")

logger.info(f"Observatory SDK loaded (version: {OBSERVATORY_VERSION})")

# =============================================================================
# PHASE CONFIGURATION
# =============================================================================
# Controls whether optimizations are detected (baseline) or applied (optimized)
#
# BASELINE MODE (default):
#   - Track all metrics with full 139-field schema
#   - Detect optimization opportunities (cache hits, routing, compression)
#   - Store opportunities in metadata for analysis
#   - NO changes to application behavior
#
# OPTIMIZED MODE:
#   - Apply all detected optimizations
#   - Two-tier caching (in-memory + SQLite persistent)
#   - Semantic caching (ChromaDB)
#   - Model routing (complexity-based)
#   - Prompt compression (simple/medium/complex variants)
#   - Token efficiency (operation-specific max_tokens)
#
# Set via environment variable or .env file:
#   OBSERVATORY_PHASE=baseline   (default - detect only)
#   OBSERVATORY_PHASE=optimized  (apply optimizations)
#
# Or run with: OBSERVATORY_PHASE=optimized python your_app.py

CURRENT_PHASE = os.getenv("OBSERVATORY_PHASE", "baseline")

# Validate phase
if CURRENT_PHASE not in ("baseline", "optimized"):
    logger.warning(f"Invalid OBSERVATORY_PHASE '{CURRENT_PHASE}', defaulting to 'baseline'")
    CURRENT_PHASE = "baseline"

# Phase descriptions for clarity
PHASE_DESCRIPTIONS = {
    "baseline": "Tracking metrics and detecting optimization opportunities (no changes applied)",
    "optimized": "Applying optimizations (caching, routing, compression, token efficiency)",
}

logger.info(f"Observatory Phase: {CURRENT_PHASE.upper()}")
logger.info(f"   {PHASE_DESCRIPTIONS[CURRENT_PHASE]}")

# =============================================================================
# [PROJECT-SPECIFIC] PROJECT CONFIGURATION
# =============================================================================
# TODO: Update these for your project via environment variables or .env file

# Project identification
PROJECT_NAME = os.getenv("PROJECT_NAME", "Your Project Name")  # TODO: Change this

# Model configuration
DEFAULT_PROVIDER = ModelProvider(os.getenv("MODEL_PROVIDER", "azure"))  # azure, openai, anthropic
DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# Database configuration
if 'DATABASE_URL' in os.environ:
    # Use explicit DATABASE_URL if provided
    OBSERVATORY_DB_PATH = os.environ['DATABASE_URL'].replace('sqlite:///', '')
else:
    # Default: observatory.db in parent directory's ai-agent-observatory folder
    db_dir = os.getenv("OBSERVATORY_DB_DIR", os.path.join(os.path.dirname(__file__), "..", "ai-agent-observatory"))
    db_name = os.getenv("OBSERVATORY_DB_NAME", "observatory.db")
    OBSERVATORY_DB_PATH = os.path.abspath(os.path.join(db_dir, db_name))
    os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"

# Ensure database directory exists
Path(OBSERVATORY_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Log configuration
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
# CONFIGURE OPTIMIZATION TRACKER
# =============================================================================
# Tracks optimization impact by comparing baseline vs optimized phases.
#
# Automatically aggregates all calls tagged with phase='baseline' vs phase='optimized'
# to measure cost, latency, token, and quality improvements.
#
# Works in both baseline and optimized phases - data is automatically tagged.

from observatory import OptimizationTracker

optimization_tracker = OptimizationTracker(
    observatory=obs,
    enabled=os.getenv("OPTIMIZATION_TRACKER_ENABLED", "true").lower() == "true",
)

logger.info(f"OptimizationTracker configured (enabled={optimization_tracker.enabled})")
if optimization_tracker.enabled:
    logger.info(f"   Database: {optimization_tracker.db_path}")
    logger.info(f"   Tracks phase comparisons automatically")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE LLM JUDGE
# =============================================================================
# TODO: Update operations, criteria, and domain_context for your domain

judge = LLMJudge(
    observatory=obs,

    # TODO: Operations worth evaluating (high-value outputs)
    operations={
        "generate_response",
        "analyze_document",
        "create_summary",
        # Add your high-value operations...
    },

    # TODO: Operations to skip (low-value or simple)
    skip_operations={
        "list_items",
        "get_details",
        # Add operations that don't need quality evaluation...
    },

    # 100% sampling for both phases to ensure full quality tracking
    sample_rate=1.0,

    # TODO: Update criteria for your domain (must sum to 1.0)
    criteria={
        "relevance": 0.25,      # How relevant is the response?
        "accuracy": 0.25,       # Is the information correct?
        "helpfulness": 0.25,    # Does it help the user?
        "professionalism": 0.15,# Is it professional?
        "clarity": 0.10,        # Is it clear and well-structured?
    },

    # TODO: Update domain context
    domain_context="your domain description here",

    judge_model=os.getenv("JUDGE_MODEL", DEFAULT_MODEL),
    track_judge_calls=True,
    enabled=os.getenv("JUDGE_ENABLED", "true").lower() == "true",

    # Quality thresholds
    min_confidence=0.7,           # Reject low-confidence evaluations
    max_prompt_chars=2000,        # Max chars to send to judge
    max_response_chars=3000,      # Max chars to send to judge
)

logger.info(f"LLMJudge configured (enabled={judge.enabled}, sample_rate={judge.sample_rate})")
logger.info(f"   Phase: {CURRENT_PHASE} (tracked in metadata)")
logger.info(f"   Evaluating: {len(judge.operations)} operations")
logger.info(f"   Skipping: {len(judge.skip_operations)} operations")
logger.info(f"   Min confidence: {judge.min_confidence}")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE CACHE MANAGER (IN-MEMORY)
# =============================================================================
# Exact hash-based caching with TTL (in-memory, resets on restart)
#
# BASELINE MODE: Detects exact match opportunities (logs would-be hits)
# OPTIMIZED MODE: Returns cached responses for exact matches
#
# TODO: Update operations with appropriate TTL and clustering

cache = CacheManager(
    observatory=obs,

    # TODO: Add your operations with TTL settings
    # Format: "operation_name": {"ttl": seconds, "normalize": bool, "cluster_id": "group_name"}
    operations={
        "search_items": {"ttl": 3600, "normalize": True, "cluster_id": "searches"},
        "get_details": {"ttl": 1800, "normalize": False, "cluster_id": "details"},
        "generate_response": {"ttl": 1800, "normalize": False, "cluster_id": "responses"},
        # Add your operations...
    },

    # Defaults
    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
    max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
    normalize_prompts=os.getenv("CACHE_NORMALIZE", "true").lower() == "true",

    # Enable in both phases (behavior differs based on detection_only)
    enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    # Baseline: Check cache, track opportunities, DON'T return cached responses
    # Optimized: Return cached responses
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"CacheManager configured (enabled={cache.enabled})")
if cache.enabled:
    mode = "detection only (tracking opportunities)" if cache.detection_only else "active caching"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Caching: {len(cache.operations)} operations")
    logger.info(f"   Default TTL: {cache.default_ttl}s, Max entries: {cache.max_entries}")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE PERSISTENT CACHE (SQLite)
# =============================================================================
# Unlike CacheManager (in-memory), PersistentCacheManager stores data in SQLite
# so it survives application restarts. Perfect for:
# - Expensive computations that shouldn't be recomputed
# - Results where the same inputs should return the same outputs
# - Cross-session caching for returning users
#
# TODO: Update operations and TTL for your use case

persistent_cache = PersistentCacheManager(
    db_path=os.getenv("PERSISTENT_CACHE_PATH", "./cache/app_cache.db"),  # TODO: Update path
    observatory=obs,

    # TODO: Add operations that benefit from cross-session persistence
    operations={
        "expensive_analysis": {"ttl": 604800},   # 7 days
        "compute_heavy_task": {"ttl": 604800},   # 7 days
        # Add your operations...
    },

    # Defaults
    default_ttl=604800,  # 7 days default for persistent cache
    max_entries=int(os.getenv("PERSISTENT_CACHE_MAX_ENTRIES", "5000")),

    # Enable based on environment
    enabled=os.getenv("PERSISTENT_CACHE_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline (same pattern as CacheManager)
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"PersistentCacheManager configured (enabled={persistent_cache.enabled})")
if persistent_cache.enabled:
    mode = "detection only (tracking opportunities)" if persistent_cache.detection_only else "active caching"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   DB path: {persistent_cache.db_path}")
    logger.info(f"   Operations: {len(persistent_cache.operations)}")
    logger.info(f"   Default TTL: {persistent_cache.default_ttl}s (7 days)")

# =============================================================================
# CONFIGURE PREFIX CACHE DETECTOR
# =============================================================================
# Detects opportunities for Azure/Anthropic prefix caching (~50% cost savings on cached prefix)
#
# BASELINE MODE: Tracks prefix reuse and calculates potential savings
# OPTIMIZED MODE: Application code can use Azure/Anthropic prefix caching API
#
# Perfect for large system prompts that rarely change

prefix_cache = PrefixCacheDetector(
    observatory=obs,

    # Track first 500 characters as prefix (captures system prompt start)
    prefix_length=500,

    # Only track prompts with 100+ tokens (smaller prompts don't benefit)
    min_prefix_tokens=100,

    # Enable in both phases
    enabled=os.getenv("PREFIX_CACHE_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    # Baseline: Track prefix reuse, calculate savings, DON'T apply caching
    # Optimized: Application can use Azure/Anthropic prefix caching API
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"PrefixCacheDetector configured (enabled={prefix_cache.enabled})")
if prefix_cache.enabled:
    mode = "detection only (tracking opportunities)" if prefix_cache.detection_only else "API integration ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Prefix length: {prefix_cache.prefix_length} chars")
    logger.info(f"   Min tokens: {prefix_cache.min_prefix_tokens}")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE SEMANTIC CACHE
# =============================================================================
# Unlike CacheManager (exact hash match), SemanticCache uses embeddings to find
# semantically similar prompts. "How do I reset my password?" ~ "Password reset help"
#
# BASELINE MODE: Detects semantic similarity opportunities (logs would-be hits)
# OPTIMIZED MODE: Actually returns cached responses
#
# Requires: pip install chromadb
# TODO: Update operations with domain-specific similarity thresholds

# Semantic cache storage path (in your application's data folder)
SEMANTIC_CACHE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data", "semantic_cache")
)

# Only initialize if ChromaDB is available
if SEMANTIC_CACHE_AVAILABLE:
    semantic_cache = SemanticCache(
        observatory=obs,
        db_path=SEMANTIC_CACHE_PATH,  # Store in project's data folder

        # TODO: Add your operations with similarity thresholds
        operations={
            "generate_response": {
                "ttl": 3600,        # 1 hour
                "threshold": 0.92,  # 92% similarity required
                "cluster_id": "responses",
            },
            "search_items": {
                "ttl": 3600,
                "threshold": 0.90,  # 90% - searches can be more lenient
                "cluster_id": "searches",
            },
            # Add your operations...
        },

        # Defaults for any operation not explicitly configured
        default_ttl=int(os.getenv("SEMANTIC_CACHE_DEFAULT_TTL", "3600")),
        default_threshold=float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92")),

        # Enable in both modes (behavior differs based on detection_only)
        enabled=os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true",

        # Detection-only mode for baseline
        # Baseline: Calculate similarity, track opportunities, DON'T return cached responses
        # Optimized: Return cached responses
        detection_only=(CURRENT_PHASE == "baseline"),
    )

    logger.info(f"SemanticCache configured (enabled={semantic_cache.enabled})")
    if semantic_cache.enabled:
        mode = "detection only (tracking opportunities)" if semantic_cache.detection_only else "active caching"
        logger.info(f"   Mode: {mode}")
        logger.info(f"   Semantic matching: {len(semantic_cache.operations)} operations")
        logger.info(f"   Default threshold: {semantic_cache.default_threshold}")
        logger.info(f"   Storage: {SEMANTIC_CACHE_PATH}")
else:
    semantic_cache = None
    logger.info("SemanticCache skipped (ChromaDB not available)")

# =============================================================================
# [PROJECT-SPECIFIC] CONFIGURE MODEL ROUTER
# =============================================================================
# Intelligent model selection based on complexity, operation, and token count
#
# BASELINE MODE: Calculates routing opportunities (logs would-be upgrades/downgrades)
# OPTIMIZED MODE: Actually routes to different models
#
# TODO: Update rules to match your operations and model strategy

router = ModelRouter(
    observatory=obs,
    default_model=DEFAULT_MODEL,
    fallback_model=os.getenv("FALLBACK_MODEL", "gpt-4o-mini"),

    # Enable in both phases (behavior differs based on detection_only)
    enabled=os.getenv("ROUTER_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    # Baseline: Calculate routing decision, log opportunities, return default_model
    # Optimized: Actually return routed model
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
if router.enabled:
    mode = "detection only (tracking opportunities)" if router.detection_only else "active routing"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Default model: {router.default_model}")
    logger.info(f"   Fallback model: {router.fallback_model}")
    logger.info(f"   Routing rules: {router.get_stats()['num_rules']}")

# =============================================================================
# CONFIGURE PROMPT MANAGER (A/B TESTING)
# =============================================================================
# Template versioning and A/B testing for prompts
# Works identically in both baseline and optimized phases

prompts = PromptManager(observatory=obs)

# Example: Register prompt templates with variants
# Uncomment and customize as needed:
#
# prompts.register(
#     template_id="system_prompt",
#     version="1.0.0",
#     content=SYSTEM_PROMPT,
#     variants={
#         "control": SYSTEM_PROMPT,
#         "concise": CONCISE_PROMPT,
#         "detailed": DETAILED_PROMPT,
#     },
#     experiment_id="prompt_test_jan_2025",
#     weights={"control": 0.5, "concise": 0.25, "detailed": 0.25},
#     description="Testing different prompt styles",
# )

logger.info(f"PromptManager configured")
logger.info(f"   Templates registered: {len(prompts.list_templates())}")
logger.info(f"   Note: A/B testing works in both baseline and optimized phases")

# =============================================================================
# [PROJECT-SPECIFIC] PROMPT VARIANTS
# =============================================================================
# Define prompt variants for compression optimization
# System prompts are often 90%+ of input tokens - huge optimization opportunity!
#
# TODO: Replace with your actual prompts

PROMPT_VARIANTS = {
    "passthrough": {
        "content": None,  # None = use the default_prompt passed to get_optimized_prompt()
        "max_tokens": None,  # None = no limit override
        "description": "Passthrough - use the caller's own task-specific prompt"
    },
    "simple": {
        "content": "You are a helpful assistant. Provide concise responses.",  # TODO: Replace
        "max_tokens": 150,
        "description": "Minimal prompt for simple tasks"
    },
    "medium": {
        "content": "You are an experienced assistant specializing in [your domain].",  # TODO: Replace
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

    # Simple operations (use compressed prompt)
    "list_items": "simple",
    "get_details": "simple",

    # Complex operations (use full system prompt)
    "chat_response": "complex",
    "main_interaction": "complex",
}

logger.info(f"Prompt variants defined")
logger.info(f"   Variants: {', '.join(PROMPT_VARIANTS.keys())}")
logger.info(f"   Operations mapped: {len(OPERATION_COMPLEXITY)}")

# =============================================================================
# CONFIGURE PROMPT OPTIMIZER
# =============================================================================
# Reduces input tokens through prompt compression and operation-specific max_tokens
#
# BASELINE MODE: Detects compression opportunities (logs potential savings)
# OPTIMIZED MODE: Returns compressed prompts based on operation complexity

prompt_optimizer = PromptOptimizer(
    observatory=obs,

    # Prompt variants with max_tokens limits
    prompt_variants=PROMPT_VARIANTS,

    # Operation -> complexity mapping
    operation_complexity=OPERATION_COMPLEXITY,

    # Enable in both phases
    enabled=os.getenv("PROMPT_OPTIMIZER_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    # Baseline: Calculate savings, log opportunities, return default prompt
    # Optimized: Return compressed prompt variant
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"PromptOptimizer configured (enabled={prompt_optimizer.enabled})")
if prompt_optimizer.enabled:
    mode = "detection only (tracking savings)" if prompt_optimizer.detection_only else "active compression"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Variants: {len(PROMPT_VARIANTS)}")
    logger.info(f"   Operations: {len(OPERATION_COMPLEXITY)}")

# =============================================================================
# EXECUTION OPTIMIZATION DETECTORS
# =============================================================================
# Detects opportunities for batching, parallelism, and streaming
#
# BASELINE MODE: Identifies patterns and calculates potential savings
# OPTIMIZED MODE: Application code can implement batching/parallel/streaming

# Batch Detector - Groups rapid sequential calls
batch_detector = BatchDetector(
    observatory=obs,

    # Group calls within 100ms window
    time_window_ms=100,

    # At least 2 calls to qualify as batch
    min_batch_size=2,

    # Monitor specific operations (None = all operations)
    # TODO: Add your operations that might benefit from batching
    operations=None,

    # Enable in both phases
    enabled=os.getenv("BATCH_DETECTOR_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"BatchDetector configured (enabled={batch_detector.enabled})")
if batch_detector.enabled:
    mode = "detection only (tracking opportunities)" if batch_detector.detection_only else "implementation ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Time window: {batch_detector.time_window_ms}ms")
    logger.info(f"   Min batch size: {batch_detector.min_batch_size}")

# Parallel Detector - Identifies independent operations
parallel_detector = ParallelDetector(
    observatory=obs,

    # Look for parallelism within 5 second window
    time_window_s=5.0,

    # At least 2 calls to parallelize
    min_parallel_count=2,

    # Enable in both phases
    enabled=os.getenv("PARALLEL_DETECTOR_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"ParallelDetector configured (enabled={parallel_detector.enabled})")
if parallel_detector.enabled:
    mode = "detection only (tracking opportunities)" if parallel_detector.detection_only else "implementation ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Time window: {parallel_detector.time_window_s}s")
    logger.info(f"   Min parallel count: {parallel_detector.min_parallel_count}")

# Streaming Detector - Flags high-latency or large-output calls
streaming_detector = StreamingDetector(
    observatory=obs,

    # Flag calls over 2 seconds
    latency_threshold_ms=2000,

    # Flag outputs over 500 tokens
    token_threshold=500,

    # Monitor specific operations (None = all operations)
    # TODO: Add operations that might benefit from streaming
    operations=None,

    # Enable in both phases
    enabled=os.getenv("STREAMING_DETECTOR_ENABLED", "true").lower() == "true",

    # Detection-only mode for baseline
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"StreamingDetector configured (enabled={streaming_detector.enabled})")
if streaming_detector.enabled:
    mode = "detection only (flagging candidates)" if streaming_detector.detection_only else "implementation ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Latency threshold: {streaming_detector.latency_threshold_ms}ms")
    logger.info(f"   Token threshold: {streaming_detector.token_threshold}")

# =============================================================================
# PROMPT PATTERN DETECTORS
# =============================================================================
# Detects sequential patterns, context growth, and token inefficiency

# Sequential Call Detector - Identifies sequential patterns over longer timeframes
sequential_detector = SequentialCallDetector(
    observatory=obs,

    # Look for patterns within 60 second window
    sequence_window_s=60.0,

    # At least 5 sequential calls to qualify
    min_sequence_count=5,

    # Monitor specific operations (None = all operations)
    # TODO: Add your operations that might be called sequentially
    operations=None,

    enabled=os.getenv("SEQUENTIAL_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"SequentialCallDetector configured (enabled={sequential_detector.enabled})")
if sequential_detector.enabled:
    mode = "detection only (tracking patterns)" if sequential_detector.detection_only else "implementation ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Sequence window: {sequential_detector.sequence_window_s}s")
    logger.info(f"   Min sequence count: {sequential_detector.min_sequence_count}")

# Context Growth Detector - Detects when chat history grows too large
context_growth_detector = ContextGrowthDetector(
    observatory=obs,

    # Alert when history > 50% of total prompt
    threshold_percentage=50.0,

    # Monitor chat operations (None = all operations)
    # TODO: Add your chat/conversation operations
    operations=None,

    enabled=os.getenv("CONTEXT_GROWTH_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"ContextGrowthDetector configured (enabled={context_growth_detector.enabled})")
if context_growth_detector.enabled:
    mode = "detection only (tracking growth)" if context_growth_detector.detection_only else "context limiting ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Threshold: {context_growth_detector.threshold_percentage}%")

# Token Efficiency Detector - Detects inefficient token usage patterns
token_efficiency_detector = TokenEfficiencyDetector(
    observatory=obs,

    # Alert when prompt/completion ratio > 50:1
    threshold_ratio=50.0,

    # Monitor specific operations (None = all operations)
    # TODO: Add operations where efficiency matters
    operations=None,

    enabled=os.getenv("TOKEN_EFFICIENCY_DETECTOR_ENABLED", "true").lower() == "true",
    detection_only=(CURRENT_PHASE == "baseline"),
)

logger.info(f"TokenEfficiencyDetector configured (enabled={token_efficiency_detector.enabled})")
if token_efficiency_detector.enabled:
    mode = "detection only (tracking inefficiency)" if token_efficiency_detector.detection_only else "compression ready"
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Threshold ratio: {token_efficiency_detector.threshold_ratio}:1")

# =============================================================================
# UNIVERSAL BATCH + PARALLEL EXECUTION
# =============================================================================
# Execute batching and parallel processing with automatic Observatory tracking

batch_processor = BatchProcessor(
    observatory=obs,

    # Default batch size (can override per operation)
    default_batch_size=3,

    # Track batch creation
    track_batching=True,

    # Enable in both phases
    enabled=os.getenv("BATCH_PROCESSOR_ENABLED", "true").lower() == "true",
)

logger.info(f"BatchProcessor configured (enabled={batch_processor.enabled})")
logger.info(f"   Default batch size: {batch_processor.default_batch_size}")
logger.info(f"   Universal batching available for all operations")

parallel_executor = ParallelExecutor(
    observatory=obs,

    # Default concurrency limit
    default_max_concurrent=3,

    # Semaphore type: 'count' (fixed limit) or 'rate' (requests/second)
    semaphore_type='count',

    # Track parallel execution
    track_parallelism=True,

    # Enable in both phases
    enabled=os.getenv("PARALLEL_EXECUTOR_ENABLED", "true").lower() == "true",
)

logger.info(f"ParallelExecutor configured (enabled={parallel_executor.enabled})")
logger.info(f"   Default concurrency: {parallel_executor.default_max_concurrent}")
logger.info(f"   Semaphore type: {parallel_executor.semaphore_type}")
logger.info(f"   Universal parallel execution available for all operations")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def classify_error(error: Exception, operation: str = None) -> dict:
    """
    Classify errors for tracking. Returns dict with error_type, error_code.

    Universal error classifier - works across different LLM providers and application types.

    Use with ** unpacking in track_llm_call:
        track_llm_call(
            ...
            **classify_error(e, operation="your_operation"),
            retry_count=0,
            ...
        )

    Categories:
        - authentication: API key, auth token errors
        - throttling: Rate limit, quota errors
        - network: Timeout, connection errors
        - llm_provider: Provider-specific errors (context length, content filter)
        - database: Database operation errors
        - database_schema: Schema/structure errors
        - data_missing: Not found, missing data
        - input_error: Validation, malformed input
        - response_format: Parsing, JSON decode errors
        - unclassified: Unknown errors

    Args:
        error: The exception that was caught
        operation: Optional operation name for context

    Returns:
        Dict with error_type, error_code
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Authentication errors (universal - all providers)
    if any(x in error_str for x in ["api key", "api_key", "unauthorized", "401", "authentication failed"]):
        return {"error_type": error_type, "error_code": "AUTH_ERROR"}

    # Throttling errors (universal - all providers)
    elif any(x in error_str for x in ["rate limit", "429", "quota exceeded", "too many requests"]):
        return {"error_type": error_type, "error_code": "RATE_LIMIT"}

    # Network errors (universal)
    elif any(x in error_str for x in ["timeout", "timed out", "connection", "network"]):
        return {"error_type": error_type, "error_code": "TIMEOUT" if "timeout" in error_str else "CONNECTION_ERROR"}

    # LLM provider errors (OpenAI, Azure, Anthropic, etc.)
    elif any(x in error_str for x in ["context length", "token limit", "max tokens", "context_length"]):
        return {"error_type": error_type, "error_code": "CONTEXT_LENGTH_EXCEEDED"}

    elif any(x in error_str for x in ["content filter", "content_filter", "policy violation"]):
        return {"error_type": error_type, "error_code": "CONTENT_FILTER"}

    elif any(x in error_str for x in ["model not found", "deployment not found", "invalid model"]):
        return {"error_type": error_type, "error_code": "MODEL_NOT_FOUND"}

    # Database errors (universal - SQLite, PostgreSQL, MySQL, etc.)
    elif any(x in error_str for x in ["no such column", "no such table", "unknown column", "unknown table"]):
        return {"error_type": error_type, "error_code": "SCHEMA_ERROR"}

    elif any(x in error_type.lower() for x in ["sqlite", "psycopg", "mysql", "database"]) or "database" in error_str:
        return {"error_type": error_type, "error_code": "DB_ERROR"}

    # Data errors (universal)
    elif re.search(r"not found|no .* found|404", error_str):
        return {"error_type": error_type, "error_code": "NOT_FOUND"}

    # Input validation errors (universal)
    elif any(x in error_str for x in ["invalid", "validation", "malformed", "bad request", "400"]):
        return {"error_type": error_type, "error_code": "VALIDATION_ERROR"}

    # Response format errors (universal)
    elif any(x in error_str for x in ["json", "parse", "decode", "unmarshal", "serialization"]):
        return {"error_type": error_type, "error_code": "PARSE_ERROR"}

    # Unclassified (catch-all)
    else:
        return {"error_type": error_type, "error_code": "UNKNOWN"}


def extract_prompt_cache_metrics(
    response: Any = None,
    usage: Any = None,
    system_prompt: str = None,
    prefix_length: int = 500,
    provider: str = "auto",
    cost_per_1k_cached: float = None,
) -> dict:
    """
    Extract prompt cache metrics from LLM responses (Azure, OpenAI, Anthropic).

    Supports automatic detection of provider format or explicit provider specification.
    Works with multiple response formats: raw API responses, SDK objects, or usage dicts.

    Returns a dict ready to be spread into track_llm_call():
        cached_prompt_tokens: int - Tokens served from provider's prompt cache
        cached_token_savings: float - Estimated cost savings from cached tokens
        prompt_prefix_hash: str - Hash for grouping by stable prefix category
        cache_creation_tokens: int - Tokens written to cache (Anthropic)
        cache_read_tokens: int - Tokens read from cache (Anthropic)

    Provider-specific caching:
        - Azure/OpenAI: Automatic prompt caching for repeated prefixes (50% discount)
        - Anthropic: Explicit cache_control blocks with cache_creation/cache_read tokens (90% discount on reads)

    Usage:
        # From LLM response object
        cache_metrics = extract_prompt_cache_metrics(response=response, system_prompt=system_prompt)

        # From usage dict directly
        cache_metrics = extract_prompt_cache_metrics(usage=usage_dict, provider="anthropic")

        # Spread into track_llm_call
        track_llm_call(
            ...other params...,
            **cache_metrics,
        )

    Args:
        response: The LLM response object (OpenAI, Anthropic, Semantic Kernel, etc.)
        usage: Usage dict/object directly (alternative to response)
        system_prompt: The system prompt used (for computing prefix hash)
        prefix_length: Characters to use for prefix hash (default: 500)
        provider: "auto", "azure", "openai", "anthropic" - auto-detects if not specified
        cost_per_1k_cached: Override cost savings per 1K cached tokens (default: provider-specific)

    Returns:
        Dict with cached_prompt_tokens, cached_token_savings, prompt_prefix_hash,
        and optionally cache_creation_tokens, cache_read_tokens for Anthropic
    """
    result = {
        "cached_prompt_tokens": 0,
        "cached_token_savings": 0.0,
        "prompt_prefix_hash": None,
    }

    # Extract usage from response if not provided directly
    if usage is None and response is not None:
        # Try various response formats
        if hasattr(response, 'usage'):
            usage = response.usage
        elif hasattr(response, 'metadata') and response.metadata:
            usage = response.metadata.get("usage")

    if usage:
        cached_tokens = 0
        cache_creation_tokens = 0
        cache_read_tokens = 0
        detected_provider = provider

        # =================================================================
        # ANTHROPIC FORMAT
        # =================================================================
        # Anthropic returns: cache_creation_input_tokens, cache_read_input_tokens
        if hasattr(usage, 'cache_creation_input_tokens') or \
           (isinstance(usage, dict) and 'cache_creation_input_tokens' in usage):
            detected_provider = "anthropic"

            if hasattr(usage, 'cache_creation_input_tokens'):
                cache_creation_tokens = usage.cache_creation_input_tokens or 0
                cache_read_tokens = usage.cache_read_input_tokens or 0
            else:
                cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)
                cache_read_tokens = usage.get('cache_read_input_tokens', 0)

            # Anthropic: cache reads are the "cached" tokens (90% discount)
            cached_tokens = cache_read_tokens
            result["cache_creation_tokens"] = cache_creation_tokens
            result["cache_read_tokens"] = cache_read_tokens

        # =================================================================
        # AZURE/OPENAI FORMAT
        # =================================================================
        # Azure/OpenAI returns: prompt_tokens_details.cached_tokens
        elif hasattr(usage, 'prompt_tokens_details') or \
             (isinstance(usage, dict) and 'prompt_tokens_details' in usage):
            detected_provider = "azure" if provider == "auto" else provider

            if hasattr(usage, 'prompt_tokens_details'):
                prompt_tokens_details = usage.prompt_tokens_details
                if hasattr(prompt_tokens_details, 'cached_tokens'):
                    cached_tokens = prompt_tokens_details.cached_tokens or 0
            elif isinstance(usage, dict):
                prompt_tokens_details = usage.get("prompt_tokens_details", {})
                if isinstance(prompt_tokens_details, dict):
                    cached_tokens = prompt_tokens_details.get("cached_tokens", 0)

        # =================================================================
        # CALCULATE SAVINGS
        # =================================================================
        if cached_tokens > 0:
            result["cached_prompt_tokens"] = cached_tokens

            # Provider-specific cost savings per 1K tokens
            if cost_per_1k_cached is not None:
                savings_per_token = cost_per_1k_cached / 1000
            elif detected_provider == "anthropic":
                # Anthropic: 90% discount on cache reads (~$0.0027/1K saved for Sonnet)
                savings_per_token = 0.0000027
            else:
                # Azure/OpenAI: 50% discount on cached tokens (~$0.0015/1K saved for GPT-4)
                savings_per_token = 0.0000015

            result["cached_token_savings"] = cached_tokens * savings_per_token

    # Compute prefix hash for grouping calls by stable prefix
    if system_prompt:
        prefix = system_prompt[:prefix_length] if len(system_prompt) > prefix_length else system_prompt
        result["prompt_prefix_hash"] = hashlib.md5(prefix.encode()).hexdigest()[:16]

    return result


# Backwards compatibility alias
extract_azure_cache_metrics = extract_prompt_cache_metrics


def extract_token_breakdown_from_messages(
    messages: List[Dict] = None,
    system_prompt: str = None,
    user_message: str = None,
    chat_history: Any = None,
    conversation_memory: Any = None,
) -> Dict[str, int]:
    """
    Extract token breakdown from various message formats.

    Universal function - works with:
    - OpenAI/Azure message format: [{"role": "system", "content": "..."}, ...]
    - Anthropic message format: Similar structure
    - LangChain messages: Convertible to dict format
    - Semantic Kernel ChatHistory: Has .messages attribute
    - Custom ConversationMemory: Has .chat_history or .get_context_for_prompt()

    Auto-populates token fields for comprehensive tracking:
    - system_prompt_tokens
    - user_message_tokens
    - chat_history_tokens
    - chat_history_count (number of messages in history)
    - conversation_context_tokens

    Args:
        messages: Full messages array (OpenAI/Azure/Anthropic format)
        system_prompt: System prompt text (alternative to messages)
        user_message: User message text (alternative to messages)
        chat_history: ChatHistory object (Semantic Kernel format)
        conversation_memory: ConversationMemory object (custom format)

    Returns:
        Dict with all token breakdown fields
    """
    breakdown = {
        'system_prompt_tokens': 0,
        'user_message_tokens': 0,
        'chat_history_tokens': 0,
        'chat_history_count': 0,
        'conversation_context_tokens': 0,
    }

    # METHOD 1: Extract from messages array (OpenAI/Azure/Anthropic)
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

        # Last user message is current, rest go to history
        if user_messages:
            breakdown['user_message_tokens'] = user_messages[-1][1]
            for content, tokens in user_messages[:-1]:
                breakdown['chat_history_tokens'] += tokens

        breakdown['chat_history_count'] = (len(user_messages) - 1) + len(assistant_messages)

    # METHOD 2: Extract from individual strings
    else:
        if system_prompt:
            breakdown['system_prompt_tokens'] = estimate_tokens(system_prompt)

        if user_message:
            breakdown['user_message_tokens'] = estimate_tokens(user_message)

        # METHOD 3: Extract from Semantic Kernel ChatHistory
        if chat_history:
            try:
                if hasattr(chat_history, 'messages'):
                    history_tokens = 0
                    history_count = 0
                    for msg in chat_history.messages:
                        if hasattr(msg, 'role') and msg.role != 'system':
                            content = str(msg.content) if hasattr(msg, 'content') else ''
                            history_tokens += estimate_tokens(content)
                            history_count += 1
                    breakdown['chat_history_tokens'] = history_tokens
                    breakdown['chat_history_count'] = history_count
            except Exception:
                pass

        # METHOD 4: Extract from ConversationMemory
        if conversation_memory:
            try:
                if hasattr(conversation_memory, 'chat_history'):
                    history = conversation_memory.chat_history
                    if hasattr(history, 'messages'):
                        history_tokens = 0
                        history_count = 0
                        for msg in history.messages:
                            if hasattr(msg, 'role') and msg.role != 'system':
                                content = str(msg.content) if hasattr(msg, 'content') else ''
                                history_tokens += estimate_tokens(content)
                                history_count += 1
                        breakdown['chat_history_tokens'] = history_tokens
                        breakdown['chat_history_count'] = history_count

                if hasattr(conversation_memory, 'get_context_for_prompt'):
                    context_text = conversation_memory.get_context_for_prompt()
                    if context_text and context_text != "No prior context.":
                        breakdown['conversation_context_tokens'] = estimate_tokens(context_text)
            except Exception:
                pass

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

    Universal function - works with:
    - OpenAI/Azure OpenAI clients
    - Anthropic clients
    - Semantic Kernel execution_settings
    - LangChain model configs
    - Direct parameter values (highest priority)

    Args:
        client: LLM client object (OpenAI, Azure, Anthropic, etc.)
        execution_settings: Semantic Kernel execution settings
        temperature: Explicit temperature value (0.0-2.0)
        max_tokens: Explicit max tokens value
        top_p: Explicit top_p value (0.0-1.0)
        **kwargs: Additional parameters from other frameworks

    Returns:
        Dict with temperature, max_tokens, top_p (None if not found)
    """
    params = {
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': top_p,
    }

    # Check kwargs for framework-specific parameters
    if 'model_kwargs' in kwargs:
        model_kwargs = kwargs['model_kwargs']
        if isinstance(model_kwargs, dict):
            params['temperature'] = params['temperature'] or model_kwargs.get('temperature')
            params['max_tokens'] = params['max_tokens'] or model_kwargs.get('max_tokens')
            params['top_p'] = params['top_p'] or model_kwargs.get('top_p')

    # Extract from execution_settings (Semantic Kernel)
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

    # Extract from client (OpenAI/Azure/Anthropic)
    if client and not all(params.values()):
        try:
            if hasattr(client, 'temperature'):
                params['temperature'] = params['temperature'] or client.temperature
            if hasattr(client, 'max_tokens'):
                params['max_tokens'] = params['max_tokens'] or client.max_tokens
            if hasattr(client, 'top_p'):
                params['top_p'] = params['top_p'] or client.top_p

            if hasattr(client, 'default_request_params'):
                defaults = client.default_request_params
                params['temperature'] = params['temperature'] or defaults.get('temperature')
                params['max_tokens'] = params['max_tokens'] or defaults.get('max_tokens')
                params['top_p'] = params['top_p'] or defaults.get('top_p')
        except Exception:
            pass

    return params


# =============================================================================
# FIRE-AND-FORGET JUDGE EVALUATION
# =============================================================================
# Runs judge evaluation in the background without blocking the main response.
# Quality scores still get tracked to Observatory, just asynchronously.

# Store for pending judge tasks (for cleanup/debugging if needed)
_pending_judge_tasks: set = set()


async def _run_judge_and_track(
    judge_instance,
    operation: str,
    prompt: str,
    response: str,
    llm_client: Any,
    conversation_id: Optional[str] = None,
    turn_number: Optional[int] = None,
    callback: Optional[Callable] = None,
):
    """Internal: Run judge evaluation and optionally call a callback with results."""
    try:
        quality_eval = await judge_instance.maybe_evaluate(
            operation=operation,
            prompt=prompt,
            response=response,
            llm_client=llm_client,
            conversation_id=conversation_id,
            turn_number=turn_number,
        )
        if callback and quality_eval:
            callback(quality_eval)
        return quality_eval
    except Exception as e:
        logger.warning(f"Background judge evaluation failed for {operation}: {e}")
        return None


def fire_and_forget_judge(
    operation: str,
    prompt: str,
    response: str,
    llm_client: Any,
    conversation_id: Optional[str] = None,
    turn_number: Optional[int] = None,
    callback: Optional[Callable] = None,
) -> None:
    """
    Fire-and-forget judge evaluation - runs in background without blocking.

    Usage:
        # Instead of:
        # quality_eval = await judge.maybe_evaluate(operation, prompt, response, llm_client)

        # Do this:
        fire_and_forget_judge(
            operation=operation,
            prompt=full_prompt,
            response=result_str,
            llm_client=llm_client,  # Your LLM client (OpenAI, Anthropic, etc.)
            conversation_id=conversation_id,  # Optional
            turn_number=turn_number,  # Optional
        )
        # Response returns immediately to user, judge runs in background

    Args:
        operation: The operation name (e.g., "generate_response", "analyze")
        prompt: The full prompt sent to the LLM
        response: The LLM's response
        llm_client: The LLM client/kernel for the judge to use
        conversation_id: Optional conversation ID for tracking
        turn_number: Optional turn number for tracking
        callback: Optional callback function that receives the quality_eval result
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug(f"No event loop for fire-and-forget judge on {operation}")
            return

        task = loop.create_task(
            _run_judge_and_track(
                judge_instance=judge,
                operation=operation,
                prompt=prompt,
                response=response,
                llm_client=llm_client,
                conversation_id=conversation_id,
                turn_number=turn_number,
                callback=callback,
            )
        )

        _pending_judge_tasks.add(task)
        task.add_done_callback(lambda t: _pending_judge_tasks.discard(t))

        logger.debug(f"Fire-and-forget judge started for {operation}")

    except Exception as e:
        logger.warning(f"Failed to start fire-and-forget judge for {operation}: {e}")


async def wait_for_pending_judges(timeout: float = 30.0) -> int:
    """
    Wait for all pending judge evaluations to complete.
    Useful at end of test scenarios or application shutdown.

    Returns:
        Number of tasks that were pending
    """
    if not _pending_judge_tasks:
        return 0

    pending_count = len(_pending_judge_tasks)
    logger.info(f"Waiting for {pending_count} pending judge evaluations...")

    try:
        await asyncio.wait_for(
            asyncio.gather(*_pending_judge_tasks, return_exceptions=True),
            timeout=timeout
        )
        logger.info(f"All {pending_count} judge evaluations completed")
    except asyncio.TimeoutError:
        logger.warning(f"Timeout waiting for judge evaluations ({len(_pending_judge_tasks)} still pending)")

    return pending_count


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

    # Token breakdown (top-level)
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
    Track an LLM call with auto-filled defaults for universal use.

    This is your main interface for tracking LLM calls. It automatically:
    - Extracts token breakdown from messages
    - Extracts model parameters from various sources
    - Populates prompt_breakdown for analysis
    - Cleans metadata before storage
    - Tags calls with current phase (baseline/optimized)

    Args:
        model_name: Model used (defaults to DEFAULT_MODEL if not provided)
        prompt_tokens: Input token count
        completion_tokens: Output token count
        latency_ms: Response time in milliseconds
        ... (all other parameters)

    Returns:
        LLMCall object from Observatory

    Example:
        # Minimal usage
        track_llm_call(
            model_name="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500,
            operation="your_operation"
        )

        # With auto-extraction
        track_llm_call(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ],
            completion_tokens=50,
            latency_ms=500,
            operation="chat"
        )
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

    # AUTO-CREATE: prompt_breakdown for analysis
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
    else:
        metadata = {}

    # AUTO-TAG: Add current phase to every call
    metadata['phase'] = CURRENT_PHASE
    metadata['phase_description'] = PHASE_DESCRIPTIONS[CURRENT_PHASE]

    # CALL: SDK track_llm_call with all parameters
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
# TRACKED LLM CALL - FACTORY FUNCTION
# =============================================================================
# Creates a pre-configured TrackedLLMCall context manager with all Observatory
# components injected. The TrackedLLMCall class is imported from the SDK and
# handles the 10-step optimization pattern.
#
# Usage:
#     # Define your LLM callable (OpenAI, Anthropic, Semantic Kernel, etc.)
#     async def my_llm_call(prompt, system_prompt=None, **kwargs):
#         messages = []
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": prompt})
#
#         response = await client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=messages,
#             **kwargs,
#         )
#         return response.choices[0].message.content, {
#             "prompt_tokens": response.usage.prompt_tokens,
#             "completion_tokens": response.usage.completion_tokens,
#         }
#
#     async with tracked_call(
#         operation="analyze_data",
#         agent_name="DataAnalyzer",
#         agent_role="analyst",
#         complexity=0.4,
#         cache_key={"data_id": data_id, "query_hash": query_hash},
#         metadata={"data_type": data.get('type')}
#     ) as ctx:
#         result = await ctx.call(
#             llm_func=my_llm_call,
#             prompt=f"Data:\n{data}\n\nQuery:\n{query}",
#             system_prompt=ANALYSIS_PROMPT,
#             temperature=0.3,
#             max_tokens=1500,
#         )
#         return self._parse_analysis(result, data)


def tracked_call(
    operation: str,
    agent_name: str = None,
    agent_role: str = None,
    complexity: float = 0.5,
    phase: str = None,
    cache_key: dict = None,
    cache_ttl: int = None,
    memory: Any = None,
    conversation_id: str = None,
    turn_number: int = None,
    metadata: dict = None,
    skip_cache: bool = False,
    skip_quality_eval: bool = False,
    skip_routing: bool = False,
) -> TrackedLLMCall:
    """
    Create a TrackedLLMCall context manager with all Observatory components injected.

    This factory function creates a TrackedLLMCall (from the SDK) pre-configured
    with all the Observatory optimization components defined in this config file.

    Args:
        operation: Operation name for tracking (e.g., "analyze_data")
        agent_name: Name of the calling agent/plugin
        agent_role: Role enum or string (e.g., "analyst", "coordinator")
        complexity: Task complexity score (0.0-1.0) for routing
        phase: "baseline" or "optimized" (defaults to CURRENT_PHASE)
        cache_key: Dict of values to generate cache key from
        cache_ttl: Cache TTL in seconds (default from CacheManager)
        memory: Optional memory/context object with chat_history
        conversation_id: ID linking related calls together
        turn_number: Turn number in conversation
        metadata: Additional metadata to track
        skip_cache: Set True to bypass cache check
        skip_quality_eval: Set True to bypass quality evaluation
        skip_routing: Set True to use default model always

    Returns:
        TrackedLLMCall context manager

    Example:
        async with tracked_call(
            operation="quick_score",
            agent_name="ResumeMatching",
            complexity=0.4,
        ) as ctx:
            result = await ctx.call(
                llm_func=my_openai_call,
                prompt="Score this resume...",
                system_prompt=SCORING_PROMPT,
            )
    """
    return TrackedLLMCall(
        operation=operation,
        agent_name=agent_name,
        agent_role=agent_role,
        complexity=complexity,
        phase=phase or CURRENT_PHASE,
        cache_key=cache_key,
        cache_ttl=cache_ttl,
        memory=memory,
        conversation_id=conversation_id,
        turn_number=turn_number,
        metadata=metadata,
        skip_cache=skip_cache,
        skip_quality_eval=skip_quality_eval,
        skip_routing=skip_routing,
        # Inject all Observatory components
        obs=obs,
        cache=cache,
        semantic_cache=semantic_cache,
        router=router,
        prefix_cache=prefix_cache,
        streaming_detector=streaming_detector,
        prompt_optimizer=prompt_optimizer,
        judge=judge,
        track_llm_call_fn=track_llm_call,
        default_model=DEFAULT_MODEL,
        estimate_tokens_fn=estimate_tokens,
        calculate_cost_fn=calculate_cost,
        create_cache_metadata_fn=create_cache_metadata,
        classify_error_fn=classify_error,
    )


# =============================================================================
# PRODUCTION HARDENING (NEW)
# =============================================================================
# Optional production-ready features for resilience and performance.
#
# Features:
# - Circuit breaker: Prevents cascading failures
# - Async writer: Non-blocking database writes
# - Health checks: Component status monitoring
#
# Enable by uncommenting the sections below.
# =============================================================================

from observatory import (
    # Circuit breaker
    CircuitBreaker,
    CircuitBreakerConfig,
    create_circuit_breaker,
    CircuitOpenError,

    # Async writer
    AsyncWriteQueue,

    # Health checks
    observatory_health_check,
    HealthStatus,

    # Graceful degradation
    SafeObservatoryWrapper,
)

# -----------------------------------------------------------------------------
# CIRCUIT BREAKER (Optional)
# -----------------------------------------------------------------------------
# Prevents cascading failures when database or external services are unhealthy.
# When the circuit is OPEN, operations fail fast instead of hanging.
#
# States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing) -> CLOSED
#
# Environment variables:
#   CB_ENABLED=true
#   CB_FAILURE_THRESHOLD=5
#   CB_RECOVERY_TIMEOUT=30

storage_circuit_breaker = create_circuit_breaker(
    name="storage",
    failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "5")),
    recovery_timeout=float(os.getenv("CB_RECOVERY_TIMEOUT", "30")),
    enabled=os.getenv("CB_ENABLED", "true").lower() == "true",
)

logger.info(f"Circuit breaker configured (enabled={storage_circuit_breaker.config.enabled})")

# -----------------------------------------------------------------------------
# ASYNC WRITER (Optional)
# -----------------------------------------------------------------------------
# Non-blocking database writes via background thread.
# Tracking calls return immediately, writes happen asynchronously.
#
# Environment variables:
#   ASYNC_WRITER_ENABLED=true
#   ASYNC_WRITER_BATCH_SIZE=10
#   ASYNC_WRITER_FLUSH_INTERVAL=1.0
#   ASYNC_WRITER_MAX_QUEUE_SIZE=1000

async_writer = AsyncWriteQueue(
    storage=obs.storage,
    batch_size=int(os.getenv("ASYNC_WRITER_BATCH_SIZE", "10")),
    flush_interval=float(os.getenv("ASYNC_WRITER_FLUSH_INTERVAL", "1.0")),
    max_queue_size=int(os.getenv("ASYNC_WRITER_MAX_QUEUE_SIZE", "1000")),
    enabled=os.getenv("ASYNC_WRITER_ENABLED", "false").lower() == "true",  # Disabled by default
)

# Start the async writer if enabled
if async_writer.enabled:
    async_writer.start()
    logger.info(f"AsyncWriteQueue started (batch_size={async_writer.batch_size})")
else:
    logger.info("AsyncWriteQueue disabled (using synchronous writes)")

# -----------------------------------------------------------------------------
# HEALTH CHECK FUNCTION
# -----------------------------------------------------------------------------
# Returns comprehensive health status for all Observatory components.
# Use in your /health endpoint for Kubernetes probes or monitoring.

def get_health(include_details: bool = True) -> dict:
    """
    Get Observatory health status.

    Returns:
        Dict with status ("healthy", "degraded", "unhealthy"), timestamp, and component details.

    Usage in FastAPI:
        @app.get("/health")
        def health():
            return get_health()

    Usage in Flask:
        @app.route("/health")
        def health():
            return jsonify(get_health())
    """
    return observatory_health_check(
        storage=obs.storage,
        cache=cache,
        persistent_cache=persistent_cache,
        semantic_cache=semantic_cache,
        judge=judge,
        router=router,
        async_writer=async_writer,
        circuit_breakers={
            "storage": storage_circuit_breaker,
        },
        include_details=include_details,
    )


logger.info("Production hardening configured")
logger.info(f"   Circuit breaker: {'enabled' if storage_circuit_breaker.config.enabled else 'disabled'}")
logger.info(f"   Async writer: {'enabled' if async_writer.enabled else 'disabled'}")
logger.info(f"   Health check: get_health() available")


# =============================================================================
# SESSION HELPERS
# =============================================================================

def start_session(operation_type: str = None, **metadata) -> Any:
    """
    Start a new Observatory session for tracking related LLM calls.

    Sessions group multiple LLM calls together (e.g., a multi-turn conversation,
    a complex workflow with multiple agent interactions).

    Args:
        operation_type: Type of operation (e.g., "chat", "workflow", "analysis")
        **metadata: Additional session metadata (user_id, conversation_id, etc.)

    Returns:
        Session object from Observatory
    """
    return obs.start_session(operation_type=operation_type, **metadata)


def end_session(session: Any, success: bool = True, error: str = None, **metadata) -> None:
    """
    End an Observatory session.

    Args:
        session: Session object from start_session()
        success: Whether the session completed successfully
        error: Error message if session failed
        **metadata: Additional metadata to store with session
    """
    return obs.end_session(session, success=success, error=error)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Observatory instance & components
    'obs',
    'judge',
    'cache',
    'persistent_cache',
    'prefix_cache',
    'semantic_cache',
    'router',
    'prompts',
    'prompt_optimizer',
    'optimization_tracker',

    # Context manager abstraction (10-step pattern)
    'TrackedLLMCall',           # From SDK
    'TrackedLLMCallResult',     # From SDK
    'tracked_call',             # Factory function (pre-configured with components)
    'create_tracked_call',      # SDK factory function

    # Execution optimization detectors
    'batch_detector',
    'parallel_detector',
    'streaming_detector',
    'sequential_detector',
    'context_growth_detector',
    'token_efficiency_detector',

    # Universal execution components
    'batch_processor',
    'parallel_executor',

    # Main interface
    'track_llm_call',

    # Helper functions
    'classify_error',
    'extract_prompt_cache_metrics',  # Universal (Azure, OpenAI, Anthropic)
    'extract_azure_cache_metrics',   # Backwards compatibility alias
    'extract_token_breakdown_from_messages',
    'extract_model_parameters',
    'fire_and_forget_judge',
    'wait_for_pending_judges',

    # Session management
    'start_session',
    'end_session',

    # Configuration constants
    'PROJECT_NAME',
    'DEFAULT_MODEL',
    'DEFAULT_PROVIDER',
    'CURRENT_PHASE',
    'OBSERVATORY_DB_PATH',
    'SEMANTIC_CACHE_PATH',
    'PROMPT_VARIANTS',
    'OPERATION_COMPLEXITY',

    # Data models (re-exported from SDK)
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

    # Cache classes
    'PersistentCacheManager',

    # Helper functions (re-exported from SDK)
    'create_routing_decision',
    'create_cache_metadata',
    'create_quality_evaluation',
    'create_prompt_metadata',
    'create_prompt_breakdown',
    'create_semantic_cache_metadata',
    'estimate_tokens',
    'calculate_cost',

    # Enums (re-exported from SDK)
    'ModelProvider',
    'AgentRole',

    # Production hardening
    'storage_circuit_breaker',
    'async_writer',
    'get_health',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitOpenError',
    'AsyncWriteQueue',
    'HealthStatus',
    'SafeObservatoryWrapper',
    'observatory_health_check',
]
