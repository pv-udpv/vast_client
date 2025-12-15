# VAST Client Package - User Guide

## Overview

The **VAST Client** package is a comprehensive, production-ready implementation for handling Video Ad Serving Template (VAST) protocol operations in CTV (Connected TV) advertising environments. It provides complete lifecycle management for VAST ads, from initial requests through playback and event tracking.

### Key Features

✨ **Full VAST Protocol Support**

- Compliant VAST 2.0, 3.0, and 4.0 parsing
- Flexible XML parsing with error recovery
- Support for inline ads and ad pods

🎯 **Advanced Tracking System**

- Event-based tracking with macro substitution
- Flexible tracking state management
- Retry mechanisms with configurable policies

▶️ **Playback Management**

- Progress tracking with quartile events
- Real-time playback state management
- Intelligent interruption handling

🔗 **HTTP Client Integration**

- Modular HTTP client architecture
- Context-aware request handling
- Connection pooling and timeout management

📊 **Extensibility & Capabilities**

- Mixin-based capability system
- Dependency injection support
- Custom macro processing

## Quick Start

### Installation

```python
from vast_client import VastClient, VastParser, VastTracker, VastPlayer
```

### Basic Usage

#### 1. Simple Ad Request

```python
from vast_client import VastClient

# Create client with URL
client = VastClient("https://ads.example.com/vast")

# Request ad
ad_data = await client.request_ad()

# Access ad information
print(f"Ad System: {ad_data.get('ad_system')}")
print(f"Creative Duration: {ad_data.get('duration')}")
```

#### 2. Ad Request with Context

```python
from vast_client import VastClient
from vast_client.embed_http_client import EmbedHttpClient

# Create HTTP client with base configuration
embed_client = EmbedHttpClient(
    base_url="https://ads.example.com/vast",
    base_params={
        "publisher": "my_publisher",
        "placement": "preroll"
    },
    base_headers={
        "User-Agent": "CTV-Device/1.0"
    }
)

# Create VAST client from HTTP client
client = VastClient.from_embed(embed_client, ctx=ad_request)

# Request ad with additional params
ad_data = await client.request_ad(params={"slot": "pre-roll"})
```

#### 3. Playing an Ad with Tracking

```python
from vast_client import VastClient, VastPlayer

# Request ad
client = VastClient("https://ads.example.com/vast", ctx=ad_request)
ad_data = await client.request_ad()

# Create player
player = VastPlayer(client, ad_data)

# Play ad (with automatic tracking)
await player.play()

# Get playback info
print(f"Current time: {player.playback_seconds}s")
print(f"Progress: {player.progress_percent}%")
```

#### 4. Manual Tracking

```python
from vast_client import VastTracker
from vast_client.embed_http_client import EmbedHttpClient

# Create tracker with tracking events
tracking_events = {
    "impression": ["https://tracking.example.com/impression"],
    "error": ["http:..."],
    "start": ["https://tracking.example.com/start"],
    "midpoint": ["https://tracking.example.com/midpoint"],
}

# Initialize tracker
tracker = VastTracker(
    tracking_events=tracking_events,
    embed_client=embed_client,
    creative_id="creative_123"
)

# Track events
await tracker.track_event("impression")
await tracker.track_event("start")
await tracker.track_event("midpoint", macros={"duration": "30"})
```

#### 5. Custom XPath Parsing

```python
from vast_client import VastClient
from vast_client.config import XPathSpec, ExtractMode

# Define XPath specifications with callback functions
xpath_specs = [
    XPathSpec(
        xpath=".//Impression",
        name="tracking_events",
        callback=lambda urls: {"impression": urls} if urls else {},
        mode=ExtractMode.LIST
    ),
    XPathSpec(
        xpath=".//Duration",
        name="duration_seconds",
        callback=lambda d: int(float(d)) if d else None,
        mode=ExtractMode.SINGLE
    ),
    XPathSpec(
        xpath=".//Extensions/ProviderData/ID",
        name="provider_id",
        callback=lambda id: int(id) if id and id.isdigit() else None,
        mode=ExtractMode.SINGLE,
        required=False
    )
]

# Create client with xpath_specs
client = VastClient(
    "https://ads.example.com/vast",
    ctx=ad_request,
    xpath_specs=xpath_specs
)

# Request ad - automatically applies xpath_specs parsing
results = await client.request_ad()

# Access parsed results
impressions = results["tracking_events"]
duration = results["duration_seconds"]
provider_id = results["provider_id"]

# Track events (no chain_id needed)
await client.track_event("impression")
await client.track_event("start")
```

#### 6. Wrapper Resolution (Automatic)

VAST wrapper ads are automatically resolved to their inline content:

```python
from vast_client import VastClient

# Wrapper resolution happens automatically - no special configuration needed
client = VastClient("https://ads.example.com/vast", ctx=ad_request)

# Request ad - client automatically follows wrapper chains up to 5 levels deep
ad_data = await client.request_ad()

# Result contains the final inline ad data
print(f"Ad Title: {ad_data.get('ad_title')}")
print(f"Duration: {ad_data.get('duration')}s")
print(f"Media URL: {ad_data.get('media_url')}")

# If wrapper resolution failed, check the flag
if ad_data.get("_wrapper_resolution_failed"):
    print("Wrapper resolution failed - returned partial data")
```

## Core Components

### VastClient

The main facade for VAST operations. Supports multiple initialization patterns.

**Features:**

- Flexible configuration (URL string, dict, VastClientConfig)
- Automatic HTTP client management
- **Automatic VAST wrapper resolution (up to 5 levels deep)**
- **Custom XPath parsing with xpath_specs parameter**
- **Enhanced logging with request IDs, aggregation, and hierarchical context**
- Integration with parser, tracker, and player

**Initialization Methods:**

```python
# From URL string
client = VastClient("https://ads.example.com/vast")

# From configuration dict
client = VastClient({
    "base_url": "https://ads.example.com/vast",
    "params": {"publisher": "pub1"},
    "headers": {"User-Agent": "Device"}
})

# From EmbedHttpClient
embed_client = EmbedHttpClient(base_url="...", base_params={...})
client = VastClient.from_embed(embed_client)

# With ad request context
client = VastClient(url, ctx=ad_request)
```

**Key Methods:**

```python
# Request ad
ad_data = await client.request_ad(params={"slot": "preroll"})

# Play ad
player = await client.play_ad(ad_data)

# Track event
await client.tracker.track_event("impression")

# Get metrics
metrics = client.get_metrics()
```

### VastParser

Handles VAST XML parsing with flexible configuration.

**Features:**

- Configurable XPath selectors
- Error recovery with optional strict parsing
- Multi-language support
- Custom provider-specific field extraction

**Usage:**

```python
from vast_client import VastParser

parser = VastParser()

# Parse VAST XML
vast_data = parser.parse_vast(xml_string)

# Access parsed data
print(vast_data['vast_version'])
print(vast_data['ad_system'])
print(vast_data['media_files'])
print(vast_data['tracking_events'])
```

**Custom Configuration:**

```python
from vast_client.config import VastParserConfig
from vast_client import VastParser

config = VastParserConfig(
    xpath_duration=".//Duration",
    strict_xml=False,
    recover_on_error=True,
    custom_xpaths={
        "provider_specific": ".//Extensions/ProviderData"
    }
)

parser = VastParser(config)
```

### VastTracker

Manages VAST tracking events with advanced capabilities.

**Features:**

- Event registry with list/single URL support
- Macro substitution in tracking URLs
- Retry mechanisms with exponential backoff
- State tracking (tracked, failed, pending)
- Trackable protocol with capability composition

**Usage:**

```python
from vast_client import VastTracker

tracker = VastTracker(
    tracking_events={
        "impression": ["https://tracking.example.com/impression"],
        "start": ["https://tracking.example.com/start"],
        "progress-0": ["https://tracking.example.com/0pct"],
        "progress-25": ["https://tracking.example.com/25pct"],
        "progress-50": ["https://tracking.example.com/50pct"],
        "progress-75": ["https://tracking.example.com/75pct"],
        "complete": ["https://tracking.example.com/complete"],
    },
    embed_client=embed_client,
    creative_id="creative_123"
)

# Track events with macros
await tracker.track_event(
    "progress-25",
    macros={
        "creative_id": "creative_123",
        "timestamp": str(int(time.time())),
        "device_id": "device_123"
    }
)
```

### VastPlayer

Handles ad playback with automatic progress tracking.

**Features:**

- Real-time progress tracking
- Quartile event detection (0%, 25%, 50%, 75%, 100%)
- Automatic tracking integration
- Playback state management
- Interruption handling

**Usage:**

```python
from vast_client import VastPlayer

player = VastPlayer(client, ad_data)

# Start playback
await player.play()

# Check status
print(f"Is playing: {player.is_playing}")
print(f"Duration: {player.creative_duration}s")
print(f"Current time: {player.playback_seconds}s")
print(f"Progress: {player.progress_percent}%")

# Stop playback
player.stop()
```

### EmbedHttpClient

HTTP client with embedded configuration for base URL, parameters, and headers.

**Features:**

- Base URL and parameter management
- Header merging
- URL encoding configuration
- Context-aware request building
- Automatic tracking macro generation

**Usage:**

```python
from vast_client.embed_http_client import EmbedHttpClient

# Create with base configuration
client = EmbedHttpClient(
    base_url="https://ads.example.com/vast",
    base_params={
        "publisher": "pub1",
        "version": "4.0"
    },
    base_headers={
        "User-Agent": "CTV-Device/1.0",
        "Accept": "application/xml"
    },
    encoding_config={
        "url_encode_params": True,
        "preserve_unicode": True
    }
)

# Build URL with additional params
url = client.build_url({"slot": "preroll"})
# Result: https://ads.example.com/vast?publisher=pub1&version=4.0&slot=preroll

# Get merged headers
headers = client.get_headers({"X-Request-ID": "req_123"})
```

## Advanced Features

### Trackable Protocol

The `Trackable` protocol defines the interface for trackable items with capability composition.

**Protocol Methods:**

```python
class Trackable(Protocol):
    key: str           # Event type identifier
    value: Any         # Tracking URL(s)
    
    def get_extra(self, name: str, default: Any = None) -> Any
    def set_extra(self, name: str, value: Any) -> None
    def has_extra(self, name: str) -> bool
    
    async def send_with(
        self, 
        client, 
        macros: dict[str, str] | None = None,
        **context
    ) -> bool
```

**TrackableEvent Implementation:**

```python
from vast_client.trackable import TrackableEvent

# Create trackable event
event = TrackableEvent(
    key="impression",
    value="https://tracking.example.com/impression"
)

# Use extra attributes
event.set_extra("creative_id", "creative_123")
event.set_extra("attempt_count", 0)

# Dot notation access
event.attempt_count  # 0
event.get_extra("creative_id")  # "creative_123"
```

### Capability Decorators

Compose functionality using capability decorators.

**Available Capabilities:**

```python
from vast_client.capabilities import (
    with_macros,
    with_state,
    with_logging,
    with_event_filtering,
    with_http_send
)

@with_macros
@with_state
@with_logging
@with_http_send
class TrackingEvent(TrackableEvent):
    pass

# Now supports macro processing, state tracking, logging, and HTTP sending
event = TrackingEvent("impression", "https://tracking.example.com/impression?cid=[CREATIVE_ID]")
```

**Capability Methods:**

- **with_macros**: `apply_macros(macros, formats)`
- **with_state**: `is_tracked()`, `mark_tracked()`, `mark_failed()`, `should_retry()`
- **with_logging**: `to_log_dict()`, `log_event()`
- **with_event_filtering**: `set_event_filters()`, `should_log_event()`
- **with_http_send**: `send_with(client, macros, **context)`

### Macro Substitution

Trackable objects support multiple macro formats with automatic `ad_request` resolution.

**Automatic Macro Mapping (New):**

The tracker now automatically resolves macros from `ad_request` without explicit configuration:

```python
# ad_request contains device_serial, user_id, etc.
ad_request = {
    "device_serial": "ABC-123",
    "user_id": "user_456",
    "ext": {
        "channel_to": {"display_name": "HBO HD"}
    }
}

# Tracking URL with macros
url = "https://track.example.com?serial=[DEVICE_SERIAL]&user=[USER_ID]&channel=[EXT_CHANNEL_TO_DISPLAY_NAME]"

# Macros are automatically resolved from ad_request:
# [DEVICE_SERIAL] → ad_request["device_serial"] → "ABC-123"
# [USER_ID] → ad_request["user_id"] → "user_456"  
# [EXT_CHANNEL_TO_DISPLAY_NAME] → ad_request["ext"]["channel_to"]["display_name"] → "HBO HD"
```

**Manual Macro Application:**

```python
# Format 1: [MACRO_NAME]
url = "https://tracking.example.com?cid=[CREATIVE_ID]&ts=[TIMESTAMP]"

# Format 2: ${MACRO_NAME}
url = "https://tracking.example.com?cid=${CREATIVE_ID}&ts=${TIMESTAMP}"

# Apply macros manually
macros = {
    "CREATIVE_ID": "creative_123",
    "TIMESTAMP": "1701234567"
}

result = event.apply_macros(macros, ["[{macro}]", "${{{macro}}}"])
# Result: https://tracking.example.com?cid=creative_123&ts=1701234567
```

**Macro Resolution Priority:**

1. Explicitly provided macros via `macros` parameter
2. Embed client tracking macros (from `get_tracking_macros()`)
3. Auto-resolved from `ad_request` (flat and nested paths)
4. Static macros from configuration

### Dependency Injection

The tracker supports dependency injection through `TrackingContext`.

**TrackingContext:**

```python
from vast_client.context import TrackingContext

context = TrackingContext(
    logger=get_context_logger("vast_tracker"),
    http_client=httpx.AsyncClient(),
    metrics_client=metrics_client,
    timeout=5.0,
    max_retries=3,
    retry_delay=1.0
)

tracker = VastTracker(
    tracking_events={...},
    context=context
)
```

**Custom Dependencies:**

```python
context = TrackingContext()
context.set("custom_header_builder", lambda: {"X-Custom": "value"})
custom_value = context.get("custom_header_builder")
```

### Event Filtering

Control which events are logged using glob patterns.

**Configuration:**

```python
@with_event_filtering
class TrackingEvent(TrackableEvent):
    pass

event = TrackingEvent("impression", "https://...")

# Include only specific events
event.set_event_filters(
    include=["impression", "start", "complete"],
    exclude=["progress-*"]
)

# Check if event should be logged
if event.should_log_event("impression"):
    print("Log this event")
```

## Configuration

### HTTP client configuration

The HTTP clients (main ad requests and tracking pixels) are configurable via settings to control timeouts, connection pooling, and SSL verification. Provide values in YAML or environment variables (nested keys use `__`).

Example YAML (as used by middleware):

```yaml
http:
    timeout: 30.0
    max_connections: 20
    max_keepalive_connections: 10
    keepalive_expiry: 5.0
    verify_ssl: true

    tracking:
        timeout: 5.0
        max_connections: 50
        max_keepalive_connections: 20
        keepalive_expiry: 5.0
        verify_ssl: true
```

Equivalent environment overrides:

- `VAST_HTTP__TIMEOUT`, `VAST_HTTP__MAX_CONNECTIONS`, `VAST_HTTP__KEEPALIVE_EXPIRY`
- `VAST_HTTP__VERIFY_SSL`
- Tracking-specific: `VAST_HTTP__TRACKING__TIMEOUT`, `VAST_HTTP__TRACKING__MAX_CONNECTIONS`, `VAST_HTTP__TRACKING__VERIFY_SSL`

The same pattern works for tracker settings (e.g., `VAST_HTTP__TRACKING__TIMEOUT`) and other VAST client knobs defined in `src/vast_client/config.py` / `src/config.py`.

### VastParserConfig

```python
from vast_client.config import VastParserConfig

config = VastParserConfig(
    # XPath selectors
    xpath_ad_system=".//AdSystem",
    xpath_ad_title=".//AdTitle",
    xpath_impression=".//Impression",
    xpath_error=".//Error",
    xpath_creative=".//Creative",
    xpath_media_files=".//MediaFile",
    xpath_tracking_events=".//Tracking",
    
    # Parsing options
    strict_xml=False,              # Allow malformed XML
    recover_on_error=True,          # Try to recover from errors
    encoding="utf-8",               # Default encoding
    
    # Custom XPath
    custom_xpaths={
        "provider_field": ".//Extensions/Provider"
    }
)

parser = VastParser(config)
```

### VastTrackerConfig

```python
from vast_client.config import VastTrackerConfig

config = VastTrackerConfig(
    # Macro formats (order matters - most specific first)
    macro_formats=["[{macro}]", "${{{macro}}}"],
    
    # Macro mapping (parameter_name: MACRO_NAME)
    # Auto-resolves from ad_request without template strings
    macro_mapping={
        "device_serial": "DEVICE_SERIAL",      # Auto: ad_request.device_serial
        "user_id": "USER_ID",                  # Auto: ad_request.user_id
        "ext.channel_to.display_name": "CHANNEL_NAME"  # Auto: nested path
    },
    
    # Tracking options
    track_errors=True,
    track_user_close=True,
    parallel_tracking=False,
    
    # Retry configuration
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0,
    
    # Context injection
    context_timeout=5.0,
    context_max_retries=3,
    context_retry_delay=1.0,
    
    # Timeout
    timeout=5.0
)

tracker = VastTracker(tracking_events={...}, config=config)
```

### VastClientConfig with SSL/TLS Verification

Configure SSL certificate verification for VAST requests:

```python
from vast_client.config import VastClientConfig
from vast_client.client import VastClient

# Enable SSL verification (default - production recommended)
config = VastClientConfig(ssl_verify=True)
client = VastClient(config)

# Disable SSL verification (development only)
config = VastClientConfig(ssl_verify=False)
client = VastClient(config)

# Use custom CA bundle
config = VastClientConfig(ssl_verify="/path/to/ca-bundle.crt")
client = VastClient(config)

# Pass ssl_verify directly to VastClient
client = VastClient("https://ads.example.com/vast", ssl_verify=False)
```

**SSL Verification Options:**

| Value | Use Case | Security |
|-------|----------|----------|
| `True` (default) | Production with standard CAs | ✅ Recommended |
| `False` | Development/testing only | ⚠️ Use with caution |
| `"/path/to/ca.crt"` | Custom internal CAs | ✅ Recommended |

For detailed SSL configuration guide, see [SSL_VERIFICATION_GUIDE.md](SSL_VERIFICATION_GUIDE.md).

## Logging and Monitoring

The package provides **enhanced logging infrastructure** with request ID correlation, hierarchical context, and namespace aggregation.

### New Logging Architecture (v1.0.0+)

**Key Features:**

- ✅ **Request ID Correlation** - All logs from a single operation share a unique `request_id`
- ✅ **Hierarchical Context** - Parent-child relationships via `span_id` and `parent_id`
- ✅ **Namespace Aggregation** - Related fields grouped under `vast_event`, `trackable`, `result`, etc.
- ✅ **Sampling Control** - Configurable debug sampling (random or deterministic)
- ✅ **Async Propagation** - Context automatically propagates through async calls

**Quick Example:**

```python
from vast_client.logging import LoggingContext, VastLoggingConfig, set_logging_config

# Configure logging behavior
config = VastLoggingConfig(
    level="INFO",
    debug_sample_rate=0.1,  # Sample 10% of debug logs
    sampling_strategy="deterministic",
    operation_levels={
        "track_event": "INFO",
        "send_trackable": "DEBUG"
    }
)
set_logging_config(config)

# Automatic in VastTracker
tracker = VastTracker(tracking_events, creative_id="creative-123")
await tracker.track_event("impression")  # Uses LoggingContext internally
```

**Log Output:**

```json
{
  "request_id": "a1b2c3d4e5f6",
  "span_id": "f6e5d4c3b2a1",
  "operation": "track_event",
  "vast_event": {"type": "impression", "creative_id": "creative-123"},
  "result": {
    "success": true,
    "duration": 0.234,
    "successful_trackables": 2,
    "total_trackables": 2
  }
}
```

**Manual Usage:**

```python
from vast_client.logging import LoggingContext
from vast_client.log_config import get_context_logger

logger = get_context_logger("my_module")

async with LoggingContext(operation="custom_op") as ctx:
    ctx.vast_event = {"type": "custom"}
    logger.info("started", **ctx.to_log_dict())
    
    # Do work
    ctx.result["items_processed"] = 10
    
    logger.info("completed", **ctx.to_log_dict())
```

**See Also:**

- 📖 Full documentation: `src/vast_client/docs/LOGGING_ARCHITECTURE.md`
- 🔬 Demo script: `examples/logging_demo.py`

### Legacy Context Variables (Deprecated)

The older context variable system is still supported for backward compatibility:

```python
from vast_client import VastClient
from log_config import get_context_logger

client = VastClient("https://ads.example.com/vast", ctx=ad_request)

# Logger automatically includes context:
# - request_id: correlation ID
# - user_agent: device info
# - creative_id: current creative
# - playback_seconds: current playback position
# - progress_quartile: current quartile
```

**Key Events:**

```python
from events import VastEvents

# Tracked automatically
VastEvents.PARSE_STARTED          # XML parsing started
VastEvents.PARSE_FAILED           # XML parsing failed
VastEvents.REQUEST_STARTED        # VAST request started
VastEvents.REQUEST_SUCCESS        # VAST request succeeded
VastEvents.REQUEST_FAILED         # VAST request failed
VastEvents.TRACKING_EVENT_SENT    # Tracking event sent
VastEvents.TRACKING_FAILED        # Tracking failed
VastEvents.PLAYER_INITIALIZED     # Player initialized
VastEvents.PLAYBACK_STARTED       # Playback started
VastEvents.PLAYBACK_INTERRUPTED   # Playback interrupted
VastEvents.PLAYBACK_COMPLETED     # Playback completed
```

## Error Handling

The package provides graceful error handling at multiple levels.

**Exception Types:**

```python
from lxml import etree

# Parser errors
try:
    parsed = parser.parse_vast(xml)
except etree.XMLSyntaxError as e:
    logger.error("XML parsing failed", error=str(e))

# HTTP errors (automatically retried)
try:
    ad_data = await client.request_ad()
except Exception as e:
    logger.error("VAST request failed", error=str(e))

# Tracking errors (logged but don't fail playback)
try:
    await tracker.track_event("impression")
except Exception as e:
    logger.error("Tracking failed", event="impression", error=str(e))
```

## Best Practices

### 1. Context Management

Always provide context for better logging:

```python
# Good: With context
client = VastClient(url, ctx={
    "device_id": device_id,
    "user_agent": user_agent,
    "session_id": session_id
})

# Acceptable: Without context
client = VastClient(url)
```

### 2. Resource Management

Use proper async context management:

```python
import httpx
from vast_client import VastClient

# Good: Proper resource cleanup
async with httpx.AsyncClient() as http_client:
    client = VastClient(url, client=http_client)
    ad_data = await client.request_ad()

# Good: Using from_embed with managed client
async with httpx.AsyncClient() as http_client:
    embed_client = EmbedHttpClient(url, ...)
    client = VastClient.from_embed(embed_client)
    ad_data = await client.request_ad()
```

### 3. Error Recovery

Configure retry behavior for reliability:

```python
from vast_client.config import VastTrackerConfig

config = VastTrackerConfig(
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0
)

tracker = VastTracker(tracking_events={...}, config=config)
```

### 4. Performance Optimization

Reuse clients across requests:

```python
# Good: Single client, multiple requests
async with httpx.AsyncClient() as http_client:
    embed_client = EmbedHttpClient(url, ...)
    client = VastClient.from_embed(embed_client)
    
    # Multiple requests share same HTTP client
    ad1 = await client.request_ad(params={"placement": "preroll"})
    ad2 = await client.request_ad(params={"placement": "midroll"})
```

### 5. Macro Configuration

Leverage automatic macro resolution:

```python
# Good: Use auto-resolution from ad_request
tracker = VastTracker(
    tracking_events={
        "impression": "https://track.example.com?serial=[DEVICE_SERIAL]"
    },
    embed_client=embed_client  # Contains ad_request
)
# [DEVICE_SERIAL] automatically resolves from ad_request.device_serial

# Also good: Provide explicit macros for non-ad_request values
await tracker.track_event("impression", macros={
    "CREATIVE_ID": "creative_123",
    "TIMESTAMP": str(int(time.time()))
})

# Safe: Handle missing macros
if "CREATIVE_ID" not in macros:
    logger.warning("Missing required macro", macro="CREATIVE_ID")
```

## Examples

### Complete VAST Workflow

```python
import asyncio
import httpx
from vast_client import VastClient, VastPlayer
from vast_client.embed_http_client import EmbedHttpClient

async def complete_vast_workflow():
    """Complete VAST ad workflow with request, playback, and tracking."""
    
    # Create HTTP client with base configuration
    embed_client = EmbedHttpClient(
        base_url="https://ads.example.com/vast",
        base_params={"publisher": "my_pub"},
        base_headers={"User-Agent": "Device/1.0"}
    )
    
    # Create VAST client
    client = VastClient.from_embed(embed_client, ctx={
        "session_id": "sess_123",
        "device_id": "dev_123"
    })
    
    # Request ad
    print("Requesting ad...")
    ad_data = await client.request_ad(params={"placement": "preroll"})
    print(f"Received ad: {ad_data['ad_title']}")
    
    # Play ad with automatic tracking
    print("Playing ad...")
    player = VastPlayer(client, ad_data)
    await player.play()
    print(f"Playback complete. Duration: {ad_data.get('duration')}s")
    
    print("Workflow complete!")

# Run
asyncio.run(complete_vast_workflow())
```

### Custom Parser Configuration

```python
from vast_client.config import VastParserConfig
from vast_client import VastParser

# Configure parser for specific provider
config = VastParserConfig(
    custom_xpaths={
        "provider_id": ".//Extensions/ProviderData/ID",
        "provider_category": ".//Extensions/ProviderData/Category"
    },
    recover_on_error=True
)

parser = VastParser(config)
vast_data = parser.parse_vast(xml_response)

# Access custom fields
provider_id = vast_data.get("extensions", {}).get("provider_id")
```

## Troubleshooting

### Issue: XML Parsing Fails

**Solution:** Enable error recovery

```python
config = VastParserConfig(recover_on_error=True, strict_xml=False)
parser = VastParser(config)
```

### Issue: Tracking URLs Not Sent

**Solution:** Check HTTP client and retry configuration

```python
config = VastTrackerConfig(
    max_retries=5,
    retry_delay=2.0,
    timeout=10.0
)
tracker = VastTracker(tracking_events={...}, config=config)
```

### Issue: Slow Playback Tracking

**Solution:** Check playback duration and update interval

```python
player = VastPlayer(client, ad_data)
# Ensure creative_duration is set correctly
assert player.creative_duration > 0, "Duration must be > 0"
```

## Contributing

When extending the VAST Client package:

1. **Implement Trackable protocol** for custom tracking objects
2. **Use capability decorators** for composable functionality
3. **Provide configuration classes** for provider-specific customization
4. **Add logging** using `get_context_logger`
5. **Document new features** in this README

## References

- VAST 2.0, 3.0, 4.0 Specifications: <https://www.iab.com/guidelines/vast/>
- CTV Middleware Architecture: See `../ARCHITECTURE.md`
- Logging System: See `../../log_config/README.md`
- HTTP Client Manager: See `../../http_client_manager.py`
