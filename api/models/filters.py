"""
Filter Models
Location: api/models/filters.py

Query parameter models for filtering data.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta


# =============================================================================
# DATE RANGE FILTERS
# =============================================================================

class DateRangeFilter(BaseModel):
    """Date range filtering."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Convenience fields
    last_hours: Optional[int] = Field(None, gt=0, le=720)  # Max 30 days
    last_days: Optional[int] = Field(None, gt=0, le=90)    # Max 90 days
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        """Ensure end_date is after start_date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    def get_datetime_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Convert to actual datetime range."""
        if self.start_date and self.end_date:
            return self.start_date, self.end_date
        
        end = datetime.utcnow()
        
        if self.last_hours:
            start = end - timedelta(hours=self.last_hours)
            return start, end
        
        if self.last_days:
            start = end - timedelta(days=self.last_days)
            return start, end
        
        # Default: last 7 days
        start = end - timedelta(days=7)
        return start, end


# =============================================================================
# LLM CALL FILTERS
# =============================================================================

class CallFilters(BaseModel):
    """Filters for querying LLM calls."""
    # Identity filters
    project_name: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Operation filters
    agent_name: Optional[str] = None
    operation: Optional[str] = None
    model_name: Optional[str] = None
    
    # Status filters
    success_only: Optional[bool] = None
    has_error: Optional[bool] = None
    
    # Feature filters
    has_quality_eval: Optional[bool] = None
    has_routing: Optional[bool] = None
    has_cache: Optional[bool] = None
    cache_hit: Optional[bool] = None
    
    # Experiment filters
    experiment_id: Optional[str] = None
    control_group: Optional[bool] = None
    
    # Date range
    date_range: Optional[DateRangeFilter] = Field(default_factory=DateRangeFilter)
    
    # Pagination
    limit: int = Field(default=1000, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)
    
    # Sorting
    sort_by: Optional[Literal[
        "timestamp",
        "latency_ms",
        "total_cost",
        "total_tokens",
        "quality_score"
    ]] = "timestamp"
    sort_order: Literal["asc", "desc"] = "desc"


# =============================================================================
# STORY FILTERS
# =============================================================================

class StoryFilters(BaseModel):
    """Filters for story analysis."""
    project_name: Optional[str] = None
    date_range: Optional[DateRangeFilter] = Field(default_factory=DateRangeFilter)
    
    # Story-specific filters
    min_calls: int = Field(default=10, ge=1)
    include_zero_issues: bool = True
    
    # Threshold overrides
    latency_threshold_ms: Optional[float] = Field(None, gt=0)
    cache_redundancy_threshold: Optional[float] = Field(None, ge=0, le=1)
    cost_concentration_threshold: Optional[float] = Field(None, ge=0, le=1)
    quality_threshold: Optional[float] = Field(None, ge=0, le=10)


# =============================================================================
# OPERATION FILTERS
# =============================================================================

class OperationFilters(BaseModel):
    """Filters for operation-level analysis."""
    project_name: Optional[str] = None
    agent_name: Optional[str] = None
    operation: str
    date_range: Optional[DateRangeFilter] = Field(default_factory=DateRangeFilter)
    limit: int = Field(default=1000, ge=1, le=5000)


# =============================================================================
# ANALYTICS FILTERS
# =============================================================================

class TimeSeriesFilters(BaseModel):
    """Filters for time series data."""
    project_name: Optional[str] = None
    metric: Literal[
        "cost",
        "latency",
        "tokens",
        "calls",
        "errors",
        "quality_score"
    ]
    aggregation: Literal["hour", "day", "week"] = "day"
    date_range: Optional[DateRangeFilter] = Field(default_factory=DateRangeFilter)
    
    # Grouping
    group_by: Optional[Literal["agent", "operation", "model"]] = None


class ComparisonFilters(BaseModel):
    """Filters for comparing two periods."""
    project_name: Optional[str] = None
    current_period: DateRangeFilter
    comparison_period: Optional[DateRangeFilter] = None  # Auto-calculated if None
    metrics: List[str] = Field(default_factory=lambda: ["cost", "latency", "quality"])


# =============================================================================
# EXPORT FILTERS
# =============================================================================

class ExportFilters(BaseModel):
    """Filters for data export."""
    story_id: Optional[str] = None
    project_name: Optional[str] = None
    date_range: Optional[DateRangeFilter] = Field(default_factory=DateRangeFilter)
    
    # Export options
    format: Literal["xlsx", "csv", "json"] = "xlsx"
    include_prompts: bool = False
    include_responses: bool = False
    max_rows: int = Field(default=10000, ge=1, le=100000)