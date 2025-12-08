# VAST Client Package - Architecture

## System Architecture Overview

The VAST Client package implements a modular, layered architecture for handling VAST protocol operations in CTV advertising. It follows separation of concerns, dependency injection, and capability-based composition patterns.

```
┌────────────────────────────────────────────────────────────────┐
│                    VAST Client Package                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │          Public API & Facade Layer                      │ │
│  │  (VastClient, VastParser, VastTracker, VastPlayer)     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │         Configuration & Context Management             │ │
│  │  (Config, TrackingContext, ContextProvider)           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │        Core Protocol Layer                             │ │
│  │  (Trackable, TrackableEvent, TrackableCollection)     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │      Capability System                                 │ │
│  │  (Decorators, Mixins, HTTP Send, Macros, State)       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │       HTTP & Networking Layer                          │ │
│  │  (EmbedHttpClient, HTTP Client Manager)               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
          External HTTP   Logging   Monitoring
          Clients       System     System
```

## Layer Descriptions

### 1. Public API & Facade Layer

**Components:** `VastClient`, `VastParser`, `VastTracker`, `VastPlayer`

**Purpose:** Provides high-level interfaces for consumers. Hides implementation complexity.

**Responsibilities:**
- Orchestrate sub-components
- Manage component lifecycle
- Handle high-level error cases
- Provide convenient initialization methods

**Design Pattern:** Facade with multiple initialization paths (Factory pattern)

```python
# Multiple entry points for different use cases
VastClient(url_string)           # Simple string URL
VastClient(config_dict)          # Full config
VastClient.from_embed(...)       # From HTTP client
VastClient.from_config(...)      # From config object
```

### 2. Configuration & Context Management Layer

**Components:** `VastParserConfig`, `VastTrackerConfig`, `TrackingContext`, `ContextProvider`

**Purpose:** Centralized configuration and dependency injection.

**Responsibilities:**
- Define configuration defaults
- Manage context lifecycle
- Provide dependency injection
- Support provider-specific customization

**Design Pattern:** Configuration objects (TypedDict), Dependency Injection (singleton pattern)

**Key Features:**
- **VastParserConfig:** XPath selectors, encoding, error recovery
- **VastTrackerConfig:** Timeouts, retries, macro formats, context injection
- **TrackingContext:** Centralized dependency container
- **ContextProvider:** Global context singleton

### 3. Core Protocol Layer

**Components:** `Trackable`, `TrackableEvent`, `TrackableCollection`

**Purpose:** Define interfaces for trackable items with flexible composition.

**Responsibilities:**
- Define trackable protocol
- Provide base implementations
- Support extensibility
- Enable protocol-based composition

**Design Pattern:** Protocol-Oriented Design with runtime checking

```python
@runtime_checkable
class Trackable(Protocol):
    key: str
    value: Any
    
    def get_extra(name: str, default: Any = None) -> Any
    def set_extra(name: str, value: Any) -> None
    def has_extra(name: str) -> bool
    
    async def send_with(client, macros: dict | None = None, **context) -> bool
```

**Key Features:**
- **Dynamic extra attributes:** Store arbitrary data
- **Type safety:** Runtime protocol checking
- **Extensibility:** Custom implementations via protocol conformance
- **Serialization:** `to_dict()` method for logging

### 4. Capability System

**Components:** Capability decorators (`@with_macros`, `@with_state`, `@with_logging`, etc.), Mixins (`MacroMixin`, `StateMixin`, etc.)

**Purpose:** Enable flexible, composable functionality without inheritance hierarchies.

**Responsibilities:**
- Provide composable behavior
- Support capability detection
- Enable runtime composition
- Maintain backward compatibility

**Design Pattern:** Mixin-based composition with capability markers

**Available Capabilities:**

| Capability | Mixin | Provides |
|-----------|-------|----------|
| `macros` | MacroMixin | Macro substitution in URLs |
| `state` | StateMixin | Tracking state management |
| `logging` | LoggingMixin | Logging serialization |
| `event_filtering` | EventFilterMixin | Event inclusion/exclusion filters |
| `http_send` | (decorator) | HTTP request sending |

**Composition Example:**

```python
@with_macros
@with_state
@with_logging
@with_http_send
class FullyFeaturedTracker(TrackableEvent):
    pass
```

### 5. HTTP & Networking Layer

**Components:** `EmbedHttpClient`, HTTP client manager, connection pooling

**Purpose:** Manage HTTP communication with embedded configuration.

**Responsibilities:**
- Build URLs with base configuration
- Manage headers (merging, enrichment)
- Handle encoding/serialization
- Support async operations
- Manage connection pooling

**Design Pattern:** Builder pattern for URL construction, Decorator pattern for header merging

**Key Features:**
- **Embedded configuration:** Base URL, parameters, headers all in one object
- **URL building:** Preserves Unicode, handles special characters
- **Header merging:** Combine base and request-specific headers
- **Encoding configuration:** Control URL encoding behavior

## Data Flow Diagrams

### VAST Request Flow

```
Client
  │
  ├─ VastClient(url_or_config)
  │    │
  │    ├─ _parse_config()
  │    │    │
  │    │    └─ Initialize from URL/Config/EmbedHttpClient
  │    │
  │    └─ Initialize Parser, Tracker, Player
  │
  └─ request_ad()
       │
       ├─ Build request using EmbedHttpClient
       │
       ├─ Send HTTP request
       │
       ├─ Receive XML response
       │
       ├─ VastParser.parse_vast()
       │    │
       │    ├─ lxml parsing with configurable recovery
       │    │
       │    ├─ XPath extraction
       │    │
       │    └─ Return structured data
       │
       └─ Return ad_data to client
```

### Tracking Flow

```
VastTracker
  │
  ├─ track_event(event_type, macros={}, params={})
  │    │
  │    ├─ Get event URLs from registry
  │    │
  │    ├─ For each URL:
  │    │    │
  │    │    ├─ Apply macros (if provided)
  │    │    │
  │    │    ├─ Build final request
  │    │    │    │
  │    │    │    ├─ Apply macros with formats: ["[{macro}]", "${{{macro}}}"]
       │    │    │
       │    │    ├─ Add context (headers, params)
       │    │    │
       │    │    └─ Check state (retry if needed)
       │    │
       │    ├─ Send via HTTP client
       │    │    │
       │    │    ├─ Retry on failure (exponential backoff)
       │    │    │
       │    │    └─ Record response time
       │    │
       │    └─ Update state (tracked/failed)
       │
       └─ Return results
```

### Playback Flow with Auto-Tracking

```
VastPlayer
  │
  ├─ play()
  │    │
  │    ├─ Track "impression" event
  │    │
  │    ├─ Track "start" event
  │    │
  │    ├─ Track "creativeView" event
  │    │
  │    └─ For each second of playback:
  │         │
  │         ├─ Sleep 1 second
  │         │
  │         ├─ _track_progress(current_time)
  │         │    │
  │         │    ├─ Calculate quartile (0%, 25%, 50%, 75%, 100%)
  │         │    │
  │         │    ├─ Track quartile event if new quartile reached
  │         │    │    │
  │         │    │    ├─ Track "start" (0%)
  │         │    │    ├─ Track "firstQuartile" (25%)
  │         │    │    ├─ Track "midpoint" (50%)
  │         │    │    ├─ Track "thirdQuartile" (75%)
  │         │    │    └─ Track "complete" (100%)
  │         │    │
  │         │    └─ Update playback context
  │         │
  │         └─ Handle interruptions
  │
  └─ Return player stats
```

## Component Interactions

### VastClient → Other Components

```
VastClient
├─ Aggregates VastParser
│  └─ Uses for XML parsing
│
├─ Aggregates VastTracker
│  ├─ Passes configuration
│  ├─ Passes HTTP client
│  └─ Passes ad_request context
│
├─ Aggregates VastPlayer
│  └─ References for playback operations
│
├─ Uses EmbedHttpClient
│  └─ For HTTP communication
│
└─ Uses contextual logger
   └─ For structured logging
```

### VastTracker → Capabilities System

```
VastTracker
├─ Stores tracking_events as registry
│  ├─ Normalizes to: dict[str, list[Trackable]]
│  └─ Converts various formats to unified format
│
├─ Uses TrackingContext for DI
│  ├─ Injected logger
│  ├─ Injected HTTP client
│  ├─ Injected metrics
│  └─ Custom dependencies
│
└─ For each event:
   ├─ If capability 'macros': apply_macros()
   ├─ If capability 'state': check/update state
   ├─ If capability 'http_send': send_with()
   └─ Log results if capability 'logging'
```

## State Management

### Tracking Event State Machine

```
        ┌─────────────┐
        │   Initial   │
        │  (pending)  │
        └──────┬──────┘
               │ track_event()
               │ (send request)
               │
        ┌──────▼──────┐
     ┌──┤  Sending    │──┐
     │  │  (retry 0)  │  │
     │  └──────┬──────┘  │
     │         │         │
     │ ┌───────▼────────┐│
     │ │ Success?       ││
     │ │ (check status) ││
     │ └────┬────────┬──┘│
     │      │yes     │no │
     │      │        └───┼──┐
     │      │            │  │
     │  ┌───▼────┐  ┌────▼──▼──┐
     │  │Tracked │  │   Failed  │
     │  │ (done) │  │           │
     │  └────────┘  └─────┬─────┘
     │                    │
     │            ┌───────▼────────┐
     │            │ Retries < max?  │
     │            └────┬────────┬───┘
     │                 │yes     │no
     │                 │        │
     │            ┌────▼────┐   │
     │            │ Waiting  │◄──┘
     │            │(backoff) │
     │            └────┬─────┘
     │                 │
     └─────────────────┘
```

**State Tracking Methods:**

- `is_tracked()` → Check if event successfully sent
- `mark_tracked(response_time)` → Mark as successfully sent
- `mark_failed(error)` → Mark as failed with error
- `should_retry(max_retries)` → Check if should retry
- `get_avg_response_time()` → Get average response time

## Macro Processing System

### Macro Format Support

The system supports multiple macro formats with priority-based processing:

```
Priority 1: [MACRO_NAME]           (Most specific, checked first)
Priority 2: ${MACRO_NAME}          (Alternative format)

Resolution order:
1. Replace all [MACRO_NAME] patterns
2. Replace all ${MACRO_NAME} patterns
3. Leave unmatched macros unchanged
```

**Example:**

```python
url_template = "https://tracking.example.com?id=[CREATIVE_ID]&ts=${TIMESTAMP}"

macros = {
    "CREATIVE_ID": "123",
    "TIMESTAMP": "1701234567",
    "UNUSED": "value"
}

formats = ["[{macro}]", "${{{macro}}}"]

# Result: https://tracking.example.com?id=123&ts=1701234567
```

**Macro Caching:**

The system caches macro application results based on macro hash:

```python
# Internal state tracking
_macro_cache_key = hash(frozenset(macros.items()))
_macro_cache_value = cached_result
```

## Error Handling Strategy

### Multi-Level Error Handling

```
Level 1: HTTP Errors
├─ Connection errors
├─ Timeout errors
├─ 4xx/5xx responses
└─ Action: Retry with exponential backoff

Level 2: Protocol Errors
├─ XML parsing errors
├─ Invalid VAST structure
├─ Missing required fields
└─ Action: Log, return partial data with error

Level 3: Tracking Errors
├─ Tracking URL failures
├─ Macro substitution errors
├─ State tracking errors
└─ Action: Log but don't fail playback

Level 4: Playback Errors
├─ Duration = 0
├─ Missing creative data
├─ Interruption during playback
└─ Action: Gracefully handle interruption
```

### Retry Strategy

**Exponential Backoff:**

```
Attempt 1: Immediate
Attempt 2: Delay = retry_delay × backoff_multiplier^1
Attempt 3: Delay = retry_delay × backoff_multiplier^2
...
Max retries: 3 (configurable)
```

**Configuration:**

```python
config = VastTrackerConfig(
    max_retries=3,
    retry_delay=1.0,           # seconds
    backoff_multiplier=2.0,    # exponential
    timeout=5.0                 # per request
)
```

## Dependency Injection Pattern

### TrackingContext Design

The `TrackingContext` provides a flexible dependency injection container:

```python
context = TrackingContext(
    # Core dependencies
    logger=logger,
    http_client=http_client,
    metrics_client=metrics,
    
    # Configuration
    timeout=5.0,
    max_retries=3,
    retry_delay=1.0,
    
    # Custom dependencies (extensible)
    _custom={}
)

# Usage
http_client = context.http_client
custom = context.get("custom_key")
```

### Capability Dependency Injection

Capabilities can inject dependencies:

```python
@with_http_send
class TrackableWithHTTP(TrackableEvent):
    async def send_with(self, client, macros=None, **context):
        # Access from TrackingContext
        ctx = get_tracking_context()
        logger = ctx.logger
        metrics = ctx.metrics_client
        
        # Use for logging, metrics, etc.
```

## Extension Points

### 1. Custom Trackable Implementations

Create domain-specific trackable types:

```python
from vast_client.trackable import Trackable, TrackableEvent

@dataclass
class CustomTrackable:
    key: str
    value: Any
    _extras: dict = field(default_factory=dict)
    
    def get_extra(self, name: str, default: Any = None) -> Any:
        return self._extras.get(name, default)
    
    def set_extra(self, name: str, value: Any) -> None:
        self._extras[name] = value
    
    def has_extra(self, name: str) -> bool:
        return name in self._extras
    
    async def send_with(self, client, macros: dict | None = None, **context) -> bool:
        # Custom implementation
        pass
```

### 2. Custom Capability Decorators

Create domain-specific capabilities:

```python
def with_custom_feature(cls):
    """Add custom feature to Trackable."""
    
    def custom_method(self):
        return "custom"
    
    setattr(cls, "custom_method", custom_method)
    _add_capability(cls, "custom_feature")
    return cls

@with_custom_feature
class EnhancedTrackable(TrackableEvent):
    pass
```

### 3. Custom Configuration

Extend configuration for provider-specific needs:

```python
class CustomVastParserConfig(VastParserConfig):
    custom_field: str = ".//CustomField"
    provider_timeout: float = 10.0

config = CustomVastParserConfig()
parser = VastParser(config)
```

### 4. Custom HTTP Clients

Create specialized HTTP clients:

```python
class ProxyAwareEmbedHttpClient(EmbedHttpClient):
    def build_url(self, additional_params=None):
        # Custom URL building logic
        return super().build_url(additional_params)
```

## Performance Considerations

### Connection Pooling

HTTP clients should use connection pooling:

```python
import httpx

# Reuse client across multiple requests
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    ),
    timeout=5.0
)
```

### Macro Caching

Macro substitution results are cached:

```python
# First call: computes result and caches
result1 = event.apply_macros(macros, formats)

# Second call with same macros: uses cache
result2 = event.apply_macros(macros, formats)  # Cache hit
```

### Async Operations

All I/O operations are async:

```python
# HTTP requests
await http_client.get(url)

# Tracking events
await tracker.track_event("impression")

# Playback
await player.play()
```

## Monitoring & Observability

### Structured Logging

All operations use structured logging:

```python
logger.info(
    "tracking_event_sent",
    event_type="impression",
    url=tracking_url,
    response_time=response_ms,
    creative_id=creative_id,
    device_id=device_id
)
```

### Metrics

The system integrates with metrics collection:

```python
context = TrackingContext(
    metrics_client=prometheus_client
)

# Capabilities can record metrics
await send_with(
    client,
    macros=macros,
    metrics=metrics_client
)
```

### Event Filtering for Logging

Control which events are logged:

```python
event.set_event_filters(
    include=["impression", "start", "complete"],
    exclude=["progress-*"]
)

if event.should_log_event("impression"):
    event.log_event()
```

## Testing Architecture

### Mock Support

```python
# Mock HTTP client
class MockHttpClient:
    async def get(self, url, **kwargs):
        return MockResponse(status_code=200, content=xml)

# Mock context
mock_context = TrackingContext(
    logger=mock_logger,
    http_client=mock_http_client,
    timeout=0.1  # Fast tests
)

tracker = VastTracker(
    tracking_events={...},
    context=mock_context
)
```

### Capability Testing

```python
# Test with specific capabilities
@with_macros
@with_state
class TestTrackable(TrackableEvent):
    pass

event = TestTrackable("test", "url")
assert 'macros' in event.__capabilities__
assert 'state' in event.__capabilities__
```

## Thread Safety & Async

The system is designed for async operations:

- **Thread-unsafe:** TrackableEvent is NOT thread-safe
- **Async-safe:** All HTTP operations are async/await
- **Context-safe:** TrackingContext is thread-safe for read operations

```python
# Async operations
async with httpx.AsyncClient() as client:
    await tracker.track_event("impression")
    await player.play()

# NOT recommended: sync operations
# Blocking would prevent other async tasks
```

## Versioning & Compatibility

- **Version:** 1.0.0
- **VAST Support:** 2.0, 3.0, 4.0
- **Python:** 3.10+
- **Async Framework:** asyncio
- **Breaking Changes:** Tracked via version numbers

## Roadmap

### Planned Features

1. **Parallel Tracking:** Send multiple tracking requests concurrently
2. **Caching:** Response caching with TTL
3. **Metrics:** Built-in Prometheus metrics
4. **Validation:** Schema validation for VAST XML
5. **Compression:** Support for gzip responses

### Deprecated Features

- `ad_request` parameter → Use `embed_client` instead
- Old initialization patterns → Use `from_embed` pattern

## Related Documentation

- README.md - User guide and examples
- config.py - Configuration classes documentation
- trackable.py - Protocol definition
- capabilities.py - Capability system details
- CTV Middleware Architecture - ../ARCHITECTURE.md
