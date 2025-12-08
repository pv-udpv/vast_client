# GitHub Copilot Instructions - VAST Client

## Project Overview

This is a **VAST (Video Ad Serving Template) Client** package for handling video advertising in CTV (Connected TV) environments. It provides a modular, production-ready implementation for VAST ad lifecycle management including ad requests, XML parsing, event tracking, and playback management.

## Technology Stack

- **Language**: Python 3.10+
- **Key Dependencies**:
  - `httpx` - Async HTTP client
  - `lxml` - XML parsing
  - `structlog` - Structured logging
- **Dev Tools**: pytest, pytest-asyncio, black, mypy, ruff
- **Package Manager**: setuptools

## Project Structure

```
src/vast_client/
├── client.py              # Main VAST client facade
├── parser.py              # VAST XML parser
├── tracker.py             # Event tracking system
├── player.py              # Real-time ad player
├── headless_player.py     # Simulated playback player
├── base_player.py         # Base player interface
├── playback_session.py    # Session state management
├── config.py              # Configuration dataclasses
├── config_resolver.py     # Config resolution logic
├── context.py             # Dependency injection context
├── trackable.py           # Trackable protocol & implementation
├── capabilities.py        # Capability decorators (mixins)
├── mixins.py              # Additional mixins
├── time_provider.py       # Time abstraction (real/simulated)
├── player_factory.py      # Player factory functions
├── http.py & http_client.py # HTTP utilities
├── helpers.py             # Utility functions
├── types.py               # Type definitions
└── docs/                  # Documentation
```

## Architecture Patterns

### 1. **Protocol-Based Design**
- Use `Trackable` protocol for event tracking objects
- Supports duck typing and composition over inheritance
- Protocol methods: `send_with()`, `get_extra()`, `set_extra()`, `has_extra()`

### 2. **Capability Decorators (Mixins)**
Located in `capabilities.py`:
- `@with_macros` - URL macro substitution (`[CREATIVE_ID]`, `${TIMESTAMP}`)
- `@with_state` - Tracking state management (tracked/failed/pending)
- `@with_logging` - Structured logging integration
- `@with_event_filtering` - Event filtering with glob patterns
- `@with_http_send` - HTTP request sending

### 3. **Dependency Injection**
- Use `TrackingContext` for dependency injection
- Supports custom injections via `context.set()` and `context.get()`
- Common injections: logger, http_client, metrics_client, timeout, retry configs

### 4. **Time Abstraction**
- `TimeProvider` protocol for pluggable time sources
- `RealtimeTimeProvider` - Wall-clock time
- `SimulatedTimeProvider` - Virtual time with speed control
- Use `create_time_provider()` factory function

### 5. **Playback Modes**
- `PlaybackMode.REAL` - Real-time playback (wall-clock)
- `PlaybackMode.HEADLESS` - Simulated playback (testing/headless)
- `PlaybackMode.AUTO` - Auto-detect from settings

## Code Style Guidelines

### Python Standards
- **Python 3.10+** features (use type unions with `|`, not `Union`)
- **Type hints** required on all public functions/methods
- **Dataclasses** for configuration objects
- **Enums** for constants (inherit from `str, Enum`)
- **Async/await** for I/O operations

### Naming Conventions
- **Classes**: PascalCase (e.g., `VastClient`, `PlaybackSession`)
- **Functions/Methods**: snake_case (e.g., `parse_vast`, `track_event`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `MAX_RETRIES`)
- **Private members**: Leading underscore (e.g., `_internal_state`)

### Imports
```python
# Standard library
import asyncio
from typing import Any

# Third-party
import httpx
from lxml import etree

# Local (relative)
from ..events import VastEvents
from ..log_config import get_context_logger
from .config import VastClientConfig
```

## Key Patterns to Follow

### 1. Logging
Always use context-aware logging:
```python
from ..log_config import get_context_logger

class MyClass:
    def __init__(self):
        self.logger = get_context_logger("component_name")
    
    async def my_method(self):
        self.logger.info("event_type", key1="value1", key2="value2")
```

Use event constants from `VastEvents`:
```python
from ..events import VastEvents

self.logger.debug(VastEvents.PARSE_STARTED, xml_length=len(xml))
self.logger.error(VastEvents.TRACKING_FAILED, event=event_type)
```

### 2. Configuration
Use dataclasses with defaults:
```python
from dataclasses import dataclass, field

@dataclass
class MyConfig:
    timeout: float = 5.0
    max_retries: int = 3
    custom_fields: dict[str, Any] = field(default_factory=dict)
```

### 3. HTTP Requests
Use `EmbedHttpClient` for base URL/params/headers management:
```python
from routes.helpers import EmbedHttpClient

client = EmbedHttpClient(
    base_url="https://api.example.com",
    base_params={"version": "4.0"},
    base_headers={"User-Agent": "Device/1.0"}
)
```

### 4. Error Handling
- **Graceful degradation**: Track errors but don't fail playback
- **Retry logic**: Use exponential backoff for HTTP failures
- **XML parsing**: Enable `recover_on_error=True` for malformed XML
- **Logging**: Always log errors with structured context

### 5. Async Patterns
```python
# Good: Proper async/await
async def request_ad(self) -> dict[str, Any]:
    response = await self.http_client.get(url)
    return response.json()

# Good: Context manager support
async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.cleanup()
```

## Domain Concepts

### VAST Protocol
- **Ad Request**: HTTP GET to VAST endpoint with query params
- **VAST XML**: Response containing ad metadata, media files, tracking events
- **Tracking Events**: URLs fired at specific playback events (impression, start, quartiles, complete)
- **Macro Substitution**: Replace placeholders in tracking URLs (e.g., `[CREATIVE_ID]` → `creative_123`)

### Playback Session
- **Session ID**: Unique identifier for each playback
- **Status**: pending → running → completed/closed/error
- **Events**: Timestamped records (start, pause, resume, quartile, complete)
- **Quartiles**: 0%, 25%, 50%, 75%, 100% progress milestones

### Tracking State
- **Tracked**: Successfully sent
- **Failed**: Send failed (may retry)
- **Pending**: Not yet attempted
- Use `mark_tracked()`, `mark_failed()`, `should_retry()` methods

## Common Tasks

### Adding a New Configuration Field
1. Add to appropriate config dataclass in `config.py`
2. Update `ConfigResolver` if needed
3. Document in docstring with example
4. Add default value

### Adding a New Tracking Event Type
1. Add constant to `VastEvents` enum
2. Update parser if new XPath needed
3. Update tracker event mapping
4. Add logging calls where event occurs

### Adding a New Capability Decorator
1. Create decorator function in `capabilities.py`
2. Define methods to add to Trackable class
3. Document usage with example
4. Update `__all__` export

### Testing Async Code
```python
import pytest

@pytest.mark.asyncio
async def test_request_ad():
    client = VastClient("https://api.example.com/vast")
    ad_data = await client.request_ad()
    assert "ad_title" in ad_data
```

## Dependencies & Imports

### External Dependencies
- Prefer `httpx` over `requests` (async support)
- Use `lxml` for XML parsing (performance)
- Use `structlog` for logging (structured output)

### Internal Dependencies
- `..events` - Event type constants
- `..log_config` - Context-aware logging
- `..http_client_manager` - HTTP client pooling
- `..config` - Global settings
- `routes.helpers` - HTTP utilities

## DO's and DON'Ts

### DO
✅ Use async/await for all I/O operations
✅ Add type hints to all public APIs
✅ Use dataclasses for configuration
✅ Log with structured context (key=value pairs)
✅ Handle errors gracefully (especially for tracking)
✅ Support provider-specific overrides via config
✅ Write docstrings for public classes/methods
✅ Use protocol-based design for extensibility

### DON'T
❌ Block on synchronous I/O in async functions
❌ Use bare `except:` - catch specific exceptions
❌ Hard-code URLs, timeouts, or provider-specific values
❌ Fail playback due to tracking errors
❌ Mix wall-clock time with simulated time
❌ Modify global state without context managers
❌ Use `print()` - always use logger
❌ Import from parent package siblings (use relative imports)

## Testing Guidelines

- Use `pytest` with `pytest-asyncio` for async tests
- Mock HTTP requests with `httpx.AsyncClient` mocks
- Test both success and error paths
- Test macro substitution with various formats
- Test playback with simulated time provider
- Test configuration overrides and resolution

## Performance Considerations

- **Reuse HTTP clients**: Don't create new client per request
- **Connection pooling**: Use `httpx.AsyncClient` with limits
- **Parallel tracking**: Consider `parallel_tracking=True` for multiple events
- **XML parsing**: Use `recover_on_error` for malformed XML
- **Memory**: Clean up sessions after playback completes

## Related Documentation

- Main package docs: `src/vast_client/docs/README.md`
- VAST specification: https://www.iab.com/guidelines/vast/
- Playback integration docs: `src/vast_client/docs/playback_integration/`
