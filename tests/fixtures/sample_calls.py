"""
Sample Call Factory Functions
Location: tests/fixtures/sample_calls.py

Factory functions for creating test LLM calls and sessions.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from observatory.models import (
    Session, LLMCall, ModelProvider, AgentRole,
    RoutingDecision, CacheMetadata, QualityEvaluation,
    PromptBreakdown, PromptMetadata,
)


# =============================================================================
# ID GENERATORS
# =============================================================================

def generate_id() -> str:
    """Generate unique ID."""
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """Generate session ID."""
    return f"session_{uuid.uuid4().hex[:8]}"


def generate_call_id() -> str:
    """Generate call ID."""
    return f"call_{uuid.uuid4().hex[:8]}"


# =============================================================================
# SESSION FACTORY
# =============================================================================

def make_session(
    id: Optional[str] = None,
    project_name: str = "test_project",
    start_time: Optional[datetime] = None,
    **kwargs
) -> Session:
    """
    Create a Session object for testing.
    
    Args:
        id: Session ID (auto-generated if not provided)
        project_name: Project name
        start_time: Session start time
        **kwargs: Additional Session fields
    
    Returns:
        Session object
    """
    return Session(
        id=id or generate_session_id(),
        project_name=project_name,
        start_time=start_time or datetime.utcnow(),
        end_time=kwargs.get('end_time'),
        total_llm_calls=kwargs.get('total_llm_calls', 0),
        total_tokens=kwargs.get('total_tokens', 0),
        total_cost=kwargs.get('total_cost', 0.0),
        total_latency_ms=kwargs.get('total_latency_ms', 0.0),
        success=kwargs.get('success', True),
        error=kwargs.get('error'),
        operation_type=kwargs.get('operation_type'),
        metadata=kwargs.get('metadata', {}),
    )


# =============================================================================
# LLM CALL FACTORY (Returns LLMCall object for DB insertion)
# =============================================================================

def make_call(
    id: Optional[str] = None,
    session_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    provider: ModelProvider = ModelProvider.AZURE,
    model_name: str = "gpt-4o-mini",
    prompt: str = "Test prompt",
    response_text: str = "Test response",
    prompt_tokens: Optional[int] = 100,
    completion_tokens: Optional[int] = 50,
    total_cost: float = 0.01,
    latency_ms: float = 1000.0,
    agent_name: str = "TestAgent",
    operation: str = "test_operation",
    success: bool = True,
    **kwargs
) -> LLMCall:
    """
    Create an LLMCall object for database insertion.
    
    Args:
        Standard LLM call fields with sensible defaults
        **kwargs: Additional fields (quality_evaluation, routing_decision, etc.)
    
    Returns:
        LLMCall object ready for storage.save_llm_call()
    """
    # Handle None values for token counts
    p_tokens = prompt_tokens if prompt_tokens is not None else 0
    c_tokens = completion_tokens if completion_tokens is not None else 0
    total_tokens = p_tokens + c_tokens
    prompt_cost = total_cost * 0.4
    completion_cost = total_cost * 0.6
    
    # Build quality evaluation if provided
    quality_eval = None
    if 'quality_evaluation' in kwargs and kwargs['quality_evaluation']:
        qe = kwargs['quality_evaluation']
        quality_eval = QualityEvaluation(
            judge_score=qe.get('judge_score'),
            reasoning=qe.get('reasoning'),
            hallucination_flag=qe.get('hallucination_flag', False),
            factual_error=qe.get('factual_error', False),
            confidence_score=qe.get('confidence_score'),
            error_category=qe.get('error_category'),
        )
    
    # Build routing decision if provided
    routing = None
    if 'routing_decision' in kwargs and kwargs['routing_decision']:
        rd = kwargs['routing_decision']
        routing = RoutingDecision(
            complexity_score=rd.get('complexity_score', 0.5),
            chosen_model=rd.get('chosen_model', model_name),
            estimated_cost_savings=rd.get('estimated_cost_savings', 0.0),
            reasoning=rd.get('reasoning'),
        )
    
    # Build cache metadata if provided
    cache = None
    if 'cache_metadata' in kwargs and kwargs['cache_metadata']:
        cm = kwargs['cache_metadata']
        cache = CacheMetadata(
            cache_key=cm.get('cache_key'),
            cache_hit=cm.get('cache_hit', False),
            ttl_seconds=cm.get('ttl_seconds'),
        )
    
    # Build prompt breakdown if provided
    breakdown = None
    if 'prompt_breakdown' in kwargs and kwargs['prompt_breakdown']:
        pb = kwargs['prompt_breakdown']
        breakdown = PromptBreakdown(
            system_prompt=pb.get('system_prompt'),
            user_message=pb.get('user_message'),
            chat_history=pb.get('chat_history'),
            system_prompt_tokens=pb.get('system_prompt_tokens', 0),
            user_message_tokens=pb.get('user_message_tokens', 0),
            chat_history_tokens=pb.get('chat_history_tokens', 0),
        )
    
    return LLMCall(
        id=id or generate_call_id(),
        session_id=session_id or generate_session_id(),
        timestamp=timestamp or datetime.utcnow(),
        provider=provider,
        model_name=model_name,
        prompt=prompt,
        response_text=response_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_cost=prompt_cost,
        completion_cost=completion_cost,
        total_cost=total_cost,
        latency_ms=latency_ms,
        agent_name=agent_name,
        operation=operation,
        success=success,
        error=kwargs.get('error'),
        error_type=kwargs.get('error_type'),
        error_code=kwargs.get('error_code'),
        conversation_id=kwargs.get('conversation_id'),
        turn_number=kwargs.get('turn_number'),
        quality_evaluation=quality_eval,
        routing_decision=routing,
        cache_metadata=cache,
        prompt_breakdown=breakdown,
        system_prompt_tokens=kwargs.get('system_prompt_tokens'),
        user_message_tokens=kwargs.get('user_message_tokens'),
        chat_history_tokens=kwargs.get('chat_history_tokens'),
        temperature=kwargs.get('temperature', 0.7),
        max_tokens=kwargs.get('max_tokens', 1000),
        metadata=kwargs.get('metadata', {}),
    )


# =============================================================================
# LLM CALL DICT FACTORY (Returns dict for unit tests)
# =============================================================================

def make_call_dict(
    id: Optional[str] = None,
    session_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    provider: str = "AZURE",
    model_name: str = "gpt-4o-mini",
    prompt: str = "Test prompt",
    response_text: str = "Test response",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    total_cost: float = 0.01,
    latency_ms: float = 1000.0,
    agent_name: str = "TestAgent",
    operation: str = "test_operation",
    success: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Create an LLM call dictionary for unit testing services.
    
    Services take List[Dict] so this is the format they expect.
    
    Args:
        Standard LLM call fields with sensible defaults
        **kwargs: Additional fields
    
    Returns:
        Dictionary matching the format from data_fetcher._llm_call_to_dict()
    """
    # Handle None values for token counts
    p_tokens = prompt_tokens if prompt_tokens is not None else 0
    c_tokens = completion_tokens if completion_tokens is not None else 0
    total_tokens = p_tokens + c_tokens
    prompt_cost = total_cost * 0.4
    completion_cost = total_cost * 0.6
    
    return {
        'id': id or generate_call_id(),
        'session_id': session_id or generate_session_id(),
        'timestamp': timestamp or datetime.utcnow(),
        'provider': provider,
        'model_name': model_name,
        'prompt': prompt,
        'response_text': response_text,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'prompt_cost': prompt_cost,
        'completion_cost': completion_cost,
        'total_cost': total_cost,
        'latency_ms': latency_ms,
        'agent_name': agent_name,
        'operation': operation,
        'success': success,
        'error': kwargs.get('error'),
        'error_type': kwargs.get('error_type'),
        'error_code': kwargs.get('error_code'),
        'conversation_id': kwargs.get('conversation_id'),
        'turn_number': kwargs.get('turn_number'),
        'quality_evaluation': kwargs.get('quality_evaluation'),
        'routing_decision': kwargs.get('routing_decision'),
        'cache_metadata': kwargs.get('cache_metadata'),
        'prompt_breakdown': kwargs.get('prompt_breakdown'),
        'system_prompt_tokens': kwargs.get('system_prompt_tokens'),
        'user_message_tokens': kwargs.get('user_message_tokens'),
        'chat_history_tokens': kwargs.get('chat_history_tokens'),
        'temperature': kwargs.get('temperature', 0.7),
        'max_tokens': kwargs.get('max_tokens', 1000),
        'metadata': kwargs.get('metadata', {}),
    }


# =============================================================================
# CONVENIENCE FACTORIES
# =============================================================================

def make_slow_call(latency_ms: float = 15000, **kwargs) -> LLMCall:
    """Create a slow LLM call (>10s)."""
    return make_call(latency_ms=latency_ms, operation="slow_operation", **kwargs)


def make_fast_call(latency_ms: float = 500, **kwargs) -> LLMCall:
    """Create a fast LLM call (<1s)."""
    return make_call(latency_ms=latency_ms, operation="fast_operation", **kwargs)


def make_expensive_call(total_cost: float = 0.25, **kwargs) -> LLMCall:
    """Create an expensive LLM call."""
    return make_call(
        total_cost=total_cost,
        prompt_tokens=2000,
        completion_tokens=1500,
        operation="expensive_operation",
        **kwargs
    )


def make_low_quality_call(judge_score: float = 4.0, **kwargs) -> LLMCall:
    """Create a low quality LLM call."""
    return make_call(
        quality_evaluation={
            'judge_score': judge_score,
            'hallucination_flag': True,
            'reasoning': 'Poor quality response',
        },
        operation="low_quality_operation",
        **kwargs
    )


def make_failed_call(error: str = "API Error", **kwargs) -> LLMCall:
    """Create a failed LLM call."""
    return make_call(
        success=False,
        error=error,
        error_type="APIError",
        operation="failed_operation",
        **kwargs
    )


# =============================================================================
# BATCH FACTORIES
# =============================================================================

def make_calls_for_operation(
    operation: str,
    agent_name: str,
    count: int = 5,
    session_id: Optional[str] = None,
    **kwargs
) -> List[LLMCall]:
    """Create multiple calls for a single operation."""
    sid = session_id or generate_session_id()
    return [
        make_call(
            session_id=sid,
            operation=operation,
            agent_name=agent_name,
            **kwargs
        )
        for _ in range(count)
    ]


def make_call_dicts_for_operation(
    operation: str,
    agent_name: str,
    count: int = 5,
    **kwargs
) -> List[Dict[str, Any]]:
    """Create multiple call dicts for a single operation (for unit tests)."""
    return [
        make_call_dict(
            operation=operation,
            agent_name=agent_name,
            **kwargs
        )
        for _ in range(count)
    ]