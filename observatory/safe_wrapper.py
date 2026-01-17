# observatory/safe_wrapper.py
"""
Graceful degradation wrappers for Observatory components.

Philosophy: Observatory is observability tooling - it should NEVER
crash the host application. All failures are logged and operations
continue with degraded functionality.

Usage:
    from observatory.safe_wrapper import safe_call, safe_method, SafeObservatoryWrapper

    # Wrap individual calls
    result = safe_call(
        storage.save_llm_call,
        llm_call,
        default=None,
        operation_name="save_llm_call"
    )

    # Decorator for methods
    class MyStorage:
        @safe_method(default=None)
        def save(self, data):
            ...

    # Wrap entire Observatory instance
    obs = Observatory(project_name="my_app")
    safe_obs = SafeObservatoryWrapper(obs)
    safe_obs.record_call(...)  # Never raises
"""

import logging
import functools
from typing import Callable, TypeVar, Any, Optional, Set

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_call(
    func: Callable[..., T],
    *args,
    default: T = None,
    operation_name: str = None,
    log_level: int = logging.WARNING,
    suppress_logging: bool = False,
    **kwargs
) -> T:
    """
    Execute a function safely, returning default on any exception.

    Use this to wrap Observatory operations that shouldn't crash the app.

    Args:
        func: Function to call
        *args: Arguments to pass to function
        default: Value to return if function raises
        operation_name: Name for logging (defaults to function name)
        log_level: Logging level for errors (default: WARNING)
        suppress_logging: If True, don't log errors
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result or default value

    Example:
        result = safe_call(
            storage.save_llm_call,
            llm_call,
            default=None,
            operation_name="save_llm_call"
        )
    """
    op_name = operation_name or getattr(func, '__name__', 'unknown')
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if not suppress_logging:
            logger.log(
                log_level,
                f"Observatory {op_name} failed (continuing gracefully): {e}"
            )
        return default


def safe_method(
    default: Any = None,
    operation_name: str = None,
    log_level: int = logging.WARNING,
    suppress_logging: bool = False,
):
    """
    Decorator for methods that should fail gracefully.

    Wraps a method so that any exception returns the default value
    instead of propagating to the caller.

    Args:
        default: Value to return on exception
        operation_name: Name for logging (defaults to method name)
        log_level: Logging level for errors
        suppress_logging: If True, don't log errors

    Example:
        class Storage:
            @safe_method(default=None)
            def save_llm_call(self, llm_call):
                # This won't crash the app if it fails
                self.db.save(llm_call)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return safe_call(
                func, *args, **kwargs,
                default=default,
                operation_name=operation_name or func.__name__,
                log_level=log_level,
                suppress_logging=suppress_logging,
            )
        return wrapper
    return decorator


class SafeObservatoryWrapper:
    """
    Wraps an Observatory instance with graceful degradation.

    All method calls are wrapped to catch exceptions and continue.
    The wrapped Observatory will never crash the host application.

    Usage:
        obs = Observatory(project_name="my_app")
        safe_obs = SafeObservatoryWrapper(obs)

        # This will never raise, even if storage fails
        safe_obs.record_call(model="gpt-4", tokens=100, latency=500)

        # Check health
        if safe_obs.is_degraded():
            logger.warning(f"Degraded components: {safe_obs.get_degraded_components()}")
    """

    def __init__(
        self,
        observatory,
        enabled: bool = True,
        log_level: int = logging.WARNING,
    ):
        """
        Initialize the safe wrapper.

        Args:
            observatory: Observatory instance to wrap
            enabled: If False, all operations become no-ops
            log_level: Logging level for errors
        """
        self._obs = observatory
        self._enabled = enabled
        self._log_level = log_level
        self._degraded_components: Set[str] = set()
        self._error_counts: dict = {}

    @property
    def enabled(self) -> bool:
        """Check if Observatory is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable/disable Observatory."""
        self._enabled = value

    def record_call(self, **kwargs):
        """Safely record an LLM call."""
        if not self._enabled:
            return None
        return safe_call(
            self._obs.record_call, **kwargs,
            default=None,
            operation_name="record_call",
            log_level=self._log_level,
        )

    def start_session(self, **kwargs):
        """Safely start a session."""
        if not self._enabled:
            return None
        return safe_call(
            self._obs.start_session, **kwargs,
            default=None,
            operation_name="start_session",
            log_level=self._log_level,
        )

    def end_session(self, session=None, **kwargs):
        """Safely end a session."""
        if not self._enabled:
            return session
        return safe_call(
            self._obs.end_session, session, **kwargs,
            default=session,
            operation_name="end_session",
            log_level=self._log_level,
        )

    @property
    def storage(self):
        """Access storage (may be None if unavailable)."""
        return getattr(self._obs, 'storage', None)

    @property
    def collector(self):
        """Access the underlying collector."""
        return getattr(self._obs, 'collector', None)

    def mark_degraded(self, component: str, error: Exception = None) -> None:
        """
        Mark a component as degraded.

        Args:
            component: Component name (e.g., "storage", "cache", "judge")
            error: Optional error that caused degradation
        """
        self._degraded_components.add(component)
        self._error_counts[component] = self._error_counts.get(component, 0) + 1

        logger.warning(
            f"Observatory component '{component}' marked as degraded"
            + (f": {error}" if error else "")
        )

    def mark_healthy(self, component: str) -> None:
        """
        Mark a component as healthy (remove from degraded set).

        Args:
            component: Component name
        """
        self._degraded_components.discard(component)
        logger.info(f"Observatory component '{component}' recovered")

    def is_degraded(self, component: str = None) -> bool:
        """
        Check if a component (or any component) is degraded.

        Args:
            component: Specific component to check, or None for any

        Returns:
            True if specified component (or any) is degraded
        """
        if component:
            return component in self._degraded_components
        return len(self._degraded_components) > 0

    def get_degraded_components(self) -> Set[str]:
        """Get set of degraded component names."""
        return self._degraded_components.copy()

    def get_error_counts(self) -> dict:
        """Get error counts per component."""
        return self._error_counts.copy()

    def reset_error_counts(self) -> None:
        """Reset all error counts."""
        self._error_counts.clear()

    def __getattr__(self, name: str):
        """
        Proxy attribute access to wrapped Observatory.

        This allows the wrapper to be used as a drop-in replacement.
        """
        if name.startswith('_'):
            raise AttributeError(name)

        attr = getattr(self._obs, name, None)
        if attr is None:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Wrap callable attributes
        if callable(attr):
            @functools.wraps(attr)
            def safe_wrapper(*args, **kwargs):
                if not self._enabled:
                    return None
                return safe_call(
                    attr, *args, **kwargs,
                    default=None,
                    operation_name=name,
                    log_level=self._log_level,
                )
            return safe_wrapper

        return attr


def with_graceful_degradation(
    component_name: str,
    default: Any = None,
    log_level: int = logging.WARNING,
):
    """
    Class decorator to add graceful degradation to all public methods.

    Wraps all non-private methods of a class to catch exceptions
    and return default values.

    Args:
        component_name: Name for logging purposes
        default: Default return value for failed methods
        log_level: Logging level for errors

    Example:
        @with_graceful_degradation("cache")
        class CacheManager:
            def get(self, key):
                return self._storage.get(key)

            def set(self, key, value):
                self._storage.set(key, value)
    """
    def class_decorator(cls):
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._component_name = component_name
            self._is_degraded = False

        cls.__init__ = new_init

        # Wrap all public methods
        for name in list(vars(cls).keys()):
            if name.startswith('_'):
                continue

            attr = getattr(cls, name)
            if callable(attr) and not isinstance(attr, type):
                wrapped = safe_method(
                    default=default,
                    operation_name=f"{component_name}.{name}",
                    log_level=log_level,
                )(attr)
                setattr(cls, name, wrapped)

        return cls

    return class_decorator


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "safe_call",
    "safe_method",
    "SafeObservatoryWrapper",
    "with_graceful_degradation",
]
