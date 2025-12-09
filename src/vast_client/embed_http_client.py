"""
Embedded HTTP Client for VAST Requests

Provides a specialized HTTP client wrapper that embeds base URL, parameters,
and headers into a single reusable client instance.
"""

import json
from typing import Any
from urllib.parse import urlencode, quote


class EmbedHttpClient:
    """
    HTTP client wrapper that embeds base configuration.

    This class wraps HTTP configuration (URL, params, headers) into a reusable
    client object that can generate full URLs and configurations for VAST requests.

    Attributes:
        base_url: Base URL for requests
        base_params: Base parameters to include in all requests
        base_headers: Base headers to include in all requests
        encoding_config: Configuration for parameter URL encoding

    Examples:
        >>> client = EmbedHttpClient(
        ...     base_url="https://g.adstrm.ru/vast3",
        ...     base_params={"city": "Санкт-Петербург", "city_code": 812},
        ...     base_headers={"Accept": "application/xml"},
        ...     encoding_config={"city": False}  # Don't encode Cyrillic
        ... )
        >>> url = client.build_url()
        >>> print(url)
        'https://g.adstrm.ru/vast3?city=Санкт-Петербург&city_code=812'
    """

    def __init__(
        self,
        base_url: str,
        base_params: dict[str, Any] | None = None,
        base_headers: dict[str, str] | None = None,
        encoding_config: dict[str, bool] | None = None,
    ):
        """
        Initialize EmbedHttpClient.

        Args:
            base_url: Base URL for all requests
            base_params: Default parameters for all requests
            base_headers: Default headers for all requests
            encoding_config: Per-parameter encoding configuration
                            True = URL encode, False = keep as-is
        """
        self.base_url = base_url
        self.base_params = base_params or {}
        self.base_headers = base_headers or {}
        self.encoding_config = encoding_config or {}

    def build_url(self, additional_params: dict[str, Any] | None = None) -> str:
        """
        Build complete URL with parameters.

        Args:
            additional_params: Additional parameters to merge with base params

        Returns:
            Complete URL with query string
        """
        # Merge parameters
        params = {**self.base_params}
        if additional_params:
            params.update(additional_params)

        # Handle JSON parameters
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, dict):
                # Serialize dict to JSON
                processed_params[key] = json.dumps(value)
            else:
                processed_params[key] = value

        # Build query string with encoding config
        query_parts = []
        for key, value in processed_params.items():
            should_encode = self.encoding_config.get(key, True)

            if should_encode:
                query_parts.append(f"{quote(str(key))}={quote(str(value))}")
            else:
                query_parts.append(f"{key}={value}")

        query_string = "&".join(query_parts)

        if query_string:
            return f"{self.base_url}?{query_string}"
        return self.base_url

    def get_headers(self, additional_headers: dict[str, str] | None = None) -> dict[str, str]:
        """
        Get complete headers dict.

        Args:
            additional_headers: Additional headers to merge with base headers

        Returns:
            Complete headers dictionary
        """
        headers = {**self.base_headers}
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for VastClient initialization.

        Returns:
            Dictionary with 'url', 'params', 'headers' keys
        """
        return {
            "url": self.base_url,
            "params": self.base_params,
            "headers": self.base_headers,
            "encoding_config": self.encoding_config,
        }

    def to_vast_config(self) -> dict[str, Any]:
        """
        Convert to VastClient-compatible configuration.

        Returns:
            Dictionary suitable for VastClient initialization
        """
        return {
            "url": self.build_url(),
            "headers": self.base_headers,
            "params": self.base_params,
        }

    def get_macros(self) -> dict[str, str]:
        """
        Extract macro mappings from parameters.

        Returns:
            Dictionary mapping parameter names to values
        """
        return {k: str(v) for k, v in self.base_params.items()}

    def set_extra(self, key: str, value: Any) -> None:
        """
        Set extra metadata on client.

        Args:
            key: Metadata key
            value: Metadata value
        """
        if not hasattr(self, "_extra"):
            self._extra = {}
        self._extra[key] = value

    def get_extra(self, key: str, default: Any = None) -> Any:
        """
        Get extra metadata from client.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if not hasattr(self, "_extra"):
            return default
        return self._extra.get(key, default)

    def has_extra(self, key: str) -> bool:
        """
        Check if extra metadata exists.

        Args:
            key: Metadata key

        Returns:
            True if metadata exists
        """
        return hasattr(self, "_extra") and key in self._extra

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmbedHttpClient":
        """
        Create EmbedHttpClient from dictionary.

        Args:
            data: Dictionary with 'base_url', 'base_params', 'base_headers'

        Returns:
            EmbedHttpClient instance
        """
        return cls(
            base_url=data.get("base_url", data.get("url", "")),
            base_params=data.get("base_params", data.get("params", {})),
            base_headers=data.get("base_headers", data.get("headers", {})),
            encoding_config=data.get("encoding_config", {}),
        )

    @classmethod
    async def from_provider_config(
        cls, provider: str, ad_request: dict[str, Any], settings=None
    ) -> "EmbedHttpClient":
        """
        Create EmbedHttpClient from YAML provider configuration.

        This is the recommended factory method for creating provider-specific
        HTTP clients using declarative YAML configuration.

        Args:
            provider: Provider name (e.g., "global", "tiger", "leto", "yandex")
            ad_request: Ad request data for context preparation
            settings: Settings instance (optional)

        Returns:
            Configured EmbedHttpClient instance

        Examples:
            >>> ad_request = {
            ...     "device_macaddr": "001122334455",
            ...     "user_agent": "DeviceUA/1.0",
            ...     "ext": {"channel_to": {"display_name": "Channel 1"}}
            ... }
            >>> client = await EmbedHttpClient.from_provider_config("global", ad_request)
            >>> url = client.build_url()
        """
        from .provider_factory import build_provider_client

        return await build_provider_client(provider, ad_request, settings)

    def with_params(self, **params) -> "EmbedHttpClient":
        """
        Create new client with additional base parameters.

        Args:
            **params: Parameters to add

        Returns:
            New EmbedHttpClient instance
        """
        new_params = {**self.base_params, **params}
        return EmbedHttpClient(
            base_url=self.base_url,
            base_params=new_params,
            base_headers=self.base_headers,
            encoding_config=self.encoding_config,
        )

    def with_headers(self, **headers) -> "EmbedHttpClient":
        """
        Create new client with additional base headers.

        Args:
            **headers: Headers to add

        Returns:
            New EmbedHttpClient instance
        """
        new_headers = {**self.base_headers, **headers}
        return EmbedHttpClient(
            base_url=self.base_url,
            base_params=self.base_params,
            base_headers=new_headers,
            encoding_config=self.encoding_config,
        )

    def with_url(self, url: str) -> "EmbedHttpClient":
        """
        Create new client with different base URL.

        Args:
            url: New base URL

        Returns:
            New EmbedHttpClient instance
        """
        return EmbedHttpClient(
            base_url=url,
            base_params=self.base_params,
            base_headers=self.base_headers,
            encoding_config=self.encoding_config,
        )

    def __repr__(self) -> str:
        return (
            f"EmbedHttpClient(base_url={self.base_url!r}, "
            f"params={len(self.base_params)}, "
            f"headers={len(self.base_headers)})"
        )


__all__ = ["EmbedHttpClient"]
