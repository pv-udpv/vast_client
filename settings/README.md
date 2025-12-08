# VAST Client Settings Configuration

This directory contains YAML-based configuration files for the VAST Client with support for:

- **Multi-environment configurations** (development, production, testing)
- **Template variable substitution** from `ad_request` context
- **Provider-specific settings** (Global, Tiger, Leto, Yandex, Google)
- **Hierarchical configuration merging**
- **Type-safe settings** via Pydantic

## Configuration Files

### Base Configuration
- `config.yaml` - Base configuration for all environments

### Environment-Specific Configurations
- `config.production.yaml` - Production overrides
- `config.testing.yaml` - Testing/CI overrides
- `config.development.yaml` - Development overrides (optional)

## Template Variable Syntax

Configuration values support template variables that are substituted at runtime from the `ad_request` context:

```yaml
# Syntax: ${variable|default_value}
http:
  default_headers:
    User-Agent: "${ad_request.user_agent|VAST-Client/1.0.0}"
    X-Device-Serial: "${ad_request.device_serial}"
```

### Supported Template Patterns

- `${ad_request.property}` - Direct property access
- `${ad_request.property|default}` - With default value
- `${ad_request.ext.nested.property}` - Nested property access

### Available Context Variables

From `ad_request`:
- `device_serial` - Device serial number
- `user_agent` - HTTP User-Agent string
- `request_id` - Unique request identifier
- `session_id` - Playback session identifier
- `platform` - Platform type (ctv, mobile, web)
- `device_type` - Device type
- `app_version` - Application version
- `ext.channel_to.title` - Channel name (nested)
- `ext.channel_to.category` - Channel category (nested)

## Usage Examples

### Basic Usage

```python
from config import get_settings

# Load settings (cached)
settings = get_settings()

print(settings.environment)  # 'development'
print(settings.vast_client.enable_tracking)  # True
```

### With Ad Request Context

```python
from config import get_settings

settings = get_settings()

# Create context-aware settings
ad_request = {
    'user_agent': 'Mozilla/5.0 (SmartTV; Linux)',
    'device_serial': 'ABC123456789',
    'request_id': 'req-uuid-1234',
    'platform': 'ctv',
    'ext': {
        'channel_to': {
            'title': 'HBO',
            'category': 'entertainment'
        }
    }
}

# Substitute template variables
context_settings = settings.with_context(ad_request=ad_request)

# Now headers have real values
print(context_settings.http.default_headers['User-Agent'])
# Output: 'Mozilla/5.0 (SmartTV; Linux)'

print(context_settings.http.context_headers['X-Device-Serial'])
# Output: 'ABC123456789'
```

### Provider-Specific Configuration

```python
from config import get_settings

settings = get_settings()

# Get Tiger provider config
tiger_config = settings.get_provider_config('tiger')
print(tiger_config['tracker']['macro_mapping'])
# {'city_name': 'CITY', 'city_code': 'CITY_CODE', ...}

# Access provider interruption rules
interruption = tiger_config['playback']['interruption_rules']['start']
print(interruption['probability'])  # 0.08
```

### Environment Variable Overrides

Configuration can be overridden via environment variables using the `VAST_` prefix:

```bash
# Override environment
export VAST_ENVIRONMENT=production

# Override specific settings
export VAST_DEBUG=false
export VAST_LOG_LEVEL=INFO
export VAST_VAST_CLIENT__ENABLE_TRACKING=true
export VAST_HTTP__TIMEOUT=15.0

# Nested settings use double underscores
export VAST_HTTP__DEFAULT_HEADERS__USER_AGENT="CustomAgent/1.0"
```

### Reload Settings

```python
from config import reload_settings

# Clear cache and reload from files
settings = reload_settings()
```

## Configuration Structure

```yaml
# Top-level settings
environment: development
debug: true
log_level: DEBUG

# VAST Client specific
vast_client:
  enable_tracking: true
  enable_parsing: true
  parser:
    # Parser configuration
  tracker:
    # Tracker configuration
  playback:
    # Playback configuration

# HTTP Client configuration
http:
  timeout: 30.0
  default_headers: {}
  context_headers: {}  # Applied with ad_request context
  base_params: {}
  context_params: {}   # Applied with ad_request context

# Logging configuration
logging:
  version: 1
  handlers: {}
  loggers: {}

# Provider-specific configurations
providers:
  global: {}
  tiger: {}
  leto: {}
  yandex: {}
  google: {}
  custom: {}

# Template engine settings
templates:
  variable_pattern: '\$\{([^}|]+)(?:\|([^}]+))?\}'
  context_paths: {}
```

## Integration with VAST Client

```python
import httpx
from config import get_settings
from vast_client import VastClient
from vast_client.config import VastClientConfig

# Load settings
settings = get_settings()

# Create ad request context
ad_request = {
    'user_agent': 'Mozilla/5.0',
    'device_serial': 'DEVICE123',
    'platform': 'ctv'
}

# Get context-aware settings
context_settings = settings.with_context(ad_request=ad_request)

# Create HTTP client with configured headers
http_client = httpx.AsyncClient(
    timeout=context_settings.http.timeout,
    headers=context_settings.http.default_headers,
    verify=context_settings.http.verify_ssl
)

# Create VAST client
vast_client = VastClient(
    "https://ads.example.com/vast",
    ctx=ad_request,
    client=http_client
)

# Make VAST request
ad_data = await vast_client.request_ad()
```

## Writing Custom Configurations

Create a new environment config:

```yaml
# settings/config.staging.yaml
environment: staging
debug: false
log_level: INFO

vast_client:
  playback:
    enable_session_persistence: true

http:
  timeout: 15.0
  verify_ssl: true
```

Load it:

```bash
export VAST_ENVIRONMENT=staging
python -m vast_client
```

## Best Practices

1. **Use template variables** for dynamic values from ad_request
2. **Set defaults** using `${var|default}` syntax
3. **Keep secrets out** of config files (use environment variables)
4. **Override per environment** rather than duplicating entire configs
5. **Validate settings** at application startup
6. **Cache settings** using `get_settings()` (auto-cached)
7. **Reload only when needed** via `reload_settings()`

## Troubleshooting

### Settings not loading
```python
from pathlib import Path
from config import get_settings

# Explicitly specify config path
config_path = Path(__file__).parent / "settings" / "config.yaml"
settings = get_settings(config_path)
```

### Template variables not substituting
```python
# Ensure you call with_context()
settings = get_settings()
context_settings = settings.with_context(ad_request={'user_agent': 'Mozilla'})
```

### Environment not detected
```bash
# Set environment explicitly
export VAST_ENVIRONMENT=production
```
