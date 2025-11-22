from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OTHER = "other"


class AgentRole(str, Enum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    FIXER = "fixer"
    ORCHESTRATOR = "orchestrator"
    CUSTOM = "custom"


class LLMCall(BaseModel):
    id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Model info
    provider: ModelProvider
    model_name: str
    
    # Request details
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
    
    # Optional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    
    # Status
    success: bool = True
    error: Optional[str] = None
    
    # Context
    operation_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Calls in this session
    llm_calls: List[LLMCall] = Field(default_factory=list)


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


class SessionReport(BaseModel):
    session: Session
    cost_breakdown: CostBreakdown
    latency_breakdown: LatencyBreakdown
    token_breakdown: TokenBreakdown
    quality_metrics: QualityMetrics
    optimization_suggestions: List[str] = Field(default_factory=list)


class OptimizationSuggestion(BaseModel):
    type: str  # "cost", "latency", "quality"
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    potential_savings: Optional[float] = None
    potential_speedup: Optional[float] = None
    effort: str  # "low", "medium", "high"
    risk: str  # "low", "medium", "high"
    implementation_hint: Optional[str] = None