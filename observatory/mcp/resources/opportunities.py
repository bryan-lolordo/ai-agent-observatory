"""
Optimization opportunity resources for MCP.

Resources:
- observatory://optimization-stories: Live list of pending optimizations
- observatory://cost-alerts: Cost threshold alerts
"""

import json
from typing import Any
from datetime import datetime, timedelta

from observatory.mcp.types import ResourceDefinition


async def get_optimization_stories(storage=None) -> str:
    """
    Get live optimization stories (pending improvements).

    Returns JSON with all tracked optimization opportunities,
    their potential savings, and implementation status.
    """
    if storage is None:
        return json.dumps({"error": "Storage not configured"})

    # Get recent calls for analysis
    cutoff = datetime.utcnow() - timedelta(days=30)
    calls = storage.get_calls(since=cutoff)

    if not calls:
        return json.dumps({
            "stories": [],
            "total_count": 0,
            "total_potential_savings": 0.0,
            "last_updated": datetime.utcnow().isoformat(),
        })

    stories = []

    # ========================================================================
    # Story 1: Model Routing Opportunities
    # ========================================================================
    expensive_models = {"gpt-4o", "gpt-4", "claude-opus-4", "claude-sonnet-4"}
    routing_candidates = {}

    for call in calls:
        model = call.model_name or "unknown"
        if model in expensive_models:
            op = call.operation or "unknown"
            if op not in routing_candidates:
                routing_candidates[op] = {"count": 0, "cost": 0.0}
            routing_candidates[op]["count"] += 1
            routing_candidates[op]["cost"] += call.total_cost or 0

    for op, data in routing_candidates.items():
        if data["count"] >= 5:
            savings = data["cost"] * 0.7  # Estimate 70% savings with routing
            stories.append({
                "id": f"routing-{op}",
                "type": "routing",
                "title": f"Route '{op}' to cheaper model",
                "description": f"{data['count']} calls using expensive models. Consider routing to gpt-4o-mini or claude-haiku.",
                "potential_monthly_savings": round(savings, 2),
                "call_count": data["count"],
                "status": "pending",
                "priority": "high" if savings > 1.0 else "medium",
            })

    # ========================================================================
    # Story 2: Caching Opportunities
    # ========================================================================
    prompt_hashes: dict[str, list] = {}
    for call in calls:
        if call.prompt:
            key = call.prompt[:100].strip().lower()
            if key not in prompt_hashes:
                prompt_hashes[key] = []
            prompt_hashes[key].append(call)

    for key, group in prompt_hashes.items():
        if len(group) >= 3:
            total_cost = sum(c.total_cost or 0 for c in group)
            savings = total_cost * ((len(group) - 1) / len(group))
            if savings > 0.01:  # At least 1 cent savings
                stories.append({
                    "id": f"cache-{hash(key) % 10000}",
                    "type": "caching",
                    "title": f"Cache '{group[0].operation or 'unknown'}' prompts",
                    "description": f"{len(group)} duplicate/similar calls detected. Enable caching to eliminate redundant API calls.",
                    "potential_monthly_savings": round(savings, 2),
                    "call_count": len(group),
                    "status": "pending",
                    "priority": "high" if savings > 0.5 else "medium",
                })

    # ========================================================================
    # Story 3: Token Efficiency Opportunities
    # ========================================================================
    op_tokens: dict[str, list] = {}
    for call in calls:
        op = call.operation or "unknown"
        if op not in op_tokens:
            op_tokens[op] = []
        op_tokens[op].append({
            "system": call.system_tokens or 0,
            "prompt": call.prompt_tokens or 0,
            "cost": call.total_cost or 0,
        })

    for op, tokens in op_tokens.items():
        if len(tokens) >= 5:
            avg_system = sum(t["system"] for t in tokens) / len(tokens)
            total_cost = sum(t["cost"] for t in tokens)

            if avg_system > 500:
                savings = total_cost * 0.2
                if savings > 0.01:
                    stories.append({
                        "id": f"tokens-system-{op}",
                        "type": "token_efficiency",
                        "title": f"Reduce system prompt for '{op}'",
                        "description": f"System prompt averages {int(avg_system)} tokens. Consider condensing to ~300 tokens.",
                        "potential_monthly_savings": round(savings, 2),
                        "call_count": len(tokens),
                        "status": "pending",
                        "priority": "medium",
                    })

    # Sort by potential savings
    stories.sort(key=lambda x: x["potential_monthly_savings"], reverse=True)

    total_savings = sum(s["potential_monthly_savings"] for s in stories)

    return json.dumps({
        "stories": stories[:50],  # Limit to top 50
        "total_count": len(stories),
        "total_potential_savings": round(total_savings, 2),
        "by_type": {
            "routing": len([s for s in stories if s["type"] == "routing"]),
            "caching": len([s for s in stories if s["type"] == "caching"]),
            "token_efficiency": len([s for s in stories if s["type"] == "token_efficiency"]),
        },
        "last_updated": datetime.utcnow().isoformat(),
    }, indent=2)


async def get_cost_alerts(
    threshold: float = 10.0,
    storage=None,
) -> str:
    """
    Get cost threshold alerts.

    Returns JSON with operations/agents exceeding cost thresholds.
    """
    if storage is None:
        return json.dumps({"error": "Storage not configured"})

    cutoff = datetime.utcnow() - timedelta(days=7)
    calls = storage.get_calls(since=cutoff)

    alerts = []

    # Check by operation
    op_costs: dict[str, float] = {}
    for call in calls:
        op = call.operation or "unknown"
        op_costs[op] = op_costs.get(op, 0) + (call.total_cost or 0)

    for op, cost in op_costs.items():
        if cost > threshold:
            alerts.append({
                "type": "operation_cost",
                "operation": op,
                "cost": round(cost, 2),
                "threshold": threshold,
                "severity": "high" if cost > threshold * 2 else "medium",
                "message": f"Operation '{op}' has cost ${cost:.2f} in the last 7 days (threshold: ${threshold:.2f})",
            })

    # Check by agent
    agent_costs: dict[str, float] = {}
    for call in calls:
        agent = call.agent_name or "unknown"
        agent_costs[agent] = agent_costs.get(agent, 0) + (call.total_cost or 0)

    for agent, cost in agent_costs.items():
        if cost > threshold:
            alerts.append({
                "type": "agent_cost",
                "agent": agent,
                "cost": round(cost, 2),
                "threshold": threshold,
                "severity": "high" if cost > threshold * 2 else "medium",
                "message": f"Agent '{agent}' has cost ${cost:.2f} in the last 7 days (threshold: ${threshold:.2f})",
            })

    return json.dumps({
        "alerts": alerts,
        "total_alerts": len(alerts),
        "threshold": threshold,
        "period": "7d",
        "last_checked": datetime.utcnow().isoformat(),
    }, indent=2)


# ============================================================================
# Resource Definitions for Registration
# ============================================================================

OPPORTUNITY_RESOURCES = [
    ResourceDefinition(
        uri="observatory://optimization-stories",
        name="Optimization Stories",
        description="Live list of pending optimization opportunities with potential savings estimates. Updates as new patterns are detected.",
        mime_type="application/json",
        handler=get_optimization_stories,
    ),
    ResourceDefinition(
        uri="observatory://cost-alerts",
        name="Cost Alerts",
        description="Cost threshold alerts for operations and agents exceeding spending limits.",
        mime_type="application/json",
        handler=get_cost_alerts,
    ),
]
