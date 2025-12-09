"""
Test automatic macro mapping with ad_request base path resolution.
"""

import pytest
from vast_client.capabilities import with_macros
from vast_client.config import VastTrackerConfig
from vast_client.embed_http_client import EmbedHttpClient
from vast_client.provider_config_loader import ProviderConfigLoader
from vast_client.trackable import TrackableEvent
from vast_client.tracker import VastTracker


def test_auto_macro_mapping_simple():
    """Test simple auto-mapping: device_serial: DEVICE_SERIAL → ad_request.device_serial"""

    macro_mapping = {"device_serial": "DEVICE_SERIAL", "city": "CITY", "user_id": "USER_ID"}

    ad_request = {"device_serial": "ABC-123-XYZ", "city": "New York", "user_id": "user_456"}

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    assert result == {"DEVICE_SERIAL": "ABC-123-XYZ", "CITY": "New York", "USER_ID": "user_456"}


def test_auto_macro_mapping_nested_path():
    """Test nested path mapping: channel_name: CHANNEL_NAME → ad_request.ext.channel_to.name"""

    macro_mapping = {"ext.channel_to.display_name": "CHANNEL_NAME", "ext.domain": "DOMAIN"}

    ad_request = {"ext": {"channel_to": {"display_name": "HBO HD"}, "domain": "example.com"}}

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    assert result == {"CHANNEL_NAME": "HBO HD", "DOMAIN": "example.com"}


def test_auto_macro_mapping_missing_values():
    """Test that missing values are not included in result"""

    macro_mapping = {
        "device_serial": "DEVICE_SERIAL",
        "missing_field": "MISSING_MACRO",
        "city": "CITY",
    }

    ad_request = {"device_serial": "ABC-123", "city": "London"}

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    # Only present values should be in result
    assert result == {"DEVICE_SERIAL": "ABC-123", "CITY": "London"}
    assert "MISSING_MACRO" not in result


def test_auto_macro_mapping_mixed_simple_and_nested():
    """Test mixing simple and nested path mappings"""

    macro_mapping = {
        "device_serial": "DEVICE_SERIAL",
        "ext.channel_to.display_name": "CHANNEL_NAME",
        "user_agent": "USER_AGENT",
        "ext.domain": "DOMAIN",
    }

    ad_request = {
        "device_serial": "DEV-001",
        "user_agent": "SmartTV/1.0",
        "ext": {"channel_to": {"display_name": "Channel 1"}, "domain": "test.com"},
    }

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    assert result == {
        "DEVICE_SERIAL": "DEV-001",
        "CHANNEL_NAME": "Channel 1",
        "USER_AGENT": "SmartTV/1.0",
        "DOMAIN": "test.com",
    }


def test_auto_macro_mapping_non_string_values():
    """Test that non-string values are converted to strings"""

    macro_mapping = {"port": "PORT", "timeout": "TIMEOUT", "enabled": "ENABLED"}

    ad_request = {"port": 8080, "timeout": 30.5, "enabled": True}

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    assert result == {"PORT": "8080", "TIMEOUT": "30.5", "ENABLED": "True"}

    # All values should be strings
    for value in result.values():
        assert isinstance(value, str)


def test_tracker_auto_macros_from_ad_request_without_mapping():
    """Tracker should expose uppercase macros directly from ad_request data."""

    embed_client = EmbedHttpClient(
        base_url="https://example.com/vast",
        base_params={"device_serial": "ABC-123"},
    )
    embed_client.set_extra(
        "ad_request",
        {"device_serial": "ABC-123", "city": "Paris", "ext": {"domain": "example.com"}},
    )

    tracker = VastTracker(
        tracking_events={"start": []},
        embed_client=embed_client,
        config=VastTrackerConfig(macro_formats=["[{macro}]"]),
    )

    assert tracker.static_macros["DEVICE_SERIAL"] == "ABC-123"
    assert tracker.static_macros["CITY"] == "Paris"
    assert tracker.static_macros["EXT_DOMAIN"] == "example.com"


def test_tracker_applies_uppercase_macro_in_url():
    """Tracking URLs with [DEVICE_SERIAL] should resolve without macro_mapping."""

    embed_client = EmbedHttpClient(
        base_url="https://example.com/vast",
        base_params={"device_serial": "DEV-999"},
    )
    embed_client.set_extra("ad_request", {"device_serial": "DEV-999"})

    tracker = VastTracker(
        tracking_events={"start": []},
        embed_client=embed_client,
        config=VastTrackerConfig(macro_formats=["[{macro}]"]),
    )

    MacroTrackable = with_macros(TrackableEvent)
    trackable = MacroTrackable(key="start_0", value="https://tracker/[DEVICE_SERIAL]")

    url = tracker._get_trackable_url(trackable, tracker.static_macros)

    assert url == "https://tracker/DEV-999"


def test_apply_macros_fallbacks_to_ad_request_when_missing_macro():
    """_apply_macros should auto-fetch ad_request fields even if macros dict is empty."""

    embed_client = EmbedHttpClient(base_url="https://example.com/vast")
    embed_client.set_extra("ad_request", {"device_serial": "AUTO-ACCESS-001"})

    tracker = VastTracker(
        tracking_events={"start": []},
        embed_client=embed_client,
        config=VastTrackerConfig(macro_formats=["[{macro}]"]),
    )

    # Supply an empty macros dict to force fallback resolution
    processed = tracker._apply_macros("https://tracker/[DEVICE_SERIAL]", {})

    assert processed == "https://tracker/AUTO-ACCESS-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
