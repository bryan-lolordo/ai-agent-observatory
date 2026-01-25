"""
Shared utilities for MCP tools and resources.

- time: Time range parsing and manipulation
- formatting: Response formatting helpers
- calculations: Reusable calculation functions
- validation: Input validation
- errors: Error handling and responses
"""

from observatory.mcp.utils.time import parse_time_range, parse_date_range, format_duration, get_today_start, get_period_label
from observatory.mcp.utils.formatting import format_cost, format_percentage, format_response, truncate_string, safe_divide, aggregate_by_key
from observatory.mcp.utils.calculations import (
    estimate_routing_savings,
    estimate_cache_savings,
    estimate_token_savings,
    calculate_hit_rate,
    calculate_change_percent,
    calculate_percentile,
    group_by,
    aggregate_metrics,
    top_n,
    bucket_values,
)
from observatory.mcp.utils.validation import (
    ValidationError,
    validate_time_range,
    validate_positive_int,
    validate_non_negative_float,
    validate_enum,
    validate_string,
    validate_list,
)
from observatory.mcp.utils.errors import (
    MCPError,
    StorageError,
    ConfigurationError,
    QueryError,
    DataNotFoundError,
    error_response,
    success_response,
    handle_tool_errors,
    require_storage,
    tool_handler,
)

__all__ = [
    # Time utilities
    "parse_time_range",
    "parse_date_range",
    "format_duration",
    "get_today_start",
    "get_period_label",
    # Formatting utilities
    "format_cost",
    "format_percentage",
    "format_response",
    "truncate_string",
    "safe_divide",
    "aggregate_by_key",
    # Calculation utilities
    "estimate_routing_savings",
    "estimate_cache_savings",
    "estimate_token_savings",
    "calculate_hit_rate",
    "calculate_change_percent",
    "calculate_percentile",
    "group_by",
    "aggregate_metrics",
    "top_n",
    "bucket_values",
    # Validation utilities
    "ValidationError",
    "validate_time_range",
    "validate_positive_int",
    "validate_non_negative_float",
    "validate_enum",
    "validate_string",
    "validate_list",
    # Error handling
    "MCPError",
    "StorageError",
    "ConfigurationError",
    "QueryError",
    "DataNotFoundError",
    "error_response",
    "success_response",
    "handle_tool_errors",
    "require_storage",
    "tool_handler",
]
