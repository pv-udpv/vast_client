"""
Multi-Source VAST Fetcher

Handles fetching VAST XML from one or more sources with support for
parallel, sequential, and race modes.
"""

import asyncio
import time
from typing import Any

import httpx

from ..events import VastEvents
from ..log_config import get_context_logger
from ..routes.helpers import build_url_preserving_unicode
from .fetch_config import FetchMode, FetchResult, FetchStrategy


def _normalize_source(
    source: str | dict[str, Any],
    global_params: dict[str, Any] | None = None,
    global_headers: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any], dict[str, str]]:
    """
    Normalize a source configuration to URL, params, and headers.

    Args:
        source: Source URL string or dict configuration
        global_params: Global parameters to merge
        global_headers: Global headers to merge

    Returns:
        Tuple of (url, params, headers)

    Examples:
        >>> url, params, headers = _normalize_source("https://ads.example.com/vast")
        >>> url
        'https://ads.example.com/vast'

        >>> url, params, headers = _normalize_source({
        ...     "base_url": "https://ads.example.com/vast",
        ...     "params": {"slot": "pre-roll"}
        ... })
        >>> url
        'https://ads.example.com/vast'
        >>> params
        {'slot': 'pre-roll'}
    """
    global_params = global_params or {}
    global_headers = global_headers or {}

    if isinstance(source, str):
        # Simple URL string
        return source, global_params.copy(), global_headers.copy()

    elif isinstance(source, dict):
        # Dict configuration (EmbedHttpClient-style)
        base_url = source.get("base_url") or source.get("url")
        if not base_url:
            raise ValueError(
                f"Dict source must have 'base_url' or 'url' key: {source}"
            )

        # Merge params: source params override global params
        merged_params = {**global_params}
        if "params" in source:
            merged_params.update(source["params"])

        # Merge headers: source headers override global headers
        merged_headers = {**global_headers}
        if "headers" in source:
            merged_headers.update(source["headers"])

        # Handle encoding_config if present
        encoding_config = source.get("encoding_config", {})
        if encoding_config:
            # Store encoding config in metadata for later use
            # For now, we'll build the URL with params and let the caller handle encoding
            pass

        return base_url, merged_params, merged_headers

    else:
        raise TypeError(
            f"Source must be str or dict, got {type(source).__name__}: {source}"
        )


class VastMultiSourceFetcher:
    """
    Multi-source VAST fetcher with parallel and sequential strategies.

    Handles fetching VAST XML from multiple sources with configurable
    strategies, timeouts, and retry logic.

    Examples:
        Parallel fetching:
        >>> fetcher = VastMultiSourceFetcher()
        >>> strategy = FetchStrategy(mode=FetchMode.PARALLEL, timeout=10.0)
        >>> result = await fetcher.fetch_all(
        ...     sources=["https://ads1.com/vast", "https://ads2.com/vast"],
        ...     strategy=strategy,
        ...     http_client=client
        ... )

        Sequential with fallbacks:
        >>> result = await fetcher.fetch_with_fallbacks(
        ...     sources=["https://primary.com/vast"],
        ...     fallbacks=["https://fallback1.com/vast", "https://fallback2.com/vast"],
        ...     strategy=strategy,
        ...     http_client=client
        ... )
    """

    def __init__(self):
        """Initialize the multi-source fetcher."""
        self.logger = get_context_logger("vast_multi_source_fetcher")

    async def fetch_all(
        self,
        sources: list[str | dict[str, Any]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """
        Fetch from all sources according to the strategy.

        Args:
            sources: List of VAST sources (URLs or dict configs)
            strategy: Fetch strategy configuration
            http_client: HTTP client for requests
            params: Additional query parameters (global)
            headers: Additional headers (global)

        Returns:
            FetchResult: Result containing successful response or errors
        """
        if not sources:
            self.logger.error("No sources provided for fetch")
            return FetchResult(
                success=False, errors=[{"error": "No sources provided"}]
            )

        self.logger.info(
            VastEvents.REQUEST_STARTED,
            source_count=len(sources),
            mode=strategy.mode,
            timeout=strategy.timeout,
        )

        start_time = time.time()

        if strategy.mode == FetchMode.PARALLEL:
            result = await self._fetch_parallel(
                sources, strategy, http_client, params, headers
            )
        elif strategy.mode == FetchMode.SEQUENTIAL:
            result = await self._fetch_sequential(
                sources, strategy, http_client, params, headers
            )
        elif strategy.mode == FetchMode.RACE:
            result = await self._fetch_race(
                sources, strategy, http_client, params, headers
            )
        else:
            result = FetchResult(
                success=False,
                errors=[{"error": f"Unknown fetch mode: {strategy.mode}"}],
            )

        elapsed = time.time() - start_time
        result.metadata["elapsed_time"] = elapsed
        result.metadata["source_count"] = len(sources)
        result.metadata["mode"] = strategy.mode

        if result.success:
            self.logger.info(
                VastEvents.REQUEST_SUCCESS,
                elapsed_time=elapsed,
                source_url=result.source_url,
            )
        else:
            self.logger.info(
                VastEvents.REQUEST_FAILED,
                elapsed_time=elapsed,
                error_count=len(result.errors),
            )

        return result

    async def fetch_with_fallbacks(
        self,
        sources: list[str | dict[str, Any]],
        fallbacks: list[str | dict[str, Any]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """
        Fetch from sources, falling back to fallback list on failure.

        Args:
            sources: Primary source URLs
            fallbacks: Fallback URLs to try if primary sources fail
            strategy: Fetch strategy
            http_client: HTTP client
            params: Additional query parameters
            headers: Additional headers

        Returns:
            FetchResult: Result from primary sources or fallbacks
        """
        # Try primary sources first
        result = await self.fetch_all(sources, strategy, http_client, params, headers)

        # If primary sources failed and we have fallbacks, try them
        if not result.success and fallbacks:
            self.logger.info(
                "Primary sources failed, trying fallbacks",
                fallback_count=len(fallbacks),
            )
            result = await self.fetch_all(
                fallbacks, strategy, http_client, params, headers
            )
            result.metadata["used_fallback"] = True

        return result

    async def _fetch_parallel(
        self,
        sources: list[str | dict[str, Any]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> FetchResult:
        """Fetch all sources in parallel."""
        tasks = [
            self._fetch_single(source, strategy, http_client, params, headers)
            for source in sources
        ]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=strategy.timeout,
            )
        except asyncio.TimeoutError:
            return FetchResult(
                success=False,
                errors=[{"error": "Overall timeout exceeded", "timeout": strategy.timeout}],
            )

        # Process results - return first successful one
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source = sources[i]
                if isinstance(source, str):
                    source_repr = source
                else:
                    source_repr = source.get("base_url", str(source))
                errors.append({"source": source_repr, "error": str(result)})
            elif result.success:
                return result  # Return first successful result
            else:
                errors.extend(result.errors)

        return FetchResult(success=False, errors=errors)

    async def _fetch_sequential(
        self,
        sources: list[str | dict[str, Any]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> FetchResult:
        """Fetch sources sequentially until one succeeds."""
        errors = []
        for source in sources:
            result = await self._fetch_single(
                source, strategy, http_client, params, headers
            )
            if result.success:
                return result
            errors.extend(result.errors)

            if strategy.stop_on_first_success:
                break

        return FetchResult(success=False, errors=errors)

    async def _fetch_race(
        self,
        sources: list[str | dict[str, Any]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> FetchResult:
        """Race mode - return first successful response."""
        tasks = [
            self._fetch_single(source, strategy, http_client, params, headers)
            for source in sources
        ]

        try:
            # Wait for first completion
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED, timeout=strategy.timeout
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Return first successful result
            for task in done:
                result = task.result()
                if result.success:
                    return result

            # If no successful results, collect errors
            errors = []
            for task in done:
                result = task.result()
                errors.extend(result.errors)

            return FetchResult(success=False, errors=errors)

        except asyncio.TimeoutError:
            return FetchResult(
                success=False,
                errors=[{"error": "Race timeout exceeded", "timeout": strategy.timeout}],
            )

    async def _fetch_single(
        self,
        source: str | dict[str, Any],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> FetchResult:
        """
        Fetch from a single source with retry logic.

        Args:
            source: Source URL or dict configuration
            strategy: Fetch strategy
            http_client: HTTP client
            params: Additional query parameters (global)
            headers: Additional headers (global)

        Returns:
            FetchResult: Result of the fetch operation
        """
        # Normalize source to URL, params, and headers
        try:
            base_url, source_params, source_headers = _normalize_source(
                source, params, headers
            )
        except (ValueError, TypeError) as e:
            return FetchResult(
                success=False,
                source_url=str(source),
                errors=[{"source": str(source), "error": f"Invalid source config: {e}"}],
            )

        # Build final URL with params
        if source_params:
            final_url = build_url_preserving_unicode(base_url, source_params)
        else:
            final_url = base_url

        # Retry logic
        last_error = None
        for attempt in range(strategy.max_retries + 1):
            try:
                self.logger.debug(
                    "Fetching VAST",
                    source=base_url,
                    attempt=attempt + 1,
                    max_retries=strategy.max_retries,
                )

                response = await asyncio.wait_for(
                    http_client.get(final_url, headers=source_headers),
                    timeout=strategy.per_source_timeout,
                )

                if response.status_code == 204:
                    self.logger.debug("Received 204 No Content", source=base_url)
                    return FetchResult(
                        success=False,
                        source_url=base_url,
                        errors=[{"source": base_url, "error": "No content (204)"}],
                    )

                response.raise_for_status()

                return FetchResult(
                    success=True,
                    source_url=base_url,
                    raw_response=response.text,
                    metadata={
                        "status_code": response.status_code,
                        "content_length": len(response.text),
                        "attempt": attempt + 1,
                    },
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {strategy.per_source_timeout}s"
                self.logger.warning(
                    "Fetch timeout",
                    source=base_url,
                    attempt=attempt + 1,
                    timeout=strategy.per_source_timeout,
                )

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                self.logger.warning(
                    "HTTP error",
                    source=base_url,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                )

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    "Fetch error",
                    source=base_url,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                )

            # Wait before retry (except on last attempt)
            if attempt < strategy.max_retries:
                await asyncio.sleep(strategy.retry_delay)

        # All retries failed
        return FetchResult(
            success=False,
            source_url=base_url,
            errors=[{"source": base_url, "error": last_error}],
        )


__all__ = ["VastMultiSourceFetcher"]
