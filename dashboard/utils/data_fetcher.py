"""
Data Fetcher - Centralized Data Access Layer
Location: dashboard/utils/data_fetcher.py

All database queries and data retrieval functions.
Pages should use these functions instead of querying storage directly.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
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


@st.cache_resource
def get_storage() -> Storage:
    """
    Get cached Storage instance.
    
    Returns:
        Storage instance connected to database
    """
    import os
    # Get database path from environment or use default
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    return Storage(database_url=db_path)


@st.cache_data(ttl=30)
def get_available_projects() -> List[str]:
    """
    Get list of all projects in database.
    
    Returns:
        Sorted list of project names
    """
    storage = get_storage()
    return storage.get_distinct_projects()


@st.cache_data(ttl=30)
def get_available_models(project_name: Optional[str] = None) -> List[str]:
    """
    Get list of all models, optionally filtered by project.
    
    Args:
        project_name: Optional project filter
    
    Returns:
        Sorted list of model names
    """
    storage = get_storage()
    return storage.get_distinct_models(project_name=project_name)


@st.cache_data(ttl=30)
def get_available_agents(project_name: Optional[str] = None) -> List[str]:
    """
    Get list of all agents, optionally filtered by project.
    
    Args:
        project_name: Optional project filter
    
    Returns:
        Sorted list of agent names
    """
    storage = get_storage()
    return storage.get_distinct_agents(project_name=project_name)


@st.cache_data(ttl=30)
def get_sessions(
    project_name: Optional[str] = None,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[Session]:
    """
    Get sessions with optional filters.
    
    Args:
        project_name: Filter by project (None for all projects)
        limit: Maximum number of sessions to return
        start_time: Filter sessions after this time
        end_time: Filter sessions before this time
    
    Returns:
        List of Session objects
    """
    storage = get_storage()
    return storage.get_sessions(
        project_name=project_name,
        limit=limit,
        start_time=start_time,
        end_time=end_time
    )


@st.cache_data(ttl=30)
def get_llm_calls(
    project_name: Optional[str] = None,
    session_id: Optional[str] = None,
    model_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get LLM calls with optional filters.
    
    Args:
        project_name: Filter by project
        session_id: Filter by specific session
        model_name: Filter by model
        agent_name: Filter by agent
        limit: Maximum number of calls to return
    
    Returns:
        List of LLMCall objects converted to dictionaries
    """
    storage = get_storage()
    calls = storage.get_llm_calls(
        project_name=project_name,
        session_id=session_id,
        model_name=model_name,
        agent_name=agent_name,
        limit=limit
    )
    
    # Convert Pydantic models to dicts
    return [_llm_call_to_dict(call) for call in calls]


def _llm_call_to_dict(call: LLMCall) -> Dict[str, Any]:
    """Convert LLMCall Pydantic model to dictionary."""
    data = {
        'id': call.id,
        'session_id': call.session_id,
        'timestamp': call.timestamp,
        'agent_name': call.agent_name,
        'operation': call.operation,
        'provider': call.provider.value if call.provider else None,
        'model_name': call.model_name,
        'prompt_tokens': call.prompt_tokens,
        'completion_tokens': call.completion_tokens,
        'total_tokens': call.total_tokens,
        'latency_ms': call.latency_ms,
        'total_cost': call.total_cost,
        'prompt': call.prompt,
        'response_text': call.response_text,
        'error': call.error,
    }
    
    # Convert nested Pydantic models
    if call.routing_decision:
        data['routing_decision'] = {
            'chosen_model': call.routing_decision.chosen_model,
            'alternative_models': call.routing_decision.alternative_models,
            'model_scores': call.routing_decision.model_scores,
            'reasoning': call.routing_decision.reasoning,
            'rule_triggered': call.routing_decision.rule_triggered,  # ✅ ADDED
            'complexity_score': call.routing_decision.complexity_score,  # ✅ ADDED
            'estimated_cost_savings': call.routing_decision.estimated_cost_savings,
        }
    else:
        data['routing_decision'] = None
    
    if call.cache_metadata:
        data['cache_metadata'] = {
            'cache_hit': call.cache_metadata.cache_hit,
            'cache_key': call.cache_metadata.cache_key,
            'cache_cluster_id': call.cache_metadata.cache_cluster_id,
        }
    else:
        data['cache_metadata'] = None
    
    if call.quality_evaluation:
        data['quality_evaluation'] = {
            'judge_score': call.quality_evaluation.judge_score,
            'score': call.quality_evaluation.judge_score,  # Alias for compatibility
            'reasoning': call.quality_evaluation.reasoning,
            'hallucination_flag': call.quality_evaluation.hallucination_flag,
            'hallucination': call.quality_evaluation.hallucination_flag,  # Alias
            'confidence_score': call.quality_evaluation.confidence_score,  # ✅ FIXED: was confidence
            'error_category': call.quality_evaluation.error_category,
            'category': call.quality_evaluation.error_category,  # Alias
        }
    else:
        data['quality_evaluation'] = None
    
    return data


@st.cache_data(ttl=60)
def get_project_overview(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get comprehensive overview metrics for a project.
    
    Args:
        project_name: Project to analyze (None for all projects)
    
    Returns:
        Dictionary containing:
        - kpis: High-level KPIs
        - cost_breakdown: Cost by model/agent
        - routing_metrics: Routing performance
        - cache_metrics: Cache performance
        - quality_metrics: Quality scores
    """
    sessions = get_sessions(project_name=project_name, limit=1000)
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    
    # Calculate KPIs
    kpis = calculate_session_kpis(sessions)
    
    # Add routing/cache/quality metrics
    routing_metrics = calculate_routing_metrics(llm_calls)
    cache_metrics = calculate_cache_metrics(llm_calls)
    quality_metrics = calculate_quality_metrics(llm_calls)
    
    # Calculate breakdowns
    by_model = aggregate_by_model(llm_calls)
    by_agent = aggregate_by_agent(llm_calls)
    cost_breakdown = calculate_cost_breakdown(llm_calls)
    
    return {
        'kpis': kpis,
        'routing_metrics': routing_metrics,
        'cache_metrics': cache_metrics,
        'quality_metrics': quality_metrics,
        'by_model': by_model,
        'by_agent': by_agent,
        'cost_breakdown': cost_breakdown,
        'total_sessions': len(sessions),
        'total_calls': len(llm_calls)
    }


@st.cache_data(ttl=60)
def get_time_series_data(
    project_name: Optional[str] = None,
    metric: str = 'cost',
    interval: str = 'hour',
    hours: int = 24
) -> Dict[datetime, float]:
    """
    Get time series data for a metric.
    
    Args:
        project_name: Filter by project
        metric: Metric to track ('cost', 'tokens', 'latency', 'count')
        interval: Time bucket size ('minute', 'hour', 'day')
        hours: Number of hours to look back
    
    Returns:
        Dictionary mapping timestamp to metric value
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    llm_calls = get_llm_calls(project_name=project_name, limit=10000)
    
    # Filter to time range - now using dict access
    recent_calls = [c for c in llm_calls if c['timestamp'] >= start_time]
    
    return calculate_time_series(recent_calls, metric=metric, interval=interval)


@st.cache_data(ttl=60)
def get_comparative_metrics(
    project_name: Optional[str] = None,
    period: str = '24h'
) -> Dict[str, Any]:
    """
    Get current vs previous period comparison metrics.
    
    Args:
        project_name: Filter by project
        period: Time period to compare ('1h', '24h', '7d', '30d')
    
    Returns:
        Dictionary with current and previous metrics plus trends
    """
    sessions = get_sessions(project_name=project_name, limit=2000)
    grouped = group_by_time_period(sessions, period=period)
    
    current_kpis = calculate_session_kpis(grouped['current'])
    previous_kpis = calculate_session_kpis(grouped['previous'])
    
    # Calculate trends
    trends = {}
    for key in ['total_cost', 'total_tokens', 'avg_latency_ms']:
        current = current_kpis.get(key, 0)
        previous = previous_kpis.get(key, 0)
        
        if previous > 0:
            change = ((current - previous) / previous) * 100
            trends[key] = {
                'current': current,
                'previous': previous,
                'change_pct': change
            }
        else:
            trends[key] = {
                'current': current,
                'previous': previous,
                'change_pct': 0.0
            }
    
    return {
        'current': current_kpis,
        'previous': previous_kpis,
        'trends': trends,
        'period': period
    }


@st.cache_data(ttl=60)
def get_routing_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed routing analysis.
    
    Args:
        project_name: Filter by project
    
    Returns:
        Dictionary with routing effectiveness metrics and examples
    """
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    calls_with_routing = [c for c in llm_calls if c.get('routing_decision') is not None]
    
    routing_metrics = calculate_routing_metrics(calls_with_routing)
    by_model = aggregate_by_model(calls_with_routing)
    
    # Get recent routing decisions for examples
    recent_decisions = sorted(
        calls_with_routing,
        key=lambda x: x['timestamp'],
        reverse=True
    )[:20]
    
    return {
        'metrics': routing_metrics,
        'by_model': by_model,
        'recent_decisions': [
            {
                'timestamp': c['timestamp'],
                'chosen_model': c['routing_decision']['chosen_model'],
                'alternatives': c['routing_decision']['alternative_models'],
                'reasoning': c['routing_decision']['reasoning'],
                'savings': c['routing_decision'].get('estimated_cost_savings', 0),
                'cost': c['total_cost'],
                'latency_ms': c['latency_ms']
            }
            for c in recent_decisions
        ]
    }


@st.cache_data(ttl=60)
def get_cache_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed cache analysis.
    
    Args:
        project_name: Filter by project
    
    Returns:
        Dictionary with cache performance metrics
    """
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    calls_with_cache = [c for c in llm_calls if c.get('cache_metadata') is not None]
    
    cache_metrics = calculate_cache_metrics(calls_with_cache)
    
    # Group by cluster
    cluster_stats = {}
    for call in calls_with_cache:
        cache_meta = call['cache_metadata']
        if cache_meta.get('cache_cluster_id'):
            cluster_id = cache_meta['cache_cluster_id']
            if cluster_id not in cluster_stats:
                cluster_stats[cluster_id] = {
                    'hits': 0,
                    'misses': 0,
                    'total_tokens': 0,
                    'total_cost': 0.0
                }
            
            stats = cluster_stats[cluster_id]
            if cache_meta.get('cache_hit'):
                stats['hits'] += 1
            else:
                stats['misses'] += 1
            stats['total_tokens'] += call['total_tokens']
            stats['total_cost'] += call['total_cost']
    
    return {
        'metrics': cache_metrics,
        'cluster_stats': cluster_stats,
        'total_clusters': len(cluster_stats)
    }


@st.cache_data(ttl=60)
def get_quality_analysis(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed quality/judge analysis.
    
    Args:
        project_name: Filter by project
    
    Returns:
        Dictionary with quality metrics and examples
    """
    llm_calls = get_llm_calls(project_name=project_name, limit=5000)
    calls_with_quality = [c for c in llm_calls if c.get('quality_evaluation') is not None]
    
    quality_metrics = calculate_quality_metrics(calls_with_quality)
    
    # Get best and worst examples
    scored_calls = [
        c for c in calls_with_quality 
        if c['quality_evaluation'].get('judge_score') is not None
    ]
    
    best_examples = sorted(
        scored_calls,
        key=lambda x: x['quality_evaluation']['judge_score'],
        reverse=True
    )[:5]
    
    worst_examples = sorted(
        scored_calls,
        key=lambda x: x['quality_evaluation']['judge_score']
    )[:5]
    
    return {
        'metrics': quality_metrics,
        'best_examples': [
            {
                'score': c['quality_evaluation']['judge_score'],
                'model': c['model_name'],
                'agent': c['agent_name'],
                'reasoning': c['quality_evaluation'].get('reasoning'),
                'prompt': c['prompt'][:200] if c.get('prompt') else None,
                'response': c['response_text'][:200] if c.get('response_text') else None
            }
            for c in best_examples
        ],
        'worst_examples': [
            {
                'score': c['quality_evaluation']['judge_score'],
                'model': c['model_name'],
                'agent': c['agent_name'],
                'reasoning': c['quality_evaluation'].get('reasoning'),
                'hallucination': c['quality_evaluation'].get('hallucination_flag'),
                'prompt': c['prompt'][:200] if c.get('prompt') else None,
                'response': c['response_text'][:200] if c.get('response_text') else None
            }
            for c in worst_examples
        ]
    }


@st.cache_data(ttl=60)
def get_cost_forecast(
    project_name: Optional[str] = None,
    requests_per_hour: int = 100,
    avg_prompt_tokens: int = 500,
    avg_completion_tokens: int = 200,
    model_mix: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Forecast costs based on projected usage.
    
    Args:
        project_name: Filter by project for historical data
        requests_per_hour: Projected requests per hour
        avg_prompt_tokens: Average prompt tokens per request
        avg_completion_tokens: Average completion tokens per request
        model_mix: Dictionary mapping model to usage percentage (e.g., {"gpt-4": 0.3, "gpt-3.5": 0.7})
    
    Returns:
        Dictionary with cost forecasts
    """
    # Get historical data for baseline
    llm_calls = get_llm_calls(project_name=project_name, limit=1000)
    
    if llm_calls:
        actual_avg_cost = sum(c['total_cost'] for c in llm_calls) / len(llm_calls)
    else:
        # Rough estimate if no data
        actual_avg_cost = 0.005  # $0.005 per request
    
    # Calculate forecasts
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


@st.cache_data(ttl=60)
def get_database_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    
    Returns:
        Dictionary with database stats
    """
    storage = get_storage()
    sessions = get_sessions(limit=10000)
    llm_calls = get_llm_calls(limit=10000)
    
    import os
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    # Remove sqlite:/// prefix if present
    if db_path.startswith("sqlite:///"):
        file_path = db_path[10:]
    else:
        file_path = "observatory.db"
    
    # Get file size if it exists
    db_size_mb = 0
    if os.path.exists(file_path):
        db_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    return {
        'total_sessions': len(sessions),
        'total_llm_calls': len(llm_calls),
        'database_size_mb': db_size_mb,
        'database_path': file_path,
    }