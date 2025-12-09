"""Integration tests for multi-source functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vast_client import VastClient
from vast_client.multi_source import (
    VastMultiSourceOrchestrator,
    VastFetchConfig,
    FetchMode,
)


@pytest.mark.asyncio
class TestVastClientMultiSourceIntegration:
    """Test VastClient integration with multi-source orchestrator."""

    def test_client_has_orchestrator(self):
        """Test that VastClient has orchestrator attribute."""
        client = VastClient("https://ads.example.com/vast")

        assert hasattr(client, "_orchestrator")
        assert isinstance(client._orchestrator, VastMultiSourceOrchestrator)

    def test_client_multi_source_property(self):
        """Test multi_source property access."""
        client = VastClient("https://ads.example.com/vast")

        orchestrator = client.multi_source
        assert isinstance(orchestrator, VastMultiSourceOrchestrator)

    @patch("vast_client.client.get_main_http_client")
    async def test_request_ad_backward_compatibility(
        self, mock_get_client, mock_vast_response
    ):
        """Test that request_ad still works (backward compatibility)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_vast_response
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        client = VastClient("https://ads.example.com/vast")
        result = await client.request_ad()

        # Should return parsed VAST data
        assert isinstance(result, dict)
        assert result["ad_system"] == "Test Ad System"

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_request_ad_with_fallback_success(
        self, mock_get_client, mock_vast_response
    ):
        """Test request_ad_with_fallback method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_vast_response
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        client = VastClient("https://ads.example.com/vast")
        result = await client.request_ad_with_fallback(
            primary="https://ads1.example.com/vast",
            fallbacks=["https://ads2.example.com/vast"],
            auto_track=False,
        )

        assert isinstance(result, dict)
        assert result["ad_system"] == "Test Ad System"

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_request_ad_with_fallback_all_fail(self, mock_get_client):
        """Test request_ad_with_fallback when all sources fail."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Not Found"))

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        client = VastClient("https://ads.example.com/vast")

        with pytest.raises(Exception, match="All sources failed"):
            await client.request_ad_with_fallback(
                primary="https://ads1.example.com/vast",
                fallbacks=["https://ads2.example.com/vast"],
            )

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_direct_orchestrator_usage(
        self, mock_get_client, mock_vast_response
    ):
        """Test direct usage of orchestrator via client.multi_source."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_vast_response
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        client = VastClient("https://ads.example.com/vast")

        # Direct orchestrator usage
        config = VastFetchConfig(
            sources=["https://ads1.com/vast", "https://ads2.com/vast"],
            auto_track=False,
        )

        result = await client.multi_source.execute_pipeline(config)

        assert result.success is True
        assert result.parsed_data is not None
        assert result.parsed_data["ad_system"] == "Test Ad System"


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @patch("vast_client.client.get_main_http_client")
    async def test_simple_url_initialization(
        self, mock_get_client, mock_vast_response
    ):
        """Test simple URL initialization still works."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_vast_response
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        # Old way - should still work
        client = VastClient("https://ads.example.com/vast")
        result = await client.request_ad()

        assert isinstance(result, dict)
        assert "ad_system" in result

    @patch("vast_client.client.get_main_http_client")
    async def test_from_uri_classmethod(self, mock_get_client, mock_vast_response):
        """Test from_uri classmethod still works."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_vast_response
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        # Old way - should still work
        client = VastClient.from_uri("https://ads.example.com/vast")
        result = await client.request_ad()

        assert isinstance(result, dict)
        assert "ad_system" in result

    def test_client_attributes_preserved(self):
        """Test that all client attributes are preserved."""
        client = VastClient("https://ads.example.com/vast")

        # Check legacy attributes
        assert hasattr(client, "upstream_url")
        assert hasattr(client, "embedded_params")
        assert hasattr(client, "embedded_headers")
        assert hasattr(client, "parser")
        assert hasattr(client, "tracker")
        assert hasattr(client, "logger")

        # Check new attributes
        assert hasattr(client, "_orchestrator")
        assert hasattr(client, "multi_source")
