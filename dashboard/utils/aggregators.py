"""
Data Aggregation Utilities
Location: dashboard/utils/aggregators.py

Functions for aggregating and calculating metrics from raw data.
"""

import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from observatory.models import Session


def calculate_percentile(values: List[float], percentile: int) -> float:
    """
    Calculate percentile from list of values.
    
    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)
    
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    return float(np.percentile(values, percentile))


def aggregate_by_model(llm_calls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate metrics grouped by model.
    
    Args:
        llm_calls: List of LLM call dictionaries
    
    Returns:
        Dictionary mapping model_name to aggregated metrics
    """
    model_data = defaultdict(lambda: {
        'count': 0,
        'total_cost': 0.0,
        'total_tokens': 0,
        'total_latency_ms': 0.0,
        'latencies': [],
        'costs': []
    })
    
    for call in llm_calls:
        data = model_data[call['model_name']]
        data['count'] += 1
        data['total_cost'] += call['total_cost']
        data['total_tokens'] += call['total_tokens']
        data['total_latency_ms'] += call['latency_ms']
        data['latencies'].append(call['latency_ms'])
        data['costs'].append(call['total_cost'])
    
    # Calculate averages
    result = {}
    for model, data in model_data.items():
        result[model] = {
            'count': data['count'],
            'total_cost': data['total_cost'],
            'avg_cost': data['total_cost'] / data['count'],
            'total_tokens': data['total_tokens'],
            'avg_tokens': data['total_tokens'] / data['count'],
            'avg_latency_ms': data['total_latency_ms'] / data['count'],
            'p50_latency_ms': calculate_percentile(data['latencies'], 50),
            'p95_latency_ms': calculate_percentile(data['latencies'], 95),
        }
    
    return result


def aggregate_by_agent(llm_calls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate metrics grouped by agent.
    
    Args:
        llm_calls: List of LLM call dictionaries
    
    Returns:
        Dictionary mapping agent_name to aggregated metrics
    """
    agent_data = defaultdict(lambda: {
        'count': 0,
        'total_cost': 0.0,
        'total_tokens': 0,
        'total_latency_ms': 0.0,
        'models_used': set(),
        'operations': defaultdict(int)
    })
    
    for call in llm_calls:
        agent_name = call.get('agent_name') or "Unknown"
        data = agent_data[agent_name]
        data['count'] += 1
        data['total_cost'] += call['total_cost']
        data['total_tokens'] += call['total_tokens']
        data['total_latency_ms'] += call['latency_ms']
        data['models_used'].add(call['model_name'])
        operation = call.get('operation')
        if operation:
            data['operations'][operation] += 1
    
    # Calculate averages and convert sets to lists
    result = {}
    for agent, data in agent_data.items():
        result[agent] = {
            'count': data['count'],
            'total_cost': data['total_cost'],
            'avg_cost': data['total_cost'] / data['count'],
            'total_tokens': data['total_tokens'],
            'avg_tokens': data['total_tokens'] / data['count'],
            'avg_latency_ms': data['total_latency_ms'] / data['count'],
            'models_used': list(data['models_used']),
            'operations': dict(data['operations'])
        }
    
    return result


def aggregate_by_operation(llm_calls: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate metrics grouped by operation type.
    
    Args:
        llm_calls: List of LLM call dictionaries
    
    Returns:
        Dictionary mapping operation to aggregated metrics
    """
    op_data = defaultdict(lambda: {
        'count': 0,
        'total_cost': 0.0,
        'total_tokens': 0,
        'total_latency_ms': 0.0,
    })
    
    for call in llm_calls:
        operation = call.get('operation') or "Unknown"
        data = op_data[operation]
        data['count'] += 1
        data['total_cost'] += call['total_cost']
        data['total_tokens'] += call['total_tokens']
        data['total_latency_ms'] += call['latency_ms']
    
    # Calculate averages
    result = {}
    for operation, data in op_data.items():
        result[operation] = {
            'count': data['count'],
            'total_cost': data['total_cost'],
            'avg_cost': data['total_cost'] / data['count'],
            'avg_latency_ms': data['total_latency_ms'] / data['count'],
        }
    
    return result


def calculate_cost_breakdown(llm_calls: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate cost breakdown by model.
    
    Args:
        llm_calls: List of LLM call dictionaries
    
    Returns:
        Dictionary mapping model_name to total cost
    """
    breakdown = defaultdict(float)
    for call in llm_calls:
        breakdown[call['model_name']] += call['total_cost']
    return dict(breakdown)


def calculate_routing_metrics(llm_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate routing effectiveness metrics.
    
    Args:
        llm_calls: List of LLM call dictionaries with routing data
    
    Returns:
        Dictionary of routing metrics
    """
    calls_with_routing = [c for c in llm_calls if c.get('routing_decision') is not None]
    
    if not calls_with_routing:
        return {
            'total_decisions': 0,
            'total_savings': 0.0,
            'avg_savings_per_decision': 0.0,
            'model_distribution': {},
            'complexity_scores': []
        }
    
    total_savings = sum(
        c['routing_decision'].get('estimated_cost_savings', 0.0) or 0.0
        for c in calls_with_routing
    )
    
    model_distribution = defaultdict(int)
    complexity_scores = []
    
    for call in calls_with_routing:
        routing = call['routing_decision']
        model_distribution[routing['chosen_model']] += 1
        complexity = routing.get('complexity_score')
        if complexity is not None:
            complexity_scores.append(complexity)
    
    return {
        'total_decisions': len(calls_with_routing),
        'total_savings': total_savings,
        'avg_savings_per_decision': total_savings / len(calls_with_routing),
        'model_distribution': dict(model_distribution),
        'complexity_scores': complexity_scores,
        'avg_complexity': np.mean(complexity_scores) if complexity_scores else None
    }


def calculate_cache_metrics(llm_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate cache performance metrics.
    
    Args:
        llm_calls: List of LLM call dictionaries with cache data
    
    Returns:
        Dictionary of cache metrics
    """
    calls_with_cache = [c for c in llm_calls if c.get('cache_metadata') is not None]
    
    if not calls_with_cache:
        return {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'hit_rate': 0.0,
            'tokens_saved': 0,
            'cost_saved': 0.0,
            'clusters': set()
        }
    
    hits = sum(1 for c in calls_with_cache if c['cache_metadata'].get('cache_hit'))
    misses = len(calls_with_cache) - hits
    
    # Estimate savings (tokens not processed on cache hits)
    tokens_saved = sum(
        c['total_tokens'] for c in calls_with_cache 
        if c['cache_metadata'].get('cache_hit')
    )
    cost_saved = sum(
        c['total_cost'] for c in calls_with_cache 
        if c['cache_metadata'].get('cache_hit')
    )
    
    clusters = {
        c['cache_metadata'].get('cache_cluster_id')
        for c in calls_with_cache 
        if c['cache_metadata'].get('cache_cluster_id')
    }
    
    return {
        'total_requests': len(calls_with_cache),
        'cache_hits': hits,
        'cache_misses': misses,
        'hit_rate': hits / len(calls_with_cache) if calls_with_cache else 0.0,
        'tokens_saved': tokens_saved,
        'cost_saved': cost_saved,
        'cluster_count': len(clusters)
    }


def calculate_quality_metrics(llm_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate quality/judge metrics.
    
    Args:
        llm_calls: List of LLM call dictionaries with quality evaluations
    
    Returns:
        Dictionary of quality metrics
    """
    calls_with_quality = [c for c in llm_calls if c.get('quality_evaluation') is not None]
    
    if not calls_with_quality:
        return {
            'total_evaluated': 0,
            'avg_judge_score': None,
            'hallucinations': 0,
            'hallucination_rate': 0.0,
            'scores': []
        }
    
    scores = [
        c['quality_evaluation']['judge_score']
        for c in calls_with_quality 
        if c['quality_evaluation'].get('judge_score') is not None
    ]
    
    hallucinations = sum(
        1 for c in calls_with_quality 
        if c['quality_evaluation'].get('hallucination_flag')
    )
    
    return {
        'total_evaluated': len(calls_with_quality),
        'avg_judge_score': np.mean(scores) if scores else None,
        'min_score': min(scores) if scores else None,
        'max_score': max(scores) if scores else None,
        'p50_score': calculate_percentile(scores, 50) if scores else None,
        'hallucinations': hallucinations,
        'hallucination_rate': hallucinations / len(calls_with_quality),
        'scores': scores
    }


def calculate_time_series(
    llm_calls: List[Dict[str, Any]],
    metric: str = 'cost',
    interval: str = 'hour'
) -> Dict[datetime, float]:
    """
    Calculate time series data for a metric.
    
    Args:
        llm_calls: List of LLM call dictionaries
        metric: Metric to track ('cost', 'tokens', 'latency', 'count')
        interval: Time interval ('hour', 'day', 'minute')
    
    Returns:
        Dictionary mapping timestamp to metric value
    """
    if not llm_calls:
        return {}
    
    # Determine time bucket function
    if interval == 'minute':
        bucket_fn = lambda dt: dt.replace(second=0, microsecond=0)
    elif interval == 'hour':
        bucket_fn = lambda dt: dt.replace(minute=0, second=0, microsecond=0)
    elif interval == 'day':
        bucket_fn = lambda dt: dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Invalid interval: {interval}")
    
    # Aggregate by time bucket
    time_data = defaultdict(lambda: {'cost': 0.0, 'tokens': 0, 'latency': 0.0, 'count': 0})
    
    for call in llm_calls:
        bucket = bucket_fn(call['timestamp'])
        time_data[bucket]['cost'] += call['total_cost']
        time_data[bucket]['tokens'] += call['total_tokens']
        time_data[bucket]['latency'] += call['latency_ms']
        time_data[bucket]['count'] += 1
    
    # Extract requested metric
    result = {}
    for bucket, data in sorted(time_data.items()):
        if metric == 'count':
            result[bucket] = data['count']
        elif metric == 'avg_latency':
            result[bucket] = data['latency'] / data['count']
        else:
            result[bucket] = data[metric]
    
    return result


def calculate_session_kpis(sessions: List[Session]) -> Dict[str, Any]:
    """
    Calculate high-level KPIs from sessions.
    
    Args:
        sessions: List of sessions
    
    Returns:
        Dictionary of KPI metrics
    """
    if not sessions:
        return {
            'total_sessions': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'total_calls': 0,
            'avg_cost_per_session': 0.0,
            'avg_latency_ms': 0.0,
            'success_rate': 0.0
        }
    
    total_cost = sum(s.total_cost for s in sessions)
    total_tokens = sum(s.total_tokens for s in sessions)
    total_calls = sum(s.total_llm_calls for s in sessions)
    total_latency = sum(s.total_latency_ms for s in sessions)
    successful = sum(1 for s in sessions if s.success)
    
    return {
        'total_sessions': len(sessions),
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'total_calls': total_calls,
        'avg_cost_per_session': total_cost / len(sessions),
        'avg_tokens_per_session': total_tokens / len(sessions),
        'avg_calls_per_session': total_calls / len(sessions),
        'avg_latency_ms': total_latency / total_calls if total_calls > 0 else 0.0,
        'success_rate': successful / len(sessions)
    }


def group_by_time_period(
    sessions: List[Session],
    period: str = '24h'
) -> Dict[str, List[Session]]:
    """
    Group sessions by time period.
    
    Args:
        sessions: List of sessions
        period: Time period ('1h', '24h', '7d', '30d')
    
    Returns:
        Dictionary with 'current' and 'previous' session lists
    """
    if not sessions:
        return {'current': [], 'previous': []}
    
    now = datetime.utcnow()
    
    # Parse period
    if period.endswith('h'):
        hours = int(period[:-1])
        delta = timedelta(hours=hours)
    elif period.endswith('d'):
        days = int(period[:-1])
        delta = timedelta(days=days)
    else:
        raise ValueError(f"Invalid period: {period}")
    
    cutoff = now - delta
    previous_cutoff = cutoff - delta
    
    current = [s for s in sessions if s.start_time >= cutoff]
    previous = [s for s in sessions if previous_cutoff <= s.start_time < cutoff]
    
    return {'current': current, 'previous': previous}