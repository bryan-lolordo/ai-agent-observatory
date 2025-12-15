"""
Services Package
Location: api/services/__init__.py

Business logic layer - converts data to response models.
All services return proper Pydantic models.
"""

from .call_service import get_call_detail
from .latency_service import get_summary as get_latency_summary
from .cache_service import get_summary as get_cache_summary
from .routing_service import get_summary as get_routing_summary
from .quality_service import get_summary as get_quality_summary
from .token_service import get_summary as get_token_summary
from .prompt_service import get_summary as get_prompt_summary
from .cost_service import get_summary as get_cost_summary
from .optimization_service import get_summary as get_optimization_summary

__all__ = [
    # Layer 3 - Call detail (shared by all stories)
    "get_call_detail",
    
    # Layer 1 & 2 - Story summaries
    "get_latency_summary",      # Story 1
    "get_cache_summary",         # Story 2
    "get_routing_summary",       # Story 3
    "get_quality_summary",       # Story 4
    "get_token_summary",         # Story 5
    "get_prompt_summary",        # Story 6
    "get_cost_summary",          # Story 7
    "get_optimization_summary",  # Story 8
]