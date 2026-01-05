"""
Story 8: Optimization Impact Router
Location: api/routers/stories/optimization.py

Hierarchical expandable rows view:
  Agent → Operation → Story → Fixes → Calls

Endpoints:
- GET /api/stories/optimization - Get hierarchy with all optimization stories
- GET /api/stories/optimization/detail/{story_id} - Get single story detail
- PATCH /api/stories/optimization/{story_id}/status - Update story status
- POST /api/stories/optimization/{story_id}/fixes - Add a fix
- DELETE /api/stories/optimization/fixes/{fix_id} - Delete a fix
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from api.services.optimization_service import (
    get_summary,
    get_optimization_detail,
    update_story_status,
    add_applied_fix,
    delete_fix,
)
from api.models.optimization import (
    OptimizationStoryUpdate,
    AppliedFixCreate,
)
from ._helpers import get_filtered_calls


router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("")
def get_optimization_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Get the hierarchical optimization view.

    Returns:
    - hierarchy: Agent → Operation → Story tree structure
    - kpis: Overall metrics (latency, cost, quality, etc.)
    - status: Overall health status
    """
    calls = get_filtered_calls(project, days, limit)
    return get_summary(calls, project, days)


@router.get("/detail/{story_id}")
def get_story_detail(
    story_id: str,
):
    """
    Get detailed view of a single optimization story.

    Returns:
    - story: Full story data with baseline/current metrics
    - fixes: All applied fixes for this story
    - calls: Sample calls that triggered this story
    """
    result = get_optimization_detail(story_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")
    return result


@router.patch("/{story_id}/status")
def update_status(
    story_id: str,
    update: OptimizationStoryUpdate,
):
    """
    Update the status of an optimization story.

    Status values:
    - pending: Not yet started
    - in_progress: Currently working on it
    - complete: Fix applied and validated
    - skipped: Decided not to fix (provide skip_reason)
    """
    success = update_story_status(
        story_id=story_id,
        status=update.status,
        skip_reason=update.skip_reason,
        current_value=update.current_value,
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Story not found: {story_id}")
    return {"success": True, "story_id": story_id, "status": update.status}


@router.post("/{story_id}/fixes")
def add_fix(
    story_id: str,
    fix: AppliedFixCreate,
):
    """
    Add an applied fix to an optimization story.

    If after_value is provided, the story status will be automatically
    set to 'complete' and improvement will be calculated.
    """
    # Override story_id from path
    fix_id = add_applied_fix(
        optimization_story_id=story_id,
        fix_type=fix.fix_type,
        before_value=fix.before_value,
        after_value=fix.after_value,
        applied_date=fix.applied_date or datetime.utcnow(),
        git_commit=fix.git_commit,
        notes=fix.notes,
    )
    return {"success": True, "fix_id": fix_id, "story_id": story_id}


@router.delete("/fixes/{fix_id}")
def remove_fix(
    fix_id: str,
):
    """
    Delete an applied fix.
    """
    success = delete_fix(fix_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Fix not found: {fix_id}")
    return {"success": True, "fix_id": fix_id}
