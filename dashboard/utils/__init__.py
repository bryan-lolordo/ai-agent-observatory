"""
Dashboard Utilities Package
Location: dashboard/utils/__init__.py

Centralized utilities for data fetching, formatting, and aggregation.
"""

from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_trend,
    format_number,
    format_duration,
    format_score,
    format_rate,
    truncate_text,
    format_model_name
)

from dashboard.utils.aggregators import (
    calculate_percentile,
    aggregate_by_model,
    aggregate_by_agent,
    aggregate_by_operation,
    calculate_cost_breakdown,
    calculate_routing_metrics,
    calculate_cache_metrics,
    calculate_quality_metrics,
    calculate_time_series,
    calculate_session_kpis,
    group_by_time_period
)

from dashboard.utils.data_fetcher import (
    get_storage,
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_sessions,
    get_llm_calls,
    get_project_overview,
    get_time_series_data,
    get_comparative_metrics,
    get_routing_analysis,
    get_cache_analysis,
    get_quality_analysis,
    get_cost_forecast
)

__all__ = [
    # Formatters
    'format_cost',
    'format_latency',
    'format_tokens',
    'format_percentage',
    'format_trend',
    'format_number',
    'format_duration',
    'format_score',
    'format_rate',
    'truncate_text',
    'format_model_name',
    
    # Aggregators
    'calculate_percentile',
    'aggregate_by_model',
    'aggregate_by_agent',
    'aggregate_by_operation',
    'calculate_cost_breakdown',
    'calculate_routing_metrics',
    'calculate_cache_metrics',
    'calculate_quality_metrics',
    'calculate_time_series',
    'calculate_session_kpis',
    'group_by_time_period',
    
    # Data Fetchers
    'get_storage',
    'get_available_projects',
    'get_available_models',
    'get_available_agents',
    'get_sessions',
    'get_llm_calls',
    'get_project_overview',
    'get_time_series_data',
    'get_comparative_metrics',
    'get_routing_analysis',
    'get_cache_analysis',
    'get_quality_analysis',
    'get_cost_forecast',
]