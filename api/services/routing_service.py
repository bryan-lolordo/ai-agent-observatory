"""
Routing Service - Story 3 Business Logic
Location: api/services/routing_service.py

Layer 1: get_summary() - Routing opportunities summary
Layer 2: get_operation_detail() - Operation calls with quality distribution
Layer 3: Shared CallDetail (uses llm_call_service.py)
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# =============================================================================
# CONSTANTS & THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "complexity_low": 0.4,      # Below this = simple task (can downgrade)
    "complexity_high": 0.7,     # Above this = complex task (may need upgrade)
    "quality_good": 8.0,        # Above this = good quality
    "quality_poor": 7.0,        # Below this = needs improvement
}

# Models considered "cheap" that might struggle with complex tasks
CHEAP_MODELS = [
    "gpt-4o-mini", "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
    "claude-3-haiku", "claude-3.5-haiku", "claude-instant"
]

# Model upgrade suggestions
MODEL_SUGGESTIONS = {
    "upgrade": "gpt-4o",
    "downgrade": "gpt-3.5-turbo",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_cheap_model(model_name: str) -> bool:
    """Check if model is in the cheap/lightweight tier."""
    if not model_name:
        return False
    model_lower = model_name.lower()
    return any(cheap.lower() in model_lower for cheap in CHEAP_MODELS)


def _estimate_complexity(call: Dict) -> Optional[float]:
    """
    Get or estimate complexity score for a call.
    
    Priority:
    1. Extracted complexity_score column
    2. routing_decision.complexity_score from JSON
    3. Heuristic estimation from token counts
    """
    # Try extracted column first
    if call.get("complexity_score") is not None:
        return call["complexity_score"]
    
    # Try routing_decision JSON
    routing = call.get("routing_decision") or {}
    if isinstance(routing, dict) and routing.get("complexity_score") is not None:
        return routing["complexity_score"]
    
    # Fallback: estimate from tokens
    prompt_tokens = call.get("prompt_tokens") or 0
    completion_tokens = call.get("completion_tokens") or 0
    
    if prompt_tokens == 0:
        return None
    
    # Heuristics:
    # - Longer prompts tend to be more complex
    # - Higher output/input ratio suggests reasoning tasks
    token_complexity = min(prompt_tokens / 2000, 1.0)
    output_ratio = completion_tokens / max(prompt_tokens, 1)
    reasoning_complexity = min(output_ratio / 0.5, 1.0)
    
    return round(token_complexity * 0.6 + reasoning_complexity * 0.4, 2)


def _get_quality_score(call: Dict) -> Optional[float]:
    """Get quality score from call data."""
    # Try extracted column first
    if call.get("judge_score") is not None:
        return call["judge_score"]
    
    # Try quality_evaluation JSON
    quality = call.get("quality_evaluation") or {}
    if isinstance(quality, dict):
        return quality.get("judge_score")
    
    return None


def _classify_opportunity(
    complexity: Optional[float],
    quality: Optional[float],
    is_cheap: bool
) -> str:
    """
    Determine routing opportunity type.
    
    Returns: "upgrade" | "downgrade" | "keep"
    """
    if complexity is None:
        return "keep"
    
    # UPGRADE: High complexity + cheap model (+ optionally low quality)
    if complexity >= THRESHOLDS["complexity_high"] and is_cheap:
        if quality is None or quality < THRESHOLDS["quality_good"]:
            return "upgrade"
    
    # DOWNGRADE: Low complexity + good quality (overpowered)
    if complexity < THRESHOLDS["complexity_low"]:
        if quality is not None and quality >= THRESHOLDS["quality_good"]:
            return "downgrade"
    
    return "keep"


def _get_complexity_display(complexity: Optional[float]) -> Tuple[str, str]:
    """Returns (label, emoji) for complexity score."""
    if complexity is None:
        return ("Unknown", "⚪")
    if complexity < THRESHOLDS["complexity_low"]:
        return ("Low", "🟢")
    if complexity < THRESHOLDS["complexity_high"]:
        return ("Medium", "🟡")
    return ("High", "🔴")


def _get_quality_status(quality: Optional[float]) -> str:
    """Returns status string for quality score."""
    if quality is None:
        return "unknown"
    if quality >= THRESHOLDS["quality_good"]:
        return "good"
    if quality >= THRESHOLDS["quality_poor"]:
        return "ok"
    return "poor"


def _get_opportunity_display(opportunity: str) -> Tuple[str, str, str]:
    """Returns (emoji, label, status_emoji) for opportunity type."""
    if opportunity == "downgrade":
        return ("↓", "Cheaper", "🔵")
    if opportunity == "upgrade":
        return ("↑", "Better", "🔴")
    return ("✓", "Keep", "🟢")


def _suggest_model(opportunity: str, current_model: str) -> Optional[str]:
    """Suggest a model based on opportunity type."""
    if opportunity == "downgrade":
        return MODEL_SUGGESTIONS["downgrade"]
    if opportunity == "upgrade":
        return MODEL_SUGGESTIONS["upgrade"]
    return None


def _format_timestamp(ts: Any) -> str:
    """Format timestamp for display."""
    if not ts:
        return "—"
    
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except:
            return ts[:16] if len(ts) > 16 else ts
    
    if isinstance(ts, datetime):
        return ts.strftime("%b %d, %I:%M %p")
    
    return str(ts)


def _build_quality_histogram(scores: List[float]) -> List[Dict]:
    """Build quality score histogram with 0.5 buckets."""
    if not scores:
        return []
    
    # Create buckets from 0 to 10 with 0.5 increments
    buckets = defaultdict(int)
    for score in scores:
        bucket = round(score * 2) / 2  # Round to nearest 0.5
        buckets[bucket] += 1
    
    # Return sorted buckets with data
    return [
        {"score": score, "count": count}
        for score, count in sorted(buckets.items())
        if count > 0
    ]


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> Dict:
    """
    Layer 1: Routing opportunities summary.
    
    Returns summary KPIs, operations table, and chart data for scatter plot.
    """
    # Filter to only LLM calls (exclude API operations without tokens)
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]
    
    if not llm_calls:
        return {
            "status": "ok",
            "health_score": 100.0,
            "summary": {
                "total_calls": 0,
                "current_model": "—",
                "current_model_pct": 0,
                "downgrade_count": 0,
                "upgrade_count": 0,
                "potential_savings": 0.0,
                "potential_savings_formatted": "$0.00",
            },
            "top_offender": None,
            "detail_table": [],
            "chart_data": [],
        }
    
    # Count models globally
    global_models = defaultdict(int)
    for call in llm_calls:
        model = call.get("model_name") or "unknown"
        global_models[model] += 1
    
    current_model = max(global_models, key=global_models.get) if global_models else "unknown"
    current_model_pct = round(global_models[current_model] / len(llm_calls) * 100) if llm_calls else 0
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_operation[(agent, op)].append(call)
    
    detail_table = []
    chart_data = []
    upgrade_ops = []
    downgrade_ops = []
    total_potential_savings = 0.0
    
    for (agent, op), op_calls in by_operation.items():
        # Calculate averages
        complexity_scores = [_estimate_complexity(c) for c in op_calls]
        complexity_scores = [c for c in complexity_scores if c is not None]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else None
        
        quality_scores = [_get_quality_score(c) for c in op_calls]
        quality_scores = [q for q in quality_scores if q is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Get primary model
        models_used = defaultdict(int)
        for call in op_calls:
            model = call.get("model_name") or "unknown"
            models_used[model] += 1
        primary_model = max(models_used, key=models_used.get) if models_used else "unknown"
        
        is_cheap = _is_cheap_model(primary_model)
        
        # Calculate costs
        total_cost = sum(c.get("total_cost") or 0 for c in op_calls)
        avg_cost = total_cost / len(op_calls) if op_calls else 0
        
        # Classify opportunity
        opportunity = _classify_opportunity(avg_complexity, avg_quality, is_cheap)
        opp_emoji, opp_label, status_emoji = _get_opportunity_display(opportunity)
        comp_label, comp_emoji = _get_complexity_display(avg_complexity)
        
        # Track upgrade/downgrade
        if opportunity == "upgrade":
            upgrade_ops.append((agent, op, avg_complexity, op_calls))
        elif opportunity == "downgrade":
            downgrade_ops.append((agent, op, avg_complexity, op_calls))
            # Estimate savings: ~50% cost reduction for downgrade
            total_potential_savings += total_cost * 0.5
        
        detail_table.append({
            "status_emoji": status_emoji,
            "agent_name": agent,
            "operation_name": op,
            "complexity": avg_complexity,
            "complexity_formatted": f"{avg_complexity:.2f}" if avg_complexity else "—",
            "complexity_label": comp_label,
            "complexity_emoji": comp_emoji,
            "avg_quality": avg_quality,
            "avg_quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
            "quality_status": _get_quality_status(avg_quality),
            "avg_cost": avg_cost,
            "avg_cost_formatted": f"${avg_cost:.4f}",
            "call_count": len(op_calls),
            "primary_model": primary_model,
            "opportunity": opportunity,
            "opportunity_emoji": opp_emoji,
            "opportunity_label": opp_label,
        })
        
        # Chart data for scatter plot
        if avg_complexity is not None:
            chart_data.append({
                "name": f"{agent}.{op}"[:25],
                "agent": agent,
                "operation": op,
                "complexity": avg_complexity,
                "quality": avg_quality or 0,
                "call_count": len(op_calls),
                "opportunity": opportunity,
            })
    
    # Sort by opportunity priority (upgrade first, then downgrade, then keep)
    priority = {"upgrade": 0, "downgrade": 1, "keep": 2}
    detail_table.sort(key=lambda x: (priority.get(x["opportunity"], 3), -(x["complexity"] or 0)))
    
    # Top offender (highest complexity needing upgrade)
    top_offender = None
    if upgrade_ops:
        upgrade_ops.sort(key=lambda x: -(x[2] or 0))
        agent, op, complexity, op_calls = upgrade_ops[0]
        
        # Get quality for this operation
        quality_scores = [_get_quality_score(c) for c in op_calls]
        quality_scores = [q for q in quality_scores if q is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        top_offender = {
            "agent": agent,
            "operation": op,
            "complexity": complexity,
            "complexity_formatted": f"{complexity:.2f}" if complexity else "—",
            "quality": avg_quality,
            "quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
            "call_count": len(op_calls),
            "opportunity": "upgrade",
            "opportunity_emoji": "↑",
            "suggested_model": MODEL_SUGGESTIONS["upgrade"],
            "diagnosis": f"High complexity ({complexity:.2f}) on lightweight model",
        }
    
    # Calculate health score
    issue_count = len(upgrade_ops) + len(downgrade_ops)
    if issue_count == 0:
        health_score = 100.0
        status = "ok"
    elif len(upgrade_ops) > 0:
        # Upgrades are more critical (quality issues)
        health_score = max(50, 85 - (len(upgrade_ops) * 15))
        status = "warning" if health_score >= 60 else "error"
    else:
        # Downgrades are optimization opportunities
        health_score = max(70, 95 - (len(downgrade_ops) * 5))
        status = "ok"
    
    return {
        "status": status,
        "health_score": round(health_score, 1),
        "summary": {
            "total_calls": len(llm_calls),
            "current_model": current_model,
            "current_model_pct": current_model_pct,
            "downgrade_count": len(downgrade_ops),
            "upgrade_count": len(upgrade_ops),
            "potential_savings": round(total_potential_savings, 2),
            "potential_savings_formatted": f"${total_potential_savings:.2f}",
        },
        "top_offender": top_offender,
        "detail_table": detail_table,
        "chart_data": chart_data,
    }


# =============================================================================
# LAYER 2: OPERATION DETAIL
# =============================================================================

def get_operation_detail(
    calls: List[Dict],
    agent: str,
    operation: str
) -> Optional[Dict]:
    """
    Layer 2: Operation detail with calls and quality distribution.
    
    Returns detailed view of a single operation including:
    - Summary stats (complexity, quality, cost)
    - Routing recommendation badge
    - All calls with metrics
    - Quality score histogram
    """
    # Filter calls for this operation
    op_calls = [
        c for c in calls
        if c.get("agent_name") == agent and c.get("operation") == operation
    ]
    
    if not op_calls:
        return None  # 404
    
    # Calculate aggregates
    complexity_scores = []
    quality_scores = []
    total_cost = 0.0
    models_used = defaultdict(int)
    
    for call in op_calls:
        # Complexity
        complexity = _estimate_complexity(call)
        if complexity is not None:
            complexity_scores.append(complexity)
        
        # Quality
        quality = _get_quality_score(call)
        if quality is not None:
            quality_scores.append(quality)
        
        # Cost
        total_cost += call.get("total_cost") or 0
        
        # Model
        model = call.get("model_name") or "unknown"
        models_used[model] += 1
    
    avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else None
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    avg_cost = total_cost / len(op_calls) if op_calls else 0
    primary_model = max(models_used, key=models_used.get) if models_used else "unknown"
    
    is_cheap = _is_cheap_model(primary_model)
    opportunity = _classify_opportunity(avg_complexity, avg_quality, is_cheap)
    opp_emoji, opp_label, status_emoji = _get_opportunity_display(opportunity)
    comp_label, comp_emoji = _get_complexity_display(avg_complexity)
    suggested_model = _suggest_model(opportunity, primary_model)
    
    # Build calls list (sorted by timestamp, newest first)
    calls_list = []
    sorted_calls = sorted(op_calls, key=lambda x: x.get("timestamp") or "", reverse=True)
    
    for i, call in enumerate(sorted_calls):
        quality = _get_quality_score(call)
        latency = call.get("latency_ms") or 0
        cost = call.get("total_cost") or 0
        
        calls_list.append({
            "call_id": call.get("id"),
            "index": i + 1,
            "timestamp": call.get("timestamp"),
            "timestamp_formatted": _format_timestamp(call.get("timestamp")),
            "quality": quality,
            "quality_formatted": f"{quality:.1f}/10" if quality else "—",
            "quality_status": _get_quality_status(quality),
            "latency_ms": latency,
            "latency_formatted": f"{latency / 1000:.1f}s" if latency else "—",
            "total_tokens": call.get("total_tokens") or 0,
            "total_cost": cost,
            "cost_formatted": f"${cost:.4f}",
            "model_name": call.get("model_name") or "—",
        })
    
    # Quality distribution histogram
    quality_distribution = _build_quality_histogram(quality_scores)
    
    return {
        "agent_name": agent,
        "operation_name": operation,
        
        # Complexity
        "complexity": avg_complexity,
        "complexity_formatted": f"{avg_complexity:.2f}" if avg_complexity else "—",
        "complexity_label": comp_label,
        "complexity_emoji": comp_emoji,
        
        # Quality
        "avg_quality": avg_quality,
        "avg_quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
        "quality_status": _get_quality_status(avg_quality),
        
        # Cost
        "avg_cost": avg_cost,
        "avg_cost_formatted": f"${avg_cost:.4f}",
        "total_cost": total_cost,
        "total_cost_formatted": f"${total_cost:.2f}",
        
        # Counts
        "call_count": len(op_calls),
        "primary_model": primary_model,
        
        # Routing recommendation (badge)
        "opportunity": opportunity,
        "opportunity_emoji": opp_emoji,
        "opportunity_label": opp_label,
        "status_emoji": status_emoji,
        "suggested_model": suggested_model,
        
        # Calls table
        "calls": calls_list,
        
        # Histogram
        "quality_distribution": quality_distribution,
    }