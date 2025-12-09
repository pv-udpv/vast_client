"""
Multi-Source VAST Client Package

This package provides multi-source VAST fetching capabilities with fallback support,
parallel/sequential fetching strategies, and unified tracking.

The architecture implements a "multi-source first" design where single-source
requests are handled as a special case of multi-source (sources=[url]).

Main Components:
    - VastMultiSourceOrchestrator: Main coordinator (FETCH → PARSE → SELECT → TRACK)
    - VastMultiSourceFetcher: Multi-source fetching with strategies
    - MultiSourceTracker: Unified tracking across sources
    - VastFetchConfig: Configuration for multi-source operations
    - VastParseFilter: Selective parsing based on criteria

Usage:
    Single-source (margin case):
    >>> from vast_client.multi_source import VastMultiSourceOrchestrator, VastFetchConfig
    >>> orchestrator = VastMultiSourceOrchestrator()
    >>> config = VastFetchConfig(sources=["https://ads.example.com/vast"])
    >>> result = await orchestrator.execute_pipeline(config)

    Multi-source with fallbacks:
    >>> config = VastFetchConfig(
    ...     sources=["https://ads1.com/vast", "https://ads2.com/vast"],
    ...     fallbacks=["https://fallback.com/vast"]
    ... )
    >>> result = await orchestrator.execute_pipeline(config)

    With filtering:
    >>> from vast_client.multi_source import VastParseFilter, MediaType
    >>> filter = VastParseFilter(media_types=[MediaType.VIDEO], min_duration=15)
    >>> config = VastFetchConfig(
    ...     sources=["https://ads.example.com/vast"],
    ...     parse_filter=filter
    ... )
    >>> result = await orchestrator.execute_pipeline(config)
"""

from .fetch_config import (
    FetchMode,
    FetchResult,
    FetchStrategy,
    MediaType,
    VastFetchConfig,
)
from .fetcher import VastMultiSourceFetcher
from .orchestrator import VastMultiSourceOrchestrator
from .parse_filter import VastParseFilter
from .tracker import MultiSourceTracker
from .upstream import (
    BaseUpstream,
    HttpUpstream,
    LocalFileUpstream,
    MockUpstream,
    VastUpstream,
    create_upstream,
)

__version__ = "1.0.0"

__all__ = [
    # Main orchestrator
    "VastMultiSourceOrchestrator",
    # Fetcher
    "VastMultiSourceFetcher",
    # Tracker
    "MultiSourceTracker",
    # Configuration
    "VastFetchConfig",
    "FetchStrategy",
    "FetchMode",
    "FetchResult",
    # Filtering
    "VastParseFilter",
    "MediaType",
    # Upstreams
    "VastUpstream",
    "BaseUpstream",
    "HttpUpstream",
    "LocalFileUpstream",
    "MockUpstream",
    "create_upstream",
    # Metadata
    "__version__",
]
