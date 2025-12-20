"""
LLM Call Detail Service (Layer 2 + Layer 3)
Location: api/services/llm_call_service.py

Business logic for call listings and single call detail with diagnosis.
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
# MAIN FUNCTION - SINGLE CALL DETAIL (Layer 3)
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
        "session_id": getattr(call, 'session_id', None),
        
        # Model Config
        "model_name": call.model_name,
        "provider": call.provider.value if getattr(call, 'provider', None) else None,
        "temperature": getattr(call, 'temperature', None),
        "max_tokens": getattr(call, 'max_tokens', None),
        "top_p": getattr(call, 'top_p', None),
        
        # Metrics
        "latency_ms": call.latency_ms,
        "prompt_tokens": call.prompt_tokens,
        "completion_tokens": call.completion_tokens,
        "total_tokens": call.total_tokens,
        "prompt_cost": getattr(call, 'prompt_cost', None),
        "completion_cost": getattr(call, 'completion_cost', None),
        "total_cost": call.total_cost,
        
        # Token Breakdown
        "system_prompt_tokens": getattr(call, 'system_prompt_tokens', None),
        "user_message_tokens": getattr(call, 'user_message_tokens', None),
        "chat_history_tokens": getattr(call, 'chat_history_tokens', None),
        "conversation_context_tokens": getattr(call, 'conversation_context_tokens', None),
        "tool_definitions_tokens": getattr(call, 'tool_definitions_tokens', None),
        
        # Content
        "prompt": getattr(call, 'prompt', None),
        "system_prompt": getattr(call, 'system_prompt', None) or _extract_system_prompt(call),
        "user_message": getattr(call, 'user_message', None) or _extract_user_message(call),
        "response_text": getattr(call, 'response_text', None),
        
        # Quality
        "success": call.success,
        "error": getattr(call, 'error', None),
        "error_type": getattr(call, 'error_type', None),
        "error_code": getattr(call, 'error_code', None),
        "judge_score": getattr(call, 'judge_score', None) or _get_judge_score(call),
        "hallucination_flag": getattr(call, 'hallucination_flag', None) if getattr(call, 'hallucination_flag', None) is not None else _get_hallucination_flag(call),
        "quality_reasoning": _get_quality_reasoning(call),
        "confidence_score": getattr(call, 'confidence_score', None),
        
        # Cache
        "cache_hit": getattr(call, 'cache_hit', None) if getattr(call, 'cache_hit', None) is not None else _get_cache_hit(call),
        "cache_key": getattr(call, 'cache_key', None) or _get_cache_key(call),
        "cached_prompt_tokens": getattr(call, 'cached_prompt_tokens', None),
        
        # Context
        "conversation_id": getattr(call, 'conversation_id', None),
        "turn_number": getattr(call, 'turn_number', None),
        "user_id": getattr(call, 'user_id', None),
        
        # Streaming
        "time_to_first_token_ms": getattr(call, 'time_to_first_token_ms', None),
        
        # Retry info
        "retry_count": getattr(call, 'retry_count', None),
        
        # Routing
        "complexity_score": getattr(call, 'complexity_score', None),
        "chosen_model": getattr(call, 'chosen_model', None),
        
        # Comparison with operation averages
        "comparison": comparison,
        
        # Diagnosis and recommendations
        "diagnosis": diagnosis,
    }


# =============================================================================
# LIST CALLS (Layer 2) - EXPANDED
# =============================================================================

def get_calls(
    days: int = 7,
    operation: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Get list of LLM calls with optional filters.
    
    Used by Layer 2 tables in all stories. Returns comprehensive
    data for filtering, sorting, and display.
    
    Args:
        days: Number of days to look back
        operation: Filter by operation name
        agent: Filter by agent name  
        limit: Maximum number of calls to return
        
    Returns:
        List of call summaries with all fields needed for Layer 2
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    try:
        calls = ObservatoryStorage.get_llm_calls(
            agent_name=agent,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    except Exception as e:
        print(f"Error fetching calls: {e}")
        return []
    
    # Convert to comprehensive summary format for Layer 2
    result = []
    for c in calls:
        # Safely extract values with fallbacks
        cache_hit = False
        if hasattr(c, 'cache_hit') and c.cache_hit is not None:
            cache_hit = c.cache_hit
        elif hasattr(c, 'cache_metadata') and c.cache_metadata:
            cache_hit = getattr(c.cache_metadata, 'cache_hit', False)
        
        judge_score = None
        if hasattr(c, 'judge_score') and c.judge_score is not None:
            judge_score = c.judge_score
        elif hasattr(c, 'quality_evaluation') and c.quality_evaluation:
            judge_score = getattr(c.quality_evaluation, 'judge_score', None)
        
        hallucination_flag = False
        if hasattr(c, 'hallucination_flag') and c.hallucination_flag is not None:
            hallucination_flag = c.hallucination_flag
        elif hasattr(c, 'quality_evaluation') and c.quality_evaluation:
            hallucination_flag = getattr(c.quality_evaluation, 'hallucination_flag', False)
        
        result.append({
            # Identity
            "call_id": c.id,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "agent_name": c.agent_name,
            "operation": c.operation,
            "session_id": getattr(c, 'session_id', None),
            
            # Model
            "model_name": c.model_name,
            "provider": c.provider.value if hasattr(c, 'provider') and c.provider else None,
            "temperature": getattr(c, 'temperature', None),
            
            # Performance
            "latency_ms": c.latency_ms,
            "time_to_first_token_ms": getattr(c, 'time_to_first_token_ms', None),
            
            # Tokens - Basic
            "prompt_tokens": c.prompt_tokens,
            "completion_tokens": c.completion_tokens,
            "total_tokens": c.total_tokens,
            
            # Tokens - Breakdown (for Prompt Composition story)
            "system_prompt_tokens": getattr(c, 'system_prompt_tokens', None),
            "user_message_tokens": getattr(c, 'user_message_tokens', None),
            "chat_history_tokens": getattr(c, 'chat_history_tokens', None),
            "conversation_context_tokens": getattr(c, 'conversation_context_tokens', None),
            "tool_definitions_tokens": getattr(c, 'tool_definitions_tokens', None),
            
            # Cost
            "prompt_cost": getattr(c, 'prompt_cost', None),
            "completion_cost": getattr(c, 'completion_cost', None),
            "total_cost": c.total_cost,
            
            # Status
            "status": "success" if c.success else "error",
            "success": c.success,
            "error": getattr(c, 'error', None),
            "error_type": getattr(c, 'error_type', None),
            "retry_count": getattr(c, 'retry_count', 0),
            
            # Cache (for Cache story)
            "cached": cache_hit,
            "cache_hit": cache_hit,
            "cache_key": getattr(c, 'cache_key', None),
            "cached_prompt_tokens": getattr(c, 'cached_prompt_tokens', None),
            
            # Quality (for Quality story)
            "judge_score": judge_score,
            "hallucination_flag": hallucination_flag,
            "confidence_score": getattr(c, 'confidence_score', None),
            
            # Routing (for Routing story)
            "complexity_score": getattr(c, 'complexity_score', None),
            "chosen_model": getattr(c, 'chosen_model', None),
            
            # Derived metrics for filtering
            "token_ratio": round(c.prompt_tokens / c.completion_tokens, 1) if c.completion_tokens and c.completion_tokens > 0 else None,
        })
    
    return result


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
    if hasattr(call, 'cache_hit') and call.cache_hit is not None:
        return call.cache_hit
    if call.cache_metadata and hasattr(call.cache_metadata, 'cache_hit'):
        return call.cache_metadata.cache_hit
    return False


def _get_cache_key(call) -> Optional[str]:
    """Get cache key."""
    if hasattr(call, 'cache_key') and call.cache_key:
        return call.cache_key
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
    judge_score = getattr(call, 'judge_score', None) or _get_judge_score(call)
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
    hallucination = call.hallucination_flag if hasattr(call, 'hallucination_flag') and call.hallucination_flag is not None else _get_hallucination_flag(call)
    if hallucination:
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
    cache_hit = call.cache_hit if hasattr(call, 'cache_hit') and call.cache_hit is not None else _get_cache_hit(call)
    if not cache_hit and call.prompt_tokens and call.prompt_tokens > 2000:
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