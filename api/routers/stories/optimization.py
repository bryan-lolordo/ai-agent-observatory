"""
Story 8: Optimization Impact Router
Location: api/routers/stories/optimization.py

MVP: Baseline mode only
Layer 1: GET /api/stories/optimization - Baseline metrics and pending optimizations
Layer 2: Placeholder for future optimization detail
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services import get_optimization_summary
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("")
def get_optimization_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Optimization Impact Summary
    
    MVP: Baseline mode - shows current metrics vs targets
    
    Returns:
    - KPIs: latency, cost, quality, cache rate
    - Baseline metrics with targets and gaps
    - Pending optimizations from Stories 1-7
    """
    calls = get_filtered_calls(project, days, limit)
    return get_optimization_summary(calls, project, days)


@router.get("/detail/{optimization_id}")
def get_optimization_detail_endpoint(
    optimization_id: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Optimization Detail (Placeholder)
    
    Will show before/after comparison when optimization tracking is implemented.
    """
    return {
        "status": "not_implemented",
        "message": "Optimization tracking coming soon. Implement optimizations from Stories 1-7, then return here to measure impact.",
        "optimization_id": optimization_id,
    }