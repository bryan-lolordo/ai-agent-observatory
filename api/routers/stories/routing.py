"""
Story 3: Model Routing Router
Location: api/routers/stories/routing.py

Layer 1: GET /api/stories/routing - Summary with opportunities
Layer 2: GET /api/stories/routing/operations/{agent}/{operation} - Operation detail
Layer 3: Uses shared GET /api/stories/calls/{call_id}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_routing_summary, get_routing_operation_detail
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("")
def get_routing_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Model Routing Opportunities Summary
    
    Returns:
    - KPIs: current model, downgrade/upgrade counts, potential savings
    - Top offender (highest complexity on cheap model)
    - Operations table with complexity, quality, opportunity
    - Chart data for complexity vs quality scatter plot
    """
    calls = get_filtered_calls(project, days, limit)
    return get_routing_summary(calls, project, days)


@router.get("/operations/{agent}/{operation}")
def get_routing_operation_detail_endpoint(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Operation Detail for Routing Analysis
    
    Returns:
    - Operation summary (complexity, quality, cost, model)
    - Routing recommendation badge (upgrade/downgrade/keep)
    - All calls with quality scores
    - Quality distribution histogram
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_routing_operation_detail(calls, agent, operation)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operation not found: {agent}.{operation}"
        )
    
    return result