#!/usr/bin/env python3
"""
Basic metrics usage example.

Demonstrates the simplest usage of VAST Client metrics.
"""

from vast_client.metrics import NoOpMetrics, VastMetrics, MetricLabels


def main():
    """Demonstrate basic metrics usage."""
    print("VAST Client Metrics - Basic Usage Example\n")
    print("=" * 50)
    
    # 1. No-Op Metrics (default, zero overhead)
    print("\n1. No-Op Metrics (Zero Overhead)")
    print("-" * 50)
    metrics = NoOpMetrics()
    
    # All operations are no-ops - no performance impact
    metrics.increment("vast.requests.total")
    metrics.histogram("vast.latency.milliseconds", 123.45)
    metrics.gauge("vast.active_requests", 5.0)
    
    print("✓ NoOpMetrics created")
    print("✓ Metrics recorded (no-op, zero overhead)")
    
    # 2. Using Metric Constants
    print("\n2. Using Metric Constants")
    print("-" * 50)
    
    # Use predefined constants for consistency
    metrics.increment(VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL)
    metrics.increment(
        VastMetrics.MULTI_SOURCE_REQUESTS_SUCCESS,
        labels={MetricLabels.FETCH_STRATEGY: "parallel"}
    )
    
    print("✓ Used VastMetrics constants")
    print(f"  - {VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL}")
    print(f"  - {VastMetrics.MULTI_SOURCE_REQUESTS_SUCCESS}")
    
    # 3. Labels for Dimensions
    print("\n3. Using Labels for Dimensions")
    print("-" * 50)
    
    labels = {
        MetricLabels.FETCH_STRATEGY: "parallel",
        MetricLabels.RESULT: "success",
        MetricLabels.PROVIDER: "example_provider"
    }
    
    metrics.increment(VastMetrics.MULTI_SOURCE_SOURCES_ATTEMPTED, labels=labels)
    metrics.histogram(VastMetrics.MULTI_SOURCE_LATENCY_MS, 123.45, labels=labels)
    
    print("✓ Applied labels to metrics")
    print(f"  Labels: {labels}")
    
    # 4. Available Metrics
    print("\n4. Available Metric Types")
    print("-" * 50)
    print("Counters (increment only):")
    print(f"  - {VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL}")
    print(f"  - {VastMetrics.MULTI_SOURCE_SOURCES_ATTEMPTED}")
    print(f"  - {VastMetrics.TRACKING_EVENT_SENT}")
    
    print("\nHistograms (record distributions):")
    print(f"  - {VastMetrics.MULTI_SOURCE_LATENCY_MS}")
    print(f"  - {VastMetrics.MULTI_SOURCE_FETCH_DURATION_MS}")
    print(f"  - {VastMetrics.PARSER_PARSE_DURATION_MS}")
    
    print("\nGauges (up/down values):")
    print(f"  - {VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS}")
    print(f"  - {VastMetrics.MULTI_SOURCE_SOURCES_COUNT}")
    
    print("\n" + "=" * 50)
    print("✓ Basic usage example complete!")


if __name__ == "__main__":
    main()
