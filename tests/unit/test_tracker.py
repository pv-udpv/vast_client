"""Unit tests for VAST tracker."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vast_client.capabilities import trackable_full
from vast_client.config import VastTrackerConfig
from vast_client.trackable import TrackableEvent
from vast_client.tracker import VastTracker


class TestVastTracker:
    """Test suite for VastTracker class."""

    def test_tracker_initialization(self, tracker_config, mock_http_client):
        """Test tracker initialization with config."""
        tracking_events = {
            "impression": ["https://tracking.example.com/impression"],
            "start": ["https://tracking.example.com/start"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_http_client,
            config=tracker_config,
            creative_id="test-creative-001",
        )

        assert tracker.creative_id == "test-creative-001"
        assert tracker.config == tracker_config
        assert "impression" in tracker.events
        assert "start" in tracker.events

    def test_tracker_initialization_with_trackable_objects(self, tracker_config, mock_http_client):
        """Test tracker initialization with Trackable objects."""
        trackable = trackable_full(TrackableEvent)(
            key="impression_0", value="https://tracking.example.com/impression"
        )

        tracking_events = {
            "impression": [trackable],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_http_client,
            config=tracker_config,
        )

        assert "impression" in tracker.events
        assert len(tracker.events["impression"]) == 1

    def test_tracker_normalize_string_urls(self, tracker_config, mock_http_client):
        """Test tracker normalizes string URLs to Trackable objects."""
        tracking_events = {
            "impression": ["https://tracking.example.com/impression"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_http_client,
            config=tracker_config,
        )

        # Should be converted to Trackable objects
        assert len(tracker.events["impression"]) == 1
        trackable = tracker.events["impression"][0]
        assert hasattr(trackable, "send_with")

    def test_build_static_macros(self, tracker_config, mock_http_client):
        """Test building static macros."""
        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=tracker_config,
            creative_id="creative-123",
        )

        assert "CREATIVE_ID" in tracker.static_macros
        assert tracker.static_macros["CREATIVE_ID"] == "creative-123"
        assert "ADID" in tracker.static_macros
        assert tracker.static_macros["ADID"] == "creative-123"

    def test_build_dynamic_macros(self, tracker_config, mock_http_client):
        """Test building dynamic macros."""
        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=tracker_config,
        )

        dynamic_macros = tracker._build_dynamic_macros()

        assert "TIMESTAMP" in dynamic_macros
        assert "CACHEBUSTING" in dynamic_macros
        assert "RANDOM" in dynamic_macros

        # Timestamp should be numeric string
        assert dynamic_macros["TIMESTAMP"].isdigit()
        assert dynamic_macros["CACHEBUSTING"].isdigit()
        assert dynamic_macros["RANDOM"].isdigit()

    def test_apply_macros_bracket_format(self, tracker_config, mock_http_client):
        """Test applying macros in bracket format [MACRO]."""
        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=tracker_config,
            creative_id="creative-456",
        )

        url = "https://tracking.example.com/event?cid=[CREATIVE_ID]&t=[TIMESTAMP]"
        macros = {"CREATIVE_ID": "creative-456", "TIMESTAMP": "1234567890"}

        result = tracker._apply_macros(url, macros)

        assert "[CREATIVE_ID]" not in result
        assert "creative-456" in result
        assert "[TIMESTAMP]" not in result
        assert "1234567890" in result

    def test_apply_macros_dollar_format(self, tracker_config, mock_http_client):
        """Test applying macros in dollar format ${MACRO}."""
        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=tracker_config,
            creative_id="creative-789",
        )

        url = "https://tracking.example.com/event?cid=${CREATIVE_ID}&t=${TIMESTAMP}"
        macros = {"CREATIVE_ID": "creative-789", "TIMESTAMP": "9876543210"}

        result = tracker._apply_macros(url, macros)

        assert "${CREATIVE_ID}" not in result
        assert "creative-789" in result
        assert "${TIMESTAMP}" not in result
        assert "9876543210" in result

    @pytest.mark.asyncio
    async def test_track_event_success(self, tracker_config):
        """Test tracking event successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "start": ["https://tracking.example.com/start"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        await tracker.track_event("start")

        # Should have made HTTP request
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_event_with_macros(self, tracker_config):
        """Test tracking event with macro substitution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "impression": ["https://tracking.example.com/imp?cid=[CREATIVE_ID]&t=[TIMESTAMP]"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
            creative_id="creative-001",
        )

        await tracker.track_event("impression")

        # Verify request was made with macro substitution
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        url = call_args[0][0]

        # Creative ID should be substituted
        assert "[CREATIVE_ID]" not in url
        assert "creative-001" in url

        # Timestamp should be substituted
        assert "[TIMESTAMP]" not in url

    @pytest.mark.asyncio
    async def test_track_event_not_found(self, tracker_config, mock_http_client):
        """Test tracking event that doesn't exist in registry."""
        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=tracker_config,
        )

        # Should not raise, just log warning
        await tracker.track_event("nonexistent")

        # No HTTP calls should be made
        mock_http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_event_http_error(self, tracker_config):
        """Test tracking event with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "start": ["https://tracking.example.com/start"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        # Should not raise exception, handle gracefully
        await tracker.track_event("start")

    @pytest.mark.asyncio
    async def test_track_event_multiple_urls(self, tracker_config):
        """Test tracking event with multiple tracking URLs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "impression": [
                "https://tracking1.example.com/imp",
                "https://tracking2.example.com/imp",
                "https://tracking3.example.com/imp",
            ],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        await tracker.track_event("impression")

        # Should make 3 HTTP requests
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_track_event_with_custom_macros(self, tracker_config):
        """Test tracking event with custom additional macros."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "custom": ["https://tracking.example.com/custom?user=[USER_ID]"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        # Pass custom macros
        await tracker.track_event("custom", macros={"USER_ID": "user-123"})

        # Verify custom macro was applied
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "user-123" in url
        assert "[USER_ID]" not in url

    def test_from_config_classmethod(self, mock_http_client):
        """Test creating tracker from config dictionary."""
        tracking_events = {
            "impression": ["https://tracking.example.com/impression"],
        }

        config_dict = {
            "timeout": 10.0,
            "macro_formats": ["[{macro}]"],
        }

        tracker = VastTracker.from_config(
            tracking_events=tracking_events,
            config=config_dict,
        )

        assert tracker.config.timeout == 10.0
        assert tracker.config.macro_formats == ["[{macro}]"]


class TestVastTrackerMacroHandling:
    """Test macro handling in VastTracker."""

    @pytest.mark.asyncio
    async def test_timestamp_macro_is_unique(self, tracker_config):
        """Test that TIMESTAMP macro generates unique values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "event": ["https://tracking.example.com/event?t=[TIMESTAMP]"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        # Track same event twice
        await tracker.track_event("event")
        first_call_url = mock_client.get.call_args_list[0][0][0]

        await tracker.track_event("event")
        second_call_url = mock_client.get.call_args_list[1][0][0]

        # Timestamps should be different (or very close if fast)
        # At minimum, they should not contain the macro placeholder
        assert "[TIMESTAMP]" not in first_call_url
        assert "[TIMESTAMP]" not in second_call_url

    @pytest.mark.asyncio
    async def test_random_macro_is_unique(self, tracker_config):
        """Test that RANDOM macro generates unique values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        tracking_events = {
            "event": ["https://tracking.example.com/event?r=[RANDOM]"],
        }

        tracker = VastTracker(
            tracking_events=tracking_events,
            client=mock_client,
            config=tracker_config,
        )

        # Track same event multiple times
        for _ in range(3):
            await tracker.track_event("event")

        urls = [call[0][0] for call in mock_client.get.call_args_list]

        # All URLs should have resolved RANDOM macro
        for url in urls:
            assert "[RANDOM]" not in url

    def test_static_macros_from_config(self, mock_http_client):
        """Test static macros from tracker config."""
        config = VastTrackerConfig(
            static_macros={
                "PUBLISHER_ID": "pub-123",
                "PLATFORM": "ctv",
            }
        )

        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            config=config,
        )

        assert "PUBLISHER_ID" in tracker.static_macros
        assert tracker.static_macros["PUBLISHER_ID"] == "pub-123"
        assert "PLATFORM" in tracker.static_macros
        assert tracker.static_macros["PLATFORM"] == "ctv"

    def test_macro_mapping_from_config(self, mock_http_client):
        """Test macro mapping from tracker config."""
        # Mock EmbedHttpClient
        mock_embed_client = MagicMock()
        mock_embed_client.base_params = {
            "publisher_id": "pub-456",
            "device_id": "device-789",
        }
        mock_embed_client.get_tracking_macros.return_value = {}

        config = VastTrackerConfig(
            macro_mapping={
                "publisher_id": "PUBLISHER_ID",
                "device_id": "DEVICE_ID",
            }
        )

        tracker = VastTracker(
            tracking_events={},
            client=mock_http_client,
            embed_client=mock_embed_client,
            config=config,
        )

        assert "PUBLISHER_ID" in tracker.static_macros
        assert tracker.static_macros["PUBLISHER_ID"] == "pub-456"
        assert "DEVICE_ID" in tracker.static_macros
        assert tracker.static_macros["DEVICE_ID"] == "device-789"
