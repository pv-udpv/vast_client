"""Dependency injection context for tracking capabilities."""

from typing import Any, TypeVar
from dataclasses import dataclass, field
import httpx
from structlog import BoundLogger

T = TypeVar('T')

@dataclass
class TrackingContext:
    """Context container for dependency injection into capabilities.

    Provides centralized dependency management for Trackable capabilities.
    All dependencies are optional and can be injected at runtime.
    """

    # Core dependencies
    logger: BoundLogger | None = None
    http_client: httpx.AsyncClient | None = None
    metrics_client: Any | None = None  # Prometheus/StatsD client

    # Configuration
    timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 1.0

    # Custom dependencies (extensible)
    _custom: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get custom dependency by key.

        Args:
            key: Dependency key
            default: Default value if key not found

        Returns:
            Dependency value or default
        """
        return self._custom.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set custom dependency.

        Args:
            key: Dependency key
            value: Dependency value
        """
        self._custom[key] = value

    def merge(self, **kwargs) -> "TrackingContext":
        """Create new context with merged values.

        Args:
            **kwargs: Values to merge

        Returns:
            New TrackingContext with merged values
        """
        from copy import deepcopy
        new_ctx = deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_ctx, key):
                setattr(new_ctx, key, value)
            else:
                new_ctx._custom[key] = value
        return new_ctx

    def has_dependency(self, key: str) -> bool:
        """Check if dependency is available.

        Args:
            key: Dependency key

        Returns:
            True if dependency exists
        """
        if hasattr(self, key):
            return getattr(self, key) is not None
        return key in self._custom

class ContextProvider:
    """Global dependency injection container for tracking capabilities.

    Singleton pattern for global context management.
    """

    _instance: "ContextProvider | None" = None
    _context: TrackingContext | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, context: TrackingContext) -> None:
        """Initialize global context.

        Args:
            context: TrackingContext to set as global
        """
        provider = cls()
        provider._context = context

    @classmethod
    def get_context(cls) -> TrackingContext:
        """Get current global context.

        Returns:
            Current TrackingContext or new default if none set
        """
        provider = cls()
        if provider._context is None:
            # Lazy initialization with defaults
            provider._context = TrackingContext()
        return provider._context

    @classmethod
    def reset(cls) -> None:
        """Reset context (useful for testing)."""
        provider = cls()
        provider._context = None

# Global helper functions

def get_tracking_context() -> TrackingContext:
    """Get global tracking context.

    Returns:
        Current global TrackingContext
    """
    return ContextProvider.get_context()

def set_tracking_context(context: TrackingContext) -> None:
    """Set global tracking context.

    Args:
        context: TrackingContext to set as global
    """
    ContextProvider.initialize(context)

def reset_tracking_context() -> None:
    """Reset global tracking context."""
    ContextProvider.reset()

__all__ = [
    "TrackingContext",
    "ContextProvider",
    "get_tracking_context",
    "set_tracking_context",
    "reset_tracking_context",
]
