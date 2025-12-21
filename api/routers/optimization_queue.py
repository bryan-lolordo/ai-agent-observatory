"""
Optimization Queue Router
Location: api/routers/optimization_queue.py

Exposes optimization opportunities for the Optimization Queue dashboard.

Endpoints:
    GET /api/optimization/opportunities - Get all optimization opportunities
"""

from fastapi import APIRouter, Query
from typing import Optional

from api.services.optimization_queue_service import get_optimization_opportunities


router = APIRouter(prefix="/api/optimization", tags=["optimization-queue"])


@router.get("/opportunities")
def list_opportunities(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    story: Optional[str] = Query(
        default=None, 
        description="Filter by story: latency, cache, cost, quality, routing"
    ),
    limit: int = Query(default=100, ge=1, le=500),
):
    """
    Get optimization opportunities across all stories.
    
    Returns a list of issues grouped by story type with impact estimates.
    Used by the Optimization Queue dashboard.
    
    Example response:
    {
        "opportunities": [
            {
                "id": "latency-no-max-ResumeMatching.deep_analyze",
                "storyId": "latency",
                "storyIcon": "🌐",
                "agent": "ResumeMatching",
                "operation": "deep_analyze",
                "issue": "No max_tokens (1,200 avg tokens)",
                "impact": "$0.34",
                "impactValue": 0.34,
                "effort": "Low",
                "callCount": 47,
                "callId": "abc123..."
            }
        ],
        "summary": {
            "total": 23,
            "totalSavings": 4.56,
            "quickWins": 15,
            "byStory": {"latency": 10, "cache": 8, "cost": 5}
        }
    }
    """
    result = get_optimization_opportunities(
        project=project,
        days=days,
        story_filter=story,
        limit=limit,
    )
    
    return result