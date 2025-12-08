"""Logging configuration and utilities."""

import logging
import structlog
from typing import Any


def get_context_logger(name: str) -> structlog.BoundLogger:
    """Get a context-aware logger.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class AdRequestContext:
    """Context manager for ad request logging context."""
    
    def __init__(self, **context: Any):
        """Initialize with context variables.
        
        Args:
            **context: Context key-value pairs
        """
        self.context = context
        self._previous_context = {}
    
    def __enter__(self):
        """Enter context."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def update_playback_progress(**kwargs: Any) -> None:
    """Update playback progress in logging context.
    
    Args:
        **kwargs: Progress metrics to update
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def set_playback_context(**kwargs: Any) -> None:
    """Set playback context in logging.
    
    Args:
        **kwargs: Context key-value pairs
    """
    structlog.contextvars.bind_contextvars(**kwargs)


__all__ = [
    "get_context_logger",
    "AdRequestContext",
    "update_playback_progress",
    "set_playback_context",
]
