"""Pytest configuration for benchmark tests."""

import sys
from pathlib import Path

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def benchmark_env_info():
    """Provide environment information for benchmarks."""
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": platform.os.cpu_count(),
    }


@pytest.fixture
def print_env_info(benchmark_env_info):
    """Print environment info before benchmarks."""
    print("\n" + "=" * 80)
    print("BENCHMARK ENVIRONMENT")
    print("=" * 80)
    for key, value in benchmark_env_info.items():
        print(f"{key}: {value}")
    print("=" * 80 + "\n")
