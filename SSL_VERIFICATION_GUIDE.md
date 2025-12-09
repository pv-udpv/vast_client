# SSL/TLS Verification Configuration for VAST Client

## Overview

The VAST Client now supports flexible SSL/TLS verification configuration, enabling users to control how SSL certificates are validated during HTTP requests to VAST endpoints. This is particularly useful for:

- **Development environments** where self-signed certificates are used
- **Custom certificate authorities** that need CA bundle configuration
- **Testing scenarios** where SSL verification may need to be disabled
- **Production deployments** with strict certificate validation

## Configuration Methods

### Method 1: VastClientConfig

The recommended approach using the configuration object:

```python
from src.vast_client.config import VastClientConfig
from src.vast_client.client import VastClient

# Enable SSL verification (default)
config = VastClientConfig(ssl_verify=True)
client = VastClient(config)

# Disable SSL verification
config = VastClientConfig(ssl_verify=False)
client = VastClient(config)

# Use custom CA bundle
config = VastClientConfig(ssl_verify="/path/to/ca-bundle.crt")
client = VastClient(config)
```

### Method 2: VastClient Constructor with kwargs

Pass `ssl_verify` directly to the VastClient:

```python
from src.vast_client.client import VastClient

# Via kwargs
client = VastClient("https://ads.example.com/vast", ssl_verify=False)

# kwargs override config values
config = VastClientConfig(ssl_verify=True)
client = VastClient(config, ssl_verify=False)  # Uses False from kwargs
```

### Method 3: URL String Initialization

```python
from src.vast_client.client import VastClient

client = VastClient("https://ads.example.com/vast", ssl_verify="/etc/ssl/certs/ca-bundle.crt")
```

## ssl_verify Parameter Values

The `ssl_verify` parameter accepts three types of values:

### `ssl_verify=True` (Default)

Strictly validates SSL certificates against the system's certificate store:

```python
config = VastClientConfig(ssl_verify=True)
```

Use this in production environments.

### `ssl_verify=False`

Disables SSL certificate verification. **Use with caution** - only in development/testing:

```python
config = VastClientConfig(ssl_verify=False)
```

### `ssl_verify="/path/to/ca-bundle.crt"` (String path)

Uses a custom CA certificate bundle:

```python
config = VastClientConfig(ssl_verify="/etc/ssl/certs/custom-ca.crt")
```

This is useful when:
- Your organization uses an internal certificate authority
- You need to validate against a specific CA bundle
- You're working in an environment with non-standard certificate locations

## Implementation Details

### HTTP Client Caching Strategy

The VAST Client uses intelligent caching of HTTP clients based on the `ssl_verify` setting:

```python
from src.vast_client.http_client_manager import get_main_http_client, _main_http_clients

# First call creates a client
client1 = get_main_http_client(ssl_verify=True)

# Second call with same ssl_verify returns cached client
client2 = get_main_http_client(ssl_verify=True)
assert client1 is client2  # Same instance

# Different ssl_verify creates new client
client3 = get_main_http_client(ssl_verify=False)
assert client1 is not client3  # Different instance
```

This approach:
- Maximizes connection reuse for each verification mode
- Supports multiple verification modes in the same application
- Maintains separate connection pools per configuration

### Configuration Priority

When multiple ssl_verify values are provided, this priority is used:

1. **VastClient kwargs** (highest priority)
2. **VastClientConfig property** (if provided)
3. **Default value: True** (lowest priority)

```python
# Example: kwargs override config
config = VastClientConfig(ssl_verify=True)
client = VastClient(config, ssl_verify=False)
assert client.ssl_verify is False  # kwargs win
```

## Usage Examples

### Development Environment

```python
import asyncio
from src.vast_client.config import VastClientConfig
from src.vast_client.client import VastClient

async def dev_example():
    # Disable SSL verification for self-signed certificates
    config = VastClientConfig(
        provider="global",
        ssl_verify=False
    )
    
    client = VastClient(config)
    
    # Request ad - SSL certificate validation is skipped
    response = await client.request_ad(params={
        "user_id": "test123",
        "channel": "dev"
    })
    
    return response

# Run example
# asyncio.run(dev_example())
```

### Production Environment

```python
import asyncio
from src.vast_client.config import VastClientConfig
from src.vast_client.client import VastClient

async def prod_example():
    # Enable strict SSL verification
    config = VastClientConfig(
        provider="global",
        ssl_verify=True  # Or omit, as True is default
    )
    
    client = VastClient(config)
    
    # Request ad - SSL certificate is strictly validated
    response = await client.request_ad(params={
        "user_id": "prod_user",
        "channel": "live"
    })
    
    return response

# asyncio.run(prod_example())
```

### Custom CA Bundle

```python
import asyncio
from src.vast_client.config import VastClientConfig
from src.vast_client.client import VastClient

async def custom_ca_example():
    # Use organization's internal CA
    config = VastClientConfig(
        provider="tiger",
        ssl_verify="/opt/company/certs/internal-ca-bundle.crt"
    )
    
    client = VastClient(config)
    
    # Request ad - validates against custom CA
    response = await client.request_ad(params={
        "user_id": "employee123",
        "channel": "internal"
    })
    
    return response

# asyncio.run(custom_ca_example())
```

### Environment-based Configuration

```python
import os
from src.vast_client.config import VastClientConfig
from src.vast_client.client import VastClient

def create_client_from_env():
    """Create VastClient with settings from environment variables."""
    
    environment = os.getenv("APP_ENV", "development")
    provider = os.getenv("VAST_PROVIDER", "global")
    
    # Set ssl_verify based on environment
    if environment == "production":
        ssl_verify = True
    elif environment == "staging":
        ca_bundle = os.getenv("CA_BUNDLE_PATH")
        ssl_verify = ca_bundle if ca_bundle else True
    else:  # development
        ssl_verify = False
    
    config = VastClientConfig(
        provider=provider,
        ssl_verify=ssl_verify
    )
    
    return VastClient(config)
```

## Testing

The SSL verification configuration is tested in:

- Unit tests validate configuration storage and retrieval
- Integration tests verify HTTP client behavior with different settings
- HTTP client caching tests ensure proper cache key usage

Test the configuration manually:

```python
# Run tests
python test_ssl_verify.py
```

## Security Considerations

### Production Best Practices

✅ **DO:**
- Use `ssl_verify=True` (default) in production
- Validate certificates from trusted CAs
- Keep system certificate store updated
- Use custom CA bundles for internal deployments

❌ **DON'T:**
- Use `ssl_verify=False` in production (except temporary debugging)
- Ignore SSL certificate validation warnings
- Use self-signed certificates without proper validation
- Store certificate paths in code (use environment variables)

### Common Issues and Solutions

**Issue: "SSL: CERTIFICATE_VERIFY_FAILED"**

Solution: Check your CA bundle and ensure certificates are properly installed.

```python
# Try with custom CA bundle
config = VastClientConfig(
    ssl_verify="/etc/ssl/certs/ca-bundle.crt"
)
```

**Issue: Self-signed certificates in development**

Solution: Disable verification only in development.

```python
if os.getenv("ENV") == "development":
    ssl_verify = False
else:
    ssl_verify = True

config = VastClientConfig(ssl_verify=ssl_verify)
```

## API Reference

### VastClientConfig.ssl_verify

```python
@dataclass
class VastClientConfig:
    # SSL/TLS verification
    ssl_verify: bool | str = True  # True (verify), False (disable), or path to CA bundle
```

### get_main_http_client()

```python
def get_main_http_client(ssl_verify: bool | str = True) -> httpx.AsyncClient:
    """Get main HTTP client for VAST requests.
    
    Args:
        ssl_verify: SSL verification setting. Can be:
            - True (default): Verify SSL certificates
            - False: Disable SSL verification
            - str: Path to CA bundle file
    
    Returns:
        Configured httpx.AsyncClient instance
    """
```

## Performance Considerations

- SSL certificate validation adds minimal overhead
- CA bundle path validation happens at httpx client initialization
- Separate clients are cached for each ssl_verify configuration
- Connection pooling is maintained per configuration

## Migration Guide

If you have existing code, update as follows:

**Before (no SSL control):**
```python
client = VastClient("https://ads.example.com/vast")
```

**After (with SSL control):**
```python
# Option 1: Keep default (True)
client = VastClient("https://ads.example.com/vast")

# Option 2: Explicit configuration
config = VastClientConfig(ssl_verify=True)
client = VastClient(config)

# Option 3: Disable for development
client = VastClient("https://ads.example.com/vast", ssl_verify=False)
```

## Related Documentation

- [VastClient Documentation](./client_readme.md)
- [HTTP Client Manager](./http_client_manager_readme.md)
- [Configuration Guide](./config_guide.md)
- [Security Best Practices](./security.md)
