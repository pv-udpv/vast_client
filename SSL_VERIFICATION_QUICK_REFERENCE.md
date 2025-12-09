# SSL/TLS Verification - Quick Reference

## One-Liner Examples

```python
# Production (recommended) - no extra config needed
client = VastClient("https://ads.example.com/vast")

# Development - disable SSL verification
client = VastClient("https://ads.example.com/vast", ssl_verify=False)

# Custom CA - internal certificate authority
client = VastClient("https://ads.example.com/vast", ssl_verify="/etc/ssl/ca.crt")
```

## Configuration Objects

```python
# Using VastClientConfig
config = VastClientConfig(ssl_verify=False)
client = VastClient(config)
```

## SSL Verification Modes

| Mode | Syntax | Use Case |
|------|--------|----------|
| **Enabled** | `ssl_verify=True` | ✅ Production (default) |
| **Disabled** | `ssl_verify=False` | ⚠️ Development only |
| **Custom CA** | `ssl_verify="/path/ca"` | ✅ Internal CAs |

## Configuration Priority

```
VastClient(config, ssl_verify=VALUE)
      ↓
    VALUE (highest priority)
      ↓
    config.ssl_verify (if present)
      ↓
    True (default)
```

## Environment-Based

```python
import os
ssl_verify = True if os.getenv("ENV") == "prod" else False
client = VastClient("https://ads.example.com/vast", ssl_verify=ssl_verify)
```

## HTTP Client Caching

```python
# Different ssl_verify = different HTTP client (separate connection pool)
client1 = get_main_http_client(ssl_verify=True)   # HTTP client 1
client2 = get_main_http_client(ssl_verify=False)  # HTTP client 2
client3 = get_main_http_client(ssl_verify=True)   # Same as client1 (cached)
```

## Security Reminders

✅ **DO:**
- Use `ssl_verify=True` in production
- Use custom CA bundles for internal deployments
- Store paths in environment variables

❌ **DON'T:**
- Use `ssl_verify=False` in production
- Store certificate paths in code
- Ignore SSL warnings

## Documentation

- **Full Guide**: [SSL_VERIFICATION_GUIDE.md](SSL_VERIFICATION_GUIDE.md)
- **Implementation**: [SSL_VERIFICATION_IMPLEMENTATION_SUMMARY.md](SSL_VERIFICATION_IMPLEMENTATION_SUMMARY.md)
- **Complete**: [SSL_VERIFICATION_COMPLETE.md](SSL_VERIFICATION_COMPLETE.md)
- **README**: See Configuration section in [README.md](README.md)

## Code Changes

**Modified Files:**
- `src/vast_client/config.py` - Added `ssl_verify` field
- `src/vast_client/http_client_manager.py` - Updated caching
- `src/vast_client/client.py` - Integrated ssl_verify

**New Files:**
- `SSL_VERIFICATION_GUIDE.md` - Comprehensive guide
- `SSL_VERIFICATION_IMPLEMENTATION_SUMMARY.md` - Technical details
- `SSL_VERIFICATION_COMPLETE.md` - Complete summary
- `SSL_VERIFICATION_QUICK_REFERENCE.md` - This file

## Backward Compatibility

✅ **100% compatible** - All existing code works unchanged

## Testing

✅ **All tests passing (7/7)**

```bash
python test_ssl_verify.py
```

## Type Hints

```python
ssl_verify: bool | str = True  # True, False, or path string
```

## Quick Troubleshooting

**SSL Certificate Failed?**
```python
# Try with custom CA
client = VastClient(url, ssl_verify="/path/to/ca-bundle.crt")
```

**Development Self-Signed Cert?**
```python
# Disable verification (development only!)
client = VastClient(url, ssl_verify=False)
```

**Production Deployment?**
```python
# Use default (or explicit True)
client = VastClient(url)  # ssl_verify=True by default
```

---

**For detailed information, see [SSL_VERIFICATION_GUIDE.md](SSL_VERIFICATION_GUIDE.md)**
