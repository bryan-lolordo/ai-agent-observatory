"""
Routers Package
Location: api/routers/__init__.py

FastAPI routers for all endpoints.
"""

from .stories import router as stories_router
from .metadata import router as metadata_router
from .calls import router as calls_router
from .optimization_queue import router as optimization_queue_router
from .analysis import router as analysis_router

__all__ = [
    "stories_router",
    "metadata_router",
    "calls_router",
    "optimization_queue_router",
    "analysis_router",
]