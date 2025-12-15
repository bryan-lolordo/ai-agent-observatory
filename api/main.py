"""
Observatory API - FastAPI Backend
Location: api/main.py

Main FastAPI application with all story endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from api.routers import stories_router, metadata_router


# =============================================================================
# CREATE APP
# =============================================================================

app = FastAPI(
    title="Observatory API",
    description="AI Agent Observatory - LLM Performance Tracking & Optimization",
    version="2.0.0",
)


# =============================================================================
# CORS
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

app.include_router(stories_router)
app.include_router(metadata_router)


# =============================================================================
# ROOT & HEALTH
# =============================================================================

@app.get("/")
def root():
    """Root endpoint - API info."""
    return {
        "name": "Observatory API",
        "version": "2.0.0",
        "description": "AI Agent Observatory - LLM Performance Tracking",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
    }


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )