"""Tests for upstream-based source configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from vast_client.multi_source import VastFetchConfig, FetchStrategy, FetchMode
from vast_client.multi_source.upstream import create_upstream, HttpUpstream, MockUpstream


class TestCreateUpstream:
    """Test create_upstream factory function."""

    def test_create_from_url_string(self):
        """Test creating upstream from URL string."""
        upstream = create_upstream("https://ads.example.com/vast")

        assert isinstance(upstream, HttpUpstream)
        assert upstream.base_url == "https://ads.example.com/vast"

    def test_create_from_dict_with_base_url(self):
        """Test creating upstream from dict config with base_url."""
        source = {
            "base_url": "https://ads.example.com/vast",
            "params": {"publisher": "acme"},
            "headers": {"X-Custom": "value"}
        }

        upstream = create_upstream(source)

        assert isinstance(upstream, HttpUpstream)
        assert upstream.base_url == "https://ads.example.com/vast"
        assert upstream.base_params == {"publisher": "acme"}
        assert upstream.base_headers == {"X-Custom": "value"}

    def test_create_from_dict_with_url_key(self):
        """Test creating upstream from dict config with 'url' key."""
        source = {
            "url": "https://ads.example.com/vast",
            "params": {"slot": "mid-roll"}
        }

        upstream = create_upstream(source)

        assert isinstance(upstream, HttpUpstream)
        assert upstream.base_url == "https://ads.example.com/vast"
        assert upstream.base_params == {"slot": "mid-roll"}

    def test_create_from_dict_without_url_raises_error(self):
        """Test that dict without URL raises ValueError."""
        source = {"params": {"slot": "pre-roll"}}

        with pytest.raises(ValueError, match="must have 'base_url' or 'url'"):
            create_upstream(source)

    def test_create_from_invalid_type_raises_error(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError, match="Source must be str, dict, or VastUpstream"):
            create_upstream(123)

    def test_create_from_upstream_returns_same(self):
        """Test that passing an upstream returns it as-is."""
        mock_upstream = MockUpstream("<VAST>test</VAST>")
        result = create_upstream(mock_upstream)

        assert result is mock_upstream


class TestVastFetchConfigWithUpstreams:
    """Test VastFetchConfig with upstream sources."""

    def test_config_accepts_string_sources(self):
        """Test config accepts string sources."""
        config = VastFetchConfig(sources=["https://ads1.com/vast", "https://ads2.com/vast"])

        assert len(config.sources) == 2
        assert config.sources[0] == "https://ads1.com/vast"
        assert config.sources[1] == "https://ads2.com/vast"

    def test_config_accepts_dict_sources(self):
        """Test config accepts dict sources."""
        config = VastFetchConfig(sources=[
            {"base_url": "https://ads1.com/vast", "params": {"slot": "pre-roll"}},
            {"base_url": "https://ads2.com/vast", "params": {"slot": "mid-roll"}}
        ])

        assert len(config.sources) == 2
        assert isinstance(config.sources[0], dict)
        assert config.sources[0]["base_url"] == "https://ads1.com/vast"

    def test_config_accepts_upstream_objects(self):
        """Test config accepts upstream objects."""
        mock1 = MockUpstream("<VAST>1</VAST>")
        mock2 = MockUpstream("<VAST>2</VAST>")

        config = VastFetchConfig(sources=[mock1, mock2])

        assert len(config.sources) == 2
        assert config.sources[0] is mock1
        assert config.sources[1] is mock2

    def test_config_accepts_mixed_sources(self):
        """Test config accepts mixed string, dict, and upstream sources."""
        mock_upstream = MockUpstream("<VAST>test</VAST>")

        config = VastFetchConfig(sources=[
            "https://ads1.com/vast",
            {"base_url": "https://ads2.com/vast", "params": {"publisher": "acme"}},
            mock_upstream
        ])

        assert len(config.sources) == 3
        assert isinstance(config.sources[0], str)
        assert isinstance(config.sources[1], dict)
        assert config.sources[2] is mock_upstream

    def test_config_with_upstream_fallbacks(self):
        """Test config with upstream fallback sources."""
        config = VastFetchConfig(
            sources=["https://primary.com/vast"],
            fallbacks=[
                {"base_url": "https://fallback1.com/vast", "params": {"fallback": "1"}},
                MockUpstream("<VAST>fallback</VAST>")
            ]
        )

        assert len(config.fallbacks) == 2
        assert isinstance(config.fallbacks[0], dict)
        assert isinstance(config.fallbacks[1], MockUpstream)


@pytest.mark.asyncio
class TestFetcherWithUpstreams:
    """Test fetcher with upstream-based source configurations."""

    async def test_fetch_with_mock_upstream(self):
        """Test fetching with mock upstream."""
        from vast_client.multi_source.fetcher import VastMultiSourceFetcher
        import httpx

        fetcher = VastMultiSourceFetcher()
        strategy = FetchStrategy(mode=FetchMode.PARALLEL, timeout=10.0)

        mock_xml = "<VAST>test</VAST>"
        mock_upstream = MockUpstream(mock_xml)

        http_client = httpx.AsyncClient()
        result = await fetcher.fetch_all(
            sources=[mock_upstream],
            strategy=strategy,
            http_client=http_client
        )

        assert result.success is True
        assert result.raw_response == mock_xml
        await http_client.aclose()

    async def test_fetch_with_mixed_sources(self, mock_http_client_success, mock_vast_response):
        """Test fetching with mixed string, dict, and upstream sources."""
        from vast_client.multi_source.fetcher import VastMultiSourceFetcher

        fetcher = VastMultiSourceFetcher()
        strategy = FetchStrategy(mode=FetchMode.PARALLEL, timeout=10.0)

        sources = [
            "https://ads1.example.com/vast",
            {
                "base_url": "https://ads2.example.com/vast",
                "params": {"publisher": "acme"}
            },
            MockUpstream(mock_vast_response)
        ]

        result = await fetcher.fetch_all(
            sources=sources,
            strategy=strategy,
            http_client=mock_http_client_success
        )

        # Mock upstream should succeed immediately
        assert result.success is True
