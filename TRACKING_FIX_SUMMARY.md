# Tracking Fix Summary

## Problem
Impression and quartile tracking stopped working after ~3 hours of operation (last successful tracking at 2025-12-09 02:49:39Z).

## Root Cause
The HTTP client `keepalive_expiry` was set to 5.0 seconds globally. This caused the following issue:

1. httpx AsyncClient maintains a connection pool with keepalive connections
2. When `keepalive_expiry=5.0`, idle connections are closed after 5 seconds
3. Ad tracking events (impression, quartiles) can be spaced more than 5 seconds apart
4. When the tracker tried to reuse connections after the 5-second window, it encountered stale/closed connections
5. This led to tracking failures or silent drops

## Solution
Increased `keepalive_expiry` to more appropriate values:

- **Main HTTP Client**: 5.0s → **30.0s** (6x increase)
  - Used for VAST ad requests
  - More aggressive reconnection is acceptable

- **Tracking HTTP Client**: 5.0s → **300.0s** (60x increase, 5 minutes)
  - Used for tracking pixels (impression, quartiles, etc.)
  - Needs longer keepalive since tracking events are intermittent
  - Prevents connection thrashing during normal playback gaps

## Changes Made

### 1. Code Defaults (`src/vast_client/http_client_manager.py`)
```python
# Before
"keepalive_expiry": _get("keepalive_expiry", 5.0),

# After
"keepalive_expiry": _get("keepalive_expiry", 30.0 if kind == "main" else 300.0),
```

### 2. Configuration (`settings/config.yaml`)
```yaml
http:
  keepalive_expiry: 30.0  # Changed from 5.0
  tracking:
    verify_ssl: false
    keepalive_expiry: 300.0  # Added tracking-specific override
```

## Verification
```bash
$ python3 -c "from src.vast_client.http_client_manager import _load_http_config; \
  print('Main:', _load_http_config('main')['keepalive_expiry'], 's'); \
  print('Tracking:', _load_http_config('tracking')['keepalive_expiry'], 's')"

Main: 30.0 s
Tracking: 300.0 s
```

## Impact
- ✅ Prevents connection pool exhaustion
- ✅ Reduces connection churn for tracking requests
- ✅ Allows tracking events spaced up to 5 minutes apart
- ✅ No breaking changes to API or behavior
- ⚠️ Slightly more persistent connections (acceptable tradeoff)

## Testing
After deploying this fix, monitor:
1. Tracking success rates over time
2. Connection pool metrics
3. No tracking gaps longer than 5 minutes

## Deployment
1. Pull latest changes from main branch
2. Restart middleware service to pick up new configuration
3. Monitor logs for successful tracking events

## Related Files
- `src/vast_client/http_client_manager.py` - Code defaults
- `settings/config.yaml` - YAML configuration
- `src/vast_client/tracker.py` - Tracking implementation
