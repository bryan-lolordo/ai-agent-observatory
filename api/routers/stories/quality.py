"""
Story 4: Quality Monitoring Router
Location: api/routers/stories/quality.py

Layer 1: GET /api/stories/quality - Summary with quality issues
Layer 2: GET /api/stories/quality/operations/{agent}/{operation} - Operation detail
Layer 3: Uses shared GET /api/stories/calls/{call_id}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_quality_summary, get_quality_operation_detail
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("")
def get_quality_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Quality Monitoring Summary
    
    Returns:
    - KPIs: avg quality, low quality ops, error rate, hallucinations
    - Top offender (worst quality operation)
    - Operations table with quality stats
    - Chart data for quality distribution histogram
    """
    calls = get_filtered_calls(project, days, limit)
    return get_quality_summary(calls, project, days)


@router.get("/operations/{agent}/{operation}")
def get_quality_operation_detail_endpoint(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Operation Detail for Quality Analysis
    
    Returns:
    - Operation summary (avg/min/max score, errors, hallucinations)
    - Quality status badge
    - All calls with quality scores and issues
    - Quality distribution histogram
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_quality_operation_detail(calls, agent, operation)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operation not found: {agent}.{operation}"
        )
    
    return result