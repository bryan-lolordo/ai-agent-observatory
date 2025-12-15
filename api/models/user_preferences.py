"""
User Preferences Models
Location: api/models/user_preferences.py

Models for user settings and team configurations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """User preferences and settings."""
    user_id: str
    
    # Defaults
    default_project: Optional[str] = None
    default_date_range_days: int = Field(default=7, ge=1, le=90)
    
    # UI preferences
    theme: str = "light"  # light, dark, auto
    default_dashboard_id: Optional[str] = None
    favorite_stories: List[str] = Field(default_factory=list)
    
    # Notifications
    notification_settings: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_alerts": True,
            "slack_alerts": False,
            "weekly_digest": True
        }
    )
    
    # Display preferences
    display_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "show_costs": True,
            "show_prompts": False,
            "compact_tables": False
        }
    )


class TeamSettings(BaseModel):
    """Team-level settings."""
    team_id: str
    team_name: str
    
    # Members
    members: List[str] = Field(default_factory=list)
    admin_users: List[str] = Field(default_factory=list)
    
    # Shared resources
    shared_dashboards: List[str] = Field(default_factory=list)
    shared_alert_rules: List[str] = Field(default_factory=list)
    
    # Budget & limits
    monthly_cost_budget: Optional[float] = None
    cost_alert_threshold_pct: float = Field(default=0.80, ge=0, le=1)
    
    # Integrations
    slack_webhook_url: Optional[str] = None
    email_addresses: List[str] = Field(default_factory=list)
    
    # Retention
    data_retention_days: int = Field(default=90, ge=7, le=365)


class UserPreferencesResponse(BaseModel):
    """User preferences response."""
    user_id: str
    preferences: UserPreferences
    team_settings: Optional[TeamSettings] = None


class UpdateUserPreferencesRequest(BaseModel):
    """Update user preferences."""
    default_project: Optional[str] = None
    default_date_range_days: Optional[int] = None
    theme: Optional[str] = None
    default_dashboard_id: Optional[str] = None
    favorite_stories: Optional[List[str]] = None
    notification_settings: Optional[Dict[str, bool]] = None
    display_settings: Optional[Dict[str, Any]] = None