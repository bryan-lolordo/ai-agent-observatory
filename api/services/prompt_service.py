"""
Prompt Service - Story 6 Business Logic
Location: api/services/prompt_service.py

Layer 1: get_summary() - Prompt composition overview
Layer 2: get_operation_detail() - Operation prompt structure analysis
Layer 3: Shared CallDetail (uses llm_call_service.py)
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# =============================================================================
# CONSTANTS & THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "system_pct_high": 50.0,     # System > 50% = high
    "history_pct_high": 40.0,    # History > 40% = concerning
    "variability_low": 0.05,     # <5% variation = static
    "variability_high": 0.20,    # >20% variation = dynamic
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_token_breakdown(call: Dict) -> Dict:
    """Extract token breakdown from call data."""
    breakdown = {
        "system_prompt_tokens": call.get("system_prompt_tokens") or 0,
        "user_message_tokens": call.get("user_message_tokens") or 0,
        "chat_history_tokens": call.get("chat_history_tokens") or 0,
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
    
    return breakdown


def _calculate_variability(values: List[float]) -> float:
    """Calculate coefficient of variation (std/mean)."""
    if not values or len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = variance ** 0.5
    return std / mean


def _get_cache_status(
    has_history: bool,
    system_variability: float,
    system_tokens: int
) -> Tuple[str, str, str]:
    """
    Determine cache readiness status.
    
    Returns (status, emoji, label)
    """
    if system_tokens == 0:
        return ("none", "➖", "No System Prompt")
    
    if system_variability > THRESHOLDS["variability_high"]:
        return ("not_ready", "❌", "Not Cache Ready")
    
    if has_history:
        if system_variability <= THRESHOLDS["variability_low"]:
            return ("partial", "⚠️", "Partial (has history)")
        return ("not_ready", "❌", "Not Cache Ready")
    
    if system_variability <= THRESHOLDS["variability_low"]:
        return ("ready", "✅", "Cache Ready")
    
    return ("partial", "⚠️", "Partial")


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


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> Dict:
    """
    Layer 1: Prompt composition summary.
    
    Returns overview of prompt structure across operations.
    """
    # Filter to only LLM calls with tokens
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]
    
    if not llm_calls:
        return {
            "status": "ok",
            "health_score": 100.0,
            "summary": {
                "total_calls": 0,
                "avg_system_tokens": 0,
                "avg_user_tokens": 0,
                "avg_history_tokens": 0,
                "system_pct": 0,
                "user_pct": 0,
                "history_pct": 0,
                "cache_ready_count": 0,
                "total_operations": 0,
            },
            "composition_chart": [],
            "detail_table": [],
        }
    
    # Global token aggregates
    total_system = 0
    total_user = 0
    total_history = 0
    
    for call in llm_calls:
        breakdown = _get_token_breakdown(call)
        total_system += breakdown["system_prompt_tokens"]
        total_user += breakdown["user_message_tokens"]
        total_history += breakdown["chat_history_tokens"]
    
    n = len(llm_calls)
    avg_system = total_system / n
    avg_user = total_user / n
    avg_history = total_history / n
    total_avg = avg_system + avg_user + avg_history
    
    if total_avg > 0:
        system_pct = (avg_system / total_avg) * 100
        user_pct = (avg_user / total_avg) * 100
        history_pct = (avg_history / total_avg) * 100
    else:
        system_pct = user_pct = history_pct = 0
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_operation[(agent, op)].append(call)
    
    detail_table = []
    cache_ready_count = 0
    
    for (agent, op), op_calls in by_operation.items():
        # Calculate averages
        system_tokens_list = []
        user_tokens_list = []
        history_tokens_list = []
        
        for call in op_calls:
            breakdown = _get_token_breakdown(call)
            system_tokens_list.append(breakdown["system_prompt_tokens"])
            user_tokens_list.append(breakdown["user_message_tokens"])
            history_tokens_list.append(breakdown["chat_history_tokens"])
        
        avg_sys = sum(system_tokens_list) / len(system_tokens_list) if system_tokens_list else 0
        avg_usr = sum(user_tokens_list) / len(user_tokens_list) if user_tokens_list else 0
        avg_hist = sum(history_tokens_list) / len(history_tokens_list) if history_tokens_list else 0
        
        # Calculate system prompt variability
        system_variability = _calculate_variability(system_tokens_list)
        has_history = avg_hist > 0
        
        # Determine cache status
        cache_status, cache_emoji, cache_label = _get_cache_status(
            has_history, system_variability, int(avg_sys)
        )
        
        if cache_status == "ready":
            cache_ready_count += 1
        
        detail_table.append({
            "agent_name": agent,
            "operation_name": op,
            "avg_system_tokens": int(avg_sys),
            "avg_system_formatted": f"{int(avg_sys):,}",
            "avg_user_tokens": int(avg_usr),
            "avg_user_formatted": f"{int(avg_usr):,}",
            "avg_history_tokens": int(avg_hist),
            "avg_history_formatted": f"{int(avg_hist):,}",
            "cache_status": cache_status,
            "cache_emoji": cache_emoji,
            "cache_label": cache_label,
            "system_variability": round(system_variability * 100, 1),
            "call_count": len(op_calls),
        })
    
    # Sort by system tokens (highest first)
    detail_table.sort(key=lambda x: -x["avg_system_tokens"])
    
    # Composition chart data
    composition_chart = [
        {"component": "System Prompt", "tokens": int(avg_system), "percentage": round(system_pct, 1), "color": "#8b5cf6"},
        {"component": "User Message", "tokens": int(avg_user), "percentage": round(user_pct, 1), "color": "#22c55e"},
        {"component": "Chat History", "tokens": int(avg_history), "percentage": round(history_pct, 1), "color": "#f97316"},
    ]
    
    # Calculate health score
    cache_ready_pct = (cache_ready_count / len(by_operation) * 100) if by_operation else 0
    health_score = min(100, 50 + cache_ready_pct * 0.5)
    
    if history_pct > 50:
        health_score = max(40, health_score - 20)
    
    status = "ok" if health_score >= 70 else "warning" if health_score >= 50 else "error"
    
    return {
        "status": status,
        "health_score": round(health_score, 1),
        "summary": {
            "total_calls": len(llm_calls),
            "avg_system_tokens": int(avg_system),
            "avg_system_formatted": f"{int(avg_system):,}",
            "avg_user_tokens": int(avg_user),
            "avg_user_formatted": f"{int(avg_user):,}",
            "avg_history_tokens": int(avg_history),
            "avg_history_formatted": f"{int(avg_history):,}",
            "system_pct": round(system_pct, 1),
            "user_pct": round(user_pct, 1),
            "history_pct": round(history_pct, 1),
            "cache_ready_count": cache_ready_count,
            "total_operations": len(by_operation),
        },
        "composition_chart": composition_chart,
        "detail_table": detail_table,
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
    Layer 2: Operation prompt structure analysis.
    
    Returns detailed breakdown of prompt composition for an operation.
    """
    # Filter calls for this operation
    op_calls = [
        c for c in calls
        if c.get("agent_name") == agent and c.get("operation") == operation
    ]
    
    if not op_calls:
        return None
    
    # Calculate aggregates
    system_tokens_list = []
    user_tokens_list = []
    history_tokens_list = []
    
    for call in op_calls:
        breakdown = _get_token_breakdown(call)
        system_tokens_list.append(breakdown["system_prompt_tokens"])
        user_tokens_list.append(breakdown["user_message_tokens"])
        history_tokens_list.append(breakdown["chat_history_tokens"])
    
    avg_system = sum(system_tokens_list) / len(system_tokens_list) if system_tokens_list else 0
    avg_user = sum(user_tokens_list) / len(user_tokens_list) if user_tokens_list else 0
    avg_history = sum(history_tokens_list) / len(history_tokens_list) if history_tokens_list else 0
    total_avg = avg_system + avg_user + avg_history
    
    # Percentages
    if total_avg > 0:
        system_pct = (avg_system / total_avg) * 100
        user_pct = (avg_user / total_avg) * 100
        history_pct = (avg_history / total_avg) * 100
    else:
        system_pct = user_pct = history_pct = 0
    
    # Variability
    system_variability = _calculate_variability(system_tokens_list)
    has_history = avg_history > 0
    
    # Cache status
    cache_status, cache_emoji, cache_label = _get_cache_status(
        has_history, system_variability, int(avg_system)
    )
    
    # Composition breakdown
    composition = [
        {
            "component": "System Prompt",
            "tokens": int(avg_system),
            "percentage": round(system_pct, 1),
            "status": "warning" if system_variability > THRESHOLDS["variability_high"] else "ok",
            "status_label": "Dynamic" if system_variability > THRESHOLDS["variability_high"] else "Static",
        },
        {
            "component": "User Message",
            "tokens": int(avg_user),
            "percentage": round(user_pct, 1),
            "status": "ok",
            "status_label": "Expected dynamic",
        },
        {
            "component": "Chat History",
            "tokens": int(avg_history),
            "percentage": round(history_pct, 1),
            "status": "warning" if history_pct > THRESHOLDS["history_pct_high"] else "ok",
            "status_label": "Large" if history_pct > THRESHOLDS["history_pct_high"] else "Normal" if avg_history > 0 else "None",
        },
    ]
    
    # Build calls list
    calls_list = []
    for i, call in enumerate(op_calls[:50]):  # Limit to 50
        breakdown = _get_token_breakdown(call)
        
        # Get prompt preview
        prompt = call.get("prompt") or ""
        system_prompt = ""
        if isinstance(call.get("prompt_breakdown"), dict):
            system_prompt = call["prompt_breakdown"].get("system_prompt") or ""
        
        calls_list.append({
            "call_id": call.get("id"),
            "index": i + 1,
            "timestamp": call.get("timestamp"),
            "timestamp_formatted": _format_timestamp(call.get("timestamp")),
            "system_tokens": breakdown["system_prompt_tokens"],
            "system_formatted": f"{breakdown['system_prompt_tokens']:,}",
            "user_tokens": breakdown["user_message_tokens"],
            "user_formatted": f"{breakdown['user_message_tokens']:,}",
            "history_tokens": breakdown["chat_history_tokens"],
            "history_formatted": f"{breakdown['chat_history_tokens']:,}",
            "system_preview": (system_prompt[:50] + "...") if len(system_prompt) > 50 else system_prompt,
            "user_preview": (prompt[:50] + "...") if len(prompt) > 50 else prompt,
        })
    
    # Determine cache issue reason
    cache_issue_reason = None
    if cache_status == "not_ready":
        if system_variability > THRESHOLDS["variability_high"]:
            cache_issue_reason = "System prompt contains dynamic content that changes between calls"
        elif has_history:
            cache_issue_reason = "Chat history in prompt prevents consistent caching"
    elif cache_status == "partial":
        if has_history:
            cache_issue_reason = "System prompt is static but chat history varies"
    
    return {
        "agent_name": agent,
        "operation_name": operation,
        
        # Cache status
        "cache_status": cache_status,
        "cache_emoji": cache_emoji,
        "cache_label": cache_label,
        "cache_issue_reason": cache_issue_reason,
        
        # Averages
        "avg_system_tokens": int(avg_system),
        "avg_system_formatted": f"{int(avg_system):,}",
        "avg_user_tokens": int(avg_user),
        "avg_user_formatted": f"{int(avg_user):,}",
        "avg_history_tokens": int(avg_history),
        "avg_history_formatted": f"{int(avg_history):,}",
        "total_prompt_tokens": int(total_avg),
        "total_prompt_formatted": f"{int(total_avg):,}",
        
        # Percentages
        "system_pct": round(system_pct, 1),
        "user_pct": round(user_pct, 1),
        "history_pct": round(history_pct, 1),
        
        # Variability
        "system_variability": round(system_variability * 100, 1),
        "system_variability_label": "High" if system_variability > THRESHOLDS["variability_high"] else "Low",
        
        # Composition breakdown
        "composition": composition,
        
        # Calls
        "calls": calls_list,
        "call_count": len(op_calls),
    }