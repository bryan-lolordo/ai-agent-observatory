# observatory/resilience.py
"""
Circuit Breaker implementation for Observatory components.

Prevents cascading failures by fast-failing when downstream services
(LLM providers, database) are unhealthy.

States:
- CLOSED: Normal operation, requests flow through
- OPEN: Failing, fast-fail all requests (return fallback immediately)
- HALF_OPEN: Testing recovery with limited requests

Configuration via environment variables:
- CB_ENABLED: Enable/disable circuit breaker (default: true)
- CB_FAILURE_THRESHOLD: Failures before opening (default: 5)
- CB_RECOVERY_TIMEOUT: Seconds before half-open (default: 30)
- CB_SUCCESS_THRESHOLD: Successes to close (default: 2)

Usage:
    from observatory.resilience import CircuitBreaker, CircuitBreakerConfig

    cb = CircuitBreaker(name="database", config=CircuitBreakerConfig())

    # As decorator
    @cb.protect
    def save_to_database(data):
        db.save(data)

    # As context manager
    with cb.call() as allowed:
        if allowed:
            db.save(data)

    # Manual check
    if cb.allow_request():
        try:
            result = external_call()
            cb.record_success()
        except Exception as e:
            cb.record_failure(e)
"""

import os
import time
import logging
import threading
from enum import Enum
from typing import Callable, TypeVar, Optional, Any, Generator
from dataclasses import dataclass, field
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 30.0      # Seconds before trying half-open
    success_threshold: int = 2          # Successes needed to close from half-open
    enabled: bool = True                # Enable/disable circuit breaker

    @classmethod
    def from_env(cls, prefix: str = "CB") -> "CircuitBreakerConfig":
        """Create config from environment variables."""
        return cls(
            failure_threshold=int(os.getenv(f"{prefix}_FAILURE_THRESHOLD", "5")),
            recovery_timeout=float(os.getenv(f"{prefix}_RECOVERY_TIMEOUT", "30")),
            success_threshold=int(os.getenv(f"{prefix}_SUCCESS_THRESHOLD", "2")),
            enabled=os.getenv(f"{prefix}_ENABLED", "true").lower() == "true",
        )


@dataclass
class CircuitBreakerStats:
    """Runtime statistics for a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    total_failures: int = 0
    total_successes: int = 0
    total_rejections: int = 0


class CircuitOpenError(Exception):
    """Raised when a request is rejected due to open circuit."""

    def __init__(self, name: str, message: str = None):
        self.name = name
        self.message = message or f"Circuit breaker '{name}' is open"
        super().__init__(self.message)


class CircuitBreaker:
    """
    Thread-safe circuit breaker for protecting external calls.

    Implements the circuit breaker pattern to prevent cascading failures
    when external services (database, LLM providers) are unhealthy.

    Usage:
        cb = CircuitBreaker(name="database")

        # As decorator
        @cb.protect
        def save_to_database(data):
            db.save(data)

        # As context manager
        with cb.call() as allowed:
            if allowed:
                db.save(data)

        # Manual usage
        if cb.allow_request():
            try:
                result = external_call()
                cb.record_success()
            except Exception as e:
                cb.record_failure(e)
                raise
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (e.g., "database", "llm_provider")
            config: Configuration options (uses defaults if not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig.from_env()
        self._stats = CircuitBreakerStats()
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic transitions."""
        with self._lock:
            self._check_state_transition()
            return self._stats.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN

    def _check_state_transition(self) -> None:
        """Check if we should automatically transition from OPEN to HALF_OPEN."""
        if self._stats.state == CircuitState.OPEN:
            time_since_failure = time.time() - (self._stats.last_failure_time or 0)
            if time_since_failure >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._stats.state
        self._stats.state = new_state
        self._stats.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self._stats.failure_count = 0
            self._stats.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._stats.success_count = 0

        logger.info(
            f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}"
        )

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._stats.total_successes += 1

            if self._stats.state == CircuitState.HALF_OPEN:
                self._stats.success_count += 1
                if self._stats.success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            elif self._stats.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._stats.failure_count = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed call."""
        with self._lock:
            self._stats.total_failures += 1
            self._stats.failure_count += 1
            self._stats.last_failure_time = time.time()

            if self._stats.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                self._transition_to(CircuitState.OPEN)
            elif self._stats.state == CircuitState.CLOSED:
                if self._stats.failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            if error:
                logger.warning(
                    f"Circuit breaker '{self.name}' recorded failure: {error}"
                )

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed through.

        Returns:
            True if request should proceed, False if it should be rejected
        """
        if not self.config.enabled:
            return True

        with self._lock:
            self._check_state_transition()

            if self._stats.state == CircuitState.CLOSED:
                return True
            elif self._stats.state == CircuitState.OPEN:
                self._stats.total_rejections += 1
                return False
            else:  # HALF_OPEN
                return True  # Allow limited requests to test recovery

    def protect(
        self,
        func: Callable[..., T] = None,
        fallback: Callable[..., T] = None,
    ) -> Callable[..., T]:
        """
        Decorator to protect a function with the circuit breaker.

        Args:
            func: Function to wrap
            fallback: Optional fallback function to call when circuit is open

        Usage:
            @cb.protect
            def risky_call():
                return external_service.call()

            @cb.protect(fallback=lambda: "default")
            def risky_call_with_fallback():
                return external_service.call()
        """
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            @wraps(fn)
            def wrapper(*args, **kwargs) -> T:
                if not self.allow_request():
                    if fallback:
                        logger.debug(
                            f"Circuit '{self.name}' open, using fallback for {fn.__name__}"
                        )
                        return fallback(*args, **kwargs)
                    raise CircuitOpenError(self.name)

                try:
                    result = fn(*args, **kwargs)
                    self.record_success()
                    return result
                except Exception as e:
                    self.record_failure(e)
                    raise

            return wrapper

        if func is not None:
            return decorator(func)
        return decorator

    @contextmanager
    def call(self) -> Generator[bool, None, None]:
        """
        Context manager for circuit breaker.

        Yields True if call is allowed, False if circuit is open.
        Automatically records success on normal exit, failure on exception.

        Usage:
            with cb.call() as allowed:
                if allowed:
                    result = external_call()
                else:
                    result = fallback_value
        """
        allowed = self.allow_request()
        try:
            yield allowed
            if allowed:
                self.record_success()
        except Exception as e:
            if allowed:
                self.record_failure(e)
            raise

    def get_stats(self) -> dict:
        """Get current circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._stats.state.value,
                "failure_count": self._stats.failure_count,
                "success_count": self._stats.success_count,
                "total_failures": self._stats.total_failures,
                "total_successes": self._stats.total_successes,
                "total_rejections": self._stats.total_rejections,
                "last_failure_time": self._stats.last_failure_time,
                "last_state_change": self._stats.last_state_change,
                "enabled": self.config.enabled,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                },
            }

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self._transition_to(CircuitState.CLOSED)
            self._stats.failure_count = 0
            self._stats.success_count = 0


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_circuit_breaker(
    name: str,
    failure_threshold: int = None,
    recovery_timeout: float = None,
    success_threshold: int = None,
    enabled: bool = None,
) -> CircuitBreaker:
    """
    Create a circuit breaker with optional overrides.

    Uses environment variables for defaults, with explicit parameters taking precedence.

    Args:
        name: Circuit breaker identifier
        failure_threshold: Override for failure threshold
        recovery_timeout: Override for recovery timeout
        success_threshold: Override for success threshold
        enabled: Override for enabled state

    Returns:
        Configured CircuitBreaker instance
    """
    config = CircuitBreakerConfig.from_env()

    if failure_threshold is not None:
        config.failure_threshold = failure_threshold
    if recovery_timeout is not None:
        config.recovery_timeout = recovery_timeout
    if success_threshold is not None:
        config.success_threshold = success_threshold
    if enabled is not None:
        config.enabled = enabled

    return CircuitBreaker(name=name, config=config)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitBreaker",
    "CircuitOpenError",
    "create_circuit_breaker",
]
