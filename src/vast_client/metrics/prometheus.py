"""
Prometheus metrics collector implementation.

Integrates with prometheus_client library for exporting metrics
to Prometheus monitoring system.
"""

from typing import Any

from .base import MetricsCollector


class PrometheusMetrics(MetricsCollector):
    """
    Prometheus metrics collector.

    Integrates with prometheus_client library to expose metrics for Prometheus scraping.
    Automatically creates and manages Counter, Histogram, and Gauge metrics.

    Note: prometheus_client is an optional dependency. Install with:
        pip install prometheus-client

    Example:
        >>> from vast_client.metrics import PrometheusMetrics
        >>> metrics = PrometheusMetrics()
        >>> metrics.increment('vast.requests.total', labels={'provider': 'example'})
    """

    def __init__(self, registry: Any | None = None) -> None:
        """
        Initialize Prometheus metrics collector.

        Args:
            registry: Optional prometheus_client CollectorRegistry.
                     If None, uses the default REGISTRY.
        """
        try:
            from prometheus_client import REGISTRY, Counter, Gauge, Histogram
        except ImportError as e:
            raise ImportError(
                "prometheus_client is required for PrometheusMetrics. "
                "Install with: pip install prometheus-client"
            ) from e

        self._registry = registry or REGISTRY
        self._Counter = Counter
        self._Histogram = Histogram
        self._Gauge = Gauge

        # Cache for created metrics
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        self._gauges: dict[str, Any] = {}

    def _sanitize_metric_name(self, metric: str) -> str:
        """
        Sanitize metric name for Prometheus.

        Converts dots to underscores and ensures valid Prometheus naming.

        Args:
            metric: Original metric name

        Returns:
            Sanitized metric name
        """
        return metric.replace(".", "_").replace("-", "_")

    def increment(
        self, metric: str, value: int = 1, labels: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            metric: Metric name
            value: Amount to increment
            labels: Optional labels
        """
        metric_name = self._sanitize_metric_name(metric)
        labels = labels or {}

        if metric_name not in self._counters:
            label_names = list(labels.keys()) if labels else []
            self._counters[metric_name] = self._Counter(
                metric_name,
                f"Counter for {metric}",
                label_names,
                registry=self._registry,
            )

        if labels:
            self._counters[metric_name].labels(**labels).inc(value)
        else:
            self._counters[metric_name].inc(value)

    def histogram(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram value.

        Args:
            metric: Metric name
            value: Value to record
            labels: Optional labels
        """
        metric_name = self._sanitize_metric_name(metric)
        labels = labels or {}

        if metric_name not in self._histograms:
            label_names = list(labels.keys()) if labels else []
            self._histograms[metric_name] = self._Histogram(
                metric_name,
                f"Histogram for {metric}",
                label_names,
                registry=self._registry,
            )

        if labels:
            self._histograms[metric_name].labels(**labels).observe(value)
        else:
            self._histograms[metric_name].observe(value)

    def gauge(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Set a gauge value.

        For increment/decrement operations, pass positive/negative values.

        Args:
            metric: Metric name
            value: Value to set (or increment/decrement amount)
            labels: Optional labels
        """
        metric_name = self._sanitize_metric_name(metric)
        labels = labels or {}

        if metric_name not in self._gauges:
            label_names = list(labels.keys()) if labels else []
            self._gauges[metric_name] = self._Gauge(
                metric_name,
                f"Gauge for {metric}",
                label_names,
                registry=self._registry,
            )

        # For gauges, we use inc/dec for relative changes
        # or set for absolute values. Assume positive/negative means inc/dec.
        if labels:
            if value > 0:
                self._gauges[metric_name].labels(**labels).inc(value)
            elif value < 0:
                self._gauges[metric_name].labels(**labels).dec(abs(value))
            # value == 0 is a no-op for increment mode
        else:
            if value > 0:
                self._gauges[metric_name].inc(value)
            elif value < 0:
                self._gauges[metric_name].dec(abs(value))


__all__ = ["PrometheusMetrics"]
