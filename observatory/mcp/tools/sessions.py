"""
Session management and query tools for MCP.

Tools:
- query_sessions: List and filter tracking sessions
- get_session_details: Get detailed metrics for a specific session
- get_active_sessions: List currently active (ongoing) sessions
"""

from datetime import datetime
from typing import Any

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import (
    parse_time_range,
    tool_handler,
    error_response,
    DataNotFoundError,
)


@tool_handler
async def query_sessions(
    time_range: str = "7d",
    status: str = "all",
    limit: int = 20,
    storage=None,
) -> dict[str, Any]:
    """
    List and filter tracking sessions.

    Args:
        time_range: Time period to query ("24h", "7d", "30d", "all")
        status: Filter by status ("active", "completed", "failed", "all")
        limit: Maximum sessions to return
        storage: Storage instance (injected by server)

    Returns:
        List of sessions with summary metrics
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)

    # Get sessions from storage
    sessions = storage.get_sessions(since=cutoff) if hasattr(storage, 'get_sessions') else []

    # Filter by status if specified
    if status != "all":
        sessions = [s for s in sessions if getattr(s, 'status', 'unknown') == status]

    # Clamp limit
    limit = min(limit, cfg.query.max_limit)

    # Build response
    session_list = []
    for session in sessions[:limit]:
        session_list.append({
            "session_id": str(session.id) if hasattr(session, 'id') else session.session_id,
            "started_at": session.started_at.isoformat() if hasattr(session, 'started_at') and session.started_at else None,
            "ended_at": session.ended_at.isoformat() if hasattr(session, 'ended_at') and session.ended_at else None,
            "status": getattr(session, 'status', 'unknown'),
            "operation_type": getattr(session, 'operation_type', None),
            "total_calls": getattr(session, 'total_llm_calls', 0),
            "total_cost": round(getattr(session, 'total_cost', 0) or 0, 4),
            "total_tokens": getattr(session, 'total_tokens', 0),
            "avg_latency_ms": round(getattr(session, 'avg_latency_ms', 0) or 0, 2),
            "cache_hit_rate": round(getattr(session, 'cache_hit_rate', 0) or 0, 2),
            "routing_savings": round(getattr(session, 'routing_cost_savings', 0) or 0, 4),
        })

    # Calculate summary stats
    total_cost = sum(s["total_cost"] for s in session_list)
    total_calls = sum(s["total_calls"] for s in session_list)

    return {
        "sessions": session_list,
        "total_returned": len(session_list),
        "summary": {
            "total_cost": round(total_cost, 4),
            "total_calls": total_calls,
            "avg_cost_per_session": round(total_cost / len(session_list), 4) if session_list else 0,
        },
        "filters_applied": {
            "time_range": time_range,
            "status": status,
        }
    }


@tool_handler
async def get_session_details(
    session_id: str,
    storage=None,
) -> dict[str, Any]:
    """
    Get detailed metrics for a specific session.

    Args:
        session_id: The session ID to query
        storage: Storage instance (injected by server)

    Returns:
        Comprehensive session details including all calls
    """
    # Get session
    session = storage.get_session(session_id) if hasattr(storage, 'get_session') else None

    if not session:
        raise DataNotFoundError("Session", session_id)

    # Get calls for this session
    calls = storage.get_calls(session_id=session_id) if hasattr(storage, 'get_calls') else []

    # Aggregate metrics
    models_used: dict[str, int] = {}
    operations_used: dict[str, int] = {}
    agents_used: dict[str, int] = {}

    for call in calls:
        model = call.model_name or "unknown"
        models_used[model] = models_used.get(model, 0) + 1

        op = call.operation or "unknown"
        operations_used[op] = operations_used.get(op, 0) + 1

        agent = call.agent_name or "unknown"
        agents_used[agent] = agents_used.get(agent, 0) + 1

    return {
        "session_id": session_id,
        "started_at": session.started_at.isoformat() if hasattr(session, 'started_at') and session.started_at else None,
        "ended_at": session.ended_at.isoformat() if hasattr(session, 'ended_at') and session.ended_at else None,
        "duration_seconds": (session.ended_at - session.started_at).total_seconds() if hasattr(session, 'ended_at') and session.ended_at and session.started_at else None,
        "status": getattr(session, 'status', 'unknown'),
        "operation_type": getattr(session, 'operation_type', None),
        "metrics": {
            "total_calls": len(calls),
            "total_cost": round(sum(c.total_cost or 0 for c in calls), 4),
            "total_prompt_tokens": sum(c.prompt_tokens or 0 for c in calls),
            "total_completion_tokens": sum(c.completion_tokens or 0 for c in calls),
            "avg_latency_ms": round(sum(c.latency_ms or 0 for c in calls) / len(calls), 2) if calls else 0,
            "cache_hits": sum(1 for c in calls if getattr(c, 'cache_hit', False)),
            "cache_savings": round(sum(c.cache_cost_savings or 0 for c in calls), 4),
            "routing_savings": round(sum(c.routing_cost_savings or 0 for c in calls), 4),
            "errors": sum(1 for c in calls if not c.success),
        },
        "breakdown": {
            "by_model": [{"model": m, "count": c} for m, c in sorted(models_used.items(), key=lambda x: x[1], reverse=True)],
            "by_operation": [{"operation": o, "count": c} for o, c in sorted(operations_used.items(), key=lambda x: x[1], reverse=True)],
            "by_agent": [{"agent": a, "count": c} for a, c in sorted(agents_used.items(), key=lambda x: x[1], reverse=True)],
        },
        "recent_calls": [
            {
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "model": c.model_name,
                "operation": c.operation,
                "cost": round(c.total_cost or 0, 6),
                "latency_ms": c.latency_ms,
                "success": c.success,
            }
            for c in sorted(calls, key=lambda x: x.timestamp or datetime.min, reverse=True)[:10]
        ],
    }


@tool_handler
async def get_active_sessions(
    storage=None,
) -> dict[str, Any]:
    """
    List currently active (ongoing) sessions.

    Returns:
        List of active sessions with live metrics
    """
    # Get sessions that haven't ended
    all_sessions = storage.get_sessions() if hasattr(storage, 'get_sessions') else []
    active = [s for s in all_sessions if not getattr(s, 'ended_at', None)]

    session_list = []
    for session in active:
        # Get calls for this session
        session_id = str(session.id) if hasattr(session, 'id') else session.session_id
        calls = storage.get_calls(session_id=session_id) if hasattr(storage, 'get_calls') else []

        session_list.append({
            "session_id": session_id,
            "started_at": session.started_at.isoformat() if hasattr(session, 'started_at') and session.started_at else None,
            "running_for_seconds": (datetime.utcnow() - session.started_at).total_seconds() if hasattr(session, 'started_at') and session.started_at else None,
            "operation_type": getattr(session, 'operation_type', None),
            "calls_so_far": len(calls),
            "cost_so_far": round(sum(c.total_cost or 0 for c in calls), 4),
            "last_call_at": max((c.timestamp for c in calls if c.timestamp), default=None),
        })

    return {
        "active_sessions": session_list,
        "total_active": len(session_list),
    }


@tool_handler
async def get_session_comparison(
    session_ids: list[str],
    storage=None,
) -> dict[str, Any]:
    """
    Compare metrics across multiple sessions.

    Args:
        session_ids: List of session IDs to compare
        storage: Storage instance (injected by server)

    Returns:
        Side-by-side comparison of session metrics
    """
    cfg = get_config()

    if not session_ids or len(session_ids) < 2:
        return error_response("At least 2 session IDs required for comparison", "VALIDATION_ERROR")

    comparisons = []
    # Limit to configured max
    for session_id in session_ids[:5]:
        details = await get_session_details(session_id, storage=storage)
        if "error" not in details:
            comparisons.append({
                "session_id": session_id,
                "total_calls": details["metrics"]["total_calls"],
                "total_cost": details["metrics"]["total_cost"],
                "avg_latency_ms": details["metrics"]["avg_latency_ms"],
                "cache_hits": details["metrics"]["cache_hits"],
                "routing_savings": details["metrics"]["routing_savings"],
                "errors": details["metrics"]["errors"],
            })

    if len(comparisons) < 2:
        return error_response("Could not find enough valid sessions for comparison", "NOT_FOUND")

    # Calculate averages for reference
    avg_cost = sum(c["total_cost"] for c in comparisons) / len(comparisons)
    avg_latency = sum(c["avg_latency_ms"] for c in comparisons) / len(comparisons)

    return {
        "sessions": comparisons,
        "averages": {
            "avg_cost": round(avg_cost, 4),
            "avg_latency_ms": round(avg_latency, 2),
        },
        "best_performers": {
            "lowest_cost": min(comparisons, key=lambda x: x["total_cost"])["session_id"],
            "lowest_latency": min(comparisons, key=lambda x: x["avg_latency_ms"])["session_id"],
            "most_cache_hits": max(comparisons, key=lambda x: x["cache_hits"])["session_id"],
        }
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

SESSION_TOOLS = [
    ToolDefinition(
        name="query_sessions",
        description="List and filter tracking sessions by time range and status. Shows summary metrics for each session.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to query",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                },
                "status": {
                    "type": "string",
                    "description": "Filter by session status",
                    "enum": ["active", "completed", "failed", "all"],
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum sessions to return",
                    "default": 20
                }
            }
        },
        handler=query_sessions,
        category="sessions"
    ),
    ToolDefinition(
        name="get_session_details",
        description="Get comprehensive details for a specific session including all calls, costs, and performance metrics.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to query"
                }
            },
            "required": ["session_id"]
        },
        handler=get_session_details,
        category="sessions"
    ),
    ToolDefinition(
        name="get_active_sessions",
        description="List currently active (ongoing) sessions with live metrics.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=get_active_sessions,
        category="sessions"
    ),
    ToolDefinition(
        name="get_session_comparison",
        description="Compare metrics across multiple sessions side-by-side.",
        parameters={
            "type": "object",
            "properties": {
                "session_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of session IDs to compare (2-5 sessions)"
                }
            },
            "required": ["session_ids"]
        },
        handler=get_session_comparison,
        category="sessions"
    ),
]
