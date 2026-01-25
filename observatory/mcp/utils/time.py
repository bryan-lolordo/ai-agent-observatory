"""
Time utilities for MCP tools.

Centralizes time range parsing and duration formatting
to avoid duplication across tool modules.
"""

from datetime import datetime, timedelta


def parse_time_range(time_range: str) -> datetime | None:
    """
    Convert time range string to datetime cutoff.

    Supports multiple formats:
    - Relative: "1h", "24h", "7d", "30d", "90d", "all"
    - ISO date: "2024-01-15" (from that date)
    - Custom days: "14d", "60d" (any number + d)
    - Custom hours: "6h", "12h" (any number + h)

    Args:
        time_range: Time range specification

    Returns:
        datetime cutoff or None for "all"

    Examples:
        >>> parse_time_range("24h")         # 24 hours ago
        >>> parse_time_range("7d")          # 7 days ago
        >>> parse_time_range("2024-01-15")  # From Jan 15, 2024
        >>> parse_time_range("14d")         # 14 days ago
        >>> parse_time_range("all")         # None (no cutoff)
    """
    now = datetime.utcnow()

    # Handle "all" - no cutoff
    if time_range == "all":
        return None

    # Handle custom days format (e.g., "14d", "60d")
    if time_range.endswith("d") and time_range[:-1].isdigit():
        days = int(time_range[:-1])
        return now - timedelta(days=days)

    # Handle custom hours format (e.g., "6h", "12h")
    if time_range.endswith("h") and time_range[:-1].isdigit():
        hours = int(time_range[:-1])
        return now - timedelta(hours=hours)

    # Handle ISO date format (YYYY-MM-DD)
    if len(time_range) == 10 and time_range[4] == "-" and time_range[7] == "-":
        try:
            return datetime.fromisoformat(time_range)
        except ValueError:
            pass

    # Handle ISO datetime format (YYYY-MM-DDTHH:MM:SS)
    if "T" in time_range:
        try:
            return datetime.fromisoformat(time_range.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Default to 7 days for unknown values
    return now - timedelta(days=7)


def parse_date_range(date_range: str) -> tuple[datetime | None, datetime | None]:
    """
    Parse a date range string into start and end datetimes.

    Args:
        date_range: Either a single date/range or "start:end" format
                   Examples: "7d", "2024-01-15", "2024-01-01:2024-01-31"

    Returns:
        Tuple of (start_time, end_time). end_time is None for open-ended ranges.

    Examples:
        >>> parse_date_range("7d")                      # (7 days ago, None)
        >>> parse_date_range("2024-01-15")              # (Jan 15, None)
        >>> parse_date_range("2024-01-01:2024-01-31")   # (Jan 1, Jan 31)
    """
    if ":" in date_range and len(date_range) > 15:  # Likely a date:date range
        parts = date_range.split(":")
        if len(parts) == 2:
            start = parse_time_range(parts[0])
            # For end date, parse and set to end of day
            try:
                end = datetime.fromisoformat(parts[1])
                end = end.replace(hour=23, minute=59, second=59)
            except ValueError:
                end = None
            return (start, end)

    # Single value - just a start time, no end
    return (parse_time_range(date_range), None)


def format_duration(seconds: float) -> str:
    """
    Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable string like "5m 30s" or "2h 15m"

    Examples:
        >>> format_duration(45)      # "45s"
        >>> format_duration(150)     # "2m 30s"
        >>> format_duration(3700)    # "1h 1m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def get_today_start() -> datetime:
    """Get the start of the current UTC day."""
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def get_period_label(time_range: str) -> str:
    """
    Get human-readable label for a time range.

    Args:
        time_range: Time range code

    Returns:
        Human-readable label
    """
    labels = {
        "1h": "last hour",
        "24h": "last 24 hours",
        "7d": "last 7 days",
        "30d": "last 30 days",
        "90d": "last 90 days",
        "all": "all time",
    }
    return labels.get(time_range, time_range)
