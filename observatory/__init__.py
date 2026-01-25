"""
AI Agent Observatory - Complete SDK Package
Location: observatory/__init__.py

Comprehensive monitoring, optimization, and evaluation toolkit for AI/LLM applications.

Core Components:
- Observatory: Main tracking interface
- LLMJudge: Quality evaluation with LLM-as-judge (production monitoring)
- CacheManager: Response caching with tracking
- ModelRouter: Intelligent model selection
- PromptManager: Template versioning and A/B testing
- OptimizationTracker: Compare baseline vs optimized phases

V2 Evaluation System (NEW):
- ToolUseEvaluator: FREE AST-based function call validation
- ModelJudgeEvaluator: Cheap Haiku-based semantic evaluation
- EvaluationPipeline: Orchestrates multiple evaluators
- ComparisonService: Baseline vs optimized comparison with recommendations

Integration Strategy:
- LLMJudge: Production quality monitoring (sampling, gpt-4o)
- V2 Evaluators: Optimization validation (test suites, Haiku)

Usage:
    from observatory import (
        # Core
        Observatory,
        observe,
        # Production monitoring
        LLMJudge,
        # V2 Evaluation
        ToolUseEvaluator,
        ModelJudgeEvaluator,
        EvaluationPipeline,
        ComparisonService,
    )

    # Production monitoring (existing)
    obs = Observatory(project_name="My App")
    judge = LLMJudge(observatory=obs, operations={"chat"}, sample_rate=0.2)

    # V2 Optimization validation (new)
    pipeline = EvaluationPipeline.create_default()
    result = await pipeline.evaluate(trace, expected)

    # Compare versions
    comparison = ComparisonService()
    report = comparison.compare(baseline_results, optimized_results, ...)
"""

__version__ = "0.5.0"  # Added V2 evaluation system

# =============================================================================
# CORE IMPORTS
# =============================================================================

from observatory.collector import (
    Observatory,
    MetricsCollector,
)

from observatory.storage import Storage

# =============================================================================
# UTILITY IMPORTS
# =============================================================================

from observatory.utils import (
    # Token estimation
    estimate_tokens,
    # Hashing functions
    compute_content_hash,
    generate_prompt_hash,
    # Text normalization
    normalize_prompt,
    # Cost calculation
    calculate_cost,
    MODEL_PRICING,
    # Client detection
    ClientType,
    detect_client_type,
    # Error classification
    classify_error,
    # Token breakdown extraction
    extract_token_breakdown_from_messages,
    # Model parameter extraction
    extract_model_parameters,
)

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
    CallType,

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

    # V2 Evaluation System - Enums
    TestCaseCategory,
    TestDifficulty,
    EvaluationStatus,
    Recommendation,

    # V2 Evaluation System - Test Infrastructure
    TestCase,
    TestCaseExpected,
    TestCaseGroundTruth,
    TestSuite,
    TestSuiteConfig,

    # V2 Evaluation System - Results
    EvaluationRun,
    EvaluationRunMetrics,
    EvaluationResultRecord,
    ComparisonRecord,
    VersionMetrics,
    ComparisonDeltas,
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
    PrefixCacheDetector,
    PersistentCacheManager,
    create_cache_metadata,
)

from observatory.router import (
    ModelRouter,
    RoutingRule,
    create_routing_decision,
)

from observatory.prompts import (
    PromptManager,
    PromptTemplate,
    PromptOptimizer,
    create_prompt_metadata,
    create_prompt_breakdown,
)

from observatory.semantic_cache import (
    SemanticCache,
    SemanticCacheResult,
    SemanticCacheOperationConfig,
    create_semantic_cache_metadata,
)

# =============================================================================
# EXECUTION OPTIMIZATION IMPORTS (NEW)
# =============================================================================

from observatory.execution import (
    # Detectors
    BatchDetector,
    ParallelDetector,
    SequentialCallDetector,
    StreamingDetector,
    ContextGrowthDetector,
    TokenEfficiencyDetector,
    # Data classes
    BatchOpportunity,
    ParallelOpportunity,
    BatchProcessor,        
    ParallelExecutor, 
    SequentialPattern,
    StreamingCandidate,
    ContextGrowthAlert,
    TokenEfficiencyAlert,
)

# =============================================================================
# OPTIMIZATION TRACKER IMPORT (NEW)
# =============================================================================

from observatory.optimization_tracker import (
    OptimizationTracker,
)


# =============================================================================
# @observe DECORATOR - THE PRIMARY PUBLIC INTERFACE
# =============================================================================

from observatory.observe import (
    observe,
    extract_response,
    ExtractedResponse,
    # ContextVar helpers for conversation context propagation
    set_conversation_context,
    get_conversation_context,
)

# =============================================================================
# PRODUCTION HARDENING IMPORTS (NEW)
# =============================================================================

from observatory.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitState,
    CircuitOpenError,
    create_circuit_breaker,
)

from observatory.async_writer import (
    AsyncWriteQueue,
    WriteOperation,
    WriteTask,
)

from observatory.safe_wrapper import (
    safe_call,
    safe_method,
    SafeObservatoryWrapper,
    with_graceful_degradation,
)

from observatory.health import (
    HealthStatus,
    observatory_health_check,
    check_storage_health,
    check_cache_health,
    check_persistent_cache_health,
    check_semantic_cache_health,
    check_judge_health,
    check_router_health,
    check_async_writer_health,
    check_circuit_breaker_health,
)

# =============================================================================
# V2 EVALUATION SYSTEM (NEW)
# =============================================================================

from observatory.evaluators import (
    # Base classes
    BaseEvaluator,
    EvaluationResult,
    # Evaluators
    ToolUseEvaluator,
    ModelJudgeEvaluator,
)

from observatory.evaluation import (
    # Pipeline
    EvaluationPipeline,
    AggregatedResult,
    # Comparison
    ComparisonService,
    ComparisonResult,
    # Test Suites
    TestSuiteLoader,
    TestSuiteBuilder,
    TestSuiteValidator,
    TestSuiteWriter,
    # Storage
    EvaluationStore,
    # Runner
    TestRunner,
    RunnerConfig,
    # Reporting
    ConsoleReporter,
    MarkdownReporter,
    JSONReporter,
    ReportBuilder,
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
    call_type: CallType = CallType.LLM,
    
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
    chat_history_count: int = None,
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

    # Prefix cache detection
    prompt_prefix_hash: str = None,
    
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
        response_text: Response text from the model
        prompt_normalized: Normalized prompt for caching
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
        chat_history_count: Number of messages in chat history (NEW)
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
        call_type=call_type,
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
    "PrefixCacheDetector",
    "PersistentCacheManager",
    "ModelRouter",
    "RoutingRule",
    "PromptManager",
    "PromptTemplate",
    "PromptOptimizer", 
    "SemanticCache",
    "SemanticCacheResult",
    "SemanticCacheOperationConfig",

    # Execution optimization components - Detectors
    "BatchDetector",
    "ParallelDetector",
    "SequentialCallDetector",
    "StreamingDetector",
    "ContextGrowthDetector",
    "TokenEfficiencyDetector",
    # Execution optimization components - Data classes
    "BatchOpportunity",
    "ParallelOpportunity",
    'BatchProcessor',      
    'ParallelExecutor',  
    "SequentialPattern",
    "StreamingCandidate",
    "ContextGrowthAlert",
    "TokenEfficiencyAlert",
    
    # Optimization tracking
    "OptimizationTracker",

    # @observe decorator - THE PRIMARY PUBLIC INTERFACE
    "observe",
    "extract_response",
    "ExtractedResponse",
    "set_conversation_context",
    "get_conversation_context",

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
    
    # Additional models
    "ModelConfig",
    "StreamingMetrics",
    "ExperimentMetadata",
    "ErrorDetails",
    "CallType",

    # V2 Evaluation Models - Enums
    "TestCaseCategory",
    "TestDifficulty",
    "EvaluationStatus",
    "Recommendation",

    # V2 Evaluation Models - Test Infrastructure
    "TestCase",
    "TestCaseExpected",
    "TestCaseGroundTruth",
    "TestSuite",
    "TestSuiteConfig",

    # V2 Evaluation Models - Results
    "EvaluationRun",
    "EvaluationRunMetrics",
    "EvaluationResultRecord",
    "ComparisonRecord",
    "VersionMetrics",
    "ComparisonDeltas",
    
    # Convenience functions
    "track_llm_call",
    "create_quality_evaluation",
    "create_cache_metadata",
    "create_routing_decision",
    "create_prompt_metadata",
    "create_prompt_breakdown",
    "create_semantic_cache_metadata",

    # Utility functions (from utils.py)
    "estimate_tokens",
    "compute_content_hash",
    "generate_prompt_hash",
    "normalize_prompt",
    "calculate_cost",
    "MODEL_PRICING",
    "ClientType",
    "detect_client_type",
    "classify_error",
    "extract_token_breakdown_from_messages",
    "extract_model_parameters",

    # Production hardening - Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitState",
    "CircuitOpenError",
    "create_circuit_breaker",

    # Production hardening - Async writer
    "AsyncWriteQueue",
    "WriteOperation",
    "WriteTask",

    # Production hardening - Graceful degradation
    "safe_call",
    "safe_method",
    "SafeObservatoryWrapper",
    "with_graceful_degradation",

    # Production hardening - Health checks
    "HealthStatus",
    "observatory_health_check",
    "check_storage_health",
    "check_cache_health",
    "check_persistent_cache_health",
    "check_semantic_cache_health",
    "check_judge_health",
    "check_router_health",
    "check_async_writer_health",
    "check_circuit_breaker_health",

    # V2 Evaluation System - Base
    "BaseEvaluator",
    "EvaluationResult",
    "ToolUseEvaluator",
    "ModelJudgeEvaluator",

    # V2 Evaluation System - Pipeline
    "EvaluationPipeline",
    "AggregatedResult",
    "ComparisonService",
    "ComparisonResult",

    # V2 Evaluation System - Test Suites
    "TestSuiteLoader",
    "TestSuiteBuilder",
    "TestSuiteValidator",
    "TestSuiteWriter",

    # V2 Evaluation System - Storage
    "EvaluationStore",

    # V2 Evaluation System - Runner
    "TestRunner",
    "RunnerConfig",

    # V2 Evaluation System - Reporting
    "ConsoleReporter",
    "MarkdownReporter",
    "JSONReporter",
    "ReportBuilder",
]