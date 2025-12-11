# VAST Client Metrics and Observability Guide

## Overview

The VAST Client package provides a pluggable metrics collection system that enables comprehensive monitoring and observability for production deployments. The metrics system is designed with zero overhead by default and supports multiple backends including Prometheus.

## Features

✨ **Pluggable Architecture** - Swap backends without changing application code  
🚀 **Zero Overhead** - Default `NoOpMetrics` implementation has no performance impact  
📊 **Comprehensive Metrics** - Pre-defined constants for all key performance indicators  
🔌 **Multiple Backends** - Built-in support for Prometheus, extensible to others  
📈 **Production Ready** - Thread-safe and async-safe implementations  

## Quick Start

### Basic Usage (No-Op Metrics)

```python
from vast_client.metrics import NoOpMetrics

# Default - zero overhead, no-op implementation
metrics = NoOpMetrics()
metrics.increment('vast.requests.total')  # No-op
metrics.histogram('vast.latency.milliseconds', 123.45)  # No-op
```

### Prometheus Integration

```python
from vast_client.metrics import PrometheusMetrics, VastMetrics, MetricLabels

# Initialize Prometheus metrics
metrics = PrometheusMetrics()

# Increment counters
metrics.increment(
    VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL,
    labels={MetricLabels.FETCH_STRATEGY: 'parallel'}
)

# Record latency histogram
metrics.histogram(
    VastMetrics.MULTI_SOURCE_LATENCY_MS,
    value=123.45,
    labels={MetricLabels.RESULT: 'success'}
)

# Update gauges
metrics.gauge(VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS, 5.0)  # Increment by 5
metrics.gauge(VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS, -1.0)  # Decrement by 1
```

### Integration with VastClient

```python
from vast_client import VastClient
from vast_client.metrics import PrometheusMetrics
from vast_client.context import TrackingContext

# Create metrics collector
metrics = PrometheusMetrics()

# Create tracking context with metrics
context = TrackingContext(metrics_client=metrics)

# Use with VAST client
client = VastClient("https://ads.example.com/vast")
# Metrics will be automatically collected (when multi-source support is added)
```

## Available Metrics

### Multi-Source Request Metrics

#### Counters

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.multi_source.requests.total` | Total multi-source requests | `fetch_strategy`, `provider` |
| `vast.multi_source.requests.success` | Successful completions | `fetch_strategy`, `result` |
| `vast.multi_source.requests.failure` | Failed requests | `fetch_strategy`, `error_type` |
| `vast.multi_source.fallback.triggered` | Fallback invocations | `fallback_depth` |
| `vast.multi_source.sources.attempted` | Individual source attempts | `source_url`, `provider` |
| `vast.multi_source.sources.success` | Individual source successes | `source_url`, `result` |
| `vast.multi_source.sources.failure` | Individual source failures | `source_url`, `error_type` |

#### Histograms

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.multi_source.latency.milliseconds` | End-to-end request latency | `fetch_strategy`, `result` |
| `vast.multi_source.fetch.duration` | Individual fetch durations | `source_url`, `result` |
| `vast.multi_source.parse.duration` | XML parse time | `source_url` |
| `vast.multi_source.filter.duration` | Filter application time | `fetch_strategy` |

#### Gauges

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.multi_source.active_requests` | Concurrent active requests | - |
| `vast.multi_source.sources.count` | Sources per request (avg) | `fetch_strategy` |

### Standard Tracking Metrics

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.tracking.event.sent` | Tracking events sent | `event_type`, `provider` |
| `vast.tracking.event.failed` | Tracking events failed | `event_type`, `error_type` |
| `vast.tracking.request.duration` | Tracking request latency | `event_type` |

### Parser Metrics

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.parser.xml.parsed` | XML successfully parsed | `provider` |
| `vast.parser.xml.failed` | XML parse failures | `error_type` |
| `vast.parser.parse.duration` | XML parse duration | `provider` |

### Client Metrics

| Metric Name | Description | Labels |
|------------|-------------|---------|
| `vast.client.request.total` | Total ad requests | `provider` |
| `vast.client.request.success` | Successful ad requests | `provider` |
| `vast.client.request.failure` | Failed ad requests | `error_type` |
| `vast.client.request.duration` | Ad request latency | `provider` |

## Metric Labels

All metrics support the following standard labels:

| Label | Values | Description |
|-------|--------|-------------|
| `fetch_strategy` | `parallel`, `sequential`, `race` | Multi-source fetch strategy |
| `source_url` | Hashed URL or domain | Ad source identifier |
| `result` | `success`, `timeout`, `error`, `invalid_xml` | Operation result |
| `fallback_depth` | `0`, `1`, `2`, ... | Fallback level in chain |
| `event_type` | `impression`, `start`, `firstQuartile`, ... | VAST event type |
| `error_type` | Exception class name | Error category |
| `http_status` | `200`, `404`, `500`, ... | HTTP status code |
| `provider` | Provider name | Ad provider identifier |
| `publisher` | Publisher ID | Publisher identifier |

## Backend Integration

### Prometheus

#### Installation

```bash
pip install prometheus-client
```

#### Basic Setup

```python
from vast_client.metrics import PrometheusMetrics
from prometheus_client import start_http_server

# Initialize metrics
metrics = PrometheusMetrics()

# Start metrics HTTP server on port 8000
start_http_server(8000)

# Use metrics in your application
metrics.increment('vast.requests.total')

# Metrics available at http://localhost:8000/metrics
```

#### Custom Registry

```python
from prometheus_client import CollectorRegistry
from vast_client.metrics import PrometheusMetrics

# Create custom registry
registry = CollectorRegistry()

# Initialize metrics with custom registry
metrics = PrometheusMetrics(registry=registry)
```

#### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'vast_client'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

### DataDog / StatsD

For DataDog or StatsD integration, create a custom collector:

```python
from vast_client.metrics import MetricsCollector

class StatsDMetrics(MetricsCollector):
    def __init__(self, statsd_client):
        self.statsd = statsd_client
    
    def increment(self, metric, value=1, labels=None):
        tags = [f"{k}:{v}" for k, v in (labels or {}).items()]
        self.statsd.increment(metric, value, tags=tags)
    
    def histogram(self, metric, value, labels=None):
        tags = [f"{k}:{v}" for k, v in (labels or {}).items()]
        self.statsd.histogram(metric, value, tags=tags)
    
    def gauge(self, metric, value, labels=None):
        tags = [f"{k}:{v}" for k, v in (labels or {}).items()]
        self.statsd.gauge(metric, value, tags=tags)

# Usage
from datadog import DogStatsd
statsd = DogStatsd(host="localhost", port=8125)
metrics = StatsDMetrics(statsd)
```

### CloudWatch

For AWS CloudWatch integration:

```python
from vast_client.metrics import MetricsCollector
import boto3

class CloudWatchMetrics(MetricsCollector):
    def __init__(self, namespace='VASTClient'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
    
    def increment(self, metric, value=1, labels=None):
        dimensions = [
            {'Name': k, 'Value': v} 
            for k, v in (labels or {}).items()
        ]
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': metric,
                'Value': value,
                'Unit': 'Count',
                'Dimensions': dimensions
            }]
        )
    
    # ... implement histogram and gauge
```

## Monitoring Dashboards

### Grafana Dashboard

A pre-built Grafana dashboard template is available in `dashboards/multi_source_monitoring.json`. Import this dashboard to visualize:

- Request rate and success rate
- Latency percentiles (p50, p95, p99)
- Fallback usage patterns
- Error distribution by type
- Active requests over time
- Source-level performance

Key panels include:

1. **Request Overview**
   - Total requests/second
   - Success rate (%)
   - Error rate by type

2. **Latency Analysis**
   - p50, p95, p99 latency
   - Latency heatmap
   - Per-strategy latency comparison

3. **Multi-Source Behavior**
   - Sources attempted per request
   - Fallback trigger rate
   - Source-level success rates

4. **Resource Utilization**
   - Active concurrent requests
   - Request throughput
   - Cache hit rates (if applicable)

### Example Grafana Queries

#### Request Success Rate

```promql
rate(vast_multi_source_requests_success[5m]) / rate(vast_multi_source_requests_total[5m]) * 100
```

#### P95 Latency

```promql
histogram_quantile(0.95, rate(vast_multi_source_latency_milliseconds_bucket[5m]))
```

#### Fallback Usage

```promql
rate(vast_multi_source_fallback_triggered[5m])
```

#### Error Distribution

```promql
sum by (error_type) (rate(vast_multi_source_requests_failure[5m]))
```

## Performance Considerations

### NoOp Metrics (Default)

The default `NoOpMetrics` implementation has **zero overhead**:
- All methods are no-ops (empty functions)
- No memory allocation
- No I/O operations
- Suitable for production when monitoring is not needed

### Prometheus Metrics

The `PrometheusMetrics` implementation has minimal overhead:
- Metric creation: One-time cost per unique metric
- Recording: ~1-2 microseconds per operation
- Memory: ~100 bytes per time series
- Recommended for production monitoring

**Performance Tips:**
1. Use a custom registry to isolate metrics
2. Limit cardinality of labels (avoid unbounded values)
3. Use sampling for high-frequency events
4. Pre-create metrics at startup when possible

## Best Practices

### 1. Use Metric Constants

Always use the predefined constants from `VastMetrics` and `MetricLabels`:

```python
# ✅ Good
metrics.increment(VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL)

# ❌ Bad
metrics.increment('vast.multi_source.requests.total')
```

### 2. Label Cardinality

Keep label cardinality low to avoid memory issues:

```python
# ✅ Good - low cardinality
labels = {
    MetricLabels.FETCH_STRATEGY: 'parallel',  # 3 values
    MetricLabels.RESULT: 'success'  # 4-5 values
}

# ❌ Bad - high cardinality
labels = {
    'request_id': uuid.uuid4(),  # Unlimited values!
    'timestamp': time.time()  # Unlimited values!
}
```

### 3. Hash Sensitive Data

Hash URLs and sensitive identifiers:

```python
import hashlib

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()[:8]

metrics.increment(
    VastMetrics.MULTI_SOURCE_SOURCES_ATTEMPTED,
    labels={MetricLabels.SOURCE_URL: hash_url(source_url)}
)
```

### 4. Context Manager for Timing

Use context managers for timing operations:

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(metrics, metric_name, labels=None):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        metrics.histogram(metric_name, duration_ms, labels=labels)

# Usage
with timer(metrics, VastMetrics.MULTI_SOURCE_LATENCY_MS):
    result = await client.multi_source.execute_pipeline(config)
```

### 5. Graceful Degradation

Always handle metrics errors gracefully:

```python
try:
    metrics.increment(VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL)
except Exception as e:
    logger.warning(f"Metrics recording failed: {e}")
    # Continue normal execution
```

## Alerting Recommendations

### Critical Alerts

```yaml
# High error rate
- alert: VASTHighErrorRate
  expr: rate(vast_multi_source_requests_failure[5m]) / rate(vast_multi_source_requests_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "VAST error rate > 10%"

# High latency
- alert: VASTHighLatency
  expr: histogram_quantile(0.95, rate(vast_multi_source_latency_milliseconds_bucket[5m])) > 1000
  for: 5m
  annotations:
    summary: "VAST p95 latency > 1s"

# All sources failing
- alert: VASTAllSourcesFailing
  expr: rate(vast_multi_source_sources_success[5m]) == 0
  for: 2m
  annotations:
    summary: "All VAST sources are failing"
```

### Warning Alerts

```yaml
# Increased fallback usage
- alert: VASTHighFallbackUsage
  expr: rate(vast_multi_source_fallback_triggered[5m]) / rate(vast_multi_source_requests_total[5m]) > 0.3
  for: 10m
  annotations:
    summary: "VAST fallback usage > 30%"

# Slow parse times
- alert: VASTSlowParsing
  expr: histogram_quantile(0.95, rate(vast_multi_source_parse_duration_bucket[5m])) > 100
  for: 10m
  annotations:
    summary: "VAST parse time > 100ms"
```

## Troubleshooting

### Metrics Not Appearing

1. **Check if prometheus_client is installed:**
   ```bash
   pip list | grep prometheus-client
   ```

2. **Verify metrics server is running:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Check metric names:**
   - Prometheus metric names use underscores, not dots
   - `vast.multi_source.requests.total` → `vast_multi_source_requests_total`

### High Memory Usage

1. **Check label cardinality:**
   ```python
   # View metrics in Prometheus
   # count({__name__=~"vast_.*"}) by (__name__)
   ```

2. **Reduce label values:**
   - Hash unbounded values (URLs, IDs)
   - Group similar values
   - Remove unnecessary labels

### Missing Labels

Labels must be consistent across all metric calls:

```python
# ✅ Good - consistent labels
metrics.increment('test', labels={'a': '1', 'b': '2'})
metrics.increment('test', labels={'a': '1', 'b': '2'})

# ❌ Bad - inconsistent labels (will create separate time series)
metrics.increment('test', labels={'a': '1'})
metrics.increment('test', labels={'a': '1', 'b': '2'})
```

## API Reference

### MetricsCollector (Abstract Base Class)

```python
class MetricsCollector(ABC):
    def increment(self, metric: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
    
    def histogram(self, metric: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram/timing value."""
    
    def gauge(self, metric: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value (positive=increment, negative=decrement)."""
    
    def timing(self, metric: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a timing metric (wrapper for histogram)."""
```

### NoOpMetrics

```python
class NoOpMetrics(MetricsCollector):
    """Zero-overhead no-op implementation. All methods are no-ops."""
```

### PrometheusMetrics

```python
class PrometheusMetrics(MetricsCollector):
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """
        Initialize Prometheus metrics collector.
        
        Args:
            registry: Optional CollectorRegistry. Uses default if None.
        """
```

## Examples

See the `examples/metrics/` directory for complete working examples:

- `basic_usage.py` - Basic metrics usage
- `prometheus_integration.py` - Prometheus integration
- `custom_collector.py` - Creating custom collectors
- `timing_decorator.py` - Timing decorator pattern
- `multi_source_simulation.py` - Simulating multi-source metrics

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [VAST Specification](https://www.iab.com/guidelines/vast/)

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/pv-udpv/vast_client/issues
- Documentation: https://github.com/pv-udpv/vast_client/tree/main/docs
