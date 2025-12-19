"""
Call Detail Router (Layer 3)
Location: api/routers/stories/calls.py

Shared endpoint for detailed LLM call information.
Used by all stories for drill-down functionality.
"""

from fastapi import APIRouter, HTTPException

from api.services import get_llm_call_detail


router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("/{call_id}")  # Removed response_model for now
def get_call(call_id: str):
    """
    Get detailed information about a specific LLM call.
    
    Includes full prompt, response, tokens, cost, quality evaluation,
    and comprehensive diagnosis with recommendations.
    
    This is the Layer 3 drill-down endpoint shared by all stories.
    
    Args:
        call_id: Unique identifier for the LLM call
        
    Returns:
        Complete call details with diagnosis and recommendations
        
    Raises:
        404: If call not found
    """
    call_detail = get_llm_call_detail(call_id)
    
    if not call_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Call not found: {call_id}"
        )
    
    return call_detail