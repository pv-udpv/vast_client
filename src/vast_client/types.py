"""Type definitions for the VAST client package."""

from typing import Any, TypedDict


class VastClientConfig(TypedDict, total=False):
    """Configuration for VAST client initialization."""

    client_base_url: str
    client_url: str | None
    client_params: dict[str, Any]
    client_headers: dict[str, str]


__all__ = ["VastClientConfig"]
