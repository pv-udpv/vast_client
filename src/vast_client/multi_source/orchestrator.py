"""
Multi-Source VAST Orchestrator

Main coordinator for multi-source VAST operations. Implements the pipeline:
FETCH → PARSE → SELECT → TRACK
"""

from ..events import VastEvents
from ..http_client_manager import get_main_http_client, get_tracking_http_client
from ..log_config import get_context_logger
from ..parser import VastParser
from .fetch_config import FetchResult, VastFetchConfig
from .fetcher import VastMultiSourceFetcher
from .parse_filter import VastParseFilter
from .tracker import MultiSourceTracker


class VastMultiSourceOrchestrator:
    """
    Main orchestrator for multi-source VAST operations.

    Coordinates the full pipeline: FETCH → PARSE → SELECT → TRACK

    This is the primary entry point for multi-source VAST requests.
    Single-source requests are handled as a special case with sources=[url].

    Attributes:
        parser: VAST XML parser instance
        fetcher: Multi-source fetcher instance

    Examples:
        Single-source request (margin case):
        >>> orchestrator = VastMultiSourceOrchestrator(parser)
        >>> config = VastFetchConfig(sources=["https://ads.example.com/vast"])
        >>> result = await orchestrator.execute_pipeline(config)

        Multi-source with fallbacks:
        >>> config = VastFetchConfig(
        ...     sources=["https://ads1.com/vast", "https://ads2.com/vast"],
        ...     fallbacks=["https://fallback.com/vast"],
        ...     auto_track=True
        ... )
        >>> result = await orchestrator.execute_pipeline(config)

        With parse filter:
        >>> from .parse_filter import VastParseFilter, MediaType
        >>> filter = VastParseFilter(media_types=[MediaType.VIDEO], min_duration=15)
        >>> config = VastFetchConfig(
        ...     sources=["https://ads.example.com/vast"],
        ...     parse_filter=filter
        ... )
        >>> result = await orchestrator.execute_pipeline(config)
    """

    def __init__(
        self,
        parser: VastParser | None = None,
        ssl_verify: bool = True,
    ):
        """
        Initialize the orchestrator.

        Args:
            parser: VAST parser instance (creates default if None)
            ssl_verify: SSL verification setting for HTTP clients
        """
        self.logger = get_context_logger("vast_multi_source_orchestrator")
        self.parser = parser or VastParser()
        self.fetcher = VastMultiSourceFetcher()
        self.ssl_verify = ssl_verify

        self.logger.debug("VastMultiSourceOrchestrator initialized")

    async def execute_pipeline(
        self,
        config: VastFetchConfig,
        parse_filter: VastParseFilter | None = None,
        auto_track: bool | None = None,
    ) -> FetchResult:
        """
        Execute the full multi-source pipeline: FETCH → PARSE → SELECT → TRACK.

        Args:
            config: Fetch configuration with sources and strategy
            parse_filter: Optional filter to apply during parsing
            auto_track: Override config.auto_track setting

        Returns:
            FetchResult: Result with parsed data and tracking info

        Raises:
            ValueError: If config is invalid
        """
        if not config.sources:
            raise ValueError("VastFetchConfig must have at least one source")

        # Use parse filter from config if not provided
        if parse_filter is None:
            parse_filter = config.parse_filter

        # Use auto_track from config if not overridden
        if auto_track is None:
            auto_track = config.auto_track

        self.logger.info(
            VastEvents.REQUEST_STARTED,
            source_count=len(config.sources),
            fallback_count=len(config.fallbacks),
            auto_track=auto_track,
            has_filter=parse_filter is not None,
        )

        # PHASE 1: FETCH
        http_client = get_main_http_client(ssl_verify=self.ssl_verify)

        if config.fallbacks:
            fetch_result = await self.fetcher.fetch_with_fallbacks(
                sources=config.sources,
                fallbacks=config.fallbacks,
                strategy=config.strategy,
                http_client=http_client,
                params=config.params,
                headers=config.headers,
            )
        else:
            fetch_result = await self.fetcher.fetch_all(
                sources=config.sources,
                strategy=config.strategy,
                http_client=http_client,
                params=config.params,
                headers=config.headers,
            )

        if not fetch_result.success:
            self.logger.error(
                VastEvents.REQUEST_FAILED,
                error_count=len(fetch_result.errors),
                errors=fetch_result.errors,
            )
            return fetch_result

        # PHASE 2: PARSE
        try:
            vast_data = self.parser.parse_vast(fetch_result.raw_response)
            fetch_result.parsed_data = vast_data
            fetch_result.metadata["parsed"] = True

            self.logger.info(
                VastEvents.PARSE_SUCCESS,
                ad_system=vast_data.get("ad_system"),
                duration=vast_data.get("duration"),
                creative_id=vast_data.get("creative", {}).get("id"),
            )

        except Exception as e:
            self.logger.error(
                VastEvents.PARSE_FAILED,
                error=str(e),
                error_type=type(e).__name__,
            )
            fetch_result.errors.append({
                "phase": "parse",
                "error": str(e),
                "error_type": type(e).__name__,
            })
            return fetch_result

        # PHASE 3: SELECT (Apply filter if provided)
        if parse_filter is not None:
            if not parse_filter.matches(vast_data):
                self.logger.info(
                    "VAST data filtered out",
                    filter_criteria=str(parse_filter),
                )
                fetch_result.success = False
                fetch_result.errors.append({
                    "phase": "select",
                    "error": "VAST data did not match filter criteria",
                })
                return fetch_result

        # PHASE 4: TRACK (if auto_track enabled)
        if auto_track:
            try:
                tracking_client = get_tracking_http_client()
                creative_data = vast_data.get("creative", {})
                creative_id = creative_data.get("id") or creative_data.get("ad_id")

                tracker = MultiSourceTracker(
                    vast_data=vast_data,
                    http_client=tracking_client,
                    creative_id=creative_id,
                )

                # Track impression
                if tracker.has_event("impression"):
                    tracking_result = await tracker.track_impression()
                    fetch_result.metadata["impression_tracked"] = True
                    fetch_result.metadata["tracking_result"] = tracking_result

                    self.logger.info(
                        VastEvents.TRACKING_SUCCESS,
                        event_type="impression",
                        result=tracking_result,
                    )

            except Exception as e:
                # Don't fail the whole operation on tracking errors
                self.logger.warning(
                    VastEvents.TRACKING_FAILED,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                fetch_result.metadata["tracking_error"] = str(e)

        self.logger.info(
            VastEvents.REQUEST_SUCCESS,
            source_url=fetch_result.source_url,
            parsed=fetch_result.parsed_data is not None,
            tracked=fetch_result.metadata.get("impression_tracked", False),
        )

        return fetch_result


__all__ = ["VastMultiSourceOrchestrator"]
