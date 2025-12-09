"""Unit tests for metrics module."""

import pytest

from vast_client.metrics import (
    MetricLabels,
    MetricsCollector,
    NoOpMetrics,
    PrometheusMetrics,
    VastMetrics,
)


class TestMetricsCollector:
    """Test MetricsCollector abstract base class."""

    def test_is_abstract(self):
        """Test that MetricsCollector cannot be instantiated."""
        with pytest.raises(TypeError):
            MetricsCollector()  # type: ignore


class TestNoOpMetrics:
    """Test NoOpMetrics implementation."""

    def test_noop_increment(self):
        """Test no-op increment method."""
        metrics = NoOpMetrics()

        # Should not raise any exceptions
        metrics.increment("test.metric")
        metrics.increment("test.metric", value=5)
        metrics.increment("test.metric", labels={"key": "value"})

    def test_noop_histogram(self):
        """Test no-op histogram method."""
        metrics = NoOpMetrics()

        # Should not raise any exceptions
        metrics.histogram("test.metric", 123.45)
        metrics.histogram("test.metric", 123.45, labels={"key": "value"})

    def test_noop_gauge(self):
        """Test no-op gauge method."""
        metrics = NoOpMetrics()

        # Should not raise any exceptions
        metrics.gauge("test.metric", 10.0)
        metrics.gauge("test.metric", -5.0)
        metrics.gauge("test.metric", 0.0, labels={"key": "value"})

    def test_noop_timing(self):
        """Test no-op timing method."""
        metrics = NoOpMetrics()

        # Should not raise any exceptions
        metrics.timing("test.metric", 123.45)
        metrics.timing("test.metric", 123.45, labels={"key": "value"})

    def test_is_instance_of_metrics_collector(self):
        """Test that NoOpMetrics is an instance of MetricsCollector."""
        metrics = NoOpMetrics()
        assert isinstance(metrics, MetricsCollector)


class TestPrometheusMetrics:
    """Test PrometheusMetrics implementation."""

    def test_requires_prometheus_client(self):
        """Test that PrometheusMetrics requires prometheus_client."""
        # This test will pass if prometheus_client is installed,
        # or raise ImportError if not
        try:
            from prometheus_client import REGISTRY  # noqa: F401

            # If prometheus_client is available, test initialization
            metrics = PrometheusMetrics()
            assert isinstance(metrics, MetricsCollector)
        except ImportError:
            # If prometheus_client is not available, test error handling
            with pytest.raises(ImportError, match="prometheus_client is required"):
                PrometheusMetrics()

    def test_prometheus_increment(self):
        """Test Prometheus increment method."""
        try:
            from prometheus_client import CollectorRegistry

            # Use custom registry to avoid conflicts
            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Increment without labels
            metrics.increment("test_counter")
            metrics.increment("test_counter", value=5)

            # Increment with labels
            metrics.increment(
                "test_labeled_counter", labels={"status": "success", "provider": "test"}
            )

            # Verify counter was created
            assert "test_counter" in metrics._counters
            assert "test_labeled_counter" in metrics._counters
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_prometheus_histogram(self):
        """Test Prometheus histogram method."""
        try:
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Record histogram values
            metrics.histogram("test_histogram", 123.45)
            metrics.histogram("test_histogram", 67.89)

            # Record with labels
            metrics.histogram("test_labeled_histogram", 100.0, labels={"method": "GET"})

            # Verify histogram was created
            assert "test_histogram" in metrics._histograms
            assert "test_labeled_histogram" in metrics._histograms
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_prometheus_gauge(self):
        """Test Prometheus gauge method."""
        try:
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Set gauge values
            metrics.gauge("test_gauge", 10.0)  # Increment by 10
            metrics.gauge("test_gauge", -5.0)  # Decrement by 5
            metrics.gauge("test_gauge", 0.0)  # No-op

            # Set with labels
            metrics.gauge("test_labeled_gauge", 1.0, labels={"type": "active"})

            # Verify gauge was created
            assert "test_gauge" in metrics._gauges
            assert "test_labeled_gauge" in metrics._gauges
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_prometheus_timing(self):
        """Test Prometheus timing method (wrapper for histogram)."""
        try:
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Record timing
            metrics.timing("test_timing", 123.45)

            # Verify histogram was created (timing is a histogram)
            assert "test_timing" in metrics._histograms
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_sanitize_metric_name(self):
        """Test metric name sanitization."""
        try:
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Test sanitization
            assert metrics._sanitize_metric_name("test.metric.name") == "test_metric_name"
            assert metrics._sanitize_metric_name("test-metric-name") == "test_metric_name"
            assert metrics._sanitize_metric_name("test.metric-name") == "test_metric_name"
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_prometheus_with_multi_source_metrics(self):
        """Test using VastMetrics constants with Prometheus."""
        try:
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry()
            metrics = PrometheusMetrics(registry=registry)

            # Use VastMetrics constants
            metrics.increment(
                VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL,
                labels={MetricLabels.FETCH_STRATEGY: "parallel"},
            )
            metrics.histogram(
                VastMetrics.MULTI_SOURCE_LATENCY_MS,
                123.45,
                labels={MetricLabels.RESULT: "success"},
            )
            metrics.gauge(VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS, 5.0)

            # Verify metrics were created
            assert "vast_multi_source_requests_total" in metrics._counters
            assert "vast_multi_source_latency_milliseconds" in metrics._histograms
            assert "vast_multi_source_active_requests" in metrics._gauges
        except ImportError:
            pytest.skip("prometheus_client not installed")


class TestVastMetrics:
    """Test VastMetrics constants."""

    def test_multi_source_counters(self):
        """Test multi-source counter constants."""
        assert VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL == "vast.multi_source.requests.total"
        assert (
            VastMetrics.MULTI_SOURCE_REQUESTS_SUCCESS
            == "vast.multi_source.requests.success"
        )
        assert (
            VastMetrics.MULTI_SOURCE_REQUESTS_FAILURE
            == "vast.multi_source.requests.failure"
        )
        assert (
            VastMetrics.MULTI_SOURCE_FALLBACK_TRIGGERED
            == "vast.multi_source.fallback.triggered"
        )

    def test_multi_source_source_counters(self):
        """Test multi-source individual source counter constants."""
        assert (
            VastMetrics.MULTI_SOURCE_SOURCES_ATTEMPTED
            == "vast.multi_source.sources.attempted"
        )
        assert (
            VastMetrics.MULTI_SOURCE_SOURCES_SUCCESS == "vast.multi_source.sources.success"
        )
        assert (
            VastMetrics.MULTI_SOURCE_SOURCES_FAILURE == "vast.multi_source.sources.failure"
        )

    def test_multi_source_histograms(self):
        """Test multi-source histogram constants."""
        assert (
            VastMetrics.MULTI_SOURCE_LATENCY_MS == "vast.multi_source.latency.milliseconds"
        )
        assert (
            VastMetrics.MULTI_SOURCE_FETCH_DURATION_MS
            == "vast.multi_source.fetch.duration"
        )
        assert (
            VastMetrics.MULTI_SOURCE_PARSE_DURATION_MS
            == "vast.multi_source.parse.duration"
        )
        assert (
            VastMetrics.MULTI_SOURCE_FILTER_DURATION_MS
            == "vast.multi_source.filter.duration"
        )

    def test_multi_source_gauges(self):
        """Test multi-source gauge constants."""
        assert (
            VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS
            == "vast.multi_source.active_requests"
        )
        assert VastMetrics.MULTI_SOURCE_SOURCES_COUNT == "vast.multi_source.sources.count"

    def test_tracking_metrics(self):
        """Test tracking metric constants."""
        assert VastMetrics.TRACKING_EVENT_SENT == "vast.tracking.event.sent"
        assert VastMetrics.TRACKING_EVENT_FAILED == "vast.tracking.event.failed"
        assert (
            VastMetrics.TRACKING_REQUEST_DURATION_MS == "vast.tracking.request.duration"
        )

    def test_parser_metrics(self):
        """Test parser metric constants."""
        assert VastMetrics.PARSER_XML_PARSED == "vast.parser.xml.parsed"
        assert VastMetrics.PARSER_XML_FAILED == "vast.parser.xml.failed"
        assert VastMetrics.PARSER_PARSE_DURATION_MS == "vast.parser.parse.duration"

    def test_client_metrics(self):
        """Test client metric constants."""
        assert VastMetrics.CLIENT_REQUEST_TOTAL == "vast.client.request.total"
        assert VastMetrics.CLIENT_REQUEST_SUCCESS == "vast.client.request.success"
        assert VastMetrics.CLIENT_REQUEST_FAILURE == "vast.client.request.failure"
        assert VastMetrics.CLIENT_REQUEST_DURATION_MS == "vast.client.request.duration"


class TestMetricLabels:
    """Test MetricLabels constants."""

    def test_multi_source_labels(self):
        """Test multi-source label constants."""
        assert MetricLabels.FETCH_STRATEGY == "fetch_strategy"
        assert MetricLabels.SOURCE_URL == "source_url"
        assert MetricLabels.RESULT == "result"
        assert MetricLabels.FALLBACK_DEPTH == "fallback_depth"

    def test_event_labels(self):
        """Test event label constants."""
        assert MetricLabels.EVENT_TYPE == "event_type"
        assert MetricLabels.ERROR_TYPE == "error_type"
        assert MetricLabels.HTTP_STATUS == "http_status"

    def test_general_labels(self):
        """Test general label constants."""
        assert MetricLabels.PROVIDER == "provider"
        assert MetricLabels.PUBLISHER == "publisher"
