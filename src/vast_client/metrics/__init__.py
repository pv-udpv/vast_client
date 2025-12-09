"""
Metrics collection module for VAST client.

Provides pluggable metrics interfaces for monitoring and observability.
Supports multiple backends including Prometheus, with zero-overhead default.

Example:
    >>> from vast_client.metrics import NoOpMetrics, PrometheusMetrics
    >>> 
    >>> # No-op metrics (default, zero overhead)
    >>> metrics = NoOpMetrics()
    >>> metrics.increment('vast.requests.total')  # No-op
    >>> 
    >>> # Prometheus metrics
    >>> metrics = PrometheusMetrics()
    >>> metrics.increment('vast.requests.total', labels={'provider': 'example'})
    >>> metrics.histogram('vast.latency.milliseconds', 123.45)
"""

from .base import MetricsCollector, NoOpMetrics
from .constants import MetricLabels, VastMetrics
from .prometheus import PrometheusMetrics

__all__ = [
    "MetricsCollector",
    "NoOpMetrics",
    "PrometheusMetrics",
    "VastMetrics",
    "MetricLabels",
]
