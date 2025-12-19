"""
Quality Service - Story 4 Business Logic
Location: api/services/quality_service.py

Layer 1: get_summary() - Quality issues summary
Layer 2: get_operation_detail() - Operation calls with quality breakdown
Layer 3: Shared CallDetail (uses llm_call_service.py)
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# =============================================================================
# CONSTANTS & THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "quality_critical": 5.0,    # Below this = critical
    "quality_low": 7.0,         # Below this = low quality
    "quality_good": 8.0,        # Above this = good
    "error_rate_critical": 5.0, # Above 5% = critical
    "error_rate_warning": 2.0,  # Above 2% = warning
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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


def _get_hallucination_flag(call: Dict) -> bool:
    """Check if call has hallucination flag."""
    # Try extracted column first
    if call.get("hallucination_flag") is not None:
        return bool(call["hallucination_flag"])
    
    # Try quality_evaluation JSON
    quality = call.get("quality_evaluation") or {}
    if isinstance(quality, dict):
        return bool(quality.get("hallucination_flag", False))
    
    return False


def _get_error_category(call: Dict) -> Optional[str]:
    """Get error category from call data."""
    # Try extracted column first
    if call.get("error_category"):
        return call["error_category"]
    
    # Try quality_evaluation JSON
    quality = call.get("quality_evaluation") or {}
    if isinstance(quality, dict) and quality.get("error_category"):
        return quality["error_category"]
    
    # Fallback to error_type
    return call.get("error_type")


def _get_quality_status(score: Optional[float]) -> Tuple[str, str, str]:
    """
    Returns (status, emoji, label) for quality score.
    """
    if score is None:
        return ("unknown", "⚪", "Not Evaluated")
    if score < THRESHOLDS["quality_critical"]:
        return ("critical", "🔴", "Critical")
    if score < THRESHOLDS["quality_low"]:
        return ("low", "🔴", "Low Quality")
    if score < THRESHOLDS["quality_good"]:
        return ("ok", "🟡", "Acceptable")
    return ("good", "🟢", "Good")


def _get_error_rate_status(error_rate: float) -> Tuple[str, str]:
    """Returns (status, emoji) for error rate."""
    if error_rate >= THRESHOLDS["error_rate_critical"]:
        return ("critical", "🔴")
    if error_rate >= THRESHOLDS["error_rate_warning"]:
        return ("warning", "🟡")
    return ("healthy", "🟢")


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


def _build_quality_histogram(scores: List[float], bucket_size: float = 1.0) -> List[Dict]:
    """Build quality score histogram."""
    if not scores:
        return []
    
    # Create buckets (0-1, 1-2, ..., 9-10)
    buckets = defaultdict(int)
    for score in scores:
        bucket = int(score)  # Floor to nearest integer
        bucket = min(bucket, 9)  # Cap at 9 (9-10 bucket)
        buckets[bucket] += 1
    
    # Return all buckets from 0 to 10
    result = []
    for i in range(11):
        count = buckets.get(i, 0)
        if i < 10:
            label = f"{i}-{i+1}"
        else:
            label = "10"
        
        # Determine color based on threshold
        if i < 5:
            color = "critical"
        elif i < 7:
            color = "low"
        elif i < 8:
            color = "ok"
        else:
            color = "good"
        
        result.append({
            "bucket": i,
            "label": label,
            "count": count,
            "color": color,
        })
    
    # Filter to only buckets with data or adjacent to data
    min_bucket = min(buckets.keys()) if buckets else 0
    max_bucket = max(buckets.keys()) if buckets else 10
    
    return [r for r in result if min_bucket - 1 <= r["bucket"] <= max_bucket + 1]


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> Dict:
    """
    Layer 1: Quality issues summary.
    
    Returns summary KPIs, operations table, and chart data.
    """
    # Filter to only LLM calls with tokens
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]
    
    if not llm_calls:
        return {
            "status": "ok",
            "health_score": 100.0,
            "summary": {
                "total_calls": 0,
                "evaluated_calls": 0,
                "avg_quality": None,
                "avg_quality_formatted": "—",
                "low_quality_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "error_rate_formatted": "0%",
                "hallucination_count": 0,
            },
            "top_offender": None,
            "detail_table": [],
            "chart_data": [],
        }
    
    # Global metrics
    all_scores = []
    total_errors = 0
    total_hallucinations = 0
    
    for call in llm_calls:
        score = _get_quality_score(call)
        if score is not None:
            all_scores.append(score)
        
        if not call.get("success", True):
            total_errors += 1
        
        if _get_hallucination_flag(call):
            total_hallucinations += 1
    
    avg_quality = sum(all_scores) / len(all_scores) if all_scores else None
    error_rate = (total_errors / len(llm_calls) * 100) if llm_calls else 0
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_operation[(agent, op)].append(call)
    
    detail_table = []
    low_quality_ops = []
    
    for (agent, op), op_calls in by_operation.items():
        # Calculate metrics
        scores = [_get_quality_score(c) for c in op_calls]
        scores = [s for s in scores if s is not None]
        
        avg_score = sum(scores) / len(scores) if scores else None
        min_score = min(scores) if scores else None
        max_score = max(scores) if scores else None
        
        error_count = sum(1 for c in op_calls if not c.get("success", True))
        halluc_count = sum(1 for c in op_calls if _get_hallucination_flag(c))
        
        # Determine status
        status, status_emoji, status_label = _get_quality_status(avg_score)
        
        # Track low quality operations
        if avg_score is not None and avg_score < THRESHOLDS["quality_low"]:
            low_quality_ops.append((agent, op, avg_score, op_calls))
        
        detail_table.append({
            "agent_name": agent,
            "operation_name": op,
            "status": status,
            "status_emoji": status_emoji,
            "status_label": status_label,
            "avg_score": avg_score,
            "avg_score_formatted": f"{avg_score:.1f}/10" if avg_score else "—",
            "min_score": min_score,
            "min_score_formatted": f"{min_score:.1f}" if min_score else "—",
            "max_score": max_score,
            "max_score_formatted": f"{max_score:.1f}" if max_score else "—",
            "error_count": error_count,
            "hallucination_count": halluc_count,
            "call_count": len(op_calls),
            "evaluated_count": len(scores),
        })
    
    # Sort by avg_score (worst first), then by error count
    detail_table.sort(key=lambda x: (
        x["avg_score"] if x["avg_score"] is not None else 999,
        -x["error_count"]
    ))
    
    # Top offender (worst quality operation)
    top_offender = None
    if low_quality_ops:
        low_quality_ops.sort(key=lambda x: x[2])  # Sort by avg_score ascending
        agent, op, score, op_calls = low_quality_ops[0]
        
        error_count = sum(1 for c in op_calls if not c.get("success", True))
        halluc_count = sum(1 for c in op_calls if _get_hallucination_flag(c))
        
        issues = []
        if error_count > 0:
            issues.append(f"{error_count} errors")
        if halluc_count > 0:
            issues.append(f"{halluc_count} hallucinations")
        
        top_offender = {
            "agent": agent,
            "operation": op,
            "avg_score": score,
            "avg_score_formatted": f"{score:.1f}/10",
            "call_count": len(op_calls),
            "error_count": error_count,
            "hallucination_count": halluc_count,
            "diagnosis": f"Avg quality {score:.1f}/10" + (f" with {', '.join(issues)}" if issues else ""),
        }
    
    # Chart data - quality distribution
    chart_data = _build_quality_histogram(all_scores)
    
    # Calculate health score
    if avg_quality is None:
        health_score = 100.0
        status = "ok"
    elif avg_quality < THRESHOLDS["quality_critical"]:
        health_score = max(20, avg_quality * 10)
        status = "error"
    elif avg_quality < THRESHOLDS["quality_low"]:
        health_score = max(40, 50 + (avg_quality - 5) * 10)
        status = "warning"
    elif avg_quality < THRESHOLDS["quality_good"]:
        health_score = max(70, 70 + (avg_quality - 7) * 15)
        status = "ok"
    else:
        health_score = min(100, 85 + (avg_quality - 8) * 7.5)
        status = "ok"
    
    # Adjust for error rate
    if error_rate >= THRESHOLDS["error_rate_critical"]:
        health_score = max(30, health_score - 30)
        status = "error"
    elif error_rate >= THRESHOLDS["error_rate_warning"]:
        health_score = max(50, health_score - 15)
        if status == "ok":
            status = "warning"
    
    error_status, error_emoji = _get_error_rate_status(error_rate)
    
    return {
        "status": status,
        "health_score": round(health_score, 1),
        "summary": {
            "total_calls": len(llm_calls),
            "evaluated_calls": len(all_scores),
            "avg_quality": avg_quality,
            "avg_quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
            "low_quality_count": len(low_quality_ops),
            "error_count": total_errors,
            "error_rate": round(error_rate, 1),
            "error_rate_formatted": f"{error_rate:.1f}%",
            "error_rate_status": error_status,
            "error_rate_emoji": error_emoji,
            "hallucination_count": total_hallucinations,
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
    - Summary stats (avg/min/max score, errors, hallucinations)
    - All calls with quality info
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
    scores = []
    total_errors = 0
    total_hallucinations = 0
    
    for call in op_calls:
        score = _get_quality_score(call)
        if score is not None:
            scores.append(score)
        
        if not call.get("success", True):
            total_errors += 1
        
        if _get_hallucination_flag(call):
            total_hallucinations += 1
    
    avg_score = sum(scores) / len(scores) if scores else None
    min_score = min(scores) if scores else None
    max_score = max(scores) if scores else None
    
    status, status_emoji, status_label = _get_quality_status(avg_score)
    
    # Build calls list (sorted by score, worst first)
    calls_list = []
    sorted_calls = sorted(
        op_calls,
        key=lambda x: (_get_quality_score(x) if _get_quality_score(x) is not None else 999)
    )
    
    for i, call in enumerate(sorted_calls):
        score = _get_quality_score(call)
        is_error = not call.get("success", True)
        is_hallucination = _get_hallucination_flag(call)
        error_category = _get_error_category(call)
        
        # Build issues list
        issues = []
        if is_error:
            issues.append({"type": "error", "emoji": "❌", "label": "Error"})
        if is_hallucination:
            issues.append({"type": "hallucination", "emoji": "⚠️", "label": "Hallucination"})
        if error_category:
            issues.append({"type": "category", "emoji": "📋", "label": error_category})
        
        score_status, score_emoji, score_label = _get_quality_status(score)
        
        calls_list.append({
            "call_id": call.get("id"),
            "index": i + 1,
            "timestamp": call.get("timestamp"),
            "timestamp_formatted": _format_timestamp(call.get("timestamp")),
            "score": score,
            "score_formatted": f"{score:.1f}/10" if score is not None else "—",
            "score_status": score_status,
            "score_emoji": score_emoji,
            "is_error": is_error,
            "is_hallucination": is_hallucination,
            "issues": issues,
            "issues_display": " ".join([i["emoji"] for i in issues]) if issues else "",
            "latency_ms": call.get("latency_ms") or 0,
            "latency_formatted": f"{(call.get('latency_ms') or 0) / 1000:.1f}s",
            "total_cost": call.get("total_cost") or 0,
            "cost_formatted": f"${(call.get('total_cost') or 0):.4f}",
            "model_name": call.get("model_name") or "—",
            "prompt_preview": (call.get("prompt") or "")[:50] + "..." if call.get("prompt") else "—",
        })
    
    # Quality distribution histogram
    quality_distribution = _build_quality_histogram(scores)
    
    return {
        "agent_name": agent,
        "operation_name": operation,
        
        # Status badge
        "status": status,
        "status_emoji": status_emoji,
        "status_label": status_label,
        
        # Quality stats
        "avg_score": avg_score,
        "avg_score_formatted": f"{avg_score:.1f}/10" if avg_score else "—",
        "min_score": min_score,
        "min_score_formatted": f"{min_score:.1f}" if min_score else "—",
        "max_score": max_score,
        "max_score_formatted": f"{max_score:.1f}" if max_score else "—",
        
        # Counts
        "call_count": len(op_calls),
        "evaluated_count": len(scores),
        "error_count": total_errors,
        "hallucination_count": total_hallucinations,
        
        # Calls table
        "calls": calls_list,
        
        # Histogram
        "quality_distribution": quality_distribution,
    }