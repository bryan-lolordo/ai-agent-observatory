"""
Webhooks Models
Location: api/models/webhooks.py

Models for webhooks and external integrations.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class WebhookConfig(BaseModel):
    """Webhook configuration."""
    id: str
    name: str
    description: Optional[str] = None
    
    # Endpoint
    url: str
    method: Literal["POST", "PUT"] = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    secret: Optional[str] = None
    
    # Events to trigger on
    events: List[str] = Field(
        default_factory=list,
        description="Events like 'alert.triggered', 'optimization.completed'"
    )
    
    # Filters
    story_ids: Optional[List[str]] = None  # Only trigger for specific stories
    severity_levels: Optional[List[str]] = None  # critical, warning, info
    
    # Settings
    enabled: bool = True
    retry_on_failure: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    last_triggered_at: Optional[datetime] = None


class WebhookDelivery(BaseModel):
    """Webhook delivery log."""
    id: str
    webhook_id: str
    webhook_name: str
    
    # Event info
    event: str
    payload: Dict[str, Any]
    
    # Delivery attempt
    attempt_number: int = 1
    delivered_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Response
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    
    # Status
    success: bool
    duration_ms: Optional[float] = None


class WebhookEvent(BaseModel):
    """Webhook event payload."""
    event: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]
    
    # Metadata
    source: str = "observatory"
    version: str = "1.0"


class WebhookListResponse(BaseModel):
    """List of webhooks."""
    webhooks: List[WebhookConfig]
    total: int
    enabled_count: int


class WebhookDeliveryListResponse(BaseModel):
    """List of webhook deliveries."""
    deliveries: List[WebhookDelivery]
    total: int
    success_count: int
    failed_count: int


class CreateWebhookRequest(BaseModel):
    """Create new webhook."""
    name: str
    description: Optional[str] = None
    url: str
    events: List[str]
    secret: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class TestWebhookResponse(BaseModel):
    """Test webhook delivery response."""
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float