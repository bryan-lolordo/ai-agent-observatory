"""
Cost analysis tools for MCP.

Tools:
- get_cost_summary: Get cost breakdown by model/agent/operation
- get_cost_trend: Analyze cost trends over time
- get_expensive_calls: Find the most expensive LLM calls
"""

from typing import Any

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import (
    parse_time_range,
    tool_handler,
    calculate_change_percent,
    aggregate_by_key,
)


@tool_handler
async def get_cost_summary(
    time_range: str = "7d",
    group_by: str = "model",
    storage=None,
) -> dict[str, Any]:
    """
    Get cost breakdown by model, agent, or operation.

    Args:
        time_range: Time period to analyze ("24h", "7d", "30d", "all")
        group_by: How to group costs ("model", "agent", "operation")
        storage: Storage instance (injected by server)

    Returns:
        Cost summary with breakdown and trends
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if not calls:
        return {
            "total_cost": 0.0,
            "total_calls": 0,
            "time_range": time_range,
            "breakdown": [],
            "top_expensive_operations": [],
            "cost_trend": "stable",
            "message": "No calls found in the specified time range"
        }

    # Aggregate by group_by field
    aggregated: dict[str, dict] = {}
    total_cost = 0.0

    for call in calls:
        cost = call.total_cost or 0.0
        total_cost += cost

        # Get the grouping key
        match group_by:
            case "model":
                key = call.model_name or "unknown"
            case "agent":
                key = call.agent_name or "unknown"
            case "operation":
                key = call.operation or "unknown"
            case _:
                key = call.model_name or "unknown"

        if key not in aggregated:
            aggregated[key] = {"cost": 0.0, "count": 0}

        aggregated[key]["cost"] += cost
        aggregated[key]["count"] += 1

    # Build breakdown
    breakdown = []
    for category, data in sorted(aggregated.items(), key=lambda x: x[1]["cost"], reverse=True):
        breakdown.append({
            "category": category,
            "total_cost": round(data["cost"], 6),
            "call_count": data["count"],
            "avg_cost_per_call": round(data["cost"] / data["count"], 6) if data["count"] > 0 else 0,
            "percentage_of_total": round((data["cost"] / total_cost) * 100, 2) if total_cost > 0 else 0,
        })

    # Find top expensive operations
    operation_costs: dict[str, float] = {}
    for call in calls:
        op = call.operation or "unknown"
        operation_costs[op] = operation_costs.get(op, 0) + (call.total_cost or 0)

    top_operations = [
        {"operation": op, "total_cost": round(cost, 6)}
        for op, cost in sorted(operation_costs.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # Trend detection using config thresholds
    cost_trend = "stable"
    if len(calls) >= 10:
        mid = len(calls) // 2
        first_half_cost = sum(c.total_cost or 0 for c in calls[:mid])
        second_half_cost = sum(c.total_cost or 0 for c in calls[mid:])
        change_percent = calculate_change_percent(first_half_cost, second_half_cost)

        if change_percent > cfg.thresholds.significant_cost_reduction:
            cost_trend = "increasing"
        elif change_percent < -cfg.thresholds.significant_cost_reduction:
            cost_trend = "decreasing"

    return {
        "total_cost": round(total_cost, 6),
        "total_calls": len(calls),
        "time_range": time_range,
        "group_by": group_by,
        "breakdown": breakdown,
        "top_expensive_operations": top_operations,
        "cost_trend": cost_trend,
    }


@tool_handler
async def get_cost_trend(
    time_range: str = "30d",
    granularity: str = "day",
    storage=None,
) -> dict[str, Any]:
    """
    Analyze cost trends over time.

    Args:
        time_range: Time period to analyze ("7d", "30d", "all")
        granularity: Time buckets ("hour", "day", "week")
        storage: Storage instance (injected by server)

    Returns:
        Cost trend data with daily/weekly breakdowns
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if not calls:
        return {
            "time_range": time_range,
            "granularity": granularity,
            "data_points": [],
            "trend": "stable",
            "message": "No calls found"
        }

    # Group by date
    daily_costs: dict[str, float] = {}
    for call in calls:
        if call.timestamp:
            date_key = call.timestamp.strftime("%Y-%m-%d")
            daily_costs[date_key] = daily_costs.get(date_key, 0) + (call.total_cost or 0)

    data_points = [
        {"date": date, "cost": round(cost, 6)}
        for date, cost in sorted(daily_costs.items())
    ]

    return {
        "time_range": time_range,
        "granularity": granularity,
        "data_points": data_points,
        "total_cost": round(sum(daily_costs.values()), 6),
        "avg_daily_cost": round(sum(daily_costs.values()) / len(daily_costs), 6) if daily_costs else 0,
    }


@tool_handler
async def get_expensive_calls(
    time_range: str = "30d",
    limit: int = 10,
    min_cost: float = 0.0,
    storage=None,
) -> dict[str, Any]:
    """
    Find the most expensive LLM calls.

    Args:
        time_range: Time period to search ("24h", "7d", "30d", "all")
        limit: Maximum number of calls to return
        min_cost: Minimum cost threshold
        storage: Storage instance (injected by server)

    Returns:
        List of expensive calls with details
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.list_limit)

    # Filter and sort by cost
    expensive = [c for c in calls if (c.total_cost or 0) >= min_cost]
    expensive.sort(key=lambda x: x.total_cost or 0, reverse=True)
    expensive = expensive[:limit]

    return {
        "time_range": time_range,
        "calls": [
            {
                "call_id": str(c.id) if hasattr(c, 'id') else None,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "model": c.model_name,
                "operation": c.operation,
                "agent": c.agent_name,
                "total_cost": round(c.total_cost or 0, 6),
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "latency_ms": c.latency_ms,
            }
            for c in expensive
        ],
        "total_returned": len(expensive),
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

COST_TOOLS = [
    ToolDefinition(
        name="get_cost_summary",
        description="Get LLM cost breakdown by model, agent, or operation. Shows total spend, per-category costs, and identifies expensive operations.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                },
                "group_by": {
                    "type": "string",
                    "description": "How to group costs",
                    "enum": ["model", "agent", "operation"],
                    "default": "model"
                }
            }
        },
        handler=get_cost_summary,
        category="cost"
    ),
    ToolDefinition(
        name="get_cost_trend",
        description="Analyze cost trends over time. Shows daily/weekly cost patterns to identify spending increases or decreases.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["7d", "30d", "all"],
                    "default": "30d"
                },
                "granularity": {
                    "type": "string",
                    "description": "Time bucket size",
                    "enum": ["hour", "day", "week"],
                    "default": "day"
                }
            }
        },
        handler=get_cost_trend,
        category="cost"
    ),
    ToolDefinition(
        name="get_expensive_calls",
        description="Find the most expensive individual LLM calls. Useful for identifying outliers and optimization targets.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to search",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "30d"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of calls to return",
                    "default": 10
                },
                "min_cost": {
                    "type": "number",
                    "description": "Minimum cost threshold in dollars",
                    "default": 0.0
                }
            }
        },
        handler=get_expensive_calls,
        category="cost"
    ),
]
