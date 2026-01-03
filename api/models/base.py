"""
Base Response Models
Location: api/models/base.py

Core Pydantic models for all API responses.
"""

from typing import Optional, Dict, Any, List, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# GENERIC RESPONSE WRAPPER
# =============================================================================

class BaseResponse(BaseModel):
    """Standard API response wrapper."""
    status: str = "ok"
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# ERROR RESPONSES
# =============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = None
    message: str
    error_code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    message: str
    error_type: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Story not found",
                "error_type": "StoryNotFoundError",
                "details": [{"field": "story_id", "message": "Invalid story ID: invalid_story"}],
                "timestamp": "2024-12-14T10:30:00Z"
            }
        }


# =============================================================================
# PAGINATED RESPONSES
# =============================================================================

T = TypeVar('T')

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    page: int = 1
    page_size: int = 100
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    pagination: PaginationMeta
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "pagination": {
                    "total": 175,
                    "page": 1,
                    "page_size": 100,
                    "total_pages": 2,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }


# =============================================================================
# HEALTH CHECK
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = "connected"
    uptime_seconds: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "1.0.0",
                "timestamp": "2024-12-14T10:30:00Z",
                "database": "connected",
                "uptime_seconds": 3600.5
            }
        }


# =============================================================================
# SUCCESS RESPONSES
# =============================================================================

class SuccessResponse(BaseModel):
    """Simple success response."""
    status: str = "ok"
    message: str
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "message": "Operation completed successfully",
                "data": {"id": "123"}
            }
        }


class CreatedResponse(BaseModel):
    """Resource created response."""
    status: str = "created"
    message: str
    id: str
    resource_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "created",
                "message": "Optimization created",
                "id": "opt_123",
                "resource_url": "/api/optimizations/opt_123"
            }
        }


class DeletedResponse(BaseModel):
    """Resource deleted response."""
    status: str = "deleted"
    message: str
    id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "deleted",
                "message": "Alert deleted successfully",
                "id": "alert_456"
            }
        }