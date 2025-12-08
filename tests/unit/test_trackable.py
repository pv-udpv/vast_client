"""Unit tests for trackable protocol and capabilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vast_client.capabilities import (
    has_capability,
    trackable_full,
    with_logging,
    with_macros,
    with_state,
)
from vast_client.trackable import TrackableCollection, TrackableEvent


class TestTrackableEvent:
    """Test TrackableEvent base class."""

    def test_trackable_event_creation(self):
        """Test creating trackable event."""
        event = TrackableEvent(key="impression_0", value="https://tracking.example.com/imp")

        assert event.key == "impression_0"
        assert event.value == "https://tracking.example.com/imp"

    def test_trackable_event_equality(self):
        """Test trackable event equality."""
        event1 = TrackableEvent(key="start", value="https://example.com/start")
        event2 = TrackableEvent(key="start", value="https://example.com/start")
        event3 = TrackableEvent(key="complete", value="https://example.com/complete")

        assert event1 == event2
        assert event1 != event3


class TestTrackableCollection:
    """Test TrackableCollection container."""

    def test_collection_creation(self):
        """Test creating trackable collection."""
        event1 = TrackableEvent(key="start", value="https://example.com/start")
        event2 = TrackableEvent(key="complete", value="https://example.com/complete")

        collection = TrackableCollection([event1, event2])

        assert len(collection) == 2
        assert event1 in collection
        assert event2 in collection

    def test_collection_iteration(self):
        """Test iterating over collection."""
        events = [
            TrackableEvent(key=f"event_{i}", value=f"https://example.com/event_{i}")
            for i in range(5)
        ]
        collection = TrackableCollection(events)

        collected = list(collection)
        assert len(collected) == 5
        assert collected == events


class TestWithMacrosCapability:
    """Test with_macros capability decorator."""

    def test_with_macros_decorator(self):
        """Test applying with_macros capability."""

        @with_macros
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com?t=[TIMESTAMP]")

        # Should have macros capability
        assert has_capability(trackable, "macros")
        assert hasattr(trackable, "apply_macros")

    def test_apply_macros_bracket_format(self):
        """Test macro substitution with bracket format."""

        @with_macros
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(
            key="test", value="https://example.com?cid=[CREATIVE_ID]&t=[TIMESTAMP]"
        )

        macros = {"CREATIVE_ID": "creative-123", "TIMESTAMP": "1234567890"}
        result = trackable.apply_macros(macros, macro_formats=["[{macro}]"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert "creative-123" in result[0]
        assert "1234567890" in result[0]
        assert "[CREATIVE_ID]" not in result[0]
        assert "[TIMESTAMP]" not in result[0]

    def test_apply_macros_dollar_format(self):
        """Test macro substitution with dollar format."""

        @with_macros
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com?cid=${CREATIVE_ID}")

        macros = {"CREATIVE_ID": "creative-456"}
        result = trackable.apply_macros(macros, macro_formats=["${{{macro}}}"])

        assert "${CREATIVE_ID}" not in result[0]
        assert "creative-456" in result[0]


class TestWithStateCapability:
    """Test with_state capability decorator."""

    def test_with_state_decorator(self):
        """Test applying with_state capability."""

        @with_state
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")

        assert has_capability(trackable, "state")
        assert hasattr(trackable, "mark_tracked")
        assert hasattr(trackable, "mark_failed")
        assert hasattr(trackable, "is_tracked")

    def test_state_tracking(self):
        """Test state tracking methods."""

        @with_state
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")

        # Initial state
        assert not trackable.is_tracked()
        assert not trackable.is_failed()

        # Mark as tracked
        trackable.mark_tracked()
        assert trackable.is_tracked()

        # Mark as failed
        trackable.mark_failed()
        assert trackable.is_failed()

    def test_should_retry(self):
        """Test should_retry logic."""

        @with_state
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")

        # Should retry if failed and under max retries
        trackable.mark_failed()
        assert trackable.should_retry(max_retries=3)

        # Should not retry after max retries
        for _ in range(3):
            trackable.mark_failed()

        assert not trackable.should_retry(max_retries=3)


class TestWithLoggingCapability:
    """Test with_logging capability decorator."""

    def test_with_logging_decorator(self):
        """Test applying with_logging capability."""

        @with_logging
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")

        assert has_capability(trackable, "logging")
        assert hasattr(trackable, "to_log_dict")

    def test_to_log_dict(self):
        """Test converting to log dictionary."""

        @with_logging
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="impression_0", value="https://example.com/imp")

        log_dict = trackable.to_log_dict()

        assert "key" in log_dict
        assert log_dict["key"] == "impression_0"
        assert "value" in log_dict or "url" in log_dict


class TestTrackableFullCapability:
    """Test trackable_full decorator (all capabilities)."""

    def test_trackable_full_decorator(self):
        """Test applying all capabilities."""

        @trackable_full
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com?t=[TIMESTAMP]")

        # Should have all capabilities
        assert has_capability(trackable, "macros")
        assert has_capability(trackable, "state")
        assert has_capability(trackable, "logging")
        assert has_capability(trackable, "http_send")

    @pytest.mark.asyncio
    async def test_trackable_full_send_with(self):
        """Test send_with method on trackable_full."""

        @trackable_full
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com?cid=[CREATIVE_ID]")

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Send with macros
        macros = {"CREATIVE_ID": "creative-789"}
        success = await trackable.send_with(mock_client, macros)

        assert success is True
        mock_client.get.assert_called_once()

        # Verify macro substitution in request
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "creative-789" in url


class TestHasCapability:
    """Test has_capability helper function."""

    def test_has_capability_true(self):
        """Test has_capability returns True for existing capability."""

        @with_macros
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")
        assert has_capability(trackable, "macros") is True

    def test_has_capability_false(self):
        """Test has_capability returns False for missing capability."""
        trackable = TrackableEvent(key="test", value="https://example.com")
        assert has_capability(trackable, "macros") is False

    def test_has_capability_multiple(self):
        """Test has_capability with multiple capabilities."""

        @trackable_full
        class TestTrackable(TrackableEvent):
            pass

        trackable = TestTrackable(key="test", value="https://example.com")

        assert has_capability(trackable, "macros") is True
        assert has_capability(trackable, "state") is True
        assert has_capability(trackable, "logging") is True
        assert has_capability(trackable, "http_send") is True
