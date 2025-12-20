"""
Call Router (Layer 2 + Layer 3)
Location: api/routers/stories/calls.py
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.services.llm_call_service import get_detail, get_calls


router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls(
    days: int = Query(default=7, ge=1, le=90),
    operation: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=1000)
):
    """
    Get all LLM calls with optional filters (Layer 2).
    """
    calls = get_calls(
        days=days,
        operation=operation,
        agent=agent,
        limit=limit
    )
    return {"calls": calls, "total": len(calls)}


@router.get("/{call_id}")
def get_call(call_id: str):
    """
    Get detailed information about a specific LLM call (Layer 3).
    """
    call_detail = get_detail(call_id)
    
    if not call_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Call not found: {call_id}"
        )
    
    return call_detail