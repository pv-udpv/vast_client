"""Benchmark results collection and reporting utilities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BenchmarkMeasurement:
    """Single benchmark measurement."""

    name: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        """Format measurement as string."""
        meta_str = ", ".join(f"{k}={v}" for k, v in self.metadata.items())
        return f"{self.name}: {self.duration_ms:.2f}ms ({meta_str})"


class BenchmarkResults:
    """Collection of benchmark measurements with reporting capabilities."""

    def __init__(self) -> None:
        """Initialize benchmark results collector."""
        self.measurements: list[BenchmarkMeasurement] = []
        self.start_time = datetime.now()

    def add(
        self, name: str, duration_ms: float, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Add a benchmark measurement.

        Args:
            name: Name of the benchmark
            duration_ms: Duration in milliseconds
            metadata: Optional metadata dictionary
        """
        measurement = BenchmarkMeasurement(
            name=name, duration_ms=duration_ms, metadata=metadata or {}
        )
        self.measurements.append(measurement)

    def get_measurement(self, name: str) -> BenchmarkMeasurement | None:
        """
        Get a specific measurement by name.

        Args:
            name: Name of the measurement

        Returns:
            The measurement or None if not found
        """
        for m in self.measurements:
            if m.name == name:
                return m
        return None

    def get_average(self, pattern: str) -> float | None:
        """
        Get average duration for measurements matching a pattern.

        Args:
            pattern: Pattern to match in measurement names

        Returns:
            Average duration in ms or None if no matches
        """
        matching = [m for m in self.measurements if pattern in m.name]
        if not matching:
            return None
        return sum(m.duration_ms for m in matching) / len(matching)

    def report_console(self) -> None:
        """Print benchmark results to console."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)
        print(f"\nTotal measurements: {len(self.measurements)}")
        print(f"Execution time: {(datetime.now() - self.start_time).total_seconds():.2f}s")
        print("\n" + "-" * 80)
        print(f"{'Scenario':<50} {'Duration (ms)':>15} {'Details':<15}")
        print("-" * 80)

        for m in self.measurements:
            meta_str = ", ".join(f"{k}={v}" for k, v in m.metadata.items())
            print(f"{m.name:<50} {m.duration_ms:>15.2f} {meta_str:<15}")

        print("=" * 80 + "\n")

    def report_markdown(self) -> str:
        """
        Generate markdown report of benchmark results.

        Returns:
            Markdown formatted string
        """
        lines = [
            "## Benchmark Results\n",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**Total Measurements:** {len(self.measurements)}\n",
            "",
            "| Scenario | Duration (ms) | Details |",
            "|----------|---------------|---------|",
        ]

        for m in self.measurements:
            meta_str = ", ".join(f"{k}={v}" for k, v in m.metadata.items())
            lines.append(f"| {m.name} | {m.duration_ms:.2f} | {meta_str} |")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert results to dictionary format.

        Returns:
            Dictionary representation of results
        """
        return {
            "start_time": self.start_time.isoformat(),
            "measurements": [
                {
                    "name": m.name,
                    "duration_ms": m.duration_ms,
                    "metadata": m.metadata,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self.measurements
            ],
        }
