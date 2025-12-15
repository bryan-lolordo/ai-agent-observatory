"""
Batch Operations Models
Location: api/models/batch.py

Models for batch operations and exports.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class BatchExportRequest(BaseModel):
    """Request to export multiple stories."""
    story_ids: List[str]
    format: Literal["xlsx", "csv", "json"] = "xlsx"
    include_prompts: bool = False
    include_responses: bool = False
    date_range: Optional[Dict[str, datetime]] = None
    project_name: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    """Request to analyze multiple operations."""
    operations: List[str]
    metrics: List[str] = Field(default_factory=lambda: ["latency", "cost", "quality"])
    project_name: Optional[str] = None
    date_range: Optional[Dict[str, datetime]] = None


class BatchOperationResponse(BaseModel):
    """Batch operation result."""
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: float = Field(ge=0, le=1, description="0-1 progress")
    
    # Results (when completed)
    results: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error info
    error: Optional[str] = None


class ExportResponse(BaseModel):
    """Export file response."""
    file_id: str
    format: str
    size_bytes: int
    download_url: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)