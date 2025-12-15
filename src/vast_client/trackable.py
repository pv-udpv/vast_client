"""Trackable protocol and implementations for VAST events."""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Trackable(Protocol):
    """Protocol for trackable items with key-value storage and extra attributes."""

    key: str  # Primary identifier (event_type, url, etc)
    value: Any  # Primary value (list of URLs, single URL, etc)

    def get_extra(self, name: str, default: Any = None) -> Any:
        """Get extra attribute by name."""
        ...

    def set_extra(self, name: str, value: Any) -> None:
        """Set extra attribute by name."""
        ...

    def has_extra(self, name: str) -> bool:
        """Check if extra attribute exists."""
        ...

    async def send_with(self, client, macros: dict[str, str] | None = None, **context) -> bool:
        """Send tracking request using provided client with optional context injection.

        Args:
            client: HTTP client (httpx.AsyncClient)
            macros: Optional macro dictionary for URL substitution
            **context: Additional context for request (headers, params, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        ...


@dataclass
class TrackableEvent:
    """Basic trackable event implementation with dynamic extra attributes."""

    key: str
    value: Any

    # Storage for extra attributes
    _extras: dict[str, Any] = field(default_factory=dict, repr=False)

    def get_extra(self, name: str, default: Any = None) -> Any:
        """Get extra attribute with default value."""
        return self._extras.get(name, default)

    def set_extra(self, name: str, value: Any) -> None:
        """Set extra attribute."""
        self._extras[name] = value

    def has_extra(self, name: str) -> bool:
        """Check if extra attribute exists."""
        return name in self._extras

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary for logging/serialization."""
        return {
            'key': self.key,
            'value': self.value,
            **self._extras
        }

    def __getattr__(self, name: str) -> Any:
        """Allow dot notation access to extra attributes."""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
        return self.get_extra(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow dot notation assignment to extra attributes."""
        if name in ('key', 'value', '_extras'):
            object.__setattr__(self, name, value)
        else:
            if not hasattr(self, '_extras'):
                object.__setattr__(self, '_extras', {})
            self._extras[name] = value

    async def send_with(self, client, macros: dict[str, str] | None = None, **context) -> bool:
        """Default implementation - does nothing and returns False.

        Subclasses should override this method or use capability decorators.
        """
        return False

    def __repr__(self) -> str:
        """Custom repr showing key and main extras."""
        extras_repr = ', '.join(f"{k}={v!r}" for k, v in self._extras.items() if not k.startswith('_'))
        if extras_repr:
            return f"{type(self).__name__}(key={self.key!r}, value={self.value!r}, {extras_repr})"
        return f"{type(self).__name__}(key={self.key!r}, value={self.value!r})"


@dataclass
class TrackableCollection:
    """Collection of trackable items with lazy loading."""

    _items: dict[str, Trackable] = field(default_factory=dict, repr=False)

    def add(self, item: Trackable) -> None:
        """Add trackable item to collection."""
        self._items[item.key] = item

    def get(self, key: str) -> Trackable | None:
        """Get trackable item by key."""
        return self._items.get(key)

    def get_all(self) -> list[Trackable]:
        """Get all trackable items."""
        return list(self._items.values())

    def get_by_predicate(self, predicate: callable) -> list[Trackable]:
        """Get items matching predicate."""
        return [item for item in self._items.values() if predicate(item)]

    def __getitem__(self, key: str) -> Trackable:
        """Get item by key with indexing syntax."""
        if key not in self._items:
            raise KeyError(f"Trackable item '{key}' not found")
        return self._items[key]

    def __setitem__(self, key: str, item: Trackable) -> None:
        """Set item by key."""
        if item.key != key:
            raise ValueError(f"Item key '{item.key}' does not match provided key '{key}'")
        self._items[key] = item

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._items

    def __len__(self) -> int:
        """Get number of items."""
        return len(self._items)

    def __iter__(self):
        """Iterate over items."""
        return iter(self._items.values())


__all__ = ["Trackable", "TrackableEvent", "TrackableCollection"]
