"""Helper functions for VAST client operations."""

from typing import Any


def extract_creative_id(vast_data: dict[str, Any]) -> str | None:
    """
    Extract creative ID from parsed VAST data.

    Args:
        vast_data: Parsed VAST data dictionary

    Returns:
        str | None: Creative ID if found, None otherwise

    Examples:
        >>> vast_data = {"creative": {"id": "creative-123"}}
        >>> extract_creative_id(vast_data)
        'creative-123'
    """
    creative_data = vast_data.get("creative", {})
    return creative_data.get("id") or creative_data.get("ad_id")


def prepare_tracking_events(vast_data: dict[str, Any]) -> dict[str, list[str]]:
    """
    Prepare tracking events dictionary from parsed VAST data.

    Consolidates impression and error URLs into the tracking_events dictionary.

    Args:
        vast_data: Parsed VAST data dictionary

    Returns:
        dict: Dictionary of event types to tracking URLs

    Examples:
        >>> vast_data = {
        ...     "tracking_events": {"start": ["https://example.com/start"]},
        ...     "impression": ["https://example.com/impression"],
        ...     "error": ["https://example.com/error"]
        ... }
        >>> events = prepare_tracking_events(vast_data)
        >>> events["impression"]
        ['https://example.com/impression']
    """
    tracking_events = vast_data.get("tracking_events", {}).copy()
    tracking_events.update({"impression": vast_data.get("impression", [])})
    tracking_events.update({"error": vast_data.get("error", [])})
    return tracking_events


__all__ = ["extract_creative_id", "prepare_tracking_events"]
