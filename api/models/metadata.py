"""
Metadata Response Models
Location: api/models/metadata.py

Models for metadata lists (projects, models, agents, operations).
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


# =============================================================================
# METADATA ITEMS
# =============================================================================

class ProjectMetadata(BaseModel):
    """Project metadata."""
    name: str
    call_count: int
    total_cost: float
    last_activity: Optional[str] = None  # ISO datetime


class ModelMetadata(BaseModel):
    """Model metadata."""
    name: str
    provider: str
    call_count: int
    total_cost: float
    avg_latency_ms: float


class AgentMetadata(BaseModel):
    """Agent metadata."""
    name: str
    operation_count: int
    call_count: int
    total_cost: float
    avg_latency_ms: float


class OperationMetadata(BaseModel):
    """Operation metadata."""
    name: str
    agent: str
    call_count: int
    total_cost: float
    avg_latency_ms: float
    avg_quality_score: Optional[float] = None


# =============================================================================
# LIST RESPONSES
# =============================================================================

class ProjectsResponse(BaseModel):
    """List of projects."""
    projects: List[ProjectMetadata]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "projects": [
                    {
                        "name": "career_copilot",
                        "call_count": 175,
                        "total_cost": 3.64,
                        "last_activity": "2024-12-14T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class ModelsResponse(BaseModel):
    """List of models."""
    models: List[ModelMetadata]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "models": [
                    {
                        "name": "gpt-4o-mini",
                        "provider": "AZURE",
                        "call_count": 175,
                        "total_cost": 3.64,
                        "avg_latency_ms": 1973
                    }
                ],
                "total": 1
            }
        }


class AgentsResponse(BaseModel):
    """List of agents."""
    agents: List[AgentMetadata]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "agents": [
                    {
                        "name": "DatabaseQuery",
                        "operation_count": 3,
                        "call_count": 45,
                        "total_cost": 0.89,
                        "avg_latency_ms": 850
                    }
                ],
                "total": 6
            }
        }


class OperationsResponse(BaseModel):
    """List of operations."""
    operations: List[OperationMetadata]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "operations": [
                    {
                        "name": "generate_sql",
                        "agent": "DatabaseQuery",
                        "call_count": 45,
                        "total_cost": 0.45,
                        "avg_latency_ms": 800,
                        "avg_quality_score": 8.5
                    }
                ],
                "total": 23
            }
        }


# =============================================================================
# STATISTICS RESPONSES
# =============================================================================

class DatabaseStats(BaseModel):
    """Database statistics."""
    total_sessions: int
    total_llm_calls: int
    total_conversations: int
    unique_users: int
    database_size_mb: float
    oldest_record: Optional[str] = None  # ISO datetime
    newest_record: Optional[str] = None  # ISO datetime


class OverviewStats(BaseModel):
    """High-level overview statistics."""
    total_calls: int
    total_cost: float
    avg_cost_per_call: float
    total_tokens: int
    avg_latency_ms: float
    success_rate: float
    unique_operations: int
    unique_agents: int
    date_range_days: int