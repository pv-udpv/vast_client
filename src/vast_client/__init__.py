"""
VAST Client Package

A modular VAST (Video Ad Serving Template) client implementation for handling
video advertising requests, parsing, tracking, and playback.

This package provides:
- VastClient: Main client for ad requests and management
- VastParser: VAST XML parsing functionality
- VastTracker: Event tracking for VAST compliance
- VastPlayer: Ad playback with progress tracking
- Type definitions and configuration classes

Usage:
    from vast_client import VastClient, VastParser, VastTracker, VastPlayer

    # Simple usage
    client = VastClient("https://ads.example.com/vast")
    ad_data = await client.request_ad()

    # Advanced usage with context
    async with VastClient.from_config(config, ctx=ad_request) as client:
        ad_data = await client.request_ad(params={"slot": "pre-roll"})
        await client.play_ad(ad_data)
"""

from .client import VastClient
from .parser import VastParser
from .player import VastPlayer
from .base_player import BaseVastPlayer
from .headless_player import HeadlessPlayer
from .tracker import VastTracker
from .types import VastClientConfig
from .config import PlaybackMode, InterruptionType, PlaybackSessionConfig
from .config_resolver import ConfigResolver
from .playback_session import (
    PlaybackSession,
    PlaybackStatus,
    PlaybackEventType,
    PlaybackEvent,
    QuartileTracker,
)
from .time_provider import (
    TimeProvider,
    RealtimeTimeProvider,
    SimulatedTimeProvider,
    AutoDetectTimeProvider,
    create_time_provider,
)

__version__ = "1.0.0"
__author__ = "CTV Middleware Team"
__email__ = "dev@ctv-middleware.com"

__all__ = [
    # Main classes
    "VastClient",
    "VastParser",
    "VastTracker",
    "VastPlayer",
    "BaseVastPlayer",
    "HeadlessPlayer",
    # Type definitions
    "VastClientConfig",
    # Configuration
    "PlaybackMode",
    "InterruptionType",
    "PlaybackSessionConfig",
    "ConfigResolver",
    # Playback session tracking
    "PlaybackSession",
    "PlaybackStatus",
    "PlaybackEventType",
    "PlaybackEvent",
    "QuartileTracker",
    # Time providers
    "TimeProvider",
    "RealtimeTimeProvider",
    "SimulatedTimeProvider",
    "AutoDetectTimeProvider",
    "create_time_provider",
    # Package metadata
    "__version__",
    "__author__",
    "__email__",
]


# Package-level convenience functions
def create_client(config_or_url, ctx=None, **kwargs):
    """Create a VastClient instance.

    Convenience function for creating VastClient instances.

    Args:
        config_or_url: URL string or configuration dict
        ctx: Request context (ad_request)
        **kwargs: Additional parameters

    Returns:
        VastClient: Configured client instance

    Example:
        client = create_client("https://ads.example.com/vast")
        client = create_client({"url": "https://ads.example.com", "params": {...}})
    """
    return VastClient(config_or_url, ctx, **kwargs)


def create_parser(**kwargs):
    """Create a VastParser instance.

    Returns:
        VastParser: Parser instance
    """
    return VastParser(**kwargs)


def create_tracker(tracking_events, client=None, ad_request=None, creative_id=None):
    """Create a VastTracker instance.

    Args:
        tracking_events: Dictionary of event types to tracking URLs
        client: HTTP client for tracking requests
        ad_request: Ad request context
        creative_id: Creative ID for tracking context

    Returns:
        VastTracker: Tracker instance
    """
    return VastTracker(tracking_events, client, ad_request, creative_id)
