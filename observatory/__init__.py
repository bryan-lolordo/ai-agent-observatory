"""
AI Agent Observatory - Complete SDK Package
Location: observatory/__init__.py

Comprehensive monitoring and optimization toolkit for AI/LLM applications.

Core Components:
- Observatory: Main tracking interface
- LLMJudge: Quality evaluation with LLM-as-judge
- CacheManager: Response caching with tracking
- ModelRouter: Intelligent model selection
- PromptManager: Template versioning and A/B testing

Usage:
    from observatory import (
        Observatory,
        LLMJudge,
        CacheManager,
        ModelRouter,
        PromptManager,
    )
    
    # Initialize
    obs = Observatory(project_name="My App")
    judge = LLMJudge(observatory=obs, operations={"chat", "analyze"})
    cache = CacheManager(observatory=obs, operations={"search": {"ttl": 3600}})
    router = ModelRouter(observatory=obs, default_model="gpt-4o-mini")
    prompts = PromptManager(observatory=obs)
"""

__version__ = "0.2.0"

# =============================================================================
# CORE IMPORTS
# =============================================================================

from observatory.collector import (
    Observatory,
    MetricsCollector,
    calculate_cost,
    generate_prompt_hash,
)

from observatory.storage import Storage

# =============================================================================
# MODEL IMPORTS
# =============================================================================

from observatory.models import (
    # Core models
    Session,
    LLMCall,
    SessionReport,
    
    # Enums
    ModelProvider,
    AgentRole,
    
    # Tracking metadata
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    PromptBreakdown,
    PromptMetadata,
    
    # Breakdown models
    CostBreakdown,
    LatencyBreakdown,
    TokenBreakdown,
    QualityMetrics,
    RoutingMetrics,
    CacheMetrics,
    OptimizationSuggestion,
)

# =============================================================================
# SDK COMPONENT IMPORTS
# =============================================================================

from observatory.judge import (
    LLMJudge,
    create_quality_evaluation,
)

from observatory.cache import (
    CacheManager,
    CacheEntry,
    create_cache_metadata,
)

from observatory.router import (
    ModelRouter,
    RoutingRule,
    create_routing_decision,
)

from observatory.prompts import (
    PromptManager,
    PromptTemplate,
    create_prompt_metadata,
    create_prompt_breakdown,
    estimate_tokens,
)

# =============================================================================
# CONVENIENCE FUNCTION: track_llm_call
# =============================================================================

def track_llm_call(
    observatory: Observatory,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    provider: ModelProvider = ModelProvider.OPENAI,
    agent_name: str = None,
    operation: str = None,
    prompt: str = None,
    response_text: str = None,
    success: bool = True,
    error: str = None,
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    prompt_breakdown: PromptBreakdown = None,
    prompt_metadata: PromptMetadata = None,
    prompt_variant_id: str = None,
    metadata: dict = None,
) -> LLMCall:
    """
    Convenience function to track an LLM call.
    
    Args:
        observatory: Observatory instance
        model_name: Name of the model used
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        latency_ms: Response time in milliseconds
        provider: Model provider (OPENAI, AZURE, ANTHROPIC)
        agent_name: Name of the agent/plugin
        operation: Operation name
        prompt: Prompt text
        response_text: Response text
        success: Whether call succeeded
        error: Error message if failed
        routing_decision: Routing metadata
        cache_metadata: Cache metadata
        quality_evaluation: Quality evaluation
        prompt_breakdown: Prompt component breakdown
        prompt_metadata: Prompt template metadata
        prompt_variant_id: A/B test variant ID
        metadata: Additional metadata dict
    
    Returns:
        LLMCall object
    """
    return observatory.record_call(
        provider=provider,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        agent_name=agent_name,
        operation=operation,
        prompt=prompt,
        response_text=response_text,
        success=success,
        error=error,
        routing_decision=routing_decision,
        cache_metadata=cache_metadata,
        quality_evaluation=quality_evaluation,
        prompt_breakdown=prompt_breakdown,
        prompt_metadata=prompt_metadata,
        prompt_variant_id=prompt_variant_id,
        metadata=metadata or {},
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Version
    "__version__",
    
    # Core classes
    "Observatory",
    "MetricsCollector",
    "Storage",
    
    # SDK components
    "LLMJudge",
    "CacheManager",
    "CacheEntry",
    "ModelRouter",
    "RoutingRule",
    "PromptManager",
    "PromptTemplate",
    
    # Models
    "Session",
    "LLMCall",
    "SessionReport",
    "ModelProvider",
    "AgentRole",
    "RoutingDecision",
    "CacheMetadata",
    "QualityEvaluation",
    "PromptBreakdown",
    "PromptMetadata",
    "CostBreakdown",
    "LatencyBreakdown",
    "TokenBreakdown",
    "QualityMetrics",
    "RoutingMetrics",
    "CacheMetrics",
    "OptimizationSuggestion",
    
    # Convenience functions
    "track_llm_call",
    "create_quality_evaluation",
    "create_cache_metadata",
    "create_routing_decision",
    "create_prompt_metadata",
    "create_prompt_breakdown",
    "estimate_tokens",
    "calculate_cost",
    "generate_prompt_hash",
]