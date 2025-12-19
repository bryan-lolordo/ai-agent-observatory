"""
Story 6: Prompt Composition Router
Location: api/routers/stories/prompt.py

Layer 1: GET /api/stories/system_prompt - Prompt composition summary
Layer 2: GET /api/stories/system_prompt/operations/{agent}/{operation} - Operation detail
Layer 3: Uses shared GET /api/stories/calls/{call_id}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_prompt_summary, get_prompt_operation_detail
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/system_prompt", tags=["system_prompt"])


@router.get("")
def get_prompt_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Prompt Composition Summary
    
    Returns:
    - KPIs: avg system/user/history tokens, cache ready count
    - Composition chart (system vs user vs history)
    - Operations table with cache readiness
    """
    calls = get_filtered_calls(project, days, limit)
    return get_prompt_summary(calls, project, days)


@router.get("/operations/{agent}/{operation}")
def get_prompt_operation_detail_endpoint(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Operation Prompt Structure
    
    Returns:
    - Cache status and reason
    - Token breakdown (system, user, history)
    - Variability analysis
    - Sample calls
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_prompt_operation_detail(calls, agent, operation)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operation not found: {agent}.{operation}"
        )
    
    return result