"""
Stories Router Package
Location: api/routers/stories/__init__.py

Combines all story routers into a single router.
Exports `router` for use by api/routers/__init__.py

Complete: All 8 stories implemented.

Endpoint Structure:
    GET  /api/stories                    - All stories summary (dashboard)
    GET  /api/stories/latency            - Story 1: Latency Monster
    GET  /api/stories/cache              - Story 2: Cache Strategy
    GET  /api/stories/routing            - Story 3: Model Routing
    GET  /api/stories/quality            - Story 4: Quality Issues
    GET  /api/stories/token_imbalance    - Story 5: Token Efficiency
    GET  /api/stories/system_prompt      - Story 6: Prompt Composition
    GET  /api/stories/cost               - Story 7: Cost Analysis
    GET  /api/stories/optimization       - Story 8: Optimization Impact
    GET  /api/stories/calls/{call_id}    - Layer 3: Call Detail
"""

from fastapi import APIRouter, Query
from typing import Optional

# Import all story routers
from .latency import router as latency_router
from .cache import router as cache_router
from .routing import router as routing_router
from .quality import router as quality_router
from .token import router as token_router
from .prompt import router as prompt_router
from .cost import router as cost_router
from .optimization import router as optimization_router
from .calls import router as calls_router

# Import services for summary endpoint
from api.services import (
    get_latency_summary,
    get_cache_summary,
    get_routing_summary,
    get_quality_summary,
    get_token_summary,
    get_prompt_summary,
    get_cost_summary,
    get_optimization_summary,
)
from ._helpers import get_filtered_calls


# =============================================================================
# HELPER: Extract health_score from dict or Pydantic model
# =============================================================================

def _get_health_score(story_result) -> float:
    """Extract health_score from either a dict or Pydantic model."""
    if hasattr(story_result, 'health_score'):
        return story_result.health_score
    elif isinstance(story_result, dict) and 'health_score' in story_result:
        return story_result['health_score']
    return 0.0


def _normalize_story_result(story_result) -> dict:
    """Convert Pydantic model to dict if needed."""
    if hasattr(story_result, 'model_dump'):
        return story_result.model_dump()
    elif hasattr(story_result, 'dict'):
        return story_result.dict()
    elif isinstance(story_result, dict):
        return story_result
    return {}


# =============================================================================
# MAIN ROUTER
# =============================================================================

router = APIRouter(prefix="/api/stories", tags=["stories"])


# =============================================================================
# ALL STORIES SUMMARY (Dashboard Endpoint)
# =============================================================================

@router.get("", response_model=dict)
def get_all_stories(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Get all story summaries in one call (for dashboard).
    
    Returns health scores and summaries for all 8 stories.
    Used by the frontend dashboard to display overview metrics.
    """
    calls = get_filtered_calls(project, days, limit)
    
    # Calculate all stories
    raw_stories = {
        "latency": get_latency_summary(calls, project, days),
        "cache": get_cache_summary(calls, project, days),
        "routing": get_routing_summary(calls, project, days),
        "quality": get_quality_summary(calls, project, days),
        "token_imbalance": get_token_summary(calls, project, days),
        "system_prompt": get_prompt_summary(calls, project, days),
        "cost": get_cost_summary(calls, project, days),
        "optimization": get_optimization_summary(calls, project, days),
    }
    
    # Normalize all results to dicts
    stories = {k: _normalize_story_result(v) for k, v in raw_stories.items()}
    
    # Calculate overall health (average of all story health scores)
    health_scores = [_get_health_score(s) for s in raw_stories.values()]
    overall_health = sum(health_scores) / len(health_scores) if health_scores else 0
    
    return {
        "overall_health": overall_health,
        "total_calls": len(calls),
        "stories": stories,
    }


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

# Story routers (Layer 1 & 2)
router.include_router(latency_router)       # /api/stories/latency
router.include_router(cache_router)         # /api/stories/cache
router.include_router(routing_router)       # /api/stories/routing
router.include_router(quality_router)       # /api/stories/quality
router.include_router(token_router)         # /api/stories/token_imbalance
router.include_router(prompt_router)        # /api/stories/system_prompt
router.include_router(cost_router)          # /api/stories/cost
router.include_router(optimization_router)  # /api/stories/optimization

# Call detail router (Layer 3)
router.include_router(calls_router)         # /api/stories/calls/{call_id}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["router"]