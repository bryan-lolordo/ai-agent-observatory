"""
AI Agent Observatory - Main Package
Location: /observatory/__init__.py
"""

from observatory.collector import Observatory, MetricsCollector
from observatory.models import (
    Session,
    LLMCall,
    SessionReport,
    ModelProvider,
    AgentRole,
)
from observatory.storage import Storage

__version__ = "0.1.0"

__all__ = [
    "Observatory",
    "MetricsCollector",
    "Session",
    "LLMCall",
    "SessionReport",
    "ModelProvider",
    "AgentRole",
    "Storage",
]