"""
Metric name constants for VAST multi-source architecture.

Provides standardized metric names to ensure consistency across
the codebase and enable easy monitoring dashboard creation.
"""


class VastMetrics:
    """Metric name constants for VAST client operations."""

    # Multi-source request counters
    MULTI_SOURCE_REQUESTS_TOTAL = "vast.multi_source.requests.total"
    MULTI_SOURCE_REQUESTS_SUCCESS = "vast.multi_source.requests.success"
    MULTI_SOURCE_REQUESTS_FAILURE = "vast.multi_source.requests.failure"
    MULTI_SOURCE_FALLBACK_TRIGGERED = "vast.multi_source.fallback.triggered"

    # Individual source counters
    MULTI_SOURCE_SOURCES_ATTEMPTED = "vast.multi_source.sources.attempted"
    MULTI_SOURCE_SOURCES_SUCCESS = "vast.multi_source.sources.success"
    MULTI_SOURCE_SOURCES_FAILURE = "vast.multi_source.sources.failure"

    # Latency histograms
    MULTI_SOURCE_LATENCY_MS = "vast.multi_source.latency.milliseconds"
    MULTI_SOURCE_FETCH_DURATION_MS = "vast.multi_source.fetch.duration"
    MULTI_SOURCE_PARSE_DURATION_MS = "vast.multi_source.parse.duration"
    MULTI_SOURCE_FILTER_DURATION_MS = "vast.multi_source.filter.duration"

    # Gauges
    MULTI_SOURCE_ACTIVE_REQUESTS = "vast.multi_source.active_requests"
    MULTI_SOURCE_SOURCES_COUNT = "vast.multi_source.sources.count"

    # Standard tracking events (for non-multi-source)
    TRACKING_EVENT_SENT = "vast.tracking.event.sent"
    TRACKING_EVENT_FAILED = "vast.tracking.event.failed"
    TRACKING_REQUEST_DURATION_MS = "vast.tracking.request.duration"

    # Parser metrics
    PARSER_XML_PARSED = "vast.parser.xml.parsed"
    PARSER_XML_FAILED = "vast.parser.xml.failed"
    PARSER_PARSE_DURATION_MS = "vast.parser.parse.duration"

    # Client metrics
    CLIENT_REQUEST_TOTAL = "vast.client.request.total"
    CLIENT_REQUEST_SUCCESS = "vast.client.request.success"
    CLIENT_REQUEST_FAILURE = "vast.client.request.failure"
    CLIENT_REQUEST_DURATION_MS = "vast.client.request.duration"


class MetricLabels:
    """Standard label names for metrics."""

    # Multi-source labels
    FETCH_STRATEGY = "fetch_strategy"  # parallel, sequential, race
    SOURCE_URL = "source_url"  # hashed URL or domain
    RESULT = "result"  # success, timeout, error, invalid_xml
    FALLBACK_DEPTH = "fallback_depth"  # 0, 1, 2, ...

    # Event labels
    EVENT_TYPE = "event_type"  # impression, start, firstQuartile, etc.
    ERROR_TYPE = "error_type"  # Exception class name
    HTTP_STATUS = "http_status"  # 200, 404, 500, etc.

    # General labels
    PROVIDER = "provider"  # Ad provider name
    PUBLISHER = "publisher"  # Publisher ID


__all__ = ["VastMetrics", "MetricLabels"]
