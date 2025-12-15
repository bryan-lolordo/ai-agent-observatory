"""
Metadata Router - Filter Metadata Endpoints
Location: api/routers/metadata.py

Handles:
- GET /api/projects - List available projects
- GET /api/models - List available models
- GET /api/agents - List available agents
- GET /api/operations - List available operations
"""

from fastapi import APIRouter
from typing import Optional

from api.utils.data_fetcher import (
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_available_operations,
)

router = APIRouter()


@router.get("/projects")
async def get_projects():
    """
    Get list of all projects in database.
    
    Returns:
        {"projects": ["project1", "project2", ...]}
    """
    return {"projects": get_available_projects()}


@router.get("/models")
async def get_models(project: Optional[str] = None):
    """
    Get list of all models, optionally filtered by project.
    
    Args:
        project: Optional project name to filter by
    
    Returns:
        {"models": ["gpt-4o-mini", "gpt-4o", ...]}
    """
    return {"models": get_available_models(project_name=project)}


@router.get("/agents")
async def get_agents(project: Optional[str] = None):
    """
    Get list of all agents, optionally filtered by project.
    
    Args:
        project: Optional project name to filter by
    
    Returns:
        {"agents": ["ResumeMatching", "DatabaseQuery", ...]}
    """
    return {"agents": get_available_agents(project_name=project)}


@router.get("/operations")
async def get_operations(project: Optional[str] = None):
    """
    Get list of all operations, optionally filtered by project.
    
    Args:
        project: Optional project name to filter by
    
    Returns:
        {"operations": ["quick_score_job", "deep_analyze_job", ...]}
    """
    return {"operations": get_available_operations(project_name=project)}