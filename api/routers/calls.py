from fastapi import APIRouter
from api.services import call_service

router = APIRouter()

@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str):
    """Layer 3: Full call detail with diagnosis."""
    return call_service.get_call_detail(call_id)