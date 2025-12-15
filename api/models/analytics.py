"""
Analytics Models
Location: api/models/analytics.py

Models for advanced analytics, time series, and trend analysis.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# TIME SERIES
# =============================================================================

class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""
    timestamp: datetime
    value: float
    label: Optional[str] = None
    
    # Optional breakdown
    breakdown: Optional[Dict[str, float]] = None


class TimeSeriesResponse(BaseModel):
    """Time series data."""
    metric: str
    aggregation: Literal["hour", "day", "week"]
    data_points: List[TimeSeriesDataPoint]
    
    # Summary stats
    min_value: float
    max_value: float
    avg_value: float
    total_value: Optional[float] = None
    
    # Metadata
    start_date: datetime
    end_date: datetime
    point_count: int
    
    class Config:
        schema_extra = {
            "example": {
                "metric": "total_cost",
                "aggregation": "day",
                "data_points": [
                    {
                        "timestamp": "2024-12-14T00:00:00Z",
                        "value": 0.52,
                        "label": "Dec 14"
                    }
                ],
                "min_value": 0.32,
                "max_value": 0.89,
                "avg_value": 0.52,
                "total_value": 3.64,
                "start_date": "2024-12-07T00:00:00Z",
                "end_date": "2024-12-14T00:00:00Z",
                "point_count": 7
            }
        }


class MultiSeriesResponse(BaseModel):
    """Multiple time series (for comparison)."""
    metric: str
    series: Dict[str, List[TimeSeriesDataPoint]]  # series_name -> data_points
    aggregation: Literal["hour", "day", "week"]
    
    class Config:
        schema_extra = {
            "example": {
                "metric": "avg_latency_ms",
                "series": {
                    "DatabaseQuery": [],
                    "ResumeMatching": []
                },
                "aggregation": "day"
            }
        }


# =============================================================================
# TREND ANALYSIS
# =============================================================================

class TrendAnalysis(BaseModel):
    """Trend detection and analysis."""
    metric: str
    trend: Literal["improving", "degrading", "stable", "volatile"]
    direction: Literal["up", "down", "flat"]
    
    # Quantitative measures
    slope: float  # Rate of change
    r_squared: Optional[float] = Field(None, ge=0, le=1, description="Goodness of fit")
    confidence: float = Field(ge=0, le=1, description="Confidence in trend")
    
    # Change statistics
    change_pct: float
    change_value: float
    
    # Period
    period_days: int
    data_points: int
    
    class Config:
        schema_extra = {
            "example": {
                "metric": "total_cost",
                "trend": "improving",
                "direction": "down",
                "slope": -0.05,
                "r_squared": 0.87,
                "confidence": 0.85,
                "change_pct": -15.3,
                "change_value": -0.68,
                "period_days": 7,
                "data_points": 7
            }
        }


class MultiTrendResponse(BaseModel):
    """Trends for multiple metrics."""
    trends: Dict[str, TrendAnalysis]  # metric -> trend
    overall_health_trend: Literal["improving", "degrading", "stable"]


# =============================================================================
# COMPARISON METRICS
# =============================================================================

class PeriodMetrics(BaseModel):
    """Metrics for a specific period."""
    start_date: datetime
    end_date: datetime
    call_count: int
    total_cost: float
    avg_cost_per_call: float
    avg_latency_ms: float
    avg_quality_score: Optional[float] = None
    error_rate: float


class ComparisonMetrics(BaseModel):
    """Compare two time periods."""
    current: PeriodMetrics
    previous: PeriodMetrics
    
    # Changes
    changes: Dict[str, float]  # metric -> percentage change
    
    # Significance
    is_significant: bool
    significance_level: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "current": {
                    "start_date": "2024-12-07T00:00:00Z",
                    "end_date": "2024-12-14T00:00:00Z",
                    "call_count": 175,
                    "total_cost": 3.64,
                    "avg_cost_per_call": 0.021,
                    "avg_latency_ms": 1973,
                    "error_rate": 0.091
                },
                "previous": {
                    "start_date": "2024-11-30T00:00:00Z",
                    "end_date": "2024-12-07T00:00:00Z",
                    "call_count": 150,
                    "total_cost": 4.20,
                    "avg_cost_per_call": 0.028,
                    "avg_latency_ms": 2450,
                    "error_rate": 0.120
                },
                "changes": {
                    "total_cost": -13.3,
                    "avg_latency_ms": -19.5,
                    "error_rate": -24.2
                },
                "is_significant": True
            }
        }


# =============================================================================
# DISTRIBUTION ANALYSIS
# =============================================================================

class DistributionBucket(BaseModel):
    """Bucket in a distribution histogram."""
    min_value: float
    max_value: float
    count: int
    percentage: float
    label: str


class DistributionAnalysis(BaseModel):
    """Distribution analysis for a metric."""
    metric: str
    buckets: List[DistributionBucket]
    
    # Statistics
    mean: float
    median: float
    std_dev: float
    p50: float
    p90: float
    p95: float
    p99: float
    
    class Config:
        schema_extra = {
            "example": {
                "metric": "latency_ms",
                "buckets": [
                    {
                        "min_value": 0,
                        "max_value": 1000,
                        "count": 85,
                        "percentage": 48.6,
                        "label": "0-1s"
                    },
                    {
                        "min_value": 1000,
                        "max_value": 5000,
                        "count": 72,
                        "percentage": 41.1,
                        "label": "1-5s"
                    }
                ],
                "mean": 1973,
                "median": 976,
                "std_dev": 3254,
                "p50": 976,
                "p90": 5214,
                "p95": 6214,
                "p99": 15890
            }
        }


# =============================================================================
# CORRELATION ANALYSIS
# =============================================================================

class CorrelationPair(BaseModel):
    """Correlation between two metrics."""
    metric1: str
    metric2: str
    correlation: float = Field(ge=-1, le=1)
    strength: Literal["strong", "moderate", "weak", "none"]
    relationship: str  # Human-readable description


class CorrelationMatrix(BaseModel):
    """Correlation matrix for multiple metrics."""
    metrics: List[str]
    correlations: List[CorrelationPair]
    
    # Interesting findings
    strong_correlations: List[CorrelationPair]