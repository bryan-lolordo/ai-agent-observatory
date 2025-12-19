"""
Story 2: Caching Strategy Router
Location: api/routers/stories/cache.py

Endpoints for cache opportunity detection with 4 cache types.

Layer 1: GET /api/stories/cache - Summary with operations table
Layer 2: GET /api/stories/cache/operations/{agent}/{operation} - Operation detail
Layer 3: GET /api/stories/cache/operations/{agent}/{operation}/groups/{group_id} - Opportunity detail
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from api.services.cache_service import get_summary, get_operation_detail, get_opportunity_detail
from api.models import CacheStoryResponse
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/cache", tags=["cache"])


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

@router.get("", response_model=CacheStoryResponse)
def get_cache_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 1: Cache opportunities summary.
    
    Returns overview with:
    - KPIs: Potential savings, cacheable calls, hit rate, top offender
    - Table: Operations ranked by cache opportunity with type indicator
    - Chart: Wasted cost by operation
    """
    calls = get_filtered_calls(project, days, limit)
    return get_summary(calls, project, days)


# =============================================================================
# LAYER 2: OPERATION DETAIL
# =============================================================================

@router.get("/operations/{agent}/{operation}")
def get_cache_operation(
    agent: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 2: Cache opportunities for a specific operation.
    
    Returns:
    - KPIs: Total calls, unique prompts, cacheable, wasted cost
    - Type counts: How many of each cache type (Exact/Stable/High-Value)
    - Table: Cache opportunities with type, repeats, wasted cost
    - Filters: By cache type
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_operation_detail(calls, agent, operation)
    
    if result['total_calls'] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No calls found for {agent}.{operation}"
        )
    
    return result


# =============================================================================
# LAYER 3: OPPORTUNITY DETAIL
# =============================================================================

@router.get("/operations/{agent}/{operation}/groups/{group_id}")
def get_cache_group(
    agent: str,
    operation: str,
    group_id: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Layer 3: Detailed view of a single cache opportunity.
    
    Returns:
    - KPIs: Times called, wasted calls, wasted cost, time saved
    - Cache type info: Type, effort level
    - Diagnosis: Type-specific problem description
    - Code snippet: Copy-paste fix for this cache type
    - Expected impact: Calls/cost/latency before vs after
    - Prompt/Response: The repeated content
    - Calls table: All calls in this group (click for CallDetail)
    """
    calls = get_filtered_calls(project, days, limit)
    result = get_opportunity_detail(calls, agent, operation, group_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cache opportunity not found: {group_id}"
        )
    
    return result