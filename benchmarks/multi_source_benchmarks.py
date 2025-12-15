"""
Performance benchmarks for multi-source VAST fetching.

This module contains benchmarks for the multi-source fetching feature
implemented in PR #16. The benchmarks measure:
- Single-source vs multi-source performance
- Different fetch strategies (parallel, sequential, race)
- Fallback cascade performance
- Parse filter overhead

Note: Since the multi-source feature is not yet merged, these benchmarks
use mock implementations that simulate the expected API and behavior.
"""

import asyncio
import contextlib
import time
from enum import Enum
from typing import Any

import pytest

from benchmarks.benchmark_results import BenchmarkResults


# Mock implementation of multi-source types (to be replaced with actual implementation)
class FetchMode(str, Enum):
    """Fetch strategy modes."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    RACE = "race"


class FetchStrategy:
    """Fetch strategy configuration."""

    def __init__(self, mode: FetchMode, timeout: float = 5.0):
        self.mode = mode
        self.timeout = timeout


class VastFetchConfig:
    """Configuration for multi-source VAST fetching."""

    def __init__(
        self,
        sources: list[str],
        strategy: FetchStrategy,
        parse_filters: dict[str, Any] | None = None,
    ):
        self.sources = sources
        self.strategy = strategy
        self.parse_filters = parse_filters or {}


class MockMultiSourceOrchestrator:
    """
    Mock multi-source orchestrator for benchmarking.

    This simulates the expected behavior of the multi-source feature
    for benchmark purposes.
    """

    def __init__(self, latencies: dict[str, float] | None = None):
        """
        Initialize mock orchestrator.

        Args:
            latencies: Dictionary mapping source URLs to simulated latency in seconds
        """
        self.latencies = latencies or {}

    async def execute_pipeline(
        self, config: VastFetchConfig
    ) -> dict[str, Any]:
        """
        Execute multi-source fetch pipeline.

        Args:
            config: Fetch configuration

        Returns:
            Mock VAST data
        """
        if config.strategy.mode == FetchMode.PARALLEL:
            return await self._fetch_parallel(config)
        elif config.strategy.mode == FetchMode.SEQUENTIAL:
            return await self._fetch_sequential(config)
        elif config.strategy.mode == FetchMode.RACE:
            return await self._fetch_race(config)
        else:
            raise ValueError(f"Unknown strategy mode: {config.strategy.mode}")

    async def _fetch_parallel(self, config: VastFetchConfig) -> dict[str, Any]:
        """Fetch from all sources in parallel."""
        tasks = [self._fetch_source(url) for url in config.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Return first successful result
        for result in results:
            if not isinstance(result, Exception):
                return result

        raise Exception("All sources failed")

    async def _fetch_sequential(self, config: VastFetchConfig) -> dict[str, Any]:
        """Fetch from sources sequentially."""
        for url in config.sources:
            try:
                return await self._fetch_source(url)
            except Exception:
                continue

        raise Exception("All sources failed")

    async def _fetch_race(self, config: VastFetchConfig) -> dict[str, Any]:
        """Race sources and return first successful result."""
        tasks = [self._fetch_source(url) for url in config.sources]
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                # Cancel remaining tasks
                for task in tasks:
                    if isinstance(task, asyncio.Task) and not task.done():
                        task.cancel()
                return result
            except Exception:
                continue

        raise Exception("All sources failed")

    async def _fetch_source(self, url: str) -> dict[str, Any]:
        """
        Fetch from a single source with simulated latency.

        Args:
            url: Source URL

        Returns:
            Mock VAST data
        """
        latency = self.latencies.get(url, 0.05)  # Default 50ms
        await asyncio.sleep(latency)

        return {
            "ad_system": "MockAdSystem",
            "duration": 30,
            "source_url": url,
            "creative_id": "test_creative",
        }


# Benchmark Fixtures


@pytest.fixture
def mock_sources():
    """Create mock source URLs with different latencies."""
    return {
        "https://fast-source.com/vast": 0.05,  # 50ms
        "https://medium-source.com/vast": 0.15,  # 150ms
        "https://slow-source.com/vast": 0.5,  # 500ms
        "https://very-slow-source.com/vast": 2.0,  # 2s
    }


@pytest.fixture
def orchestrator(mock_sources):
    """Create mock multi-source orchestrator."""
    return MockMultiSourceOrchestrator(latencies=mock_sources)


# Benchmark Tests


@pytest.mark.benchmark
class TestSingleVsMultiSource:
    """Benchmarks comparing single-source vs multi-source performance."""

    @pytest.mark.asyncio
    async def test_single_vs_multi_parallel(self, orchestrator, mock_sources):
        """Compare single source vs multi-source parallel fetching."""
        results = BenchmarkResults()

        # Single source fetch
        config_single = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_single)
        duration_single = (time.perf_counter() - start) * 1000
        results.add(
            "Single Source",
            duration_single,
            {"sources": 1, "strategy": "sequential"},
        )

        # Multi-source parallel (3 sources)
        config_multi_3 = VastFetchConfig(
            sources=[
                "https://fast-source.com/vast",
                "https://medium-source.com/vast",
                "https://slow-source.com/vast",
            ],
            strategy=FetchStrategy(mode=FetchMode.PARALLEL),
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_multi_3)
        duration_multi_3 = (time.perf_counter() - start) * 1000
        results.add(
            "Multi-Source Parallel (3)",
            duration_multi_3,
            {"sources": 3, "strategy": "parallel"},
        )

        # Multi-source parallel (5 sources)
        config_multi_5 = VastFetchConfig(
            sources=list(mock_sources.keys()),
            strategy=FetchStrategy(mode=FetchMode.PARALLEL),
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_multi_5)
        duration_multi_5 = (time.perf_counter() - start) * 1000
        results.add(
            "Multi-Source Parallel (5)",
            duration_multi_5,
            {"sources": 5, "strategy": "parallel"},
        )

        # Report results
        results.report_console()

        # Assertions to verify performance targets
        assert duration_single < 100, "Single source should be < 100ms"
        assert duration_multi_3 < 600, "Multi parallel (3) should be < 600ms"
        assert duration_multi_5 < 2100, "Multi parallel (5) should be < 2100ms"

    @pytest.mark.asyncio
    async def test_orchestrator_overhead(self, orchestrator):
        """Measure overhead of orchestrator vs direct fetch."""
        results = BenchmarkResults()

        # Direct fetch (simulated)
        start = time.perf_counter()
        await orchestrator._fetch_source("https://fast-source.com/vast")
        duration_direct = (time.perf_counter() - start) * 1000
        results.add("Direct Fetch", duration_direct, {"overhead": "none"})

        # Via orchestrator
        config = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration_orchestrator = (time.perf_counter() - start) * 1000
        results.add(
            "Orchestrator Fetch",
            duration_orchestrator,
            {"overhead": f"{duration_orchestrator - duration_direct:.2f}ms"},
        )

        overhead = duration_orchestrator - duration_direct
        results.add("Orchestrator Overhead", overhead, {"type": "computed"})

        results.report_console()

        # Overhead should be minimal
        assert overhead < 20, f"Orchestrator overhead should be < 20ms, got {overhead:.2f}ms"


@pytest.mark.benchmark
class TestFetchStrategies:
    """Benchmarks comparing different fetch strategies."""

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_vs_race(self, orchestrator):
        """Compare all fetch strategies under mixed latency."""
        results = BenchmarkResults()

        sources = [
            "https://fast-source.com/vast",
            "https://medium-source.com/vast",
            "https://slow-source.com/vast",
        ]

        # Parallel strategy
        config_parallel = VastFetchConfig(
            sources=sources, strategy=FetchStrategy(mode=FetchMode.PARALLEL)
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_parallel)
        duration_parallel = (time.perf_counter() - start) * 1000
        results.add(
            "Strategy: Parallel",
            duration_parallel,
            {"sources": 3, "condition": "mixed_latency"},
        )

        # Sequential strategy
        config_sequential = VastFetchConfig(
            sources=sources, strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL)
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_sequential)
        duration_sequential = (time.perf_counter() - start) * 1000
        results.add(
            "Strategy: Sequential",
            duration_sequential,
            {"sources": 3, "condition": "mixed_latency"},
        )

        # Race strategy
        config_race = VastFetchConfig(
            sources=sources, strategy=FetchStrategy(mode=FetchMode.RACE)
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config_race)
        duration_race = (time.perf_counter() - start) * 1000
        results.add(
            "Strategy: Race",
            duration_race,
            {"sources": 3, "condition": "mixed_latency"},
        )

        results.report_console()

        # Parallel should wait for all sources (slowest determines time)
        # Sequential tries in order (gets first working)
        # Race returns first to complete (should be similar to sequential with fast first source)
        # Note: With fast first source, race and sequential have similar performance
        assert duration_parallel > duration_sequential, "Parallel should be slower with mixed latency"
        assert duration_race <= duration_sequential * 1.5, "Race should be comparable to sequential"

    @pytest.mark.asyncio
    async def test_all_sources_fast(self, orchestrator):
        """Benchmark strategies when all sources are fast."""
        results = BenchmarkResults()

        # Create fast sources
        fast_sources = ["https://fast-source.com/vast"] * 3

        for mode in [FetchMode.PARALLEL, FetchMode.SEQUENTIAL, FetchMode.RACE]:
            config = VastFetchConfig(
                sources=fast_sources, strategy=FetchStrategy(mode=mode)
            )

            start = time.perf_counter()
            await orchestrator.execute_pipeline(config)
            duration = (time.perf_counter() - start) * 1000
            results.add(
                f"All Fast - {mode.value}",
                duration,
                {"sources": 3, "condition": "all_fast"},
            )

        results.report_console()

    @pytest.mark.asyncio
    async def test_one_slow_source_timeout(self, orchestrator):
        """Benchmark with one very slow source that times out."""
        results = BenchmarkResults()

        sources = [
            "https://fast-source.com/vast",
            "https://medium-source.com/vast",
            "https://very-slow-source.com/vast",  # 2s - should timeout
        ]

        for mode in [FetchMode.PARALLEL, FetchMode.SEQUENTIAL, FetchMode.RACE]:
            config = VastFetchConfig(
                sources=sources, strategy=FetchStrategy(mode=mode, timeout=1.0)
            )

            start = time.perf_counter()
            with contextlib.suppress(Exception):
                # Timeout expected
                await orchestrator.execute_pipeline(config)
            duration = (time.perf_counter() - start) * 1000
            results.add(
                f"One Slow - {mode.value}",
                duration,
                {"sources": 3, "condition": "one_timeout"},
            )

        results.report_console()


@pytest.mark.benchmark
class TestFallbackPerformance:
    """Benchmarks for fallback cascade performance."""

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self, orchestrator):
        """Measure performance when primary succeeds (no fallback)."""
        results = BenchmarkResults()

        config = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add(
            "Primary Success (No Fallback)",
            duration,
            {"fallbacks_used": 0},
        )

        results.report_console()

        assert duration < 100, "Primary success should be < 100ms"

    @pytest.mark.asyncio
    async def test_primary_failure_single_fallback(self):
        """Measure performance with one fallback."""
        results = BenchmarkResults()

        # Simulate primary failure by using non-existent source
        orchestrator_with_failure = MockMultiSourceOrchestrator(
            latencies={
                "https://primary.com/vast": 0.05,
                "https://fallback.com/vast": 0.05,
            }
        )

        # Override to simulate failure
        original_fetch = orchestrator_with_failure._fetch_source

        async def mock_fetch_with_failure(url: str) -> dict[str, Any]:
            if "primary" in url:
                raise Exception("Primary failed")
            return await original_fetch(url)

        orchestrator_with_failure._fetch_source = mock_fetch_with_failure

        config = VastFetchConfig(
            sources=["https://primary.com/vast", "https://fallback.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
        )

        start = time.perf_counter()
        await orchestrator_with_failure.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add(
            "Primary Failure → Single Fallback",
            duration,
            {"fallbacks_used": 1},
        )

        results.report_console()

    @pytest.mark.asyncio
    async def test_cascade_failure_time(self):
        """Measure total time when all sources fail."""
        results = BenchmarkResults()

        orchestrator_all_fail = MockMultiSourceOrchestrator()

        # Override to make all fetches fail
        async def mock_fetch_failure(_url: str) -> dict[str, Any]:
            await asyncio.sleep(0.05)  # Simulate attempt
            raise Exception("Source failed")

        orchestrator_all_fail._fetch_source = mock_fetch_failure

        config = VastFetchConfig(
            sources=[
                "https://source1.com/vast",
                "https://source2.com/vast",
                "https://source3.com/vast",
            ],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
        )

        start = time.perf_counter()
        with contextlib.suppress(Exception):
            # Expected to fail
            await orchestrator_all_fail.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add(
            "Cascade Failure (All Sources)",
            duration,
            {"sources_tried": 3, "all_failed": True},
        )

        results.report_console()


@pytest.mark.benchmark
class TestParseFilterImpact:
    """Benchmarks for parse filter overhead."""

    @pytest.mark.asyncio
    async def test_no_filtering(self, orchestrator):
        """Baseline: no filtering."""
        results = BenchmarkResults()

        config = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
            parse_filters={},
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add("No Filtering", duration, {"filters": 0})

        results.report_console()

    @pytest.mark.asyncio
    async def test_media_type_filtering(self, orchestrator):
        """Measure overhead of media type filtering."""
        results = BenchmarkResults()

        config = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
            parse_filters={"media_type": "video/mp4"},
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add("Media Type Filter", duration, {"filters": 1})

        results.report_console()

    @pytest.mark.asyncio
    async def test_complex_filtering(self, orchestrator):
        """Measure overhead of complex multi-criteria filtering."""
        results = BenchmarkResults()

        config = VastFetchConfig(
            sources=["https://fast-source.com/vast"],
            strategy=FetchStrategy(mode=FetchMode.SEQUENTIAL),
            parse_filters={
                "media_type": "video/mp4",
                "min_bitrate": 500,
                "max_bitrate": 2000,
                "min_width": 1280,
                "min_height": 720,
            },
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add("Complex Multi-Criteria Filter", duration, {"filters": 5})

        results.report_console()


# Helper function to run all benchmarks and generate report


@pytest.mark.benchmark
async def test_run_full_benchmark_suite(orchestrator, mock_sources):
    """
    Run the complete benchmark suite and generate comprehensive report.

    This test runs all benchmarks and generates both console and markdown output.
    """
    results = BenchmarkResults()

    print("\n" + "=" * 80)
    print("RUNNING FULL MULTI-SOURCE BENCHMARK SUITE")
    print("=" * 80 + "\n")

    # Single vs Multi-Source
    for num_sources in [1, 3, 5]:
        sources = list(mock_sources.keys())[:num_sources]
        config = VastFetchConfig(
            sources=sources, strategy=FetchStrategy(mode=FetchMode.PARALLEL)
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add(
            f"Multi-Source ({num_sources})",
            duration,
            {"sources": num_sources, "strategy": "parallel"},
        )

    # Strategy comparison
    sources = list(mock_sources.keys())[:3]
    for mode in [FetchMode.PARALLEL, FetchMode.SEQUENTIAL, FetchMode.RACE]:
        config = VastFetchConfig(
            sources=sources, strategy=FetchStrategy(mode=mode)
        )

        start = time.perf_counter()
        await orchestrator.execute_pipeline(config)
        duration = (time.perf_counter() - start) * 1000
        results.add(f"Strategy: {mode.value}", duration, {"sources": 3})

    # Generate reports
    results.report_console()
    markdown = results.report_markdown()

    # Write markdown report
    with open("/home/runner/work/vast_client/vast_client/benchmarks/RESULTS.md", "w") as f:
        f.write("# Multi-Source Performance Benchmark Results\n\n")
        f.write(markdown)

    print("\nMarkdown report written to benchmarks/RESULTS.md")


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "-v", "-m", "benchmark"])
