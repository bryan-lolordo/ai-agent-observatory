"""
Formatting Utilities
Location: api/utils/formatters.py

Consistent formatting functions for displaying metrics across the dashboard.
"""

from typing import Optional


def format_cost(cost: float, precision: int = 4) -> str:
    """
    Format cost in USD with appropriate precision.
    
    Args:
        cost: Cost value in USD
        precision: Number of decimal places (default 4 for small costs)
    
    Returns:
        Formatted cost string like "$0.0042" or "$12.34"
    """
    if cost < 0.01:
        return f"${cost:.{precision}f}"
    elif cost < 1:
        return f"${cost:.3f}"
    elif cost < 1000:
        return f"${cost:.2f}"
    else:
        return f"${cost:,.2f}"


def format_latency(latency_ms: float) -> str:
    """
    Format latency with appropriate units (ms or s).
    
    Args:
        latency_ms: Latency in milliseconds
    
    Returns:
        Formatted latency string like "450ms" or "1.2s"
    """
    if latency_ms < 1000:
        return f"{latency_ms:.0f}ms"
    else:
        return f"{latency_ms / 1000:.1f}s"


def format_tokens(tokens: int) -> str:
    """
    Format token count with K/M suffix for large numbers.
    
    Args:
        tokens: Number of tokens
    
    Returns:
        Formatted token string like "1,234 tokens" or "12.4K tokens"
    """
    if tokens < 10000:
        return f"{tokens:,} tokens"
    elif tokens < 1000000:
        return f"{tokens / 1000:.1f}K tokens"
    else:
        return f"{tokens / 1000000:.2f}M tokens"


def format_percentage(value: float, precision: int = 1) -> str:
    """
    Format decimal as percentage.
    
    Args:
        value: Decimal value (0.0 to 1.0)
        precision: Number of decimal places
    
    Returns:
        Formatted percentage string like "23.5%"
    """
    return f"{value * 100:.{precision}f}%"


def format_ratio(prompt_tokens: int, completion_tokens: int) -> str:
    """
    Format token ratio as X:1 format.
    
    Args:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
    
    Returns:
        Formatted ratio string like "28:1" or "3.2:1"
    """
    if completion_tokens == 0:
        return "∞:1"
    
    ratio = prompt_tokens / completion_tokens
    
    if ratio >= 10:
        return f"{ratio:.0f}:1"
    else:
        return f"{ratio:.1f}:1"


def format_trend(current: float, previous: float, is_cost: bool = False) -> tuple[str, str]:
    """
    Format trend comparison with arrow and color.
    
    Args:
        current: Current value
        previous: Previous value to compare against
        is_cost: If True, decreasing is good (green). If False, increasing is good.
    
    Returns:
        Tuple of (trend_text, color) like ("↑ 12.3%", "green")
    """
    if previous == 0:
        return ("N/A", "gray")
    
    change = ((current - previous) / previous) * 100
    
    if abs(change) < 0.1:
        return ("→ 0.0%", "gray")
    
    arrow = "↑" if change > 0 else "↓"
    trend_text = f"{arrow} {abs(change):.1f}%"
    
    # Determine color based on whether increase/decrease is good
    if is_cost:
        # For costs, decreasing is good
        color = "green" if change < 0 else "red"
    else:
        # For performance metrics, increasing is good
        color = "green" if change > 0 else "red"
    
    return (trend_text, color)


def format_number(value: float, precision: int = 1) -> str:
    """
    Format large numbers with K/M/B suffix.
    
    Args:
        value: Numeric value
        precision: Number of decimal places
    
    Returns:
        Formatted number string like "1.2K" or "3.4M"
    """
    if value < 1000:
        return f"{value:.{precision}f}"
    elif value < 1000000:
        return f"{value / 1000:.{precision}f}K"
    elif value < 1000000000:
        return f"{value / 1000000:.{precision}f}M"
    else:
        return f"{value / 1000000000:.{precision}f}B"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration like "2m 30s" or "1h 15m"
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_score(score: float, max_score: float = 10.0) -> str:
    """
    Format quality/judge score with context.
    
    Args:
        score: Score value
        max_score: Maximum possible score (default 10.0)
    
    Returns:
        Formatted score like "8.5/10"
    """
    return f"{score:.1f}/{max_score}"


def format_rate(numerator: int, denominator: int) -> str:
    """
    Format rate as fraction and percentage.
    
    Args:
        numerator: Count of successful/hit events
        denominator: Total count
    
    Returns:
        Formatted rate like "45/100 (45.0%)"
    """
    if denominator == 0:
        return "0/0 (N/A)"
    
    percentage = (numerator / denominator) * 100
    return f"{numerator}/{denominator} ({percentage:.1f}%)"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated (default "...")
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_model_name(model_name: str) -> str:
    """
    Format model name for display (shorten common prefixes).
    
    Args:
        model_name: Full model name
    
    Returns:
        Shortened model name
    """
    # Common model name mappings
    mappings = {
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-4o": "GPT-4o",
        "gpt-4": "GPT-4",
        "gpt-3.5-turbo": "GPT-3.5",
        "claude-3-5-sonnet": "Claude 3.5 Sonnet",
        "claude-3-sonnet": "Claude 3 Sonnet",
        "claude-3-opus": "Claude 3 Opus",
        "claude-3-haiku": "Claude 3 Haiku",
        "mistral-small": "Mistral Small",
        "mistral-medium": "Mistral Medium",
        "mistral-large": "Mistral Large",
    }
    
    # Check for partial matches
    for key, display_name in mappings.items():
        if key in model_name.lower():
            return display_name
    
    # Default: capitalize and clean
    return model_name.replace("-", " ").title()


def format_relative_time(timestamp) -> str:
    """
    Format timestamp as relative time (e.g., '2 hours ago').
    
    Args:
        timestamp: datetime object or ISO string
    
    Returns:
        Formatted relative time string like "2 hours ago" or "just now"
    """
    from datetime import datetime, timezone
    
    # Handle string timestamps
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return "unknown"
    
    # Make timezone-aware if needed
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m ago" if minutes > 1 else "1m ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h ago" if hours > 1 else "1h ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days}d ago" if days > 1 else "1d ago"
    else:
        weeks = int(seconds // 604800)
        return f"{weeks}w ago" if weeks > 1 else "1w ago"