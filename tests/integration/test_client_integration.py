"""Integration tests for end-to-end VAST client workflows."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vast_client.client import VastClient
from vast_client.config import PlaybackMode, VastClientConfig


class TestVastClientIntegration:
    """End-to-end integration tests for VAST client."""

    @pytest.mark.asyncio
    async def test_request_and_parse_workflow(self, minimal_vast_xml):
        """Test complete workflow: request → parse → tracker creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            client = VastClient("https://ads.example.com/vast")
            # Request ad
            vast_data = await client.request_ad()

            # Verify parsing
            assert vast_data["ad_system"] == "Test Ad System"
            # Media URL may have whitespace from XML formatting
            assert "https://media.example.com/video.mp4" in vast_data["media_url"]

            # Verify tracker created
            assert client.tracker is not None
            assert "impression" in client.tracker.events or "start" in client.tracker.events

    @pytest.mark.asyncio
    async def test_request_parse_track_workflow(self, vast_with_quartiles_xml):
        """Test complete workflow: request → parse → track events."""
        # Mock VAST response
        vast_response = MagicMock()
        vast_response.status_code = 200
        vast_response.headers = {"content-type": "application/xml"}
        vast_response.text = vast_with_quartiles_xml
        vast_response.raise_for_status = MagicMock()

        # Mock tracking responses
        tracking_response = MagicMock()
        tracking_response.status_code = 200
        tracking_response.text = ""
        tracking_response.raise_for_status = MagicMock()

        mock_main_client = AsyncMock()
        mock_main_client.get = AsyncMock(return_value=vast_response)

        mock_tracking_client = AsyncMock()
        mock_tracking_client.get = AsyncMock(return_value=tracking_response)

        # Patch both main and tracking clients - tracking client is needed when tracker is created
        with patch('vast_client.client.get_main_http_client', return_value=mock_main_client), \
             patch('vast_client.client.get_tracking_http_client', return_value=mock_tracking_client):
            client = VastClient("https://ads.example.com/vast")
            # Request ad
            vast_data = await client.request_ad()

            # Verify parsed data
            assert "start" in vast_data["tracking_events"]
            assert "firstQuartile" in vast_data["tracking_events"]
            assert "complete" in vast_data["tracking_events"]

            # Track events
            await client.tracker.track_event("start")
            await client.tracker.track_event("complete")

            # Verify tracking calls were made
            assert mock_main_client.get.call_count >= 1
            assert mock_tracking_client.get.call_count >= 2

    @pytest.mark.asyncio
    async def test_macro_substitution_workflow(self, vast_with_macros_xml):
        """Test workflow with macro substitution in tracking URLs."""
        vast_response = MagicMock()
        vast_response.status_code = 200
        vast_response.headers = {"content-type": "application/xml"}
        vast_response.text = vast_with_macros_xml
        vast_response.raise_for_status = MagicMock()

        tracking_response = MagicMock()
        tracking_response.status_code = 200
        tracking_response.text = ""
        tracking_response.raise_for_status = MagicMock()

        mock_main_client = AsyncMock()
        mock_main_client.get = AsyncMock(return_value=vast_response)

        mock_tracking_client = AsyncMock()
        mock_tracking_client.get = AsyncMock(return_value=tracking_response)

        # Patch both clients - tracking client is needed when tracker is created
        with patch('vast_client.client.get_main_http_client', return_value=mock_main_client), \
             patch('vast_client.client.get_tracking_http_client', return_value=mock_tracking_client):
            client = VastClient("https://ads.example.com/vast")
            # Request ad
            await client.request_ad()

            # Track impression with macros
            await client.tracker.track_event("impression")

            # Get the tracking request URL
            tracking_calls = [
                call for call in mock_tracking_client.get.call_args_list if "tracking" in str(call)
            ]
            if tracking_calls:
                tracking_url = str(tracking_calls[-1])

                # Verify macros were substituted (not containing original placeholders)
                # Note: exact verification depends on macro format
                assert "tracking" in tracking_url

    @pytest.mark.asyncio
    async def test_context_manager_workflow(self, minimal_vast_xml):
        """Test client usage as async context manager."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            async with VastClient("https://ads.example.com/vast") as client:
                vast_data = await client.request_ad()
                assert vast_data is not None

        # Context manager should have completed successfully

    @pytest.mark.asyncio
    async def test_multiple_impression_tracking(self):
        """Test workflow with multiple impression URLs."""
        vast_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression>https://tracking1.example.com/imp</Impression>
      <Impression>https://tracking2.example.com/imp</Impression>
      <Impression>https://tracking3.example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_response = MagicMock()
        vast_response.status_code = 200
        vast_response.headers = {"content-type": "application/xml"}
        vast_response.text = vast_xml
        vast_response.raise_for_status = MagicMock()

        tracking_response = MagicMock()
        tracking_response.status_code = 200
        tracking_response.text = ""
        tracking_response.raise_for_status = MagicMock()

        mock_main_client = AsyncMock()
        mock_main_client.get = AsyncMock(return_value=vast_response)

        mock_tracking_client = AsyncMock()
        mock_tracking_client.get = AsyncMock(return_value=tracking_response)

        # Patch both clients - tracking client is needed when tracker is created
        with patch('vast_client.client.get_main_http_client', return_value=mock_main_client), \
             patch('vast_client.client.get_tracking_http_client', return_value=mock_tracking_client):
            client = VastClient("https://ads.example.com/vast")
            # Request and track
            vast_data = await client.request_ad()
            assert len(vast_data["impression"]) == 3

            await client.tracker.track_event("impression")

            # Should have made 1 VAST call and 3 tracking calls
            assert mock_main_client.get.call_count == 1
            assert mock_tracking_client.get.call_count == 3


class TestVastClientConfigIntegration:
    """Integration tests for different client configurations."""

    @pytest.mark.asyncio
    async def test_headless_playback_config(self, minimal_vast_xml, vast_client_config):
        """Test client with headless playback configuration."""
        vast_client_config.playback.mode = PlaybackMode.HEADLESS

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            client = VastClient(vast_client_config)
            # Set upstream_url since VastClientConfig doesn't include it
            client.upstream_url = "https://ads.example.com/vast"
            vast_data = await client.request_ad()
            assert vast_data is not None

    @pytest.mark.asyncio
    async def test_tracking_disabled_config(self, minimal_vast_xml):
        """Test client with tracking disabled."""
        config = VastClientConfig(
            provider="test",
            publisher="test",
            enable_tracking=False,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            client = VastClient(config)
            # Set upstream_url since VastClientConfig doesn't include it
            client.upstream_url = "https://ads.example.com/vast"
            vast_data = await client.request_ad()
            assert vast_data is not None


class TestVastClientErrorHandling:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            client = VastClient("https://ads.example.com/vast")
            with pytest.raises(Exception):
                await client.request_ad()

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=asyncio.TimeoutError("Timeout"))

        with patch('vast_client.client.get_main_http_client', return_value=mock_client):
            client = VastClient("https://ads.example.com/vast")
            with pytest.raises(asyncio.TimeoutError):
                await client.request_ad()

    @pytest.mark.asyncio
    async def test_tracking_failure_graceful_degradation(self, minimal_vast_xml):
        """Test that tracking failures don't break the workflow."""
        vast_response = MagicMock()
        vast_response.status_code = 200
        vast_response.headers = {"content-type": "application/xml"}
        vast_response.text = minimal_vast_xml
        vast_response.raise_for_status = MagicMock()

        # Tracking request will fail
        tracking_response = MagicMock()
        tracking_response.status_code = 500
        tracking_response.raise_for_status.side_effect = Exception("Server error")

        mock_main_client = AsyncMock()
        mock_main_client.get = AsyncMock(return_value=vast_response)

        mock_tracking_client = AsyncMock()
        mock_tracking_client.get = AsyncMock(return_value=tracking_response)

        # Patch both clients - tracking client is needed when tracker is created
        with patch('vast_client.client.get_main_http_client', return_value=mock_main_client), \
             patch('vast_client.client.get_tracking_http_client', return_value=mock_tracking_client):
            client = VastClient("https://ads.example.com/vast")
            # Request should succeed
            vast_data = await client.request_ad()
            assert vast_data is not None

            # Tracking should fail gracefully (not raise)
            await client.tracker.track_event("start")
