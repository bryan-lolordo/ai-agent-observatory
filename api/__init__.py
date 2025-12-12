"""
API Utilities Package
Location: api/utils/__init__.py

Centralized utilities for data fetching, formatting, and aggregation.
Migrated from dashboard/utils - no Streamlit dependencies.
"""

from api.utils.formatters import (
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

from api.utils.aggregators import (
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
    group_by_time_period,
    calculate_prompt_breakdown_metrics,
)

from api.utils.data_fetcher import (
    get_storage,
    reset_storage,
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_available_operations,
    get_sessions,
    get_llm_calls,
    get_project_overview,
    get_time_series_data,
    get_comparative_metrics,
    get_routing_analysis,
    get_cache_analysis,
    get_quality_analysis,
    get_prompt_analysis,
    get_cost_forecast,
    get_database_stats,
)

from api.utils.story_analyzer import (
    # Individual story analyzers
    analyze_latency_story,
    analyze_cache_story,
    analyze_cost_story,
    analyze_system_prompt_story,
    analyze_token_imbalance_story,
    analyze_routing_story,
    analyze_quality_story,
    
    # Aggregate functions
    analyze_all_stories,
    get_story_summary,
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
    'calculate_prompt_breakdown_metrics',
    
    # Data Fetchers
    'get_storage',
    'reset_storage',
    'get_available_projects',
    'get_available_models',
    'get_available_agents',
    'get_available_operations',
    'get_sessions',
    'get_llm_calls',
    'get_project_overview',
    'get_time_series_data',
    'get_comparative_metrics',
    'get_routing_analysis',
    'get_cache_analysis',
    'get_quality_analysis',
    'get_prompt_analysis',
    'get_cost_forecast',
    'get_database_stats',
    
    # Story Analyzers
    'analyze_latency_story',
    'analyze_cache_story',
    'analyze_cost_story',
    'analyze_system_prompt_story',
    'analyze_token_imbalance_story',
    'analyze_routing_story',
    'analyze_quality_story',
    'analyze_all_stories',
    'get_story_summary',
]