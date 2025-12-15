"""
VAST HTTP Client Management

Provides specialized HTTP client management for VAST operations,
integrating with the global HTTP client manager.
"""

import asyncio
import time
from typing import Any

import httpx

from .config import get_vast_http_config, get_vast_settings, get_vast_tracking_config
from .http_client_manager import (
    get_http_client_manager,
    get_main_http_client,
    get_tracking_http_client,
    record_main_client_request,
    record_tracking_client_request,
)
from .log_config import get_context_logger


logger = get_context_logger(__name__)


class VastHttpClient:
    """
    VAST-specific HTTP client wrapper that provides specialized functionality
    for VAST requests while leveraging the global HTTP client manager.
    """

    def __init__(self):
        """Initialize VAST HTTP client."""
        self.settings = get_vast_settings()
        self.http_config = get_vast_http_config()
        self.tracking_config = get_vast_tracking_config()
        self._client_manager = get_http_client_manager()

    async def request_vast_ad(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """
        Make a VAST ad request.

        Args:
            url: VAST request URL
            headers: Additional headers
            timeout: Request timeout override

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        start_time = time.time()
        client = await get_main_http_client()

        request_timeout = timeout or self.settings.default_timeout
        request_headers = headers or {}

        try:
            logger.debug(
                "Making VAST ad request",
                url=url,
                headers=list(request_headers.keys()),
                timeout=request_timeout,
            )

            response = await client.get(
                url,
                headers=request_headers,
                timeout=request_timeout,
                follow_redirects=True,
            )

            response_time = time.time() - start_time

            # Record successful request
            record_main_client_request(
                success=True,
                response_time=response_time,
                info_type=f"vast_ad_{response.status_code}",
            )

            logger.info(
                "VAST ad request completed",
                url=url,
                status_code=response.status_code,
                response_time=response_time,
                content_length=len(response.content),
            )

            return response

        except httpx.TimeoutException:
            response_time = time.time() - start_time
            record_main_client_request(
                success=False,
                response_time=response_time,
                error_type="timeout",
            )

            logger.warning(
                "VAST ad request timeout",
                url=url,
                timeout=request_timeout,
                response_time=response_time,
            )
            raise

        except httpx.HTTPError as e:
            response_time = time.time() - start_time
            record_main_client_request(
                success=False,
                response_time=response_time,
                error_type=type(e).__name__,
            )

            logger.error(
                "VAST ad request failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                response_time=response_time,
            )
            raise

        except Exception as e:
            response_time = time.time() - start_time
            record_main_client_request(
                success=False,
                response_time=response_time,
                error_type="exception",
            )

            # Record exception with full context
            self._client_manager.record_exception(
                exception=e,
                client_type="main",
                context="VAST ad request",
                extra_data={
                    "url": url,
                    "headers": request_headers,
                    "timeout": request_timeout,
                },
            )
            raise

    async def send_tracking_event(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bool:
        """
        Send a VAST tracking event.

        Args:
            url: Tracking URL
            headers: Additional headers
            timeout: Request timeout override

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        client = await get_tracking_http_client()

        request_timeout = timeout or self.settings.tracking_timeout
        request_headers = headers or {}

        try:
            logger.debug(
                "Sending VAST tracking event",
                url=url,
                timeout=request_timeout,
            )

            response = await client.get(
                url,
                headers=request_headers,
                timeout=request_timeout,
                follow_redirects=True,
            )

            response_time = time.time() - start_time

            # Record tracking request
            record_tracking_client_request(
                success=response.status_code < 400,
                response_time=response_time,
                info_type=f"tracking_{response.status_code}",
            )

            logger.debug(
                "VAST tracking event sent",
                url=url,
                status_code=response.status_code,
                response_time=response_time,
            )

            return response.status_code < 400

        except httpx.TimeoutException:
            response_time = time.time() - start_time
            record_tracking_client_request(
                success=False,
                response_time=response_time,
                error_type="timeout",
            )

            logger.warning(
                "VAST tracking event timeout",
                url=url,
                timeout=request_timeout,
            )
            return False

        except httpx.HTTPError as e:
            response_time = time.time() - start_time
            record_tracking_client_request(
                success=False,
                response_time=response_time,
                error_type=type(e).__name__,
            )

            logger.warning(
                "VAST tracking event failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

        except Exception as e:
            response_time = time.time() - start_time
            record_tracking_client_request(
                success=False,
                response_time=response_time,
                error_type="exception",
            )

            # Record exception for tracking
            self._client_manager.record_exception(
                exception=e,
                client_type="tracking",
                context="VAST tracking event",
                extra_data={
                    "url": url,
                    "headers": request_headers,
                    "timeout": request_timeout,
                },
            )

            logger.warning(
                "VAST tracking event exception",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def request_vast_ad_with_retry(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        """
        Make a VAST ad request with retry logic.

        Args:
            url: VAST request URL
            headers: Additional headers
            timeout: Request timeout override
            max_retries: Maximum retry attempts override

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: After all retries are exhausted
        """
        retry_attempts = max_retries or self.settings.retry_attempts
        last_exception = None

        for attempt in range(retry_attempts + 1):
            try:
                return await self.request_vast_ad(url, headers, timeout)

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < retry_attempts:
                    await asyncio.sleep(self.settings.retry_delay * (attempt + 1))
                    logger.debug(
                        "Retrying VAST ad request after timeout",
                        url=url,
                        attempt=attempt + 1,
                        max_retries=retry_attempts,
                    )
                continue

            except httpx.HTTPError as e:
                # Don't retry client errors (4xx)
                if (
                    hasattr(e, "response")
                    and e.response  # type: ignore
                    and 400 <= e.response.status_code < 500  # type: ignore
                ):
                    raise

                last_exception = e
                if attempt < retry_attempts:
                    await asyncio.sleep(self.settings.retry_delay * (attempt + 1))
                    logger.debug(
                        "Retrying VAST ad request after HTTP error",
                        url=url,
                        attempt=attempt + 1,
                        max_retries=retry_attempts,
                        error=str(e),
                    )
                continue

        # If we get here, all retries were exhausted
        logger.error(
            "VAST ad request failed after all retries",
            url=url,
            attempts=retry_attempts + 1,
            last_error=str(last_exception),
        )

        if last_exception:
            raise last_exception
        else:
            raise httpx.RequestError("All retry attempts exhausted")

    async def get_client_stats(self) -> dict[str, Any]:
        """Get VAST client statistics."""
        return await self._client_manager.get_client_stats()


# Global VAST HTTP client instance
_vast_http_client: VastHttpClient | None = None


async def get_vast_http_client() -> VastHttpClient:
    """Get the global VAST HTTP client instance."""
    global _vast_http_client
    if _vast_http_client is None:
        _vast_http_client = VastHttpClient()
    return _vast_http_client


__all__ = [
    "VastHttpClient",
    "get_vast_http_client",
]
