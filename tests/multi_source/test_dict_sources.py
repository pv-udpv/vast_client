"""Tests for dict-based source configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from vast_client.multi_source import VastFetchConfig, FetchStrategy, FetchMode
from vast_client.multi_source.fetcher import _normalize_source


class TestNormalizeSource:
    """Test _normalize_source helper function."""

    def test_normalize_url_string(self):
        """Test normalizing a simple URL string."""
        url, params, headers = _normalize_source("https://ads.example.com/vast")

        assert url == "https://ads.example.com/vast"
        assert params == {}
        assert headers == {}

    def test_normalize_url_with_global_params(self):
        """Test normalizing URL with global params."""
        url, params, headers = _normalize_source(
            "https://ads.example.com/vast",
            global_params={"slot": "pre-roll"},
            global_headers={"User-Agent": "Device/1.0"}
        )

        assert url == "https://ads.example.com/vast"
        assert params == {"slot": "pre-roll"}
        assert headers == {"User-Agent": "Device/1.0"}

    def test_normalize_dict_with_base_url(self):
        """Test normalizing dict config with base_url."""
        source = {
            "base_url": "https://ads.example.com/vast",
            "params": {"publisher": "acme"},
            "headers": {"X-Custom": "value"}
        }

        url, params, headers = _normalize_source(source)

        assert url == "https://ads.example.com/vast"
        assert params == {"publisher": "acme"}
        assert headers == {"X-Custom": "value"}

    def test_normalize_dict_with_url_key(self):
        """Test normalizing dict config with 'url' key."""
        source = {
            "url": "https://ads.example.com/vast",
            "params": {"slot": "mid-roll"}
        }

        url, params, headers = _normalize_source(source)

        assert url == "https://ads.example.com/vast"
        assert params == {"slot": "mid-roll"}

    def test_normalize_dict_merges_global_params(self):
        """Test that dict config merges with global params."""
        source = {
            "base_url": "https://ads.example.com/vast",
            "params": {"publisher": "acme"}
        }

        url, params, headers = _normalize_source(
            source,
            global_params={"slot": "pre-roll", "version": "4.0"},
            global_headers={"Accept": "application/xml"}
        )

        assert url == "https://ads.example.com/vast"
        # Source params override global params
        assert params == {"slot": "pre-roll", "version": "4.0", "publisher": "acme"}
        assert headers == {"Accept": "application/xml"}

    def test_normalize_dict_source_params_override_global(self):
        """Test that source params override global params."""
        source = {
            "base_url": "https://ads.example.com/vast",
            "params": {"slot": "mid-roll"},  # Override
            "headers": {"User-Agent": "CTV/2.0"}  # Override
        }

        url, params, headers = _normalize_source(
            source,
            global_params={"slot": "pre-roll", "publisher": "acme"},
            global_headers={"User-Agent": "Device/1.0", "Accept": "application/xml"}
        )

        assert params["slot"] == "mid-roll"  # Source overrides global
        assert params["publisher"] == "acme"  # Global preserved
        assert headers["User-Agent"] == "CTV/2.0"  # Source overrides global
        assert headers["Accept"] == "application/xml"  # Global preserved

    def test_normalize_dict_without_url_raises_error(self):
        """Test that dict without URL raises ValueError."""
        source = {"params": {"slot": "pre-roll"}}

        with pytest.raises(ValueError, match="must have 'base_url' or 'url'"):
            _normalize_source(source)

    def test_normalize_invalid_type_raises_error(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError, match="Source must be str or dict"):
            _normalize_source(123)


class TestVastFetchConfigWithDicts:
    """Test VastFetchConfig with dict sources."""

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

    def test_config_accepts_mixed_sources(self):
        """Test config accepts mixed string and dict sources."""
        config = VastFetchConfig(sources=[
            "https://ads1.com/vast",
            {"base_url": "https://ads2.com/vast", "params": {"publisher": "acme"}},
            "https://ads3.com/vast"
        ])

        assert len(config.sources) == 3
        assert isinstance(config.sources[0], str)
        assert isinstance(config.sources[1], dict)
        assert isinstance(config.sources[2], str)

    def test_config_with_dict_fallbacks(self):
        """Test config with dict fallback sources."""
        config = VastFetchConfig(
            sources=["https://primary.com/vast"],
            fallbacks=[
                {"base_url": "https://fallback1.com/vast", "params": {"fallback": "1"}},
                {"base_url": "https://fallback2.com/vast", "params": {"fallback": "2"}}
            ]
        )

        assert len(config.fallbacks) == 2
        assert isinstance(config.fallbacks[0], dict)
        assert config.fallbacks[0]["params"]["fallback"] == "1"


@pytest.mark.asyncio
class TestFetcherWithDictSources:
    """Test fetcher with dict-based source configurations."""

    async def test_fetch_with_dict_source(self, mock_http_client_success, mock_vast_response):
        """Test fetching with dict source configuration."""
        from vast_client.multi_source.fetcher import VastMultiSourceFetcher

        fetcher = VastMultiSourceFetcher()
        strategy = FetchStrategy(mode=FetchMode.PARALLEL, timeout=10.0)

        sources = [
            {
                "base_url": "https://ads.example.com/vast",
                "params": {"slot": "pre-roll", "publisher": "acme"},
                "headers": {"X-Custom": "value"}
            }
        ]

        result = await fetcher.fetch_all(
            sources=sources,
            strategy=strategy,
            http_client=mock_http_client_success
        )

        assert result.success is True
        assert result.raw_response == mock_vast_response

    async def test_fetch_with_mixed_sources(self, mock_http_client_success, mock_vast_response):
        """Test fetching with mixed string and dict sources."""
        from vast_client.multi_source.fetcher import VastMultiSourceFetcher

        fetcher = VastMultiSourceFetcher()
        strategy = FetchStrategy(mode=FetchMode.PARALLEL, timeout=10.0)

        sources = [
            "https://ads1.example.com/vast",
            {
                "base_url": "https://ads2.example.com/vast",
                "params": {"publisher": "acme"}
            }
        ]

        result = await fetcher.fetch_all(
            sources=sources,
            strategy=strategy,
            http_client=mock_http_client_success
        )

        assert result.success is True
