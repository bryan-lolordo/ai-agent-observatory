"""
Dashboard Models
Location: api/models/dashboard.py

Models for dashboard configuration and widgets.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class WidgetConfig(BaseModel):
    """Dashboard widget configuration."""
    id: str
    type: Literal["story_card", "chart", "metric", "table", "alert_list"]
    
    # Data source
    story_id: Optional[str] = None
    metric: Optional[str] = None
    
    # Layout
    position: Dict[str, int] = Field(description="x, y, w, h for grid layout")
    
    # Settings
    settings: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval_seconds: int = Field(default=60, ge=10, le=3600)


class DashboardLayout(BaseModel):
    """Dashboard layout configuration."""
    id: str
    name: str
    description: Optional[str] = None
    
    # Widgets
    widgets: List[WidgetConfig]
    
    # Settings
    is_default: bool = False
    is_public: bool = False
    
    # Ownership
    created_by: Optional[str] = None
    team_id: Optional[str] = None


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    layout: DashboardLayout
    data: Dict[str, Any]  # widget_id -> widget_data
    last_updated: Optional[str] = None


class DashboardListResponse(BaseModel):
    """List of available dashboards."""
    dashboards: List[DashboardLayout]
    default_dashboard_id: Optional[str] = None