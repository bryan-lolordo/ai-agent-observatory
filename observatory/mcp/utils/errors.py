"""
Error handling utilities for MCP tools.

Provides consistent error responses and exception handling.
"""

from typing import Any
from functools import wraps
import traceback


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    def __init__(self, message: str, code: str = "MCP_ERROR", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to error response dict."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class StorageError(MCPError):
    """Raised when storage operations fail."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "STORAGE_ERROR", details)


class ConfigurationError(MCPError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "CONFIG_ERROR", details)


class QueryError(MCPError):
    """Raised when query parameters are invalid."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "QUERY_ERROR", details)


class DataNotFoundError(MCPError):
    """Raised when requested data doesn't exist."""

    def __init__(self, resource: str, identifier: str | None = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        super().__init__(message, "NOT_FOUND", details)


def error_response(message: str, code: str = "ERROR", **kwargs) -> dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        message: Error message
        code: Error code
        **kwargs: Additional details to include

    Returns:
        Error response dict
    """
    return {
        "error": True,
        "code": code,
        "message": message,
        **kwargs,
    }


def success_response(data: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Optional success message

    Returns:
        Success response dict with data
    """
    response = {"error": False, **data}
    if message:
        response["message"] = message
    return response


def handle_tool_errors(func):
    """
    Decorator to handle errors in MCP tool functions.

    Catches exceptions and returns standardized error responses
    instead of raising.

    Usage:
        @handle_tool_errors
        async def my_tool(param: str, storage=None) -> dict:
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            return e.to_dict()
        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR")
        except Exception as e:
            # Log the full traceback for debugging
            tb = traceback.format_exc()
            return error_response(
                f"Internal error: {str(e)}",
                "INTERNAL_ERROR",
                traceback=tb if __debug__ else None,
            )

    return wrapper


def require_storage(func):
    """
    Decorator to validate storage is provided.

    Returns a standard error if storage is None.

    Usage:
        @require_storage
        async def my_tool(param: str, storage=None) -> dict:
            # storage is guaranteed to be not None here
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        storage = kwargs.get("storage")
        if storage is None:
            return error_response(
                "Storage not configured",
                "STORAGE_NOT_CONFIGURED",
                hint="Ensure the MCP server is properly initialized with storage",
            )
        return await func(*args, **kwargs)

    return wrapper


def combine_decorators(*decorators):
    """
    Combine multiple decorators into one.

    Usage:
        @combine_decorators(handle_tool_errors, require_storage)
        async def my_tool(...):
            ...
    """
    def combined(func):
        for decorator in reversed(decorators):
            func = decorator(func)
        return func
    return combined


# Convenience decorator combining common patterns
def tool_handler(func):
    """
    Standard decorator for MCP tool handlers.

    Combines error handling and storage validation.

    Usage:
        @tool_handler
        async def my_tool(param: str, storage=None) -> dict:
            ...
    """
    return handle_tool_errors(require_storage(func))
