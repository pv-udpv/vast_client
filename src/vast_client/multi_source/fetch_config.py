"""
Multi-Source Fetch Configuration

Configuration classes for multi-source VAST fetching, including fetch strategies,
source definitions, and result structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FetchMode(str, Enum):
    """Fetch execution mode."""

    PARALLEL = "parallel"  # Fetch all sources in parallel
    SEQUENTIAL = "sequential"  # Fetch sources one by one
    RACE = "race"  # Return first successful response


class MediaType(str, Enum):
    """Media file type enumeration."""

    VIDEO = "video"
    AUDIO = "audio"
    ALL = "all"


@dataclass
class FetchStrategy:
    """
    Strategy configuration for multi-source fetching.

    Attributes:
        mode: Fetch execution mode (parallel, sequential, race)
        timeout: Overall timeout for all fetch operations (seconds)
        per_source_timeout: Timeout per individual source (seconds)
        max_retries: Maximum number of retry attempts per source
        retry_delay: Delay between retries (seconds)
        stop_on_first_success: Stop fetching after first successful response

    Examples:
        Parallel fetching with timeout:
        >>> strategy = FetchStrategy(
        ...     mode=FetchMode.PARALLEL,
        ...     timeout=10.0,
        ...     per_source_timeout=5.0
        ... )

        Sequential fetching with retries:
        >>> strategy = FetchStrategy(
        ...     mode=FetchMode.SEQUENTIAL,
        ...     max_retries=3,
        ...     retry_delay=1.0
        ... )
    """

    mode: FetchMode = FetchMode.PARALLEL
    timeout: float = 30.0
    per_source_timeout: float = 10.0
    max_retries: int = 2
    retry_delay: float = 1.0
    stop_on_first_success: bool = False


@dataclass
class VastFetchConfig:
    """
    Configuration for multi-source VAST fetching.

    This class defines a fetch operation that can handle one or more VAST sources,
    with optional fallback sources. Single-source requests are handled as a special
    case with sources=[url].

    Sources can be either:
    - Simple URL strings: "https://ads.example.com/vast"
    - Dict configurations (EmbedHttpClient-style):
      {
          "base_url": "https://ads.example.com/vast",
          "params": {"publisher": "acme"},
          "headers": {"User-Agent": "Device/1.0"},
          "encoding_config": {"city": False}
      }

    Attributes:
        sources: List of primary VAST sources (URLs or dict configs)
        fallbacks: Optional list of fallback sources (URLs or dict configs)
        strategy: Fetch strategy configuration
        params: Additional query parameters to merge with all requests
        headers: Additional headers to merge with all requests
        parse_filter: Optional filter to apply during parsing
        auto_track: Whether to automatically track impression/start events

    Examples:
        Single-source with URL (margin case):
        >>> config = VastFetchConfig(sources=["https://ads.example.com/vast"])

        Single-source with dict config:
        >>> config = VastFetchConfig(sources=[{
        ...     "base_url": "https://ads.example.com/vast",
        ...     "params": {"slot": "pre-roll"},
        ...     "headers": {"User-Agent": "CTV-Device/1.0"}
        ... }])

        Multi-source with mixed types:
        >>> config = VastFetchConfig(
        ...     sources=[
        ...         "https://ads1.com/vast",  # URL string
        ...         {  # Dict config
        ...             "base_url": "https://ads2.com/vast",
        ...             "params": {"publisher": "acme"}
        ...         }
        ...     ],
        ...     fallbacks=["https://fallback.com/vast"],
        ...     strategy=FetchStrategy(mode=FetchMode.PARALLEL)
        ... )

        With additional parameters (merged with source configs):
        >>> config = VastFetchConfig(
        ...     sources=["https://ads.example.com/vast"],
        ...     params={"slot": "pre-roll", "publisher": "acme"},
        ...     headers={"User-Agent": "CTV-Device/1.0"}
        ... )
    """

    sources: list[str | dict[str, Any]] = field(default_factory=list)
    fallbacks: list[str | dict[str, Any]] = field(default_factory=list)
    strategy: FetchStrategy = field(default_factory=FetchStrategy)
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    parse_filter: Any = None  # VastParseFilter from parse_filter.py
    auto_track: bool = True


@dataclass
class FetchResult:
    """
    Result of a multi-source fetch operation.

    Attributes:
        success: Whether at least one source succeeded
        source_url: URL of the successful source (if any)
        raw_response: Raw VAST XML response
        parsed_data: Parsed VAST data dictionary (if parse was successful)
        errors: List of errors encountered during fetching
        metadata: Additional metadata about the fetch operation

    Examples:
        Successful fetch:
        >>> result = FetchResult(
        ...     success=True,
        ...     source_url="https://ads.example.com/vast",
        ...     raw_response="<?xml version='1.0'?>...",
        ...     parsed_data={"ad_system": "Test", ...}
        ... )

        Failed fetch with errors:
        >>> result = FetchResult(
        ...     success=False,
        ...     errors=[
        ...         {"source": "https://ads1.com/vast", "error": "Timeout"},
        ...         {"source": "https://ads2.com/vast", "error": "HTTP 404"}
        ...     ]
        ... )
    """

    success: bool = False
    source_url: str | None = None
    raw_response: str = ""
    parsed_data: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "FetchMode",
    "MediaType",
    "FetchStrategy",
    "VastFetchConfig",
    "FetchResult",
]
