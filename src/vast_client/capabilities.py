"""Capability decorators for composing Trackable functionality."""

import asyncio
from typing import TYPE_CHECKING, TypeVar


if TYPE_CHECKING:
    from .mixins import EventFilterMixin, LoggingMixin, MacroMixin, StateMixin
    from .trackable import TrackableEvent
else:
    # Runtime imports to avoid circular dependencies
    import importlib

    trackable_module = importlib.import_module("ctv_middleware.vast_client.trackable")
    mixins_module = importlib.import_module("ctv_middleware.vast_client.mixins")
    TrackableEvent = trackable_module.TrackableEvent
    MacroMixin = mixins_module.MacroMixin
    StateMixin = mixins_module.StateMixin
    LoggingMixin = mixins_module.LoggingMixin
    EventFilterMixin = mixins_module.EventFilterMixin

T = TypeVar("T")

# Import context for dependency injection
from .context import get_tracking_context


def _add_capability(cls, name: str) -> None:
    """Safely register a capability on the class without triggering static analyzer errors."""
    caps = getattr(cls, "__capabilities__", None)
    if caps is None:
        caps = set()
    if name not in caps:
        caps.add(name)
    cls.__capabilities__ = caps


def with_macros(cls: type[T]) -> type[T]:
    """Add macro processing capability to Trackable class.

    Injects MacroMixin methods: apply_macros, _apply_to_str
    """
    # Inject MacroMixin methods
    for attr in ["apply_macros", "_apply_to_str"]:
        if not hasattr(cls, attr):  # Don't override existing methods
            setattr(cls, attr, getattr(MacroMixin, attr))

    # Mark capability
    _add_capability(cls, "macros")

    return cls


def with_state(cls: type[T]) -> type[T]:
    """Add state management capability to Trackable class.

    Injects StateMixin methods: is_tracked, mark_tracked, mark_failed, etc.
    """
    # Inject StateMixin methods
    state_methods = [
        "is_tracked",
        "mark_tracked",
        "mark_failed",
        "should_retry",
        "get_avg_response_time",
        "get_last_error",
        "reset_state",
    ]

    for attr in state_methods:
        if not hasattr(cls, attr):  # Don't override existing methods
            setattr(cls, attr, getattr(StateMixin, attr))

    # Mark capability
    _add_capability(cls, "state")

    return cls


def with_event_filtering(cls: type[T]) -> type[T]:
    """Add event filtering capability to Trackable class.

    Injects EventFilterMixin methods: set_event_filters, should_log_event,
    filter_events, get_event_filter_stats
    """
    filter_methods = [
        "set_event_filters",
        "should_log_event",
        "filter_events",
        "get_event_filter_stats",
    ]
    for attr in filter_methods:
        if not hasattr(cls, attr):
            setattr(cls, attr, getattr(EventFilterMixin, attr))

    # Initialize default patterns if not present
    if not hasattr(cls, "_event_include_patterns"):
        cls._event_include_patterns = ["*"]
    if not hasattr(cls, "_event_exclude_patterns"):
        cls._event_exclude_patterns = []

    _add_capability(cls, "event_filtering")

    return cls


def with_logging(cls: type[T]) -> type[T]:
    """Add logging capability (with event filtering) to Trackable class.

    Injects LoggingMixin methods: to_log_dict, log_state, log_event
    Also ensures event filtering capability is present.
    """
    # Ensure event filtering first
    cls = with_event_filtering(cls)

    for attr in ["to_log_dict", "log_state", "log_event"]:
        if not hasattr(cls, attr):
            setattr(cls, attr, getattr(LoggingMixin, attr))

    _add_capability(cls, "logging")

    return cls


def with_http_send(cls: type[T]) -> type[T]:
    """Add HTTP send capability to Trackable class.

    Injects send_with method for HTTP requests with context injection support.
    """

    async def send_with(self, client, macros=None, **context):
        """Send tracking request using HTTP client with optional context injection.

        Args:
            client: HTTP client (httpx.AsyncClient)
            macros: Optional macro dictionary for URL substitution
            **context: Additional context for request:
                - headers: dict of headers to add
                - params: dict of query parameters to add
                - timeout: request timeout
                - any other httpx request parameters

        Returns:
            bool: True if successful, False otherwise
        """
        status_code = None
        error_msg = None
        
        try:
            # Get URL from value
            if isinstance(self.value, list):
                url = self.value[0] if self.value else ""
            else:
                url = self.value

            if not url:
                return False

            # Apply macros if capability exists and macros provided
            if macros and "macros" in getattr(self, "__capabilities__", set()):
                url = self.apply_macros(macros, ["[{macro}]", "${{{macro}}}"])
                if isinstance(url, list):
                    url = url[0]

            # Prepare request parameters
            request_kwargs = {}

            # Extract context parameters
            headers = context.get("headers", {})
            params = context.get("params", {})
            timeout = context.get("timeout")

            # Add headers if provided
            if headers:
                request_kwargs["headers"] = headers

            # Add query parameters if provided
            if params:
                request_kwargs["params"] = params

            # Add timeout if provided
            if timeout is not None:
                request_kwargs["timeout"] = timeout

            # Send request with context
            response = await client.get(url, **request_kwargs)
            status_code = response.status_code
            response.raise_for_status()

            # Mark success if state capability exists
            if "state" in getattr(self, "__capabilities__", set()):
                self.mark_tracked()
                self.set_extra("last_status_code", status_code)

            return True

        except Exception as e:
            error_msg = str(e)
            # Extract status code from HTTP error if available
            if hasattr(e, "response") and hasattr(e.response, "status_code"):
                status_code = e.response.status_code
            
            # Mark failure if state capability exists
            if "state" in getattr(self, "__capabilities__", set()):
                self.mark_failed(error_msg)
                if status_code:
                    self.set_extra("last_status_code", status_code)
            return False

    # Inject method
    if not hasattr(cls, "send_with"):  # Don't override existing methods
        cls.send_with = send_with

    # Mark capability
    _add_capability(cls, "http_send")

    return cls


def with_retry_logic(cls: type[T]) -> type[T]:
    """Add retry logic capability to Trackable class.

    Enhances send_with with retry functionality.
    """
    original_send_with = getattr(cls, "send_with", None)

    async def send_with_with_retry(
        self, client, macros=None, max_retries=3, retry_delay=1.0, **context
    ):
        """Send with retry logic and context injection.

        Args:
            client: HTTP client
            macros: Optional macro dictionary
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **context: Additional context for request (headers, params, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                if original_send_with:
                    success = await original_send_with(self, client, macros, **context)
                else:
                    # Fallback to basic send_with from with_http_send
                    async def basic_send_with(obj, client, macros=None, **context):
                        try:
                            # Get URL from value
                            if isinstance(obj.value, list):
                                url = obj.value[0] if obj.value else ""
                            else:
                                url = obj.value

                            if not url:
                                return False

                            # Apply macros if capability exists and macros provided
                            if macros and "macros" in getattr(obj, "__capabilities__", set()):
                                url = obj.apply_macros(macros, ["[{macro}]", "${{{macro}}}"])
                                if isinstance(url, list):
                                    url = url[0]

                            # Prepare request parameters
                            request_kwargs = {}

                            # Extract context parameters
                            headers = context.get("headers", {})
                            params = context.get("params", {})
                            timeout = context.get("timeout")

                            # Add headers if provided
                            if headers:
                                request_kwargs["headers"] = headers

                            # Add query parameters if provided
                            if params:
                                request_kwargs["params"] = params

                            # Add timeout if provided
                            if timeout is not None:
                                request_kwargs["timeout"] = timeout

                            # Send request with context
                            response = await client.get(url, **request_kwargs)
                            response.raise_for_status()

                            # Mark success if state capability exists
                            if "state" in getattr(obj, "__capabilities__", set()):
                                obj.mark_tracked()

                            return True

                        except Exception as e:
                            # Mark failure if state capability exists
                            if "state" in getattr(obj, "__capabilities__", set()):
                                obj.mark_failed(str(e))
                            return False

                    success = await basic_send_with(self, client, macros, **context)

                if success:
                    return True

            except Exception as e:
                # Log retry attempt
                if "logging" in getattr(self, "__capabilities__", set()):
                    self.log_state(f"Retry attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        return False

    # Replace or add method
    cls.send_with = send_with_with_retry

    # Mark capability
    _add_capability(cls, "retry")

    return cls


# Composite decorators for common combinations


def trackable_basic(cls: type[T]) -> type[T]:
    """Apply basic capabilities: macros and state."""
    return with_state(with_macros(cls))


def trackable_standard(cls: type[T]) -> type[T]:
    """Apply standard capabilities: macros, state, logging."""
    return with_logging(with_state(with_macros(cls)))


def trackable_full(cls: type[T]) -> type[T]:
    """Apply all capabilities: macros, state, logging, http_send."""
    return with_http_send(with_logging(with_state(with_macros(cls))))


def trackable_with_retry(cls: type[T]) -> type[T]:
    """Apply full capabilities with retry logic."""
    return with_retry_logic(with_http_send(with_logging(with_state(with_macros(cls)))))


# Context-aware decorators (Dependency Injection)


def with_http_send_contextual(cls: type[T]) -> type[T]:
    """Add HTTP send capability with context injection support.

    Automatically injects:
    - logger from context
    - http_client from context (if not provided)
    - timeout from context (if not provided)
    """

    async def send_with(self, client=None, macros=None, **context):
        """Send with full context injection support."""
        # Get global context
        ctx = get_tracking_context()

        # Use client from parameter or context
        active_client = client or ctx.http_client
        if active_client is None:
            raise ValueError("No HTTP client available (not in params or context)")

        # Merge context: global → local
        timeout = context.get("timeout", ctx.timeout)
        headers = context.get("headers", {})
        params = context.get("params", {})

        # Get logger from context if available
        logger = ctx.logger

        try:
            # Get URL
            if isinstance(self.value, list):
                url = self.value[0] if self.value else ""
            else:
                url = self.value

            if not url:
                return False

            # Apply macros
            if macros and "macros" in getattr(self, "__capabilities__", set()):
                url = self.apply_macros(macros, ["[{macro}]", "${{{macro}}}"])
                if isinstance(url, list):
                    url = url[0]

            # Log if logger available
            if logger:
                logger.debug("Sending tracking request", url=url, trackable_key=self.key)

            # Prepare request
            request_kwargs = {"timeout": timeout}
            if headers:
                request_kwargs["headers"] = headers
            if params:
                request_kwargs["params"] = params

            # Send request
            response = await active_client.get(url, **request_kwargs)
            response.raise_for_status()

            # Mark success
            if "state" in getattr(self, "__capabilities__", set()):
                self.mark_tracked()

            if logger:
                logger.debug("Tracking request successful", url=url, status=response.status_code)

            return True

        except Exception as e:
            if "state" in getattr(self, "__capabilities__", set()):
                self.mark_failed(str(e))

            if logger:
                logger.error("Tracking request failed", url=url, error=str(e))

            return False

    cls.send_with = send_with

    _add_capability(cls, "http_send_contextual")

    return cls


def with_logging_contextual(cls: type[T]) -> type[T]:
    """Add logging capability with context-injected logger and event filtering.

    Automatically uses logger from TrackingContext.
    """
    # Ensure event filtering capability
    cls = with_event_filtering(cls)

    def log_state(self, message: str, level: str = "info"):
        """Log state using context logger."""
        ctx = get_tracking_context()
        logger = ctx.logger

        if logger is None:
            return  # Silent if no logger in context

        log_data = self.to_log_dict() if hasattr(self, "to_log_dict") else {}

        if level == "debug":
            logger.debug(message, **log_data)
        elif level == "info":
            logger.info(message, **log_data)
        elif level == "warning":
            logger.warning(message, **log_data)
        elif level == "error":
            logger.error(message, **log_data)

    cls.log_state_contextual = log_state

    _add_capability(cls, "logging_contextual")

    return cls


def with_metrics_contextual(cls: type[T]) -> type[T]:
    """Add metrics capability with context-injected metrics client.

    NEW CAPABILITY - track metrics via Prometheus/StatsD.
    """

    def record_metric(self, metric_name: str, value: float, tags: dict[str, str] | None = None):
        """Record metric using context metrics client."""
        ctx = get_tracking_context()
        metrics = ctx.metrics_client

        if metrics is None:
            return  # Silent if no metrics client

        # Example: StatsD-style API
        if hasattr(metrics, "increment"):
            metrics.increment(metric_name, tags=tags or {})
        elif hasattr(metrics, "gauge"):
            metrics.gauge(metric_name, value, tags=tags or {})

    cls.record_metric = record_metric

    _add_capability(cls, "metrics")

    return cls


def with_retry_logic_contextual(cls: type[T]) -> type[T]:
    """Add retry logic capability with context injection.

    Uses max_retries and retry_delay from TrackingContext.
    """
    original_send_with = getattr(cls, "send_with", None)

    async def send_with_with_retry(self, client=None, macros=None, **context):
        """Send with retry logic using context configuration."""
        ctx = get_tracking_context()

        # Use context defaults
        max_retries = context.get("max_retries", ctx.max_retries)
        retry_delay = context.get("retry_delay", ctx.retry_delay)

        for attempt in range(max_retries):
            try:
                if original_send_with:
                    success = await original_send_with(self, client, macros, **context)
                else:
                    # Fallback to basic send_with from with_http_send_contextual
                    async def basic_send_with(obj, client=None, macros=None, **context):
                        # Get global context
                        ctx = get_tracking_context()
                        active_client = client or ctx.http_client
                        if active_client is None:
                            raise ValueError("No HTTP client available")

                        timeout = context.get("timeout", ctx.timeout)
                        headers = context.get("headers", {})
                        params = context.get("params", {})
                        logger = ctx.logger

                        try:
                            if isinstance(obj.value, list):
                                url = obj.value[0] if obj.value else ""
                            else:
                                url = obj.value

                            if not url:
                                return False

                            if macros and "macros" in getattr(obj, "__capabilities__", set()):
                                url = obj.apply_macros(macros, ["[{macro}]", "${{{macro}}}"])
                                if isinstance(url, list):
                                    url = url[0]

                            if logger:
                                logger.debug(
                                    "Sending tracking request", url=url, trackable_key=obj.key
                                )

                            request_kwargs = {"timeout": timeout}
                            if headers:
                                request_kwargs["headers"] = headers
                            if params:
                                request_kwargs["params"] = params

                            response = await active_client.get(url, **request_kwargs)
                            response.raise_for_status()

                            if "state" in getattr(obj, "__capabilities__", set()):
                                obj.mark_tracked()

                            if logger:
                                logger.debug(
                                    "Tracking request successful",
                                    url=url,
                                    status=response.status_code,
                                )

                            return True

                        except Exception as e:
                            if "state" in getattr(obj, "__capabilities__", set()):
                                obj.mark_failed(str(e))

                            if logger:
                                logger.error("Tracking request failed", url=url, error=str(e))

                            return False

                    success = await basic_send_with(self, client, macros, **context)

                if success:
                    return True

            except Exception as e:
                # Log retry attempt
                if "logging_contextual" in getattr(self, "__capabilities__", set()):
                    self.log_state_contextual(f"Retry attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        return False

    # Replace or add method
    cls.send_with = send_with_with_retry

    # Mark capability
    _add_capability(cls, "retry_contextual")

    return cls


# Composite decorators with context injection


def trackable_contextual_basic(cls: type[T]) -> type[T]:
    """Apply basic contextual capabilities: macros, state, logging_contextual."""
    return with_logging_contextual(with_state(with_macros(cls)))


def trackable_contextual_full(cls: type[T]) -> type[T]:
    """Apply full contextual capabilities: macros, state, logging_contextual, http_send_contextual."""
    return with_http_send_contextual(with_logging_contextual(with_state(with_macros(cls))))


def trackable_contextual_with_retry(cls: type[T]) -> type[T]:
    """Apply full contextual capabilities with retry logic."""
    return with_retry_logic_contextual(
        with_http_send_contextual(with_logging_contextual(with_state(with_macros(cls))))
    )


def trackable_contextual_with_metrics(cls: type[T]) -> type[T]:
    """Apply full contextual capabilities with metrics."""
    return with_metrics_contextual(
        with_http_send_contextual(with_logging_contextual(with_state(with_macros(cls))))
    )


# Capability introspection utilities


def has_capability(trackable, capability: str) -> bool:
    """Check if Trackable has specific capability.

    Args:
        trackable: Trackable instance
        capability: Capability name ('macros', 'state', 'logging', 'http_send', 'retry')

    Returns:
        bool: True if capability is present
    """
    return capability in getattr(trackable, "__capabilities__", set())


def get_capabilities(trackable) -> set[str]:
    """Get all capabilities of Trackable.

    Args:
        trackable: Trackable instance

    Returns:
        set[str]: Set of capability names
    """
    return getattr(trackable, "__capabilities__", set())


def has_all_capabilities(trackable, capabilities: list[str]) -> bool:
    """Check if Trackable has all specified capabilities.

    Args:
        trackable: Trackable instance
        capabilities: List of capability names

    Returns:
        bool: True if all capabilities are present
    """
    trackable_caps = getattr(trackable, "__capabilities__", set())
    return all(cap in trackable_caps for cap in capabilities)


def has_any_capability(trackable, capabilities: list[str]) -> bool:
    """Check if Trackable has any of the specified capabilities.

    Args:
        trackable: Trackable instance
        capabilities: List of capability names

    Returns:
        bool: True if any capability is present
    """
    trackable_caps = getattr(trackable, "__capabilities__", set())
    return any(cap in trackable_caps for cap in capabilities)


__all__ = [
    # Individual decorators
    "with_macros",
    "with_state",
    "with_event_filtering",
    "with_logging",
    "with_http_send",
    "with_retry_logic",
    # Context-aware decorators (Dependency Injection)
    "with_http_send_contextual",
    "with_logging_contextual",
    "with_metrics_contextual",
    "with_retry_logic_contextual",
    # Composite decorators
    "trackable_basic",
    "trackable_standard",
    "trackable_full",
    "trackable_with_retry",
    # Composite decorators with context injection
    "trackable_contextual_basic",
    "trackable_contextual_full",
    "trackable_contextual_with_retry",
    "trackable_contextual_with_metrics",
    # Introspection utilities
    "has_capability",
    "get_capabilities",
    "has_all_capabilities",
    "has_any_capability",
]
