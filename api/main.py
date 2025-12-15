"""
Observatory API - Production Structure
Location: api/main.py

Minimal FastAPI app with router registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Import routers
from api.routers import stories, calls, metadata

app = FastAPI(
    title="Observatory API",
    description="AI Agent Observatory - LLM Performance Analytics",
    version="2.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(metadata.router, prefix="/api", tags=["metadata"])
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(calls.router, prefix="/api", tags=["calls"])


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)