"""
MCP Server Configuration

Centralizes all configurable values for the MCP server.
Values can be overridden via environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelConfig:
    """Model-related configuration."""

    # Models considered "expensive" for routing optimization suggestions
    expensive_models: set[str] = field(default_factory=lambda: {
        "gpt-4o",
        "gpt-4",
        "gpt-4-turbo",
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-3-opus",
        "claude-3-sonnet",
    })

    # Suggested cheaper alternatives for routing
    cheaper_alternatives: dict[str, str] = field(default_factory=lambda: {
        "gpt-4o": "gpt-4o-mini",
        "gpt-4": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4o-mini",
        "claude-opus-4": "claude-haiku",
        "claude-sonnet-4": "claude-haiku",
        "claude-3-opus": "claude-3-haiku",
        "claude-3-sonnet": "claude-3-haiku",
    })

    def is_expensive(self, model_name: str) -> bool:
        """Check if a model is in the expensive tier."""
        return model_name in self.expensive_models

    def get_cheaper_alternative(self, model_name: str) -> str | None:
        """Get a cheaper alternative for a model, if available."""
        return self.cheaper_alternatives.get(model_name)


@dataclass
class SavingsConfig:
    """Savings estimation factors."""

    # Estimated savings when routing to cheaper model (0.7 = 70% savings)
    routing_savings_factor: float = 0.7

    # Estimated savings from token reduction in system prompts
    token_reduction_factor: float = 0.2

    # Estimated savings from context compression
    context_compression_factor: float = 0.3

    # Estimated savings from caching (based on hit rate)
    # Actual savings = cost * (duplicates - 1) / duplicates


@dataclass
class ThresholdsConfig:
    """Detection thresholds for optimization opportunities."""

    # Minimum calls before suggesting routing optimization
    min_calls_for_routing: int = 5

    # Minimum duplicate calls before suggesting caching
    min_duplicates_for_cache: int = 3

    # Minimum calls to analyze for token patterns
    min_calls_for_token_analysis: int = 5

    # System prompt token count considered "bloated"
    system_prompt_bloat_tokens: int = 500

    # Prompt token count suggesting context growth issue
    context_growth_tokens: int = 2000

    # Cache hit rate below this is considered "low"
    low_cache_hit_rate: float = 10.0

    # Minimum savings (dollars) to report an opportunity
    min_savings_to_report: float = 0.01

    # Cost reduction % considered "significant"
    significant_cost_reduction: float = 5.0

    # Latency increase % considered concerning
    concerning_latency_increase: float = 10.0

    # Quality score change considered significant
    significant_quality_change: float = 0.2


@dataclass
class QueryConfig:
    """Query and pagination configuration."""

    # Default query limit if not specified
    default_limit: int = 1000

    # Maximum allowed query limit
    max_limit: int = 10000

    # Default limit for expensive aggregation queries
    aggregation_limit: int = 2000

    # Default limit for list/detail queries
    list_limit: int = 500

    # Default time range if not specified
    default_time_range: str = "7d"

    def clamp_limit(self, requested: int | None) -> int:
        """Clamp a requested limit to valid bounds."""
        if requested is None:
            return self.default_limit
        return max(1, min(requested, self.max_limit))


@dataclass
class MCPConfig:
    """Main configuration container."""

    models: ModelConfig = field(default_factory=ModelConfig)
    savings: SavingsConfig = field(default_factory=SavingsConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    query: QueryConfig = field(default_factory=QueryConfig)

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """
        Create config from environment variables.

        Environment variables (all optional):
            MCP_ROUTING_SAVINGS_FACTOR: float (default 0.7)
            MCP_TOKEN_REDUCTION_FACTOR: float (default 0.2)
            MCP_MIN_CALLS_FOR_ROUTING: int (default 5)
            MCP_MIN_DUPLICATES_FOR_CACHE: int (default 3)
            MCP_SYSTEM_PROMPT_BLOAT_TOKENS: int (default 500)
            MCP_DEFAULT_QUERY_LIMIT: int (default 1000)
            MCP_MAX_QUERY_LIMIT: int (default 10000)
            MCP_DEFAULT_TIME_RANGE: str (default "7d")
        """
        config = cls()

        # Override savings factors
        if val := os.getenv("MCP_ROUTING_SAVINGS_FACTOR"):
            config.savings.routing_savings_factor = float(val)
        if val := os.getenv("MCP_TOKEN_REDUCTION_FACTOR"):
            config.savings.token_reduction_factor = float(val)

        # Override thresholds
        if val := os.getenv("MCP_MIN_CALLS_FOR_ROUTING"):
            config.thresholds.min_calls_for_routing = int(val)
        if val := os.getenv("MCP_MIN_DUPLICATES_FOR_CACHE"):
            config.thresholds.min_duplicates_for_cache = int(val)
        if val := os.getenv("MCP_SYSTEM_PROMPT_BLOAT_TOKENS"):
            config.thresholds.system_prompt_bloat_tokens = int(val)

        # Override query config
        if val := os.getenv("MCP_DEFAULT_QUERY_LIMIT"):
            config.query.default_limit = int(val)
        if val := os.getenv("MCP_MAX_QUERY_LIMIT"):
            config.query.max_limit = int(val)
        if val := os.getenv("MCP_DEFAULT_TIME_RANGE"):
            config.query.default_time_range = val

        return config


# Global config instance - initialized from environment
config = MCPConfig.from_env()


def get_config() -> MCPConfig:
    """Get the global config instance."""
    return config


def reload_config() -> MCPConfig:
    """Reload config from environment variables."""
    global config
    config = MCPConfig.from_env()
    return config
