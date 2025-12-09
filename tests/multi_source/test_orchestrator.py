"""Tests for multi-source orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vast_client.multi_source import (
    VastMultiSourceOrchestrator,
    VastFetchConfig,
    FetchStrategy,
    FetchMode,
    VastParseFilter,
    MediaType,
)
from vast_client.parser import VastParser


@pytest.mark.asyncio
class TestVastMultiSourceOrchestrator:
    """Test VastMultiSourceOrchestrator."""

    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = VastMultiSourceOrchestrator()

        assert orchestrator.parser is not None
        assert orchestrator.fetcher is not None
        assert orchestrator.ssl_verify is True

    async def test_orchestrator_with_custom_parser(self):
        """Test orchestrator with custom parser."""
        parser = VastParser()
        orchestrator = VastMultiSourceOrchestrator(parser=parser)

        assert orchestrator.parser is parser

    async def test_execute_pipeline_no_sources(self):
        """Test pipeline execution with no sources."""
        orchestrator = VastMultiSourceOrchestrator()
        config = VastFetchConfig(sources=[])

        with pytest.raises(ValueError, match="must have at least one source"):
            await orchestrator.execute_pipeline(config)

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_execute_pipeline_single_source_success(
        self, mock_get_client, mock_vast_response, mock_http_client_success
    ):
        """Test successful single-source pipeline execution."""
        mock_get_client.return_value = mock_http_client_success

        orchestrator = VastMultiSourceOrchestrator()
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"],
            auto_track=False,  # Disable tracking for this test
        )

        result = await orchestrator.execute_pipeline(config)

        assert result.success is True
        assert result.source_url == "https://ads.example.com/vast"
        assert result.parsed_data is not None
        assert result.parsed_data["ad_system"] == "Test Ad System"

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_execute_pipeline_with_fallback(
        self, mock_get_client, mock_vast_response
    ):
        """Test pipeline execution with fallback."""
        # Primary source fails all retries (3 attempts total: initial + 2 retries)
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 404
        mock_response_fail.raise_for_status = MagicMock(
            side_effect=Exception("Not Found")
        )

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.text = mock_vast_response
        mock_response_success.headers = {"content-type": "application/xml"}
        mock_response_success.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First 3 calls fail (primary with retries), 4th succeeds (fallback)
        mock_client.get = AsyncMock(
            side_effect=[
                mock_response_fail,
                mock_response_fail,
                mock_response_fail,
                mock_response_success,
            ]
        )
        mock_get_client.return_value = mock_client

        orchestrator = VastMultiSourceOrchestrator()
        config = VastFetchConfig(
            sources=["https://ads1.example.com/vast"],
            fallbacks=["https://fallback.example.com/vast"],
            auto_track=False,
        )

        result = await orchestrator.execute_pipeline(config)

        assert result.success is True
        assert result.metadata.get("used_fallback") is True

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_execute_pipeline_with_filter_match(
        self, mock_get_client, mock_vast_response, mock_http_client_success
    ):
        """Test pipeline with filter that matches."""
        mock_get_client.return_value = mock_http_client_success

        orchestrator = VastMultiSourceOrchestrator()
        filter = VastParseFilter(
            media_types=[MediaType.VIDEO], min_duration=10, max_duration=30
        )
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"],
            parse_filter=filter,
            auto_track=False,
        )

        result = await orchestrator.execute_pipeline(config)

        assert result.success is True
        assert result.parsed_data is not None

    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_execute_pipeline_with_filter_no_match(
        self, mock_get_client, mock_vast_response, mock_http_client_success
    ):
        """Test pipeline with filter that doesn't match."""
        mock_get_client.return_value = mock_http_client_success

        orchestrator = VastMultiSourceOrchestrator()
        # Filter requires duration > 60, but response has 15 seconds
        filter = VastParseFilter(min_duration=60)
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"],
            parse_filter=filter,
            auto_track=False,
        )

        result = await orchestrator.execute_pipeline(config)

        assert result.success is False
        assert any("filter" in str(err).lower() for err in result.errors)

    @patch("vast_client.multi_source.orchestrator.get_tracking_http_client")
    @patch("vast_client.multi_source.orchestrator.get_main_http_client")
    async def test_execute_pipeline_with_auto_track(
        self,
        mock_get_main_client,
        mock_get_tracking_client,
        mock_vast_response,
        mock_http_client_success,
    ):
        """Test pipeline with auto_track enabled."""
        mock_get_main_client.return_value = mock_http_client_success
        mock_get_tracking_client.return_value = mock_http_client_success

        orchestrator = VastMultiSourceOrchestrator()
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"], auto_track=True
        )

        result = await orchestrator.execute_pipeline(config)

        assert result.success is True
        # Tracking may have been attempted (check metadata)
        # Note: Actual tracking might fail in tests without real HTTP, that's OK
