"""
LLM Calls Router
Location: api/routers/llm_calls.py
"""

from fastapi import APIRouter, HTTPException
from api.services import llm_call_service
from api.models import LLMCallResponse

router = APIRouter(
    prefix="/calls",          # ← Prefix handles /calls
    tags=["llm-calls"],      # ← Swagger grouping
)

@router.get("/{call_id}", response_model=LLMCallResponse)  # ← Just /{call_id} since prefix adds /calls
async def get_call_detail(call_id: str):
    """
    Get full LLM call detail with diagnosis and recommendations.
    
    **Layer 3 Endpoint** - Used by all stories for call drill-down.
    """
    result = llm_call_service.get_detail(call_id)  # ← Changed to get_detail()
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Call not found: {call_id}"
        )
    
    return result