"""
Stories Router - All Story Endpoints (Layer 1 & 2)
Location: api/routers/stories.py

Handles:
- Layer 1: GET /api/stories/{story_id} - Summary view
- Layer 2: GET /api/stories/{story_id}/operations/{operation} - Operation detail
- Special endpoints for caching and optimization impact
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from api.utils.data_fetcher import get_llm_calls
from api.services import (
    latency_service,
    cache_service,
    routing_service,
    quality_service,
    token_service,
    prompt_service,
    cost_service,
    optimization_service,
)

router = APIRouter()


# =============================================================================
# LAYER 1: STORY SUMMARY
# =============================================================================

@router.get("/{story_id}")
async def get_story_summary(
    story_id: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, ge=1, le=10000),
):
    """
    Layer 1: Story summary with KPI cards + table.
    
    Args:
        story_id: One of: latency, caching, routing, quality, 
                  token-efficiency, prompt-composition, cost, optimization-impact
        project: Filter by project name
        days: Number of days to analyze (1-90)
        limit: Maximum number of calls to analyze
    
    Returns:
        {
            "kpi_cards": {...},
            "table": [...],
            "insights": [...],
            "meta": {...}
        }
    """
    # Get data
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    calls = get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    # Route to appropriate service
    services = {
        "latency": latency_service.get_summary,
        "caching": cache_service.get_summary,
        "routing": routing_service.get_summary,
        "quality": quality_service.get_summary,
        "token-efficiency": token_service.get_summary,
        "prompt-composition": prompt_service.get_summary,
        "cost": cost_service.get_summary,
        "optimization-impact": optimization_service.get_summary,
    }
    
    if story_id not in services:
        return {
            "error": f"Unknown story: {story_id}",
            "valid_stories": list(services.keys())
        }
    
    result = services[story_id](calls, project, days)
    return result


# =============================================================================
# LAYER 2: OPERATION DRILL-DOWN
# =============================================================================

@router.get("/{story_id}/operations/{operation}")
async def get_operation_detail(
    story_id: str,
    operation: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, ge=1, le=10000),
):
    """
    Layer 2: Operation-specific detail.
    
    Args:
        story_id: Story identifier
        operation: Operation name (from Layer 1 table)
        project: Filter by project name
        days: Number of days to analyze
        limit: Maximum number of calls
    
    Returns:
        {
            "operation_summary": {...},
            "detail_breakdown": {...},
            "calls_table": [...],
            "recommendations": [...]
        }
    """
    # Get data for this operation
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    calls = get_llm_calls(
        project_name=project,
        operation=operation,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    # Route to appropriate service
    services = {
        "latency": latency_service.get_operation_detail,
        "caching": cache_service.get_operation_detail,
        "routing": routing_service.get_operation_detail,
        "quality": quality_service.get_operation_detail,
        "token-efficiency": token_service.get_operation_detail,
        "prompt-composition": prompt_service.get_operation_detail,
        "cost": cost_service.get_operation_detail,
    }
    
    if story_id not in services:
        return {"error": f"Unknown story: {story_id}"}
    
    result = services[story_id](calls, operation, project, days)
    return result


# =============================================================================
# STORY 2 SPECIAL: CACHING - DUPLICATE GROUPS
# =============================================================================

@router.get("/caching/operations/{operation}/groups/{group_id}")
async def get_duplicate_group(
    operation: str,
    group_id: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
):
    """
    Layer 3 for Caching: Duplicate group detail.
    
    Shows all calls that share the same normalized prompt (duplicates).
    
    Args:
        operation: Operation name
        group_id: Hash of normalized prompt
        project: Filter by project name
        days: Number of days to analyze
    
    Returns:
        {
            "group_stats": {...},
            "prompt": "...",
            "response": "...",
            "calls": [...],
            "diagnosis": {...}
        }
    """
    return cache_service.get_duplicate_group(operation, group_id, project, days)


# =============================================================================
# STORY 8 SPECIAL: OPTIMIZATION IMPACT
# =============================================================================

@router.get("/optimization-impact/optimizations/{optimization_id}")
async def get_optimization_detail(optimization_id: str):
    """
    Layer 2 for Optimization Impact.
    
    Shows before/after comparison for a specific optimization.
    
    Args:
        optimization_id: Unique identifier for optimization
    
    Returns:
        {
            "optimization_info": {...},
            "before_after_comparison": {...},
            "trend_data": [...],
            "roi_analysis": {...}
        }
    """
    return optimization_service.get_optimization_detail(optimization_id)


@router.get("/optimization-impact/compare")
async def compare_optimization_calls(
    before: str = Query(..., description="Call ID from before optimization"),
    after: str = Query(..., description="Call ID from after optimization"),
):
    """
    Layer 3 for Optimization Impact: Side-by-side call comparison.
    
    Args:
        before: Call ID from before period
        after: Call ID from after period
    
    Returns:
        {
            "before_call": {...},
            "after_call": {...},
            "differences": {...},
            "quality_analysis": {...}
        }
    """
    return optimization_service.compare_calls(before, after)