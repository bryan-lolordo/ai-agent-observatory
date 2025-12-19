"""
Optimization Service - Story 8 Business Logic
Location: api/services/optimization_service.py

MVP: Baseline mode only - shows current metrics vs targets.
Future: Will add before/after comparison when optimizations are tracked.

Layer 1: get_summary() - Baseline metrics and pending optimizations
Layer 2: get_optimization_detail() - Placeholder for future
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

# =============================================================================
# CONSTANTS & TARGETS
# =============================================================================

TARGETS = {
    "latency_ms": 1000,          # Target: < 1 second
    "weekly_cost": 2.00,         # Target: < $2/week
    "cache_hit_rate": 50.0,      # Target: > 50%
    "quality_score": 8.0,        # Target: > 8.0
    "error_rate": 1.0,           # Target: < 1%
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_gap_status(current: float, target: float, lower_is_better: bool = True) -> str:
    """Determine status based on gap to target."""
    if lower_is_better:
        if current <= target:
            return "met"
        elif current <= target * 1.5:
            return "close"
        else:
            return "far"
    else:
        if current >= target:
            return "met"
        elif current >= target * 0.75:
            return "close"
        else:
            return "far"


def _format_gap(current: float, target: float, unit: str = "", lower_is_better: bool = True) -> str:
    """Format gap between current and target."""
    gap = target - current if lower_is_better else current - target
    sign = "+" if gap > 0 else ""
    
    if unit == "s":
        return f"{sign}{gap:.2f}s"
    elif unit == "$":
        return f"{sign}${abs(gap):.2f}"
    elif unit == "%":
        return f"{sign}{gap:.1f}%"
    else:
        return f"{sign}{gap:.1f}"


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(
    calls: List[Dict], 
    project: str = None, 
    days: int = 7,
    optimizations: List[Dict] = None
) -> Dict:
    """
    Layer 1: Optimization impact summary.
    
    MVP: Baseline mode - shows current metrics and targets.
    """
    # Filter to LLM calls
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]
    
    if not llm_calls:
        return {
            "status": "ok",
            "health_score": 50.0,
            "mode": "baseline",
            "summary": {
                "total_calls": 0,
                "has_optimizations": False,
            },
            "baselines": [],
            "pending_optimizations": [],
        }
    
    # Calculate current metrics
    latencies = [c.get("latency_ms") or 0 for c in llm_calls if c.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    total_cost = sum(c.get("total_cost") or 0 for c in llm_calls)
    
    # Cache hit rate (simplified - check for cache_hit field)
    cache_hits = sum(1 for c in llm_calls if c.get("cache_hit"))
    cache_rate = (cache_hits / len(llm_calls) * 100) if llm_calls else 0
    
    # Quality score
    quality_scores = [c.get("judge_score") for c in llm_calls if c.get("judge_score") is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    
    # Error rate
    errors = sum(1 for c in llm_calls if not c.get("success", True))
    error_rate = (errors / len(llm_calls) * 100) if llm_calls else 0
    
    # Build baseline metrics
    baselines = [
        {
            "metric": "Avg Latency",
            "current": avg_latency / 1000,  # Convert to seconds
            "current_formatted": f"{avg_latency / 1000:.2f}s",
            "target": TARGETS["latency_ms"] / 1000,
            "target_formatted": f"<{TARGETS['latency_ms'] / 1000:.1f}s",
            "gap": _format_gap(avg_latency / 1000, TARGETS["latency_ms"] / 1000, "s", True),
            "status": _get_gap_status(avg_latency, TARGETS["latency_ms"], True),
            "priority": "high" if avg_latency > TARGETS["latency_ms"] * 2 else "medium",
        },
        {
            "metric": "Weekly Cost",
            "current": total_cost,
            "current_formatted": f"${total_cost:.2f}",
            "target": TARGETS["weekly_cost"],
            "target_formatted": f"<${TARGETS['weekly_cost']:.2f}",
            "gap": _format_gap(total_cost, TARGETS["weekly_cost"], "$", True),
            "status": _get_gap_status(total_cost, TARGETS["weekly_cost"], True),
            "priority": "high" if total_cost > TARGETS["weekly_cost"] * 2 else "medium",
        },
        {
            "metric": "Cache Hit Rate",
            "current": cache_rate,
            "current_formatted": f"{cache_rate:.0f}%",
            "target": TARGETS["cache_hit_rate"],
            "target_formatted": f">{TARGETS['cache_hit_rate']:.0f}%",
            "gap": _format_gap(cache_rate, TARGETS["cache_hit_rate"], "%", False),
            "status": _get_gap_status(cache_rate, TARGETS["cache_hit_rate"], False),
            "priority": "high" if cache_rate < 10 else "medium",
        },
        {
            "metric": "Avg Quality",
            "current": avg_quality,
            "current_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
            "target": TARGETS["quality_score"],
            "target_formatted": f">{TARGETS['quality_score']:.1f}",
            "gap": _format_gap(avg_quality or 0, TARGETS["quality_score"], "", False) if avg_quality else "—",
            "status": _get_gap_status(avg_quality or 0, TARGETS["quality_score"], False) if avg_quality else "unknown",
            "priority": "medium",
        },
        {
            "metric": "Error Rate",
            "current": error_rate,
            "current_formatted": f"{error_rate:.1f}%",
            "target": TARGETS["error_rate"],
            "target_formatted": f"<{TARGETS['error_rate']:.0f}%",
            "gap": _format_gap(error_rate, TARGETS["error_rate"], "%", True),
            "status": _get_gap_status(error_rate, TARGETS["error_rate"], True),
            "priority": "medium" if error_rate > TARGETS["error_rate"] else "low",
        },
    ]
    
    # Identify pending optimizations from other stories
    pending_optimizations = _identify_pending_optimizations(llm_calls)
    
    # Calculate health score based on how many targets are met
    met_count = sum(1 for b in baselines if b["status"] == "met")
    health_score = (met_count / len(baselines)) * 100 if baselines else 50
    
    status = "ok" if health_score >= 60 else "warning" if health_score >= 40 else "error"
    
    return {
        "status": status,
        "health_score": round(health_score, 1),
        "mode": "baseline",
        "summary": {
            "total_calls": len(llm_calls),
            "days": days,
            "has_optimizations": False,
            "targets_met": met_count,
            "total_targets": len(baselines),
        },
        "kpis": {
            "avg_latency": avg_latency / 1000,
            "avg_latency_formatted": f"{avg_latency / 1000:.2f}s",
            "total_cost": total_cost,
            "total_cost_formatted": f"${total_cost:.2f}",
            "avg_quality": avg_quality,
            "avg_quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
            "cache_hit_rate": cache_rate,
            "cache_hit_rate_formatted": f"{cache_rate:.0f}%",
        },
        "baselines": baselines,
        "pending_optimizations": pending_optimizations,
    }


def _identify_pending_optimizations(calls: List[Dict]) -> List[Dict]:
    """
    Identify potential optimizations based on call data.
    
    This connects findings from Stories 1-7 to actionable items.
    """
    optimizations = []
    
    # Group by operation for analysis
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_operation[(agent, op)].append(call)
    
    for (agent, op), op_calls in by_operation.items():
        # Check for latency issues (Story 1)
        latencies = [c.get("latency_ms") or 0 for c in op_calls if c.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        if avg_latency > 5000:  # > 5 seconds
            optimizations.append({
                "story": 1,
                "story_name": "Latency Monster",
                "target": f"{agent}.{op}",
                "issue": f"Avg latency {avg_latency/1000:.1f}s",
                "recommendation": "Constrain output or stream response",
                "expected_impact": "-75% latency",
                "status": "todo",
            })
        
        # Check for cache opportunities (Story 2)
        # Simplified: if same operation called many times, might benefit from caching
        if len(op_calls) > 10:
            cache_hits = sum(1 for c in op_calls if c.get("cache_hit"))
            if cache_hits == 0:
                optimizations.append({
                    "story": 2,
                    "story_name": "Cache Strategy",
                    "target": f"{agent}.{op}",
                    "issue": f"{len(op_calls)} calls with 0% cache hit",
                    "recommendation": "Enable semantic caching",
                    "expected_impact": "-50% cost",
                    "status": "todo",
                })
        
        # Check for quality issues (Story 4)
        quality_scores = [c.get("judge_score") for c in op_calls if c.get("judge_score") is not None]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality < 7.0:
                optimizations.append({
                    "story": 4,
                    "story_name": "Quality Issues",
                    "target": f"{agent}.{op}",
                    "issue": f"Avg quality {avg_quality:.1f}/10",
                    "recommendation": "Improve prompt or upgrade model",
                    "expected_impact": "+2.0 quality",
                    "status": "todo",
                })
        
        # Check for token imbalance (Story 5)
        prompt_tokens = [c.get("prompt_tokens") or 0 for c in op_calls]
        completion_tokens = [c.get("completion_tokens") or 0 for c in op_calls]
        avg_prompt = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
        avg_completion = sum(completion_tokens) / len(completion_tokens) if completion_tokens else 1
        
        ratio = avg_prompt / avg_completion if avg_completion > 0 else 0
        if ratio > 15:
            optimizations.append({
                "story": 5,
                "story_name": "Token Efficiency",
                "target": f"{agent}.{op}",
                "issue": f"Token ratio {ratio:.0f}:1",
                "recommendation": "Sliding window or summarize history",
                "expected_impact": "-50% tokens",
                "status": "todo",
            })
    
    # Sort by story number, limit to top 5
    optimizations.sort(key=lambda x: x["story"])
    return optimizations[:5]


# =============================================================================
# LAYER 2: OPTIMIZATION DETAIL (Placeholder)
# =============================================================================

def get_optimization_detail(
    calls: List[Dict],
    optimization_id: str
) -> Optional[Dict]:
    """
    Layer 2: Optimization detail.
    
    MVP: Returns placeholder - will be implemented when we add
    optimization tracking with before/after dates.
    """
    return {
        "status": "not_implemented",
        "message": "Optimization tracking coming soon. Implement optimizations from Stories 1-7, then return here to measure impact.",
        "optimization_id": optimization_id,
    }