"""
Cache effectiveness analysis tools for MCP.

Tools:
- get_cache_effectiveness: Analyze cache hit rates and savings
- get_cacheable_patterns: Identify patterns suitable for caching
"""

from typing import Any
from collections import defaultdict

from observatory.mcp.types import ToolDefinition
from observatory.mcp.config import get_config
from observatory.mcp.utils import (
    parse_time_range,
    tool_handler,
    calculate_hit_rate,
    estimate_cache_savings,
)


@tool_handler
async def get_cache_effectiveness(
    cache_type: str = "all",
    time_range: str = "7d",
    storage=None,
) -> dict[str, Any]:
    """
    Analyze cache hit rates and cost savings.

    Evaluates the effectiveness of different caching strategies:
    - Exact match caching
    - Semantic similarity caching
    - Prefix caching

    Args:
        cache_type: Type of cache to analyze ("exact", "semantic", "prefix", "all")
        time_range: Time period to analyze
        storage: Storage instance (injected by server)

    Returns:
        Cache analysis with hit rates, savings, and recommendations
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if not calls:
        return {
            "overall_hit_rate": 0.0,
            "total_cache_savings": 0.0,
            "message": "No calls found in the specified time range"
        }

    # Analyze cache metrics
    total_calls = len(calls)
    cache_hits = 0
    cache_misses = 0
    total_savings = 0.0

    exact_stats = {"hits": 0, "misses": 0, "savings": 0.0}
    semantic_stats = {"hits": 0, "misses": 0, "savings": 0.0}
    prefix_stats = {"hits": 0, "misses": 0, "savings": 0.0}

    for call in calls:
        # Check cache metadata
        cache_hit = call.cache_hit if hasattr(call, 'cache_hit') else False
        cache_savings = call.cache_cost_savings or 0

        if cache_hit:
            cache_hits += 1
            total_savings += cache_savings

            # Categorize by cache type
            cache_type_used = getattr(call, 'cache_type', 'exact')
            if cache_type_used == 'semantic':
                semantic_stats["hits"] += 1
                semantic_stats["savings"] += cache_savings
            elif cache_type_used == 'prefix':
                prefix_stats["hits"] += 1
                prefix_stats["savings"] += cache_savings
            else:
                exact_stats["hits"] += 1
                exact_stats["savings"] += cache_savings
        else:
            cache_misses += 1
            # Count as miss for each type
            exact_stats["misses"] += 1
            semantic_stats["misses"] += 1
            prefix_stats["misses"] += 1

    # Calculate hit rates using utility
    overall_hit_rate = calculate_hit_rate(cache_hits, total_calls)

    def calc_hit_rate(stats):
        total = stats["hits"] + stats["misses"]
        return calculate_hit_rate(stats["hits"], total)

    stats_by_type = []

    if cache_type in ("all", "exact"):
        stats_by_type.append({
            "cache_type": "exact",
            "total_lookups": exact_stats["hits"] + exact_stats["misses"],
            "hits": exact_stats["hits"],
            "misses": exact_stats["misses"],
            "hit_rate": calc_hit_rate(exact_stats),
            "savings": round(exact_stats["savings"], 4),
        })

    if cache_type in ("all", "semantic"):
        stats_by_type.append({
            "cache_type": "semantic",
            "total_lookups": semantic_stats["hits"] + semantic_stats["misses"],
            "hits": semantic_stats["hits"],
            "misses": semantic_stats["misses"],
            "hit_rate": calc_hit_rate(semantic_stats),
            "savings": round(semantic_stats["savings"], 4),
        })

    if cache_type in ("all", "prefix"):
        stats_by_type.append({
            "cache_type": "prefix",
            "total_lookups": prefix_stats["hits"] + prefix_stats["misses"],
            "hits": prefix_stats["hits"],
            "misses": prefix_stats["misses"],
            "hit_rate": calc_hit_rate(prefix_stats),
            "savings": round(prefix_stats["savings"], 4),
        })

    # Generate recommendations using config thresholds
    recommendations = []

    if overall_hit_rate < cfg.thresholds.low_cache_hit_rate:
        recommendations.append("Cache hit rate is low. Consider enabling semantic caching for similar prompts.")

    if exact_stats["hits"] == 0 and exact_stats["misses"] > 10:
        recommendations.append("No exact cache hits detected. Check if caching is properly configured.")

    if semantic_stats["hits"] == 0:
        recommendations.append("Semantic caching not utilized. Enable it to catch similar (not just identical) prompts.")

    if not recommendations:
        recommendations.append(f"Caching is working well with {overall_hit_rate:.1f}% hit rate.")

    return {
        "overall_hit_rate": overall_hit_rate,
        "total_cache_savings": round(total_savings, 4),
        "total_calls": total_calls,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "time_range": time_range,
        "stats_by_type": stats_by_type,
        "recommendations": recommendations,
    }


@tool_handler
async def get_cacheable_patterns(
    time_range: str = "30d",
    min_occurrences: int = 3,
    limit: int = 20,
    storage=None,
) -> dict[str, Any]:
    """
    Identify prompt patterns suitable for caching.

    Analyzes prompts to find:
    - Exact duplicates
    - Similar prompts (semantic clusters)
    - Common prefixes

    Args:
        time_range: Time period to analyze ("7d", "30d", "all")
        min_occurrences: Minimum times a pattern must occur
        limit: Maximum patterns to return
        storage: Storage instance (injected by server)

    Returns:
        Cacheable patterns with potential savings
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    if not calls:
        return {
            "patterns": [],
            "total_potential_savings": 0.0,
            "message": "No calls found to analyze"
        }

    # Group by cache key or prompt prefix
    prompt_groups: dict[str, list] = defaultdict(list)

    for call in calls:
        # Use cache_key if available, else first 100 chars of prompt
        if call.cache_key:
            key = call.cache_key
        elif call.prompt:
            key = call.prompt[:100].strip().lower()
        else:
            continue

        prompt_groups[key].append(call)

    # Find patterns with enough occurrences (use config or param)
    min_occ = min_occurrences or cfg.thresholds.min_duplicates_for_cache
    patterns = []
    total_potential_savings = 0.0

    for key, group in prompt_groups.items():
        if len(group) >= min_occ:
            total_cost = sum(c.total_cost or 0 for c in group)
            potential_savings = estimate_cache_savings(total_cost, len(group))
            total_potential_savings += potential_savings

            # Get sample operations
            operations = list(set(c.operation for c in group if c.operation))[:3]

            patterns.append({
                "pattern_key": key[:80] + "..." if len(key) > 80 else key,
                "occurrences": len(group),
                "total_cost": round(total_cost, 4),
                "potential_savings": round(potential_savings, 4),
                "potential_hit_rate": round((len(group) - 1) / len(group) * 100, 1),
                "operations": operations,
                "agents": list(set(c.agent_name for c in group if c.agent_name))[:3],
            })

    # Sort by potential savings
    patterns.sort(key=lambda x: x["potential_savings"], reverse=True)
    patterns = patterns[:limit]

    return {
        "patterns": patterns,
        "total_patterns_found": len(patterns),
        "total_potential_savings": round(total_potential_savings, 2),
        "recommendation": f"Found {len(patterns)} cacheable patterns that could save ${total_potential_savings:.2f}/month" if patterns else "No significant cacheable patterns detected.",
    }


@tool_handler
async def get_cache_clusters(
    time_range: str = "30d",
    storage=None,
) -> dict[str, Any]:
    """
    Get semantic cache clusters (groups of similar prompts).

    Args:
        time_range: Time period to analyze ("7d", "30d", "all")

    Returns:
        Cache clusters with similarity metrics
    """
    cfg = get_config()
    cutoff = parse_time_range(time_range)
    calls = storage.get_calls(since=cutoff, limit=cfg.query.default_limit)

    # Group by cache_cluster_id if available
    clusters: dict[str, list] = defaultdict(list)

    for call in calls:
        cluster_id = getattr(call, 'cache_cluster_id', None) or call.operation or "unclustered"
        clusters[cluster_id].append(call)

    cluster_info = []
    for cluster_id, group in clusters.items():
        if len(group) >= 2:
            total_cost = sum(c.total_cost or 0 for c in group)
            cluster_info.append({
                "cluster_id": cluster_id,
                "call_count": len(group),
                "unique_prompts": len(set(c.prompt[:100] if c.prompt else "" for c in group)),
                "total_cost": round(total_cost, 4),
                "avg_cost": round(total_cost / len(group), 6),
                "models_used": list(set(c.model_name for c in group if c.model_name)),
            })

    cluster_info.sort(key=lambda x: x["call_count"], reverse=True)

    return {
        "clusters": cluster_info[:20],
        "total_clusters": len(cluster_info),
    }


# ============================================================================
# Tool Definitions for Registration
# ============================================================================

CACHE_TOOLS = [
    ToolDefinition(
        name="get_cache_effectiveness",
        description="Analyze cache hit rates and cost savings across exact, semantic, and prefix caching strategies.",
        parameters={
            "type": "object",
            "properties": {
                "cache_type": {
                    "type": "string",
                    "description": "Type of cache to analyze",
                    "enum": ["exact", "semantic", "prefix", "all"],
                    "default": "all"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["24h", "7d", "30d", "all"],
                    "default": "7d"
                }
            }
        },
        handler=get_cache_effectiveness,
        category="cache"
    ),
    ToolDefinition(
        name="get_cacheable_patterns",
        description="Identify prompt patterns suitable for caching. Finds duplicate and similar prompts that could benefit from caching.",
        parameters={
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time period to analyze",
                    "enum": ["7d", "30d", "all"],
                    "default": "30d"
                },
                "min_occurrences": {
                    "type": "integer",
                    "description": "Minimum times a pattern must occur",
                    "default": 3
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum patterns to return",
                    "default": 20
                }
            }
        },
        handler=get_cacheable_patterns,
        category="cache"
    ),
    ToolDefinition(
        name="get_cache_clusters",
        description="Get semantic cache clusters - groups of similar prompts that share cache behavior.",
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
        handler=get_cache_clusters,
        category="cache"
    ),
]
