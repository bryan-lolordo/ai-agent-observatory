"""
Utils Module
Location: api/utils/__init__.py

Centralized utilities for the Observatory API.
"""

# Data fetching
from api.utils.data_fetcher import (
    get_storage,
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_available_operations,
    get_sessions,
    get_llm_calls,
    get_conversation,
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

# Aggregation functions
from api.utils.aggregators import (
    aggregate_by_model,
    aggregate_by_agent,
    aggregate_by_operation,
    calculate_cost_breakdown,
    calculate_routing_metrics,
    calculate_cache_metrics,
    calculate_quality_metrics,
    calculate_prompt_breakdown_metrics,
    calculate_time_series,
    calculate_session_kpis,
    group_by_time_period,
    calculate_conversation_metrics,
    calculate_experiment_metrics,
)

# Formatting utilities
from api.utils.formatters import (
    format_cost,
    format_tokens,
    format_latency,
    format_percentage,
    format_timestamp,
    format_duration,
    format_number,
    format_model_name,
    format_ratio,
    format_relative_time,
)

# Exceptions
from api.utils.exceptions import (
    ObservatoryError,
    DatabaseError,
    DatabaseConnectionError,
    DataNotFoundError,
    QueryError,
    StoryError,
    StoryNotFoundError,
    InsufficientDataError,
    AnalysisError,
    ValidationError,
    InvalidParameterError,
    InvalidFilterError,
    InvalidDateRangeError,
    TrackingError,
    StorageError,
    ConfigurationError,
    MissingEnvironmentVariableError,
    get_http_status_code,
)

__all__ = [
    # Data fetching
    'get_storage',
    'get_available_projects',
    'get_available_models',
    'get_available_agents',
    'get_available_operations',
    'get_sessions',
    'get_llm_calls',
    'get_conversation',
    'get_project_overview',
    'get_time_series_data',
    'get_comparative_metrics',
    'get_routing_analysis',
    'get_cache_analysis',
    'get_quality_analysis',
    'get_prompt_analysis',
    'get_cost_forecast',
    'get_database_stats',
    
    # Aggregators
    'aggregate_by_model',
    'aggregate_by_agent',
    'aggregate_by_operation',
    'calculate_cost_breakdown',
    'calculate_routing_metrics',
    'calculate_cache_metrics',
    'calculate_quality_metrics',
    'calculate_prompt_breakdown_metrics',
    'calculate_time_series',
    'calculate_session_kpis',
    'group_by_time_period',
    'calculate_conversation_metrics',
    'calculate_experiment_metrics',
    
    # Formatters
    'format_cost',
    'format_tokens',
    'format_latency',
    'format_percentage',
    'format_timestamp',
    'format_duration',
    'format_number',
    'format_model_name',
    'format_ratio',
    'format_relative_time',
    
    # Exceptions
    'ObservatoryError',
    'DatabaseError',
    'DatabaseConnectionError',
    'DataNotFoundError',
    'QueryError',
    'StoryError',
    'StoryNotFoundError',
    'InsufficientDataError',
    'AnalysisError',
    'ValidationError',
    'InvalidParameterError',
    'InvalidFilterError',
    'InvalidDateRangeError',
    'TrackingError',
    'StorageError',
    'ConfigurationError',
    'MissingEnvironmentVariableError',
    'get_http_status_code',
]