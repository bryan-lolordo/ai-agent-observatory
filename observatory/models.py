# observatory/models.py
# UPDATED: Added PromptBreakdown, PromptMetadata, and extended existing models

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


# =============================================================================
# ROUTING DECISION (EXTENDED)
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
    
    # NEW: Extended routing fields
    routing_strategy: Optional[str] = None  # e.g., "complexity_based", "cost_optimized", "quality_first"
    
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
# CACHE METADATA (EXTENDED)
# =============================================================================

class CacheMetadata(BaseModel):
    """Cache-related metadata"""
    cache_hit: bool = False
    cache_key: Optional[str] = None
    cache_cluster_id: Optional[str] = None
    normalization_strategy: Optional[str] = None
    similarity_score: Optional[float] = None  # Keep original name for compatibility
    eviction_info: Optional[str] = None
    
    # NEW: Extended cache fields
    cache_key_candidates: Optional[List[str]] = None  # Alternative keys considered
    dynamic_fields: Optional[List[str]] = None  # Fields excluded from caching
    content_hash: Optional[str] = None  # Hash of cacheable content
    ttl_seconds: Optional[int] = None  # Time-to-live for cache entry
    
    @field_validator('similarity_score')
    @classmethod
    def similarity_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Similarity score must be between 0 and 1')
        return v


# =============================================================================
# QUALITY EVALUATION (EXTENDED)
# =============================================================================

class QualityEvaluation(BaseModel):
    """Quality evaluation from LLM Judge"""
    judge_score: Optional[float] = None
    hallucination_flag: bool = False
    error_category: Optional[str] = None
    reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # NEW: Extended quality fields
    judge_model: Optional[str] = None  # Model used for judging
    failure_reason: Optional[str] = None  # HALLUCINATION, FACTUAL_ERROR, VERY_LOW_QUALITY, LOW_QUALITY
    improvement_suggestion: Optional[str] = None  # Auto-generated fix suggestion
    hallucination_details: Optional[str] = None  # What specifically was hallucinated
    evidence_cited: Optional[bool] = None  # Whether response cited sources
    factual_error: Optional[bool] = None  # Whether factual error detected
    criteria_scores: Optional[Dict[str, float]] = None  # Individual criteria scores
    
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
# PROMPT BREAKDOWN (NEW)
# =============================================================================

class PromptBreakdown(BaseModel):
    """
    Structured breakdown of prompt components.
    
    Used by:
    - Model Router: View token consumption by component
    - Prompt Optimizer: Find optimization opportunities
    """
    # System prompt
    system_prompt: Optional[str] = None  # First 1000 chars
    system_prompt_tokens: Optional[int] = None
    
    # Chat history
    chat_history: Optional[List[Dict]] = None  # Message list
    chat_history_tokens: Optional[int] = None
    chat_history_count: Optional[int] = None  # Number of messages
    
    # User message (current query)
    user_message: Optional[str] = None  # First 500 chars
    user_message_tokens: Optional[int] = None
    
    # Response (for quality analysis)
    response_text: Optional[str] = None  # First 1000 chars


# =============================================================================
# PROMPT METADATA (NEW)
# =============================================================================

class PromptMetadata(BaseModel):
    """
    Metadata for prompt tracking and optimization.
    
    Used by:
    - Prompt Optimizer: Track template versions
    - Impact Tracker: Attribute changes to prompt updates
    """
    prompt_template_id: Optional[str] = None  # e.g., "job_match_v2"
    prompt_version: Optional[str] = None      # e.g., "1.2.0" (manual label)
    prompt_hash: Optional[str] = None         # NEW: Auto-generated from prompt prefix
    experiment_id: Optional[str] = None       # NEW: A/B test grouping
    compressible_sections: Optional[List[str]] = None
    optimization_flags: Optional[Dict[str, bool]] = None
    config_version: Optional[str] = None

# =============================================================================
# LLM CALL (EXTENDED)
# =============================================================================

class LLMCall(BaseModel):
    id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Model info
    provider: ModelProvider
    model_name: str
    
    # Request details
    prompt: Optional[str] = None
    prompt_normalized: Optional[str] = None
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
    
    # Enhanced fields - Routing
    routing_decision: Optional[RoutingDecision] = None
    
    # Enhanced fields - Caching
    cache_metadata: Optional[CacheMetadata] = None
    
    # Enhanced fields - Quality
    quality_evaluation: Optional[QualityEvaluation] = None
    
    # NEW: Enhanced fields - Prompt Analysis
    prompt_breakdown: Optional[PromptBreakdown] = None
    prompt_metadata: Optional[PromptMetadata] = None
    
    # Enhanced fields - Prompt Variants (for A/B testing)
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


# =============================================================================
# SESSION (unchanged)
# =============================================================================

class Session(BaseModel):
    id: str
    project_name: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Aggregated metrics
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    
    # Enhanced aggregated metrics - Routing
    total_routing_decisions: int = 0
    routing_cost_savings: float = 0.0
    
    # Enhanced aggregated metrics - Caching
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    cache_cost_savings: float = 0.0
    
    # Enhanced aggregated metrics - Quality
    avg_quality_score: Optional[float] = None
    total_hallucinations: int = 0
    total_errors: int = 0
    
    # Status
    success: bool = True
    error: Optional[str] = None
    
    # Context
    operation_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Calls in this session
    llm_calls: List[LLMCall] = Field(default_factory=list)
    
    @field_validator('total_llm_calls', 'total_tokens', 'total_routing_decisions', 
               'total_cache_hits', 'total_cache_misses', 'total_hallucinations', 'total_errors')
    @classmethod
    def counts_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Count metrics cannot be negative')
        return v
    
    @field_validator('total_cost', 'total_latency_ms', 'routing_cost_savings', 'cache_cost_savings')
    @classmethod
    def aggregated_metrics_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Aggregated metrics cannot be negative')
        return v
    
    @field_validator('avg_quality_score')
    @classmethod
    def avg_quality_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Average quality score must be between 0 and 10')
        return v


# =============================================================================
# BREAKDOWN MODELS (unchanged)
# =============================================================================

class CostBreakdown(BaseModel):
    total_cost: float
    by_model: Dict[str, float]
    by_provider: Dict[str, float]
    by_agent: Dict[str, float]
    by_operation: Dict[str, float]


class LatencyBreakdown(BaseModel):
    total_latency_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    by_agent: Dict[str, float]
    by_operation: Dict[str, float]


class TokenBreakdown(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    by_model: Dict[str, int]
    by_agent: Dict[str, int]


class QualityMetrics(BaseModel):
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_tokens_per_call: float
    cache_hit_rate: Optional[float] = None
    avg_quality_score: Optional[float] = None
    hallucination_rate: Optional[float] = None
    
    @field_validator('total_calls', 'successful_calls', 'failed_calls')
    @classmethod
    def counts_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Call counts cannot be negative')
        return v
    
    @field_validator('success_rate', 'cache_hit_rate', 'hallucination_rate')
    @classmethod
    def rates_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Rates must be between 0 and 1')
        return v
    
    @field_validator('avg_quality_score')
    @classmethod
    def quality_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Average quality score must be between 0 and 10')
        return v
    
    @field_validator('avg_tokens_per_call')
    @classmethod
    def avg_tokens_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Average tokens per call cannot be negative')
        return v


class RoutingMetrics(BaseModel):
    """Routing effectiveness metrics"""
    total_routing_decisions: int
    routing_accuracy: Optional[float] = None
    avg_cost_per_route: float
    total_cost_savings: float
    model_distribution: Dict[str, int]
    avg_complexity_score: Optional[float] = None
    
    @field_validator('total_routing_decisions')
    @classmethod
    def decisions_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Total routing decisions cannot be negative')
        return v
    
    @field_validator('routing_accuracy')
    @classmethod
    def accuracy_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Routing accuracy must be between 0 and 1')
        return v
    
    @field_validator('avg_cost_per_route', 'total_cost_savings')
    @classmethod
    def costs_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Cost metrics cannot be negative')
        return v
    
    @field_validator('avg_complexity_score')
    @classmethod
    def complexity_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Average complexity score must be between 0 and 1')
        return v


class CacheMetrics(BaseModel):
    """Cache performance metrics"""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    tokens_saved: int
    cost_saved: float
    latency_saved_ms: float
    cluster_count: Optional[int] = None
    
    @field_validator('total_requests', 'cache_hits', 'cache_misses', 'tokens_saved')
    @classmethod
    def counts_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Cache counts cannot be negative')
        return v
    
    @field_validator('hit_rate')
    @classmethod
    def hit_rate_must_be_valid(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Hit rate must be between 0 and 1')
        return v
    
    @field_validator('cost_saved', 'latency_saved_ms')
    @classmethod
    def savings_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Savings metrics cannot be negative')
        return v
    
    @field_validator('cluster_count')
    @classmethod
    def cluster_count_must_be_valid(cls, v):
        if v is not None and v < 0:
            raise ValueError('Cluster count cannot be negative')
        return v


class SessionReport(BaseModel):
    session: Session
    cost_breakdown: CostBreakdown
    latency_breakdown: LatencyBreakdown
    token_breakdown: TokenBreakdown
    quality_metrics: QualityMetrics
    routing_metrics: Optional[RoutingMetrics] = None
    cache_metrics: Optional[CacheMetrics] = None
    optimization_suggestions: List[str] = Field(default_factory=list)


class OptimizationSuggestion(BaseModel):
    type: str  # "cost", "latency", "quality", "routing", "caching"
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    potential_savings: Optional[float] = None
    potential_speedup: Optional[float] = None
    effort: str  # "low", "medium", "high"
    risk: str  # "low", "medium", "high"
    implementation_hint: Optional[str] = None