# VAST Client Performance Benchmarks

This directory contains performance benchmarks for the VAST client, specifically focused on the multi-source fetching architecture.

## Overview

The benchmark suite measures performance characteristics across different scenarios:

1. **Single-Source vs Multi-Source** - Compare single source fetching with multi-source parallel fetching
2. **Fetch Strategy Comparison** - Compare PARALLEL, SEQUENTIAL, and RACE strategies
3. **Fallback Performance** - Measure fallback cascade behavior
4. **Parse Filter Impact** - Measure overhead of different filtering criteria

## Quick Start

### Run All Benchmarks

```bash
make benchmark
```

or

```bash
pytest -m benchmark benchmarks/ -v
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

### Generate Full Report

```bash
pytest -m benchmark benchmarks/multi_source_benchmarks.py::test_run_full_benchmark_suite -v
```

This will generate a detailed report at `benchmarks/RESULTS.md`.

## Files

- **`multi_source_benchmarks.py`** - Main benchmark test suite
- **`benchmark_results.py`** - Results collection and reporting utilities
- **`BENCHMARKS.md`** - Benchmark documentation and results template
- **`RESULTS.md`** - Generated results from benchmark runs (created when benchmarks run)

## Benchmark Structure

Each benchmark test:
1. Sets up the test scenario with configured latencies
2. Measures execution time using `time.perf_counter()`
3. Records results in `BenchmarkResults` object
4. Validates against performance targets
5. Reports results to console

## Performance Targets

| Metric | Target (p95) |
|--------|--------------|
| Single source | < 100ms |
| Multi parallel (3 sources) | < 150ms |
| Multi parallel (5 sources) | < 200ms |
| Fallback overhead | < 20ms per fallback |
| Parse filter overhead | < 10ms |
| Orchestrator overhead | < 20ms |

## Adding New Benchmarks

1. Add test method to appropriate test class or create new class
2. Use `@pytest.mark.benchmark` decorator
3. Use `BenchmarkResults` to collect measurements
4. Add assertions for performance targets
5. Update `BENCHMARKS.md` with new benchmark documentation

Example:

```python
@pytest.mark.benchmark
class TestNewFeature:
    """Benchmarks for new feature."""

    @pytest.mark.asyncio
    async def test_new_scenario(self, orchestrator):
        """Measure performance of new scenario."""
        results = BenchmarkResults()

        start = time.perf_counter()
        # ... perform operation ...
        duration = (time.perf_counter() - start) * 1000

        results.add("New Scenario", duration, {"key": "value"})
        results.report_console()

        assert duration < 100, "Should be < 100ms"
```

## CI Integration

To integrate benchmarks into CI:

1. Create `.github/workflows/benchmarks.yml`
2. Run benchmarks on PR and main branch
3. Upload results as artifacts
4. Optionally post results as PR comments

See `BENCHMARKS.md` for example workflow configuration.

## Interpreting Results

### Console Output

Benchmarks print results in tabular format:

```
================================================================================
BENCHMARK RESULTS
================================================================================

Total measurements: 10
Execution time: 2.45s

--------------------------------------------------------------------------------
Scenario                                           Duration (ms)        Details
--------------------------------------------------------------------------------
Single Source                                               52.34 sources=1
Multi-Source Parallel (3)                                  156.78 sources=3
...
================================================================================
```

### Markdown Report

The `test_run_full_benchmark_suite` test generates a markdown report at `benchmarks/RESULTS.md` with:
- Summary table of all measurements
- Metadata for each measurement
- Timestamp of benchmark run

## Mock Implementation

**Note:** The multi-source feature is implemented in PR #16 but not yet merged. These benchmarks use mock implementations (`MockMultiSourceOrchestrator`) that simulate the expected behavior.

Once PR #16 is merged, update the imports in `multi_source_benchmarks.py` to use the actual implementation:

```python
# Replace mock imports with:
from vast_client.multi_source import (
    FetchMode,
    FetchStrategy,
    VastFetchConfig,
    MultiSourceOrchestrator
)
```

## Troubleshooting

### Benchmarks are slow

- Reduce the number of sources in tests
- Decrease simulated latencies in fixtures
- Run specific benchmark suites instead of full suite

### Benchmarks fail assertions

- Check if targets are realistic for test environment
- Review latency configurations in fixtures
- Consider adjusting targets based on environment

### Import errors

- Ensure benchmark marker is registered in `pytest.ini`
- Check that `benchmarks/` is in `testpaths`
- Verify Python path includes `src/`

## Related Documentation

- [BENCHMARKS.md](BENCHMARKS.md) - Detailed benchmark documentation and results
- [Multi-Source Architecture](../docs/multi_source_architecture.md) - Architecture overview
- [Performance Tuning Guide](../docs/performance_tuning.md) - Optimization tips
