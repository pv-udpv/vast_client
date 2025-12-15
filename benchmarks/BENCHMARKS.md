# Multi-Source Performance Benchmarks

**Last Updated:** 2024-12-09

## Overview

This document contains performance benchmarks for the VAST client's multi-source fetching architecture implemented in PR #16. The benchmarks measure performance across different scenarios to ensure production requirements are met.

## Quick Reference

### Performance Targets

| Metric | Target (p95) | Status |
|--------|--------------|--------|
| Single source | < 100ms | ⏳ Pending |
| Multi parallel (3 sources) | < 150ms | ⏳ Pending |
| Multi parallel (5 sources) | < 200ms | ⏳ Pending |
| Fallback overhead | < 20ms per fallback | ⏳ Pending |
| Parse filter overhead | < 10ms | ⏳ Pending |
| Orchestrator overhead | < 20ms | ⏳ Pending |

### Legend
- ✅ PASS - Within target
- ⚠️ WARNING - Close to target (within 10%)
- ❌ FAIL - Exceeds target
- ⏳ Pending - Awaiting measurement

## Environment

```yaml
Python Version: 3.11
CPU: 4 cores
Memory: 8GB
Network: Mocked (configurable latency)
OS: Linux
```

## Running Benchmarks

### Run All Benchmarks

```bash
pytest -m benchmark benchmarks/multi_source_benchmarks.py -v
```

### Run Specific Benchmark Suite

```bash
# Single vs Multi-Source
pytest -m benchmark benchmarks/multi_source_benchmarks.py::TestSingleVsMultiSource -v

# Fetch Strategies
pytest -m benchmark benchmarks/multi_source_benchmarks.py::TestFetchStrategies -v

# Fallback Performance
pytest -m benchmark benchmarks/multi_source_benchmarks.py::TestFallbackPerformance -v

# Parse Filter Impact
pytest -m benchmark benchmarks/multi_source_benchmarks.py::TestParseFilterImpact -v
```

### Generate Report

```bash
pytest -m benchmark benchmarks/multi_source_benchmarks.py::test_run_full_benchmark_suite -v
# Report will be generated at benchmarks/RESULTS.md
```

## Benchmark Results

### 1. Single-Source vs Multi-Source

Comparing single-source fetching with multi-source parallel fetching.

| Scenario | Duration (ms) | Sources | Strategy | Status |
|----------|--------------|---------|----------|--------|
| Single source | - | 1 | sequential | ⏳ Pending |
| Multi-source (3) | - | 3 | parallel | ⏳ Pending |
| Multi-source (5) | - | 5 | parallel | ⏳ Pending |

**Key Findings:**
- *Results pending - run benchmarks to populate*

### 2. Fetch Strategy Comparison

Comparing different fetch strategies under various conditions.

#### Mixed Latency (50ms - 500ms)

| Strategy | Duration (ms) | Status |
|----------|--------------|--------|
| Parallel | - | ⏳ Pending |
| Sequential | - | ⏳ Pending |
| Race | - | ⏳ Pending |

**Key Findings:**
- *Results pending - run benchmarks to populate*

#### All Sources Fast (< 100ms)

| Strategy | Duration (ms) | Status |
|----------|--------------|--------|
| Parallel | - | ⏳ Pending |
| Sequential | - | ⏳ Pending |
| Race | - | ⏳ Pending |

#### One Slow Source (> 2s timeout)

| Strategy | Duration (ms) | Status |
|----------|--------------|--------|
| Parallel | - | ⏳ Pending |
| Sequential | - | ⏳ Pending |
| Race | - | ⏳ Pending |

### 3. Fallback Performance

Measuring fallback cascade behavior.

| Scenario | Duration (ms) | Fallbacks Used | Status |
|----------|--------------|----------------|--------|
| Primary success | - | 0 | ⏳ Pending |
| Primary failure → single fallback | - | 1 | ⏳ Pending |
| Cascade failure (all sources) | - | 3 | ⏳ Pending |

**Key Findings:**
- *Results pending - run benchmarks to populate*

### 4. Parse Filter Impact

Measuring overhead of different filtering criteria.

| Filter Type | Duration (ms) | Overhead | Status |
|-------------|--------------|----------|--------|
| No filtering (baseline) | - | 0ms | ⏳ Pending |
| Media type filtering | - | - | ⏳ Pending |
| Bitrate + dimension filtering | - | - | ⏳ Pending |
| Complex multi-criteria | - | - | ⏳ Pending |

**Key Findings:**
- *Results pending - run benchmarks to populate*

### 5. Orchestrator Overhead

Measuring the overhead of the multi-source orchestrator vs direct fetch.

| Scenario | Duration (ms) | Overhead | Status |
|----------|--------------|----------|--------|
| Direct fetch | - | 0ms | ⏳ Pending |
| Via orchestrator | - | - | ⏳ Pending |

**Target:** Orchestrator overhead should be < 20ms

## Analysis

### Performance Characteristics

*To be filled after running benchmarks*

#### Parallel Strategy
- **Best for:** Multiple reliable sources with varying latency
- **Characteristics:** 
  - Waits for all sources
  - Returns first successful result
  - Provides redundancy

#### Sequential Strategy
- **Best for:** Ordered source priorities with fallback
- **Characteristics:**
  - Tries sources in order
  - Stops at first success
  - Lower resource usage

#### Race Strategy
- **Best for:** Fast response time with multiple sources
- **Characteristics:**
  - Returns first to complete
  - Cancels remaining requests
  - Minimizes latency

### Recommendations

*To be filled after running benchmarks*

1. **For production environments:**
   - Use PARALLEL strategy with 3-5 sources for redundancy
   - Set timeout to 2-3 seconds per source
   - Enable parse filtering for quality control

2. **For testing/development:**
   - Use SEQUENTIAL strategy to minimize resource usage
   - Use shorter timeouts (1 second)
   - Disable unnecessary filters

3. **For low-latency requirements:**
   - Use RACE strategy with 2-3 fast sources
   - Set aggressive timeouts (500ms)
   - Use minimal filtering

## Regression Testing

### Baseline Metrics

*To be established after initial benchmark run*

### Regression Thresholds

- **Warning:** Performance degrades by > 10%
- **Failure:** Performance degrades by > 20%

### CI Integration

Add to `.github/workflows/benchmarks.yml`:

```yaml
name: Performance Benchmarks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"
      - name: Run benchmarks
        run: |
          pytest -m benchmark benchmarks/ -v
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmarks/RESULTS.md
```

## Changelog

### 2024-12-09
- Initial benchmark suite created
- Defined performance targets
- Implemented benchmark framework

## See Also

- [Multi-Source Architecture Design](../docs/multi_source_architecture.md)
- [Performance Tuning Guide](../docs/performance_tuning.md)
- [Testing Guide](../tests/README.md)
