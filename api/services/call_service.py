"""
Call Service - Layer 3 Business Logic
Location: api/services/call_service.py

Handles full call detail with diagnosis.
Shared by Stories 1, 3, 4, 5, 6, 7.
"""

from typing import Dict, Any, Optional
from api.utils.data_fetcher import get_llm_calls


def get_call_detail(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full call detail with diagnosis and recommendations.
    
    Args:
        call_id: Unique identifier for the LLM call
    
    Returns:
        Full call details with expanded JSON fields and diagnosis,
        or None if call not found
    """
    # Get the specific call
    calls = get_llm_calls(limit=1)
    
    # In production, you'd filter by ID:
    # calls = storage.query(LLMCall).filter(LLMCall.id == call_id).first()
    # For now, we'll search the list
    call = None
    all_calls = get_llm_calls(limit=10000)
    for c in all_calls:
        if c.get('id') == call_id:
            call = c
            break
    
    if not call:
        return None
    
    # Add diagnosis based on call characteristics
    diagnosis = _diagnose_call(call)
    
    # Return full call with diagnosis
    return {
        # Basic info
        "id": call.get('id'),
        "session_id": call.get('session_id'),
        "timestamp": call.get('timestamp'),
        "agent_name": call.get('agent_name'),
        "operation": call.get('operation'),
        "model_name": call.get('model_name'),
        
        # Performance metrics
        "latency_ms": call.get('latency_ms'),
        "prompt_tokens": call.get('prompt_tokens'),
        "completion_tokens": call.get('completion_tokens'),
        "total_tokens": call.get('total_tokens'),
        
        # Cost metrics
        "total_cost": call.get('total_cost'),
        "prompt_cost": call.get('prompt_cost'),
        "completion_cost": call.get('completion_cost'),
        
        # Content
        "prompt": call.get('prompt'),
        "response_text": call.get('response_text'),
        
        # Metadata (expanded JSON)
        "routing_decision": call.get('routing_decision'),
        "cache_metadata": call.get('cache_metadata'),
        "quality_evaluation": call.get('quality_evaluation'),
        "prompt_breakdown": call.get('prompt_breakdown'),
        "model_config": call.get('model_config'),
        
        # Diagnosis
        "diagnosis": diagnosis,
    }


def _diagnose_call(call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnose issues and provide recommendations for a call.
    
    Args:
        call: LLM call dictionary
    
    Returns:
        {
            "problem_type": str,
            "problem_description": str,
            "recommendations": [str, ...]
        }
    """
    problems = []
    recommendations = []
    
    latency = call.get('latency_ms', 0)
    prompt_tokens = call.get('prompt_tokens', 0)
    completion_tokens = call.get('completion_tokens', 0)
    
    # Check latency
    if latency > 10000:
        problems.append("critical_latency")
        recommendations.append("Latency > 10s: Consider faster model or reduce output tokens")
    elif latency > 5000:
        problems.append("high_latency")
        recommendations.append("Latency > 5s: Review completion token count")
    
    # Check completion tokens
    if completion_tokens > 2000:
        problems.append("high_completion")
        recommendations.append(
            f"High completion tokens ({completion_tokens}): Add JSON schema or explicit length limits"
        )
    
    # Check prompt tokens
    if prompt_tokens > 4000:
        problems.append("large_prompt")
        recommendations.append(
            f"Large prompt ({prompt_tokens} tokens): Consider caching or compression"
        )
    
    # Check token ratio
    if completion_tokens > 0:
        ratio = prompt_tokens / completion_tokens
        if ratio > 20:
            problems.append("token_imbalance")
            recommendations.append(
                f"Poor token ratio ({ratio:.0f}:1): Review if all context is necessary"
            )
    
    # Check quality
    quality_eval = call.get('quality_evaluation')
    if quality_eval:
        score = quality_eval.get('judge_score', 0)
        if score < 7.0:
            problems.append("low_quality")
            recommendations.append(
                f"Low quality score ({score}): Review prompt or consider model upgrade"
            )
        
        if quality_eval.get('hallucination_flag'):
            problems.append("hallucination")
            recommendations.append("Hallucination detected: Add factual grounding or citations")
    
    # Check errors
    if not call.get('success', True):
        problems.append("error")
        error = call.get('error', 'Unknown error')
        recommendations.append(f"Call failed: {error}")
    
    # Determine primary problem
    if not problems:
        problem_type = "none"
        problem_description = "Call performing normally"
    else:
        problem_type = problems[0]
        problem_description = recommendations[0] if recommendations else "Issues detected"
    
    return {
        "problem_type": problem_type,
        "problem_description": problem_description,
        "all_problems": problems,
        "recommendations": recommendations,
    }