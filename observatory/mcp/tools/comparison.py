"""
A/B testing and phase comparison tools for MCP.

Tools:
- compare_phases: Compare baseline vs optimized phases
- compare_models: Compare performance across different models
- compare_agents: Compare performance across different agents
"""

from typing import Any

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import (
    parse_time_range,
    tool_handler,
    calculate_change_percent,
    calculate_percentile,
)


@tool_handler
async def compare_phases(
    baseline_session: str | None = None,
    optimized_session: str | None = None,
    time_range: str = "30d",
    storage=None,
) -> dict[str, Any]:
    """
    Compare baseline vs optimized phases to measure optimization impact.

    If session IDs are not provided, automatically identifies baseline
    and optimized phases from the data.

    Args:
        baseline_session: Session ID for baseline phase (optional)
        optimized_session: Session ID for optimized phase (optional)
        time_range: Time range for auto-detection
        storage: Storage instance (injected by server)

    Returns:
        Comparison metrics showing optimization impact
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    all_calls = storage.get_calls(since=cutoff, limit=cfg.query.aggregation_limit)

    if not all_calls:
        return {
            "error": "No calls found for comparison",
            "message": "Track some LLM calls first to enable phase comparison"
        }

    # Separate by phase if metadata available, otherwise split by time
    baseline_calls = []
    optimized_calls = []

    for call in all_calls:
        phase = getattr(call, 'experiment_phase', None) or getattr(call, 'phase', None)
        if phase == 'baseline':
            baseline_calls.append(call)
        elif phase == 'optimized':
            optimized_calls.append(call)

    # If no phase metadata, split by time (first half = baseline, second half = optimized)
    if not baseline_calls and not optimized_calls:
        mid = len(all_calls) // 2
        baseline_calls = all_calls[:mid]
        optimized_calls = all_calls[mid:]

    if not baseline_calls or not optimized_calls:
        return {
            "error": "Could not identify distinct phases",
            "message": "Need calls from both baseline and optimized phases for comparison"
        }

    # Calculate metrics for each phase
    def calc_phase_metrics(calls, phase_name):
        if not calls:
            return None

        total_cost = sum(c.total_cost or 0 for c in calls)
        total_tokens = sum((c.prompt_tokens or 0) + (c.completion_tokens or 0) for c in calls)
        latencies = [c.latency_ms for c in calls if c.latency_ms]
        quality_scores = [c.quality_score for c in calls if getattr(c, 'quality_score', None)]
        cache_hits = sum(1 for c in calls if getattr(c, 'cache_hit', False))
        routing_savings = sum(c.routing_cost_savings or 0 for c in calls)

        return {
            "phase_name": phase_name,
            "call_count": len(calls),
            "total_cost": round(total_cost, 4),
            "avg_cost_per_call": round(total_cost / len(calls), 6) if calls else 0,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "p95_latency_ms": round(calculate_percentile(latencies, 95), 2) if latencies else 0,
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
            "cache_hit_rate": round(cache_hits / len(calls) * 100, 2) if calls else 0,
            "routing_savings": round(routing_savings, 4),
            "error_rate": round(sum(1 for c in calls if not c.success) / len(calls) * 100, 2) if calls else 0,
        }

    baseline = calc_phase_metrics(baseline_calls, "baseline")
    optimized = calc_phase_metrics(optimized_calls, "optimized")

    # Calculate improvements using utility
    cost_reduction = calculate_change_percent(baseline["total_cost"], optimized["total_cost"]) * -1  # Invert for "reduction"
    latency_change = calculate_change_percent(baseline["avg_latency_ms"], optimized["avg_latency_ms"])

    quality_change = None
    if baseline["avg_quality_score"] and optimized["avg_quality_score"]:
        quality_change = optimized["avg_quality_score"] - baseline["avg_quality_score"]

    cache_improvement = optimized["cache_hit_rate"] - baseline["cache_hit_rate"]

    # Generate summary using config thresholds
    improvements = []
    concerns = []

    if cost_reduction > cfg.thresholds.significant_cost_reduction:
        improvements.append(f"Cost reduced by {cost_reduction:.1f}%")
    elif cost_reduction < -cfg.thresholds.significant_cost_reduction:
        concerns.append(f"Cost increased by {abs(cost_reduction):.1f}%")

    if latency_change < -cfg.thresholds.concerning_latency_increase:
        improvements.append(f"Latency improved by {abs(latency_change):.1f}%")
    elif latency_change > cfg.thresholds.concerning_latency_increase:
        concerns.append(f"Latency degraded by {latency_change:.1f}%")

    if cache_improvement > 5:
        improvements.append(f"Cache hit rate improved by {cache_improvement:.1f}%")

    if quality_change is not None:
        if quality_change > cfg.thresholds.significant_quality_change:
            improvements.append(f"Quality improved by {quality_change:.2f} points")
        elif quality_change < -cfg.thresholds.significant_quality_change:
            concerns.append(f"Quality decreased by {abs(quality_change):.2f} points")

    if improvements and not concerns:
        summary = "Optimizations are working well. " + " ".join(improvements)
        recommendation = "Continue with current optimization strategy."
    elif concerns and not improvements:
        summary = "Optimization may need adjustment. " + " ".join(concerns)
        recommendation = "Review optimization settings and consider rollback."
    elif improvements and concerns:
        summary = "Mixed results. Improvements: " + ", ".join(improvements) + ". Concerns: " + ", ".join(concerns)
        recommendation = "Fine-tune optimizations to address concerns while maintaining gains."
    else:
        summary = "No significant difference between phases."
        recommendation = "Consider more aggressive optimization or longer evaluation period."

    return {
        "baseline": baseline,
        "optimized": optimized,
        "comparison": {
            "cost_reduction_percent": round(cost_reduction, 2),
            "latency_change_percent": round(latency_change, 2),
            "quality_change": round(quality_change, 2) if quality_change else None,
            "cache_improvement_percent": round(cache_improvement, 2),
            "routing_impact": round(optimized["routing_savings"], 4),
        },
        "summary": summary,
        "recommendation": recommendation,
    }


@tool_handler
async def compare_models(
    models: list[str] | None = None,
    operation: str | None = None,
    time_range: str = "7d",
    storage=None,
) -> dict[str, Any]:
    """
    Compare performance across different models.

    Args:
        models: List of model names to compare (optional, auto-detect if not provided)
        operation: Filter by specific operation
        time_range: Time period to analyze
        storage: Storage instance (injected by server)

    Returns:
        Model comparison with cost, latency, and quality metrics
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if operation:
        calls = [c for c in calls if c.operation == operation]

    if not calls:
        return {"error": "No calls found for comparison"}

    # Group by model
    model_calls: dict[str, list] = {}
    for call in calls:
        model = call.model_name or "unknown"
        if models and model not in models:
            continue
        if model not in model_calls:
            model_calls[model] = []
        model_calls[model].append(call)

    # Calculate metrics for each model
    model_metrics = []
    for model, calls_list in model_calls.items():
        total_cost = sum(c.total_cost or 0 for c in calls_list)
        latencies = [c.latency_ms for c in calls_list if c.latency_ms]
        quality_scores = [c.quality_score for c in calls_list if getattr(c, 'quality_score', None)]

        model_metrics.append({
            "model": model,
            "call_count": len(calls_list),
            "total_cost": round(total_cost, 4),
            "avg_cost_per_call": round(total_cost / len(calls_list), 6),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
            "error_rate": round(sum(1 for c in calls_list if not c.success) / len(calls_list) * 100, 2),
        })

    # Sort by cost efficiency (quality per dollar if available)
    model_metrics.sort(key=lambda x: x["avg_cost_per_call"])

    # Determine best performers
    cheapest = min(model_metrics, key=lambda x: x["avg_cost_per_call"])
    fastest = min(model_metrics, key=lambda x: x["avg_latency_ms"])
    quality_models = [m for m in model_metrics if m["avg_quality_score"]]
    highest_quality = max(quality_models, key=lambda x: x["avg_quality_score"]) if quality_models else None

    return {
        "models": model_metrics,
        "best_performers": {
            "cheapest": cheapest["model"],
            "fastest": fastest["model"],
            "highest_quality": highest_quality["model"] if highest_quality else None,
        },
        "recommendation": f"For cost optimization, consider using {cheapest['model']}. For speed, use {fastest['model']}.",
    }


@tool_handler
async def compare_agents(
    agents: list[str] | None = None,
    time_range: str = "7d",
    storage=None,
) -> dict[str, Any]:
    """
    Compare performance across different agents.

    Args:
        agents: List of agent names to compare (optional)
        time_range: Time period to analyze
        storage: Storage instance (injected by server)

    Returns:
        Agent comparison with efficiency metrics
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if not calls:
        return {"error": "No calls found for comparison"}

    # Group by agent
    agent_calls: dict[str, list] = {}
    for call in calls:
        agent = call.agent_name or "unknown"
        if agents and agent not in agents:
            continue
        if agent not in agent_calls:
            agent_calls[agent] = []
        agent_calls[agent].append(call)

    # Calculate metrics for each agent
    agent_metrics = []
    for agent, calls_list in agent_calls.items():
        total_cost = sum(c.total_cost or 0 for c in calls_list)
        total_tokens = sum((c.prompt_tokens or 0) + (c.completion_tokens or 0) for c in calls_list)
        latencies = [c.latency_ms for c in calls_list if c.latency_ms]
        quality_scores = [c.quality_score for c in calls_list if getattr(c, 'quality_score', None)]
        cache_hits = sum(1 for c in calls_list if getattr(c, 'cache_hit', False))

        # Get unique operations for this agent
        operations = list(set(c.operation for c in calls_list if c.operation))

        agent_metrics.append({
            "agent": agent,
            "call_count": len(calls_list),
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
            "cache_hit_rate": round(cache_hits / len(calls_list) * 100, 2),
            "error_rate": round(sum(1 for c in calls_list if not c.success) / len(calls_list) * 100, 2),
            "operations": operations[:5],
        })

    # Sort by total cost
    agent_metrics.sort(key=lambda x: x["total_cost"], reverse=True)

    # Identify optimization targets
    avg_cost = sum(m["total_cost"] for m in agent_metrics) / len(agent_metrics) if agent_metrics else 0
    high_cost_agents = [a for a in agent_metrics if a["total_cost"] > avg_cost]

    return {
        "agents": agent_metrics,
        "total_agents": len(agent_metrics),
        "optimization_targets": [a["agent"] for a in high_cost_agents],
        "recommendation": f"Focus optimization on: {', '.join(a['agent'] for a in high_cost_agents[:3])}" if high_cost_agents else "All agents are within normal cost range.",
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

COMPARISON_TOOLS = [
    ToolDefinition(
        name="compare_phases",
        description="Compare baseline vs optimized phases to measure the impact of optimizations. Shows cost reduction, latency changes, and quality differences.",
        parameters={
            "type": "object",
            "properties": {
                "baseline_session": {
                    "type": "string",
                    "description": "Session ID for baseline phase (optional, auto-detect if not provided)"
                },
                "optimized_session": {
                    "type": "string",
                    "description": "Session ID for optimized phase (optional)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for auto-detection",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "30d"
                }
            }
        },
        handler=compare_phases,
        category="comparison"
    ),
    ToolDefinition(
        name="compare_models",
        description="Compare performance across different LLM models. Shows cost, latency, and quality metrics for each model.",
        parameters={
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of model names to compare (optional)"
                },
                "operation": {
                    "type": "string",
                    "description": "Filter by specific operation (optional)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                }
            }
        },
        handler=compare_models,
        category="comparison"
    ),
    ToolDefinition(
        name="compare_agents",
        description="Compare performance across different agents. Identifies high-cost agents and optimization targets.",
        parameters={
            "type": "object",
            "properties": {
                "agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of agent names to compare (optional)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                }
            }
        },
        handler=compare_agents,
        category="comparison"
    ),
]
