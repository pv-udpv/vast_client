"""
Multi-Source VAST Fetcher

Handles fetching VAST XML from one or more upstreams with support for
parallel, sequential, and race modes.
"""

import asyncio
import time
from typing import Any, Union

import httpx

from ..events import VastEvents
from ..log_config import get_context_logger
from .fetch_config import FetchMode, FetchResult, FetchStrategy
from .upstream import VastUpstream, create_upstream


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
        sources: list[Union[str, dict[str, Any], VastUpstream]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None = None,
        headers: Union[dict[str, str], None] = None,
    ) -> FetchResult:
        """
        Fetch from all upstreams according to the strategy.

        Args:
            sources: List of VAST sources (URLs, dict configs, or VastUpstream objects)
            strategy: Fetch strategy configuration
            http_client: HTTP client for HTTP upstreams (optional)
            params: Additional query parameters (global, for URL/dict sources)
            headers: Additional headers (global, for URL/dict sources)

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
        sources: list[Union[str, dict[str, Any], VastUpstream]],
        fallbacks: list[Union[str, dict[str, Any], VastUpstream]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None = None,
        headers: Union[dict[str, str], None] = None,
    ) -> FetchResult:
        """
        Fetch from upstreams, falling back to fallback list on failure.

        Args:
            sources: Primary sources (URLs, dicts, or upstreams)
            fallbacks: Fallback sources to try if primary sources fail
            strategy: Fetch strategy
            http_client: HTTP client for HTTP upstreams
            params: Additional query parameters (for URL/dict sources)
            headers: Additional headers (for URL/dict sources)

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
        sources: list[Union[str, dict[str, Any], VastUpstream]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: Union[dict[str, str], None],
    ) -> FetchResult:
        """Fetch all upstreams in parallel."""
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
                # Get source identifier
                upstream = create_upstream(sources[i])
                source_id = upstream.get_identifier() if hasattr(upstream, 'get_identifier') else str(sources[i])
                errors.append({"source": source_id, "error": str(result)})
            elif result.success:
                return result  # Return first successful result
            else:
                errors.extend(result.errors)

        return FetchResult(success=False, errors=errors)

    async def _fetch_sequential(
        self,
        sources: list[Union[str, dict[str, Any], VastUpstream]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: Union[dict[str, str], None],
    ) -> FetchResult:
        """Fetch upstreams sequentially until one succeeds."""
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
        sources: list[Union[str, dict[str, Any], VastUpstream]],
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: Union[dict[str, str], None],
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
        source: str | dict[str, Any] | VastUpstream,
        strategy: FetchStrategy,
        http_client: httpx.AsyncClient,
        params: dict[str, Any] | None,
        headers: Union[dict[str, str], None],
    ) -> FetchResult:
        """
        Fetch from a single upstream with retry logic.

        Args:
            source: Source (URL, dict config, or VastUpstream object)
            strategy: Fetch strategy
            http_client: HTTP client (for HTTP upstreams)
            params: Additional query parameters (for URL/dict sources)
            headers: Additional headers (for URL/dict sources)

        Returns:
            FetchResult: Result of the fetch operation
        """
        # Create upstream from source
        try:
            upstream = create_upstream(source)
            source_id = upstream.get_identifier() if hasattr(upstream, 'get_identifier') else str(source)
        except (ValueError, TypeError) as e:
            return FetchResult(
                success=False,
                source_url=str(source),
                errors=[{"source": str(source), "error": f"Invalid source: {e}"}],
            )

        # Retry logic
        last_error = None
        for attempt in range(strategy.max_retries + 1):
            try:
                self.logger.debug(
                    "Fetching VAST from upstream",
                    source=source_id,
                    attempt=attempt + 1,
                    max_retries=strategy.max_retries,
                )

                # Fetch with timeout
                vast_xml = await asyncio.wait_for(
                    upstream.fetch(extra_params=params, extra_headers=headers),
                    timeout=strategy.per_source_timeout,
                )

                # Check for empty content
                if not vast_xml or not vast_xml.strip():
                    self.logger.debug("Received empty content", source=source_id)
                    return FetchResult(
                        success=False,
                        source_url=source_id,
                        errors=[{"source": source_id, "error": "Empty content"}],
                    )

                return FetchResult(
                    success=True,
                    source_url=source_id,
                    raw_response=vast_xml,
                    metadata={
                        "content_length": len(vast_xml),
                        "attempt": attempt + 1,
                    },
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {strategy.per_source_timeout}s"
                self.logger.warning(
                    "Fetch timeout",
                    source=source_id,
                    attempt=attempt + 1,
                    timeout=strategy.per_source_timeout,
                )

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                self.logger.warning(
                    "HTTP error",
                    source=source_id,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                )

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    "Fetch error",
                    source=source_id,
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
            source_url=source_id,
            errors=[{"source": source_id, "error": last_error}],
        )


__all__ = ["VastMultiSourceFetcher"]
