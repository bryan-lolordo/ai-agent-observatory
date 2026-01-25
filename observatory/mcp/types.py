"""
Shared types and response models for MCP tools and resources.
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class TimeRange(str, Enum):
    """Supported time ranges for queries."""
    HOUR_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    ALL = "all"


class GroupBy(str, Enum):
    """Grouping options for aggregations."""
    MODEL = "model"
    AGENT = "agent"
    OPERATION = "operation"
    SESSION = "session"


class OptimizationCategory(str, Enum):
    """Categories of optimization opportunities."""
    ROUTING = "routing"
    CACHING = "caching"
    TOKENS = "tokens"
    BATCHING = "batching"
    ALL = "all"


class CacheType(str, Enum):
    """Types of caching strategies."""
    EXACT = "exact"
    SEMANTIC = "semantic"
    PREFIX = "prefix"
    ALL = "all"


# ============================================================================
# Response Models
# ============================================================================

@dataclass
class CostBreakdown:
    """Cost breakdown for a single category."""
    category: str
    total_cost: float
    call_count: int
    avg_cost_per_call: float
    percentage_of_total: float


@dataclass
class CostSummary:
    """Complete cost summary response."""
    total_cost: float
    total_calls: int
    time_range: str
    breakdown: list[CostBreakdown]
    top_expensive_operations: list[dict[str, Any]]
    cost_trend: str  # "increasing", "decreasing", "stable"


@dataclass
class RoutingOptimization:
    """A single routing optimization opportunity."""
    current_model: str
    suggested_model: str
    operation: str
    call_count: int
    estimated_monthly_savings: float
    reasoning: str
    rule_triggered: str | None = None
    confidence: float = 0.0


@dataclass
class CachingOptimization:
    """A single caching optimization opportunity."""
    cache_cluster: str
    unique_prompts: int
    duplicate_calls: int
    potential_hit_rate: float
    estimated_monthly_savings: float
    normalization_strategy: str


@dataclass
class TokenOptimization:
    """A single token efficiency optimization."""
    operation: str
    issue_type: str  # "system_prompt_bloat", "context_growth", "redundant_tokens"
    current_avg_tokens: int
    suggested_avg_tokens: int
    estimated_monthly_savings: float
    recommendation: str


@dataclass
class OptimizationOpportunities:
    """Complete optimization opportunities response."""
    total_opportunities: int
    total_potential_savings: float
    routing_optimizations: list[RoutingOptimization]
    caching_optimizations: list[CachingOptimization]
    token_optimizations: list[TokenOptimization]
    priority_recommendation: str


@dataclass
class RoutingDecisionDetail:
    """Details of a routing decision made."""
    timestamp: str
    operation: str
    original_model: str
    routed_model: str
    cost_saved: float
    rule_triggered: str
    complexity_score: float


@dataclass
class RoutingAnalysis:
    """Complete routing analysis response."""
    total_routing_decisions: int
    total_savings: float
    savings_by_operation: dict[str, float]
    top_rules_triggered: list[dict[str, Any]]
    recent_decisions: list[RoutingDecisionDetail]
    recommendation: str


@dataclass
class CacheStats:
    """Statistics for a cache type."""
    cache_type: str
    total_lookups: int
    hits: int
    misses: int
    hit_rate: float
    estimated_savings: float


@dataclass
class CacheAnalysis:
    """Complete cache effectiveness response."""
    overall_hit_rate: float
    total_cache_savings: float
    stats_by_type: list[CacheStats]
    cacheable_patterns: list[dict[str, Any]]
    recommendations: list[str]


@dataclass
class PhaseMetrics:
    """Metrics for a single phase (baseline or optimized)."""
    phase_name: str
    session_count: int
    total_calls: int
    total_cost: float
    avg_latency_ms: float
    avg_quality_score: float | None
    cache_hit_rate: float
    routing_savings: float


@dataclass
class PhaseComparison:
    """Comparison between baseline and optimized phases."""
    baseline: PhaseMetrics
    optimized: PhaseMetrics
    cost_reduction_percent: float
    latency_change_percent: float
    quality_change: float | None
    cache_improvement: float
    routing_impact: float
    summary: str
    recommendation: str


@dataclass
class SessionSummary:
    """Summary of a tracking session."""
    session_id: str
    started_at: str
    ended_at: str | None
    status: str
    total_calls: int
    total_cost: float
    total_tokens: int
    avg_latency_ms: float
    cache_hit_rate: float
    routing_savings: float
    quality_score: float | None


@dataclass
class QualityEvaluation:
    """Quality evaluation result."""
    call_id: str
    timestamp: str
    operation: str
    agent_name: str
    quality_score: float
    correctness: float | None
    helpfulness: float | None
    safety: float | None
    hallucination_detected: bool
    evaluation_notes: str | None


@dataclass
class QualityAnalysis:
    """Complete quality analysis response."""
    avg_quality_score: float
    total_evaluations: int
    hallucination_rate: float
    score_distribution: dict[str, int]
    low_quality_calls: list[QualityEvaluation]
    quality_by_agent: dict[str, float]
    quality_by_operation: dict[str, float]
    recommendations: list[str]


# ============================================================================
# Tool Registration Helpers
# ============================================================================

@dataclass
class ToolDefinition:
    """Definition of an MCP tool for registration."""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: callable
    category: str = "general"


@dataclass
class ResourceDefinition:
    """Definition of an MCP resource for registration."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    handler: callable = None


@dataclass
class PromptDefinition:
    """Definition of an MCP prompt template for registration."""
    name: str
    description: str
    template: str
    arguments: list[dict[str, Any]] | None = None  # Optional arguments the prompt accepts
    category: str = "general"
