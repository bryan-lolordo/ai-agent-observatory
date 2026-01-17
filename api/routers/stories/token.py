"""
Story 5: Token Efficiency Router
Location: api/routers/stories/token.py

Layer 1: GET /api/stories/token_imbalance - Summary with ratio analysis
Layer 2: GET /api/stories/token_imbalance/operations/{agent}/{operation} - Token breakdown
Layer 3: Uses shared GET /api/stories/calls/{call_id}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_token_summary, get_token_operation_detail
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/token_imbalance", tags=["token_imbalance"])


@router.get("")
def get_token_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
    phase: Optional[str] = Query(default=None, description="Filter by phase: 'baseline' or 'optimized'"),
):
    """
    Layer 1: Token Efficiency Summary

    Returns:
    - KPIs: avg ratio, imbalanced ops, worst ratio, wasted cost
    - Top offender (worst ratio operation)
    - Operations table with token stats
    - Chart data for ratio distribution
    """
    calls = get_filtered_calls(project, days, limit, phase=phase)
    return get_token_summary(calls, project, days)


@router.get("/operations/{agent}/{operation}")
def get_token_operation_detail_endpoint(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
    phase: Optional[str] = Query(default=None, description="Filter by phase: 'baseline' or 'optimized'"),
):
    """
    Layer 2: Operation Detail for Token Analysis

    Returns:
    - Operation summary (avg prompt, completion, ratio)
    - Token breakdown visualization (system, history, user, etc.)
    - Problem detection
    - All calls with token details
    """
    calls = get_filtered_calls(project, days, limit, phase=phase)
    result = get_token_operation_detail(calls, agent, operation)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operation not found: {agent}.{operation}"
        )
    
    return result