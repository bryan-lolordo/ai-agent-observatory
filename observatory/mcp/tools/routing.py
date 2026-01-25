"""
Model routing analysis tools for MCP.

Tools:
- analyze_routing_savings: Analyze model routing effectiveness and savings
- get_routing_decisions: List recent routing decisions
"""

from typing import Any

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import parse_time_range, tool_handler


@tool_handler
async def analyze_routing_savings(
    operation: str | None = None,
    time_range: str = "7d",
    storage=None,
) -> dict[str, Any]:
    """
    Analyze model routing effectiveness and cost savings.

    Shows how intelligent model routing has saved costs by selecting
    appropriate models for different task complexities.

    Args:
        operation: Filter by specific operation (optional)
        time_range: Time period to analyze ("24h", "7d", "30d", "all")
        storage: Storage instance (injected by server)

    Returns:
        Routing analysis with savings breakdown and recommendations
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if operation:
        calls = [c for c in calls if c.operation == operation]

    if not calls:
        return {
            "total_routing_decisions": 0,
            "total_savings": 0.0,
            "message": "No routing data found for the specified criteria"
        }

    # Analyze routing decisions
    routing_decisions = []
    total_savings = 0.0
    savings_by_operation: dict[str, float] = {}
    savings_by_rule: dict[str, float] = {}
    model_transitions: dict[str, int] = {}

    for call in calls:
        # Check if this call had routing metadata
        routing_savings = call.routing_cost_savings or 0
        if routing_savings > 0 or (hasattr(call, 'routing_decision') and call.routing_decision):
            total_savings += routing_savings

            op = call.operation or "unknown"
            savings_by_operation[op] = savings_by_operation.get(op, 0) + routing_savings

            # Track model transitions
            if hasattr(call, 'routing_decision') and call.routing_decision:
                rd = call.routing_decision
                original = rd.get('original_model', 'unknown')
                routed = rd.get('routed_model', call.model_name)
                rule = rd.get('rule_triggered', 'auto')

                transition_key = f"{original} → {routed}"
                model_transitions[transition_key] = model_transitions.get(transition_key, 0) + 1
                savings_by_rule[rule] = savings_by_rule.get(rule, 0) + routing_savings

                routing_decisions.append({
                    "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                    "operation": op,
                    "original_model": original,
                    "routed_model": routed,
                    "cost_saved": round(routing_savings, 6),
                    "rule_triggered": rule,
                    "complexity_score": rd.get('complexity_score', None),
                })

    # Sort decisions by savings
    routing_decisions.sort(key=lambda x: x["cost_saved"], reverse=True)

    # Build response
    top_operations = [
        {"operation": op, "savings": round(savings, 4)}
        for op, savings in sorted(savings_by_operation.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    top_rules = [
        {"rule": rule, "savings": round(savings, 4), "times_triggered": sum(1 for d in routing_decisions if d.get("rule_triggered") == rule)}
        for rule, savings in sorted(savings_by_rule.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    top_transitions = [
        {"transition": t, "count": count}
        for t, count in sorted(model_transitions.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # Generate recommendation
    if total_savings > 0:
        recommendation = f"Routing has saved ${total_savings:.2f} in the {time_range} period. "
        if top_operations:
            recommendation += f"'{top_operations[0]['operation']}' benefited most from routing."
    else:
        recommendation = "No routing savings detected. Consider enabling intelligent model routing to reduce costs."

    return {
        "total_routing_decisions": len(routing_decisions),
        "total_savings": round(total_savings, 4),
        "time_range": time_range,
        "savings_by_operation": top_operations,
        "top_rules_triggered": top_rules,
        "common_model_transitions": top_transitions,
        "recent_decisions": routing_decisions[:10],
        "recommendation": recommendation,
    }


@tool_handler
async def get_routing_decisions(
    time_range: str = "7d",
    limit: int = 20,
    operation: str | None = None,
    storage=None,
) -> dict[str, Any]:
    """
    List recent routing decisions with details.

    Args:
        time_range: Time period to search ("24h", "7d", "30d", "all")
        limit: Maximum number of decisions to return
        operation: Filter by specific operation
        storage: Storage instance (injected by server)

    Returns:
        List of routing decisions with full details
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.list_limit)

    if operation:
        calls = [c for c in calls if c.operation == operation]

    # Filter to calls with routing decisions
    routed_calls = []
    for call in calls:
        if hasattr(call, 'routing_decision') and call.routing_decision:
            rd = call.routing_decision
            routed_calls.append({
                "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                "operation": call.operation,
                "agent": call.agent_name,
                "original_model": rd.get('original_model', 'unknown'),
                "routed_model": rd.get('routed_model', call.model_name),
                "cost_saved": round(call.routing_cost_savings or 0, 6),
                "rule_triggered": rd.get('rule_triggered', 'auto'),
                "complexity_score": rd.get('complexity_score'),
                "reasoning": rd.get('reasoning', ''),
            })

    # Sort by timestamp descending
    routed_calls.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    routed_calls = routed_calls[:limit]

    return {
        "decisions": routed_calls,
        "total_returned": len(routed_calls),
    }


@tool_handler
async def get_routing_rules(
    time_range: str = "30d",
    storage=None,
) -> dict[str, Any]:
    """
    Get configured routing rules and their effectiveness.

    Args:
        time_range: Time period to analyze ("7d", "30d", "all")

    Returns:
        List of routing rules with usage statistics
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    # Aggregate by rule
    rule_stats: dict[str, dict] = {}
    for call in calls:
        if hasattr(call, 'routing_decision') and call.routing_decision:
            rd = call.routing_decision
            rule = rd.get('rule_triggered', 'auto')

            if rule not in rule_stats:
                rule_stats[rule] = {
                    "times_triggered": 0,
                    "total_savings": 0.0,
                    "operations": set(),
                }

            rule_stats[rule]["times_triggered"] += 1
            rule_stats[rule]["total_savings"] += call.routing_cost_savings or 0
            rule_stats[rule]["operations"].add(call.operation or "unknown")

    rules = [
        {
            "rule": rule,
            "times_triggered": stats["times_triggered"],
            "total_savings": round(stats["total_savings"], 4),
            "operations_affected": list(stats["operations"])[:5],
        }
        for rule, stats in sorted(rule_stats.items(), key=lambda x: x[1]["total_savings"], reverse=True)
    ]

    return {
        "rules": rules,
        "total_rules": len(rules),
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

ROUTING_TOOLS = [
    ToolDefinition(
        name="analyze_routing_savings",
        description="Analyze model routing effectiveness and cost savings. Shows how intelligent routing has reduced costs by selecting appropriate models for different tasks.",
        parameters={
            "type": "object",
            "properties": {
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
        handler=analyze_routing_savings,
        category="routing"
    ),
    ToolDefinition(
        name="get_routing_decisions",
        description="List recent routing decisions with full details including original model, routed model, rule triggered, and savings.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to search",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of decisions to return",
                    "default": 20
                },
                "operation": {
                    "type": "string",
                    "description": "Filter by specific operation (optional)"
                }
            }
        },
        handler=get_routing_decisions,
        category="routing"
    ),
    ToolDefinition(
        name="get_routing_rules",
        description="Get configured routing rules and their effectiveness statistics.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["7d", "30d", "all"],
                    "default": "30d"
                }
            }
        },
        handler=get_routing_rules,
        category="routing"
    ),
]
