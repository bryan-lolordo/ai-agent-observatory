"""
Story Response Models
Location: api/models/story_responses.py

Pydantic models for story API responses.
Defines the contract between backend and frontend.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# =============================================================================
# SHARED MODELS
# =============================================================================

class TopOffender(BaseModel):
    """Top offending operation in a story."""
    agent: str
    operation: str
    value: float  # The primary metric (latency_ms, cost, ratio, etc.)
    value_formatted: str  # Human-readable version
    call_count: int
    diagnosis: Optional[str] = None  # Story-specific insight


class Recommendation(BaseModel):
    """Optimization recommendation."""
    title: str
    description: str
    impact: Literal["High", "Medium", "Low"]


class ChartDataPoint(BaseModel):
    """Generic chart data point."""
    name: str
    value: float
    label: Optional[str] = None
    # Allow extra fields for specific chart types
    class Config:
        extra = "allow"


# =============================================================================
# STORY RESPONSE BASE
# =============================================================================

class StoryResponse(BaseModel):
    """Base response structure for all stories."""
    status: Literal["ok", "warning", "error"]
    health_score: float = Field(ge=0, le=100, description="0-100 health score")
    summary: Dict[str, Any]  # Story-specific metrics
    top_offender: Optional[TopOffender] = None
    detail_table: List[Dict[str, Any]]  # Rows for the detail table
    chart_data: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, str]] = Field(default_factory=list)


# =============================================================================
# STORY-SPECIFIC SUMMARY MODELS
# =============================================================================

class LatencySummary(BaseModel):
    """Summary metrics for latency story."""
    total_calls: int
    issue_count: int  # Slow operations
    total_slow_calls: int  # Total calls in slow operations
    avg_latency_ms: float
    avg_latency: str  # Formatted
    critical_count: int  # >10s
    warning_count: int  # >5s


class CacheSummary(BaseModel):
    """Summary metrics for cache story."""
    total_calls: int
    issue_count: int
    cache_hits: int
    cache_misses: int
    hit_rate: float  # 0-1
    hit_rate_formatted: str  # "45.2%"
    duplicate_prompts: int
    potential_savings: float  # Cost that could be saved


class CostSummary(BaseModel):
    """Summary metrics for cost story."""
    total_calls: int
    issue_count: int  # Operations with concentrated cost
    total_cost: float
    total_cost_formatted: str
    top_3_concentration: float  # 0-1, what % top 3 ops represent
    avg_cost_per_call: float


class SystemPromptSummary(BaseModel):
    """Summary metrics for system prompt story."""
    total_calls: int
    issue_count: int  # High system prompt token operations
    avg_system_tokens: float
    avg_total_tokens: float
    system_token_pct: float  # 0-1
    system_token_pct_formatted: str
    wasted_tokens: int  # Excess system tokens


class TokenImbalanceSummary(BaseModel):
    """Summary metrics for token imbalance story."""
    total_calls: int
    issue_count: int  # High ratio operations
    avg_prompt_tokens: float
    avg_completion_tokens: float
    avg_ratio: float  # prompt:completion ratio
    critical_count: int  # >20:1
    warning_count: int  # >10:1


class RoutingSummary(BaseModel):
    """Summary metrics for routing story."""
    total_calls: int
    issue_count: int  # Misrouted calls
    routed_calls: int  # Calls with routing decision
    high_complexity_on_cheap: int  # Complex tasks on cheap models
    low_complexity_on_expensive: int  # Simple tasks on expensive models
    potential_savings: float


class QualitySummary(BaseModel):
    """Summary metrics for quality story."""
    total_calls: int
    issue_count: int  # Failed/low-quality calls
    evaluated_calls: int
    avg_quality_score: float  # 0-1
    avg_quality_score_formatted: str  # "85.2%"
    error_count: int
    hallucination_count: int
    error_rate: float  # 0-1


# =============================================================================
# COMPLETE STORY RESPONSES (with typed summaries)
# =============================================================================

class LatencyStoryResponse(StoryResponse):
    """Latency story response."""
    summary: LatencySummary


class CacheStoryResponse(StoryResponse):
    """Cache story response."""
    summary: CacheSummary


class CostStoryResponse(StoryResponse):
    """Cost story response."""
    summary: CostSummary


class SystemPromptStoryResponse(StoryResponse):
    """System prompt story response."""
    summary: SystemPromptSummary


class TokenImbalanceStoryResponse(StoryResponse):
    """Token imbalance story response."""
    summary: TokenImbalanceSummary


class RoutingStoryResponse(StoryResponse):
    """Routing story response."""
    summary: RoutingSummary


class QualityStoryResponse(StoryResponse):
    """Quality story response."""
    summary: QualitySummary


# =============================================================================
# ALL STORIES RESPONSE
# =============================================================================

class AllStoriesResponse(BaseModel):
    """Response for GET /api/stories endpoint."""
    stories: Dict[str, StoryResponse]  # story_id -> response
    overall_health: float = Field(ge=0, le=100)
    total_calls: int
    timestamp: Optional[str] = None