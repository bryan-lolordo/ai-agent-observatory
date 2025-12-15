"""
Call Service - Layer 3 Business Logic
Location: api/services/call_service.py

Handles full call detail with diagnosis and recommendations.
Returns proper LLMCallResponse model.
"""

from typing import Optional, List, Dict, Any
from api.utils.data_fetcher import get_llm_calls
from api.models import LLMCallResponse


def get_call_detail(call_id: str) -> Optional[LLMCallResponse]:
    """
    Get full call detail with diagnosis and recommendations.
    
    Args:
        call_id: Unique identifier for the LLM call
    
    Returns:
        LLMCallResponse model with full details and diagnosis,
        or None if call not found
    """
    # Get all calls and find the specific one
    # TODO: In production, use direct database query by ID for efficiency
    all_calls = get_llm_calls(limit=10000)
    
    call = None
    for c in all_calls:
        if c.get('id') == call_id:
            call = c
            break
    
    if not call:
        return None
    
    # Add diagnosis
    diagnosis = _diagnose_call(call)
    
    # Build and return LLMCallResponse model
    return LLMCallResponse(
        # Basic info
        id=call.get('id'),
        session_id=call.get('session_id'),
        timestamp=call.get('timestamp'),
        agent_name=call.get('agent_name'),
        operation=call.get('operation'),
        model_name=call.get('model_name'),
        provider=call.get('provider'),
        
        # Performance metrics
        latency_ms=call.get('latency_ms', 0),
        prompt_tokens=call.get('prompt_tokens', 0),
        completion_tokens=call.get('completion_tokens', 0),
        total_tokens=call.get('total_tokens', 0),
        
        # Cost metrics
        total_cost=call.get('total_cost', 0),
        prompt_cost=call.get('prompt_cost', 0),
        completion_cost=call.get('completion_cost', 0),
        
        # Content
        prompt=call.get('prompt'),
        response_text=call.get('response_text'),
        
        # Success/error
        success=call.get('success', True),
        error=call.get('error'),
        
        # Metadata (these are already parsed as dicts from data_fetcher)
        routing_decision=call.get('routing_decision'),
        cache_metadata=call.get('cache_metadata'),
        quality_evaluation=call.get('quality_evaluation'),
        prompt_breakdown=call.get('prompt_breakdown'),
        model_config=call.get('model_config'),
        
        # Conversation tracking
        conversation_id=call.get('conversation_id'),
        turn_number=call.get('turn_number'),
        
        # Diagnosis (our added insights)
        diagnosis=diagnosis,
    )


def _diagnose_call(call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnose issues and provide recommendations for a call.
    
    Args:
        call: LLM call dictionary
    
    Returns:
        {
            "problem_type": str,
            "problem_description": str,
            "all_problems": [str, ...],
            "recommendations": [str, ...],
            "severity": str  # "none", "low", "medium", "high", "critical"
        }
    """
    problems = []
    recommendations = []
    
    latency = call.get('latency_ms', 0)
    prompt_tokens = call.get('prompt_tokens', 0)
    completion_tokens = call.get('completion_tokens', 0)
    total_cost = call.get('total_cost', 0)
    
    # Check latency
    if latency > 10000:
        problems.append("critical_latency")
        recommendations.append(
            f"Critical latency ({latency/1000:.1f}s): Consider faster model or reduce output tokens"
        )
    elif latency > 5000:
        problems.append("high_latency")
        recommendations.append(
            f"High latency ({latency/1000:.1f}s): Review completion token count and model choice"
        )
    
    # Check completion tokens
    if completion_tokens > 2000:
        problems.append("high_completion")
        recommendations.append(
            f"High completion tokens ({completion_tokens:,}): Add JSON schema or explicit length limits"
        )
    elif completion_tokens > 1000:
        problems.append("moderate_completion")
        recommendations.append(
            f"Moderate completion tokens ({completion_tokens:,}): Consider output constraints"
        )
    
    # Check prompt tokens
    if prompt_tokens > 4000:
        problems.append("large_prompt")
        recommendations.append(
            f"Large prompt ({prompt_tokens:,} tokens): Consider caching or compression"
        )
    elif prompt_tokens > 2000:
        problems.append("moderate_prompt")
        recommendations.append(
            f"Moderate prompt ({prompt_tokens:,} tokens): Review if all context is necessary"
        )
    
    # Check token ratio (imbalance)
    if completion_tokens > 0:
        ratio = prompt_tokens / completion_tokens
        if ratio > 20:
            problems.append("severe_token_imbalance")
            recommendations.append(
                f"Severe token imbalance ({ratio:.0f}:1): Implement sliding window or summarization"
            )
        elif ratio > 10:
            problems.append("token_imbalance")
            recommendations.append(
                f"Token imbalance ({ratio:.0f}:1): Review if all context is needed"
            )
    
    # Check cost
    if total_cost > 0.10:
        problems.append("high_cost")
        recommendations.append(
            f"High cost (${total_cost:.3f}): Consider cheaper model or output constraints"
        )
    
    # Check quality
    quality_eval = call.get('quality_evaluation')
    if quality_eval:
        score = quality_eval.get('judge_score', 0)
        if score < 5.0:
            problems.append("critical_quality")
            recommendations.append(
                f"Critical quality score ({score}/10): Upgrade model or improve prompt"
            )
        elif score < 7.0:
            problems.append("low_quality")
            recommendations.append(
                f"Low quality score ({score}/10): Review prompt or consider model upgrade"
            )
        
        if quality_eval.get('hallucination_flag'):
            problems.append("hallucination")
            recommendations.append(
                "Hallucination detected: Add factual grounding, citations, or validation"
            )
        
        if quality_eval.get('factual_error'):
            problems.append("factual_error")
            recommendations.append(
                "Factual error detected: Review prompt accuracy and model choice"
            )
    
    # Check errors
    if not call.get('success', True):
        problems.append("error")
        error = call.get('error', 'Unknown error')
        error_type = call.get('error_type', 'UNKNOWN')
        recommendations.append(f"Call failed ({error_type}): {error}")
    
    # Check routing (complexity mismatch)
    routing = call.get('routing_decision')
    if routing:
        complexity = routing.get('complexity_score', 0)
        model = call.get('model_name', '').lower()
        cheap_models = ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-haiku']
        
        if complexity > 0.7 and any(m in model for m in cheap_models):
            problems.append("underspec_model")
            recommendations.append(
                f"High complexity ({complexity:.2f}) on cheap model: Consider upgrading to premium model"
            )
    
    # Check caching opportunity
    cache_meta = call.get('cache_metadata')
    if cache_meta and not cache_meta.get('cache_hit'):
        # This is a miss - could be cached if seen before
        if prompt_tokens > 500:
            problems.append("cache_opportunity")
            recommendations.append(
                "Cache opportunity: Enable caching for repeated prompts"
            )
    
    # Determine severity and primary problem
    severity = "none"
    if not problems:
        problem_type = "none"
        problem_description = "Call performing normally - no issues detected"
    else:
        # Prioritize problems by severity
        if "error" in problems or "critical_latency" in problems or "critical_quality" in problems:
            severity = "critical"
        elif "high_latency" in problems or "low_quality" in problems or "high_cost" in problems:
            severity = "high"
        elif "severe_token_imbalance" in problems or "hallucination" in problems:
            severity = "high"
        elif any("moderate" in p for p in problems):
            severity = "medium"
        else:
            severity = "low"
        
        problem_type = problems[0]
        problem_description = recommendations[0] if recommendations else "Issues detected"
    
    return {
        "problem_type": problem_type,
        "problem_description": problem_description,
        "all_problems": problems,
        "recommendations": recommendations,
        "severity": severity,
        "health_score": _calculate_health_score(problems, call),
    }


def _calculate_health_score(problems: List[str], call: Dict[str, Any]) -> float:
    """
    Calculate a 0-100 health score for the call.
    
    Args:
        problems: List of problem identifiers
        call: Call dictionary
    
    Returns:
        Health score (0-100)
    """
    if not problems:
        return 100.0
    
    # Start at 100, deduct points for each problem
    score = 100.0
    
    # Critical issues
    if "error" in problems:
        score -= 50
    if "critical_latency" in problems:
        score -= 30
    if "critical_quality" in problems:
        score -= 30
    
    # High severity issues
    if "high_latency" in problems:
        score -= 20
    if "low_quality" in problems:
        score -= 20
    if "severe_token_imbalance" in problems:
        score -= 15
    if "hallucination" in problems:
        score -= 25
    if "factual_error" in problems:
        score -= 20
    
    # Medium severity issues
    if "high_completion" in problems:
        score -= 10
    if "large_prompt" in problems:
        score -= 10
    if "token_imbalance" in problems:
        score -= 10
    if "high_cost" in problems:
        score -= 10
    if "underspec_model" in problems:
        score -= 15
    
    # Low severity issues
    if "moderate_completion" in problems:
        score -= 5
    if "moderate_prompt" in problems:
        score -= 5
    if "cache_opportunity" in problems:
        score -= 5
    
    # Ensure score stays in 0-100 range
    return max(0.0, min(100.0, score))