"""
VAST Client Helpers Module

Provides utility functions and helpers for VAST client operations,
including EmbedHttpClient integration and URL building utilities.
"""

import secrets
from typing import Any

from shared.helpers import (
    PROVIDER_IPS,
    generate_uuid_from_multi_fields,
)

# Import base classes from the http_client module - this is the authoritative source
from .http_client import EmbedHttpClient, build_url_preserving_unicode


class VastEmbedHttpClient(EmbedHttpClient):
    """
    Enhanced EmbedHttpClient specifically for VAST operations.

    Provides VAST-specific functionality while maintaining compatibility
    with the base EmbedHttpClient interface.
    """

    def __init__(
        self,
        base_url: str,
        base_params: dict[str, Any] | None = None,
        base_headers: dict[str, str] | None = None,
        encoding_config: dict[str, bool] | None = None,
        vast_settings: dict[str, Any] | None = None,
    ):
        """
        Initialize VAST-specific HTTP client.

        Args:
            base_url: Base URL for VAST requests
            base_params: Base parameters for all requests
            base_headers: Base headers for all requests
            encoding_config: URL encoding configuration
            vast_settings: VAST-specific settings
        """
        super().__init__(base_url, base_params, base_headers, encoding_config)
        self.vast_settings = vast_settings or {}

    def build_vast_url(
        self,
        placement_type: str = "switchroll",
        additional_params: dict[str, Any] | None = None,
    ) -> str:
        """
        Build VAST request URL with placement-specific parameters.

        Args:
            placement_type: Type of ad placement (switchroll, preroll, etc.)
            additional_params: Additional parameters for the request

        Returns:
            Complete VAST request URL
        """
        params = {
            "ad_place": placement_type,
            "media_type": "stream",
            **(additional_params or {}),
        }

        return self.build_url(params)

    def with_vast_context(self, ad_request: dict[str, Any]) -> "VastEmbedHttpClient":
        """
        Create a new client with ad request context.

        Args:
            ad_request: Ad request context data

        Returns:
            New VastEmbedHttpClient with context-specific configuration
        """
        # Extract context-specific data
        device_serial = self._generate_device_serial(ad_request)
        user_agent = ad_request.get("user_agent", "")

        # Create context-specific headers
        context_headers = {
            "User-Agent": user_agent,
            "X-Serial-Number": device_serial,
            "Accept": "application/xml, text/xml, */*",
        }

        # Create context-specific parameters
        context_params = {
            "ab_uid": device_serial,
        }

        # If channel information is available, add it
        if "ext" in ad_request and "channel_to" in ad_request["ext"]:
            channel = ad_request["ext"]["channel_to"]
            if hasattr(channel, "get_display_name"):
                context_params["media_title"] = channel.get_display_name()
            if hasattr(channel, "iptvorg_categories"):
                context_params["media_tag"] = channel.iptvorg_categories

        return VastEmbedHttpClient(
            base_url=self.base_url,
            base_params={**self.base_params, **context_params},
            base_headers={**self.base_headers, **context_headers},
            encoding_config=self.encoding_config,
            vast_settings=self.vast_settings,
        )

    def _generate_device_serial(self, ad_request: dict[str, Any]) -> str:
        """Generate device serial from ad request context."""
        macaddr = ad_request.get("device_macaddr", "")
        user_agent = ad_request.get("user_agent", "")
        domain = ad_request.get("ext", {}).get("domain", "")

        return generate_uuid_from_multi_fields(
            "VAST_CLIENT", macaddr, user_agent, domain
        )

    def get_vast_headers(self, tracking: bool = False) -> dict[str, str]:
        """
        Get headers optimized for VAST requests.

        Args:
            tracking: Whether this is for tracking requests

        Returns:
            Headers dictionary
        """
        headers = self.get_headers()

        if tracking:
            # For tracking requests, we might want different headers
            headers.update(
                {
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
            )

        return headers

    def copy_vast(self) -> "VastEmbedHttpClient":
        """Create a copy of this VAST client."""
        return VastEmbedHttpClient(
            base_url=self.base_url,
            base_params=self.base_params.copy(),
            base_headers=self.base_headers.copy(),
            encoding_config=self.encoding_config.copy(),
            vast_settings=self.vast_settings.copy(),
        )


def create_vast_client_from_config(
    provider: str,
    ad_request: dict[str, Any],
    provider_configs: dict[str, dict[str, Any]] | None = None,
) -> VastEmbedHttpClient:
    """
    Create a VastEmbedHttpClient for a specific provider.

    Args:
        provider: Provider name (e.g., "global", "tiger")
        ad_request: Ad request context
        provider_configs: Provider-specific configurations

    Returns:
        Configured VastEmbedHttpClient
    """
    configs = provider_configs or {}

    if provider == "global":
        return _create_global_vast_client(ad_request, configs.get("global", {}))
    elif provider == "tiger":
        return _create_tiger_vast_client(ad_request, configs.get("tiger", {}))
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _create_global_vast_client(
    ad_request: dict[str, Any], config: dict[str, Any]
) -> VastEmbedHttpClient:
    """Create VAST client for Global/AdStream provider."""
    # Default IPs for AT-HOME provider
    default_ips = [
        "213.21.4.190",
        "213.21.14.29",
        "213.21.19.169",
        "77.239.236.16",
        "77.239.238.211",
        "77.239.253.122",
    ]

    ip_list = config.get("provider_ips", default_ips)
    ip = secrets.choice(ip_list) if ip_list else "213.21.4.190"

    device_serial = generate_uuid_from_multi_fields(
        "GLOBAL",
        ad_request.get("device_macaddr", ""),
        ad_request.get("user_agent", ""),
        ad_request.get("ext", {}).get("domain", ""),
    )

    base_params = {
        "city": "Санкт-Петербург",
        "ab_uid": device_serial,
        "media_type": "stream",
        "city_code": 812,
    }

    base_headers = {
        "User-Agent": ad_request.get("user_agent", ""),
        "X-Serial-Number": device_serial,
        "X-Real-Ip": ip,
        "X-Forwarded-For": ip,
        "Accept": "application/xml, text/xml, */*",
    }

    encoding_config = {
        "city": False,  # Keep Cyrillic as-is
        "ab_uid": False,
        "media_type": False,
        "city_code": False,
    }

    return VastEmbedHttpClient(
        base_url=config.get("base_url", "https://g.adstrm.ru/vast3"),
        base_params=base_params,
        base_headers=base_headers,
        encoding_config=encoding_config,
        vast_settings=config,
    )


def _create_tiger_vast_client(
    ad_request: dict[str, Any], config: dict[str, Any]
) -> VastEmbedHttpClient:
    """Create VAST client for Tiger provider."""
    device_serial = generate_uuid_from_multi_fields(
        "TIGER",
        ad_request.get("device_macaddr", ""),
        ad_request.get("user_agent", ""),
        ad_request.get("ext", {}).get("domain", ""),
    )

    base_params = {
        "ab_uid": device_serial,
        "media_type": "stream",
    }

    base_headers = {
        "User-Agent": ad_request.get("user_agent", ""),
        "X-Serial-Number": device_serial,
        "Accept": "application/xml, text/xml, */*",
    }

    return VastEmbedHttpClient(
        base_url=config.get("base_url", "https://tiger.adstrm.ru/vast3"),
        base_params=base_params,
        base_headers=base_headers,
        encoding_config={},
        vast_settings=config,
    )


def build_vast_tracking_url(
    base_url: str,
    event_type: str,
    additional_params: dict[str, Any] | None = None,
) -> str:
    """
    Build URL for VAST tracking events.

    Args:
        base_url: Base tracking URL
        event_type: Type of tracking event
        additional_params: Additional tracking parameters

    Returns:
        Complete tracking URL
    """
    params = {
        "event": event_type,
        **(additional_params or {}),
    }

    return build_url_preserving_unicode(base_url, params)


__all__ = [
    "VastEmbedHttpClient",
    "create_vast_client_from_config",
    "build_vast_tracking_url",
    "generate_uuid_from_multi_fields",
]


async def build_leto_client(_ad_request) -> EmbedHttpClient:
    """Создает EmbedHttpClient для Leto."""
    return EmbedHttpClient(
        base_url="https://ssp.rambler.ru/vapirs",
        base_params={
            "wl": "rambler",
            "pad_id": "579447018",
            "block_id": "579447026",
            "jparams": {  # Автоматически сериализуется в JSON + URL-encoding
                "puid8": "10",
                "puid25": "iptvportal",
            },
            "ip": _ad_request.device_ip,
            "external_ids": {  # Автоматически сериализуется в JSON + URL-encoding
                "user_id": f"ebe4c323-31c3-4db0-da00-{_ad_request.custom_params.get('macaddr', 'fe191380d281')}"
            },
        },
        base_headers={
            "User-Agent": _ad_request.user_agent,
            "X-Real-Ip": _ad_request.device_ip,
            "X-Forwarded-For": _ad_request.device_ip,
            "Accept": "application/xml, text/xml, */*",
        },
    )


async def build_global_client(_ad_request: dict) -> EmbedHttpClient:
    """Создает EmbedHttpClient для AdStream (Global интеграция)."""
    ip_list = PROVIDER_IPS["AT-HOME"]
    ip = secrets.choice(ip_list) if ip_list else "213.21.4.190"
    channel = _ad_request.get("ext", {}).get("channel_to")
    # media_id = getattr(channel, 'iptvorg_numeric_id', 0)  # Unused variable removed
    media_title = channel.get_display_name() if channel else ""
    media_tag = getattr(channel, "iptvorg_categories", "")
    device_serial = generate_uuid_from_multi_fields(
        "GLOBAL",
        _ad_request.get("device_macaddr", ""),
        _ad_request.get("user_agent", ""),
        _ad_request["ext"].get("domain", ""),
    )

    return EmbedHttpClient(
        base_url="https://g.adstrm.ru/vast3",
        base_params={
            "city": "Санкт-Петербург",
            "ab_uid": device_serial,
            "ad_place": _ad_request.get("placement_type", "switchroll"),
            "media_type": "stream",
            "media_title": media_title,
            "media_tag": media_tag,
            "city_code": 812,
        },
        base_headers={
            "User-Agent": _ad_request.get("user_agent") or "",
            "X-Serial-Number": device_serial,
            "X-Real-Ip": ip,
            "X-Forwarded-For": ip,
            "Accept": "application/xml, text/xml, */*",
        },
        encoding_config={
            # Кириллицу оставляем как есть, остальные параметры тоже не кодируем
            "city": False,  # Санкт-Петербург - сохраняем без кодирования
            "ab_uid": False,  # UUID не требует кодирования
            "ad_place": False,  # Простые значения
            "media_type": False,
            "media_title": False,  # Название канала может содержать Unicode
            "media_tag": False,
            "city_code": False,
        },
    )


async def build_global_context(_ad_request: dict) -> dict[str, Any]:
    """Собирает конфигурацию запроса для AdStream (Global интеграция).

    Deprecated: Используйте build_global_client() для получения EmbedHttpClient.
    """
    client = await build_global_client(_ad_request)
    return client.to_vast_config()


async def build_tiger_client(_ad_request: dict) -> EmbedHttpClient:
    """Создает EmbedHttpClient для AdStream (Tiger интеграция)."""
    channel = _ad_request.get("ext", {}).get("channel_to")
    # media_id = getattr(channel, 'iptvorg_numeric_id', 0)  # Unused variable removed
    media_title = channel.get_display_name() if channel else ""
    media_tag = getattr(channel, "iptvorg_categories", "")

    return EmbedHttpClient(
        base_url="https://t.adstrm.ru/vast3",
        base_params={
            "city_name": "Санкт-Петербург",
            "ab_uid": _ad_request.get("device_serial"),
            "ad_place": _ad_request.get("placement_type", "switchroll"),
            "media_type": "stream",
            "media_title": media_title,
            "media_tag": media_tag,
            "city_code": 812,
        },
        base_headers={
            "User-Agent": _ad_request.get("user_agent") or "",
            "X-Serial-Number": _ad_request.get("device_serial") or "",
            "X-Real-Ip": _ad_request.get("device_ip") or "",
            "X-Forwarded-For": _ad_request.get("device_ip") or "",
            "Accept": "application/xml, text/xml, */*",
        },
        encoding_config={
            # Аналогично global контексту
            "city_name": False,  # Санкт-Петербург - сохраняем без кодирования
            "ab_uid": False,
            "ad_place": False,
            "media_type": False,
            "media_title": False,  # Название канала может содержать Unicode
            "media_tag": False,
            "city_code": False,
        },
    )
