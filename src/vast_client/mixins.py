"""Mixins for Trackable objects providing additional functionality with robust fallbacks."""

import fnmatch
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .trackable import TrackableEvent
else:
    import importlib
    trackable_module = importlib.import_module("ctv_middleware.vast_client.trackable")
    TrackableEvent = trackable_module.TrackableEvent

# ---------------------------------------------------------------------------
# Fallback helper for objects that might not define extra storage utilities
# ---------------------------------------------------------------------------

def _ensure_extra_api(obj: Any) -> None:
    """Ensure the object has has_extra/get_extra/set_extra API."""
    if not hasattr(obj, "_extras"):
        obj._extras = {}

    if not hasattr(obj, "has_extra"):
        def has_extra(key: str) -> bool:
            return key in obj._extras
        obj.has_extra = has_extra  # type: ignore[attr-defined]

    if not hasattr(obj, "get_extra"):
        def get_extra(key: str, default: Any = None) -> Any:
            return obj._extras.get(key, default)
        obj.get_extra = get_extra  # type: ignore[attr-defined]

    if not hasattr(obj, "set_extra"):
        def set_extra(key: str, value: Any) -> None:
            obj._extras[key] = value
        obj.set_extra = set_extra  # type: ignore[attr-defined]

def _safe_list(val: Any) -> List[Any]:
    return val if isinstance(val, list) else []

# ---------------------------------------------------------------------------
# Macro processing
# ---------------------------------------------------------------------------

class MacroMixin:
    """Mixin providing macro substitution functionality with caching."""

    def apply_macros(self, macros: Dict[str, str], formats: List[str]) -> Any:
        _ensure_extra_api(self)
        value = getattr(self, "value", None)

        if not isinstance(value, (list, str)):
            return value

        cache_key = hash(frozenset(macros.items()))
        if self.has_extra("_macro_cache_key") and self.get_extra("_macro_cache_key") == cache_key:
            return self.get_extra("_macro_cache_value")

        if isinstance(value, list):
            result = [self._apply_to_str(url, macros, formats) for url in value]
        else:
            result = self._apply_to_str(value, macros, formats)

        self.set_extra("_macro_cache_value", result)
        self.set_extra("_macro_cache_key", cache_key)
        return result

    def _apply_to_str(self, text: str, macros: Dict[str, str], formats: List[str]) -> str:
        for macro_key, macro_value in macros.items():
            for fmt in formats:
                pattern = fmt.format(macro=macro_key)
                text = text.replace(pattern, str(macro_value))
        return text

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

class StateMixin:
    """Mixin providing state management for tracking operations."""

    def is_tracked(self) -> bool:
        _ensure_extra_api(self)
        return bool(self.get_extra("tracked", False))

    def mark_tracked(self, response_time: float | None = None) -> None:
        _ensure_extra_api(self)
        attempt_count = self.get_extra("attempt_count", 0)
        if attempt_count is None:
            attempt_count = 0
        self.set_extra("tracked", True)
        self.set_extra("tracked_at", datetime.now())
        self.set_extra("attempt_count", attempt_count + 1)

        if response_time is not None:
            self.set_extra("last_response_time", response_time)
            response_times = _safe_list(self.get_extra("response_times", []))
            response_times.append(response_time)
            self.set_extra("response_times", response_times)

    def mark_failed(self, error: str) -> None:
        _ensure_extra_api(self)
        attempt_count = self.get_extra("attempt_count", 0)
        if attempt_count is None:
            attempt_count = 0
        attempt_count += 1
        self.set_extra("attempt_count", attempt_count)
        self.set_extra("last_error", error)
        self.set_extra("last_error_at", datetime.now())

        error_history = _safe_list(self.get_extra("error_history", []))
        error_history.append({"error": error, "timestamp": datetime.now(), "attempt": attempt_count})
        self.set_extra("error_history", error_history)

    def should_retry(self, max_retries: int = 3) -> bool:
        if self.is_tracked():
            return False
        _ensure_extra_api(self)
        attempt_count = self.get_extra("attempt_count", 0)
        if attempt_count is None:
            attempt_count = 0
        return attempt_count < max_retries

    def get_avg_response_time(self) -> float | None:
        _ensure_extra_api(self)
        response_times = _safe_list(self.get_extra("response_times", []))
        if not response_times:
            return None
        return sum(response_times) / len(response_times)

    def get_last_error(self) -> Any:
        _ensure_extra_api(self)
        return self.get_extra("last_error")

    def reset_state(self) -> None:
        _ensure_extra_api(self)
        self.set_extra("tracked", False)
        self.set_extra("tracked_at", None)
        self.set_extra("attempt_count", 0)
        self.set_extra("last_error", None)
        self.set_extra("last_error_at", None)
        self.set_extra("response_times", [])
        self.set_extra("error_history", [])

# ---------------------------------------------------------------------------
# Event filtering
# ---------------------------------------------------------------------------

class EventFilterMixin:
    """Mixin providing glob-based event filtering capability."""

    def set_event_filters(
        self,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> None:
        if include is not None:
            self._event_include_patterns = include
        if exclude is not None:
            self._event_exclude_patterns = exclude

    def should_log_event(self, event_name: str) -> bool:
        include_patterns = getattr(self, "_event_include_patterns", ["*"])
        exclude_patterns = getattr(self, "_event_exclude_patterns", [])
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(event_name, pattern):
                return False
        for pattern in include_patterns:
            if fnmatch.fnmatch(event_name, pattern):
                return True
        return False

    def filter_events(self, events: List[str]) -> List[str]:
        return [e for e in events if self.should_log_event(e)]

    def get_event_filter_stats(self) -> dict[str, Any]:
        include = getattr(self, "_event_include_patterns", ["*"])
        exclude = getattr(self, "_event_exclude_patterns", [])
        return {
            "include_patterns": include,
            "exclude_patterns": exclude,
            "filter_active": include != ["*"] or bool(exclude),
        }

# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------

class LoggingMixin(EventFilterMixin):
    """Mixin providing logging integration + event filtering."""

    def log_event(self, logger, event_name: str, level: str = "info", **kwargs) -> None:
        if not self.should_log_event(event_name):
            return
        log_method = getattr(logger, level, logger.info)
        log_method(event_name, **kwargs)

    def to_log_dict(self) -> dict[str, Any]:
        to_dict_fn = getattr(self, "to_dict", None)
        base: dict[str, Any] = {}
        if callable(to_dict_fn):
            maybe = to_dict_fn()
            if isinstance(maybe, dict):
                base = maybe
        stats = self.get_event_filter_stats()
        if stats["filter_active"]:
            base["_event_filters"] = stats
        return base

    def log_state(self, logger, level: str = "info") -> None:
        log_method = getattr(logger, level, logger.info)
        log_method("Trackable state", **self.to_log_dict())

# ---------------------------------------------------------------------------
# Composite convenience class
# ---------------------------------------------------------------------------

class TrackableEventWithMacros(TrackableEvent, MacroMixin, StateMixin, LoggingMixin):
    """Convenience class combining TrackableEvent with all mixins."""

    def __init__(self, key: str, value: Any, **kwargs):
        super().__init__(key, value)
        _ensure_extra_api(self)
        self._event_include_patterns = ["*"]
        self._event_exclude_patterns = []
        for attr_name, attr_value in kwargs.items():
            self.set_extra(attr_name, attr_value)

    def __repr__(self) -> str:
        base_repr = super().__repr__()
        capabilities: List[str] = []
        if hasattr(self, "apply_macros"):
            capabilities.append("macros")
        if hasattr(self, "is_tracked"):
            capabilities.append("state")
        if hasattr(self, "to_log_dict"):
            capabilities.append("logging")
        if capabilities:
            return f"{base_repr[:-1]}, mixins=[{', '.join(capabilities)}])"
        return base_repr

__all__ = [
    "MacroMixin",
    "StateMixin",
    "EventFilterMixin",
    "LoggingMixin",
    "TrackableEventWithMacros",
]
