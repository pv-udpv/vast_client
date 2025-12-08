"""HTTP client manager for connection pooling and lifecycle management."""

import httpx
from typing import Optional


# Global HTTP client instances
_main_http_client: Optional[httpx.AsyncClient] = None
_tracking_http_client: Optional[httpx.AsyncClient] = None


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
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._main_client
    
    def get_tracking_client(self) -> httpx.AsyncClient:
        """Get or create tracking HTTP client."""
        if self._tracking_client is None:
            self._tracking_client = httpx.AsyncClient(
                timeout=5.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
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
    if '_manager' not in globals():
        globals()['_manager'] = HttpClientManager()
    return globals()['_manager']


def get_main_http_client() -> httpx.AsyncClient:
    """Get main HTTP client for VAST requests."""
    global _main_http_client
    if _main_http_client is None:
        _main_http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    return _main_http_client


def get_tracking_http_client() -> httpx.AsyncClient:
    """Get tracking HTTP client for tracking pixel requests."""
    global _tracking_http_client
    if _tracking_http_client is None:
        _tracking_http_client = httpx.AsyncClient(
            timeout=5.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
    return _tracking_http_client


def record_main_client_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None
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
    error: Optional[str] = None
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
