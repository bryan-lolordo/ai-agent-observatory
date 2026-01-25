"""
Optimization opportunity detection tools for MCP.

Tools:
- get_optimization_opportunities: Find all pending optimization opportunities
- get_optimization_details: Get details on a specific optimization
"""

from typing import Any
from datetime import datetime, timedelta

from observatory.mcp.types import (
    ToolDefinition,
    OptimizationCategory,
)


async def get_optimization_opportunities(
    min_savings: float = 0.0,
    category: str = "all",
    limit: int = 20,
    storage=None,
) -> dict[str, Any]:
    """
    Find all pending optimization opportunities.

    Analyzes tracked LLM calls to identify:
    - Model routing opportunities (use cheaper models for simple tasks)
    - Caching opportunities (duplicate/similar prompts)
    - Token efficiency (prompt bloat, context growth)
    - Batching opportunities (parallelizable calls)

    Args:
        min_savings: Minimum monthly savings to include (dollars)
        category: Filter by category ("routing", "caching", "tokens", "batching", "all")
        limit: Maximum opportunities per category
        storage: Storage instance (injected by server)

    Returns:
        Categorized optimization opportunities with savings estimates
    """
    if storage is None:
        return {"error": "Storage not configured"}

    # Get recent calls for analysis
    cutoff = datetime.utcnow() - timedelta(days=30)
    calls = storage.get_calls(since=cutoff)

    if not calls:
        return {
            "total_opportunities": 0,
            "total_potential_savings": 0.0,
            "routing_optimizations": [],
            "caching_optimizations": [],
            "token_optimizations": [],
            "priority_recommendation": "Start tracking LLM calls to identify optimization opportunities."
        }

    routing_opts = []
    caching_opts = []
    token_opts = []

    # ========================================================================
    # Routing Optimization Detection
    # ========================================================================
    if category in ("all", "routing"):
        # Group calls by operation and model
        operation_models: dict[str, dict] = {}
        for call in calls:
            op = call.operation or "unknown"
            model = call.model_name or "unknown"

            if op not in operation_models:
                operation_models[op] = {}
            if model not in operation_models[op]:
                operation_models[op][model] = {"count": 0, "total_cost": 0.0, "avg_tokens": 0}

            operation_models[op][model]["count"] += 1
            operation_models[op][model]["total_cost"] += call.total_cost or 0
            operation_models[op][model]["avg_tokens"] += (call.prompt_tokens or 0) + (call.completion_tokens or 0)

        # Find operations using expensive models that could use cheaper ones
        expensive_models = {"gpt-4o", "gpt-4", "claude-opus-4", "claude-sonnet-4"}
        cheaper_alternatives = {
            "gpt-4o": "gpt-4o-mini",
            "gpt-4": "gpt-4o-mini",
            "claude-opus-4": "claude-haiku",
            "claude-sonnet-4": "claude-haiku",
        }

        for op, models in operation_models.items():
            for model, stats in models.items():
                if model in expensive_models and stats["count"] >= 5:
                    cheaper = cheaper_alternatives.get(model, "gpt-4o-mini")
                    # Estimate 60-80% cost reduction with cheaper model
                    estimated_savings = stats["total_cost"] * 0.7

                    if estimated_savings >= min_savings:
                        routing_opts.append({
                            "current_model": model,
                            "suggested_model": cheaper,
                            "operation": op,
                            "call_count": stats["count"],
                            "current_monthly_cost": round(stats["total_cost"], 4),
                            "estimated_monthly_savings": round(estimated_savings, 4),
                            "reasoning": f"Operation '{op}' uses {model} for {stats['count']} calls. Consider {cheaper} for simpler tasks.",
                            "confidence": 0.7,
                        })

        routing_opts.sort(key=lambda x: x["estimated_monthly_savings"], reverse=True)
        routing_opts = routing_opts[:limit]

    # ========================================================================
    # Caching Optimization Detection
    # ========================================================================
    if category in ("all", "caching"):
        # Group by normalized prompt to find duplicates
        prompt_groups: dict[str, list] = {}
        for call in calls:
            # Use cache_key if available, otherwise hash the prompt
            key = call.cache_key or (call.prompt[:100] if call.prompt else "unknown")
            if key not in prompt_groups:
                prompt_groups[key] = []
            prompt_groups[key].append(call)

        # Find groups with duplicates
        for key, group in prompt_groups.items():
            if len(group) >= 3:  # At least 3 similar calls
                total_cost = sum(c.total_cost or 0 for c in group)
                # First call would be cached, rest would be free
                potential_savings = total_cost * ((len(group) - 1) / len(group))

                if potential_savings >= min_savings:
                    caching_opts.append({
                        "cache_cluster": key[:50] + "..." if len(key) > 50 else key,
                        "unique_prompts": 1,
                        "duplicate_calls": len(group),
                        "potential_hit_rate": round((len(group) - 1) / len(group) * 100, 1),
                        "current_cost": round(total_cost, 4),
                        "estimated_monthly_savings": round(potential_savings, 4),
                        "sample_operation": group[0].operation or "unknown",
                    })

        caching_opts.sort(key=lambda x: x["estimated_monthly_savings"], reverse=True)
        caching_opts = caching_opts[:limit]

    # ========================================================================
    # Token Efficiency Detection
    # ========================================================================
    if category in ("all", "tokens"):
        # Group by operation to find token patterns
        operation_tokens: dict[str, list] = {}
        for call in calls:
            op = call.operation or "unknown"
            if op not in operation_tokens:
                operation_tokens[op] = []
            operation_tokens[op].append({
                "prompt_tokens": call.prompt_tokens or 0,
                "completion_tokens": call.completion_tokens or 0,
                "system_tokens": call.system_tokens or 0,
                "cost": call.total_cost or 0,
            })

        for op, tokens in operation_tokens.items():
            if len(tokens) >= 5:
                avg_prompt = sum(t["prompt_tokens"] for t in tokens) / len(tokens)
                avg_system = sum(t["system_tokens"] for t in tokens) / len(tokens)
                total_cost = sum(t["cost"] for t in tokens)

                # Detect system prompt bloat (>500 tokens average)
                if avg_system > 500:
                    potential_savings = total_cost * 0.2  # Estimate 20% savings
                    if potential_savings >= min_savings:
                        token_opts.append({
                            "operation": op,
                            "issue_type": "system_prompt_bloat",
                            "current_avg_system_tokens": round(avg_system),
                            "suggested_avg_tokens": 300,
                            "call_count": len(tokens),
                            "estimated_monthly_savings": round(potential_savings, 4),
                            "recommendation": f"System prompt averages {round(avg_system)} tokens. Consider condensing to ~300 tokens.",
                        })

                # Detect large prompts that could be summarized
                if avg_prompt > 2000:
                    potential_savings = total_cost * 0.3
                    if potential_savings >= min_savings:
                        token_opts.append({
                            "operation": op,
                            "issue_type": "context_growth",
                            "current_avg_prompt_tokens": round(avg_prompt),
                            "suggested_avg_tokens": 1000,
                            "call_count": len(tokens),
                            "estimated_monthly_savings": round(potential_savings, 4),
                            "recommendation": f"Prompts average {round(avg_prompt)} tokens. Consider summarizing context or using RAG.",
                        })

        token_opts.sort(key=lambda x: x["estimated_monthly_savings"], reverse=True)
        token_opts = token_opts[:limit]

    # ========================================================================
    # Build Response
    # ========================================================================
    total_savings = (
        sum(o["estimated_monthly_savings"] for o in routing_opts) +
        sum(o["estimated_monthly_savings"] for o in caching_opts) +
        sum(o["estimated_monthly_savings"] for o in token_opts)
    )

    # Priority recommendation
    all_opts = [
        *[("routing", o) for o in routing_opts],
        *[("caching", o) for o in caching_opts],
        *[("tokens", o) for o in token_opts],
    ]
    all_opts.sort(key=lambda x: x[1].get("estimated_monthly_savings", 0), reverse=True)

    if all_opts:
        top_category, top_opt = all_opts[0]
        priority = f"Top opportunity: {top_category} - {top_opt.get('operation', 'unknown')} could save ${top_opt.get('estimated_monthly_savings', 0):.2f}/month"
    else:
        priority = "No significant optimization opportunities detected. Your LLM usage is already efficient!"

    return {
        "total_opportunities": len(routing_opts) + len(caching_opts) + len(token_opts),
        "total_potential_savings": round(total_savings, 2),
        "routing_optimizations": routing_opts,
        "caching_optimizations": caching_opts,
        "token_optimizations": token_opts,
        "priority_recommendation": priority,
    }


async def get_optimization_summary(
    storage=None,
) -> dict[str, Any]:
    """
    Get a quick summary of optimization status.

    Returns high-level metrics without detailed breakdowns.
    """
    result = await get_optimization_opportunities(storage=storage)

    return {
        "total_opportunities": result["total_opportunities"],
        "total_potential_savings": result["total_potential_savings"],
        "by_category": {
            "routing": len(result["routing_optimizations"]),
            "caching": len(result["caching_optimizations"]),
            "tokens": len(result["token_optimizations"]),
        },
        "priority_recommendation": result["priority_recommendation"],
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

OPTIMIZATION_TOOLS = [
    ToolDefinition(
        name="get_optimization_opportunities",
        description="Find all pending optimization opportunities across routing, caching, and token efficiency. Shows potential monthly savings for each opportunity.",
        parameters={
            "type": "object",
            "properties": {
                "min_savings": {
                    "type": "number",
                    "description": "Minimum monthly savings threshold in dollars",
                    "default": 0.0
                },
                "category": {
                    "type": "string",
                    "description": "Filter by optimization category",
                    "enum": ["routing", "caching", "tokens", "batching", "all"],
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum opportunities per category",
                    "default": 20
                }
            }
        },
        handler=get_optimization_opportunities,
        category="optimization"
    ),
    ToolDefinition(
        name="get_optimization_summary",
        description="Get a quick summary of optimization opportunities without detailed breakdowns. Good for a high-level overview.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=get_optimization_summary,
        category="optimization"
    ),
]
