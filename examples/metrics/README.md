# VAST Client Metrics Examples

This directory contains examples demonstrating the use of the VAST Client metrics system.

## Prerequisites

Install the VAST Client package with optional Prometheus support:

```bash
pip install vast-client
pip install prometheus-client  # Optional, for Prometheus integration
```

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates the fundamental concepts of the metrics system:
- Using NoOpMetrics (zero overhead)
- Working with metric constants
- Applying labels to metrics
- Available metric types

**Run:**
```bash
python basic_usage.py
```

**What you'll learn:**
- How to create and use metrics collectors
- The difference between NoOp and production metrics
- How to use VastMetrics and MetricLabels constants
- Available metric types (counters, histograms, gauges)

### 2. Prometheus Integration (`prometheus_integration.py`)

Shows how to integrate with Prometheus for production monitoring:
- Initializing PrometheusMetrics
- Recording metrics with labels
- Starting the metrics HTTP server
- Viewing metrics output

**Run:**
```bash
python prometheus_integration.py
```

**What you'll learn:**
- How to set up Prometheus metrics collection
- How to start the metrics HTTP server
- How to view exported metrics
- Prometheus configuration

**Test the server:**
```bash
# In another terminal, while the script is running:
curl http://localhost:8000/metrics | grep vast_
```

## Metrics Available

The VAST Client provides metrics for:

### Multi-Source Operations
- Request rates (total, success, failure)
- Latency percentiles (p50, p95, p99)
- Fallback usage patterns
- Source-level performance

### Tracking Events
- Events sent/failed
- Event latency

### Parser Performance
- Parse success/failure rates
- Parse duration

### Client Operations
- Request rates
- Request latency

See `docs/METRICS.md` for complete documentation.

## Creating Custom Collectors

You can create custom metrics collectors for other backends:

```python
from vast_client.metrics import MetricsCollector

class CustomMetrics(MetricsCollector):
    def __init__(self, backend_client):
        self.client = backend_client
    
    def increment(self, metric, value=1, labels=None):
        # Your implementation
        pass
    
    def histogram(self, metric, value, labels=None):
        # Your implementation
        pass
    
    def gauge(self, metric, value, labels=None):
        # Your implementation
        pass
```

## Grafana Dashboard

A pre-built Grafana dashboard is available in `dashboards/multi_source_monitoring.json`.

Import this dashboard to visualize:
- Request rates and success rates
- Latency distributions
- Error patterns
- Active requests
- Source-level performance

## Best Practices

1. **Use metric constants** - Always use `VastMetrics` and `MetricLabels` constants
2. **Limit label cardinality** - Keep the number of unique label values low
3. **Hash sensitive data** - Don't use raw URLs or IDs as label values
4. **Handle errors gracefully** - Don't let metrics failures break your application
5. **Use NoOp in development** - Zero overhead when you don't need monitoring

## Support

For more information:
- Full documentation: `docs/METRICS.md`
- GitHub Issues: https://github.com/pv-udpv/vast_client/issues
