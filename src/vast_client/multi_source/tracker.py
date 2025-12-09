"""
Multi-Source VAST Tracker

Unified tracking for multi-source VAST requests with aggregated results.
"""

from typing import Any

import httpx

from ..log_config import get_context_logger
from ..tracker import VastTracker
from ..vast_helpers import prepare_tracking_events


class MultiSourceTracker:
    """
    Unified tracker for multi-source VAST operations.

    Aggregates tracking results from multiple sources and provides
    a unified interface for event tracking.

    Examples:
        Create tracker from parsed VAST data:
        >>> tracker = MultiSourceTracker(
        ...     vast_data=parsed_data,
        ...     http_client=client,
        ...     creative_id="creative-123"
        ... )

        Track impression event:
        >>> await tracker.track_impression()

        Track playback event:
        >>> await tracker.track_event("start")
    """

    def __init__(
        self,
        vast_data: dict[str, Any],
        http_client: httpx.AsyncClient,
        creative_id: str | None = None,
        embed_client: Any = None,
    ):
        """
        Initialize multi-source tracker.

        Args:
            vast_data: Parsed VAST data with tracking events
            http_client: HTTP client for tracking requests
            creative_id: Creative ID for tracking context
            embed_client: Optional EmbedHttpClient for URL building
        """
        self.logger = get_context_logger("vast_multi_source_tracker")
        self.vast_data = vast_data
        self.http_client = http_client
        self.creative_id = creative_id
        self.embed_client = embed_client

        # Extract tracking events from VAST data using helper
        tracking_events = prepare_tracking_events(vast_data)

        # Create underlying VastTracker
        self.tracker = VastTracker(
            tracking_events,
            http_client,
            embed_client,
            creative_id,
        )

        self.logger.debug(
            "MultiSourceTracker initialized",
            event_count=len(tracking_events),
            creative_id=creative_id,
        )

    async def track_impression(self) -> dict[str, Any]:
        """
        Track impression event.

        Returns:
            dict: Tracking results with success/failure counts
        """
        return await self.tracker.track_event("impression")

    async def track_event(self, event_type: str) -> dict[str, Any]:
        """
        Track a specific event type.

        Args:
            event_type: Event type to track (start, complete, etc.)

        Returns:
            dict: Tracking results
        """
        return await self.tracker.track_event(event_type)

    def get_tracking_events(self) -> dict[str, list[str]]:
        """
        Get all tracking events.

        Returns:
            dict: Dictionary of event types to tracking URLs
        """
        return self.tracker.tracking_events

    def has_event(self, event_type: str) -> bool:
        """
        Check if tracker has specific event type.

        Args:
            event_type: Event type to check

        Returns:
            bool: True if event exists
        """
        return event_type in self.tracker.tracking_events


__all__ = ["MultiSourceTracker"]
