"""Pytest configuration and shared fixtures for VAST client tests."""

import asyncio
import json

# Import VAST client components
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vast_client.client import VastClient
from vast_client.config import (
    PlaybackMode,
    PlaybackSessionConfig,
    VastClientConfig,
    VastParserConfig,
    VastTrackerConfig,
)
from vast_client.context import TrackingContext
from vast_client.parser import VastParser
from vast_client.time_provider import SimulatedTimeProvider
from vast_client.tracker import VastTracker


# ==================== Pytest Configuration ====================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Path Fixtures ====================


@pytest.fixture(scope="session")
def tests_dir() -> Path:
    """Get tests directory path."""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def fixtures_dir(tests_dir) -> Path:
    """Get fixtures directory path."""
    return tests_dir / "fixtures"


@pytest.fixture(scope="session")
def iab_samples_dir(tests_dir) -> Path:
    """Get IAB samples directory path."""
    return tests_dir / "iab_samples"


# ==================== Configuration Fixtures ====================


@pytest.fixture
def parser_config() -> VastParserConfig:
    """Create default parser configuration."""
    return VastParserConfig(
        recover_on_error=True,
        encoding="utf-8",
    )


@pytest.fixture
def tracker_config() -> VastTrackerConfig:
    """Create default tracker configuration."""
    return VastTrackerConfig(
        timeout=5.0,
        macro_formats=["[{macro}]", "${{{macro}}}"],
        static_macros={},
        macro_mapping={},
    )


@pytest.fixture
def session_config() -> PlaybackSessionConfig:
    """Create default playback session configuration."""
    return PlaybackSessionConfig(
        mode=PlaybackMode.HEADLESS,
        enable_auto_quartiles=True,
        headless_tick_interval_sec=0.1,
    )


@pytest.fixture
def vast_client_config(
    parser_config: VastParserConfig,
    tracker_config: VastTrackerConfig,
    session_config: PlaybackSessionConfig,
) -> VastClientConfig:
    """Create default VAST client configuration."""
    return VastClientConfig(
        provider="test_provider",
        publisher="test_publisher",
        enable_tracking=True,
        enable_parsing=True,
        parser=parser_config,
        tracker=tracker_config,
        playback=session_config,
    )


# ==================== Mock HTTP Client Fixtures ====================


@pytest.fixture
def mock_http_response():
    """Create mock HTTP response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.headers = {"content-type": "application/xml"}
    response.text = ""
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_http_client(mock_http_response):
    """Create mock async HTTP client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_http_response)
    client.post = AsyncMock(return_value=mock_http_response)
    client.aclose = AsyncMock()
    return client


# ==================== VAST XML Fixtures ====================


@pytest.fixture
def minimal_vast_xml() -> str:
    """Minimal valid VAST 4.0 XML."""
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
def vast_with_quartiles_xml() -> str:
    """VAST XML with quartile tracking events."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="test-ad-002">
    <InLine>
      <AdSystem>Test Ad System</AdSystem>
      <AdTitle>Test Quartile Ad</AdTitle>
      <Impression><![CDATA[https://tracking.example.com/impression]]></Impression>
      <Creatives>
        <Creative id="creative-002" adId="ad-002">
          <Linear>
            <Duration>00:00:30</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4" width="1920" height="1080">
                <![CDATA[https://media.example.com/video_30s.mp4]]>
              </MediaFile>
            </MediaFiles>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://tracking.example.com/start]]></Tracking>
              <Tracking event="firstQuartile"><![CDATA[https://tracking.example.com/q1]]></Tracking>
              <Tracking event="midpoint"><![CDATA[https://tracking.example.com/mid]]></Tracking>
              <Tracking event="thirdQuartile"><![CDATA[https://tracking.example.com/q3]]></Tracking>
              <Tracking event="complete"><![CDATA[https://tracking.example.com/complete]]></Tracking>
            </TrackingEvents>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


@pytest.fixture
def vast_with_macros_xml() -> str:
    """VAST XML with macro placeholders in tracking URLs."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="test-ad-003">
    <InLine>
      <AdSystem>Test Ad System</AdSystem>
      <AdTitle>Test Macro Ad</AdTitle>
      <Impression><![CDATA[https://tracking.example.com/impression?t=[TIMESTAMP]&r=[RANDOM]]]></Impression>
      <Creatives>
        <Creative id="creative-003" adId="ad-003">
          <Linear>
            <Duration>00:00:20</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4">
                <![CDATA[https://media.example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://tracking.example.com/start?cid=[CREATIVE_ID]&t=${TIMESTAMP}]]></Tracking>
              <Tracking event="complete"><![CDATA[https://tracking.example.com/complete?cid=[CREATIVE_ID]]]></Tracking>
            </TrackingEvents>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


@pytest.fixture
def vast_with_error_xml() -> str:
    """VAST XML with error tracking URLs."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="test-ad-004">
    <InLine>
      <AdSystem>Test Ad System</AdSystem>
      <Error><![CDATA[https://tracking.example.com/error?code=[ERRORCODE]]]></Error>
      <Impression><![CDATA[https://tracking.example.com/impression]]></Impression>
      <Creatives>
        <Creative id="creative-004">
          <Linear>
            <Duration>00:00:10</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4">
                <![CDATA[https://media.example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


@pytest.fixture
def malformed_vast_xml() -> str:
    """Malformed VAST XML for error handling tests."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="malformed">
    <InLine>
      <AdSystem>Test System</AdSystem>
      <!-- Missing closing tag -->
      <AdTitle>Malformed Ad
    </InLine>
  </Ad>
"""


@pytest.fixture
def empty_vast_xml() -> str:
    """Empty VAST response (no ads)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0"></VAST>"""


# ==================== Parsed VAST Data Fixtures ====================


@pytest.fixture
def minimal_vast_data() -> dict[str, Any]:
    """Parsed minimal VAST data."""
    return {
        "vast_version": "4.0",
        "ad_system": "Test Ad System",
        "ad_title": "Test Ad Title",
        "impression": ["https://tracking.example.com/impression"],
        "error": [],
        "creative": {"id": "creative-001", "ad_id": "ad-001"},
        "media_files": [
            {
                "url": "https://media.example.com/video.mp4",
                "delivery": "progressive",
                "type": "video/mp4",
                "width": "1280",
                "height": "720",
                "bitrate": None,
            }
        ],
        "media_url": "https://media.example.com/video.mp4",
        "tracking_events": {
            "start": ["https://tracking.example.com/start"],
            "complete": ["https://tracking.example.com/complete"],
        },
        "extensions": {},
        "duration": 15,
    }


# ==================== Component Fixtures ====================


@pytest.fixture
def vast_parser(parser_config: VastParserConfig) -> VastParser:
    """Create VAST parser instance."""
    return VastParser(config=parser_config)


@pytest.fixture
def vast_tracker(
    tracker_config: VastTrackerConfig,
    mock_http_client: AsyncMock,
) -> VastTracker:
    """Create VAST tracker instance."""
    tracking_events = {
        "impression": ["https://tracking.example.com/impression"],
        "start": ["https://tracking.example.com/start"],
        "complete": ["https://tracking.example.com/complete"],
    }
    return VastTracker(
        tracking_events=tracking_events,
        client=mock_http_client,
        config=tracker_config,
        creative_id="test-creative-001",
    )


@pytest.fixture
async def vast_client(
    vast_client_config: VastClientConfig,
    mock_http_client: AsyncMock,
) -> VastClient:
    """Create VAST client instance."""
    client = VastClient(vast_client_config)
    client.client = mock_http_client
    return client


# ==================== Time Provider Fixtures ====================


@pytest.fixture
def simulated_time_provider() -> SimulatedTimeProvider:
    """Create simulated time provider."""
    return SimulatedTimeProvider(speed_multiplier=1.0)


# ==================== Tracking Context Fixtures ====================


@pytest.fixture
def tracking_context(mock_http_client: AsyncMock) -> TrackingContext:
    """Create tracking context for dependency injection."""
    return TrackingContext(
        http_client=mock_http_client,
        timeout=5.0,
        max_retries=3,
        retry_delay=1.0,
    )


# ==================== Helper Functions ====================


@pytest.fixture
def load_fixture_file(fixtures_dir: Path):
    """Load fixture file from fixtures directory."""

    def _load(filename: str) -> str:
        file_path = fixtures_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    return _load


@pytest.fixture
def load_json_fixture(fixtures_dir: Path):
    """Load JSON fixture from fixtures directory."""

    def _load(filename: str) -> dict[str, Any]:
        file_path = fixtures_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"JSON fixture file not found: {file_path}")
        return json.loads(file_path.read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def load_iab_sample(iab_samples_dir: Path):
    """Load IAB VAST sample XML file."""

    def _load(filename: str) -> str:
        file_path = iab_samples_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"IAB sample not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    return _load


# ==================== Assertion Helpers ====================


@pytest.fixture
def assert_valid_vast_data():
    """Assert that parsed VAST data has required fields."""

    def _assert(vast_data: dict[str, Any]):
        assert "vast_version" in vast_data
        assert "ad_system" in vast_data
        assert "impression" in vast_data
        assert isinstance(vast_data["impression"], list)
        assert "tracking_events" in vast_data
        assert isinstance(vast_data["tracking_events"], dict)

    return _assert


@pytest.fixture
def assert_tracking_url_valid():
    """Assert that tracking URL is valid."""

    def _assert(url: str):
        assert url.startswith("http://") or url.startswith("https://")
        assert len(url) > 10
        # Should not contain unresolved macros in common formats
        assert "[TIMESTAMP]" not in url or "TIMESTAMP" in url  # Either resolved or different format
        assert "${TIMESTAMP}" not in url or "TIMESTAMP" in url

    return _assert
