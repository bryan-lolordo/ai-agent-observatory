"""
FastAPI Dependencies
Location: api/dependencies.py

Shared dependencies for FastAPI routes.

NOTE: Currently not used - our architecture uses direct function calls.
This file is a placeholder for future enhancements like:
- Database session management
- Authentication
- Rate limiting
- Common query parameters
"""

from typing import Optional
from fastapi import Query


# =============================================================================
# COMMON QUERY PARAMETERS (Not currently used)
# =============================================================================

class CommonQueryParams:
    """
    Common query parameters for story endpoints.
    
    Usage (if we want to refactor later):
        @router.get("/story")
        def get_story(commons: CommonQueryParams = Depends()):
            ...
    """
    def __init__(
        self,
        project: Optional[str] = None,
        days: int = Query(default=7, ge=1, le=90),
        limit: int = Query(default=2000, le=5000),
    ):
        self.project = project
        self.days = days
        self.limit = limit


# =============================================================================
# DATABASE SESSION (Not currently used - we use singleton Storage)
# =============================================================================

# Future: If we want to use dependency injection for database
# from fastapi import Depends
# 
# def get_db():
#     """Get database session."""
#     db = get_storage()
#     try:
#         yield db
#     finally:
#         # Cleanup if needed
#         pass


# =============================================================================
# AUTHENTICATION (Not implemented)
# =============================================================================

# Future: Add API key or JWT authentication
# 
# async def verify_api_key(api_key: str = Header(None)):
#     if api_key != "expected_key":
#         raise HTTPException(status_code=401, detail="Invalid API key")
#     return api_key


# =============================================================================
# RATE LIMITING (Not implemented)
# =============================================================================

# Future: Add rate limiting per IP or API key
#
# def check_rate_limit():
#     # Rate limiting logic
#     pass