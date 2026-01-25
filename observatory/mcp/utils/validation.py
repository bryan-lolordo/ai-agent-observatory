"""
Input validation utilities for MCP tools.

Provides consistent validation across all tool parameters.
"""

from typing import Any


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_time_range(value: str) -> str:
    """
    Validate a time range string.

    Accepts:
    - Relative: "1h", "24h", "7d", "30d", "90d", "all"
    - Custom: "14d", "6h" (number + d/h)
    - ISO date: "2024-01-15"
    - ISO datetime: "2024-01-15T10:30:00"
    - Range: "2024-01-01:2024-01-31"

    Returns:
        The validated time range string

    Raises:
        ValidationError: If the format is invalid
    """
    if not value or not isinstance(value, str):
        raise ValidationError("time_range", "Must be a non-empty string")

    value = value.strip()

    # Check for "all"
    if value == "all":
        return value

    # Check for relative format (number + d/h)
    if len(value) >= 2:
        suffix = value[-1]
        prefix = value[:-1]
        if suffix in ("d", "h") and prefix.isdigit():
            return value

    # Check for ISO date format
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        try:
            year, month, day = value.split("-")
            if year.isdigit() and month.isdigit() and day.isdigit():
                return value
        except ValueError:
            pass

    # Check for ISO datetime format
    if "T" in value:
        # Basic check - let parse_time_range handle the actual parsing
        return value

    # Check for date range format
    if ":" in value and len(value) > 15:
        parts = value.split(":")
        if len(parts) == 2:
            # Validate both parts
            validate_time_range(parts[0])
            validate_time_range(parts[1])
            return value

    raise ValidationError(
        "time_range",
        f"Invalid format '{value}'. Use: '7d', '24h', '2024-01-15', or 'all'"
    )


def validate_positive_int(value: Any, field_name: str, max_value: int | None = None) -> int:
    """
    Validate a positive integer.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        max_value: Optional maximum allowed value

    Returns:
        The validated integer

    Raises:
        ValidationError: If validation fails
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(field_name, f"Must be an integer, got {type(value).__name__}")

    if int_value < 1:
        raise ValidationError(field_name, f"Must be positive, got {int_value}")

    if max_value is not None and int_value > max_value:
        raise ValidationError(field_name, f"Must be at most {max_value}, got {int_value}")

    return int_value


def validate_non_negative_float(value: Any, field_name: str) -> float:
    """
    Validate a non-negative float.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated float

    Raises:
        ValidationError: If validation fails
    """
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(field_name, f"Must be a number, got {type(value).__name__}")

    if float_value < 0:
        raise ValidationError(field_name, f"Must be non-negative, got {float_value}")

    return float_value


def validate_enum(value: Any, field_name: str, allowed: list[str]) -> str:
    """
    Validate that a value is one of the allowed options.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        allowed: List of allowed values

    Returns:
        The validated string

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, str):
        raise ValidationError(field_name, f"Must be a string, got {type(value).__name__}")

    if value not in allowed:
        raise ValidationError(
            field_name,
            f"Must be one of {allowed}, got '{value}'"
        )

    return value


def validate_string(
    value: Any,
    field_name: str,
    min_length: int = 0,
    max_length: int | None = None,
    allow_empty: bool = True,
) -> str:
    """
    Validate a string value.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length
        allow_empty: Whether empty strings are allowed

    Returns:
        The validated string

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if allow_empty:
            return ""
        raise ValidationError(field_name, "Cannot be empty")

    if not isinstance(value, str):
        raise ValidationError(field_name, f"Must be a string, got {type(value).__name__}")

    if not allow_empty and len(value) == 0:
        raise ValidationError(field_name, "Cannot be empty")

    if len(value) < min_length:
        raise ValidationError(field_name, f"Must be at least {min_length} characters")

    if max_length is not None and len(value) > max_length:
        raise ValidationError(field_name, f"Must be at most {max_length} characters")

    return value


def validate_list(
    value: Any,
    field_name: str,
    min_items: int = 0,
    max_items: int | None = None,
) -> list:
    """
    Validate a list value.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        min_items: Minimum required items
        max_items: Maximum allowed items

    Returns:
        The validated list

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, list):
        raise ValidationError(field_name, f"Must be a list, got {type(value).__name__}")

    if len(value) < min_items:
        raise ValidationError(field_name, f"Must have at least {min_items} items")

    if max_items is not None and len(value) > max_items:
        raise ValidationError(field_name, f"Must have at most {max_items} items")

    return value
