"""
Abstract base class for metrics collection.

Provides a pluggable interface for integrating various metrics backends
(Prometheus, StatsD, DataDog, CloudWatch, etc.) with zero-overhead default implementation.
"""

from abc import ABC, abstractmethod
from typing import Any


class MetricsCollector(ABC):
    """
    Abstract base class for metrics collection.

    Defines the interface for recording metrics across different backends.
    All implementations should be thread-safe and async-safe.
    """

    @abstractmethod
    def increment(
        self, metric: str, value: int = 1, labels: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            metric: Metric name (e.g., 'vast.multi_source.requests.total')
            value: Amount to increment (default: 1)
            labels: Optional labels/tags (e.g., {'strategy': 'parallel', 'result': 'success'})
        """
        pass

    @abstractmethod
    def histogram(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram/timing metric.

        Args:
            metric: Metric name (e.g., 'vast.multi_source.latency.milliseconds')
            value: Value to record (e.g., latency in milliseconds)
            labels: Optional labels/tags
        """
        pass

    @abstractmethod
    def gauge(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Set a gauge metric.

        Args:
            metric: Metric name (e.g., 'vast.multi_source.active_requests')
            value: Value to set (can be positive or negative for increment/decrement)
            labels: Optional labels/tags
        """
        pass

    def timing(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a timing metric (convenience wrapper for histogram).

        Args:
            metric: Metric name
            value: Duration in milliseconds
            labels: Optional labels/tags
        """
        self.histogram(metric, value, labels)


class NoOpMetrics(MetricsCollector):
    """
    No-operation metrics collector.

    Default implementation with zero overhead. All methods are no-ops,
    ensuring no performance impact when metrics are disabled.
    """

    def increment(
        self, metric: str, value: int = 1, labels: dict[str, str] | None = None
    ) -> None:
        """No-op increment."""
        pass

    def histogram(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """No-op histogram."""
        pass

    def gauge(
        self, metric: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """No-op gauge."""
        pass


__all__ = ["MetricsCollector", "NoOpMetrics"]
