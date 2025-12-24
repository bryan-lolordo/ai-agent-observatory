# observatory/models.py
# UPDATED: Complete schema with all new fields for production AI observability


from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OTHER = "other"


class AgentRole(str, Enum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    WRITER = "writer"
    RETRIEVER = "retriever"
    PLANNER = "planner"
    FORMATTER = "formatter"
    FIXER = "fixer"
    ORCHESTRATOR = "orchestrator"
    CUSTOM = "custom"

class CallType(str, Enum):
    LLM = "llm"
    API = "api"
    DATABASE = "database"
    TOOL = "tool"


# =============================================================================
# MODEL CONFIGURATION 
# =============================================================================

class ModelConfig(BaseModel):
    """
    Model configuration/parameters used for this call.
    
    Critical for:
    - Reproducibility (knowing exact settings used)
    - Debugging (why did this call behave differently?)
    - Optimization (testing temperature/max_tokens impact)
    """
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    response_format: Optional[str] = None  # "text", "json_object"
    seed: Optional[int] = None  # For reproducibility
    
    @field_validator('temperature')
    @classmethod
    def temperature_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 2):
            raise ValueError('Temperature must be between 0 and 2')
        return v
    
    @field_validator('max_tokens')
    @classmethod
    def max_tokens_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Max tokens must be positive')
        return v


# =============================================================================
# STREAMING METRICS (NEW)
# =============================================================================

class StreamingMetrics(BaseModel):
    """
    Streaming-specific performance metrics.
    
    Critical for:
    - UX optimization (perceived latency vs total latency)
    - Debugging stream issues
    - Comparing streaming vs non-streaming performance
    """
    is_streaming: bool = False
    time_to_first_token_ms: Optional[float] = None  # Perceived latency
    stream_chunk_count: Optional[int] = None
    stream_interrupted: bool = False
    average_chunk_size: Optional[int] = None  # Tokens per chunk
    
    @field_validator('time_to_first_token_ms')
    @classmethod
    def ttft_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Time to first token must be positive')
        return v


# =============================================================================
# EXPERIMENT METADATA (NEW)
# =============================================================================

class ExperimentMetadata(BaseModel):
    """
    A/B testing and experimentation tracking.
    
    Critical for:
    - Comparing prompt variants
    - Measuring optimization impact
    - Statistical significance testing
    """
    experiment_id: Optional[str] = None  # e.g., "prompt_compression_001"
    experiment_name: Optional[str] = None  # e.g., "System Prompt Compression"
    variant_id: Optional[str] = None  # e.g., "variant_a", "variant_b"
    variant_name: Optional[str] = None  # e.g., "Compressed", "Original"
    control_group: bool = False  # Is this the baseline?
    
    # Experiment parameters
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sample_rate: Optional[float] = None  # % of traffic allocated
    
    # Hypothesis tracking
    hypothesis: Optional[str] = None  # What are you testing?
    expected_improvement: Optional[str] = None  # What metric should improve?
    
    # Grouping for analysis
    cohort: Optional[str] = None  # User segment
    test_dataset_id: Optional[str] = None  # Evaluation dataset
    
    # Metrics snapshot (for quick comparison)
    baseline_cost: Optional[float] = None
    baseline_latency: Optional[float] = None
    baseline_quality: Optional[float] = None
    
    @field_validator('sample_rate')
    @classmethod
    def sample_rate_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Sample rate must be between 0 and 1')
        return v


# =============================================================================
# ERROR DETAILS (NEW)
# =============================================================================

class ErrorDetails(BaseModel):
    """
    Enhanced error classification and tracking.
    
    Critical for:
    - Debugging (what type of error?)
    - Retry strategy optimization
    - Provider reliability tracking
    """
    error_type: Optional[str] = None  # RATE_LIMIT, TIMEOUT, INVALID_REQUEST, etc.
    error_code: Optional[str] = None  # Provider error code (e.g., "429")
    retry_count: Optional[int] = None  # How many retries
    retry_strategy: Optional[str] = None  # exponential_backoff, linear, etc.
    final_success: Optional[bool] = None  # Did retry succeed?
    error_details: Optional[str] = None  # Full error message
    
    @field_validator('retry_count')
    @classmethod
    def retry_count_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Retry count cannot be negative')
        return v


# =============================================================================
# ROUTING DECISION (EXISTING - UNCHANGED)
# =============================================================================

class RoutingDecision(BaseModel):
    """Detailed routing decision metadata"""
    chosen_model: str
    alternative_models: List[str] = Field(default_factory=list)
    model_scores: Dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""
    rule_triggered: Optional[str] = None
    complexity_score: Optional[float] = None
    estimated_cost_savings: Optional[float] = None
    routing_strategy: Optional[str] = None
    
    @field_validator('complexity_score')
    @classmethod
    def complexity_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Complexity score must be between 0 and 1')
        return v
    
    @field_validator('estimated_cost_savings')
    @classmethod
    def savings_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Estimated cost savings cannot be negative')
        return v


# =============================================================================
# CACHE METADATA (EXISTING - UNCHANGED)
# =============================================================================

class CacheMetadata(BaseModel):
    """Cache-related metadata"""
    cache_hit: bool = False
    cache_key: Optional[str] = None
    cache_cluster_id: Optional[str] = None
    normalization_strategy: Optional[str] = None
    similarity_score: Optional[float] = None
    eviction_info: Optional[str] = None
    cache_key_candidates: Optional[List[str]] = None
    dynamic_fields: Optional[List[str]] = None
    content_hash: Optional[str] = None
    ttl_seconds: Optional[int] = None
    
    @field_validator('similarity_score')
    @classmethod
    def similarity_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Similarity score must be between 0 and 1')
        return v


# =============================================================================
# QUALITY EVALUATION (EXISTING - UNCHANGED)
# =============================================================================

class QualityEvaluation(BaseModel):
    """Quality evaluation from LLM Judge"""
    judge_score: Optional[float] = None
    hallucination_flag: bool = False
    error_category: Optional[str] = None
    reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    judge_model: Optional[str] = None
    failure_reason: Optional[str] = None
    improvement_suggestion: Optional[str] = None
    hallucination_details: Optional[str] = None
    evidence_cited: Optional[bool] = None
    factual_error: Optional[bool] = None
    criteria_scores: Optional[Dict[str, float]] = None
    
    @field_validator('judge_score')
    @classmethod
    def judge_score_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Judge score must be between 0 and 10')
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def confidence_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Confidence score must be between 0 and 1')
        return v


# =============================================================================
# PROMPT BREAKDOWN (UPDATED - ENHANCED)
# =============================================================================

class PromptBreakdown(BaseModel):
    """
    Complete breakdown of ALL prompt components.
    
    UPDATED: Added conversation_context_tokens, tool_definitions_tokens,
             total_input_tokens, and ratio calculations.
    
    Critical for:
    - Token optimization (where are tokens going?)
    - Cost attribution (what's expensive?)
    - Context growth tracking (is history bloating?)
    """
    # === INPUT COMPONENTS ===
    
    # 1. System prompt
    system_prompt: Optional[str] = None  # First 1000 chars
    system_prompt_tokens: Optional[int] = None
    
    # 2. User message (current turn only)
    user_message: Optional[str] = None  # First 500 chars
    user_message_tokens: Optional[int] = None
    
    # 3. Chat history (raw messages only)
    chat_history: Optional[List[Dict]] = None  # Message list
    chat_history_tokens: Optional[int] = None
    chat_history_count: Optional[int] = None
    
    # 4. Conversation context (NEW - memory state)
    conversation_context: Optional[str] = None  # First 500 chars
    conversation_context_tokens: Optional[int] = None
    
    # 5. Tool definitions (NEW - function calling schemas)
    tool_definitions: Optional[List[Dict]] = None
    tool_definitions_tokens: Optional[int] = None
    tool_definitions_count: Optional[int] = None
    
    # === COMPUTED TOTALS ===
    total_input_tokens: Optional[int] = None  # NEW - validation
    
    # === RATIOS (NEW - for analysis) ===
    system_to_total_ratio: Optional[float] = None
    history_to_total_ratio: Optional[float] = None
    context_to_total_ratio: Optional[float] = None
    
    # === OUTPUT ===
    response_text: Optional[str] = None  # First 1000 chars
    response_tokens: Optional[int] = None  # Alias for completion_tokens


# =============================================================================
# PROMPT METADATA (EXISTING - UNCHANGED)
# =============================================================================

class PromptMetadata(BaseModel):
    """Metadata for prompt tracking and optimization"""
    prompt_template_id: Optional[str] = None
    prompt_version: Optional[str] = None
    prompt_hash: Optional[str] = None
    experiment_id: Optional[str] = None
    compressible_sections: Optional[List[str]] = None
    optimization_flags: Optional[Dict[str, bool]] = None
    config_version: Optional[str] = None


# =============================================================================
# LLM CALL (UPDATED - COMPREHENSIVE)
# =============================================================================

class LLMCall(BaseModel):
    """
    Complete LLM call record with all tracking fields.
    
    UPDATED: Added 18 new fields for production observability:
    - Conversation linking (conversation_id, turn_number, parent_call_id, user_id)
    - Model config (temperature, max_tokens, top_p, model_config)
    - Tool tracking (tool_call_count, tool_execution_time_ms, tool_calls_made)
    - Token breakdown (5 promoted fields)
    - Experiment tracking (experiment_id, control_group, experiment_metadata)
    - Streaming (time_to_first_token_ms, streaming_metrics)
    - Error details (error_type, error_code, retry_count, error_details)
    - Caching (cached_prompt_tokens, cached_token_savings)
    - Observability (trace_id, request_id, environment)
    """
    id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Call classification
    call_type: CallType = CallType.LLM

    # Model info
    provider: ModelProvider
    model_name: str
    
    # Request details
    prompt: Optional[str] = None
    prompt_normalized: Optional[str] = None
    content_hash: Optional[str] = None  # Hash of prompt for deduplication
    response_text: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    # Cost
    prompt_cost: float
    completion_cost: float
    total_cost: float
    
    # Timing
    latency_ms: float
    
    # Context
    agent_name: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    operation: Optional[str] = None
    
    # Quality
    success: bool = True
    error: Optional[str] = None
    
    # === NEW: CONVERSATION LINKING ===
    conversation_id: Optional[str] = None
    turn_number: Optional[int] = None
    parent_call_id: Optional[str] = None  # For retries/branches
    user_id: Optional[str] = None
    
    # === NEW: MODEL CONFIGURATION ===
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    llm_config: Optional[ModelConfig] = None  # Full config object
    
    # === NEW: TOKEN BREAKDOWN (promoted from JSON for query performance) ===
    system_prompt_tokens: Optional[int] = None
    user_message_tokens: Optional[int] = None
    chat_history_tokens: Optional[int] = None
    chat_history_count: Optional[int] = None
    conversation_context_tokens: Optional[int] = None
    tool_definitions_tokens: Optional[int] = None
    
    # === NEW: TOOL/FUNCTION CALLING ===
    tool_calls_made: Optional[List[Dict]] = None  # Detailed tool calls
    tool_call_count: Optional[int] = None
    tool_execution_time_ms: Optional[float] = None
    
    # === NEW: STREAMING ===
    time_to_first_token_ms: Optional[float] = None
    streaming_metrics: Optional[StreamingMetrics] = None
    
    # === NEW: ERROR DETAILS ===
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: Optional[int] = None
    error_details: Optional[ErrorDetails] = None
    
    # === NEW: CACHED TOKENS ===
    cached_prompt_tokens: Optional[int] = None
    cached_token_savings: Optional[float] = None
    
    # === NEW: OBSERVABILITY ===
    trace_id: Optional[str] = None  # OpenTelemetry
    request_id: Optional[str] = None  # Provider request ID
    environment: Optional[str] = None  # dev, staging, prod
    
    # === EXISTING: Optimization metadata ===
    routing_decision: Optional[RoutingDecision] = None
    cache_metadata: Optional[CacheMetadata] = None
    quality_evaluation: Optional[QualityEvaluation] = None
    prompt_breakdown: Optional[PromptBreakdown] = None
    prompt_metadata: Optional[PromptMetadata] = None
    
    # === NEW: EXPERIMENT TRACKING ===
    experiment_id: Optional[str] = None
    control_group: Optional[bool] = None
    experiment_metadata: Optional[ExperimentMetadata] = None
    
    # === EXISTING: A/B Testing (kept for backward compatibility) ===
    prompt_variant_id: Optional[str] = None
    test_dataset_id: Optional[str] = None
    
    # Optional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('prompt_cost', 'completion_cost', 'total_cost')
    @classmethod
    def cost_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Cost cannot be negative')
        return v
    
    @field_validator('latency_ms')
    @classmethod
    def latency_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Latency must be positive')
        return v
    
    @field_validator('prompt_tokens', 'completion_tokens', 'total_tokens')
    @classmethod
    def tokens_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Token count cannot be negative')
        return v
    
    @field_validator('turn_number')
    @classmethod
    def turn_number_must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError('Turn number must be >= 1')
        return v


# =============================================================================
# SESSION (EXISTING - UNCHANGED)
# =============================================================================

class Session(BaseModel):
    """Session aggregates metrics across multiple LLM calls"""
    id: str
    project_name: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # List of LLM calls in this session
    llm_calls: List['LLMCall'] = Field(default_factory=list)
    
    # Basic aggregated metrics
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    
    # Routing metrics
    total_routing_decisions: int = 0
    routing_cost_savings: float = 0.0
    
    # Caching metrics
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    cache_cost_savings: float = 0.0
    
    # Quality metrics
    avg_quality_score: Optional[float] = None
    total_hallucinations: int = 0
    total_errors: int = 0
    
    success: bool = True
    error: Optional[str] = None
    operation_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# BREAKDOWN MODELS (EXISTING - UNCHANGED)
# =============================================================================

class CostBreakdown(BaseModel):
    """Cost breakdown by component"""
    total_cost: float
    prompt_cost: float
    completion_cost: float
    by_model: Dict[str, float] = Field(default_factory=dict)
    by_agent: Dict[str, float] = Field(default_factory=dict)
    by_operation: Dict[str, float] = Field(default_factory=dict)


class LatencyBreakdown(BaseModel):
    """Latency breakdown and percentiles"""
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float


class TokenBreakdown(BaseModel):
    """Token usage breakdown"""
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    avg_prompt_tokens: float
    avg_completion_tokens: float
    by_operation: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class QualityMetrics(BaseModel):
    """Quality metrics aggregated"""
    avg_score: Optional[float] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    hallucination_rate: float = 0.0
    error_rate: float = 0.0
    total_evaluated: int = 0


class RoutingMetrics(BaseModel):
    """Routing decision metrics"""
    total_routing_decisions: int = 0
    estimated_cost_savings: float = 0.0
    avg_complexity_score: Optional[float] = None
    routes_by_model: Dict[str, int] = Field(default_factory=dict)


class CacheMetrics(BaseModel):
    """Cache performance metrics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    estimated_cost_savings: float = 0.0
    estimated_latency_savings_ms: float = 0.0


class OptimizationSuggestion(BaseModel):
    """Optimization recommendation"""
    category: str  # "caching", "routing", "prompt"
    severity: str  # "high", "medium", "low"
    title: str
    description: str
    estimated_savings: Optional[float] = None
    implementation_effort: str  # "low", "medium", "high"
    data_source: Dict[str, Any] = Field(default_factory=dict)


class SessionReport(BaseModel):
    """Comprehensive session analysis report"""
    session: Session
    cost_breakdown: CostBreakdown
    latency_breakdown: LatencyBreakdown
    token_breakdown: TokenBreakdown
    quality_metrics: QualityMetrics
    routing_metrics: RoutingMetrics
    cache_metrics: CacheMetrics
    optimization_suggestions: List[OptimizationSuggestion] = Field(default_factory=list)

# Rebuild models to resolve forward references
Session.model_rebuild()