"""
Data Fetcher - Centralized Data Access Layer
Location: dashboard/utils/data_fetcher.py

All database queries and data retrieval functions.
Pages should use these functions instead of querying storage directly.
"""

import streamlit as st
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

from observatory import Storage
from observatory.models import Session, LLMCall, ModelProvider
from dashboard.utils.aggregators import (
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
# STORAGE ACCESS
# =============================================================================

@st.cache_resource
def get_storage() -> Storage:
    """Get cached Storage instance."""
    import os
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    return Storage(database_url=db_path)


# =============================================================================
# BASIC QUERIES
# =============================================================================

@st.cache_data(ttl=30)
def get_available_projects() -> List[str]:
    """Get list of all projects in database."""
    storage = get_storage()
    return storage.get_distinct_projects()


@st.cache_data(ttl=30)
def get_available_models(project_name: Optional[str] = None) -> List[str]:
    """Get list of all models, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_models(project_name=project_name)


@st.cache_data(ttl=30)
def get_available_agents(project_name: Optional[str] = None) -> List[str]:
    """Get list of all agents, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_agents(project_name=project_name)


@st.cache_data(ttl=30)
def get_available_operations(project_name: Optional[str] = None) -> List[str]:
    """Get list of all operations, optionally filtered by project."""
    storage = get_storage()
    return storage.get_distinct_operations(project_name=project_name)


@st.cache_data(ttl=30)
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
        operation_type=operation_type,
    )


@st.cache_data(ttl=30)
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
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Get LLM calls with optional filters."""
    storage = get_storage()
    calls = storage.get_llm_calls(
        project_name=project_name,
        session_id=session_id,
        model_name=model_name,
        agent_name=agent_name,
        operation=operation,
        start_time=start_time,
        end_time=end_time,
        success_only=success_only,
        has_quality_eval=has_quality_eval,
        has_routing=has_routing,
        has_cache=has_cache,
        limit=limit
    )
    
    return [_llm_call_to_dict(call) for call in calls]


# =============================================================================
# CONVERSION: LLMCall to Dict
# =============================================================================

def _llm_call_to_dict(call: LLMCall) -> Dict[str, Any]:
    """Convert LLMCall Pydantic model to dictionary."""
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
        
        # A/B testing
        'prompt_variant_id': call.prompt_variant_id,
        'test_dataset_id': call.test_dataset_id,
        
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
            'judge_model': call.quality_evaluation.judge_model,
            'criteria_scores': call.quality_evaluation.criteria_scores,
            'reasoning': call.quality_evaluation.reasoning,
            'hallucination_flag': call.quality_evaluation.hallucination_flag,
            'confidence': call.quality_evaluation.confidence,
            'failure_reason': getattr(call.quality_evaluation, 'failure_reason', None),
            'improvement_suggestion': getattr(call.quality_evaluation, 'improvement_suggestion', None),
            'hallucination_details': getattr(call.quality_evaluation, 'hallucination_details', None),
            'evidence_cited': getattr(call.quality_evaluation, 'evidence_cited', None),
            'factual_error': getattr(call.quality_evaluation, 'factual_error', None),
        }
    else:
        data['quality_evaluation'] = None
    
    # Prompt Breakdown
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
        }
    else:
        data['prompt_breakdown'] = None
    
    # Prompt Metadata
    if hasattr(call, 'prompt_metadata') and call.prompt_metadata:
        data['prompt_metadata'] = {
            'prompt_template_id': call.prompt_metadata.prompt_template_id,
            'prompt_version': call.prompt_metadata.prompt_version,
            'compressible_sections': call.prompt_metadata.compressible_sections,
            'optimization_flags': call.prompt_metadata.optimization_flags,
            'config_version': call.prompt_metadata.config_version,
        }
    else:
        data['prompt_metadata'] = None
    
    return data


# =============================================================================
# HIGH-LEVEL ANALYSIS FUNCTIONS
# =============================================================================

@st.cache_data(ttl=60)
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
    
    # Calculate KPIs
    total_calls = len(llm_calls)
    total_cost = sum(c['total_cost'] for c in llm_calls)
    total_tokens = sum(c['total_tokens'] for c in llm_calls)
    avg_latency = sum(c['latency_ms'] for c in llm_calls) / total_calls if total_calls > 0 else 0
    
    # Success rate
    success_count = sum(1 for c in llm_calls if c.get('success', True))
    success_rate = success_count / total_calls if total_calls > 0 else 1.0
    
    # Unique sessions
    sessions = set(c['session_id'] for c in llm_calls if c.get('session_id'))
    total_sessions = len(sessions)
    avg_cost_per_session = total_cost / total_sessions if total_sessions > 0 else 0
    
    return {
        'kpis': {
            'total_calls': total_calls,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'avg_latency_ms': avg_latency,
            'avg_cost_per_session': avg_cost_per_session,
            'success_rate': success_rate,
            'total_sessions': total_sessions,
        },
        'by_model': aggregate_by_model(llm_calls),
        'by_agent': aggregate_by_agent(llm_calls),
        'by_operation': aggregate_by_operation(llm_calls),
        'cost_breakdown': calculate_cost_breakdown(llm_calls),
        'routing_metrics': calculate_routing_metrics(llm_calls),
        'cache_metrics': calculate_cache_metrics(llm_calls),
        'quality_metrics': calculate_quality_metrics(llm_calls),
    }


@st.cache_data(ttl=60)
def get_comparative_metrics(
    project_name: Optional[str] = None,
    days: Union[int, float] = 7,
    period: Union[str, int, float, None] = None
) -> Dict[str, Any]:
    """
    Get metrics comparison between current and previous period.
    
    Args:
        project_name: Filter by project
        days: Number of days (default 7)
        period: Period string like '1h', '24h', '7d', '30d' (overrides days)
    """
    # Parse period to days
    days_float = parse_period_to_days(period, default=float(days))
    
    now = datetime.utcnow()
    
    # Current period
    current_start = now - timedelta(days=days_float)
    current_calls = get_llm_calls(
        project_name=project_name,
        start_time=current_start,
        end_time=now,
        limit=5000
    )
    
    # Previous period
    previous_start = current_start - timedelta(days=days_float)
    previous_calls = get_llm_calls(
        project_name=project_name,
        start_time=previous_start,
        end_time=current_start,
        limit=5000
    )
    
    def calc_metrics(calls):
        if not calls:
            return {
                'total_calls': 0,
                'total_cost': 0,
                'total_tokens': 0,
                'avg_latency_ms': 0,
                'avg_cost_per_call': 0,
            }
        return {
            'total_calls': len(calls),
            'total_cost': sum(c['total_cost'] for c in calls),
            'total_tokens': sum(c['total_tokens'] for c in calls),
            'avg_latency_ms': sum(c['latency_ms'] for c in calls) / len(calls),
            'avg_cost_per_call': sum(c['total_cost'] for c in calls) / len(calls),
        }
    
    current = calc_metrics(current_calls)
    previous = calc_metrics(previous_calls)
    
    # Calculate trends
    trends = {}
    for key in current:
        if previous[key] > 0:
            change_pct = ((current[key] - previous[key]) / previous[key]) * 100
        else:
            change_pct = 100 if current[key] > 0 else 0
        trends[key] = {
            'current': current[key],
            'previous': previous[key],
            'change_pct': change_pct,
        }
    
    return {
        'current': current,
        'previous': previous,
        'trends': trends,
        'period_days': days_float,
    }


@st.cache_data(ttl=60)
def get_time_series_data(
    project_name: Optional[str] = None,
    days: Union[int, float] = 7,
    period: Union[str, int, float, None] = None,
    granularity: str = 'hour'
) -> Dict[str, Any]:
    """
    Get time series data for charts.
    
    Args:
        project_name: Filter by project
        days: Number of days (default 7)
        period: Period string like '1h', '24h', '7d', '30d' (overrides days)
        granularity: 'hour', 'day', or 'week'
    """
    # Parse period to days
    days_float = parse_period_to_days(period, default=float(days))
    
    start_time = datetime.utcnow() - timedelta(days=days_float)
    calls = get_llm_calls(
        project_name=project_name,
        start_time=start_time,
        limit=10000
    )
    
    if not calls:
        return {
            'timestamps': [],
            'costs': [],
            'calls': [],
            'latencies': [],
            'tokens': [],
        }
    
    # Group by time bucket
    buckets = {}
    for call in calls:
        ts = call['timestamp']
        if not ts:
            continue
        if granularity == 'hour':
            bucket = ts.replace(minute=0, second=0, microsecond=0)
        elif granularity == 'day':
            bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # week
            bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)
            bucket = bucket - timedelta(days=bucket.weekday())
        
        if bucket not in buckets:
            buckets[bucket] = {'cost': 0, 'calls': 0, 'latency_sum': 0, 'tokens': 0}
        
        buckets[bucket]['cost'] += call['total_cost']
        buckets[bucket]['calls'] += 1
        buckets[bucket]['latency_sum'] += call['latency_ms']
        buckets[bucket]['tokens'] += call['total_tokens']
    
    sorted_buckets = sorted(buckets.items())
    
    return {
        'timestamps': [b[0] for b in sorted_buckets],
        'costs': [b[1]['cost'] for b in sorted_buckets],
        'calls': [b[1]['calls'] for b in sorted_buckets],
        'latencies': [b[1]['latency_sum'] / b[1]['calls'] if b[1]['calls'] > 0 else 0 for b in sorted_buckets],
        'tokens': [b[1]['tokens'] for b in sorted_buckets],
    }


@st.cache_data(ttl=60)
def get_routing_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get routing analysis for Model Router page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    routing_metrics = calculate_routing_metrics(llm_calls)
    
    # Get recent routing decisions
    recent_decisions = []
    for call in llm_calls:
        if call.get('routing_decision'):
            rd = call['routing_decision']
            recent_decisions.append({
                'timestamp': call['timestamp'],
                'chosen_model': rd.get('chosen_model'),
                'alternatives': rd.get('alternative_models', []),
                'reasoning': rd.get('reasoning'),
                'complexity_score': rd.get('complexity_score'),
                'cost_savings': rd.get('estimated_cost_savings'),
                'latency_ms': call['latency_ms'],
                'cost': call['total_cost'],
            })
    
    # Sort by timestamp descending
    recent_decisions.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min, reverse=True)
    
    return {
        'metrics': routing_metrics,
        'recent_decisions': recent_decisions[:100],
        'total_routed': len(recent_decisions),
        'total_calls': len(llm_calls),
    }


@st.cache_data(ttl=60)
def get_cache_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get cache analysis for Cache Analyzer page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    cache_metrics = calculate_cache_metrics(llm_calls)
    
    # Analyze cache patterns
    cache_patterns = {}
    for call in llm_calls:
        if call.get('cache_metadata'):
            cm = call['cache_metadata']
            key = cm.get('cache_key', 'unknown')
            if key not in cache_patterns:
                cache_patterns[key] = {'hits': 0, 'misses': 0, 'total_tokens': 0}
            
            if cm.get('cache_hit'):
                cache_patterns[key]['hits'] += 1
            else:
                cache_patterns[key]['misses'] += 1
            cache_patterns[key]['total_tokens'] += call['total_tokens']
    
    return {
        'metrics': cache_metrics,
        'patterns': cache_patterns,
        'total_with_cache': sum(1 for c in llm_calls if c.get('cache_metadata')),
        'total_calls': len(llm_calls),
    }


@st.cache_data(ttl=60)
def get_quality_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get quality analysis for LLM Judge page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    quality_metrics = calculate_quality_metrics(llm_calls)
    
    # Get calls with quality evaluation
    evaluated_calls = [c for c in llm_calls if c.get('quality_evaluation')]
    
    # Sort by score
    evaluated_calls.sort(
        key=lambda x: x['quality_evaluation'].get('judge_score', 0) if x.get('quality_evaluation') else 0,
        reverse=True
    )
    
    best_examples = evaluated_calls[:5]
    worst_examples = evaluated_calls[-5:][::-1] if len(evaluated_calls) >= 5 else []
    
    # Failure reasons breakdown
    failure_reasons = {}
    for call in evaluated_calls:
        qe = call.get('quality_evaluation', {})
        reason = qe.get('failure_reason')
        if reason:
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    
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
        'total_evaluated': len(evaluated_calls),
        'total_calls': len(llm_calls),
    }


@st.cache_data(ttl=60)
def get_prompt_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """Get prompt analysis for Prompt Optimizer page."""
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    if not llm_calls:
        return {
            'total_calls': 0,
            'calls_with_breakdown': 0,
            'token_stats': {
                'avg_system_tokens': 0,
                'avg_history_tokens': 0,
                'avg_user_tokens': 0,
                'avg_total_prompt_tokens': 0,
            },
            'long_prompt_count': 0,
            'by_operation': {},
        }
    
    # Analyze calls with prompt breakdown
    calls_with_breakdown = [c for c in llm_calls if c.get('prompt_breakdown')]
    
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
            }
        by_operation[op]['count'] += 1
        by_operation[op]['total_prompt_tokens'] += call['prompt_tokens']
        if call.get('prompt_breakdown'):
            by_operation[op]['has_breakdown'] += 1
    
    # Calculate averages
    for op in by_operation:
        by_operation[op]['avg_prompt_tokens'] = (
            by_operation[op]['total_prompt_tokens'] / by_operation[op]['count']
        )
    
    return {
        'total_calls': len(llm_calls),
        'calls_with_breakdown': len(calls_with_breakdown),
        'token_stats': token_stats,
        'long_prompt_count': len(long_prompts),
        'by_operation': by_operation,
    }


# =============================================================================
# COST ANALYSIS
# =============================================================================

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    sessions = get_sessions(limit=10000)
    llm_calls = get_llm_calls(limit=10000)
    
    import os
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