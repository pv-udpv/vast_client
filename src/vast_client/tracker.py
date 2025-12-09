"""VAST tracking events management."""

import re
import secrets
import time
from typing import Any
import httpx

from .http_client_manager import (
    get_http_client_manager,
    get_tracking_http_client,
    record_tracking_client_request,
)
from .log_config import get_context_logger
from .log_config.tracing import (
    create_async_span,
    propagate_trace_headers,
    should_propagate_to_service,
)
from .capabilities import has_capability, trackable_full
from .config import VastTrackerConfig
from .context import TrackingContext, set_tracking_context
from .embed_http_client import EmbedHttpClient
from .trackable import Trackable, TrackableCollection, TrackableEvent


class VastTracker:
    """Handles VAST tracking events for ad playback."""

    def __init__(
        self,
        tracking_events: dict[str, list[str]]
        | dict[str, list[Trackable]]
        | dict[str, Trackable]
        | TrackableCollection,
        client: httpx.AsyncClient | None = None,
        embed_client: "EmbedHttpClient | None" = None,
        creative_id: str | None = None,
        config: "VastTrackerConfig | None" = None,
        context: TrackingContext | None = None,  # NEW: Dependency injection context
        # Deprecated: use embed_client instead
        ad_request: dict[str, Any] | None = None,
    ):
        """Initialize VAST tracker.

        Args:
            tracking_events: Dictionary of event types to tracking URLs or Trackable objects/lists
            client: HTTP client for tracking requests
            embed_client: EmbedHttpClient with frozen context for macros
            creative_id: Creative ID for tracking context
            config: Tracker configuration
            ad_request: [DEPRECATED] Use embed_client instead
        """
        # Convert tracking_events to registry format: dict[str, list[Trackable]]
        self.events = self._normalize_to_registry(tracking_events)

        self.client = client  # Will be initialized later if None
        self.embed_client = embed_client
        self.creative_id = creative_id
        self.config = config or VastTrackerConfig()
        self.tracked_events = set()

        self.logger = get_context_logger("vast_tracker")

        # Backward compatibility: extract embed_client from ad_request if needed
        if self.embed_client is None and ad_request is not None:
            # TODO: Remove this backward compatibility in future version
            self.logger.warning(
                "Using deprecated ad_request parameter, use embed_client instead",
                creative_id=creative_id,
            )

        # Initialize tracking context for dependency injection
        if context is None:
            # Create default context with tracker's dependencies
            context = TrackingContext(
                logger=self.logger,
                http_client=self.client,
                timeout=self.config.timeout,
                max_retries=3,
                retry_delay=1.0,
            )

        # Set global context (scoped to this tracker's operations)
        set_tracking_context(context)
        self.context = context

        self.logger.debug(
            "TrackingContext initialized",
            has_logger=context.logger is not None,
            has_http_client=context.http_client is not None,
            has_metrics=context.metrics_client is not None,
            timeout=context.timeout,
            custom_deps=list(context._custom.keys()),
        )

        # Build static macros once during initialization
        self.static_macros = self._build_static_macros()

        # Count total tracking URLs and trackables
        total_trackables = sum(len(trackables) for trackables in self.events.values())
        self.logger.debug(
            "VastTracker initialized",
            event_types=list(self.events.keys()),
            events_count=len(self.events),
            total_trackables=total_trackables,
            creative_id=creative_id,
            static_macros_count=len(self.static_macros),
            has_embed_client=self.embed_client is not None,
        )

        # Log details of each event type
        for event_type, trackables in self.events.items():
            self.logger.debug(
                "Tracking event configured",
                event_type=event_type,
                trackables_count=len(trackables),
                creative_id=creative_id,
                capabilities=[getattr(t, "__capabilities__", set()) for t in trackables],
            )

    def _build_static_macros(self) -> dict[str, str]:
        """Build static macros from EmbedHttpClient (frozen context).

        Returns:
            Dictionary of static macros that don't change during tracker lifetime
        """
        macros = {}

        # 1. Static macros from configuration
        macros.update(self.config.static_macros)

        # 2. Extract macros from EmbedHttpClient
        if self.embed_client:
            embed_macros: dict[str, Any] = {}

            # Prefer provider-aware tracking macros if available
            if hasattr(self.embed_client, "get_tracking_macros"):
                embed_macros = self.embed_client.get_tracking_macros()
            elif hasattr(self.embed_client, "get_macros"):
                embed_macros = self.embed_client.get_macros()

            macros.update({k: str(v) for k, v in embed_macros.items()})

            # Auto-add uppercase variants so [DEVICE_SERIAL] resolves without explicit mapping
            for param_key, param_value in embed_macros.items():
                macros.setdefault(param_key.upper(), str(param_value))

            # Auto-build macros directly from original ad_request (if attached to the client)
            ad_request = None
            if hasattr(self.embed_client, "get_extra"):
                ad_request = self.embed_client.get_extra("ad_request")
            elif hasattr(self.embed_client, "ad_request"):
                ad_request = getattr(self.embed_client, "ad_request")

            if isinstance(ad_request, dict):
                auto_macros = self._build_auto_macros_from_ad_request(ad_request)
                for macro_key, macro_value in auto_macros.items():
                    macros.setdefault(macro_key, macro_value)

            # Apply custom mapping from config
            for param_key, macro_key in self.config.macro_mapping.items():
                if (
                    hasattr(self.embed_client, "base_params")
                    and param_key in self.embed_client.base_params
                ):
                    macros[macro_key] = str(self.embed_client.base_params[param_key])

        # 3. Creative macros (static for this tracker instance)
        if self.creative_id:
            macros["CREATIVE_ID"] = self.creative_id
            macros["ADID"] = self.creative_id

        self.logger.debug(
            "Built static macros",
            macros_count=len(macros),
            macro_keys=list(macros.keys()),
            creative_id=self.creative_id,
            has_embed_client=self.embed_client is not None,
        )

        return macros

    @staticmethod
    def _build_auto_macros_from_ad_request(ad_request: dict[str, Any]) -> dict[str, str]:
        """Create macro dictionary from ad_request using uppercased keys.

        Generates macros like DEVICE_SERIAL for ad_request.device_serial and
        EXT_CHANNEL_TO_DISPLAY_NAME for nested paths. Does not override
        existing macros, leaving precedence to explicitly configured ones.
        """

        auto_macros: dict[str, str] = {}

        def _walk(data: dict[str, Any], prefix: str = "") -> None:
            for key, value in data.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    _walk(value, path)
                else:
                    macro_key = path.replace(".", "_").upper()
                    auto_macros[macro_key] = str(value)

        _walk(ad_request)
        return auto_macros

    def _build_dynamic_macros(self) -> dict[str, str]:
        """Build dynamic macros (generated per event).

        Returns:
            Dictionary of dynamic macros that change with each event
        """
        return {
            "TIMESTAMP": str(int(time.time() * 1000)),
            "CACHEBUSTING": str(int(time.time() * 1000)),
            "RANDOM": str(secrets.randbelow(900000) + 100000),
        }

    def _normalize_to_registry(
        self,
        tracking_events: dict[str, list[str]]
        | dict[str, list[Trackable]]
        | dict[str, Trackable]
        | TrackableCollection,
    ) -> dict[str, list[Trackable]]:
        """Normalize tracking events to registry format: dict[str, list[Trackable]].

        Args:
            tracking_events: Input tracking events in any supported format

        Returns:
            Registry dictionary mapping event types to lists of Trackable objects
        """
        registry: dict[str, list[Trackable]] = {}

        if isinstance(tracking_events, TrackableCollection):
            # TrackableCollection - convert to registry
            for trackable in tracking_events:
                if trackable.key not in registry:
                    registry[trackable.key] = []
                registry[trackable.key].append(trackable)

        elif isinstance(tracking_events, dict):
            # Dictionary - check values and convert to lists
            for key, value in tracking_events.items():
                if isinstance(value, list):
                    if value and isinstance(value[0], Trackable):
                        # list[Trackable] - use as-is
                        registry[key] = value
                    else:
                        # list[str] - convert to Trackable objects with full capabilities
                        registry[key] = [
                            trackable_full(TrackableEvent)(key=f"{key}_{i}", value=url)
                            for i, url in enumerate(value)
                        ]
                elif isinstance(value, Trackable):
                    # Single Trackable - wrap in list
                    registry[key] = [value]
                else:
                    # Single URL string - convert to Trackable and wrap in list
                    url_str = str(value)
                    trackable = trackable_full(TrackableEvent)(key=f"{key}_0", value=url_str)
                    registry[key] = [trackable]
        else:
            raise ValueError(f"Unsupported tracking_events type: {type(tracking_events)}")

        return registry

    def build_default_macros(self) -> dict[str, str]:
        """Build default macros from ad_request context.

        DEPRECATED: Use _build_static_macros() and _build_dynamic_macros() instead.

        Returns:
            Dictionary of macros for substitution in tracking URLs
        """
        # For backward compatibility, still support old method
        # but delegate to new architecture
        static_macros = self._build_static_macros()
        dynamic_macros = self._build_dynamic_macros()
        return {**static_macros, **dynamic_macros}

    async def track_event(self, event: str, macros: dict[str, str] | None = None):
        """Track a VAST event by sending tracking requests via all registered Trackables.

        Args:
            event: Event name to track
            macros: Additional macros for URL substitution
        """
        # Ensure HTTP client is available for trackable sends
        if self.client is None:
            self.client = get_tracking_http_client()
            self.context.http_client = self.client

        # Get the list of trackable objects for this event
        trackables = self.events.get(event, [])
        self.logger.debug(
            "Preparing to track event", event_type=event, creative_id=self.creative_id
        )
        if not trackables:
            self.logger.warning(
                "Event not found in tracking events",
                event_type=event,
                creative_id=self.creative_id,
                available_events=list(self.events.keys()),
            )
            return

        # Build final macros: static + dynamic + additional
        dynamic_macros = self._build_dynamic_macros()
        final_macros = {
            **self.static_macros,  # Static macros (frozen)
            **dynamic_macros,  # Dynamic macros (fresh)
            **(macros or {}),  # Additional macros (override)
        }

        self.logger.debug(
            "Tracking event started",
            event_type=event,
            creative_id=self.creative_id,
            trackables_count=len(trackables),
            static_macros_count=len(self.static_macros),
            dynamic_macros_count=len(dynamic_macros),
            total_macros_count=len(final_macros),
            capabilities=[getattr(t, "__capabilities__", set()) for t in trackables],
        )

        # Track the event using all registered Trackables
        start_time = time.time()
        results = []
        processed_events = []  # Collect structured event data for logging

        try:
            # Send tracking requests via each Trackable
            for i, trackable in enumerate(trackables):
                event_info = {
                    "event_key": trackable.key,
                    "event_type": event,
                    "event_url": None,
                    "status_code": None,
                    "error": None,
                    "success": False,
                }

                try:
                    # Extract URL for logging
                    url = self._get_trackable_url(trackable, final_macros)
                    event_info["event_url"] = url

                    # Check if Trackable has http_send capability
                    if has_capability(trackable, "http_send"):
                        # Use Trackable's send_with method
                        success = await trackable.send_with(self.client, final_macros)
                        results.append(success)
                        event_info["success"] = success

                        # Extract status code if available from trackable state
                        if has_capability(trackable, "state"):
                            event_info["status_code"] = trackable.get_extra("last_status_code")

                        # Log individual Trackable result
                        if success:
                            self.logger.debug(
                                "Trackable sent successfully",
                                event_type=event,
                                creative_id=self.creative_id,
                                trackable_index=i,
                                trackable_key=trackable.key,
                                **trackable.to_log_dict()
                                if has_capability(trackable, "logging")
                                else {},
                            )
                        else:
                            has_state = has_capability(trackable, "state")
                            error_msg = trackable.get_extra("last_error") if has_state else None

                            if not error_msg:
                                # Ensure a reason is recorded even if the trackable didn't set one
                                error_msg = "unknown_failure"
                                if has_state:
                                    trackable.set_extra("last_error", error_msg)

                            event_info["error"] = error_msg
                            event_info["capabilities"] = list(
                                getattr(trackable, "__capabilities__", set())
                            )
                            # Capture status and attempts when available to debug "failed completely" cases
                            event_info["status_code"] = trackable.get_extra("last_status_code")
                            event_info["attempt_count"] = (
                                trackable.get_extra("attempt_count") or 0 if has_state else 0
                            )

                            self.logger.debug(
                                "Trackable send failed",
                                event_type=event,
                                creative_id=self.creative_id,
                                trackable_index=i,
                                trackable_key=trackable.key,
                                **trackable.to_log_dict()
                                if has_capability(trackable, "logging")
                                else {},
                            )
                    else:
                        # Fallback: use legacy URL-based sending
                        await self._send_legacy_trackable(trackable, final_macros, event, i)
                        results.append(True)  # Assume success for legacy method
                        event_info["success"] = True

                except Exception as e:
                    results.append(False)
                    event_info["error"] = str(e)
                    self.logger.error(
                        "Trackable tracking failed",
                        event_type=event,
                        creative_id=self.creative_id,
                        trackable_index=i,
                        trackable_key=trackable.key,
                        error=str(e),
                        **trackable.to_log_dict() if has_capability(trackable, "logging") else {},
                    )
                finally:
                    processed_events.append(event_info)

            # Check overall success
            successful_count = sum(results)
            total_count = len(trackables)

            if successful_count == total_count:
                self.logger.info(
                    "Event tracked successfully",
                    event_type=event,
                    creative_id=self.creative_id,
                    response_time=time.time() - start_time,
                    successful_trackables=successful_count,
                    total_trackables=total_count,
                    processed_events=processed_events,
                )
            elif successful_count > 0:
                self.logger.warning(
                    "Event tracked partially",
                    event_type=event,
                    creative_id=self.creative_id,
                    response_time=time.time() - start_time,
                    successful_trackables=successful_count,
                    total_trackables=total_count,
                    processed_events=processed_events,
                )
            else:
                self.logger.warning(
                    "Event tracking failed completely",
                    event_type=event,
                    creative_id=self.creative_id,
                    response_time=time.time() - start_time,
                    successful_trackables=successful_count,
                    total_trackables=total_count,
                    processed_events=processed_events,
                )

        except Exception as e:
            self.logger.warning(
                "Event tracking failed",
                event_type=event,
                creative_id=self.creative_id,
                error=str(e),
                successful_trackables=sum(results),
                total_trackables=len(trackables),
            )
            raise

    def _get_trackable_url(self, trackable: Trackable, macros: dict[str, str]) -> str | None:
        """Extract and process URL from a trackable object.

        Args:
            trackable: Trackable object
            macros: Macros for URL substitution

        Returns:
            Processed URL string or None if no URL available
        """
        try:
            # Get the value (URL or list of URLs)
            value = trackable.value

            # Apply macros if capability exists
            if has_capability(trackable, "macros"):
                processed = trackable.apply_macros(macros, self.config.macro_formats)
            else:
                processed = value

            # Extract first URL if list
            if isinstance(processed, list):
                return processed[0] if processed else None

            return str(processed) if processed else None

        except Exception:
            # Fallback to raw value
            if isinstance(trackable.value, list):
                return trackable.value[0] if trackable.value else None
            return str(trackable.value) if trackable.value else None

    async def _send_legacy_trackable(
        self, trackable: Trackable, macros: dict[str, str], event_type: str, trackable_index: int
    ):
        """Send tracking request using legacy URL-based method for backward compatibility.

        Args:
            trackable: Trackable object
            macros: Macros for URL substitution
            event_type: Type of event being tracked
            trackable_index: Index of trackable in the list
        """
        # Get URLs - use Trackable's apply_macros if available
        if has_capability(trackable, "macros"):
            urls = trackable.apply_macros(macros, self.config.macro_formats)
        else:
            urls = trackable.value

        # Ensure URLs is a list
        if not isinstance(urls, list):
            urls = [urls]

        # Send requests for each URL
        for url in urls:
            await self._send_tracking_request(url, trackable_index + 1, len(urls), event_type)

    async def _send_tracking_requests(
        self, urls: list[str], macros: dict[str, str], event_type: str
    ):
        """Send tracking requests for all URLs.

        Args:
            urls: List of tracking URLs
            macros: Macros for URL substitution
            event_type: Type of event being tracked (e.g., 'impression', 'firstQuartile')
        """
        self.logger.debug(
            "Sending tracking requests",
            event_type=event_type,
            creative_id=self.creative_id,
            urls_count=len(urls),
            macros_count=len(macros),
            original_urls=[url[:100] + "..." if len(url) > 100 else url for url in urls],
        )

        for i, url in enumerate(urls):
            original_url = url
            # Apply macros using configured formats
            url = self._apply_macros(url, macros)

            if url != original_url:
                self.logger.debug(
                    "Applied macros to tracking URL",
                    event_type=event_type,
                    creative_id=self.creative_id,
                    original_url=(
                        original_url[:100] + "..." if len(original_url) > 100 else original_url
                    ),
                    processed_url=url[:100] + "..." if len(url) > 100 else url,
                    applied_macros=list(macros.keys()),
                )

            await self._send_tracking_request(url, i + 1, len(urls), event_type)

    def _apply_macros(self, url: str, macros: dict[str, str]) -> str:
        """Apply macros to URL using configured formats.

        Args:
            url: Original URL
            macros: Macro dictionary

        Returns:
            URL with macros applied
        """
        resolved_macros = dict(macros)

        # Opportunistically resolve missing macros straight from ad_request for auto-access
        missing_macros = self._extract_macro_keys(url)
        for macro_key in missing_macros:
            if macro_key in resolved_macros:
                continue
            ad_value = self._resolve_macro_from_ad_request(macro_key)
            if ad_value is not None:
                resolved_macros[macro_key] = str(ad_value)

        for macro_key, macro_value in resolved_macros.items():
            # Apply all configured macro formats
            for format_template in self.config.macro_formats:
                pattern = format_template.format(macro=macro_key)
                url = url.replace(pattern, str(macro_value))

        return url

    def _resolve_macro_from_ad_request(self, macro_key: str) -> Any:
        """Resolve macro value directly from ad_request using common patterns.

        Supports both flat access (DEVICE_SERIAL -> ad_request["device_serial"])
        and nested access via underscore paths (EXT_DOMAIN -> ad_request["ext"]["domain"]).
        """

        if not self.embed_client:
            return None

        ad_request = None
        if hasattr(self.embed_client, "get_extra"):
            ad_request = self.embed_client.get_extra("ad_request")
        elif hasattr(self.embed_client, "ad_request"):
            ad_request = getattr(self.embed_client, "ad_request")

        if not isinstance(ad_request, dict):
            return None

        # 1) Direct key lookup (device_serial)
        direct_key = macro_key.lower()
        if direct_key in ad_request:
            value = ad_request[direct_key]
            return value if not isinstance(value, dict) else None

        # 2) Nested lookup by splitting underscores (EXT_DOMAIN -> ext.domain)
        parts = direct_key.split("_")
        current: Any = ad_request
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current if not isinstance(current, dict) else None

    def _extract_macro_keys(self, url: str) -> set[str]:
        """Extract macro keys from URL based on configured macro formats."""

        macro_keys: set[str] = set()
        for format_template in self.config.macro_formats:
            # Convert format template (e.g., "[{macro}]") into regex capturing macro name
            escaped = re.escape(format_template).replace("\\{macro\\}", "(?P<macro>[A-Za-z0-9_]+)")
            pattern = re.compile(escaped)
            for match in pattern.finditer(url):
                macro_keys.add(match.group("macro"))

        return macro_keys

    def _create_tracking_context(
        self, url: str, request_num: int, total_requests: int, event_type: str
    ) -> dict[str, Any]:
        """Create shared tracking context for request/response logging.

        Args:
            url: Tracking URL
            request_num: Current request number
            total_requests: Total number of requests
            event_type: Type of event being tracked

        Returns:
            Dictionary with shared tracking context
        """
        return {
            "event_type": event_type,
            "creative_id": self.creative_id,
            "request": f"{request_num}/{total_requests}",
            "tracking_url": url,
            "url_preview": url[:100] + "..." if len(url) > 100 else url,
        }

    async def _send_tracking_request(
        self, url: str, request_num: int, total_requests: int, event_type: str
    ):
        """Send a single tracking request with request/response paired logging and span tracing.

        Args:
            url: Tracking URL
            request_num: Current request number
            total_requests: Total number of requests
            event_type: Type of event being tracked (e.g., 'impression', 'firstQuartile')
        """
        # Create span for this tracking request
        span_name = f"vast.player.tracking.{event_type}"
        async with create_async_span(span_name) as span:
            # Create shared context for this request
            tracking_context = self._create_tracking_context(
                url, request_num, total_requests, event_type
            )

            # Log request phase
            self.logger.debug(
                "vast.player.tracking.request",
                tracking_request=tracking_context,
                span_name=span.span_name,
            )

            start_time = time.time()
            success = False
            error_type = None
            status_code = None
            response_length = 0

            try:
                # Get global HTTP client for tracking if not set
                if self.client is None:
                    self.client = get_tracking_http_client()

                # Selective propagation: only propagate to trusted tracking services
                headers = {}
                if should_propagate_to_service(url, "external"):
                    headers.update(propagate_trace_headers())

                response = await self.client.get(url, timeout=self.config.timeout, headers=headers)
                response.raise_for_status()
                success = True
                status_code = response.status_code
                response_length = len(response.text)

            except httpx.TimeoutException:
                error_type = "timeout"
            except httpx.HTTPStatusError as e:
                error_type = f"http_{e.response.status_code}"
                status_code = e.response.status_code
            except Exception as e:
                error_type = "exception"

                # Log exception to separate file with full context
                manager = get_http_client_manager()
                manager.record_exception(
                    e,
                    "tracking",
                    context=f"VAST {event_type} tracking request",
                    extra_data={
                        "event_type": event_type,
                        "creative_id": self.creative_id,
                        "tracking_url": url,
                        "request_number": f"{request_num}/{total_requests}",
                        "url_preview": url[:100] + "..." if len(url) > 100 else url,
                    },
                )

            finally:
                # Calculate response time
                response_time = time.time() - start_time

                # Create response context
                tracking_response = {
                    **tracking_context,  # Include all shared context
                    "ok": success,
                    "response_time": round(response_time, 3),
                }

                # Add response-specific fields
                if success:
                    tracking_response.update(
                        {
                            "status_code": status_code,
                            "response_length": response_length,
                        }
                    )
                else:
                    tracking_response.update(
                        {
                            "error_type": error_type,
                        }
                    )
                    if status_code:
                        tracking_response["status_code"] = status_code

                # Log response phase with appropriate level
                if success:
                    # Success: debug level (quiet)
                    self.logger.debug(
                        "vast.player.tracking.response",
                        tracking_response=tracking_response,
                        span_duration=span.duration,
                    )
                else:
                    # Error: info level (visible)
                    self.logger.info(
                        "vast.player.tracking.response",
                        tracking_response=tracking_response,
                        span_duration=span.duration,
                    )

                # Record request metric
                record_tracking_client_request(
                    url=url,
                    status_code=status_code,
                    duration=response_time,
                    error=error_type,
                )

    @classmethod
    def from_config(
        cls,
        tracking_events: dict[str, list[str]],
        embed_client: "EmbedHttpClient | None" = None,
        creative_id: str | None = None,
        config: dict[str, Any] | None = None,
        context: TrackingContext | None = None,
    ) -> "VastTracker":
        """Create tracker from configuration dictionary.

        Args:
            tracking_events: Dictionary of event types to tracking URLs
            embed_client: EmbedHttpClient with frozen context
            creative_id: Creative ID for tracking context
            config: Tracker configuration dictionary
            context: TrackingContext for dependency injection

        Returns:
            VastTracker: Configured tracker instance
        """
        from .config import VastTrackerConfig

        tracker_config = VastTrackerConfig(**(config or {}))
        return cls(
            tracking_events=tracking_events,
            embed_client=embed_client,
            creative_id=creative_id,
            config=tracker_config,
            context=context,
        )


__all__ = ["VastTracker"]
