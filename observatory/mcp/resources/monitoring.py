"""
Monitoring resources for MCP.

Resources:
- observatory://active-sessions: Currently running sessions
- observatory://system-health: Observatory health status
- observatory://daily-summary: Daily metrics summary
"""

import json
from datetime import datetime, timedelta

from observatory.mcp.types import ResourceDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import format_duration, get_today_start


async def get_active_sessions(storage=None) -> str:
    """
    Get currently active (ongoing) sessions.

    Returns JSON with live session data for monitoring.
    """
    if storage is None:
        return json.dumps({"error": "Storage not configured"})

    cfg = get_config()

    # Get all sessions and filter to active
    all_sessions = storage.get_sessions(limit=cfg.query.list_limit) if hasattr(storage, 'get_sessions') else []
    active = [s for s in all_sessions if not getattr(s, 'ended_at', None)]

    sessions_data = []
    for session in active:
        session_id = str(session.id) if hasattr(session, 'id') else getattr(session, 'session_id', 'unknown')

        # Get calls for this session
        calls = storage.get_calls(session_id=session_id) if hasattr(storage, 'get_calls') else []

        started_at = session.started_at if hasattr(session, 'started_at') else None
        running_seconds = (datetime.utcnow() - started_at).total_seconds() if started_at else None

        sessions_data.append({
            "session_id": session_id,
            "started_at": started_at.isoformat() if started_at else None,
            "running_for_seconds": round(running_seconds, 0) if running_seconds else None,
            "running_for_human": format_duration(running_seconds) if running_seconds else None,
            "operation_type": getattr(session, 'operation_type', None),
            "calls_count": len(calls),
            "cost_so_far": round(sum(c.total_cost or 0 for c in calls), 4),
            "tokens_so_far": sum((c.prompt_tokens or 0) + (c.completion_tokens or 0) for c in calls),
            "last_call_at": max((c.timestamp.isoformat() for c in calls if c.timestamp), default=None),
            "errors_count": sum(1 for c in calls if not c.success),
        })

    return json.dumps({
        "active_sessions": sessions_data,
        "total_active": len(sessions_data),
        "total_cost_active": round(sum(s["cost_so_far"] for s in sessions_data), 4),
        "last_updated": datetime.utcnow().isoformat(),
    }, indent=2)


async def get_system_health(storage=None) -> str:
    """
    Get Observatory system health status.

    Returns JSON with health metrics for all components.
    """
    health = {
        "status": "healthy",
        "components": {},
        "last_checked": datetime.utcnow().isoformat(),
    }

    # Check storage
    try:
        if storage:
            calls = storage.get_calls(limit=1)
            health["components"]["storage"] = {
                "status": "healthy",
                "message": "Storage accessible",
            }
        else:
            health["components"]["storage"] = {
                "status": "degraded",
                "message": "Storage not configured",
            }
    except Exception as e:
        health["components"]["storage"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        health["status"] = "degraded"

    # Check recent activity
    try:
        if storage:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_calls = storage.get_calls(since=cutoff)
            health["components"]["tracking"] = {
                "status": "healthy" if recent_calls else "idle",
                "calls_last_hour": len(recent_calls) if recent_calls else 0,
                "message": f"{len(recent_calls)} calls tracked in last hour" if recent_calls else "No recent tracking activity",
            }
    except Exception as e:
        health["components"]["tracking"] = {
            "status": "unknown",
            "message": str(e),
        }

    # Overall status
    unhealthy = [c for c in health["components"].values() if c.get("status") == "unhealthy"]
    if unhealthy:
        health["status"] = "unhealthy"
    elif any(c.get("status") == "degraded" for c in health["components"].values()):
        health["status"] = "degraded"

    return json.dumps(health, indent=2)


async def get_daily_summary(storage=None) -> str:
    """
    Get daily metrics summary.

    Returns JSON with key metrics for the current day.
    """
    if storage is None:
        return json.dumps({"error": "Storage not configured"})

    cfg = get_config()

    # Get today's calls
    today_start = get_today_start()
    calls = storage.get_calls(since=today_start, limit=cfg.query.default_limit)

    if not calls:
        return json.dumps({
            "date": today_start.strftime("%Y-%m-%d"),
            "total_calls": 0,
            "total_cost": 0.0,
            "message": "No calls tracked today yet",
            "last_updated": datetime.utcnow().isoformat(),
        })

    # Calculate metrics
    total_cost = sum(c.total_cost or 0 for c in calls)
    total_tokens = sum((c.prompt_tokens or 0) + (c.completion_tokens or 0) for c in calls)
    latencies = [c.latency_ms for c in calls if c.latency_ms]
    cache_hits = sum(1 for c in calls if getattr(c, 'cache_hit', False))
    routing_savings = sum(c.routing_cost_savings or 0 for c in calls)
    errors = sum(1 for c in calls if not c.success)

    # By model
    by_model: dict[str, int] = {}
    for call in calls:
        model = call.model_name or "unknown"
        by_model[model] = by_model.get(model, 0) + 1

    # By operation
    by_operation: dict[str, int] = {}
    for call in calls:
        op = call.operation or "unknown"
        by_operation[op] = by_operation.get(op, 0) + 1

    return json.dumps({
        "date": today_start.strftime("%Y-%m-%d"),
        "total_calls": len(calls),
        "total_cost": round(total_cost, 4),
        "total_tokens": total_tokens,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "cache_hit_rate": round(cache_hits / len(calls) * 100, 2) if calls else 0,
        "routing_savings": round(routing_savings, 4),
        "error_rate": round(errors / len(calls) * 100, 2) if calls else 0,
        "by_model": dict(sorted(by_model.items(), key=lambda x: x[1], reverse=True)[:5]),
        "by_operation": dict(sorted(by_operation.items(), key=lambda x: x[1], reverse=True)[:5]),
        "last_updated": datetime.utcnow().isoformat(),
    }, indent=2)


# ============================================================================
# Resource Definitions for Registration
# ============================================================================

MONITORING_RESOURCES = [
    ResourceDefinition(
        uri="observatory://active-sessions",
        name="Active Sessions",
        description="Currently running tracking sessions with live metrics including cost, call count, and duration.",
        mime_type="application/json",
        handler=get_active_sessions,
    ),
    ResourceDefinition(
        uri="observatory://system-health",
        name="System Health",
        description="Observatory system health status including storage connectivity and recent tracking activity.",
        mime_type="application/json",
        handler=get_system_health,
    ),
    ResourceDefinition(
        uri="observatory://daily-summary",
        name="Daily Summary",
        description="Key metrics summary for the current day including total cost, calls, and performance.",
        mime_type="application/json",
        handler=get_daily_summary,
    ),
]
