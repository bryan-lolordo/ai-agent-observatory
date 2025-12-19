"""
Metadata Router - Filter Options
Location: api/routers/metadata.py

Provides lists of available projects, models, agents, operations
for filtering in the frontend.
"""

from fastapi import APIRouter
from typing import Optional

from api.utils.data_fetcher import (
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_available_operations,
)


router = APIRouter(prefix="/api", tags=["metadata"])


# =============================================================================
# METADATA ENDPOINTS
# =============================================================================

@router.get("/projects")
def list_projects():
    """
    Get list of all available projects.
    
    Returns:
        List of project names
    """
    return {
        "projects": get_available_projects()
    }


@router.get("/models")
def list_models(project: Optional[str] = None):
    """
    Get list of all available models.
    
    Args:
        project: Optional project filter
    
    Returns:
        List of model names
    """
    return {
        "models": get_available_models(project_name=project)
    }


@router.get("/agents")
def list_agents(project: Optional[str] = None):
    """
    Get list of all available agents.
    
    Args:
        project: Optional project filter
    
    Returns:
        List of agent names
    """
    return {
        "agents": get_available_agents(project_name=project)
    }


@router.get("/operations")
def list_operations(project: Optional[str] = None):
    """
    Get list of all available operations.
    
    Args:
        project: Optional project filter
    
    Returns:
        List of operation names
    """
    return {
        "operations": get_available_operations(project_name=project)
    }


@router.get("/filters")
def get_all_filters(project: Optional[str] = None):
    """
    Get all filter options at once.
    
    Convenience endpoint that returns projects, models, agents,
    and operations in a single response.
    
    Args:
        project: Optional project filter (for models/agents/operations)
    
    Returns:
        Dictionary with all filter options
    """
    return {
        "projects": get_available_projects(),
        "models": get_available_models(project_name=project),
        "agents": get_available_agents(project_name=project),
        "operations": get_available_operations(project_name=project),
    }