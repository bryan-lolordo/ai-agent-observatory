"""
LLM Call Detail Service (Layer 2 + Layer 3)
Location: api/services/llm_call_service.py

Business logic for call listings and single call detail with diagnosis.
Shared by all stories for drill-down functionality.

Enhanced for Layer 3 pages:
- Quality: judge_evaluation object, criteria_scores, operation quality stats
- Token: ratio calculations, token breakdown, operation token averages
- Cost: pricing info, alternative models, operation cost stats
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from observatory.storage import ObservatoryStorage
from observatory.models import CallType


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
    "token_ratio_high": 20.0,  # prompt/completion ratio
    "token_ratio_severe": 50.0,
}

PROMPT_THRESHOLDS = {
    "variability_low": 0.05,      # <5% variation = static
    "variability_high": 0.20,     # >20% variation = dynamic
    "history_pct_high": 40.0,     # History > 40% is concerning
    "system_pct_high": 70.0,      # System > 70% is very high
    "history_tokens_large": 500,  # >500 history tokens = large
}

ROUTING_THRESHOLDS = {
    "complexity_low": 0.4,       # Below = simple task (can downgrade)
    "complexity_high": 0.7,      # Above = complex task (may need upgrade)
    "quality_good": 8.0,         # Above = good quality
    "quality_poor": 7.0,         # Below = needs improvement
}

CHEAP_MODELS = [
    "gpt-4o-mini", "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
    "claude-3-haiku", "claude-3.5-haiku", "claude-instant"
]


# =============================================================================
# MODEL PRICING (per 1K tokens)
# =============================================================================

MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01, "quality": "100%"},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "quality": "~90%"},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03, "quality": "~98%"},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015, "quality": "~85%"},
    
    # Anthropic
    "claude-3-opus": {"input": 0.015, "output": 0.075, "quality": "100%"},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015, "quality": "~95%"},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125, "quality": "~92%"},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015, "quality": "~98%"},
    
    # Defaults
    "default": {"input": 0.001, "output": 0.002, "quality": "~90%"},
}

# Alternative model suggestions for cost optimization
ALTERNATIVE_MODELS = [
    {"name": "gpt-4o-mini", "input_1k": 0.00015, "output_1k": 0.0006, "quality": "~90%"},
    {"name": "claude-3-haiku", "input_1k": 0.00025, "output_1k": 0.00125, "quality": "~92%"},
    {"name": "gpt-3.5-turbo", "input_1k": 0.0005, "output_1k": 0.0015, "quality": "~85%"},
]


# =============================================================================
# ROUTING ANALYSIS HELPER (for Routing Layer 3)
# =============================================================================

def _get_routing_analysis(call) -> Dict[str, Any]:
    """
    Get routing opportunity analysis for a single call (for Routing Layer 3).
    
    Delegates to routing_service for detailed analysis.
    """
    # Import here to avoid circular dependency
    from api.services.routing_service import analyze_call_routing
    
    # Convert call object to dict format that routing_service expects
    call_dict = {
        "model_name": call.model_name,
        "complexity_score": getattr(call, 'complexity_score', None),
        "judge_score": getattr(call, 'judge_score', None),
        "prompt_tokens": call.prompt_tokens,
        "completion_tokens": call.completion_tokens,
        "total_cost": call.total_cost,
        "operation": call.operation,
        "tool_call_count": getattr(call, 'tool_call_count', 0),
    }
    
    # Get detailed analysis
    return analyze_call_routing(call_dict)


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
    
    # Get model pricing
    pricing = _get_model_pricing(call.model_name)
    
    # Calculate token ratio
    token_ratio = None
    if call.completion_tokens and call.completion_tokens > 0:
        token_ratio = round(call.prompt_tokens / call.completion_tokens, 1)
    
    # Get alternative models with estimated costs
    alternative_models = _get_alternative_models(
        call.prompt_tokens or 0,
        call.completion_tokens or 0,
        call.model_name
    )
    
    # Build response
    return {
        # Identity
        "call_id": call.id,
        "timestamp": call.timestamp.isoformat() if call.timestamp else None,
        "agent_name": call.agent_name,
        "operation": call.operation,
        "session_id": getattr(call, 'session_id', None),

        # Parent call
        "request_id": getattr(call, 'request_id', None),
        "parent_call_id": getattr(call, 'parent_call_id', None),

        # Call type
        "call_type": getattr(call, 'call_type', 'llm').value if hasattr(getattr(call, 'call_type', None), 'value') else getattr(call, 'call_type', 'llm'),

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
        
        # Token Ratio (for Token Imbalance story)
        "ratio": token_ratio,
        "token_ratio": token_ratio,
        
        # Token Breakdown
        "system_prompt_tokens": getattr(call, 'system_prompt_tokens', None),
        "user_message_tokens": getattr(call, 'user_message_tokens', None),
        "chat_history_tokens": getattr(call, 'chat_history_tokens', None),
        "chat_history_count": getattr(call, 'chat_history_count', None),
        "conversation_context_tokens": getattr(call, 'conversation_context_tokens', None),
        "tool_definitions_tokens": getattr(call, 'tool_definitions_tokens', None),
        
        # Content
        "prompt": getattr(call, 'prompt', None),
        "system_prompt": getattr(call, 'system_prompt', None) or _extract_system_prompt(call),
        "user_message": getattr(call, 'user_message', None) or _extract_user_message(call),
        "response_text": getattr(call, 'response_text', None),
        
        # Quality - Basic
        "success": call.success,
        "error": getattr(call, 'error', None),
        "error_type": getattr(call, 'error_type', None),
        "error_code": getattr(call, 'error_code', None),
        "judge_score": getattr(call, 'judge_score', None) or _get_judge_score(call),
        "judge_confidence": _get_judge_confidence(call),
        "hallucination_flag": getattr(call, 'hallucination_flag', None) if getattr(call, 'hallucination_flag', None) is not None else _get_hallucination_flag(call),
        "hallucination_detected": getattr(call, 'hallucination_flag', None) if getattr(call, 'hallucination_flag', None) is not None else _get_hallucination_flag(call),
        "quality_reasoning": _get_quality_reasoning(call),
        "confidence_score": getattr(call, 'confidence_score', None),
        
        # Quality - Full Evaluation Object (for Quality Layer 3)
        "judge_evaluation": _get_full_quality_evaluation(call),
        
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
        
        # Pricing (for Cost Layer 3)
        "input_price_per_1k": pricing["input"],
        "output_price_per_1k": pricing["output"],
        
        # Alternative Models (for Cost Layer 3)
        "alternative_models": alternative_models,
        
        # Operation Stats (for all Layer 3 pages)
        "operation_avg_cost": comparison.get("operation_avg_cost"),
        "operation_total_cost": comparison.get("operation_total_cost"),
        "operation_call_count": comparison.get("operation_call_count"),
        "operation_avg_latency_ms": comparison.get("operation_avg_latency_ms"),
        "operation_avg_tokens": comparison.get("operation_avg_tokens"),
        
        # Token Stats (for Token Layer 3)
        "operation_avg_ratio": comparison.get("operation_avg_ratio"),
        "operation_avg_prompt": comparison.get("operation_avg_prompt"),
        "operation_avg_completion": comparison.get("operation_avg_completion"),
        
        # Quality Stats (for Quality Layer 3)
        "operation_avg_score": comparison.get("operation_avg_score"),
        "operation_min_score": comparison.get("operation_min_score"),
        "operation_max_score": comparison.get("operation_max_score"),
        
        # Full Comparison object
        "comparison": comparison,
        
        # Diagnosis and recommendations
        "diagnosis": diagnosis,
        
        # Routing Analysis (for Routing Layer 3)
        "routing_analysis": _get_routing_analysis(call),

        # NEW: Conversation Breakdown (for Latency Layer 3)
        "conversation_breakdown": _analyze_conversation_breakdown(call),
        
        # NEW: Comparison Benchmarks (for Latency Layer 3)
        "comparison_benchmarks": _get_comparison_benchmarks(call),
    }


# =============================================================================
# LIST CALLS (Layer 2) - EXPANDED
# =============================================================================

def get_calls(
    days: int = 7,
    operation: Optional[str] = None,
    agent: Optional[str] = None,
    call_type: Optional[str] = None,
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

    # Convert call_type string to enum if provided
    call_type_enum = CallType(call_type) if call_type else None
    
    try:
        calls = ObservatoryStorage.get_llm_calls(
            agent_name=agent,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            call_type=call_type_enum,
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
        
        # Calculate token ratio
        token_ratio = None
        if c.completion_tokens and c.completion_tokens > 0:
            token_ratio = round(c.prompt_tokens / c.completion_tokens, 1)
        
        result.append({
            # Identity
            "call_id": c.id,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "agent_name": c.agent_name,
            "operation": c.operation,
            "session_id": getattr(c, 'session_id', None),
            
            # Call type
            "call_type": getattr(c, 'call_type', 'llm').value if hasattr(getattr(c, 'call_type', None), 'value') else getattr(c, 'call_type', 'llm'),

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
            "ratio": token_ratio,
            "token_ratio": token_ratio,
            
            # Tokens - Breakdown (for Prompt Composition story)
            "system_prompt_tokens": getattr(c, 'system_prompt_tokens', None),
            "user_message_tokens": getattr(c, 'user_message_tokens', None),
            "chat_history_tokens": getattr(c, 'chat_history_tokens', None),
            "chat_history_count": getattr(c, 'chat_history_count', None),
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
        })
    
    return result

# =============================================================================
# TRACE TREE METHODS (NEW)
# =============================================================================

def get_calls_by_parent(parent_call_id: str) -> List[Dict[str, Any]]:
    """
    Get all child calls for a parent.
    Used to build call tree hierarchy.
    
    Args:
        parent_call_id: The request_id of the parent call
        
    Returns:
        List of child calls (same format as get_calls)
    """
    try:
        children = ObservatoryStorage.get_llm_calls(
            parent_call_id=parent_call_id,
            limit=1000  # Reasonable limit for children
        )
    except Exception as e:
        print(f"Error fetching child calls: {e}")
        return []
    
    # Convert to same format as get_calls()
    result = []
    for c in children:
        # Reuse existing conversion logic
        cache_hit = _get_cache_hit(c)
        judge_score = _get_judge_score(c)
        hallucination_flag = _get_hallucination_flag(c)
        
        token_ratio = None
        if c.completion_tokens and c.completion_tokens > 0:
            token_ratio = round(c.prompt_tokens / c.completion_tokens, 1)
        
        result.append({
            "call_id": c.id,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "agent_name": c.agent_name,
            "agent_role": getattr(c, 'agent_role', None).value if getattr(c, 'agent_role', None) else None,
            "operation": c.operation,
            "model_name": c.model_name,
            "latency_ms": c.latency_ms,
            "prompt_tokens": c.prompt_tokens,
            "completion_tokens": c.completion_tokens,
            "total_tokens": c.total_tokens,
            "total_cost": c.total_cost,
            "success": c.success,
            "error": getattr(c, 'error', None),
            "request_id": getattr(c, 'request_id', None),  # Important for tree building
            "parent_call_id": getattr(c, 'parent_call_id', None),
            "conversation_id": getattr(c, 'conversation_id', None),
            "turn_number": getattr(c, 'turn_number', None),
            "cache_hit": cache_hit,
            "judge_score": judge_score,
            "hallucination_flag": hallucination_flag,
            "token_ratio": token_ratio,
        })
    
    return result


def get_calls_by_conversation(
    conversation_id: str,
    role_filter: Optional[str] = None,
    order_by: str = "turn_number",
) -> List[Dict[str, Any]]:
    """
    Get all calls in a conversation.
    
    Args:
        conversation_id: Conversation identifier
        role_filter: Optional filter (e.g., "orchestrator")
        order_by: Sort field ("turn_number", "timestamp")
        
    Returns:
        List of calls in conversation
    """
    try:
        calls = ObservatoryStorage.get_llm_calls(
            conversation_id=conversation_id,
            order_by=order_by,
            limit=1000
        )
    except Exception as e:
        print(f"Error fetching conversation calls: {e}")
        return []
    
    # Apply role filter if specified
    if role_filter:
        calls = [c for c in calls if getattr(c, 'agent_role', None) and getattr(c, 'agent_role').value == role_filter]
    
    # Convert using same logic as get_calls_by_parent
    result = []
    for c in calls:
        cache_hit = _get_cache_hit(c)
        judge_score = _get_judge_score(c)
        
        token_ratio = None
        if c.completion_tokens and c.completion_tokens > 0:
            token_ratio = round(c.prompt_tokens / c.completion_tokens, 1)
        
        result.append({
            "call_id": c.id,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "agent_name": c.agent_name,
            "agent_role": getattr(c, 'agent_role', None).value if getattr(c, 'agent_role', None) else None,
            "operation": c.operation,
            "model_name": c.model_name,
            "latency_ms": c.latency_ms,
            "prompt_tokens": c.prompt_tokens,
            "completion_tokens": c.completion_tokens,
            "total_tokens": c.total_tokens,
            "total_cost": c.total_cost,
            "success": c.success,
            "request_id": getattr(c, 'request_id', None),
            "parent_call_id": getattr(c, 'parent_call_id', None),
            "conversation_id": getattr(c, 'conversation_id', None),
            "turn_number": getattr(c, 'turn_number', None),
            "user_message": _extract_user_message(c),
            "cache_hit": cache_hit,
            "judge_score": judge_score,
            "token_ratio": token_ratio,
        })
    
    return result


# =============================================================================
# HELPER FUNCTIONS - EXTRACTION
# =============================================================================

def _extract_system_prompt(call) -> Optional[str]:
    """Extract system prompt from prompt_breakdown or prompt field."""
    try:
        return call.prompt_breakdown.system_prompt if call.prompt_breakdown else None
    except AttributeError:
        return None


def _extract_user_message(call) -> Optional[str]:
    """Extract user message from prompt_breakdown or prompt field."""
    try:
        return call.prompt_breakdown.user_message if call.prompt_breakdown else None
    except AttributeError:
        return None

def _get_judge_score(call) -> Optional[float]:
    """Get quality judge score."""
    if hasattr(call, 'quality_evaluation') and call.quality_evaluation:
        if hasattr(call.quality_evaluation, 'judge_score'):
            return call.quality_evaluation.judge_score
    return None


def _get_judge_confidence(call) -> Optional[float]:
    """Get quality judge confidence."""
    if hasattr(call, 'quality_evaluation') and call.quality_evaluation:
        if hasattr(call.quality_evaluation, 'confidence'):
            return call.quality_evaluation.confidence
    return None


def _get_hallucination_flag(call) -> bool:
    """Get hallucination flag."""
    if hasattr(call, 'quality_evaluation') and call.quality_evaluation:
        if hasattr(call.quality_evaluation, 'hallucination_flag'):
            return call.quality_evaluation.hallucination_flag
    return False


def _get_quality_reasoning(call) -> Optional[str]:
    """Get quality evaluation reasoning."""
    if hasattr(call, 'quality_evaluation') and call.quality_evaluation:
        if hasattr(call.quality_evaluation, 'reasoning'):
            return call.quality_evaluation.reasoning
    return None


def _get_cache_hit(call) -> bool:
    """Get cache hit status."""
    if hasattr(call, 'cache_hit') and call.cache_hit is not None:
        return call.cache_hit
    if hasattr(call, 'cache_metadata') and call.cache_metadata:
        if hasattr(call.cache_metadata, 'cache_hit'):
            return call.cache_metadata.cache_hit
    return False


def _get_cache_key(call) -> Optional[str]:
    """Get cache key."""
    if hasattr(call, 'cache_key') and call.cache_key:
        return call.cache_key
    if hasattr(call, 'cache_metadata') and call.cache_metadata:
        if hasattr(call.cache_metadata, 'cache_key'):
            return call.cache_metadata.cache_key
    return None


def _get_full_quality_evaluation(call) -> Optional[Dict]:
    """
    Get full quality evaluation object for Layer 3 Quality page.
    
    Returns structured object with:
    - overall_score
    - confidence
    - criteria_scores (relevance, accuracy, completeness, coherence, helpfulness)
    - reasoning
    - issues_found
    - strengths
    """
    if not hasattr(call, 'quality_evaluation') or not call.quality_evaluation:
        return None
    
    qe = call.quality_evaluation
    
    # If it's already a dict, return it
    if isinstance(qe, dict):
        return qe
    
    # If it's a Pydantic model, convert to dict
    if hasattr(qe, 'model_dump'):
        return qe.model_dump()
    elif hasattr(qe, 'dict'):
        return qe.dict()
    
    # Build from individual attributes
    return {
        "overall_score": getattr(qe, 'judge_score', None) or getattr(qe, 'overall_score', None),
        "confidence": getattr(qe, 'confidence', None),
        "criteria_scores": getattr(qe, 'criteria_scores', None),
        "reasoning": getattr(qe, 'reasoning', None),
        "issues_found": getattr(qe, 'issues_found', []),
        "strengths": getattr(qe, 'strengths', []),
        "hallucination_flag": getattr(qe, 'hallucination_flag', False),
    }


def _get_model_pricing(model_name: str) -> Dict[str, float]:
    """Get pricing for a model (per 1K tokens)."""
    if not model_name:
        return MODEL_PRICING["default"]
    
    model_lower = model_name.lower()
    
    # Try exact match first
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    
    # Try partial matches
    for key in MODEL_PRICING:
        if key in model_lower:
            return MODEL_PRICING[key]
    
    return MODEL_PRICING["default"]


def _get_alternative_models(
    prompt_tokens: int,
    completion_tokens: int,
    current_model: str
) -> List[Dict[str, Any]]:
    """
    Get alternative models with estimated costs for comparison.
    
    Used by Cost Layer 3 to show cheaper alternatives.
    """
    alternatives = []
    
    for model in ALTERNATIVE_MODELS:
        # Skip if this is the current model
        if current_model and model["name"].lower() in current_model.lower():
            continue
        
        # Calculate estimated cost
        input_cost = (prompt_tokens / 1000) * model["input_1k"]
        output_cost = (completion_tokens / 1000) * model["output_1k"]
        estimated_cost = input_cost + output_cost
        
        alternatives.append({
            "name": model["name"],
            "input_1k": model["input_1k"],
            "output_1k": model["output_1k"],
            "estimated_cost": round(estimated_cost, 6),
            "quality": model["quality"],
        })
    
    # Sort by estimated cost
    alternatives.sort(key=lambda x: x["estimated_cost"])
    
    return alternatives


# =============================================================================
# COMPARISON METRICS (Enhanced for all Layer 3 pages)
# =============================================================================

def _get_comparison_metrics(call) -> Dict[str, Any]:
    """
    Get comparison metrics for this call vs operation averages.
    
    Enhanced to include:
    - Latency stats
    - Cost stats (for Cost Layer 3)
    - Token stats (for Token Layer 3)
    - Quality stats (for Quality Layer 3)
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
    
    # === LATENCY STATS ===
    latencies = [c.latency_ms for c in operation_calls if c.latency_ms]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # === COST STATS ===
    costs = [c.total_cost for c in operation_calls if c.total_cost]
    avg_cost = sum(costs) / len(costs) if costs else 0
    total_cost = sum(costs) if costs else 0
    
    # === TOKEN STATS ===
    prompt_tokens_list = [c.prompt_tokens for c in operation_calls if c.prompt_tokens]
    completion_tokens_list = [c.completion_tokens for c in operation_calls if c.completion_tokens]
    total_tokens_list = [c.total_tokens for c in operation_calls if c.total_tokens]
    
    avg_prompt = sum(prompt_tokens_list) / len(prompt_tokens_list) if prompt_tokens_list else 0
    avg_completion = sum(completion_tokens_list) / len(completion_tokens_list) if completion_tokens_list else 0
    avg_tokens = sum(total_tokens_list) / len(total_tokens_list) if total_tokens_list else 0
    
    # Calculate token ratios
    ratios = []
    for c in operation_calls:
        if c.prompt_tokens and c.completion_tokens and c.completion_tokens > 0:
            ratios.append(c.prompt_tokens / c.completion_tokens)
    avg_ratio = sum(ratios) / len(ratios) if ratios else None
    
    # === QUALITY STATS ===
    quality_scores = []
    for c in operation_calls:
        score = None
        if hasattr(c, 'judge_score') and c.judge_score is not None:
            score = c.judge_score
        elif hasattr(c, 'quality_evaluation') and c.quality_evaluation:
            score = getattr(c.quality_evaluation, 'judge_score', None)
        if score is not None:
            quality_scores.append(score)
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    min_quality = min(quality_scores) if quality_scores else None
    max_quality = max(quality_scores) if quality_scores else None
    
    # === CALCULATE RATIOS ===
    latency_ratio = call.latency_ms / avg_latency if avg_latency > 0 and call.latency_ms else 1.0
    cost_ratio = call.total_cost / avg_cost if avg_cost > 0 and call.total_cost else 1.0
    
    return {
        "available": True,
        "operation_call_count": len(operation_calls),
        
        # Latency
        "operation_avg_latency_ms": round(avg_latency, 1),
        "latency_ratio": round(latency_ratio, 2),
        "is_latency_outlier": latency_ratio > 2.0,
        
        # Cost
        "operation_avg_cost": round(avg_cost, 6),
        "operation_total_cost": round(total_cost, 4),
        "cost_ratio": round(cost_ratio, 2),
        "is_cost_outlier": cost_ratio > 2.0,
        
        # Tokens
        "operation_avg_tokens": round(avg_tokens, 0),
        "operation_avg_prompt": round(avg_prompt, 0),
        "operation_avg_completion": round(avg_completion, 0),
        "operation_avg_ratio": round(avg_ratio, 1) if avg_ratio else None,
        
        # Quality
        "operation_avg_score": round(avg_quality, 1) if avg_quality else None,
        "operation_min_score": round(min_quality, 1) if min_quality else None,
        "operation_max_score": round(max_quality, 1) if max_quality else None,
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
    
    # ----- TOKEN RATIO ISSUES (for Token Imbalance story) -----
    if call.prompt_tokens and call.completion_tokens and call.completion_tokens > 0:
        ratio = call.prompt_tokens / call.completion_tokens
        if ratio > THRESHOLDS["token_ratio_severe"]:
            issues.append({
                "type": "severe_token_imbalance",
                "severity": "critical",
                "message": f"Severe token imbalance ({ratio:.0f}:1 ratio)",
                "detail": "Prompt is extremely large relative to output"
            })
            recommendations.append({
                "action": "Simplify system prompt",
                "impact": "high",
                "code_hint": "Remove verbose examples, use structured format",
                "estimated_improvement": "40-60% token reduction"
            })
        elif ratio > THRESHOLDS["token_ratio_high"]:
            issues.append({
                "type": "high_token_imbalance",
                "severity": "warning",
                "message": f"High token imbalance ({ratio:.0f}:1 ratio)",
                "detail": "Prompt is disproportionately large"
            })
            recommendations.append({
                "action": "Request longer output or reduce input",
                "impact": "medium",
                "code_hint": "Add 'Provide detailed response' instruction",
                "estimated_improvement": "Better token efficiency"
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
    max_tokens = getattr(call, 'max_tokens', None)
    if max_tokens is None and call.completion_tokens and call.completion_tokens > 500:
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
    system_prompt_tokens = getattr(call, 'system_prompt_tokens', None)
    if system_prompt_tokens and call.prompt_tokens:
        ratio = system_prompt_tokens / call.prompt_tokens
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
    hallucination = getattr(call, 'hallucination_flag', None)
    if hallucination is None:
        hallucination = _get_hallucination_flag(call)
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
    
    # ----- COST ISSUES -----
    if call.total_cost:
        if call.total_cost > THRESHOLDS["cost_very_high"]:
            issues.append({
                "type": "very_high_cost",
                "severity": "critical",
                "message": f"Very high cost (${call.total_cost:.3f})",
                "detail": "This call is expensive, consider optimization"
            })
            recommendations.append({
                "action": "Switch to cheaper model",
                "impact": "high",
                "code_hint": "model='gpt-4o-mini' for simpler tasks",
                "estimated_improvement": "90%+ cost reduction possible"
            })
        elif call.total_cost > THRESHOLDS["cost_high"]:
            issues.append({
                "type": "high_cost",
                "severity": "warning",
                "message": f"High cost (${call.total_cost:.3f})",
                "detail": "Consider cost optimization strategies"
            })
    
    # ----- CACHE MISS -----
    cache_hit = getattr(call, 'cache_hit', None)
    if cache_hit is None:
        cache_hit = _get_cache_hit(call)
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
    if not call.success:
        error = getattr(call, 'error', None)
        error_type = getattr(call, 'error_type', None)
        issues.append({
            "type": "error",
            "severity": "critical",
            "message": f"Call failed: {error_type or 'Unknown error'}",
            "detail": (error[:200] if error else "No error details") if error else "No error details"
        })
        if error_type == "RATE_LIMIT":
            recommendations.append({
                "action": "Implement rate limiting",
                "impact": "high",
                "code_hint": "Add exponential backoff retry logic",
                "estimated_improvement": "Prevents rate limit errors"
            })
        elif error_type == "TIMEOUT":
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
    
    if comparison.get("available") and comparison.get("is_cost_outlier"):
        issues.append({
            "type": "cost_outlier",
            "severity": "info",
            "message": f"This call is {comparison['cost_ratio']:.1f}x more expensive than average",
            "detail": f"Operation average: ${comparison['operation_avg_cost']:.4f}"
        })
    
    # ----- EXPENSIVE MODEL FOR SIMPLE TASK -----
    if call.model_name and ("gpt-4" in call.model_name.lower() or "claude-3-opus" in call.model_name.lower()):
        if call.completion_tokens and call.completion_tokens < 200:
            # Short response from expensive model
            issues.append({
                "type": "expensive_model",
                "severity": "info",
                "message": f"Using {call.model_name} for short response",
                "detail": "Consider cheaper model for simple tasks"
            })
            if not any("cheaper model" in r["action"].lower() for r in recommendations):
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

# =============================================================================
# CONVERSATION BREAKDOWN ANALYSIS (NEW)
# =============================================================================

def _analyze_conversation_breakdown(call) -> Optional[Dict[str, Any]]:
    """
    Analyze multi-turn conversation to identify optimization opportunities.
    
    Returns detailed breakdown of chat history with recommendations.
    Used by Latency Layer 3 to visualize conversation accumulation.
    """
    chat_history_tokens = getattr(call, 'chat_history_tokens', None)
    chat_history_count = getattr(call, 'chat_history_count', None)
    turn_number = getattr(call, 'turn_number', None)
    
    if not chat_history_tokens or not turn_number or turn_number <= 1:
        return None
    
    system_prompt_tokens = getattr(call, 'system_prompt_tokens', None) or 0
    user_message_tokens = getattr(call, 'user_message_tokens', None) or 0
    conversation_context_tokens = getattr(call, 'conversation_context_tokens', None) or 0
    prompt_tokens = call.prompt_tokens or 0
    
    messages = []
    
    # System prompt
    if system_prompt_tokens > 0:
        messages.append({
            'type': 'system',
            'turn': 0,
            'tokens': system_prompt_tokens,
            'percentage': (system_prompt_tokens / prompt_tokens * 100) if prompt_tokens else 0,
            'status': 'cacheable',
            'color': 'blue',
            'label': 'System Prompt'
        })
    
    # Estimate tokens per turn
    if chat_history_count and chat_history_count > 0:
        avg_tokens_per_message = chat_history_tokens / chat_history_count
        
        for i in range(1, turn_number):
            messages.append({
                'type': 'user',
                'turn': i,
                'tokens': int(avg_tokens_per_message * 0.3),
                'percentage': (avg_tokens_per_message * 0.3 / prompt_tokens * 100) if prompt_tokens else 0,
                'status': 'old' if i < turn_number - 1 else 'recent',
                'color': 'yellow' if i < turn_number - 1 else 'orange',
                'label': f'Turn {i} User'
            })
            
            messages.append({
                'type': 'assistant',
                'turn': i,
                'tokens': int(avg_tokens_per_message * 0.7),
                'percentage': (avg_tokens_per_message * 0.7 / prompt_tokens * 100) if prompt_tokens else 0,
                'status': 'old' if i < turn_number - 1 else 'recent',
                'color': 'yellow' if i < turn_number - 1 else 'orange',
                'label': f'Turn {i} Assistant'
            })
    
    # Current user message
    if user_message_tokens > 0:
        messages.append({
            'type': 'user',
            'turn': turn_number,
            'tokens': user_message_tokens,
            'percentage': (user_message_tokens / prompt_tokens * 100) if prompt_tokens else 0,
            'status': 'current',
            'color': 'green',
            'label': f'Turn {turn_number} User (Current)'
        })
    
    # Static context
    if conversation_context_tokens > 0:
        messages.append({
            'type': 'context',
            'turn': 0,
            'tokens': conversation_context_tokens,
            'percentage': (conversation_context_tokens / prompt_tokens * 100) if prompt_tokens else 0,
            'status': 'cacheable',
            'color': 'blue',
            'label': 'Static Context (Job/Resume)'
        })
    
    # Calculate insights
    old_tokens = sum(m['tokens'] for m in messages if m['status'] == 'old')
    cacheable_tokens = sum(m['tokens'] for m in messages if m['status'] == 'cacheable')
    current_tokens = sum(m['tokens'] for m in messages if m['status'] == 'current')
    
    insights = []
    
    if old_tokens > prompt_tokens * 0.4:
        pct = (old_tokens / prompt_tokens * 100)
        insights.append(f"{pct:.0f}% ({old_tokens:,} tokens) are old turns not needed for current task")
    
    if cacheable_tokens > prompt_tokens * 0.2:
        pct = (cacheable_tokens / prompt_tokens * 100)
        insights.append(f"{pct:.0f}% ({cacheable_tokens:,} tokens) are static → cache candidate")
    
    if current_tokens < prompt_tokens * 0.05:
        pct = (current_tokens / prompt_tokens * 100)
        insights.append(f"Only {pct:.1f}% ({current_tokens} tokens) is new user input")
    
    return {
        'messages': messages,
        'total_tokens': prompt_tokens,
        'old_tokens': old_tokens,
        'cacheable_tokens': cacheable_tokens,
        'current_tokens': current_tokens,
        'turn_number': turn_number,
        'chat_history_count': chat_history_count,
        'insights': insights,
    }


def build_chat_history_breakdown(conversation_id: str, current_turn: int) -> Dict[str, Any]:
    """
    Build chat history breakdown with actual message content.

    Used by the /tree endpoint to provide expandable chat history.
    Returns messages with content for the ChatHistoryBreakdown component.
    """
    # Get all orchestrator calls in conversation
    try:
        calls = ObservatoryStorage.get_llm_calls(
            conversation_id=conversation_id,
            order_by="turn_number",
            limit=100
        )
    except Exception:
        return {"messages": []}

    # Filter to orchestrator calls only
    orchestrator_calls = [c for c in calls if getattr(c, 'agent_role', None) and getattr(c, 'agent_role').value == 'orchestrator']

    if not orchestrator_calls:
        return {"messages": []}

    messages = []
    total_tokens = 0

    # Get the current call to extract system prompt
    current_call = next((c for c in orchestrator_calls if getattr(c, 'turn_number', 0) == current_turn), None)

    if current_call:
        total_tokens = current_call.prompt_tokens or 0

        # 1. System Prompt 
        system_prompt = _extract_system_prompt(current_call)
        system_prompt_tokens = getattr(current_call, 'system_prompt_tokens', None) or 0

        if system_prompt and system_prompt_tokens > 0:
            messages.append({
                'type': 'system',
                'turn': 0,
                'tokens': system_prompt_tokens,
                'percentage': (system_prompt_tokens / total_tokens * 100) if total_tokens else 0,
                'status': 'cacheable',
                'label': 'System Prompt',
                'content': system_prompt[:500] + '...' if len(system_prompt) > 500 else system_prompt,
                'optimization': 'Enable caching for 90% cost reduction on repeated calls' if system_prompt_tokens > 500 else None
            })

    # 2. Chat History 
    for call in orchestrator_calls:
        turn = getattr(call, 'turn_number', 0)

        if turn >= current_turn:
            break

        # User message
        user_msg = _extract_user_message(call)
        user_tokens = getattr(call, 'user_message_tokens', None) or 0

        if user_msg and user_tokens > 0:
            status = 'recent' if turn >= current_turn - 2 else 'old'

            messages.append({
                'type': 'user',
                'turn': turn,
                'tokens': user_tokens,
                'percentage': (user_tokens / total_tokens * 100) if total_tokens else 0,
                'status': status,
                'label': f'Turn {turn} User',
                'content': user_msg,
                'optimization': f'Turn {turn} could be summarized or removed' if status == 'old' else None
            })

        # Assistant response
        response = getattr(call, 'response_text', None)
        response_tokens = call.completion_tokens or 0

        if response:
            status = 'recent' if turn >= current_turn - 2 else 'old'

            messages.append({
                'type': 'assistant',
                'turn': turn,
                'tokens': response_tokens,
                'percentage': (response_tokens / total_tokens * 100) if total_tokens else 0,
                'status': status,
                'label': f'Turn {turn} Assistant',
                'content': response[:300] + '...' if len(response) > 300 else response,
                'optimization': None
            })

    # 3. Current user message
    if current_call:
        current_user_msg = _extract_user_message(current_call)
        current_user_tokens = getattr(current_call, 'user_message_tokens', None) or 0

        if current_user_msg and current_user_tokens > 0:
            messages.append({
                'type': 'user',
                'turn': current_turn,
                'tokens': current_user_tokens,
                'percentage': (current_user_tokens / total_tokens * 100) if total_tokens else 0,
                'status': 'current',
                'label': f'Turn {current_turn} User (Current)',
                'content': current_user_msg,
                'optimization': None
            })
        # 4. Current assistant response
        current_response = getattr(current_call, 'response_text', None)
        current_response_tokens = current_call.completion_tokens or 0
        
        if current_response:
            messages.append({
                'type': 'assistant',
                'turn': current_turn,
                'tokens': current_response_tokens,
                'percentage': (current_response_tokens / total_tokens * 100) if total_tokens else 0,
                'status': 'current',
                'label': f'Turn {current_turn} Assistant (Current)',
                'content': current_response[:300] + '...' if len(current_response) > 300 else current_response,
                'optimization': None
            })

    # Calculate stats
    old_tokens = sum(m['tokens'] for m in messages if m.get('status') == 'old')
    cacheable_tokens = sum(m['tokens'] for m in messages if m.get('status') == 'cacheable')
    current_tokens = sum(m['tokens'] for m in messages if m.get('status') == 'current')
    recent_tokens = sum(m['tokens'] for m in messages if m.get('status') == 'recent')

    return {
        'messages': messages,
        'total_tokens': total_tokens,
        'old_tokens': old_tokens,
        'cacheable_tokens': cacheable_tokens,
        'current_tokens': current_tokens,
        'recent_tokens': recent_tokens,
        'turn_number': current_turn,
    }


def _get_comparison_benchmarks(call) -> Dict[str, Any]:
    """
    Get comparison benchmarks for this call.
    
    Returns 3 types of comparisons:
    1. Fastest same operation
    2. Fastest similar context (similar tokens + turn)
    3. Median for operation
    """
    if not call.agent_name or not call.operation:
        return {'available': False}
    
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
        return {'available': False}
    
    if len(operation_calls) < 2:
        return {'available': False}
    
    successful_calls = [c for c in operation_calls if c.success and c.latency_ms]
    if not successful_calls:
        return {'available': False}
    
    # 1. Fastest same operation
    fastest_same = min(successful_calls, key=lambda c: c.latency_ms)
    
    # 2. Fastest similar context
    turn_number = getattr(call, 'turn_number', None)
    similar_context_calls = [
        c for c in successful_calls
        if abs(c.prompt_tokens - call.prompt_tokens) < call.prompt_tokens * 0.3
        and (not turn_number or abs(getattr(c, 'turn_number', 0) - turn_number) <= 1)
    ]
    fastest_similar = min(similar_context_calls, key=lambda c: c.latency_ms) if similar_context_calls else None
    
    # 3. Median for operation
    latencies = sorted([c.latency_ms for c in successful_calls])
    median_latency = latencies[len(latencies) // 2]
    median_call = next((c for c in successful_calls if c.latency_ms == median_latency), None)
    
    return {
        'available': True,
        'current': {
            'latency_ms': call.latency_ms,
            'prompt_tokens': call.prompt_tokens,
            'completion_tokens': call.completion_tokens,
            'turn_number': turn_number,
        },
        'fastest_same_operation': {
            'latency_ms': fastest_same.latency_ms,
            'speedup': round(call.latency_ms / fastest_same.latency_ms, 1),
            'call_id': fastest_same.id,
        } if fastest_same else None,
        'fastest_similar_context': {
            'latency_ms': fastest_similar.latency_ms,
            'speedup': round(call.latency_ms / fastest_similar.latency_ms, 1),
            'call_id': fastest_similar.id,
            'prompt_tokens': fastest_similar.prompt_tokens,
            'turn_number': getattr(fastest_similar, 'turn_number', None),
        } if fastest_similar else None,
        'median_for_operation': {
            'latency_ms': median_latency,
            'comparison': 'faster' if call.latency_ms < median_latency else 'slower',
            'ratio': round(call.latency_ms / median_latency, 1),
        } if median_call else None,
    }