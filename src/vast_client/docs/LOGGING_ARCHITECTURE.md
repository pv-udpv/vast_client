# Logging Architecture - Request IDs and Aggregation

## Overview

The VAST client now includes enhanced logging infrastructure with request ID correlation, hierarchical context, and namespace aggregation. This makes it easy to:

1. **Join related logs** - All logs from a single request share a `request_id`
2. **Aggregate operations** - Group related fields under namespaces (vast_event, trackable, result)
3. **Follow request flow** - Parent-child relationships via `span_id` and `parent_id`
4. **Control verbosity** - Sampling and operation-level configuration

## Core Concepts

### Request ID

Every operation gets a unique `request_id` (12-character hex string) that automatically propagates through async calls:

```python
async with LoggingContext(operation="track_event") as ctx:
    # ctx.request_id = "a1b2c3d4e5f6"
    await nested_operation()  # Inherits same request_id
```

### Span ID

Each context gets a unique `span_id` for identifying specific operations:

```python
async with LoggingContext(operation="parent") as parent:
    # parent.span_id = "abc123def456"
    async with LoggingContext(operation="child") as child:
        # child.span_id = "xyz789uvw012"
        # child.parent_id = "abc123def456"
```

### Namespace Aggregation

Related fields are grouped under logical namespaces:

- **vast_event**: Event metadata (type, creative_id)
- **trackable**: Trackable-specific data (index, key, URL)
- **result**: Operation results (success, duration, counts)
- **Custom**: Any custom namespace (http, config, player, etc.)

```python
ctx = LoggingContext(operation="track_event")
ctx.vast_event = {"type": "impression", "creative_id": "123"}
ctx.result = {"success": True, "duration": 0.234}
ctx.set_namespace("http", status_code=200)

log_dict = ctx.to_log_dict()
# {
#   "request_id": "...",
#   "vast_event": {"type": "impression", "creative_id": "123"},
#   "result": {"success": True, "duration": 0.234},
#   "http": {"status_code": 200}
# }
```

## Configuration

### VastLoggingConfig

Control logging behavior globally or per-operation:

```python
from vast_client.logging import VastLoggingConfig, SamplingStrategy, set_logging_config

config = VastLoggingConfig(
    # Global log level
    level="INFO",
    
    # Debug sampling (0.0 = none, 1.0 = all)
    debug_sample_rate=0.1,  # 10% of debug logs
    
    # Sampling strategy
    sampling_strategy=SamplingStrategy.DETERMINISTIC,  # or RANDOM, NONE
    
    # Operation-specific overrides
    operation_levels={
        "track_event": "INFO",      # Always log
        "send_trackable": "DEBUG",  # Only if sampled
        "apply_macros": "DEBUG",    # Only if sampled
    },
    
    # Advanced options
    enable_hierarchical_messages=True,
    max_namespace_depth=3,
)

set_logging_config(config)
```

### Sampling Strategies

1. **Random**: Each log has `debug_sample_rate` probability of being emitted
2. **Deterministic**: Hash of `request_id` determines sampling (consistent per request)
3. **None**: All debug logs emitted (ignores sample rate)

**Example: Deterministic Sampling**

```python
config = VastLoggingConfig(
    debug_sample_rate=0.5,
    sampling_strategy=SamplingStrategy.DETERMINISTIC,
)

# Request A (request_id="aaa111") - hash % 100 = 23 → logged (< 50)
# Request B (request_id="bbb222") - hash % 100 = 67 → not logged (>= 50)
# Request A again - hash % 100 = 23 → logged (consistent!)
```

## Integration with Tracker

The `VastTracker.track_event()` method now automatically uses `LoggingContext`:

```python
tracker = VastTracker(tracking_events, creative_id="creative-123")

# When you call track_event, logs look like:
await tracker.track_event("impression")

# Log output (structured JSON):
{
  "event": "Event tracked successfully",
  "timestamp": "2025-12-09T16:05:48.123Z",
  "level": "info",
  "request_id": "a1b2c3d4e5f6",
  "span_id": "f6e5d4c3b2a1",
  "operation": "track_event",
  "vast_event": {
    "type": "impression",
    "creative_id": "creative-123"
  },
  "result": {
    "success": true,
    "duration": 0.234,
    "successful_trackables": 2,
    "total_trackables": 2
  }
}
```

### Nested Trackable Context

Each trackable send creates a nested context:

```python
# Parent context (track_event)
{
  "request_id": "a1b2c3d4e5f6",
  "span_id": "parent-span-id",
  "operation": "track_event",
  "vast_event": {"type": "impression"}
}

# Child context (send_trackable)
{
  "request_id": "a1b2c3d4e5f6",  # Same request_id!
  "span_id": "child-span-id",
  "parent_id": "parent-span-id",   # Links to parent
  "operation": "send_trackable",
  "trackable": {"index": 0, "key": "imp_0"},
  "http": {"url": "https://...", "status_code": 200}
}
```

## Usage Examples

### Example 1: Basic Context

```python
from vast_client.logging import LoggingContext
from vast_client.log_config import get_context_logger

logger = get_context_logger("my_module")

async def my_operation():
    async with LoggingContext(operation="my_op") as ctx:
        logger.info("operation.started", **ctx.to_log_dict())
        
        # Do work
        ctx.result["items_processed"] = 10
        
        logger.info("operation.completed", **ctx.to_log_dict())
```

### Example 2: Nested Operations

```python
async def parent_operation():
    async with LoggingContext(operation="parent") as parent_ctx:
        parent_ctx.set_namespace("config", timeout=5.0)
        logger.info("parent.started", **parent_ctx.to_log_dict())
        
        # Child operation inherits request_id
        async with LoggingContext(
            parent_id=parent_ctx.span_id,
            operation="child"
        ) as child_ctx:
            child_ctx.set_namespace("http", method="GET")
            logger.debug("child.started", **child_ctx.to_log_dict())
            
            # Both logs share same request_id
            # Can query/filter by request_id to see full operation flow
```

### Example 3: Custom Namespaces

```python
async def http_request():
    async with LoggingContext(operation="http_request") as ctx:
        # Track HTTP-specific fields
        ctx.set_namespace("http", method="POST", url="https://api.example.com")
        
        # Track request payload
        ctx.set_namespace("request", size_bytes=1024, content_type="application/json")
        
        # Make request
        response = await client.post(...)
        
        # Track response
        ctx.set_namespace("http", status_code=response.status_code)
        ctx.result["success"] = response.status_code == 200
        
        logger.info("http.completed", **ctx.to_log_dict())
```

## Querying Logs

### Find all logs for a request

```bash
# If using structured logging to file/ELK/CloudWatch
jq 'select(.request_id == "a1b2c3d4e5f6")' logs.jsonl
```

### Find parent-child relationships

```bash
# Find parent
jq 'select(.span_id == "parent-span-id")' logs.jsonl

# Find children
jq 'select(.parent_id == "parent-span-id")' logs.jsonl
```

### Aggregate by operation

```bash
# Count operations by type
jq -r '.operation' logs.jsonl | sort | uniq -c

# Average duration by operation
jq -r 'select(.operation == "track_event") | .result.duration' logs.jsonl | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

## Migration Guide

### From Old Logging

**Old:**
```python
logger.info("Event tracked", event_type=event, creative_id=creative_id, 
            response_time=time.time() - start, success_count=5)
```

**New:**
```python
async with LoggingContext(operation="track_event", 
                          vast_event={"type": event, "creative_id": creative_id}) as ctx:
    # ... do work ...
    ctx.result.update({
        "duration": time.time() - start,
        "success_count": 5
    })
    logger.info("Event tracked", **ctx.to_log_dict())
```

### Benefits

1. **Structured**: Fields grouped logically (vast_event.*, result.*)
2. **Correlated**: All logs have same request_id
3. **Hierarchical**: Parent-child relationships preserved
4. **Queryable**: Easy to filter/aggregate in log systems

## Advanced Topics

### Context Propagation in Tasks

LoggingContext automatically propagates through asyncio tasks:

```python
async def background_task():
    # This inherits the parent's request_id!
    ctx = get_current_context()
    logger.info("background.started", request_id=ctx.request_id)

async with LoggingContext(operation="main") as ctx:
    task = asyncio.create_task(background_task())
    await task
```

### Manual Context Access

```python
from vast_client.logging import get_current_context, clear_context

# Get current context
ctx = get_current_context()
if ctx:
    print(f"Current request: {ctx.request_id}")

# Clear context (useful in tests)
clear_context()
```

### Duration Tracking

```python
async with LoggingContext(operation="long_task") as ctx:
    await asyncio.sleep(2)
    
    # Get elapsed time
    duration = ctx.get_duration()  # ~2.0 seconds
    ctx.result["duration"] = duration
```

## Troubleshooting

### Too many debug logs?

Increase sampling rate:
```python
config = VastLoggingConfig(debug_sample_rate=0.01)  # Only 1%
```

### Debug logs not appearing?

Check sampling and operation levels:
```python
config = VastLoggingConfig(
    debug_sample_rate=1.0,  # Enable all
    operation_levels={"my_op": "DEBUG"}  # Enable for specific operation
)
```

### Missing request_id?

Ensure you're inside a LoggingContext:
```python
# Wrong - no context
logger.info("message")  # No request_id

# Right - inside context
async with LoggingContext(operation="op"):
    logger.info("message", **ctx.to_log_dict())  # Has request_id
```

## Performance Considerations

- LoggingContext uses contextvars (low overhead)
- Sampling reduces log volume (use deterministic for consistency)
- Namespace grouping has minimal impact on log size
- to_log_dict() creates shallow copies (safe to modify)

## Future Enhancements

See issue for planned future PRs:
- PR #2: Tracker integration improvements
- PR #3: HTTP client logging integration
- PR #4: Documentation and query pattern examples
