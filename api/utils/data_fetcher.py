"""
Data Fetcher - Centralized Data Access Layer
Location: api/utils/data_fetcher.py

All database queries and data retrieval functions.
Migrated from Streamlit dashboard - no caching decorators.

UPDATED: Added conversation_id, user_id, experiment_id filters
UPDATED: Enhanced _llm_call_to_dict() with all new top-level fields
"""

import os
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from functools import lru_cache

from observatory import Storage
from observatory.models import Session, LLMCall, ModelProvider
from api.utils.aggregators import (
    calculate_session_kpis,
    aggregate_by_model,
    aggregate_by_agent,
    aggregate_by_operation,
    calculate_cost_breakdown,
    calculate_routing_metrics,
    calculate_cache_metrics,
    calculate_quality_metrics,
    calculate_time_series,
    group_by_time_period
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_period_to_days(period: Union[str, int, float, None], default: float = 7) -> float:
    """
    Parse period string like '1h', '24h', '7d', '30d' to days.
    
    Args:
        period: Period string, int, or None
        default: Default days if period is None
    
    Returns:
        Number of days as float
    """
    if period is None:
        return default
    
    if isinstance(period, (int, float)):
        return float(period)
    
    if isinstance(period, str):
        period = period.strip().lower()
        if period.endswith('h'):
            hours = int(period[:-1])
            return hours / 24
        elif period.endswith('d'):
            return int(period[:-1])
        elif period.endswith('w'):
            return int(period[:-1]) * 7
        elif period.endswith('m'):
            return int(period[:-1]) * 30
        else:
            try:
                return float(period)
            except ValueError:
                return default
    
    return default


# =============================================================================
# STORAGE ACCESS (Singleton pattern instead of st.cache_resource)
# =============================================================================

_storage_instance: Optional[Storage] = None

def get_storage() -> Storage:
    """Get Storage instance (singleton)."""
    global _storage_instance
    if _storage_instance is None:
        db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
        _storage_instance = Storage(database_url=db_path)
    return _storage_instance


def reset_storage():
    """Reset storage instance (useful for testing)."""
    global _storage_instance
    _storage_instance = None


# =============================================================================
# BASIC QUERIES
# =============================================================================

def get_available_projects() -> List[str]:
    """Get list of all projects in database."""
    storage = get_storage()
    return storage.get_distinct_projects()


def get_available_models(project_name: Optional[str] = None) -> List[str]:
    """Get list of all models, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_models(project_name=project_name)


def get_available_agents(project_name: Optional[str] = None) -> List[str]:
    """Get list of all agents, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_agents(project_name=project_name)


def get_available_operations(project_name: Optional[str] = None) -> List[str]:
    """Get list of all operations, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_operations(project_name=project_name)


def get_sessions(
    project_name: Optional[str] = None,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    operation_type: Optional[str] = None,
) -> List[Session]:
    """Get sessions with optional filters."""
    storage = get_storage()
    return storage.get_sessions(
        project_name=project_name,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )


def get_llm_calls(
    project_name: Optional[str] = None,
    session_id: Optional[str] = None,
    model_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    operation: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    success_only: Optional[bool] = None,
    has_quality_eval: Optional[bool] = None,
    has_routing: Optional[bool] = None,
    has_cache: Optional[bool] = None,
    conversation_id: Optional[str] = None,  # NEW
    user_id: Optional[str] = None,          # NEW
    experiment_id: Optional[str] = None,    # NEW
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get LLM calls with optional filters.
    
    UPDATED: Added conversation_id, user_id, experiment_id filters
    
    Args:
        project_name: Filter by project name
        session_id: Filter by session ID
        model_name: Filter by model name
        agent_name: Filter by agent name
        operation: Filter by operation name
        start_time: Filter calls on or after this time
        end_time: Filter calls on or before this time
        success_only: If True, only return successful calls
        has_quality_eval: If True, only return calls with quality evaluation
        has_routing: If True, only return calls with routing decision
        has_cache: If True, only return calls with cache metadata
        conversation_id: Filter by conversation ID (NEW)
        user_id: Filter by user ID (NEW)
        experiment_id: Filter by experiment ID (NEW)
        limit: Maximum number of calls to return
    
    Returns:
        List of LLM call dictionaries
    """
    storage = get_storage()
    
    # Pass all supported filters to storage layer
    calls = storage.get_llm_calls(
        project_name=project_name,
        session_id=session_id,
        model_name=model_name,
        agent_name=agent_name,
        operation=operation,
        start_time=start_time,
        end_time=end_time,
        success_only=success_only,
        conversation_id=conversation_id,  # NEW
        user_id=user_id,                  # NEW
        experiment_id=experiment_id,      # NEW
        limit=limit
    )
    
    # Convert to dicts
    result = [_llm_call_to_dict(call) for call in calls]
    
    # Apply additional filters that storage doesn't support natively
    if has_quality_eval is True:
        result = [c for c in result if c.get('quality_evaluation') is not None]
    elif has_quality_eval is False:
        result = [c for c in result if c.get('quality_evaluation') is None]
    
    if has_routing is True:
        result = [c for c in result if c.get('routing_decision') is not None]
    elif has_routing is False:
        result = [c for c in result if c.get('routing_decision') is None]
    
    if has_cache is True:
        result = [c for c in result if c.get('cache_metadata') is not None]
    elif has_cache is False:
        result = [c for c in result if c.get('cache_metadata') is None]
    
    return result


def get_conversation(
    conversation_id: str,
    project_name: Optional[str] = None,
) -> List[Dict]:
    """
    Get all calls in a conversation, ordered by turn number.
    
    NEW FUNCTION
    
    Args:
        conversation_id: Conversation ID
        project_name: Optional project filter
    
    Returns:
        List of LLM calls in conversation order
    """
    storage = get_storage()
    
    calls = storage.get_llm_calls(
        project_name=project_name,
        conversation_id=conversation_id,
        limit=1000,
    )
    
    # Convert to dicts and sort by turn_number
    call_dicts = [_llm_call_to_dict(call) for call in calls]
    call_dicts.sort(key=lambda x: x.get('turn_number') or 0)
    
    return call_dicts


# =============================================================================
# CONVERSION: LLMCall to Dict (UPDATED)
# =============================================================================

def _llm_call_to_dict(call: LLMCall) -> Dict[str, Any]:
    """
    Convert LLMCall Pydantic model to dictionary.
    
    UPDATED: Added all new top-level fields
    """
    data = {
        # Basic fields
        'id': call.id,
        'session_id': call.session_id,
        'timestamp': call.timestamp,
        'agent_name': call.agent_name,
        'operation': call.operation,
        'provider': call.provider.value if call.provider else None,
        'model_name': call.model_name,
        
        # Token counts
        'prompt_tokens': call.prompt_tokens or 0,
        'completion_tokens': call.completion_tokens or 0,
        'total_tokens': call.total_tokens or 0,
        
        # Cost and latency
        'latency_ms': call.latency_ms or 0,
        'prompt_cost': call.prompt_cost or 0,
        'completion_cost': call.completion_cost or 0,
        'total_cost': call.total_cost or 0,
        
        # Content
        'prompt': call.prompt,
        'prompt_normalized': call.prompt_normalized,
        'response_text': call.response_text,
        
        # Status
        'error': call.error,
        'success': call.success if call.success is not None else True,
        
        # A/B testing (existing)
        'prompt_variant_id': call.prompt_variant_id,
        'test_dataset_id': call.test_dataset_id,
        
        # NEW: Conversation linking
        'conversation_id': getattr(call, 'conversation_id', None),
        'turn_number': getattr(call, 'turn_number', None),
        'parent_call_id': getattr(call, 'parent_call_id', None),
        'user_id': getattr(call, 'user_id', None),
        
        # NEW: Model configuration
        'temperature': getattr(call, 'temperature', None),
        'max_tokens': getattr(call, 'max_tokens', None),
        'top_p': getattr(call, 'top_p', None),
        
        # NEW: Token breakdown (promoted to top-level)
        'system_prompt_tokens': getattr(call, 'system_prompt_tokens', None),
        'user_message_tokens': getattr(call, 'user_message_tokens', None),
        'chat_history_tokens': getattr(call, 'chat_history_tokens', None),
        'conversation_context_tokens': getattr(call, 'conversation_context_tokens', None),
        'tool_definitions_tokens': getattr(call, 'tool_definitions_tokens', None),
        
        # NEW: Tool tracking
        'tool_call_count': getattr(call, 'tool_call_count', None),
        'tool_execution_time_ms': getattr(call, 'tool_execution_time_ms', None),
        
        # NEW: Streaming
        'time_to_first_token_ms': getattr(call, 'time_to_first_token_ms', None),
        
        # NEW: Error details
        'error_type': getattr(call, 'error_type', None),
        'error_code': getattr(call, 'error_code', None),
        'retry_count': getattr(call, 'retry_count', None),
        
        # NEW: Cached tokens
        'cached_prompt_tokens': getattr(call, 'cached_prompt_tokens', None),
        'cached_token_savings': getattr(call, 'cached_token_savings', None),
        
        # NEW: Observability
        'trace_id': getattr(call, 'trace_id', None),
        'request_id': getattr(call, 'request_id', None),
        'environment': getattr(call, 'environment', None),
        
        # NEW: Experiment tracking
        'experiment_id': getattr(call, 'experiment_id', None),
        'control_group': getattr(call, 'control_group', None),
        
        # Flexible metadata
        'metadata': call.metadata,
    }
    
    # Routing Decision
    if call.routing_decision:
        data['routing_decision'] = {
            'chosen_model': call.routing_decision.chosen_model,
            'alternative_models': call.routing_decision.alternative_models,
            'model_scores': call.routing_decision.model_scores,
            'reasoning': call.routing_decision.reasoning,
            'rule_triggered': call.routing_decision.rule_triggered,
            'complexity_score': call.routing_decision.complexity_score,
            'estimated_cost_savings': call.routing_decision.estimated_cost_savings,
            'routing_strategy': getattr(call.routing_decision, 'routing_strategy', None),
        }
    else:
        data['routing_decision'] = None
    
    # Cache Metadata
    if call.cache_metadata:
        data['cache_metadata'] = {
            'cache_hit': call.cache_metadata.cache_hit,
            'cache_key': call.cache_metadata.cache_key,
            'cache_cluster_id': call.cache_metadata.cache_cluster_id,
            'normalization_strategy': call.cache_metadata.normalization_strategy,
            'similarity_score': call.cache_metadata.similarity_score,
            'eviction_info': call.cache_metadata.eviction_info,
            'cache_key_candidates': getattr(call.cache_metadata, 'cache_key_candidates', None),
            'dynamic_fields': getattr(call.cache_metadata, 'dynamic_fields', None),
            'content_hash': getattr(call.cache_metadata, 'content_hash', None),
            'ttl_seconds': getattr(call.cache_metadata, 'ttl_seconds', None),
        }
    else:
        data['cache_metadata'] = None
    
    # Quality Evaluation
    if call.quality_evaluation:
        data['quality_evaluation'] = {
            'judge_score': call.quality_evaluation.judge_score,
            'reasoning': call.quality_evaluation.reasoning,
            'hallucination_flag': call.quality_evaluation.hallucination_flag,
            'error_category': getattr(call.quality_evaluation, 'error_category', None),
            'confidence_score': getattr(call.quality_evaluation, 'confidence_score', None),
            'judge_model': getattr(call.quality_evaluation, 'judge_model', None),
            'criteria_scores': getattr(call.quality_evaluation, 'criteria_scores', None),
            'failure_reason': getattr(call.quality_evaluation, 'failure_reason', None),
            'improvement_suggestion': getattr(call.quality_evaluation, 'improvement_suggestion', None),
            'hallucination_details': getattr(call.quality_evaluation, 'hallucination_details', None),
            'evidence_cited': getattr(call.quality_evaluation, 'evidence_cited', None),
            'factual_error': getattr(call.quality_evaluation, 'factual_error', None),
        }
    else:
        data['quality_evaluation'] = None
    
    # Prompt Breakdown (UPDATED with new fields)
    if hasattr(call, 'prompt_breakdown') and call.prompt_breakdown:
        data['prompt_breakdown'] = {
            'system_prompt': call.prompt_breakdown.system_prompt,
            'system_prompt_tokens': call.prompt_breakdown.system_prompt_tokens,
            'chat_history': call.prompt_breakdown.chat_history,
            'chat_history_tokens': call.prompt_breakdown.chat_history_tokens,
            'chat_history_count': call.prompt_breakdown.chat_history_count,
            'user_message': call.prompt_breakdown.user_message,
            'user_message_tokens': call.prompt_breakdown.user_message_tokens,
            'response_text': call.prompt_breakdown.response_text,
            # NEW fields
            'conversation_context': getattr(call.prompt_breakdown, 'conversation_context', None),
            'conversation_context_tokens': getattr(call.prompt_breakdown, 'conversation_context_tokens', None),
            'tool_definitions': getattr(call.prompt_breakdown, 'tool_definitions', None),
            'tool_definitions_tokens': getattr(call.prompt_breakdown, 'tool_definitions_tokens', None),
            'tool_definitions_count': getattr(call.prompt_breakdown, 'tool_definitions_count', None),
            'total_input_tokens': getattr(call.prompt_breakdown, 'total_input_tokens', None),
            'system_to_total_ratio': getattr(call.prompt_breakdown, 'system_to_total_ratio', None),
            'history_to_total_ratio': getattr(call.prompt_breakdown, 'history_to_total_ratio', None),
            'context_to_total_ratio': getattr(call.prompt_breakdown, 'context_to_total_ratio', None),
            'response_tokens': getattr(call.prompt_breakdown, 'response_tokens', None),
        }
    else:
        data['prompt_breakdown'] = None
    
    # Prompt Metadata
    if hasattr(call, 'prompt_metadata') and call.prompt_metadata:
        data['prompt_metadata'] = {
            'prompt_template_id': call.prompt_metadata.prompt_template_id,
            'prompt_version': call.prompt_metadata.prompt_version,
            'prompt_hash': getattr(call.prompt_metadata, 'prompt_hash', None),         
            'experiment_id': getattr(call.prompt_metadata, 'experiment_id', None),     
            'compressible_sections': call.prompt_metadata.compressible_sections,
            'optimization_flags': call.prompt_metadata.optimization_flags,
            'config_version': call.prompt_metadata.config_version,
        }
    else:
        data['prompt_metadata'] = None
    
    # NEW: Model Config
    if hasattr(call, 'llm_config') and call.llm_config:
        data['model_config'] = {  # Keep as 'model_config' in dict for API compatibility
            'temperature': call.llm_config.temperature,
            'max_tokens': call.llm_config.max_tokens,
            'top_p': call.llm_config.top_p,
            'frequency_penalty': getattr(call.llm_config, 'frequency_penalty', None),
            'presence_penalty': getattr(call.llm_config, 'presence_penalty', None),
            'stop_sequences': getattr(call.llm_config, 'stop_sequences', None),
            'response_format': getattr(call.llm_config, 'response_format', None),
            'seed': getattr(call.llm_config, 'seed', None),
        }
    else:
        data['model_config'] = None
    
    # NEW: Streaming Metrics
    if hasattr(call, 'streaming_metrics') and call.streaming_metrics:
        data['streaming_metrics'] = {
            'is_streaming': call.streaming_metrics.is_streaming,
            'time_to_first_token_ms': call.streaming_metrics.time_to_first_token_ms,
            'stream_chunk_count': getattr(call.streaming_metrics, 'stream_chunk_count', None),
            'stream_interrupted': getattr(call.streaming_metrics, 'stream_interrupted', None),
            'average_chunk_size': getattr(call.streaming_metrics, 'average_chunk_size', None),
        }
    else:
        data['streaming_metrics'] = None
    
    # NEW: Experiment Metadata
    if hasattr(call, 'experiment_metadata') and call.experiment_metadata:
        data['experiment_metadata'] = {
            'experiment_id': call.experiment_metadata.experiment_id,
            'experiment_name': getattr(call.experiment_metadata, 'experiment_name', None),
            'variant_id': getattr(call.experiment_metadata, 'variant_id', None),
            'variant_name': getattr(call.experiment_metadata, 'variant_name', None),
            'control_group': call.experiment_metadata.control_group,
            'hypothesis': getattr(call.experiment_metadata, 'hypothesis', None),
            'expected_improvement': getattr(call.experiment_metadata, 'expected_improvement', None),
        }
    else:
        data['experiment_metadata'] = None
    
    # NEW: Error Details
    if hasattr(call, 'error_details') and call.error_details:
        data['error_details'] = {
            'error_type': call.error_details.error_type,
            'error_code': call.error_details.error_code,
            'retry_count': call.error_details.retry_count,
            'retry_strategy': getattr(call.error_details, 'retry_strategy', None),
            'final_success': getattr(call.error_details, 'final_success', None),
            'error_details': getattr(call.error_details, 'error_details', None),
        }
    else:
        data['error_details'] = None
    
    # NEW: Tool Calls Made
    if hasattr(call, 'tool_calls_made') and call.tool_calls_made:
        data['tool_calls_made'] = call.tool_calls_made
    else:
        data['tool_calls_made'] = None
    
    return data


# =============================================================================
# HIGH-LEVEL ANALYSIS FUNCTIONS
# =============================================================================

def get_project_overview(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get comprehensive project overview with all metrics."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    if not llm_calls:
        return {
            'kpis': {
                'total_calls': 0,
                'total_cost': 0,
                'total_tokens': 0,
                'avg_latency_ms': 0,
                'avg_cost_per_session': 0,
                'success_rate': 1.0,
                'total_sessions': 0,
            },
            'by_model': {},
            'by_agent': {},
            'by_operation': {},
            'cost_breakdown': {},
            'routing_metrics': {},
            'cache_metrics': {},
            'quality_metrics': {},
        }
    
    # Calculate all metrics
    by_model = aggregate_by_model(llm_calls)
    by_agent = aggregate_by_agent(llm_calls)
    by_operation = aggregate_by_operation(llm_calls)
    cost_breakdown = calculate_cost_breakdown(llm_calls)
    routing_metrics = calculate_routing_metrics(llm_calls)
    cache_metrics = calculate_cache_metrics(llm_calls)
    quality_metrics = calculate_quality_metrics(llm_calls)
    
    # Calculate KPIs
    total_cost = sum(c['total_cost'] for c in llm_calls)
    total_tokens = sum(c['total_tokens'] for c in llm_calls)
    total_latency = sum(c['latency_ms'] for c in llm_calls)
    successful = sum(1 for c in llm_calls if c.get('success', True))
    
    kpis = {
        'total_calls': len(llm_calls),
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'avg_latency_ms': total_latency / len(llm_calls) if llm_calls else 0,
        'avg_cost_per_call': total_cost / len(llm_calls) if llm_calls else 0,
        'success_rate': successful / len(llm_calls) if llm_calls else 1.0,
    }
    
    return {
        'kpis': kpis,
        'by_model': by_model,
        'by_agent': by_agent,
        'by_operation': by_operation,
        'cost_breakdown': cost_breakdown,
        'routing_metrics': routing_metrics,
        'cache_metrics': cache_metrics,
        'quality_metrics': quality_metrics,
    }


def get_time_series_data(
    project_name: Optional[str] = None,
    metric: str = 'cost',
    interval: str = 'hour',
    period: str = '24h'
) -> Dict[datetime, float]:
    """Get time series data for charts."""
    days = parse_period_to_days(period)
    start_time = datetime.utcnow() - timedelta(days=days)
    
    llm_calls = get_llm_calls(
        project_name=project_name,
        start_time=start_time,
        limit=10000
    )
    
    return calculate_time_series(llm_calls, metric=metric, interval=interval)


def get_comparative_metrics(
    project_name: Optional[str] = None,
    period: str = '24h'
) -> Dict[str, Any]:
    """Get comparative metrics between current and previous period."""
    days = parse_period_to_days(period)
    now = datetime.utcnow()
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    
    current_calls = get_llm_calls(
        project_name=project_name,
        start_time=current_start,
        limit=5000
    )
    
    previous_calls = get_llm_calls(
        project_name=project_name,
        start_time=previous_start,
        end_time=current_start,
        limit=5000
    )
    
    def calc_metrics(calls):
        if not calls:
            return {'cost': 0, 'tokens': 0, 'latency': 0, 'count': 0}
        return {
            'cost': sum(c['total_cost'] for c in calls),
            'tokens': sum(c['total_tokens'] for c in calls),
            'latency': sum(c['latency_ms'] for c in calls) / len(calls),
            'count': len(calls),
        }
    
    return {
        'current': calc_metrics(current_calls),
        'previous': calc_metrics(previous_calls),
    }


def get_routing_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get routing analysis for Model Router page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    routing_metrics = calculate_routing_metrics(llm_calls)
    
    # Get calls with routing decisions for detailed analysis
    routed_calls = [c for c in llm_calls if c.get('routing_decision')]
    
    # Group by strategy
    by_strategy = {}
    for call in routed_calls:
        strategy = call['routing_decision'].get('routing_strategy') or 'unknown'
        if strategy not in by_strategy:
            by_strategy[strategy] = {
                'count': 0,
                'total_cost': 0,
                'total_savings': 0,
                'models_used': set(),
            }
        by_strategy[strategy]['count'] += 1
        by_strategy[strategy]['total_cost'] += call['total_cost']
        by_strategy[strategy]['total_savings'] += (
            call['routing_decision'].get('estimated_cost_savings') or 0
        )
        by_strategy[strategy]['models_used'].add(
            call['routing_decision']['chosen_model']
        )
    
    # Convert sets to lists
    for strategy in by_strategy:
        by_strategy[strategy]['models_used'] = list(by_strategy[strategy]['models_used'])
    
    # Complexity distribution
    complexity_scores = [
        c['routing_decision'].get('complexity_score')
        for c in routed_calls
        if c['routing_decision'].get('complexity_score') is not None
    ]
    
    return {
        'metrics': routing_metrics,
        'by_strategy': by_strategy,
        'complexity_scores': complexity_scores,
        'total_routed': len(routed_calls),
        'total_calls': len(llm_calls),
    }


def get_cache_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get cache analysis for Cache Analyzer page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    cache_metrics = calculate_cache_metrics(llm_calls)
    
    # Get calls with cache metadata
    cached_calls = [c for c in llm_calls if c.get('cache_metadata')]
    
    # Analyze cache hits vs misses
    hits = [c for c in cached_calls if (c.get('cache_metadata') or {}).get('cache_hit')]
    misses = [c for c in cached_calls if not (c.get('cache_metadata') or {}).get('cache_hit')]
    
    # Group by cluster
    by_cluster = {}
    for call in cached_calls:
        cluster = (call.get('cache_metadata') or {}).get('cache_cluster_id') or 'unknown'
        if cluster not in by_cluster:
            by_cluster[cluster] = {'hits': 0, 'misses': 0, 'total_cost': 0}
        if (call.get('cache_metadata') or {}).get('cache_hit'):
            by_cluster[cluster]['hits'] += 1
        else:
            by_cluster[cluster]['misses'] += 1
        by_cluster[cluster]['total_cost'] += call['total_cost']
    
    # Find duplicate prompts (potential cache opportunities)
    prompt_counts = {}
    for call in llm_calls:
        prompt = call.get('prompt_normalized') or call.get('prompt')
        if prompt:
            prompt_key = prompt[:200]  # Use first 200 chars as key
            if prompt_key not in prompt_counts:
                prompt_counts[prompt_key] = {'count': 0, 'total_cost': 0, 'operations': set()}
            prompt_counts[prompt_key]['count'] += 1
            prompt_counts[prompt_key]['total_cost'] += call['total_cost']
            if call.get('operation'):
                prompt_counts[prompt_key]['operations'].add(call['operation'])
    
    # Find duplicates (count > 1)
    duplicates = [
        {
            'prompt_preview': k[:100],
            'count': v['count'],
            'total_cost': v['total_cost'],
            'operations': list(v['operations']),
        }
        for k, v in prompt_counts.items()
        if v['count'] > 1
    ]
    duplicates.sort(key=lambda x: x['total_cost'], reverse=True)
    
    return {
        'metrics': cache_metrics,
        'by_cluster': by_cluster,
        'hits': len(hits),
        'misses': len(misses),
        'duplicates': duplicates[:20],  # Top 20 duplicates
        'total_with_cache': len(cached_calls),
        'total_calls': len(llm_calls),
    }


def get_quality_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get quality analysis for LLM Judge page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    quality_metrics = calculate_quality_metrics(llm_calls)
    
    # Get calls with quality evaluation
    evaluated_calls = [c for c in llm_calls if c.get('quality_evaluation')]
    
    # Find best and worst examples
    scored_calls = [
        c for c in evaluated_calls 
        if c.get('quality_evaluation', {}).get('judge_score') is not None
    ]
    scored_calls.sort(key=lambda x: x['quality_evaluation']['judge_score'], reverse=True)
    
    best_examples = scored_calls[:5]
    worst_examples = scored_calls[-5:] if len(scored_calls) >= 5 else scored_calls
    
    # Analyze failure reasons
    failure_reasons = {}
    for call in evaluated_calls:
        reason = (call.get('quality_evaluation') or {}).get('failure_reason')
        if reason:
            if reason not in failure_reasons:
                failure_reasons[reason] = {'count': 0, 'examples': []}
            failure_reasons[reason]['count'] += 1
            if len(failure_reasons[reason]['examples']) < 3:
                failure_reasons[reason]['examples'].append({
                    'prompt': call.get('prompt', '')[:200],
                    'response': call.get('response_text', '')[:200],
                    'score': call['quality_evaluation'].get('judge_score'),
                })
    
    # Analyze by criteria
    criteria_analysis = {}
    for call in evaluated_calls:
        criteria_scores = (call.get('quality_evaluation') or {}).get('criteria_scores')
        if criteria_scores:
            for criterion, score in criteria_scores.items():
                if criterion not in criteria_analysis:
                    criteria_analysis[criterion] = []
                criteria_analysis[criterion].append(score)
    
    # Calculate averages
    for criterion in criteria_analysis:
        scores = criteria_analysis[criterion]
        criteria_analysis[criterion] = {
            'avg': sum(scores) / len(scores) if scores else 0,
            'min': min(scores) if scores else 0,
            'max': max(scores) if scores else 0,
            'count': len(scores),
        }
    
    return {
        'metrics': quality_metrics,
        'best_examples': [
            {
                'score': c['quality_evaluation']['judge_score'],
                'model': c['model_name'],
                'agent': c['agent_name'],
                'operation': c.get('operation'),
                'reasoning': c['quality_evaluation'].get('reasoning'),
                'prompt': c['prompt'][:200] if c.get('prompt') else None,
                'response': c['response_text'][:200] if c.get('response_text') else None
            }
            for c in best_examples if c.get('quality_evaluation')
        ],
        'worst_examples': [
            {
                'score': c['quality_evaluation']['judge_score'],
                'model': c['model_name'],
                'agent': c['agent_name'],
                'operation': c.get('operation'),
                'reasoning': c['quality_evaluation'].get('reasoning'),
                'failure_reason': c['quality_evaluation'].get('failure_reason'),
                'improvement_suggestion': c['quality_evaluation'].get('improvement_suggestion'),
                'hallucination': c['quality_evaluation'].get('hallucination_flag'),
                'prompt': c['prompt'][:200] if c.get('prompt') else None,
                'response': c['response_text'][:200] if c.get('response_text') else None
            }
            for c in worst_examples if c.get('quality_evaluation')
        ],
        'failure_reasons': failure_reasons,
        'criteria_analysis': criteria_analysis,
        'total_evaluated': len(evaluated_calls),
        'total_calls': len(llm_calls),
    }


def get_prompt_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get prompt analysis for Prompt Optimizer page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    if not llm_calls:
        return {
            'total_calls': 0,
            'calls_with_breakdown': 0,
            'calls_with_metadata': 0,
            'token_stats': {
                'avg_system_tokens': 0,
                'avg_history_tokens': 0,
                'avg_user_tokens': 0,
                'avg_total_prompt_tokens': 0,
            },
            'long_prompt_count': 0,
            'by_operation': {},
            'by_template': {},
        }
    
    # Analyze calls with prompt breakdown
    calls_with_breakdown = [c for c in llm_calls if c.get('prompt_breakdown')]
    calls_with_metadata = [c for c in llm_calls if c.get('prompt_metadata')]
    
    # Token distribution
    token_stats = {
        'avg_system_tokens': 0,
        'avg_history_tokens': 0,
        'avg_user_tokens': 0,
        'avg_total_prompt_tokens': 0,
    }
    
    if calls_with_breakdown:
        token_stats['avg_system_tokens'] = sum(
            c['prompt_breakdown'].get('system_prompt_tokens', 0) or 0 
            for c in calls_with_breakdown
        ) / len(calls_with_breakdown)
        
        token_stats['avg_history_tokens'] = sum(
            c['prompt_breakdown'].get('chat_history_tokens', 0) or 0 
            for c in calls_with_breakdown
        ) / len(calls_with_breakdown)
        
        token_stats['avg_user_tokens'] = sum(
            c['prompt_breakdown'].get('user_message_tokens', 0) or 0 
            for c in calls_with_breakdown
        ) / len(calls_with_breakdown)
    
    token_stats['avg_total_prompt_tokens'] = sum(
        c['prompt_tokens'] for c in llm_calls
    ) / len(llm_calls) if llm_calls else 0
    
    # Find long prompts
    long_prompts = [c for c in llm_calls if c['prompt_tokens'] > 4000]
    
    # By operation analysis
    by_operation = {}
    for call in llm_calls:
        op = call.get('operation') or 'unknown'
        if op not in by_operation:
            by_operation[op] = {
                'count': 0,
                'total_prompt_tokens': 0,
                'has_breakdown': 0,
                'has_metadata': 0,
            }
        by_operation[op]['count'] += 1
        by_operation[op]['total_prompt_tokens'] += call['prompt_tokens']
        if call.get('prompt_breakdown'):
            by_operation[op]['has_breakdown'] += 1
        if call.get('prompt_metadata'):
            by_operation[op]['has_metadata'] += 1
    
    # Calculate averages
    for op in by_operation:
        by_operation[op]['avg_prompt_tokens'] = (
            by_operation[op]['total_prompt_tokens'] / by_operation[op]['count']
        )
    
    # By template analysis
    by_template = {}
    for call in calls_with_metadata:
        template_id = call['prompt_metadata'].get('prompt_template_id') or 'unknown'
        version = call['prompt_metadata'].get('prompt_version') or 'unknown'
        key = f"{template_id}@{version}"
        
        if key not in by_template:
            by_template[key] = {
                'template_id': template_id,
                'version': version,
                'count': 0,
                'total_cost': 0,
                'total_tokens': 0,
            }
        by_template[key]['count'] += 1
        by_template[key]['total_cost'] += call['total_cost']
        by_template[key]['total_tokens'] += call['prompt_tokens']
    
    # Calculate averages
    for key in by_template:
        by_template[key]['avg_cost'] = (
            by_template[key]['total_cost'] / by_template[key]['count']
        )
        by_template[key]['avg_tokens'] = (
            by_template[key]['total_tokens'] / by_template[key]['count']
        )
    
    return {
        'total_calls': len(llm_calls),
        'calls_with_breakdown': len(calls_with_breakdown),
        'calls_with_metadata': len(calls_with_metadata),
        'token_stats': token_stats,
        'long_prompt_count': len(long_prompts),
        'by_operation': by_operation,
        'by_template': by_template,
    }


# =============================================================================
# COST ANALYSIS
# =============================================================================

def get_cost_forecast(
    project_name: Optional[str] = None,
    requests_per_hour: int = 100,
    avg_prompt_tokens: int = 500,
    avg_completion_tokens: int = 200,
    model_mix: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Forecast costs based on projected usage."""
    llm_calls = get_llm_calls(project_name=project_name, limit=1000)
    
    if llm_calls:
        actual_avg_cost = sum(c['total_cost'] for c in llm_calls) / len(llm_calls)
    else:
        actual_avg_cost = 0.005
    
    requests_per_day = requests_per_hour * 24
    requests_per_month = requests_per_day * 30
    
    daily_cost = actual_avg_cost * requests_per_day
    monthly_cost = actual_avg_cost * requests_per_month
    
    return {
        'hourly': {
            'requests': requests_per_hour,
            'cost': actual_avg_cost * requests_per_hour
        },
        'daily': {
            'requests': requests_per_day,
            'cost': daily_cost
        },
        'monthly': {
            'requests': requests_per_month,
            'cost': monthly_cost
        },
        'avg_cost_per_request': actual_avg_cost,
        'assumptions': {
            'requests_per_hour': requests_per_hour,
            'avg_prompt_tokens': avg_prompt_tokens,
            'avg_completion_tokens': avg_completion_tokens
        }
    }


# =============================================================================
# DATABASE STATS
# =============================================================================

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    sessions = get_sessions(limit=10000)
    llm_calls = get_llm_calls(limit=10000)
    
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    if db_path.startswith("sqlite:///"):
        file_path = db_path[10:]
    else:
        file_path = "observatory.db"
    
    db_size_mb = 0
    if os.path.exists(file_path):
        db_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    return {
        'total_sessions': len(sessions),
        'total_llm_calls': len(llm_calls),
        'database_size_mb': db_size_mb,
        'database_path': file_path,
    }