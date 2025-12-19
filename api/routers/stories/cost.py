"""
Story 7: Cost Analysis Router
Location: api/routers/stories/cost.py

Layer 1: GET /api/stories/cost - Cost summary
Layer 2: GET /api/stories/cost/operations/{agent}/{operation} - Operation cost breakdown
Layer 3: Uses shared GET /api/stories/calls/{call_id}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_cost_summary, get_cost_operation_detail
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/cost", tags=["cost"])


@router.get("")
def get_cost_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Cost Analysis Summary
    
    Returns:
    - KPIs: total cost, avg cost/call, top 3 concentration, potential savings
    - Operations table sorted by cost
    - Pie chart data for cost distribution
    """
    calls = get_filtered_calls(project, days, limit)
    return get_cost_summary(calls, project, days)


@router.get("/operations/{agent}/{operation}")
def get_cost_operation_detail_endpoint(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Operation Cost Breakdown
    
    Returns:
    - Cost status and totals
    - Prompt vs completion cost breakdown
    - Cost driver analysis
    - Savings opportunities
    - Calls sorted by cost
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_cost_operation_detail(calls, agent, operation)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operation not found: {agent}.{operation}"
        )
    
    return result