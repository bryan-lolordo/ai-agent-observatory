"""
Quality evaluation tools for MCP.

Tools:
- get_quality_scores: Get quality evaluation results
- get_quality_analysis: Comprehensive quality analysis
- get_low_quality_calls: Find calls with quality issues
"""

from typing import Any

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import (
    parse_time_range,
    tool_handler,
    calculate_hit_rate,
    bucket_values,
)


@tool_handler
async def get_quality_scores(
    agent: str | None = None,
    operation: str | None = None,
    min_score: float = 0.0,
    time_range: str = "7d",
    limit: int = 50,
    storage=None,
) -> dict[str, Any]:
    """
    Get quality evaluation results for LLM calls.

    Args:
        agent: Filter by agent name
        operation: Filter by operation
        min_score: Minimum quality score threshold
        time_range: Time period to query
        limit: Maximum results to return
        storage: Storage instance (injected by server)

    Returns:
        Quality scores with evaluation details
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    # Filter calls with quality evaluations
    evaluated_calls = []
    for call in calls:
        quality_score = getattr(call, 'quality_score', None)
        if quality_score is None:
            continue

        if agent and call.agent_name != agent:
            continue
        if operation and call.operation != operation:
            continue
        if quality_score < min_score:
            continue

        evaluated_calls.append({
            "call_id": str(call.id) if hasattr(call, 'id') else None,
            "timestamp": call.timestamp.isoformat() if call.timestamp else None,
            "agent": call.agent_name,
            "operation": call.operation,
            "model": call.model_name,
            "quality_score": round(quality_score, 2),
            "correctness": round(getattr(call, 'correctness_score', 0) or 0, 2),
            "helpfulness": round(getattr(call, 'helpfulness_score', 0) or 0, 2),
            "safety": round(getattr(call, 'safety_score', 0) or 0, 2),
            "hallucination_detected": getattr(call, 'hallucination_flag', False),
            "evaluation_notes": getattr(call, 'evaluation_notes', None),
        })

    # Sort by score descending
    evaluated_calls.sort(key=lambda x: x["quality_score"], reverse=True)
    evaluated_calls = evaluated_calls[:limit]

    # Calculate summary
    if evaluated_calls:
        avg_score = sum(c["quality_score"] for c in evaluated_calls) / len(evaluated_calls)
        hallucination_count = sum(1 for c in evaluated_calls if c["hallucination_detected"])
    else:
        avg_score = 0
        hallucination_count = 0

    return {
        "evaluations": evaluated_calls,
        "total_returned": len(evaluated_calls),
        "summary": {
            "avg_quality_score": round(avg_score, 2),
            "hallucination_rate": calculate_hit_rate(hallucination_count, len(evaluated_calls)) if evaluated_calls else 0,
            "evaluations_count": len(evaluated_calls),
        },
        "filters_applied": {
            "agent": agent,
            "operation": operation,
            "min_score": min_score,
            "time_range": time_range,
        }
    }


@tool_handler
async def get_quality_analysis(
    time_range: str = "7d",
    storage=None,
) -> dict[str, Any]:
    """
    Comprehensive quality analysis across all evaluations.

    Args:
        time_range: Time period to analyze
        storage: Storage instance (injected by server)

    Returns:
        Quality analysis with breakdowns and recommendations
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.aggregation_limit)

    # Filter to evaluated calls
    evaluated = [c for c in calls if getattr(c, 'quality_score', None) is not None]

    if not evaluated:
        return {
            "avg_quality_score": 0,
            "total_evaluations": 0,
            "message": "No quality evaluations found in the specified time range"
        }

    # Calculate overall metrics
    scores = [c.quality_score for c in evaluated]
    avg_score = sum(scores) / len(scores)
    hallucinations = sum(1 for c in evaluated if getattr(c, 'hallucination_flag', False))

    # Score distribution using bucket_values utility
    score_buckets = bucket_values(
        scores,
        [
            ("bad (0-1.5)", 0, 1.5),
            ("poor (1.5-2.5)", 1.5, 2.5),
            ("fair (2.5-3.5)", 2.5, 3.5),
            ("good (3.5-4.5)", 3.5, 4.5),
            ("excellent (4.5-5.0)", 4.5, 5.1),  # 5.1 to include 5.0
        ]
    )

    # Quality by agent
    agent_scores: dict[str, list] = {}
    for call in evaluated:
        agent = call.agent_name or "unknown"
        if agent not in agent_scores:
            agent_scores[agent] = []
        agent_scores[agent].append(call.quality_score)

    quality_by_agent = {
        agent: round(sum(scores) / len(scores), 2)
        for agent, scores in agent_scores.items()
    }

    # Quality by operation
    op_scores: dict[str, list] = {}
    for call in evaluated:
        op = call.operation or "unknown"
        if op not in op_scores:
            op_scores[op] = []
        op_scores[op].append(call.quality_score)

    quality_by_operation = {
        op: round(sum(scores) / len(scores), 2)
        for op, scores in op_scores.items()
    }

    # Find low quality calls
    low_quality = [
        {
            "call_id": str(c.id) if hasattr(c, 'id') else None,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "agent": c.agent_name,
            "operation": c.operation,
            "quality_score": round(c.quality_score, 2),
            "hallucination": getattr(c, 'hallucination_flag', False),
        }
        for c in evaluated if c.quality_score < 3.0
    ][:10]

    # Generate recommendations using config thresholds
    recommendations = []
    hallucination_rate = hallucinations / len(evaluated)

    if hallucination_rate > 0.1:
        recommendations.append(f"High hallucination rate ({hallucination_rate * 100:.1f}%). Review prompts for clarity and add grounding context.")

    low_scoring_agents = [a for a, s in quality_by_agent.items() if s < 3.5]
    if low_scoring_agents:
        recommendations.append(f"Agents with low scores: {', '.join(low_scoring_agents)}. Review their prompts and consider fine-tuning.")

    if avg_score < 3.5:
        recommendations.append("Overall quality below target. Consider prompt engineering improvements.")
    elif avg_score >= 4.5:
        recommendations.append("Excellent quality scores! Current prompt strategies are effective.")

    if not recommendations:
        recommendations.append("Quality metrics are within acceptable range.")

    return {
        "avg_quality_score": round(avg_score, 2),
        "total_evaluations": len(evaluated),
        "hallucination_rate": round(hallucination_rate * 100, 2),
        "score_distribution": score_buckets,
        "quality_by_agent": dict(sorted(quality_by_agent.items(), key=lambda x: x[1])),
        "quality_by_operation": dict(sorted(quality_by_operation.items(), key=lambda x: x[1])),
        "low_quality_calls": low_quality,
        "recommendations": recommendations,
    }


@tool_handler
async def get_hallucinations(
    time_range: str = "7d",
    limit: int = 20,
    storage=None,
) -> dict[str, Any]:
    """
    Find calls where hallucinations were detected.

    Args:
        time_range: Time period to query
        limit: Maximum results to return
        storage: Storage instance (injected by server)

    Returns:
        List of calls with detected hallucinations
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    # Filter to hallucinations
    hallucinations = []
    for call in calls:
        if getattr(call, 'hallucination_flag', False):
            hallucinations.append({
                "call_id": str(call.id) if hasattr(call, 'id') else None,
                "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                "agent": call.agent_name,
                "operation": call.operation,
                "model": call.model_name,
                "quality_score": round(getattr(call, 'quality_score', 0) or 0, 2),
                "prompt_preview": (call.prompt[:200] + "...") if call.prompt and len(call.prompt) > 200 else call.prompt,
                "response_preview": (call.response_text[:200] + "...") if call.response_text and len(call.response_text) > 200 else call.response_text,
                "evaluation_notes": getattr(call, 'evaluation_notes', None),
            })

    hallucinations = hallucinations[:limit]

    # Aggregate by agent/operation
    by_agent: dict[str, int] = {}
    by_operation: dict[str, int] = {}
    for h in hallucinations:
        agent = h["agent"] or "unknown"
        by_agent[agent] = by_agent.get(agent, 0) + 1
        op = h["operation"] or "unknown"
        by_operation[op] = by_operation.get(op, 0) + 1

    return {
        "hallucinations": hallucinations,
        "total_found": len(hallucinations),
        "by_agent": dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True)),
        "by_operation": dict(sorted(by_operation.items(), key=lambda x: x[1], reverse=True)),
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

QUALITY_TOOLS = [
    ToolDefinition(
        name="get_quality_scores",
        description="Get quality evaluation results for LLM calls. Filter by agent, operation, or minimum score.",
        parameters={
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Filter by agent name (optional)"
                },
                "operation": {
                    "type": "string",
                    "description": "Filter by operation (optional)"
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum quality score threshold (0-5)",
                    "default": 0.0
                },
                "time_range": {
                    "type": "string",
                    "description": "Time period to query",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 50
                }
            }
        },
        handler=get_quality_scores,
        category="quality"
    ),
    ToolDefinition(
        name="get_quality_analysis",
        description="Comprehensive quality analysis with score distributions, breakdowns by agent/operation, and recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                }
            }
        },
        handler=get_quality_analysis,
        category="quality"
    ),
    ToolDefinition(
        name="get_hallucinations",
        description="Find calls where hallucinations were detected by the quality evaluation system.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to query",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 20
                }
            }
        },
        handler=get_hallucinations,
        category="quality"
    ),
]
