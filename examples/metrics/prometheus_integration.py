#!/usr/bin/env python3
"""
Prometheus metrics integration example.

Demonstrates how to use PrometheusMetrics with the VAST Client
and expose metrics for Prometheus scraping.
"""

import time

from vast_client.metrics import PrometheusMetrics, VastMetrics, MetricLabels


def simulate_requests(metrics: PrometheusMetrics, num_requests: int = 10):
    """Simulate VAST ad requests with metrics."""
    print(f"\nSimulating {num_requests} ad requests...")
    
    for i in range(num_requests):
        # Increment active requests
        metrics.gauge(VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS, 1.0)
        
        # Simulate request latency
        start_time = time.perf_counter()
        time.sleep(0.01)  # Simulate 10ms work
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Record metrics
        metrics.increment(VastMetrics.MULTI_SOURCE_REQUESTS_TOTAL)
        
        # Simulate success/failure (90% success rate)
        if i % 10 != 9:
            metrics.increment(
                VastMetrics.MULTI_SOURCE_REQUESTS_SUCCESS,
                labels={MetricLabels.FETCH_STRATEGY: "parallel"}
            )
            metrics.histogram(
                VastMetrics.MULTI_SOURCE_LATENCY_MS,
                latency_ms,
                labels={MetricLabels.RESULT: "success"}
            )
        else:
            metrics.increment(
                VastMetrics.MULTI_SOURCE_REQUESTS_FAILURE,
                labels={MetricLabels.ERROR_TYPE: "TimeoutError"}
            )
        
        # Decrement active requests
        metrics.gauge(VastMetrics.MULTI_SOURCE_ACTIVE_REQUESTS, -1.0)
        
        if (i + 1) % 5 == 0:
            print(f"  ✓ Processed {i + 1} requests")


def main():
    """Demonstrate Prometheus metrics integration."""
    print("VAST Client Metrics - Prometheus Integration Example\n")
    print("=" * 60)
    
    # Check if prometheus_client is available
    try:
        from prometheus_client import start_http_server, generate_latest, REGISTRY
        print("\n✓ prometheus_client is installed")
    except ImportError:
        print("\n✗ prometheus_client not installed")
        print("  Install with: pip install prometheus-client")
        return
    
    # 1. Initialize Prometheus Metrics
    print("\n1. Initialize Prometheus Metrics")
    print("-" * 60)
    metrics = PrometheusMetrics()
    print("✓ PrometheusMetrics initialized")
    print("✓ Using default Prometheus registry")
    
    # 2. Record Some Metrics
    print("\n2. Record Metrics")
    print("-" * 60)
    simulate_requests(metrics, num_requests=20)
    print("✓ Metrics recorded")
    
    # 3. Start Metrics HTTP Server
    print("\n3. Start Metrics HTTP Server")
    print("-" * 60)
    port = 8000
    try:
        start_http_server(port)
        print(f"✓ Metrics server started on port {port}")
        print(f"✓ Metrics available at http://localhost:{port}/metrics")
    except OSError as e:
        print(f"✗ Failed to start metrics server: {e}")
        print("  (Port may already be in use)")
    
    # 4. Display Sample Metrics Output
    print("\n4. Sample Metrics Output")
    print("-" * 60)
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Show relevant VAST metrics
    print("\nVAST-related metrics:")
    for line in metrics_output.split('\n'):
        if 'vast_' in line and not line.startswith('#'):
            print(f"  {line}")
    
    # 5. Configuration for Prometheus
    print("\n5. Prometheus Configuration")
    print("-" * 60)
    print("Add to your prometheus.yml:")
    print("""
scrape_configs:
  - job_name: 'vast_client'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
""")
    
    # 6. Keep Server Running
    print("\n6. Server Running")
    print("-" * 60)
    print(f"Metrics server is running at http://localhost:{port}/metrics")
    print("Press Ctrl+C to stop the server")
    print("\nYou can test with:")
    print(f"  curl http://localhost:{port}/metrics | grep vast_")
    
    try:
        # Keep the server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
    
    print("\n" + "=" * 60)
    print("✓ Prometheus integration example complete!")


if __name__ == "__main__":
    main()
