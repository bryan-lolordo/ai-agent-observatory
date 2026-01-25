"""
Formatting utilities for MCP tools.

Provides consistent formatting for costs, responses, and strings.
"""

from typing import Any


def format_cost(cost: float, precision: int = 4) -> float:
    """
    Round cost to consistent precision.

    Args:
        cost: Cost value in dollars
        precision: Decimal places (default 4)

    Returns:
        Rounded cost value
    """
    return round(cost, precision)


def format_percentage(value: float, total: float) -> float:
    """
    Calculate and format percentage.

    Args:
        value: The part
        total: The whole

    Returns:
        Percentage rounded to 2 decimal places, or 0 if total is 0
    """
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


def truncate_string(s: str, max_length: int = 80, suffix: str = "...") -> str:
    """
    Truncate string to max length with suffix.

    Args:
        s: String to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Truncated string or original if short enough
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_response(
    data: dict[str, Any],
    message: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Wrap response data in consistent format.

    Args:
        data: Response data
        message: Optional success message
        error: Optional error message

    Returns:
        Formatted response dict
    """
    if error:
        return {"error": error, **data}

    response = {**data}
    if message:
        response["message"] = message

    return response


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is 0.

    Args:
        numerator: Top of fraction
        denominator: Bottom of fraction
        default: Value to return if denominator is 0

    Returns:
        Division result or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def aggregate_by_key(items: list, key_func: callable, value_func: callable) -> dict:
    """
    Aggregate items by a key function.

    Args:
        items: List of items to aggregate
        key_func: Function to extract key from item
        value_func: Function to extract value from item

    Returns:
        Dict of key -> sum of values

    Example:
        >>> calls = [{"model": "gpt-4", "cost": 0.1}, {"model": "gpt-4", "cost": 0.2}]
        >>> aggregate_by_key(calls, lambda c: c["model"], lambda c: c["cost"])
        {"gpt-4": 0.3}
    """
    result: dict = {}
    for item in items:
        key = key_func(item)
        value = value_func(item)
        result[key] = result.get(key, 0) + value
    return result
