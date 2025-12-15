"""
Generic Provider Client Factory

Replaces hardcoded provider factory functions with YAML-driven configuration.
"""

from typing import Any

from .embed_http_client import EmbedHttpClient
from .provider_config_loader import ProviderConfigLoader
from .settings import get_settings


async def build_provider_client(
    provider: str, ad_request: dict[str, Any], settings=None
) -> EmbedHttpClient:
    """
    Build EmbedHttpClient for any provider using YAML configuration.

    This generic factory replaces provider-specific functions like:
    - build_global_client()
    - build_tiger_client()
    - build_leto_client()
    - build_adfox_client()

    Args:
        provider: Provider name (e.g., "global", "tiger", "leto", "yandex")
        ad_request: Ad request data for context preparation
        settings: Settings instance (optional, uses global if not provided)

    Returns:
        EmbedHttpClient configured for the provider

    Raises:
        ValueError: If provider not found or missing required configuration

    Examples:
        >>> ad_request = {
        ...     "device_macaddr": "00:11:22:33:44:55",
        ...     "user_agent": "DeviceUA/1.0",
        ...     "placement_type": "switchroll",
        ...     "ext": {
        ...         "domain": "example.com",
        ...         "channel_to": {
        ...             "display_name": "Channel 1",
        ...             "iptvorg_categories": "News"
        ...         }
        ...     }
        ... }
        >>> client = await build_provider_client("global", ad_request)
        >>> # Client is ready to use
        >>> vast_url = client.build_url()
    """
    settings = settings or get_settings()
    loader = ProviderConfigLoader(settings)

    # Build HTTP client configuration from YAML
    http_config = loader.build_http_client_config(provider, ad_request)

    # Create client and attach original ad_request for downstream macro resolution
    embed_client = EmbedHttpClient(
        base_url=http_config["base_url"],
        base_params=http_config["base_params"],
        base_headers=http_config["base_headers"],
        encoding_config=http_config["encoding_config"],
    )
    embed_client.set_extra("ad_request", ad_request)

    return embed_client


async def get_provider_client(
    provider: str, ad_request: dict[str, Any], settings=None
) -> EmbedHttpClient:
    """
    Alias for build_provider_client for backward compatibility.

    Args:
        provider: Provider name
        ad_request: Ad request data
        settings: Settings instance (optional)

    Returns:
        EmbedHttpClient configured for the provider
    """
    return await build_provider_client(provider, ad_request, settings)


# Export both names for flexibility
__all__ = [
    "build_provider_client",
    "get_provider_client",
]
