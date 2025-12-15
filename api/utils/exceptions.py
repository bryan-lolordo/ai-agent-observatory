"""
Custom Exceptions
Location: api/utils/exceptions.py

Custom exception classes for the Observatory API.
Provides clear error messages and proper HTTP status code mapping.
"""

from typing import Optional, Any


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class ObservatoryError(Exception):
    """Base exception for all Observatory errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# =============================================================================
# DATABASE EXCEPTIONS
# =============================================================================

class DatabaseError(ObservatoryError):
    """Base class for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DataNotFoundError(DatabaseError):
    """Raised when requested data doesn't exist."""
    pass


class QueryError(DatabaseError):
    """Raised when database query fails."""
    pass


# =============================================================================
# STORY/ANALYSIS EXCEPTIONS
# =============================================================================

class StoryError(ObservatoryError):
    """Base class for story analysis errors."""
    pass


class StoryNotFoundError(StoryError):
    """Raised when requesting invalid story ID."""
    
    def __init__(self, story_id: str):
        super().__init__(
            message=f"Story '{story_id}' not found",
            details={"story_id": story_id}
        )


class InsufficientDataError(StoryError):
    """Raised when not enough data to perform analysis."""
    
    def __init__(self, story_id: str, min_required: int, actual: int):
        super().__init__(
            message=f"Insufficient data for story '{story_id}': need {min_required}, have {actual}",
            details={
                "story_id": story_id,
                "min_required": min_required,
                "actual": actual
            }
        )


class AnalysisError(StoryError):
    """Raised when story analysis fails."""
    pass


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================

class ValidationError(ObservatoryError):
    """Base class for validation errors."""
    pass


class InvalidParameterError(ValidationError):
    """Raised when API parameter is invalid."""
    
    def __init__(self, param_name: str, param_value: Any, reason: str):
        super().__init__(
            message=f"Invalid parameter '{param_name}': {reason}",
            details={
                "param_name": param_name,
                "param_value": param_value,
                "reason": reason
            }
        )


class InvalidFilterError(ValidationError):
    """Raised when filter parameters are invalid."""
    pass


class InvalidDateRangeError(ValidationError):
    """Raised when date range is invalid (e.g., start > end)."""
    
    def __init__(self, start_date: Any, end_date: Any):
        super().__init__(
            message=f"Invalid date range: start ({start_date}) is after end ({end_date})",
            details={"start_date": start_date, "end_date": end_date}
        )


# =============================================================================
# TRACKING/STORAGE EXCEPTIONS
# =============================================================================

class TrackingError(ObservatoryError):
    """Raised when LLM call tracking fails."""
    pass


class StorageError(ObservatoryError):
    """Raised when saving data to storage fails."""
    pass


# =============================================================================
# CONFIGURATION EXCEPTIONS
# =============================================================================

class ConfigurationError(ObservatoryError):
    """Raised when configuration is invalid or missing."""
    pass


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when required environment variable is missing."""
    
    def __init__(self, var_name: str):
        super().__init__(
            message=f"Required environment variable '{var_name}' is not set",
            details={"var_name": var_name}
        )


# =============================================================================
# HTTP STATUS CODE MAPPING
# =============================================================================

def get_http_status_code(error: Exception) -> int:
    """
    Map exception types to HTTP status codes.
    
    Args:
        error: Exception instance
    
    Returns:
        HTTP status code (400, 404, 500, etc.)
    """
    error_status_map = {
        DataNotFoundError: 404,
        StoryNotFoundError: 404,
        InvalidParameterError: 400,
        InvalidFilterError: 400,
        InvalidDateRangeError: 400,
        ValidationError: 400,
        InsufficientDataError: 422,  # Unprocessable Entity
        DatabaseConnectionError: 503,  # Service Unavailable
        ConfigurationError: 500,
        MissingEnvironmentVariableError: 500,
    }
    
    return error_status_map.get(type(error), 500)