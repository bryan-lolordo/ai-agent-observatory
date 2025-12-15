"""
Alerts Models
Location: api/models/alerts.py

Models for alerting system.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# ALERT RULE
# =============================================================================

class AlertRule(BaseModel):
    """Alert threshold rule."""
    id: str
    name: str
    description: Optional[str] = None
    
    # What to monitor
    story_id: str
    metric: str
    
    # Threshold
    threshold: float
    operator: Literal["gt", "lt", "gte", "lte", "eq"]
    
    # Settings
    severity: Literal["critical", "warning", "info"] = "warning"
    enabled: bool = True
    
    # Notification
    notification_channels: List[str] = Field(default_factory=list)  # ["email", "slack"]
    
    # Timing
    evaluation_interval_minutes: int = Field(default=5, ge=1, le=1440)
    
    # Created/updated
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None


# =============================================================================
# ALERT
# =============================================================================

class Alert(BaseModel):
    """Triggered alert."""
    id: str
    rule_id: str
    rule_name: str
    story_id: str
    
    # Alert details
    severity: Literal["critical", "warning", "info"]
    message: str
    metric: str
    current_value: float
    threshold_value: float
    
    # Status
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    
    # Context
    affected_operations: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# RESPONSES
# =============================================================================

class AlertsResponse(BaseModel):
    """List of active alerts."""
    alerts: List[Alert]
    
    # Summary
    total: int
    critical_count: int
    warning_count: int
    info_count: int
    unacknowledged_count: int


class AlertRulesResponse(BaseModel):
    """List of alert rules."""
    rules: List[AlertRule]
    total: int
    enabled_count: int
    disabled_count: int


# =============================================================================
# CREATE/UPDATE
# =============================================================================

class CreateAlertRuleRequest(BaseModel):
    """Create new alert rule."""
    name: str
    description: Optional[str] = None
    story_id: str
    metric: str
    threshold: float
    operator: Literal["gt", "lt", "gte", "lte", "eq"]
    severity: Literal["critical", "warning", "info"] = "warning"
    notification_channels: List[str] = Field(default_factory=list)


class AcknowledgeAlertRequest(BaseModel):
    """Acknowledge an alert."""
    note: Optional[str] = None