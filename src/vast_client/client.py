"""Main VAST client implementation."""

import time
from typing import TYPE_CHECKING, Any

import httpx

from .events import VastEvents
from .http_client_manager import (
    get_http_client_manager,
    get_main_http_client,
    get_tracking_http_client,
    record_main_client_request,
)
from .log_config import AdRequestContext, get_context_logger
from .routes.helpers import build_url_preserving_unicode
from .config import VastClientConfig, VastTrackerConfig
from .parser import VastParser
from .player import VastPlayer
from .tracker import VastTracker


if TYPE_CHECKING:
    from routes.helpers import EmbedHttpClient


class VastClient:
    """
    Facade for working with VAST advertising requests.

    Supports various initialization methods:
    - VastClient(url_string, ctx) - simple URL
    - VastClient(config_dict, ctx) - full configuration
    - VastClient.from_uri(uri, **kwargs) - from URI
    - VastClient.from_embed(embed_client, **kwargs) - from EmbedHttpClient

    Automatically uses context from context variables for logging.
    """

    def __init__(self, config_or_url, ctx: dict[str, Any] | None = None, **kwargs):
        """
        Universal VastClient constructor.

        Args:
            config_or_url: URL string, configuration dictionary, or VastClientConfig
            ctx: Request context (ad_request)
            **kwargs: Additional parameters (client, parser, tracker, ssl_verify, etc.)
        """
        # Ad request context (priority: ctx, then ad_request from kwargs)
        self.ad_request = ctx or kwargs.get("ad_request", {})

        # SSL verification setting
        self.ssl_verify = kwargs.get("ssl_verify", True)

        # Initialize contextual logger - automatically picks up context variables
        self.logger = get_context_logger("vast_client")

        # Check if config_or_url is VastClientConfig
        if isinstance(config_or_url, VastClientConfig):
            self._init_from_vast_config(config_or_url, **kwargs)
        else:
            # Legacy initialization
            # Extract components from kwargs
            self.parser = kwargs.get("parser") or VastParser()
            self.tracker = kwargs.get("tracker") or VastTracker(
                {},
                None,  # client will be fetched on each request
                None,  # embed_client will be set later
                None,  # No creative_id initially
            )
            # Parse configuration
            self._parse_config(config_or_url, kwargs.get("embed_client"))

    def _parse_config(self, config_or_url, embed_client: "EmbedHttpClient | None" = None):
        """Parse configuration from various sources."""
        # Priority: embed_client > config_dict > url_string
        if embed_client:
            self._init_from_embed_client(embed_client)
        elif isinstance(config_or_url, dict):
            self._init_from_config_dict(config_or_url)
        elif isinstance(config_or_url, str):
            self._init_from_url_string(config_or_url)
        else:
            raise ValueError(f"Unsupported config type: {type(config_or_url)}")

    def _init_from_embed_client(self, embed_client: "EmbedHttpClient"):
        """Initialize from EmbedHttpClient."""
        self.upstream_url = embed_client.base_url
        self.embedded_params = embed_client.base_params
        self.embedded_headers = embed_client.base_headers
        self.encoding_config = embed_client.encoding_config
        self.embed_client = embed_client

        self.logger.debug(
            "VastClient initialized from EmbedHttpClient",
            url=self.upstream_url,
            embedded_params=list(self.embedded_params.keys()),
            embedded_headers=list(self.embedded_headers.keys()),
            encoding_config=self.encoding_config,
        )

    def _init_from_config_dict(self, config: dict[str, Any]):
        """Initialize from configuration dictionary."""
        # Support nested client config
        client_config = config.get("client", {})
        if client_config and isinstance(client_config, dict):
            # If client.base_url exists, use as EmbedHttpClient
            if "base_url" in client_config:
                from routes.helpers import EmbedHttpClient

                base_url = client_config.get("base_url")
                if base_url:  # Check that base_url is not None
                    embed_client = EmbedHttpClient(
                        base_url=base_url,
                        base_params=client_config.get("params", {}),
                        base_headers=client_config.get("headers", {}),
                        encoding_config=client_config.get("encoding_config", {}),
                    )
                    self._init_from_embed_client(embed_client)
                    return

        # Regular configuration
        self.upstream_url = config.get("url") or config.get("base_url")
        self.embedded_params = config.get("params", {})
        self.embedded_headers = config.get("headers", {})
        self.encoding_config = config.get("encoding_config", {})
        self.embed_client = None

        self.logger.debug(
            "VastClient initialized from config dict",
            url=self.upstream_url,
            embedded_params=list(self.embedded_params.keys()),
            embedded_headers=list(self.embedded_headers.keys()),
            encoding_config=self.encoding_config,
        )

    def _init_from_url_string(self, url: str):
        """Initialize from simple URL."""
        self.upstream_url = url
        self.embedded_params = {}
        self.embedded_headers = {}
        self.encoding_config = {}
        self.embed_client = None

        self.logger.debug("VastClient initialized from URL string", url=self.upstream_url)

    def _init_from_vast_config(self, config: VastClientConfig, **kwargs):
        """Initialize from VastClientConfig."""
        self.config = config

        # Store ssl_verify from config (can be overridden by kwargs)
        if "ssl_verify" in kwargs:
            self.ssl_verify = kwargs["ssl_verify"]
        elif hasattr(config, "ssl_verify"):
            self.ssl_verify = config.ssl_verify
        else:
            self.ssl_verify = True  # default

        # Initialize components from config
        # Note: client is NOT cached here - it will be fetched on each request

        # Create parser from config
        if isinstance(config.parser, VastParser):
            self.parser = config.parser
        else:
            self.parser = VastParser.from_config(config.parser.__dict__)

        # Create initial tracker (will be replaced when ad is requested)
        self.tracker = VastTracker(
            {},
            None,  # client will be fetched on each request
            None,  # embed_client will be set later
            None,  # No creative_id initially
            config.tracker if isinstance(config.tracker, VastTrackerConfig) else None,
        )

        # For backward compatibility, set some attributes
        self.upstream_url = None
        self.embedded_params = {}
        self.embedded_headers = {}
        self.encoding_config = {}
        self.embed_client = None

        self.logger.debug(
            "VastClient initialized from VastClientConfig",
            provider=config.provider,
            publisher=config.publisher,
            enable_tracking=config.enable_tracking,
            enable_parsing=config.enable_parsing,
            ssl_verify=self.ssl_verify,
        )

    @classmethod
    def from_uri(cls, uri: str, ctx: dict[str, Any] | None = None, **kwargs) -> "VastClient":
        """
        Create VastClient from URI.

        Args:
            uri: URI string
            ctx: Request context (ad_request)
            **kwargs: Additional parameters

        Returns:
            VastClient: New client instance

        Example:
            client = VastClient.from_uri("https://ads.example.com/vast", ctx=ad_request)
        """
        return cls(uri, ctx, **kwargs)

    @classmethod
    def from_embed(
        cls,
        embed_client: "EmbedHttpClient",
        ctx: dict[str, Any] | None = None,
        **kwargs,
    ) -> "VastClient":
        """
        Create VastClient from EmbedHttpClient.

        Args:
            embed_client: EmbedHttpClient instance
            ctx: Request context (ad_request)
            **kwargs: Additional parameters

        Returns:
            VastClient: New client instance

        Example:
            embed = EmbedHttpClient(base_url="https://ads.example.com", ...)
            client = VastClient.from_embed(embed, ctx=ad_request)
        """
        kwargs["embed_client"] = embed_client
        return cls("", ctx, **kwargs)

    @classmethod
    def from_config(
        cls, config: dict[str, Any], ctx: dict[str, Any] | None = None, **kwargs
    ) -> "VastClient":
        """
        Create VastClient from configuration dictionary.

        Args:
            config: Configuration dictionary
            ctx: Request context (ad_request)
            **kwargs: Additional parameters

        Returns:
            VastClient: New client instance

        Example:
            config = {
                "client": {
                    "base_url": "https://ads.example.com",
                    "params": {"key": "value"},
                    "headers": {"User-Agent": "MyApp"}
                },
                "parser": {...},
                "tracker": {...}
            }
            client = VastClient.from_config(config, ctx=ad_request)
        """
        # Extract components from config into kwargs
        if "parser" in config and "parser" not in kwargs:
            # Only if it's a real parser object, not dict
            if hasattr(config["parser"], "parse_vast"):
                kwargs["parser"] = config["parser"]
        if "tracker" in config and "tracker" not in kwargs:
            # Only if it's a real tracker object, not dict
            if hasattr(config["tracker"], "track_event"):
                kwargs["tracker"] = config["tracker"]
        # DON'T extract 'client' as httpx.AsyncClient if it's dict with configuration

        return cls(config, ctx, **kwargs)

    async def request_ad(
        self,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        """Request ad from VAST endpoint.

        Args:
            params: Additional parameters for the request
            headers: Additional headers for the request

        Returns:
            Raw response string or parsed VAST data dictionary

        Raises:
            httpx.HTTPStatusError: For HTTP errors
            Exception: For other request errors
        """
        start_time = time.time()
        success = False
        error_type = None
        info_type = None

        try:
            # Use EmbedHttpClient if available
            if self.embed_client:
                final_url = self.embed_client.build_url(params)
                final_headers = self.embed_client.get_headers(headers)
                self.logger.debug("Using EmbedHttpClient for URL building", url=final_url)
            else:
                # Merge embedded parameters and headers with passed ones
                final_params = {**self.embedded_params, **(params or {})}
                final_headers = {**self.embedded_headers, **(headers or {})}

                self.logger.debug(
                    "Requesting ad",
                    url=self.upstream_url,
                    params=final_params,
                    headers=list(final_headers.keys()),
                )

                # Log Cyrillic parameters for debugging
                for key, value in final_params.items():
                    if isinstance(value, str) and any(ord(char) > 127 for char in value):
                        self.logger.debug("Cyrillic parameter detected", key=key, value=value)

                # Build URL preserving Unicode symbols (including Cyrillic)
                if self.upstream_url is None:
                    raise ValueError("Upstream URL must not be None")

                self.logger.debug(
                    "Building URL",
                    base_url=self.upstream_url,
                    has_query=("?" in self.upstream_url),
                    params_count=len(final_params),
                    encoding_config=self.encoding_config,
                )

                final_url = build_url_preserving_unicode(self.upstream_url, final_params)

                self.logger.debug("Final request URL", url=final_url)

            # Make request with manually constructed URL to avoid automatic encoding
            # Get SSL verification setting (priority: config > instance > default)
            ssl_verify = self.ssl_verify
            if hasattr(self, "config") and self.config and hasattr(self.config, "ssl_verify"):
                ssl_verify = self.config.ssl_verify

            # Always get fresh HTTP client from manager (avoids closed client issues)
            http_client = get_main_http_client(ssl_verify=ssl_verify)
            response = await http_client.get(final_url, headers=final_headers)

            if response.status_code == 204:
                success = True  # 204 - valid response (no ad)
                info_type = "no_content"  # Special marker for no ad
                self.logger.debug("Received 204 No Content response, no ad data available.")
                return ""

            response.raise_for_status()
            success = True  # HTTP request successful
            response_text = response.text

            self.logger.info(
                VastEvents.REQUEST_COMPLETED,
                status_code=response.status_code,
                response_length=len(response_text),
                vast_response_preview=response_text[:500]
                if len(response_text) > 500
                else response_text,
            )

            # If response contains VAST XML, parse it
            content_type = response.headers.get("content-type", "").lower()
            is_xml_content = "xml" in content_type
            starts_with_xml = response_text.strip().startswith("<?xml")

            self.logger.debug(
                "Analyzing response content",
                content_type=content_type,
                is_xml_content=is_xml_content,
                starts_with_xml=starts_with_xml,
                response_preview=response_text[:200],
            )

            if is_xml_content or starts_with_xml:
                self.logger.info("Detected XML response, attempting VAST parsing")
                try:
                    vast_data = self.parser.parse_vast(response_text)

                    # Preserve raw VAST XML response
                    vast_data["_raw_vast_response"] = response_text

                    # Create tracker if there are events to track
                    tracking_events: dict[str, list[str]] = vast_data.get("tracking_events", {})
                    tracking_events.update({"impression": vast_data.get("impression", [])})
                    tracking_events.update({"error": vast_data.get("error", [])})

                    if tracking_events:
                        # Extract creative_id from vast_data
                        creative_data = vast_data.get("creative", {})
                        creative_id = creative_data.get("id") or creative_data.get("ad_id")

                        self.logger.info(
                            "Creating VastTracker",
                            tracking_events_count=len(tracking_events),
                            creative_id=creative_id,
                        )
                        # Use separate client for tracking
                        tracking_client = get_tracking_http_client()
                        self.tracker = VastTracker(
                            tracking_events,
                            tracking_client,
                            self.embed_client,  # Use embed_client instead of ad_request
                            creative_id,
                        )
                    else:
                        self.logger.debug("No tracking events found, skipping tracker creation")

                    return vast_data
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse as VAST XML, returning raw response",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return response_text
            else:
                self.logger.info("Non-XML response detected, returning raw content")
                return response_text

        except httpx.HTTPStatusError as e:
            error_type = f"http_{e.response.status_code}"
            self.logger.error(
                "HTTP error in ad request",
                status_code=e.response.status_code,
                url=str(e.request.url),
            )
            raise
        except Exception as e:
            error_type = "exception"
            self.logger.exception("Unexpected error in ad request", error=str(e))
            raise
        finally:
            # Record request metric
            response_time = time.time() - start_time
            record_main_client_request(success, response_time, error_type, info_type)

    async def play_ad(self, ad_data: dict[str, Any]):
        """Play ad using VastPlayer.

        Args:
            ad_data: Parsed VAST ad data
        """
        player = VastPlayer(self, ad_data)
        await player.play()

    async def close(self):
        """Close client and cleanup resources."""
        # Don't close global HTTP client - managed by manager
        if self.client is not None and hasattr(self.client, "_is_global_client"):
            # This is global client, don't close it
            pass
        elif self.client is not None:
            # This is local client, close it
            await self.client.aclose()

        self.logger.info("VastClient closed")
        # Clear playback context when closing client
        from .log_config import clear_playback_context

        clear_playback_context()

    async def __aenter__(self):
        """Async context manager entry."""
        # Set context variables from ad_request if not already set
        if self.ad_request:
            self._context_manager = AdRequestContext(**self.ad_request)
            self._context_manager.__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, "_context_manager"):
            self._context_manager.__exit__(exc_type, exc_val, exc_tb)
        await self.close()


__all__ = ["VastClient"]
