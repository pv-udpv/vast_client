"""
VAST Upstream Protocol and Implementations

Defines the abstract upstream interface for VAST sources, allowing flexible
implementations with different transport mechanisms, client configurations,
and middleware.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, Union

import httpx

from ..log_config import get_context_logger
from ..routes.helpers import build_url_preserving_unicode


class VastUpstream(Protocol):
    """
    Protocol for VAST upstream sources.

    An upstream represents a source that can fetch VAST XML content. It abstracts
    away the transport mechanism, allowing for HTTP, gRPC, local files, mocks, etc.

    Examples:
        >>> class MyCustomUpstream:
        ...     async def fetch(self, extra_params=None, extra_headers=None):
        ...         # Custom fetch logic
        ...         return "<VAST>...</VAST>"
        ...
        >>> upstream = MyCustomUpstream()
        >>> xml = await upstream.fetch()
    """

    async def fetch(
        self,
        extra_params: Union[dict[str, Any], None] = None,
        extra_headers: Union[dict[str, str], None] = None,
    ) -> str:
        """
        Fetch VAST XML content.

        Args:
            extra_params: Additional query parameters to merge
            extra_headers: Additional headers to merge

        Returns:
            str: VAST XML content

        Raises:
            Exception: If fetch fails
        """
        ...


class BaseUpstream(ABC):
    """
    Base class for VAST upstream implementations.

    Provides common functionality and logging infrastructure.
    """

    def __init__(self):
        """Initialize base upstream."""
        self.logger = get_context_logger(f"vast_upstream.{self.__class__.__name__}")

    @abstractmethod
    async def fetch(
        self,
        extra_params: Union[dict[str, Any], None] = None,
        extra_headers: Union[dict[str, str], None] = None,
    ) -> str:
        """Fetch VAST XML content."""
        pass

    def get_identifier(self) -> str:
        """
        Get identifier for this upstream (for logging/debugging).

        Returns:
            str: Upstream identifier
        """
        return f"{self.__class__.__name__}"


class HttpUpstream(BaseUpstream):
    """
    HTTP-based VAST upstream.

    Fetches VAST XML from an HTTP endpoint using httpx.

    Attributes:
        base_url: Base URL for the VAST endpoint
        base_params: Default query parameters
        base_headers: Default HTTP headers
        encoding_config: Per-parameter encoding rules
        http_client: HTTP client instance (optional, will use default if not provided)
        timeout: Request timeout in seconds

    Examples:
        Simple URL upstream:
        >>> upstream = HttpUpstream("https://ads.example.com/vast")
        >>> xml = await upstream.fetch()

        With custom configuration:
        >>> upstream = HttpUpstream(
        ...     base_url="https://ads.example.com/vast",
        ...     base_params={"publisher": "acme"},
        ...     base_headers={"User-Agent": "CTV/1.0"},
        ...     timeout=10.0
        ... )
        >>> xml = await upstream.fetch(extra_params={"slot": "pre-roll"})
    """

    def __init__(
        self,
        base_url: str,
        base_params: Union[dict[str, Any], None] = None,
        base_headers: Union[dict[str, str], None] = None,
        encoding_config: Union[dict[str, bool], None] = None,
        http_client: Union[httpx.AsyncClient, None] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize HTTP upstream.

        Args:
            base_url: Base URL for VAST endpoint
            base_params: Default query parameters
            base_headers: Default HTTP headers
            encoding_config: Per-parameter URL encoding rules (param_name → bool)
            http_client: HTTP client to use (optional)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.base_url = base_url
        self.base_params = base_params or {}
        self.base_headers = base_headers or {}
        self.encoding_config = encoding_config or {}
        self._http_client = http_client
        self.timeout = timeout

    async def fetch(
        self,
        extra_params: Union[dict[str, Any], None] = None,
        extra_headers: Union[dict[str, str], None] = None,
    ) -> str:
        """
        Fetch VAST XML via HTTP GET request.

        Args:
            extra_params: Additional query parameters to merge with base_params
            extra_headers: Additional headers to merge with base_headers

        Returns:
            str: VAST XML content

        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            httpx.TimeoutException: If request times out
        """
        # Merge parameters and headers
        params = {**self.base_params}
        if extra_params:
            params.update(extra_params)

        headers = {**self.base_headers}
        if extra_headers:
            headers.update(extra_headers)

        # Build URL with encoding config
        if params:
            url = build_url_preserving_unicode(
                self.base_url, params, self.encoding_config
            )
        else:
            url = self.base_url

        self.logger.debug(
            "Fetching VAST via HTTP",
            url=url,
            params_count=len(params),
            headers_count=len(headers),
        )

        # Get or create HTTP client
        if self._http_client:
            response = await self._http_client.get(
                url, headers=headers, timeout=self.timeout
            )
        else:
            # Use default client from http_client_manager
            from ..http_client_manager import get_main_http_client

            http_client = get_main_http_client()
            response = await http_client.get(
                url, headers=headers, timeout=self.timeout
            )

        response.raise_for_status()

        self.logger.debug(
            "VAST fetched successfully",
            status_code=response.status_code,
            content_length=len(response.text),
        )

        return response.text

    def get_identifier(self) -> str:
        """Get identifier for this upstream."""
        return self.base_url


class LocalFileUpstream(BaseUpstream):
    """
    Local file-based VAST upstream.

    Reads VAST XML from a local file. Useful for testing and development.

    Attributes:
        file_path: Path to the VAST XML file

    Examples:
        >>> upstream = LocalFileUpstream("/path/to/vast.xml")
        >>> xml = await upstream.fetch()
    """

    def __init__(self, file_path: str):
        """
        Initialize local file upstream.

        Args:
            file_path: Path to VAST XML file
        """
        super().__init__()
        self.file_path = file_path

    async def fetch(
        self,
        extra_params: Union[dict[str, Any], None] = None,
        extra_headers: Union[dict[str, str], None] = None,
    ) -> str:
        """
        Read VAST XML from local file.

        Args:
            extra_params: Ignored for file upstream
            extra_headers: Ignored for file upstream

        Returns:
            str: VAST XML content

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file read fails
        """
        self.logger.debug("Reading VAST from local file", file_path=self.file_path)

        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.logger.debug(
            "VAST file read successfully", content_length=len(content)
        )

        return content

    def get_identifier(self) -> str:
        """Get identifier for this upstream."""
        return f"file://{self.file_path}"


class MockUpstream(BaseUpstream):
    """
    Mock VAST upstream for testing.

    Returns predefined VAST XML content without network requests.

    Attributes:
        vast_xml: The VAST XML content to return
        delay: Simulated delay in seconds (optional)

    Examples:
        >>> upstream = MockUpstream("<VAST>...</VAST>")
        >>> xml = await upstream.fetch()

        With simulated delay:
        >>> upstream = MockUpstream("<VAST>...</VAST>", delay=0.5)
        >>> xml = await upstream.fetch()  # Takes 0.5 seconds
    """

    def __init__(self, vast_xml: str, delay: float = 0.0):
        """
        Initialize mock upstream.

        Args:
            vast_xml: VAST XML content to return
            delay: Simulated delay in seconds
        """
        super().__init__()
        self.vast_xml = vast_xml
        self.delay = delay

    async def fetch(
        self,
        extra_params: Union[dict[str, Any], None] = None,
        extra_headers: Union[dict[str, str], None] = None,
    ) -> str:
        """
        Return mock VAST XML content.

        Args:
            extra_params: Ignored for mock upstream
            extra_headers: Ignored for mock upstream

        Returns:
            str: Mock VAST XML content
        """
        if self.delay > 0:
            import asyncio

            self.logger.debug("Simulating delay", delay=self.delay)
            await asyncio.sleep(self.delay)

        self.logger.debug("Returning mock VAST", content_length=len(self.vast_xml))
        return self.vast_xml

    def get_identifier(self) -> str:
        """Get identifier for this upstream."""
        return "mock://vast"


def create_upstream(source: Union[str, dict[str, Any], "VastUpstream"]) -> "VastUpstream":
    """
    Factory function to create upstream from various source types.

    Converts URL strings and dict configurations into appropriate upstream instances,
    or returns the upstream as-is if it's already an upstream object.

    Args:
        source: Source specification (URL string, dict config, or VastUpstream)

    Returns:
        VastUpstream: Upstream instance

    Raises:
        ValueError: If source dict is invalid
        TypeError: If source type is unsupported

    Examples:
        From URL string:
        >>> upstream = create_upstream("https://ads.example.com/vast")

        From dict config:
        >>> upstream = create_upstream({
        ...     "base_url": "https://ads.example.com/vast",
        ...     "params": {"publisher": "acme"}
        ... })

        From upstream object (pass-through):
        >>> custom_upstream = MyCustomUpstream()
        >>> upstream = create_upstream(custom_upstream)
        >>> assert upstream is custom_upstream
    """
    # If already an upstream, return as-is
    if hasattr(source, "fetch") and callable(source.fetch):
        return source

    # String URL -> HttpUpstream
    if isinstance(source, str):
        return HttpUpstream(base_url=source)

    # Dict config -> HttpUpstream with config
    if isinstance(source, dict):
        base_url = source.get("base_url") or source.get("url")
        if not base_url:
            raise ValueError(
                f"Dict source must have 'base_url' or 'url' key: {source}"
            )

        return HttpUpstream(
            base_url=base_url,
            base_params=source.get("params"),
            base_headers=source.get("headers"),
            encoding_config=source.get("encoding_config"),
            timeout=source.get("timeout", 10.0),
        )

    raise TypeError(
        f"Source must be str, dict, or VastUpstream, got {type(source).__name__}"
    )


__all__ = [
    "VastUpstream",
    "BaseUpstream",
    "HttpUpstream",
    "LocalFileUpstream",
    "MockUpstream",
    "create_upstream",
]
