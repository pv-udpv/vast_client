"""Tests for multi-source fetch configuration."""

import pytest

from vast_client.multi_source import (
    FetchMode,
    FetchStrategy,
    VastFetchConfig,
    FetchResult,
    MediaType,
)


class TestFetchStrategy:
    """Test FetchStrategy configuration."""

    def test_default_strategy(self):
        """Test default fetch strategy."""
        strategy = FetchStrategy()

        assert strategy.mode == FetchMode.PARALLEL
        assert strategy.timeout == 30.0
        assert strategy.per_source_timeout == 10.0
        assert strategy.max_retries == 2
        assert strategy.retry_delay == 1.0
        assert strategy.stop_on_first_success is False

    def test_custom_strategy(self):
        """Test custom fetch strategy."""
        strategy = FetchStrategy(
            mode=FetchMode.SEQUENTIAL,
            timeout=60.0,
            per_source_timeout=20.0,
            max_retries=5,
            retry_delay=2.0,
            stop_on_first_success=True,
        )

        assert strategy.mode == FetchMode.SEQUENTIAL
        assert strategy.timeout == 60.0
        assert strategy.per_source_timeout == 20.0
        assert strategy.max_retries == 5
        assert strategy.retry_delay == 2.0
        assert strategy.stop_on_first_success is True


class TestVastFetchConfig:
    """Test VastFetchConfig."""

    def test_single_source_config(self):
        """Test single-source configuration (margin case)."""
        config = VastFetchConfig(sources=["https://ads.example.com/vast"])

        assert len(config.sources) == 1
        assert config.sources[0] == "https://ads.example.com/vast"
        assert len(config.fallbacks) == 0
        assert config.auto_track is True

    def test_multi_source_config(self):
        """Test multi-source configuration."""
        config = VastFetchConfig(
            sources=["https://ads1.com/vast", "https://ads2.com/vast"],
            fallbacks=["https://fallback.com/vast"],
        )

        assert len(config.sources) == 2
        assert len(config.fallbacks) == 1
        assert config.sources[0] == "https://ads1.com/vast"
        assert config.sources[1] == "https://ads2.com/vast"
        assert config.fallbacks[0] == "https://fallback.com/vast"

    def test_config_with_params_and_headers(self):
        """Test configuration with additional params and headers."""
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"],
            params={"slot": "pre-roll", "publisher": "acme"},
            headers={"User-Agent": "CTV-Device/1.0"},
        )

        assert config.params == {"slot": "pre-roll", "publisher": "acme"}
        assert config.headers == {"User-Agent": "CTV-Device/1.0"}

    def test_config_with_custom_strategy(self):
        """Test configuration with custom strategy."""
        strategy = FetchStrategy(mode=FetchMode.SEQUENTIAL, timeout=15.0)
        config = VastFetchConfig(
            sources=["https://ads.example.com/vast"], strategy=strategy
        )

        assert config.strategy.mode == FetchMode.SEQUENTIAL
        assert config.strategy.timeout == 15.0


class TestFetchResult:
    """Test FetchResult."""

    def test_successful_result(self):
        """Test successful fetch result."""
        result = FetchResult(
            success=True,
            source_url="https://ads.example.com/vast",
            raw_response="<?xml version='1.0'?>...",
            parsed_data={"ad_system": "Test"},
        )

        assert result.success is True
        assert result.source_url == "https://ads.example.com/vast"
        assert result.raw_response == "<?xml version='1.0'?>..."
        assert result.parsed_data == {"ad_system": "Test"}
        assert len(result.errors) == 0

    def test_failed_result(self):
        """Test failed fetch result."""
        result = FetchResult(
            success=False,
            errors=[
                {"source": "https://ads1.com/vast", "error": "Timeout"},
                {"source": "https://ads2.com/vast", "error": "HTTP 404"},
            ],
        )

        assert result.success is False
        assert result.source_url is None
        assert result.raw_response == ""
        assert result.parsed_data is None
        assert len(result.errors) == 2
        assert result.errors[0]["source"] == "https://ads1.com/vast"
        assert result.errors[1]["error"] == "HTTP 404"

    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = FetchResult(
            success=True,
            source_url="https://ads.example.com/vast",
            raw_response="<?xml version='1.0'?>...",
            metadata={"elapsed_time": 1.5, "used_fallback": False},
        )

        assert result.metadata["elapsed_time"] == 1.5
        assert result.metadata["used_fallback"] is False


class TestFetchMode:
    """Test FetchMode enum."""

    def test_fetch_modes(self):
        """Test all fetch modes."""
        assert FetchMode.PARALLEL == "parallel"
        assert FetchMode.SEQUENTIAL == "sequential"
        assert FetchMode.RACE == "race"


class TestMediaType:
    """Test MediaType enum."""

    def test_media_types(self):
        """Test all media types."""
        assert MediaType.VIDEO == "video"
        assert MediaType.AUDIO == "audio"
        assert MediaType.ALL == "all"
