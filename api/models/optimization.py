"""
Optimization Tracking Models
Location: api/models/optimization.py

Models for Story 8: Optimization Impact tracking.
Supports the hierarchical expandable rows view:
  Agent → Operation → Story → Fixes → Calls
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# STORY ICONS & METADATA
# =============================================================================

STORY_METADATA = {
    "latency": {"icon": "🌐", "color": "purple", "unit": "s", "lower_is_better": True},
    "cache": {"icon": "💾", "color": "pink", "unit": "$", "lower_is_better": True},
    "cost": {"icon": "💰", "color": "orange", "unit": "$", "lower_is_better": True},
    "quality": {"icon": "❌", "color": "red", "unit": "score", "lower_is_better": False},
    "routing": {"icon": "🔀", "color": "blue", "unit": "$", "lower_is_better": True},
    "token": {"icon": "⚖️", "color": "green", "unit": "ratio", "lower_is_better": True},
    "prompt": {"icon": "📝", "color": "yellow", "unit": "%", "lower_is_better": True},
}


# =============================================================================
# APPLIED FIX MODEL
# =============================================================================

class AppliedFix(BaseModel):
    """A single fix applied to an optimization story."""
    id: str
    optimization_story_id: str
    fix_type: str  # "max_tokens", "truncate_hist", "semantic_cache", etc.

    # Before/After for THIS fix
    before_value: float
    after_value: Optional[float] = None
    improvement_pct: Optional[float] = None

    # Tracking
    applied_date: datetime
    git_commit: Optional[str] = None
    notes: Optional[str] = None

    created_at: Optional[datetime] = None


class AppliedFixCreate(BaseModel):
    """Request to create an applied fix."""
    optimization_story_id: str
    fix_type: str
    before_value: float
    after_value: Optional[float] = None
    applied_date: Optional[datetime] = None
    git_commit: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# CALL REFERENCE MODEL (for expandable rows)
# =============================================================================

class CallReference(BaseModel):
    """Reference to a call that triggered an optimization opportunity."""
    id: str
    metric_value: float  # The specific metric value for this call
    metric_formatted: str  # Formatted display (e.g., "118s", "$0.24")
    timestamp: Optional[datetime] = None


# =============================================================================
# OPTIMIZATION STORY MODEL (the main tracking unit)
# =============================================================================

class OptimizationStory(BaseModel):
    """
    An optimization opportunity at the (Agent, Operation, Story) level.
    This is the main tracking unit for the hierarchical view.
    """
    id: str

    # Hierarchy identifiers
    agent_name: str
    operation: str
    story_id: str  # "latency", "cache", "cost", etc.

    # Story display info
    story_icon: str = ""
    story_color: str = ""

    # Call information
    call_count: int = 0
    call_ids: List[str] = Field(default_factory=list)
    calls: List[CallReference] = Field(default_factory=list)  # Populated on expand

    # Baseline metrics
    baseline_value: float
    baseline_value_formatted: str = ""
    baseline_unit: str = ""
    baseline_p95: Optional[float] = None
    baseline_p95_formatted: Optional[str] = None
    baseline_date: Optional[datetime] = None
    baseline_call_count: int = 0

    # Current metrics
    current_value: Optional[float] = None
    current_value_formatted: Optional[str] = None
    current_date: Optional[datetime] = None
    improvement_pct: Optional[float] = None
    improvement_formatted: Optional[str] = None

    # Status
    status: str = "pending"  # pending, in_progress, complete, skipped
    skip_reason: Optional[str] = None

    # Applied fixes
    fixes: List[AppliedFix] = Field(default_factory=list)
    fix_count: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OptimizationStoryCreate(BaseModel):
    """Request to create an optimization story (usually auto-generated)."""
    agent_name: str
    operation: str
    story_id: str
    call_count: int = 0
    call_ids: List[str] = Field(default_factory=list)
    baseline_value: float
    baseline_unit: str
    baseline_p95: Optional[float] = None
    baseline_date: Optional[datetime] = None
    baseline_call_count: int = 0


class OptimizationStoryUpdate(BaseModel):
    """Request to update an optimization story status."""
    status: Optional[str] = None
    skip_reason: Optional[str] = None
    current_value: Optional[float] = None


# =============================================================================
# OPERATION LEVEL (groups stories under an operation)
# =============================================================================

class OperationNode(BaseModel):
    """An operation with its optimization stories."""
    operation: str
    call_count: int = 0
    stories: List[OptimizationStory] = Field(default_factory=list)

    # Aggregate status
    total_stories: int = 0
    pending_count: int = 0
    complete_count: int = 0


# =============================================================================
# AGENT LEVEL (top of hierarchy)
# =============================================================================

class AgentNode(BaseModel):
    """An agent with its operations and optimization stories."""
    agent_name: str
    call_count: int = 0
    operations: List[OperationNode] = Field(default_factory=list)

    # Aggregate status
    total_stories: int = 0
    pending_count: int = 0
    complete_count: int = 0


# =============================================================================
# HIERARCHICAL RESPONSE (the full tree)
# =============================================================================

class OptimizationHierarchy(BaseModel):
    """
    The full hierarchical view for the expandable rows table.

    Structure:
      agents[]
        └── operations[]
              └── stories[]
                    ├── fixes[]
                    └── calls[]
    """
    agents: List[AgentNode] = Field(default_factory=list)

    # Summary stats
    total_agents: int = 0
    total_operations: int = 0
    total_stories: int = 0
    total_pending: int = 0
    total_complete: int = 0

    # Overall impact
    total_improvement_pct: Optional[float] = None
    total_cost_saved: Optional[float] = None
    total_latency_saved_ms: Optional[float] = None


# =============================================================================
# API RESPONSE MODELS
# =============================================================================

class OptimizationSummaryResponse(BaseModel):
    """Summary response for the optimization story page."""
    status: str  # "ok", "warning", "error"
    health_score: float

    # Hierarchy data
    hierarchy: OptimizationHierarchy

    # KPIs (overall metrics)
    kpis: Dict[str, Any] = Field(default_factory=dict)

    # Mode indicator
    mode: str = "tracking"  # "baseline" (old) or "tracking" (new)


class OptimizationDetailResponse(BaseModel):
    """Detailed response for a single optimization story."""
    story: OptimizationStory
    fixes: List[AppliedFix] = Field(default_factory=list)
    calls: List[CallReference] = Field(default_factory=list)

    # Metric history for chart
    metric_history: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_metric(value: float, unit: str) -> str:
    """Format a metric value with its unit."""
    if unit == "s":
        return f"{value:.1f}s"
    elif unit == "$":
        return f"${value:.2f}"
    elif unit == "%":
        return f"{value:.0f}%"
    elif unit == "ratio":
        return f"{value:.0f}:1"
    elif unit == "score":
        return f"{value:.1f}/10"
    else:
        return f"{value:.2f}"


def format_improvement(baseline: float, current: float, lower_is_better: bool = True) -> str:
    """Format the improvement percentage."""
    if baseline == 0:
        return "—"

    change_pct = ((baseline - current) / baseline) * 100

    if lower_is_better:
        # For latency/cost, negative change is good
        if change_pct > 0:
            return f"-{change_pct:.0f}%"
        else:
            return f"+{abs(change_pct):.0f}%"
    else:
        # For quality, positive change is good
        if change_pct < 0:
            return f"+{abs(change_pct):.0f}%"
        else:
            return f"-{change_pct:.0f}%"


def get_story_metadata(story_id: str) -> Dict[str, Any]:
    """Get icon and color for a story type."""
    return STORY_METADATA.get(story_id, {"icon": "❓", "color": "gray", "unit": "", "lower_is_better": True})
