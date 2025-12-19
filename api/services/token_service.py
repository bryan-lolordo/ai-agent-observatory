"""
Token Service - Story 5 Business Logic
Location: api/services/token_service.py

Layer 1: get_summary() - Token efficiency summary with ratio analysis
Layer 2: get_operation_detail() - Operation token breakdown
Layer 3: Shared CallDetail (uses llm_call_service.py)
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# =============================================================================
# CONSTANTS & THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "ratio_severe": 20.0,      # Above this = severe imbalance
    "ratio_high": 10.0,        # Above this = high imbalance
    "ratio_moderate": 5.0,     # Above this = moderate imbalance
    # Below 5.0 = balanced
    
    "history_pct_warning": 50.0,   # Chat history > 50% of prompt = warning
    "system_pct_warning": 40.0,    # System prompt > 40% of prompt = warning
}

# Cost per 1K tokens (rough estimate for waste calculation)
COST_PER_1K_PROMPT = 0.003  # ~$3/1M tokens


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _calculate_ratio(prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Calculate prompt:completion ratio."""
    if not completion_tokens or completion_tokens == 0:
        return None
    return prompt_tokens / completion_tokens


def _get_ratio_status(ratio: Optional[float]) -> Tuple[str, str, str]:
    """
    Returns (status, emoji, label) for ratio.
    """
    if ratio is None:
        return ("unknown", "⚪", "Unknown")
    if ratio >= THRESHOLDS["ratio_severe"]:
        return ("severe", "🔴", "Severe Imbalance")
    if ratio >= THRESHOLDS["ratio_high"]:
        return ("high", "🔴", "High Imbalance")
    if ratio >= THRESHOLDS["ratio_moderate"]:
        return ("moderate", "🟡", "Moderate")
    return ("balanced", "🟢", "Balanced")


def _format_ratio(ratio: Optional[float]) -> str:
    """Format ratio for display."""
    if ratio is None:
        return "—"
    if ratio >= 100:
        return f"{int(ratio)}:1"
    if ratio >= 10:
        return f"{ratio:.0f}:1"
    return f"{ratio:.1f}:1"


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


def _get_token_breakdown(call: Dict) -> Dict:
    """
    Extract token breakdown from call data.
    
    Returns dict with system_prompt, chat_history, user_message, etc.
    """
    # Try extracted columns first
    breakdown = {
        "system_prompt_tokens": call.get("system_prompt_tokens") or 0,
        "user_message_tokens": call.get("user_message_tokens") or 0,
        "chat_history_tokens": call.get("chat_history_tokens") or 0,
        "conversation_context_tokens": call.get("conversation_context_tokens") or 0,
        "tool_definitions_tokens": call.get("tool_definitions_tokens") or 0,
    }
    
    # Try prompt_breakdown JSON if columns are empty
    prompt_breakdown = call.get("prompt_breakdown") or {}
    if isinstance(prompt_breakdown, dict):
        if not breakdown["system_prompt_tokens"]:
            breakdown["system_prompt_tokens"] = prompt_breakdown.get("system_prompt_tokens") or 0
        if not breakdown["user_message_tokens"]:
            breakdown["user_message_tokens"] = prompt_breakdown.get("user_message_tokens") or 0
        if not breakdown["chat_history_tokens"]:
            breakdown["chat_history_tokens"] = prompt_breakdown.get("chat_history_tokens") or 0
    
    # Calculate "other" tokens (anything not categorized)
    categorized = (
        breakdown["system_prompt_tokens"] +
        breakdown["user_message_tokens"] +
        breakdown["chat_history_tokens"] +
        breakdown["conversation_context_tokens"] +
        breakdown["tool_definitions_tokens"]
    )
    
    total_prompt = call.get("prompt_tokens") or 0
    breakdown["other_tokens"] = max(0, total_prompt - categorized)
    breakdown["total_prompt_tokens"] = total_prompt
    
    return breakdown


def _estimate_wasted_cost(calls: List[Dict], avg_ratio: float) -> float:
    """
    Estimate cost wasted due to token imbalance.
    
    Assumes a "balanced" ratio of 3:1 as baseline.
    Excess tokens beyond that are considered "waste".
    """
    if avg_ratio <= 3.0:
        return 0.0
    
    total_waste = 0.0
    baseline_ratio = 3.0
    
    for call in calls:
        prompt = call.get("prompt_tokens") or 0
        completion = call.get("completion_tokens") or 1
        ratio = prompt / completion
        
        if ratio > baseline_ratio:
            # Excess tokens = actual - (completion * baseline)
            ideal_prompt = completion * baseline_ratio
            excess_tokens = prompt - ideal_prompt
            waste = (excess_tokens / 1000) * COST_PER_1K_PROMPT
            total_waste += waste
    
    return total_waste


def _build_ratio_histogram(ratios: List[float]) -> List[Dict]:
    """Build ratio distribution histogram."""
    if not ratios:
        return []
    
    # Buckets: 0-2, 2-5, 5-10, 10-20, 20+
    buckets = [
        {"label": "0-2:1", "min": 0, "max": 2, "count": 0, "status": "balanced"},
        {"label": "2-5:1", "min": 2, "max": 5, "count": 0, "status": "balanced"},
        {"label": "5-10:1", "min": 5, "max": 10, "count": 0, "status": "moderate"},
        {"label": "10-20:1", "min": 10, "max": 20, "count": 0, "status": "high"},
        {"label": "20+:1", "min": 20, "max": 9999, "count": 0, "status": "severe"},
    ]
    
    for ratio in ratios:
        for bucket in buckets:
            if bucket["min"] <= ratio < bucket["max"]:
                bucket["count"] += 1
                break
    
    return [b for b in buckets if b["count"] > 0 or b["min"] < max(ratios)]


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> Dict:
    """
    Layer 1: Token efficiency summary.
    
    Returns summary KPIs, operations table, and ratio distribution chart.
    """
    # Filter to only LLM calls with tokens
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]
    
    if not llm_calls:
        return {
            "status": "ok",
            "health_score": 100.0,
            "summary": {
                "total_calls": 0,
                "avg_ratio": None,
                "avg_ratio_formatted": "—",
                "imbalanced_count": 0,
                "worst_ratio": None,
                "worst_ratio_formatted": "—",
                "wasted_cost": 0.0,
                "wasted_cost_formatted": "$0.00",
            },
            "top_offender": None,
            "detail_table": [],
            "chart_data": [],
        }
    
    # Global metrics
    all_ratios = []
    for call in llm_calls:
        ratio = _calculate_ratio(
            call.get("prompt_tokens") or 0,
            call.get("completion_tokens") or 1
        )
        if ratio is not None:
            all_ratios.append(ratio)
    
    avg_ratio = sum(all_ratios) / len(all_ratios) if all_ratios else None
    worst_ratio = max(all_ratios) if all_ratios else None
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_operation[(agent, op)].append(call)
    
    detail_table = []
    imbalanced_ops = []
    
    for (agent, op), op_calls in by_operation.items():
        # Calculate averages
        prompt_tokens = [c.get("prompt_tokens") or 0 for c in op_calls]
        completion_tokens = [c.get("completion_tokens") or 0 for c in op_calls]
        
        avg_prompt = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
        avg_completion = sum(completion_tokens) / len(completion_tokens) if completion_tokens else 0
        
        ratio = _calculate_ratio(int(avg_prompt), int(avg_completion))
        status, status_emoji, status_label = _get_ratio_status(ratio)
        
        total_cost = sum(c.get("total_cost") or 0 for c in op_calls)
        
        # Track imbalanced operations
        if ratio is not None and ratio >= THRESHOLDS["ratio_high"]:
            imbalanced_ops.append((agent, op, ratio, op_calls))
        
        detail_table.append({
            "agent_name": agent,
            "operation_name": op,
            "status": status,
            "status_emoji": status_emoji,
            "status_label": status_label,
            "avg_prompt_tokens": int(avg_prompt),
            "avg_prompt_formatted": f"{int(avg_prompt):,}",
            "avg_completion_tokens": int(avg_completion),
            "avg_completion_formatted": f"{int(avg_completion):,}",
            "ratio": ratio,
            "ratio_formatted": _format_ratio(ratio),
            "total_cost": total_cost,
            "total_cost_formatted": f"${total_cost:.2f}",
            "call_count": len(op_calls),
        })
    
    # Sort by ratio (worst first)
    detail_table.sort(key=lambda x: -(x["ratio"] or 0))
    
    # Top offender (worst ratio operation)
    top_offender = None
    if imbalanced_ops:
        imbalanced_ops.sort(key=lambda x: -x[2])  # Sort by ratio descending
        agent, op, ratio, op_calls = imbalanced_ops[0]
        
        # Get breakdown for diagnosis
        avg_breakdown = {"system": 0, "history": 0, "user": 0}
        for call in op_calls:
            breakdown = _get_token_breakdown(call)
            avg_breakdown["system"] += breakdown["system_prompt_tokens"]
            avg_breakdown["history"] += breakdown["chat_history_tokens"]
            avg_breakdown["user"] += breakdown["user_message_tokens"]
        
        for key in avg_breakdown:
            avg_breakdown[key] /= len(op_calls)
        
        # Determine likely cause
        total = avg_breakdown["system"] + avg_breakdown["history"] + avg_breakdown["user"]
        if total > 0:
            history_pct = (avg_breakdown["history"] / total) * 100
            system_pct = (avg_breakdown["system"] / total) * 100
            
            if history_pct > 50:
                diagnosis = f"Chat history is {history_pct:.0f}% of prompt - likely unbounded history"
            elif system_pct > 40:
                diagnosis = f"System prompt is {system_pct:.0f}% of prompt - consider compression"
            else:
                diagnosis = f"High ratio ({_format_ratio(ratio)}) - review prompt composition"
        else:
            diagnosis = f"High ratio ({_format_ratio(ratio)}) - sending lots, getting little"
        
        top_offender = {
            "agent": agent,
            "operation": op,
            "ratio": ratio,
            "ratio_formatted": _format_ratio(ratio),
            "call_count": len(op_calls),
            "diagnosis": diagnosis,
        }
    
    # Estimate wasted cost
    wasted_cost = _estimate_wasted_cost(llm_calls, avg_ratio or 0)
    
    # Chart data - ratio distribution
    chart_data = _build_ratio_histogram(all_ratios)
    
    # Calculate health score
    if avg_ratio is None:
        health_score = 100.0
        status = "ok"
    elif avg_ratio >= THRESHOLDS["ratio_severe"]:
        health_score = max(30, 50 - (avg_ratio - 20))
        status = "error"
    elif avg_ratio >= THRESHOLDS["ratio_high"]:
        health_score = max(50, 70 - (avg_ratio - 10) * 2)
        status = "warning"
    elif avg_ratio >= THRESHOLDS["ratio_moderate"]:
        health_score = max(70, 85 - (avg_ratio - 5) * 3)
        status = "ok"
    else:
        health_score = min(100, 90 + (5 - avg_ratio) * 2)
        status = "ok"
    
    return {
        "status": status,
        "health_score": round(health_score, 1),
        "summary": {
            "total_calls": len(llm_calls),
            "avg_ratio": avg_ratio,
            "avg_ratio_formatted": _format_ratio(avg_ratio),
            "imbalanced_count": len(imbalanced_ops),
            "worst_ratio": worst_ratio,
            "worst_ratio_formatted": _format_ratio(worst_ratio),
            "wasted_cost": round(wasted_cost, 2),
            "wasted_cost_formatted": f"${wasted_cost:.2f}",
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
    Layer 2: Operation detail with token breakdown.
    
    Returns detailed view of a single operation including:
    - Summary stats (avg prompt, completion, ratio)
    - Token breakdown visualization data
    - Problem detection
    - All calls with token details
    """
    # Filter calls for this operation
    op_calls = [
        c for c in calls
        if c.get("agent_name") == agent and c.get("operation") == operation
    ]
    
    if not op_calls:
        return None  # 404
    
    # Calculate aggregates
    prompt_tokens = [c.get("prompt_tokens") or 0 for c in op_calls]
    completion_tokens = [c.get("completion_tokens") or 0 for c in op_calls]
    
    avg_prompt = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
    avg_completion = sum(completion_tokens) / len(completion_tokens) if completion_tokens else 0
    
    ratio = _calculate_ratio(int(avg_prompt), int(avg_completion))
    status, status_emoji, status_label = _get_ratio_status(ratio)
    
    total_cost = sum(c.get("total_cost") or 0 for c in op_calls)
    
    # Aggregate token breakdown
    breakdown_totals = {
        "system_prompt_tokens": 0,
        "user_message_tokens": 0,
        "chat_history_tokens": 0,
        "conversation_context_tokens": 0,
        "tool_definitions_tokens": 0,
        "other_tokens": 0,
    }
    
    for call in op_calls:
        breakdown = _get_token_breakdown(call)
        for key in breakdown_totals:
            breakdown_totals[key] += breakdown.get(key, 0)
    
    # Calculate averages
    n = len(op_calls)
    avg_breakdown = {k: v / n for k, v in breakdown_totals.items()}
    
    # Calculate percentages
    total_prompt_avg = avg_prompt
    if total_prompt_avg > 0:
        breakdown_pcts = {
            "system_pct": (avg_breakdown["system_prompt_tokens"] / total_prompt_avg) * 100,
            "user_pct": (avg_breakdown["user_message_tokens"] / total_prompt_avg) * 100,
            "history_pct": (avg_breakdown["chat_history_tokens"] / total_prompt_avg) * 100,
            "context_pct": (avg_breakdown["conversation_context_tokens"] / total_prompt_avg) * 100,
            "tools_pct": (avg_breakdown["tool_definitions_tokens"] / total_prompt_avg) * 100,
            "other_pct": (avg_breakdown["other_tokens"] / total_prompt_avg) * 100,
        }
    else:
        breakdown_pcts = {k: 0 for k in ["system_pct", "user_pct", "history_pct", "context_pct", "tools_pct", "other_pct"]}
    
    # Build token breakdown for visualization
    token_breakdown = [
        {
            "component": "System Prompt",
            "tokens": int(avg_breakdown["system_prompt_tokens"]),
            "percentage": round(breakdown_pcts["system_pct"], 1),
            "status": "warning" if breakdown_pcts["system_pct"] > THRESHOLDS["system_pct_warning"] else "ok",
        },
        {
            "component": "Chat History",
            "tokens": int(avg_breakdown["chat_history_tokens"]),
            "percentage": round(breakdown_pcts["history_pct"], 1),
            "status": "warning" if breakdown_pcts["history_pct"] > THRESHOLDS["history_pct_warning"] else "ok",
        },
        {
            "component": "User Message",
            "tokens": int(avg_breakdown["user_message_tokens"]),
            "percentage": round(breakdown_pcts["user_pct"], 1),
            "status": "ok",
        },
        {
            "component": "Context",
            "tokens": int(avg_breakdown["conversation_context_tokens"]),
            "percentage": round(breakdown_pcts["context_pct"], 1),
            "status": "ok",
        },
        {
            "component": "Tool Definitions",
            "tokens": int(avg_breakdown["tool_definitions_tokens"]),
            "percentage": round(breakdown_pcts["tools_pct"], 1),
            "status": "ok",
        },
    ]
    
    # Filter out zero-token components
    token_breakdown = [t for t in token_breakdown if t["tokens"] > 0]
    
    # Problem detection
    problems = []
    if breakdown_pcts["history_pct"] > THRESHOLDS["history_pct_warning"]:
        problems.append({
            "emoji": "🔴",
            "title": f"Chat history is {breakdown_pcts['history_pct']:.0f}% of prompt tokens!",
            "description": "This operation sends large conversation history on every call. Consider sliding window or summarization.",
        })
    if breakdown_pcts["system_pct"] > THRESHOLDS["system_pct_warning"]:
        problems.append({
            "emoji": "🟡",
            "title": f"System prompt is {breakdown_pcts['system_pct']:.0f}% of prompt tokens",
            "description": "Large static instructions. Consider prompt compression or caching.",
        })
    if ratio and ratio >= THRESHOLDS["ratio_high"] and not problems:
        problems.append({
            "emoji": "🔴",
            "title": f"High ratio ({_format_ratio(ratio)}) - sending lots, getting little",
            "description": "Review prompt composition to identify token waste.",
        })
    
    # Build calls list (sorted by ratio, worst first)
    calls_list = []
    sorted_calls = sorted(
        op_calls,
        key=lambda x: -(_calculate_ratio(x.get("prompt_tokens") or 0, x.get("completion_tokens") or 1) or 0)
    )
    
    for i, call in enumerate(sorted_calls):
        prompt = call.get("prompt_tokens") or 0
        completion = call.get("completion_tokens") or 0
        call_ratio = _calculate_ratio(prompt, completion)
        
        breakdown = _get_token_breakdown(call)
        
        calls_list.append({
            "call_id": call.get("id"),
            "index": i + 1,
            "timestamp": call.get("timestamp"),
            "timestamp_formatted": _format_timestamp(call.get("timestamp")),
            "prompt_tokens": prompt,
            "prompt_formatted": f"{prompt:,}",
            "completion_tokens": completion,
            "completion_formatted": f"{completion:,}",
            "history_tokens": breakdown["chat_history_tokens"],
            "history_formatted": f"{breakdown['chat_history_tokens']:,}",
            "ratio": call_ratio,
            "ratio_formatted": _format_ratio(call_ratio),
            "ratio_status": _get_ratio_status(call_ratio)[0],
            "total_cost": call.get("total_cost") or 0,
            "cost_formatted": f"${(call.get('total_cost') or 0):.4f}",
            "model_name": call.get("model_name") or "—",
        })
    
    return {
        "agent_name": agent,
        "operation_name": operation,
        
        # Status badge
        "status": status,
        "status_emoji": status_emoji,
        "status_label": status_label,
        
        # Summary stats
        "avg_prompt_tokens": int(avg_prompt),
        "avg_prompt_formatted": f"{int(avg_prompt):,}",
        "avg_completion_tokens": int(avg_completion),
        "avg_completion_formatted": f"{int(avg_completion):,}",
        "ratio": ratio,
        "ratio_formatted": _format_ratio(ratio),
        "total_cost": total_cost,
        "total_cost_formatted": f"${total_cost:.2f}",
        "call_count": len(op_calls),
        
        # Token breakdown for visualization
        "token_breakdown": token_breakdown,
        
        # Problem detection
        "problems": problems,
        
        # Calls table
        "calls": calls_list,
    }