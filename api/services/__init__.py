"""
Services Package
Location: api/services/__init__.py

Business logic layer - converts data to response models.
All services return dicts for simplicity.

Complete: All 8 stories implemented.
"""

from .llm_call_service import get_detail as get_llm_call_detail
from .llm_call_service import get_calls as get_llm_calls

# Story 1 - Latency Monster
from .latency_service import get_summary as get_latency_summary

# Story 2 - Cache Strategy
from .cache_service import (
    get_summary as get_cache_summary,
    get_operation_detail as get_cache_operation_detail,
    get_opportunity_detail as get_cache_opportunity_detail,
)

# Story 3 - Model Routing
from .routing_service import (
    get_summary as get_routing_summary,
    get_operation_detail as get_routing_operation_detail,
)

# Story 4 - Quality Monitoring
from .quality_service import (
    get_summary as get_quality_summary,
    get_operation_detail as get_quality_operation_detail,
)

# Story 5 - Token Efficiency
from .token_service import (
    get_summary as get_token_summary,
    get_operation_detail as get_token_operation_detail,
)

# Story 6 - Prompt Composition
from .prompt_service import (
    get_summary as get_prompt_summary,
    get_operation_detail as get_prompt_operation_detail,
)

# Story 7 - Cost Analysis
from .cost_service import (
    get_summary as get_cost_summary,
    get_operation_detail as get_cost_operation_detail,
)

# Story 8 - Optimization Impact
from .optimization_service import (
    get_summary as get_optimization_summary,
)


__all__ = [
    # Layer 3 - Call detail (shared by all stories)
    "get_llm_call_detail",
    "get_llm_calls",
    
    # Story 1 - Latency Monster
    "get_latency_summary",
    
    # Story 2 - Cache Strategy
    "get_cache_summary",
    "get_cache_operation_detail",
    "get_cache_opportunity_detail",
    
    # Story 3 - Model Routing
    "get_routing_summary",
    "get_routing_operation_detail",
    
    # Story 4 - Quality Monitoring
    "get_quality_summary",
    "get_quality_operation_detail",
    
    # Story 5 - Token Efficiency
    "get_token_summary",
    "get_token_operation_detail",
    
    # Story 6 - Prompt Composition
    "get_prompt_summary",
    "get_prompt_operation_detail",
    
    # Story 7 - Cost Analysis
    "get_cost_summary",
    "get_cost_operation_detail",
    
    # Story 8 - Optimization Impact
    "get_optimization_summary",
]