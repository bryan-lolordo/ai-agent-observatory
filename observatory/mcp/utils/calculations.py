"""
Calculation utilities for MCP tools.

Provides reusable calculation functions for:
- Savings estimation
- Metrics aggregation
- Statistical calculations
"""

from typing import Any, Callable
from collections import defaultdict


def estimate_routing_savings(
    current_cost: float,
    savings_factor: float = 0.7,
) -> float:
    """
    Estimate savings from routing to a cheaper model.

    Args:
        current_cost: Current cost for the calls
        savings_factor: Expected cost reduction (0.7 = 70% savings)

    Returns:
        Estimated savings in dollars
    """
    return round(current_cost * savings_factor, 4)


def estimate_cache_savings(
    total_cost: float,
    call_count: int,
) -> float:
    """
    Estimate savings from caching duplicate calls.

    First call populates cache, rest are free.

    Args:
        total_cost: Total cost of all calls
        call_count: Number of duplicate calls

    Returns:
        Estimated savings (cost of all but first call)
    """
    if call_count <= 1:
        return 0.0
    return round(total_cost * ((call_count - 1) / call_count), 4)


def estimate_token_savings(
    total_cost: float,
    reduction_factor: float = 0.2,
) -> float:
    """
    Estimate savings from token reduction.

    Args:
        total_cost: Current total cost
        reduction_factor: Expected reduction (0.2 = 20% savings)

    Returns:
        Estimated savings in dollars
    """
    return round(total_cost * reduction_factor, 4)


def calculate_hit_rate(hits: int, total: int) -> float:
    """
    Calculate hit rate as percentage.

    Args:
        hits: Number of hits
        total: Total attempts

    Returns:
        Hit rate as percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)


def calculate_change_percent(
    old_value: float,
    new_value: float,
) -> float:
    """
    Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value

    Returns:
        Percentage change (positive = increase, negative = decrease)
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else 100.0
    return round(((new_value - old_value) / old_value) * 100, 2)


def calculate_percentile(values: list[float], percentile: float) -> float:
    """
    Calculate a percentile from a list of values.

    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)

    Returns:
        Value at the specified percentile
    """
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * (percentile / 100))
    index = min(index, len(sorted_values) - 1)
    return sorted_values[index]


def group_by(
    items: list[Any],
    key_func: Callable[[Any], str],
) -> dict[str, list[Any]]:
    """
    Group items by a key function.

    Args:
        items: List of items to group
        key_func: Function to extract group key from item

    Returns:
        Dict mapping keys to lists of items
    """
    groups: dict[str, list] = defaultdict(list)
    for item in items:
        key = key_func(item)
        groups[key].append(item)
    return dict(groups)


def aggregate_metrics(
    items: list[Any],
    key_func: Callable[[Any], str],
    metrics: dict[str, Callable[[Any], float]],
) -> dict[str, dict[str, float]]:
    """
    Aggregate multiple metrics grouped by a key.

    Args:
        items: List of items to aggregate
        key_func: Function to extract group key
        metrics: Dict of metric_name -> extraction function

    Returns:
        Dict mapping keys to dicts of aggregated metrics

    Example:
        >>> aggregate_metrics(
        ...     calls,
        ...     key_func=lambda c: c.model_name,
        ...     metrics={
        ...         "total_cost": lambda c: c.total_cost or 0,
        ...         "call_count": lambda c: 1,
        ...     }
        ... )
        {"gpt-4": {"total_cost": 1.23, "call_count": 15}, ...}
    """
    result: dict[str, dict[str, float]] = defaultdict(lambda: {m: 0.0 for m in metrics})

    for item in items:
        key = key_func(item)
        for metric_name, extract_func in metrics.items():
            result[key][metric_name] += extract_func(item)

    return dict(result)


def top_n(
    items: dict[str, Any],
    value_func: Callable[[Any], float],
    n: int = 5,
    reverse: bool = True,
) -> list[tuple[str, Any]]:
    """
    Get top N items from a dict by a value function.

    Args:
        items: Dict of key -> value
        value_func: Function to extract sort value
        n: Number of items to return
        reverse: True for descending (top), False for ascending (bottom)

    Returns:
        List of (key, value) tuples
    """
    sorted_items = sorted(items.items(), key=lambda x: value_func(x[1]), reverse=reverse)
    return sorted_items[:n]


def bucket_values(
    values: list[float],
    buckets: list[tuple[str, float, float]],
) -> dict[str, int]:
    """
    Distribute values into named buckets.

    Args:
        values: List of values to bucket
        buckets: List of (name, min, max) tuples defining buckets

    Returns:
        Dict of bucket_name -> count

    Example:
        >>> bucket_values(
        ...     [1.0, 2.5, 4.0, 4.8],
        ...     [("low", 0, 2), ("medium", 2, 4), ("high", 4, 5)]
        ... )
        {"low": 1, "medium": 1, "high": 2}
    """
    result = {name: 0 for name, _, _ in buckets}

    for value in values:
        for name, min_val, max_val in buckets:
            if min_val <= value < max_val:
                result[name] += 1
                break
        else:
            # Value doesn't fit any bucket - put in last one if >= max
            if buckets and value >= buckets[-1][2]:
                result[buckets[-1][0]] += 1

    return result
