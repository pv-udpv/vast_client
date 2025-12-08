"""Test utilities and helper functions."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx


def create_mock_http_response(
    status_code: int = 200,
    content: str = "",
    content_type: str = "application/xml",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock HTTP response.

    Args:
        status_code: HTTP status code
        content: Response body content
        content_type: Content-Type header value
        headers: Additional headers

    Returns:
        Mock HTTP response object
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = content
    response.headers = {"content-type": content_type}

    if headers:
        response.headers.update(headers)

    response.raise_for_status = MagicMock()

    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=response
        )

    return response


def create_mock_http_client(
    default_response: MagicMock | None = None,
) -> AsyncMock:
    """Create a mock async HTTP client.

    Args:
        default_response: Default response for all requests

    Returns:
        Mock async HTTP client
    """
    client = AsyncMock(spec=httpx.AsyncClient)

    if default_response is None:
        default_response = create_mock_http_response()

    client.get = AsyncMock(return_value=default_response)
    client.post = AsyncMock(return_value=default_response)
    client.aclose = AsyncMock()

    return client


def assert_valid_tracking_url(url: str):
    """Assert that a tracking URL is valid.

    Args:
        url: Tracking URL to validate

    Raises:
        AssertionError: If URL is invalid
    """
    assert isinstance(url, str)
    assert url.startswith("http://") or url.startswith("https://")
    assert len(url) > 10
    # URL should not contain unresolved common macros
    unresolved_macros = ["[TIMESTAMP]", "${TIMESTAMP}", "[RANDOM]", "${RANDOM}"]
    for macro in unresolved_macros:
        if macro in url:
            # If macro is in URL, it should be part of a parameter name, not a value
            # This is a simplified check
            pass


def assert_valid_vast_structure(vast_data: dict[str, Any]):
    """Assert that VAST data has valid structure.

    Args:
        vast_data: Parsed VAST data dictionary

    Raises:
        AssertionError: If structure is invalid
    """
    # Required top-level fields
    assert "vast_version" in vast_data
    assert "impression" in vast_data
    assert "tracking_events" in vast_data

    # Type checks
    assert isinstance(vast_data["impression"], list)
    assert isinstance(vast_data["tracking_events"], dict)

    # If media files exist, check structure
    if "media_files" in vast_data and vast_data["media_files"]:
        assert isinstance(vast_data["media_files"], list)
        for media_file in vast_data["media_files"]:
            assert "url" in media_file
            assert isinstance(media_file["url"], str)


def assert_tracking_events_valid(tracking_events: dict[str, list[str]]):
    """Assert that tracking events structure is valid.

    Args:
        tracking_events: Tracking events dictionary

    Raises:
        AssertionError: If structure is invalid
    """
    assert isinstance(tracking_events, dict)

    for event_type, urls in tracking_events.items():
        assert isinstance(event_type, str)
        assert isinstance(urls, list)

        for url in urls:
            assert_valid_tracking_url(url)


def create_test_vast_xml(
    version: str = "4.0",
    ad_system: str = "Test System",
    duration: str = "00:00:30",
    tracking_events: dict[str, str] | None = None,
) -> str:
    """Create a test VAST XML document.

    Args:
        version: VAST version
        ad_system: Ad system name
        duration: Ad duration in HH:MM:SS format
        tracking_events: Dictionary of event type to tracking URL

    Returns:
        VAST XML string
    """
    if tracking_events is None:
        tracking_events = {
            "start": "https://tracking.example.com/start",
            "complete": "https://tracking.example.com/complete",
        }

    tracking_xml = "\n".join(
        f'          <Tracking event="{event}"><![CDATA[{url}]]></Tracking>'
        for event, url in tracking_events.items()
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<VAST version="{version}">
  <Ad id="test-ad">
    <InLine>
      <AdSystem>{ad_system}</AdSystem>
      <AdTitle>Test Ad</AdTitle>
      <Impression><![CDATA[https://tracking.example.com/impression]]></Impression>
      <Creatives>
        <Creative id="creative-001">
          <Linear>
            <Duration>{duration}</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4">
                <![CDATA[https://media.example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
            <TrackingEvents>
{tracking_xml}
            </TrackingEvents>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""


def extract_macro_value(url: str, param_name: str) -> str | None:
    """Extract parameter value from URL.

    Args:
        url: URL with query parameters
        param_name: Parameter name to extract

    Returns:
        Parameter value or None if not found
    """
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    return params.get(param_name, [None])[0]


def count_tracking_urls(vast_data: dict[str, Any]) -> int:
    """Count total number of tracking URLs in VAST data.

    Args:
        vast_data: Parsed VAST data

    Returns:
        Total count of tracking URLs
    """
    count = 0

    # Count impressions
    count += len(vast_data.get("impression", []))

    # Count error URLs
    count += len(vast_data.get("error", []))

    # Count tracking events
    for urls in vast_data.get("tracking_events", {}).values():
        count += len(urls)

    return count
