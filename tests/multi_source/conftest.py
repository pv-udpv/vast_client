"""Pytest configuration and fixtures for multi-source tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from vast_client.multi_source import (
    VastFetchConfig,
    FetchStrategy,
    FetchMode,
    VastParseFilter,
    MediaType,
)


@pytest.fixture
def fetch_strategy():
    """Create default fetch strategy."""
    return FetchStrategy(
        mode=FetchMode.PARALLEL,
        timeout=10.0,
        per_source_timeout=5.0,
        max_retries=2,
        retry_delay=0.1,
    )


@pytest.fixture
def fetch_config(fetch_strategy):
    """Create default fetch configuration."""
    return VastFetchConfig(
        sources=["https://ads.example.com/vast"],
        fallbacks=[],
        strategy=fetch_strategy,
        params={},
        headers={},
        auto_track=False,
    )


@pytest.fixture
def multi_source_config(fetch_strategy):
    """Create multi-source fetch configuration."""
    return VastFetchConfig(
        sources=[
            "https://ads1.example.com/vast",
            "https://ads2.example.com/vast",
        ],
        fallbacks=["https://fallback.example.com/vast"],
        strategy=fetch_strategy,
        params={},
        headers={},
        auto_track=False,
    )


@pytest.fixture
def parse_filter():
    """Create default parse filter."""
    return VastParseFilter(
        media_types=[MediaType.VIDEO],
        min_duration=10,
        max_duration=60,
    )


@pytest.fixture
def mock_vast_response():
    """Create mock VAST XML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="test-ad-001">
    <InLine>
      <AdSystem>Test Ad System</AdSystem>
      <AdTitle>Test Ad Title</AdTitle>
      <Impression><![CDATA[https://tracking.example.com/impression]]></Impression>
      <Creatives>
        <Creative id="creative-001" adId="ad-001">
          <Linear>
            <Duration>00:00:15</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4" width="1280" height="720">
                <![CDATA[https://media.example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://tracking.example.com/start]]></Tracking>
              <Tracking event="complete"><![CDATA[https://tracking.example.com/complete]]></Tracking>
            </TrackingEvents>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


@pytest.fixture
def mock_http_client_success(mock_vast_response):
    """Create mock HTTP client that returns successful responses."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = mock_vast_response
    mock_response.headers = {"content-type": "application/xml"}
    mock_response.raise_for_status = MagicMock()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_http_client_failure():
    """Create mock HTTP client that returns failure responses."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
    )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    return client
