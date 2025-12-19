"""
LLM Call Detail Service (Layer 3)
Location: api/services/llm_call_service.py

Business logic for single call detail with diagnosis and recommendations.
Shared by all stories for drill-down functionality.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from observatory.storage import ObservatoryStorage


# =============================================================================
# THRESHOLDS FOR DIAGNOSIS
# =============================================================================

THRESHOLDS = {
    "latency_warning_ms": 5000,
    "latency_critical_ms": 10000,
    "completion_tokens_high": 1000,
    "completion_tokens_very_high": 2000,
    "prompt_tokens_high": 4000,
    "prompt_tokens_very_high": 8000,
    "system_prompt_ratio_high": 0.5,  # >50% of prompt is system prompt
    "quality_score_low": 5.0,
    "quality_score_very_low": 3.0,
    "cost_high": 0.05,
    "cost_very_high": 0.10,
}


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def get_detail(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific LLM call.
    
    Includes full prompt, response, tokens, cost, quality evaluation,
    and comprehensive diagnosis with recommendations.
    
    Args:
        call_id: Unique identifier for the LLM call
        
    Returns:
        Complete call details with diagnosis and recommendations,
        or None if call not found
    """
    # Fetch the call from storage
    call = ObservatoryStorage.get_llm_call_by_id(call_id)
    
    if not call:
        return None
    
    # Get comparison metrics (operation averages)
    comparison = _get_comparison_metrics(call)
    
    # Generate diagnosis
    diagnosis = _generate_diagnosis(call, comparison)
    
    # Build response
    return {
        # Identity
        "call_id": call.id,
        "timestamp": call.timestamp.isoformat() if call.timestamp else None,
        "agent_name": call.agent_name,
        "operation": call.operation,
        "session_id": call.session_id,
        
        # Model Config
        "model_name": call.model_name,
        "provider": call.provider.value if call.provider else None,
        "temperature": call.temperature,
        "max_tokens": call.max_tokens,
        "top_p": call.top_p,
        
        # Metrics
        "latency_ms": call.latency_ms,
        "prompt_tokens": call.prompt_tokens,
        "completion_tokens": call.completion_tokens,
        "total_tokens": call.total_tokens,
        "prompt_cost": call.prompt_cost,
        "completion_cost": call.completion_cost,
        "total_cost": call.total_cost,
        
        # Token Breakdown
        "system_prompt_tokens": call.system_prompt_tokens,
        "user_message_tokens": call.user_message_tokens,
        "chat_history_tokens": call.chat_history_tokens,
        "conversation_context_tokens": call.conversation_context_tokens,
        "tool_definitions_tokens": call.tool_definitions_tokens,
        
        # Content
        "prompt": call.prompt,
        "system_prompt": _extract_system_prompt(call),
        "user_message": _extract_user_message(call),
        "response_text": call.response_text,
        
        # Quality
        "success": call.success,
        "error": call.error,
        "error_type": call.error_type,
        "error_code": call.error_code,
        "judge_score": _get_judge_score(call),
        "hallucination_flag": _get_hallucination_flag(call),
        "quality_reasoning": _get_quality_reasoning(call),
        
        # Cache
        "cache_hit": _get_cache_hit(call),
        "cache_key": _get_cache_key(call),
        
        # Context
        "conversation_id": call.conversation_id,
        "turn_number": call.turn_number,
        "user_id": call.user_id,
        
        # Streaming
        "time_to_first_token_ms": call.time_to_first_token_ms,
        
        # Retry info
        "retry_count": call.retry_count,
        
        # Comparison with operation averages
        "comparison": comparison,
        
        # Diagnosis and recommendations
        "diagnosis": diagnosis,
    }


# =============================================================================
# HELPER FUNCTIONS - EXTRACTION
# =============================================================================

def _extract_system_prompt(call) -> Optional[str]:
    """Extract system prompt from prompt_breakdown or prompt field."""
    if call.prompt_breakdown and hasattr(call.prompt_breakdown, 'system_prompt'):
        return call.prompt_breakdown.system_prompt
    return None


def _extract_user_message(call) -> Optional[str]:
    """Extract user message from prompt_breakdown or prompt field."""
    if call.prompt_breakdown and hasattr(call.prompt_breakdown, 'user_message'):
        return call.prompt_breakdown.user_message
    return None


def _get_judge_score(call) -> Optional[float]:
    """Get quality judge score."""
    if call.quality_evaluation and hasattr(call.quality_evaluation, 'judge_score'):
        return call.quality_evaluation.judge_score
    return None


def _get_hallucination_flag(call) -> bool:
    """Get hallucination flag."""
    if call.quality_evaluation and hasattr(call.quality_evaluation, 'hallucination_flag'):
        return call.quality_evaluation.hallucination_flag
    return False


def _get_quality_reasoning(call) -> Optional[str]:
    """Get quality evaluation reasoning."""
    if call.quality_evaluation and hasattr(call.quality_evaluation, 'reasoning'):
        return call.quality_evaluation.reasoning
    return None


def _get_cache_hit(call) -> bool:
    """Get cache hit status."""
    if call.cache_metadata and hasattr(call.cache_metadata, 'cache_hit'):
        return call.cache_metadata.cache_hit
    return False


def _get_cache_key(call) -> Optional[str]:
    """Get cache key."""
    if call.cache_metadata and hasattr(call.cache_metadata, 'cache_key'):
        return call.cache_metadata.cache_key
    return None


# =============================================================================
# COMPARISON METRICS
# =============================================================================

def _get_comparison_metrics(call) -> Dict[str, Any]:
    """
    Get comparison metrics for this call vs operation averages.
    
    Helps developer understand if this call is an outlier or typical.
    """
    if not call.agent_name or not call.operation:
        return {
            "available": False,
            "reason": "No agent/operation context"
        }
    
    # Get recent calls for same operation (last 7 days)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        operation_calls = ObservatoryStorage.get_llm_calls(
            agent_name=call.agent_name,
            operation=call.operation,
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )
    except Exception:
        return {
            "available": False,
            "reason": "Could not fetch comparison data"
        }
    
    if len(operation_calls) < 2:
        return {
            "available": False,
            "reason": "Not enough calls for comparison"
        }
    
    # Calculate averages
    latencies = [c.latency_ms for c in operation_calls if c.latency_ms]
    costs = [c.total_cost for c in operation_calls if c.total_cost]
    tokens = [c.total_tokens for c in operation_calls if c.total_tokens]
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    avg_cost = sum(costs) / len(costs) if costs else 0
    avg_tokens = sum(tokens) / len(tokens) if tokens else 0
    
    # Calculate ratios
    latency_ratio = call.latency_ms / avg_latency if avg_latency > 0 else 1.0
    cost_ratio = call.total_cost / avg_cost if avg_cost > 0 else 1.0
    
    return {
        "available": True,
        "operation_call_count": len(operation_calls),
        "operation_avg_latency_ms": round(avg_latency, 1),
        "operation_avg_cost": round(avg_cost, 6),
        "operation_avg_tokens": round(avg_tokens, 0),
        "latency_ratio": round(latency_ratio, 2),
        "cost_ratio": round(cost_ratio, 2),
        "is_latency_outlier": latency_ratio > 2.0,
        "is_cost_outlier": cost_ratio > 2.0,
    }


# =============================================================================
# DIAGNOSIS ENGINE
# =============================================================================

def _generate_diagnosis(call, comparison: Dict) -> Dict[str, Any]:
    """
    Generate comprehensive diagnosis with issues and recommendations.
    
    Analyzes the call for common problems and provides actionable fixes.
    """
    issues = []
    recommendations = []
    
    # ----- LATENCY ISSUES -----
    if call.latency_ms:
        if call.latency_ms > THRESHOLDS["latency_critical_ms"]:
            issues.append({
                "type": "high_latency",
                "severity": "critical",
                "message": f"Critical latency ({call.latency_ms / 1000:.1f}s)",
                "detail": "Response time exceeds 10 seconds"
            })
        elif call.latency_ms > THRESHOLDS["latency_warning_ms"]:
            issues.append({
                "type": "high_latency",
                "severity": "warning",
                "message": f"High latency ({call.latency_ms / 1000:.1f}s)",
                "detail": "Response time exceeds 5 seconds"
            })
    
    # ----- COMPLETION TOKEN ISSUES -----
    if call.completion_tokens:
        if call.completion_tokens > THRESHOLDS["completion_tokens_very_high"]:
            issues.append({
                "type": "high_completion_tokens",
                "severity": "warning",
                "message": f"Very high completion tokens ({call.completion_tokens:,})",
                "detail": "Model generating extremely verbose response"
            })
            recommendations.append({
                "action": "Set max_tokens limit",
                "impact": "high",
                "code_hint": "max_tokens=500",
                "estimated_improvement": "50-70% latency reduction"
            })
            recommendations.append({
                "action": "Use structured JSON output",
                "impact": "medium",
                "code_hint": "response_format={'type': 'json_object'}",
                "estimated_improvement": "30-50% token reduction"
            })
        elif call.completion_tokens > THRESHOLDS["completion_tokens_high"]:
            issues.append({
                "type": "high_completion_tokens",
                "severity": "info",
                "message": f"High completion tokens ({call.completion_tokens:,})",
                "detail": "Model generating verbose response"
            })
    
    # ----- MAX_TOKENS NOT SET -----
    if call.max_tokens is None and call.completion_tokens and call.completion_tokens > 500:
        issues.append({
            "type": "no_max_tokens",
            "severity": "warning",
            "message": "No max_tokens limit set",
            "detail": "Output length is unbounded, risking runaway generation"
        })
        if not any(r["action"] == "Set max_tokens limit" for r in recommendations):
            recommendations.append({
                "action": "Set max_tokens limit",
                "impact": "high",
                "code_hint": f"max_tokens={min(call.completion_tokens + 100, 1000)}",
                "estimated_improvement": "Prevents runaway generation"
            })
    
    # ----- PROMPT TOKEN ISSUES -----
    if call.prompt_tokens:
        if call.prompt_tokens > THRESHOLDS["prompt_tokens_very_high"]:
            issues.append({
                "type": "high_prompt_tokens",
                "severity": "warning",
                "message": f"Very large prompt ({call.prompt_tokens:,} tokens)",
                "detail": "Large context increases cost and latency"
            })
            recommendations.append({
                "action": "Enable prompt caching",
                "impact": "high",
                "code_hint": "cache={'type': 'ephemeral'}",
                "estimated_improvement": "50% cost reduction on repeated calls"
            })
        elif call.prompt_tokens > THRESHOLDS["prompt_tokens_high"]:
            issues.append({
                "type": "high_prompt_tokens",
                "severity": "info",
                "message": f"Large prompt ({call.prompt_tokens:,} tokens)",
                "detail": "Consider reducing context size"
            })
    
    # ----- SYSTEM PROMPT RATIO -----
    if call.system_prompt_tokens and call.prompt_tokens:
        ratio = call.system_prompt_tokens / call.prompt_tokens
        if ratio > THRESHOLDS["system_prompt_ratio_high"]:
            issues.append({
                "type": "bloated_system_prompt",
                "severity": "info",
                "message": f"System prompt is {ratio:.0%} of total input",
                "detail": "Consider compressing or caching system prompt"
            })
            recommendations.append({
                "action": "Compress system prompt",
                "impact": "medium",
                "code_hint": "Move examples to few-shot messages",
                "estimated_improvement": "20-40% token reduction"
            })
    
    # ----- QUALITY ISSUES -----
    judge_score = _get_judge_score(call)
    if judge_score is not None:
        if judge_score < THRESHOLDS["quality_score_very_low"]:
            issues.append({
                "type": "low_quality",
                "severity": "critical",
                "message": f"Very low quality score ({judge_score:.1f}/10)",
                "detail": "Response quality is poor"
            })
            recommendations.append({
                "action": "Review and improve prompt",
                "impact": "high",
                "code_hint": "Add clear instructions and examples",
                "estimated_improvement": "Significant quality improvement"
            })
        elif judge_score < THRESHOLDS["quality_score_low"]:
            issues.append({
                "type": "low_quality",
                "severity": "warning",
                "message": f"Below average quality ({judge_score:.1f}/10)",
                "detail": "Response quality could be improved"
            })
    
    # ----- HALLUCINATION -----
    if _get_hallucination_flag(call):
        issues.append({
            "type": "hallucination",
            "severity": "critical",
            "message": "Hallucination detected",
            "detail": "Model fabricated information not in source"
        })
        recommendations.append({
            "action": "Add grounding instructions",
            "impact": "high",
            "code_hint": "Add: 'Only use information from the provided text'",
            "estimated_improvement": "Reduces hallucinations significantly"
        })
        recommendations.append({
            "action": "Lower temperature",
            "impact": "medium",
            "code_hint": "temperature=0.3",
            "estimated_improvement": "More deterministic, factual responses"
        })
    
    # ----- CACHE MISS -----
    if not _get_cache_hit(call) and call.prompt_tokens and call.prompt_tokens > 2000:
        issues.append({
            "type": "cache_miss",
            "severity": "info",
            "message": "Cache miss on large prompt",
            "detail": "This prompt could benefit from caching"
        })
        if not any(r["action"] == "Enable prompt caching" for r in recommendations):
            recommendations.append({
                "action": "Enable semantic caching",
                "impact": "medium",
                "code_hint": "Enable caching for repeated prompts",
                "estimated_improvement": "Reduced latency and cost on similar queries"
            })
    
    # ----- ERROR -----
    if not call.success and call.error:
        issues.append({
            "type": "error",
            "severity": "critical",
            "message": f"Call failed: {call.error_type or 'Unknown error'}",
            "detail": call.error[:200] if call.error else "No error details"
        })
        if call.error_type == "RATE_LIMIT":
            recommendations.append({
                "action": "Implement rate limiting",
                "impact": "high",
                "code_hint": "Add exponential backoff retry logic",
                "estimated_improvement": "Prevents rate limit errors"
            })
        elif call.error_type == "TIMEOUT":
            recommendations.append({
                "action": "Reduce prompt size or add timeout handling",
                "impact": "high",
                "code_hint": "Set reasonable timeout, reduce context",
                "estimated_improvement": "Prevents timeout failures"
            })
    
    # ----- OUTLIER DETECTION -----
    if comparison.get("available") and comparison.get("is_latency_outlier"):
        issues.append({
            "type": "latency_outlier",
            "severity": "info",
            "message": f"This call is {comparison['latency_ratio']:.1f}x slower than average",
            "detail": f"Operation average: {comparison['operation_avg_latency_ms'] / 1000:.1f}s"
        })
    
    # ----- EXPENSIVE MODEL FOR SIMPLE TASK -----
    if call.model_name and "gpt-4" in call.model_name.lower():
        if call.completion_tokens and call.completion_tokens < 200:
            # Short response from expensive model
            issues.append({
                "type": "expensive_model",
                "severity": "info",
                "message": "Using GPT-4 for short response",
                "detail": "Consider cheaper model for simple tasks"
            })
            recommendations.append({
                "action": "Route to cheaper model",
                "impact": "high",
                "code_hint": "model='gpt-4o-mini' for simple tasks",
                "estimated_improvement": "90% cost reduction"
            })
    
    # Determine overall status
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    
    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    elif len(issues) > 0:
        status = "info"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "issue_count": len(issues),
        "issues": issues,
        "recommendations": recommendations,
    }