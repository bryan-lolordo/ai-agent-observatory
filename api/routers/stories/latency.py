"""
Story 1: Latency Analysis Router
Location: api/routers/stories/latency.py

Endpoints for latency analysis and slow operation detection.

Endpoints:
    GET /latency                                    - Layer 1: Story summary
    GET /latency/operations/{agent}/{operation}     - Layer 2: Operation detail
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from urllib.parse import unquote
from datetime import datetime, timedelta

from api.services import get_latency_summary
from api.models import LatencyStoryResponse
from ._helpers import get_filtered_calls

router = APIRouter(prefix="/latency", tags=["latency"])


# =============================================================================
# LAYER 1: Story Summary
# =============================================================================

@router.get("", response_model=LatencyStoryResponse)
def get_latency_story(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Story 1: Latency Analysis (Layer 1)
    
    Returns operations with excessive response times.
    Identifies slow endpoints and provides optimization recommendations.
    """
    calls = get_filtered_calls(project, days, limit)
    return get_latency_summary(calls, project, days)


# =============================================================================
# LAYER 2: Operation Detail
# =============================================================================

@router.get("/operations/{agent_name}/{operation_name}")
def get_latency_operation_detail(
    agent_name: str,
    operation_name: str,
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
):
    """
    Layer 2: Operation detail with all calls
    
    Returns all LLM calls for a specific agent+operation with latency metrics.
    
    URL Example: /api/stories/latency/operations/ResumeMatching/deep_analyze_job
    
    Args:
        agent_name: Agent name (e.g., "ResumeMatching")
        operation_name: Operation name (e.g., "deep_analyze_job")
        project: Optional project filter
        days: Number of days to look back (default 7)
    """
    from observatory.storage import ObservatoryStorage
    
    # Decode URL-encoded parameters
    agent_name = unquote(agent_name)
    operation_name = unquote(operation_name)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Query with both agent and operation
    calls = ObservatoryStorage.get_llm_calls(
        project_name=project,
        agent_name=agent_name,
        operation=operation_name,
        start_time=start_time,
        end_time=end_time,
        limit=2000
    )
    
    if not calls:
        raise HTTPException(
            status_code=404, 
            detail=f"No calls found for: {agent_name}.{operation_name}"
        )
    
    # Calculate summary stats
    latencies = [c.latency_ms for c in calls if c.latency_ms]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    
    total_cost = sum(c.total_cost or 0 for c in calls)
    error_count = sum(1 for c in calls if c.error)
    
    # Convert to response format
    calls_data = [{
        "call_id": c.id,
        "timestamp": c.timestamp.isoformat() if c.timestamp else None,
        "operation": c.operation,
        "agent_name": c.agent_name,
        "latency_ms": c.latency_ms,
        "prompt_tokens": c.prompt_tokens,
        "completion_tokens": c.completion_tokens,
        "total_tokens": c.total_tokens,
        "model_name": c.model_name,
        "total_cost": c.total_cost,
        "prompt_preview": c.prompt[:100] if c.prompt else None,
        "quality_score": c.quality_evaluation.judge_score if c.quality_evaluation else None,
        "cached": c.cache_metadata.cache_hit if c.cache_metadata else False,
        "error": c.error,
        "success": c.success,
    } for c in calls]
    
    # Sort by latency DESC (slowest first)
    calls_data.sort(key=lambda x: x["latency_ms"] or 0, reverse=True)
    
    return {
        "agent_name": agent_name,
        "operation": operation_name,
        "total_calls": len(calls_data),
        "summary": {
            "avg_latency_ms": round(avg_latency, 2),
            "max_latency_ms": max_latency,
            "min_latency_ms": min_latency,
            "total_cost": round(total_cost, 6),
            "error_count": error_count,
            "error_rate": round(error_count / len(calls) * 100, 1) if calls else 0,
        },
        "calls": calls_data,
    }