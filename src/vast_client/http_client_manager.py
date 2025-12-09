"""HTTP client manager for connection pooling and lifecycle management."""

from typing import Any, Optional

import httpx

from .settings import get_settings


# Global HTTP client instances (keyed by config tuple)
_main_http_clients: dict[tuple[Any, ...], httpx.AsyncClient] = {}
_tracking_http_clients: dict[tuple[Any, ...], httpx.AsyncClient] = {}


class HttpClientManager:
    """Manages HTTP client lifecycle and pooling."""

    def __init__(self):
        """Initialize HTTP client manager."""
        self._main_client: Optional[httpx.AsyncClient] = None
        self._tracking_client: Optional[httpx.AsyncClient] = None

    def get_main_client(self) -> httpx.AsyncClient:
        """Get or create main HTTP client."""
        if self._main_client is None:
            self._main_client = httpx.AsyncClient(
                timeout=30.0, limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._main_client

    def get_tracking_client(self) -> httpx.AsyncClient:
        """Get or create tracking HTTP client."""
        if self._tracking_client is None:
            self._tracking_client = httpx.AsyncClient(
                timeout=5.0, limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
            )
        return self._tracking_client

    async def close(self):
        """Close all HTTP clients."""
        if self._main_client:
            await self._main_client.aclose()
            self._main_client = None
        if self._tracking_client:
            await self._tracking_client.aclose()
            self._tracking_client = None


def get_http_client_manager() -> HttpClientManager:
    """Get global HTTP client manager instance."""
    global _manager
    if "_manager" not in globals():
        globals()["_manager"] = HttpClientManager()
    return globals()["_manager"]


def _load_http_config(kind: str) -> dict[str, Any]:
    """Load HTTP client configuration for a given client kind ("main" or "tracking")."""

    settings = get_settings()
    http_cfg = getattr(settings, "http", {}) or {}

    # Allow nested config per kind, otherwise fall back to flat keys
    kind_cfg = http_cfg.get(kind, {}) if isinstance(http_cfg, dict) else {}

    def _get(key: str, default: Any) -> Any:
        if key in kind_cfg:
            return kind_cfg[key]
        if isinstance(http_cfg, dict) and key in http_cfg:
            return http_cfg[key]
        return default

    return {
        "timeout": _get("timeout", 30.0 if kind == "main" else 5.0),
        "max_connections": _get("max_connections", 20 if kind == "main" else 50),
        "max_keepalive_connections": _get(
            "max_keepalive_connections", 10 if kind == "main" else 20
        ),
        "keepalive_expiry": _get("keepalive_expiry", 5.0),
        # Default to verifying SSL for main client, but tracking defaults to False
        # so we can continue firing pixels even if the endpoint has a bad cert.
        "verify": _get("verify_ssl", True if kind == "main" else False),
    }


def _client_cache_key(kind: str, cfg: dict[str, Any]) -> tuple[Any, ...]:
    """Build a cache key tuple from HTTP configuration."""

    return (
        kind,
        cfg.get("verify"),
        cfg.get("timeout"),
        cfg.get("max_connections"),
        cfg.get("max_keepalive_connections"),
        cfg.get("keepalive_expiry"),
    )


def get_main_http_client(
    *,
    ssl_verify: bool | str | None = None,
    timeout: float | None = None,
    max_connections: int | None = None,
    max_keepalive_connections: int | None = None,
    keepalive_expiry: float | None = None,
) -> httpx.AsyncClient:
    """Get main HTTP client for VAST requests using configurable settings."""

    global _main_http_clients

    cfg = _load_http_config("main")
    if ssl_verify is not None:
        cfg["verify"] = ssl_verify
    if timeout is not None:
        cfg["timeout"] = timeout
    if max_connections is not None:
        cfg["max_connections"] = max_connections
    if max_keepalive_connections is not None:
        cfg["max_keepalive_connections"] = max_keepalive_connections
    if keepalive_expiry is not None:
        cfg["keepalive_expiry"] = keepalive_expiry

    key = _client_cache_key("main", cfg)
    if key not in _main_http_clients:
        _main_http_clients[key] = httpx.AsyncClient(
            timeout=cfg["timeout"],
            limits=httpx.Limits(
                max_keepalive_connections=cfg["max_keepalive_connections"],
                max_connections=cfg["max_connections"],
                keepalive_expiry=cfg["keepalive_expiry"],
            ),
            verify=cfg["verify"],
        )
    return _main_http_clients[key]


def get_tracking_http_client(
    *,
    ssl_verify: bool | str | None = None,
    timeout: float | None = None,
    max_connections: int | None = None,
    max_keepalive_connections: int | None = None,
    keepalive_expiry: float | None = None,
) -> httpx.AsyncClient:
    """Get tracking HTTP client for tracking pixel requests using configurable settings."""

    global _tracking_http_clients

    cfg = _load_http_config("tracking")
    if ssl_verify is not None:
        cfg["verify"] = ssl_verify
    if timeout is not None:
        cfg["timeout"] = timeout
    if max_connections is not None:
        cfg["max_connections"] = max_connections
    if max_keepalive_connections is not None:
        cfg["max_keepalive_connections"] = max_keepalive_connections
    if keepalive_expiry is not None:
        cfg["keepalive_expiry"] = keepalive_expiry

    key = _client_cache_key("tracking", cfg)
    if key not in _tracking_http_clients:
        _tracking_http_clients[key] = httpx.AsyncClient(
            timeout=cfg["timeout"],
            limits=httpx.Limits(
                max_keepalive_connections=cfg["max_keepalive_connections"],
                max_connections=cfg["max_connections"],
                keepalive_expiry=cfg["keepalive_expiry"],
            ),
            verify=cfg["verify"],
        )
    return _tracking_http_clients[key]


def record_main_client_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Record metrics for main client request.

    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        duration: Request duration in seconds
        error: Error message if failed
    """
    pass  # Stub for now


def record_tracking_client_request(
    url: str,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Record metrics for tracking client request.

    Args:
        url: Request URL
        status_code: Response status code
        duration: Request duration in seconds
        error: Error message if failed
    """
    pass  # Stub for now


__all__ = [
    "HttpClientManager",
    "get_http_client_manager",
    "get_main_http_client",
    "get_tracking_http_client",
    "record_main_client_request",
    "record_tracking_client_request",
]
