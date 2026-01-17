# observatory/health.py
"""
Health check utilities for Observatory components.

Provides health check functions for monitoring system status,
useful for Kubernetes probes, monitoring dashboards, and status endpoints.

Usage:
    from observatory.health import observatory_health_check, HealthStatus

    # In your Flask/FastAPI app
    @app.get("/health")
    def health():
        return observatory_health_check(
            storage=storage,
            cache=cache,
            semantic_cache=semantic_cache,
            judge=judge,
            async_writer=async_writer,
        )

    # Check specific component
    from observatory.health import check_storage_health
    result = check_storage_health(storage)
    if result["status"] == HealthStatus.UNHEALTHY:
        alert_ops_team()
"""

import time
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


def check_storage_health(storage) -> Dict[str, Any]:
    """
    Check database storage health.

    Performs a simple query to verify database connectivity.

    Args:
        storage: Storage instance

    Returns:
        Dict with status, message, and latency_ms
    """
    if storage is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "Storage not configured",
        }

    start = time.time()
    try:
        # Check if lazy loading is enabled and not yet initialized
        if hasattr(storage, '_initialized') and not storage._initialized:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Storage not yet initialized (lazy loading)",
                "latency_ms": 0,
            }

        # Try a simple count query to test connection
        if hasattr(storage, 'get_call_count'):
            storage.get_call_count(limit=1)
        elif hasattr(storage, 'SessionLocal'):
            # Fallback: create and close a session
            db = storage.SessionLocal()
            db.close()

        latency_ms = (time.time() - start) * 1000

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Database connection OK",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


def check_cache_health(cache) -> Dict[str, Any]:
    """
    Check in-memory cache health.

    Args:
        cache: CacheManager instance

    Returns:
        Dict with status, message, and cache statistics
    """
    if cache is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "Cache not configured",
        }

    try:
        if not getattr(cache, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Cache disabled",
            }

        stats = {}
        if hasattr(cache, 'get_stats'):
            stats = cache.get_stats()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Cache OK",
            "entries": stats.get("total_entries", 0),
            "hit_rate": stats.get("hit_rate", 0),
            "hits": stats.get("hits", 0),
            "misses": stats.get("misses", 0),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_persistent_cache_health(persistent_cache) -> Dict[str, Any]:
    """
    Check persistent (SQLite) cache health.

    Args:
        persistent_cache: PersistentCacheManager instance

    Returns:
        Dict with status and cache info
    """
    if persistent_cache is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "PersistentCache not configured",
        }

    try:
        if not getattr(persistent_cache, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "PersistentCache disabled",
            }

        stats = {}
        if hasattr(persistent_cache, 'get_stats'):
            stats = persistent_cache.get_stats()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "PersistentCache OK",
            "db_path": getattr(persistent_cache, 'db_path', None),
            "entries": stats.get("total_entries", 0),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_semantic_cache_health(semantic_cache) -> Dict[str, Any]:
    """
    Check semantic cache (ChromaDB) health.

    Args:
        semantic_cache: SemanticCache instance

    Returns:
        Dict with status and cache info
    """
    if semantic_cache is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "SemanticCache not configured (ChromaDB not available)",
        }

    try:
        if not getattr(semantic_cache, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "SemanticCache disabled",
            }

        # Check if lazy initialized
        if not getattr(semantic_cache, '_initialized', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "SemanticCache not yet initialized (lazy loading)",
            }

        stats = {}
        if hasattr(semantic_cache, 'get_stats'):
            stats = semantic_cache.get_stats()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "SemanticCache OK",
            "entries": stats.get("total_entries", 0),
            "db_path": getattr(semantic_cache, 'db_path', None),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_judge_health(judge) -> Dict[str, Any]:
    """
    Check LLM judge health.

    Args:
        judge: LLMJudge instance

    Returns:
        Dict with status and judge statistics
    """
    if judge is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "Judge not configured",
        }

    try:
        if not getattr(judge, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Judge disabled",
            }

        stats = {}
        if hasattr(judge, 'get_stats'):
            stats = judge.get_stats()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Judge OK",
            "total_evaluated": stats.get("total_evaluated", 0),
            "sample_rate": getattr(judge, 'sample_rate', None),
            "operations": len(getattr(judge, 'operations', set())),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_router_health(router) -> Dict[str, Any]:
    """
    Check model router health.

    Args:
        router: ModelRouter instance

    Returns:
        Dict with status and router info
    """
    if router is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "Router not configured",
        }

    try:
        if not getattr(router, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Router disabled",
            }

        stats = {}
        if hasattr(router, 'get_stats'):
            stats = router.get_stats()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Router OK",
            "default_model": getattr(router, 'default_model', None),
            "num_rules": stats.get("num_rules", 0),
            "total_routed": stats.get("total_routed", 0),
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_async_writer_health(async_writer) -> Dict[str, Any]:
    """
    Check async writer queue health.

    Args:
        async_writer: AsyncWriteQueue instance

    Returns:
        Dict with status and queue statistics
    """
    if async_writer is None:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "AsyncWriter not configured",
        }

    try:
        if not getattr(async_writer, 'enabled', True):
            return {
                "status": HealthStatus.HEALTHY,
                "message": "AsyncWriter disabled (using sync writes)",
            }

        stats = async_writer.get_stats() if hasattr(async_writer, 'get_stats') else {}

        queue_size = stats.get("queue_size", 0)
        max_size = stats.get("max_queue_size", 1000)
        running = stats.get("running", False)

        # Check for issues
        if not running and async_writer.enabled:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "AsyncWriter enabled but not running",
                **stats,
            }

        # Degraded if queue is > 80% full
        if queue_size > max_size * 0.8:
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"Queue nearly full ({queue_size}/{max_size})",
                **stats,
            }

        # Degraded if many errors
        error_rate = stats.get("total_errors", 0) / max(stats.get("total_enqueued", 1), 1)
        if error_rate > 0.1:  # >10% error rate
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"High error rate ({error_rate:.1%})",
                **stats,
            }

        return {
            "status": HealthStatus.HEALTHY,
            "message": "AsyncWriter OK",
            **stats,
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e),
        }


def check_circuit_breaker_health(
    circuit_breakers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Check circuit breaker states.

    Args:
        circuit_breakers: Dict of name -> CircuitBreaker instances

    Returns:
        Dict with overall status and per-breaker details
    """
    if not circuit_breakers:
        return {
            "status": HealthStatus.UNKNOWN,
            "message": "No circuit breakers configured",
        }

    results = {}
    overall_status = HealthStatus.HEALTHY

    for name, cb in circuit_breakers.items():
        try:
            stats = cb.get_stats() if hasattr(cb, 'get_stats') else {}
            state = stats.get("state", "unknown")

            if state == "open":
                results[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "state": state,
                    "failures": stats.get("failure_count", 0),
                    "rejections": stats.get("total_rejections", 0),
                }
                overall_status = HealthStatus.UNHEALTHY

            elif state == "half_open":
                results[name] = {
                    "status": HealthStatus.DEGRADED,
                    "state": state,
                    "failures": stats.get("failure_count", 0),
                    "successes": stats.get("success_count", 0),
                }
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

            else:  # closed
                results[name] = {
                    "status": HealthStatus.HEALTHY,
                    "state": state,
                    "total_successes": stats.get("total_successes", 0),
                }

        except Exception as e:
            results[name] = {
                "status": HealthStatus.UNHEALTHY,
                "message": str(e),
            }
            overall_status = HealthStatus.UNHEALTHY

    return {
        "status": overall_status,
        "circuit_breakers": results,
    }


def observatory_health_check(
    observatory=None,
    storage=None,
    cache=None,
    persistent_cache=None,
    semantic_cache=None,
    judge=None,
    router=None,
    async_writer=None,
    circuit_breakers: Dict[str, Any] = None,
    include_details: bool = True,
) -> Dict[str, Any]:
    """
    Comprehensive health check for all Observatory components.

    Checks each configured component and returns overall system health.

    Args:
        observatory: Observatory instance (will extract storage if provided)
        storage: Storage instance
        cache: CacheManager instance
        persistent_cache: PersistentCacheManager instance
        semantic_cache: SemanticCache instance
        judge: LLMJudge instance
        router: ModelRouter instance
        async_writer: AsyncWriteQueue instance
        circuit_breakers: Dict of circuit breaker instances
        include_details: Include detailed per-component info

    Returns:
        Dict with:
        - status: "healthy", "degraded", or "unhealthy"
        - healthy: boolean for quick checks
        - timestamp: Unix timestamp
        - components: detailed status per component (if include_details)

    Example:
        @app.get("/health")
        def health():
            return observatory_health_check(
                storage=storage,
                cache=cache,
                async_writer=async_writer,
            )

        @app.get("/health/live")
        def liveness():
            result = observatory_health_check(storage=storage, include_details=False)
            return {"status": "ok"} if result["healthy"] else {"status": "fail"}
    """
    components = {}
    overall_status = HealthStatus.HEALTHY

    # Extract storage from observatory if provided
    if observatory and storage is None:
        storage = getattr(observatory, 'storage', None)

    # Define all health checks
    checks = [
        ("storage", storage, check_storage_health),
        ("cache", cache, check_cache_health),
        ("persistent_cache", persistent_cache, check_persistent_cache_health),
        ("semantic_cache", semantic_cache, check_semantic_cache_health),
        ("judge", judge, check_judge_health),
        ("router", router, check_router_health),
        ("async_writer", async_writer, check_async_writer_health),
    ]

    for name, component, check_func in checks:
        if component is not None:
            try:
                result = check_func(component)
                components[name] = result

                # Update overall status
                status = result.get("status", HealthStatus.UNKNOWN)
                if status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            except Exception as e:
                components[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Health check failed: {e}",
                }
                overall_status = HealthStatus.UNHEALTHY

    # Check circuit breakers
    if circuit_breakers:
        cb_result = check_circuit_breaker_health(circuit_breakers)
        components["circuit_breakers"] = cb_result

        if cb_result["status"] == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif cb_result["status"] == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED

    response = {
        "status": overall_status.value,
        "healthy": overall_status == HealthStatus.HEALTHY,
        "timestamp": time.time(),
    }

    if include_details:
        response["components"] = components

    return response


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "HealthStatus",
    "check_storage_health",
    "check_cache_health",
    "check_persistent_cache_health",
    "check_semantic_cache_health",
    "check_judge_health",
    "check_router_health",
    "check_async_writer_health",
    "check_circuit_breaker_health",
    "observatory_health_check",
]
