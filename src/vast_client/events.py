"""VAST event type constants."""

from enum import Enum


class VastEvents(str, Enum):
    """Event type constants for structured logging."""

    # Parser events
    PARSE_STARTED = "vast.parse.started"
    PARSE_SUCCESS = "vast.parse.success"
    PARSE_FAILED = "vast.parse.failed"

    # Request events
    REQUEST_STARTED = "vast.request.started"
    REQUEST_SUCCESS = "vast.request.success"
    REQUEST_FAILED = "vast.request.failed"

    # Tracking events
    TRACKING_EVENT_SENT = "vast.tracking.sent"
    TRACKING_FAILED = "vast.tracking.failed"

    # Player events
    PLAYER_INITIALIZED = "vast.player.initialized"
    PLAYBACK_STARTED = "vast.playback.started"
    PLAYBACK_PAUSED = "vast.playback.paused"
    PLAYBACK_RESUMED = "vast.playback.resumed"
    PLAYBACK_INTERRUPTED = "vast.playback.interrupted"
    PLAYBACK_COMPLETED = "vast.playback.completed"

    # Quartile events
    QUARTILE_FIRST = "vast.quartile.first"
    QUARTILE_MIDPOINT = "vast.quartile.midpoint"
    QUARTILE_THIRD = "vast.quartile.third"


__all__ = ["VastEvents"]
