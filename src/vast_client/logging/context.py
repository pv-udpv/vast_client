"""Logging context management with request IDs and hierarchical tracking."""

import contextlib
import contextvars
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

import structlog


# Context variables for async propagation
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "span_id", default=None
)
_parent_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parent_id", default=None
)
_operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "operation", default=None
)


def _generate_id() -> str:
    """Generate a unique ID for request/span tracking.

    Returns:
        12-character hexadecimal ID
    """
    return secrets.token_hex(6)


@dataclass
class LoggingContext:
    """Logging context with request IDs and hierarchical tracking.

    Provides request correlation, parent-child relationships, and namespace grouping
    for structured logging. Context is automatically propagated across async calls
    via contextvars.

    Example:
        ```python
        async def track_event():
            with LoggingContext(operation="track_event", event_type="impression") as ctx:
                logger.info("event.start", **ctx.to_log_dict())

                # Nested operation inherits request_id
                with LoggingContext(parent_id=ctx.span_id, operation="send_trackable"):
                    logger.debug("trackable.send", **ctx.to_log_dict())
        ```
    """

    # Core IDs
    request_id: str | None = None
    span_id: str | None = None
    parent_id: str | None = None

    # Operation metadata
    operation: str | None = None

    # Namespace-grouped context (aggregation)
    # Note: renamed from "event" to "vast_event" to avoid conflicts with structlog's "event" parameter
    vast_event: dict[str, Any] = field(default_factory=dict)
    trackable: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)

    # Custom namespaces (extensible)
    _custom_namespaces: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Internal state
    _start_time: float = field(default_factory=time.time)
    _token_request_id: contextvars.Token | None = field(default=None, init=False, repr=False)
    _token_span_id: contextvars.Token | None = field(default=None, init=False, repr=False)
    _token_parent_id: contextvars.Token | None = field(default=None, init=False, repr=False)
    _token_operation: contextvars.Token | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize IDs if not provided."""
        # Generate request_id if not provided (root context)
        if self.request_id is None:
            # Try to inherit from parent context
            parent_request_id = _request_id_var.get()
            if parent_request_id:
                self.request_id = parent_request_id
            else:
                # Root context - generate new request_id
                self.request_id = _generate_id()

        # Generate span_id if not provided
        if self.span_id is None:
            self.span_id = _generate_id()

        # Inherit parent_id from context if not explicitly provided
        if self.parent_id is None:
            # Try to inherit from parent span
            parent_span_id = _span_id_var.get()
            if parent_span_id:
                self.parent_id = parent_span_id

    def __enter__(self) -> "LoggingContext":
        """Enter context and bind to contextvars."""
        # Set contextvars for async propagation
        self._token_request_id = _request_id_var.set(self.request_id)
        self._token_span_id = _span_id_var.set(self.span_id)
        self._token_parent_id = _parent_id_var.set(self.parent_id)
        self._token_operation = _operation_var.set(self.operation)

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(
            request_id=self.request_id,
            span_id=self.span_id,
            parent_id=self.parent_id,
            operation=self.operation,
        )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and unbind from contextvars."""
        # Restore previous contextvar values
        if self._token_request_id:
            _request_id_var.reset(self._token_request_id)
        if self._token_span_id:
            _span_id_var.reset(self._token_span_id)
        if self._token_parent_id:
            _parent_id_var.reset(self._token_parent_id)
        if self._token_operation:
            _operation_var.reset(self._token_operation)

        # Unbind from structlog context
        structlog.contextvars.unbind_contextvars(
            "request_id", "span_id", "parent_id", "operation"
        )

    async def __aenter__(self) -> "LoggingContext":
        """Async context manager entry."""
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.__exit__(exc_type, exc_val, exc_tb)

    def to_log_dict(self, include_namespaces: bool = True) -> dict[str, Any]:
        """Convert context to dictionary for logging.

        Args:
            include_namespaces: Whether to include namespace groups (vast_event, trackable, result)

        Returns:
            Dictionary with context fields suitable for structured logging
        """
        log_dict: dict[str, Any] = {
            "request_id": self.request_id,
            "span_id": self.span_id,
        }

        # Add parent_id only if present (not root context)
        if self.parent_id:
            log_dict["parent_id"] = self.parent_id

        # Add operation if present
        if self.operation:
            log_dict["operation"] = self.operation

        # Add namespace-grouped fields
        if include_namespaces:
            if self.vast_event:
                log_dict["vast_event"] = self.vast_event
            if self.trackable:
                log_dict["trackable"] = self.trackable
            if self.result:
                log_dict["result"] = self.result

            # Add custom namespaces
            for namespace, fields in self._custom_namespaces.items():
                if fields:
                    log_dict[namespace] = fields

        return log_dict

    def set_namespace(self, namespace: str, **fields: Any) -> None:
        """Set fields in a custom namespace.

        Args:
            namespace: Namespace name (e.g., "http", "player", "config")
            **fields: Key-value pairs to set in the namespace
        """
        if namespace in ("vast_event", "trackable", "result"):
            # Use built-in namespaces
            getattr(self, namespace).update(fields)
        else:
            # Use custom namespace
            if namespace not in self._custom_namespaces:
                self._custom_namespaces[namespace] = {}
            self._custom_namespaces[namespace].update(fields)

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        """Get fields from a namespace.

        Args:
            namespace: Namespace name

        Returns:
            Dictionary of fields in the namespace
        """
        if namespace in ("vast_event", "trackable", "result"):
            return dict(getattr(self, namespace))
        return self._custom_namespaces.get(namespace, {})

    def get_duration(self) -> float:
        """Get elapsed time since context creation.

        Returns:
            Duration in seconds
        """
        return time.time() - self._start_time


def get_current_context() -> LoggingContext | None:
    """Get current logging context from contextvars.

    Returns:
        Current LoggingContext if in a context, None otherwise
    """
    request_id = _request_id_var.get()
    if request_id is None:
        return None

    # Reconstruct context from contextvars
    return LoggingContext(
        request_id=request_id,
        span_id=_span_id_var.get(),
        parent_id=_parent_id_var.get(),
        operation=_operation_var.get(),
    )


def clear_context() -> None:
    """Clear all logging context from contextvars.

    Useful for testing or explicit context cleanup.
    """
    _request_id_var.set(None)
    _span_id_var.set(None)
    _parent_id_var.set(None)
    _operation_var.set(None)

    # Also clear from structlog
    with contextlib.suppress(KeyError):
        structlog.contextvars.unbind_contextvars(
            "request_id", "span_id", "parent_id", "operation"
        )


__all__ = [
    "LoggingContext",
    "get_current_context",
    "clear_context",
]
