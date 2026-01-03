"""
FastAPI Dependencies
Location: api/dependencies.py

Shared dependencies for FastAPI routes.
"""

from typing import Optional, Generator
from fastapi import Query
from sqlalchemy.orm import Session

from observatory.storage import ObservatoryStorage


# =============================================================================
# DATABASE SESSION DEPENDENCY
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Yields a SQLAlchemy session and ensures it's closed after use.
    
    Usage:
        @router.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db here
            from observatory.storage import LLMCallDB
            calls = db.query(LLMCallDB).all()
    
    Example:
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from api.dependencies import get_db
        
        @router.get("/calls")
        def get_calls(db: Session = Depends(get_db)):
            return db.query(LLMCallDB).all()
    """
    db = ObservatoryStorage.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# COMMON QUERY PARAMETERS (Optional - for future refactoring)
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
# AUTHENTICATION (Not implemented)
# =============================================================================

# Future: Add API key or JWT authentication
# 
# from fastapi import Header, HTTPException
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