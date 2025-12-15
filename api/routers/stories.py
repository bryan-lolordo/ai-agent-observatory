"""
Stories Router - All Story Endpoints
Location: api/routers/stories.py

Exposes all 8 optimization stories + call detail endpoint.
Uses services layer for business logic.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime, timedelta

from api.services import (
    get_call_detail,
    get_latency_summary,
    get_cache_summary,
    get_routing_summary,
    get_quality_summary,
    get_token_summary,
    get_prompt_summary,
    get_cost_summary,
    get_optimization_summary,
)
from api.models import (
    LLMCallResponse,
    LatencyStoryResponse,
    CacheStoryResponse,
    RoutingStoryResponse,
    QualityStoryResponse,
    TokenStoryResponse,
    PromptStoryResponse,
    CostStoryResponse,
    OptimizationStoryResponse,
)
from api.utils.data_fetcher import get_llm_calls


router = APIRouter(prefix="/api/stories", tags=["stories"])


# =============================================================================
# HELPER: Get Calls with Filters
# =============================================================================

def _get_filtered_calls(
    project: Optional[str] = None,
    days: int = 7,
    limit: int = 2000,
) -> list:
    """Get LLM calls with common filters."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    return get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )


# =============================================================================
# STORY 1: LATENCY
# =============================================================================

@router.get("/latency", response_model=LatencyStoryResponse)
def get_latency_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 1: Latency Monster
    
    Returns operations with excessive response times.
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_latency_summary(calls, project, days)


# =============================================================================
# STORY 2: CACHING
# =============================================================================

@router.get("/cache", response_model=CacheStoryResponse)
def get_cache_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 2: Zero Cache Hits
    
    Returns caching opportunities (duplicate prompts).
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_cache_summary(calls, project, days)


# =============================================================================
# STORY 3: ROUTING
# =============================================================================

@router.get("/routing", response_model=RoutingStoryResponse)
def get_routing_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 3: Model Routing
    
    Returns routing opportunities (complexity mismatches).
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_routing_summary(calls, project, days)


# =============================================================================
# STORY 4: QUALITY
# =============================================================================

@router.get("/quality", response_model=QualityStoryResponse)
def get_quality_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 4: Quality Issues
    
    Returns errors, hallucinations, and quality problems.
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_quality_summary(calls, project, days)


# =============================================================================
# STORY 5: TOKEN EFFICIENCY
# =============================================================================

@router.get("/token-efficiency", response_model=TokenStoryResponse)
def get_token_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 5: Token Imbalance
    
    Returns operations with poor prompt:completion ratios.
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_token_summary(calls, project, days)


# =============================================================================
# STORY 6: PROMPT COMPOSITION
# =============================================================================

@router.get("/prompt-composition", response_model=PromptStoryResponse)
def get_prompt_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 6: System Prompt Waste
    
    Returns prompt composition and wasteful system prompts.
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_prompt_summary(calls, project, days)


# =============================================================================
# STORY 7: COST
# =============================================================================

@router.get("/cost", response_model=CostStoryResponse)
def get_cost_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 7: Cost Deep Dive
    
    Returns cost breakdown and concentration analysis.
    """
    calls = _get_filtered_calls(project, days, limit)
    return get_cost_summary(calls, project, days)


# =============================================================================
# STORY 8: OPTIMIZATION IMPACT
# =============================================================================

@router.get("/optimization-impact", response_model=OptimizationStoryResponse)
def get_optimization_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
    optimization_date: Optional[str] = None,
):
    """
    Story 8: Optimization Impact
    
    Returns baseline metrics or before/after comparison.
    
    Args:
        optimization_date: ISO date string (e.g., "2024-12-10") for comparison
    """
    calls = _get_filtered_calls(project, days, limit)
    
    # Parse optimization date if provided
    opt_date = None
    if optimization_date:
        try:
            opt_date = datetime.fromisoformat(optimization_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {optimization_date}. Use ISO format (YYYY-MM-DD)"
            )
    
    return get_optimization_summary(calls, project, days, opt_date)


# =============================================================================
# CALL DETAIL (Layer 3 - shared by all stories)
# =============================================================================

@router.get("/calls/{call_id}", response_model=LLMCallResponse)
def get_call(call_id: str):
    """
    Get detailed information about a specific LLM call.
    
    Includes full prompt, response, tokens, cost, quality evaluation,
    and comprehensive diagnosis with recommendations.
    """
    call_detail = get_call_detail(call_id)
    
    if not call_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Call not found: {call_id}"
        )
    
    return call_detail