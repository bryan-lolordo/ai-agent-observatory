"""
Analysis Router
Location: api/routers/analysis.py

Endpoints for LLM-powered call analysis and fix recommendations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.services.fix_analysis_service import (
    analyze_call_for_fixes,
    clear_analysis_cache,
    get_cached_analysis,
)


router = APIRouter(prefix="/analysis", tags=["analysis"])


# =============================================================================
# ANALYZE CALL
# =============================================================================

@router.get("/calls/{call_id}")
async def analyze_call(
    call_id: str,
    use_cache: bool = Query(default=True, description="Use cached analysis if available"),
):
    """
    Analyze a call using LLM and return tailored fix recommendations.
    
    This endpoint uses GPT-4o to deeply analyze the call's prompt, response,
    and metrics to generate 3 specific, actionable recommendations.
    
    **Cost:** ~$0.01-0.03 per analysis (cached results are free)
    
    Returns:
    - analysis: Purpose, essential/redundant output, prompt issues
    - recommendations: 3 prioritized fixes with:
        - Problem description
        - Solution
        - Rewritten prompt (ready to copy)
        - Expected impact (tokens, latency, cost reduction)
        - Effort level
        - Confidence score
    """
    result = analyze_call_for_fixes(call_id, use_cache=use_cache)
    
    if "error" in result:
        # Return error details but don't raise HTTPException for analysis failures
        # This allows frontend to show helpful error messages
        return result
    
    return result


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

@router.delete("/cache")
async def clear_cache(call_id: Optional[str] = None):
    """
    Clear analysis cache.
    
    - If call_id provided: Clear cache for that specific call
    - If no call_id: Clear entire cache
    """
    clear_analysis_cache(call_id)
    return {
        "status": "ok",
        "message": f"Cache cleared for {call_id}" if call_id else "All cache cleared"
    }


@router.get("/cache/{call_id}")
async def get_cached(call_id: str):
    """
    Get cached analysis for a call (if available).
    Returns null if no cached analysis exists.
    """
    cached = get_cached_analysis(call_id)
    if cached:
        return {"cached": True, "analysis": cached}
    return {"cached": False, "analysis": None}