"""
Optimization Tracking Models
Location: api/models/optimization.py

Models for Story 8: Optimization Impact tracking.
Includes both simple models (for current service) and complex models (for future enhancement).
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# SIMPLE MODELS (Used by optimization_service.py NOW)
# =============================================================================

class OptimizationSummary(BaseModel):
    """High-level optimization metrics summary."""
    total_optimizations: int
    total_cost_saved: float
    total_latency_reduction: float  # As percentage (e.g., 0.75 = 75%)
    avg_quality_improvement: float


class BaselineMetrics(BaseModel):
    """Baseline metrics before any optimization."""
    total_calls: int
    avg_latency_ms: float
    avg_latency: str  # Formatted (e.g., "2.5s")
    total_cost: float
    total_cost_formatted: str  # Formatted (e.g., "$4.56")
    avg_quality_score: float
    cache_hit_rate: float
    cache_hit_rate_formatted: str  # Formatted (e.g., "45%")
    error_rate: float
    error_rate_formatted: str  # Formatted (e.g., "2.1%")


class OptimizationImpactSimple(BaseModel):
    """Simplified impact measurement (used by service)."""
    id: str
    name: str
    target_operation: str
    implemented_date: datetime
    
    # Before metrics
    before_avg_latency_ms: float
    before_total_cost: float
    before_avg_quality: float
    
    # After metrics
    after_avg_latency_ms: float
    after_total_cost: float
    after_avg_quality: float
    
    # Improvements
    cost_saved: float
    latency_reduction_pct: float
    quality_improvement: float


class OptimizationStoryResponse(BaseModel):
    """Story 8 response (what optimization_service actually returns)."""
    mode: Literal["baseline", "impact"]
    status: str  # "ok", "warning", "error"
    health_score: float
    
    # Summary
    summary: OptimizationSummary
    
    # Baseline (only in baseline mode)
    baseline: Optional[BaselineMetrics] = None
    
    # Optimizations (only in impact mode)
    optimizations: List[OptimizationImpactSimple] = Field(default_factory=list)
    
    # Data tables
    detail_table: List[Dict[str, Any]] = Field(default_factory=list)
    chart_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[Dict[str, str]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "baseline",
                "status": "ok",
                "health_score": 100.0,
                "summary": {
                    "total_optimizations": 0,
                    "total_cost_saved": 0.0,
                    "total_latency_reduction": 0.0,
                    "avg_quality_improvement": 0.0
                },
                "baseline": {
                    "total_calls": 175,
                    "avg_latency_ms": 1973,
                    "avg_latency": "2.0s",
                    "total_cost": 3.64,
                    "total_cost_formatted": "$3.64",
                    "avg_quality_score": 7.4,
                    "cache_hit_rate": 0.0,
                    "cache_hit_rate_formatted": "0%",
                    "error_rate": 0.091,
                    "error_rate_formatted": "9.1%"
                },
                "optimizations": [],
                "detail_table": [],
                "chart_data": [],
                "recommendations": []
            }
        }


# =============================================================================
# COMPLEX MODELS (For future enhancement - Story 8 full implementation)
# =============================================================================

class OptimizationRecord(BaseModel):
    """Track an optimization implementation (future use)."""
    id: str
    name: str
    description: Optional[str] = None
    story_id: str
    target_operation: str
    target_agent: str
    
    # Implementation details
    implemented_date: datetime
    implemented_by: Optional[str] = None
    
    # Expected impact (predictions)
    expected_impact: Dict[str, float] = Field(
        default_factory=dict,
        description="Expected improvements (e.g., {'latency_reduction_pct': 60, 'cost_savings': 0.45})"
    )
    
    # Actual impact (measured)
    actual_impact: Optional[Dict[str, float]] = None
    
    # Optimization type
    optimization_type: Literal[
        "cache",
        "prompt_compression",
        "output_constraint",
        "model_routing",
        "sliding_window",
        "other"
    ]
    
    # Code changes
    files_changed: Optional[List[str]] = None
    code_location: Optional[str] = None
    
    # Status
    status: Literal["planned", "in_progress", "deployed", "measuring", "completed"] = "planned"
    
    # Notes
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "opt_001",
                "name": "Add output constraints to deep_analyze_job",
                "description": "Constrain output to JSON schema to reduce tokens",
                "story_id": "latency",
                "target_operation": "deep_analyze_job",
                "target_agent": "ResumeMatching",
                "implemented_date": "2024-12-14T10:00:00Z",
                "expected_impact": {
                    "latency_reduction_pct": 75,
                    "token_reduction_pct": 85,
                    "cost_savings_per_call": 0.14
                },
                "optimization_type": "output_constraint",
                "status": "deployed"
            }
        }


class BeforeAfterMetrics(BaseModel):
    """Before and after metrics for detailed comparison."""
    before_value: float
    after_value: float
    change_value: float
    change_pct: float
    improvement: bool  # True if change is positive


class OptimizationImpact(BaseModel):
    """Measured impact of an optimization (complex version for future)."""
    optimization_id: str
    
    # Metrics measured
    metrics: Dict[str, BeforeAfterMetrics]
    
    # Measurement period
    before_period_start: datetime
    before_period_end: datetime
    after_period_start: datetime
    after_period_end: datetime
    
    # Sample sizes
    before_call_count: int
    after_call_count: int
    
    # Success criteria
    achieved_goal: bool
    goal_description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "optimization_id": "opt_001",
                "metrics": {
                    "avg_latency_ms": {
                        "before_value": 10740,
                        "after_value": 2500,
                        "change_value": -8240,
                        "change_pct": -76.7,
                        "improvement": True
                    },
                    "avg_cost_per_call": {
                        "before_value": 0.273,
                        "after_value": 0.042,
                        "change_value": -0.231,
                        "change_pct": -84.6,
                        "improvement": True
                    }
                },
                "before_call_count": 3,
                "after_call_count": 8,
                "achieved_goal": True,
                "goal_description": "Reduce latency to <3s"
            }
        }


# =============================================================================
# FUTURE RESPONSE MODELS (For full Story 8 implementation)
# =============================================================================

class OptimizationListResponse(BaseModel):
    """List of optimizations (future use)."""
    optimizations: List[OptimizationRecord]
    total: int
    
    # Summary
    total_cost_savings: float
    total_latency_savings_ms: float
    
    # By status
    planned_count: int
    deployed_count: int
    completed_count: int


class OptimizationDetailResponse(BaseModel):
    """Detailed optimization with impact (future use)."""
    optimization: OptimizationRecord
    impact: Optional[OptimizationImpact] = None
    
    # Related calls (sample)
    before_calls: Optional[List[Dict[str, Any]]] = None
    after_calls: Optional[List[Dict[str, Any]]] = None
    
    # Time series (show trend)
    metric_history: Optional[List[Dict[str, Any]]] = None


class OptimizationSummaryResponse(BaseModel):
    """High-level optimization summary (future use - different from OptimizationStoryResponse)."""
    total_optimizations: int
    total_savings: Dict[str, float]  # {cost: 1.23, latency_ms: 5000}
    avg_improvement_pct: Dict[str, float]
    
    # By story
    by_story: Dict[str, int]  # story_id -> count
    
    # By type
    by_type: Dict[str, int]  # optimization_type -> count


# =============================================================================
# CREATE/UPDATE MODELS (Future use)
# =============================================================================

class CreateOptimizationRequest(BaseModel):
    """Request to create new optimization."""
    name: str
    description: Optional[str] = None
    story_id: str
    target_operation: str
    target_agent: str
    optimization_type: str
    expected_impact: Dict[str, float] = Field(default_factory=dict)
    notes: Optional[str] = None


class UpdateOptimizationRequest(BaseModel):
    """Request to update optimization."""
    status: Optional[str] = None
    actual_impact: Optional[Dict[str, float]] = None
    notes: Optional[str] = None