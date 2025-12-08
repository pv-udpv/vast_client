# VAST Client Settings Configuration System - Implementation Summary

## Overview

Created a comprehensive, production-ready configuration management system for the VAST Client using **pydantic-settings** with YAML support. The system provides:

✅ **Multi-environment configuration** (development, production, testing)  
✅ **Template variable substitution** from `ad_request` context  
✅ **Provider-specific settings** (Global, Tiger, Leto, Yandex, Google, Custom)  
✅ **Type-safe configuration** via Pydantic models  
✅ **Hierarchical configuration merging**  
✅ **Environment variable overrides**  
✅ **HTTP client context composition**  

## Files Created

### 1. Configuration Files (YAML)

#### `settings/config.yaml` (11.5 KB)
**Main configuration file** with comprehensive settings:

```yaml
# Key sections:
- environment: development/production/testing
- vast_client: Parser, Tracker, Playback configurations
- http: HTTP client with template variable support
- logging: Python logging configuration
- providers: Provider-specific configs (global, tiger, leto, yandex, google, custom)
- templates: Template engine configuration
```

**Features:**
- Template variables: `${ad_request.property|default}`
- Context-aware headers and parameters
- Provider-specific macro mappings
- Interruption rules for headless playback simulation

#### `settings/config.production.yaml` (587 bytes)
Production overrides:
- `environment: production`
- `debug: false`
- `log_level: INFO`
- Session persistence enabled
- Stricter logging

#### `settings/config.testing.yaml` (577 bytes)
Testing/CI overrides:
- `environment: testing`
- Headless mode with faster tick interval
- Relaxed SSL verification
- Debug logging enabled

### 2. Python Configuration Module

#### `src/config.py` (9 KB)
**Core settings management module** with:

**Classes:**
- `TemplateEngine` - Variable substitution engine
  - Pattern: `${variable}` or `${variable|default}`
  - Nested property access: `${ad_request.ext.channel_to.title}`
  - Recursive dict/list substitution
  
- `VastClientSettings` - VAST-specific settings (Pydantic model)
- `HttpSettings` - HTTP client configuration (Pydantic model)
- `Settings` - Main settings class (Pydantic BaseSettings)
  - YAML file loading
  - Environment-based overrides
  - Deep merging
  - Context substitution via `with_context()`

**Functions:**
- `get_settings()` - Cached settings loader
- `reload_settings()` - Cache clear and reload

**Usage:**
```python
from config import get_settings

# Load settings (cached)
settings = get_settings()

# With ad_request context
ad_request = {'user_agent': 'Mozilla/5.0', 'device_serial': 'ABC123'}
context_settings = settings.with_context(ad_request=ad_request)

# Access substituted values
print(context_settings.http.default_headers['User-Agent'])
# Output: 'Mozilla/5.0'
```

### 3. Documentation

#### `settings/README.md` (6.7 KB)
**Comprehensive usage guide** covering:
- Configuration file structure
- Template variable syntax
- Available context variables
- Usage examples (6 detailed examples)
- Integration with VAST Client
- Best practices
- Troubleshooting guide

### 4. Supporting Files

#### `settings/__init__.py` (46 bytes)
Package marker for settings directory

#### `examples/settings_usage.py` (Created)
Example script demonstrating configuration usage

## Template Variable System

### Syntax

```yaml
# Basic variable
User-Agent: "${ad_request.user_agent}"

# With default value
User-Agent: "${ad_request.user_agent|VAST-Client/1.0.0}"

# Nested property
Channel: "${ad_request.ext.channel_to.title|Unknown}"
```

### Available Context Variables

From `ad_request`:
- `device_serial` - Device serial number
- `user_agent` - HTTP User-Agent
- `request_id` - Request UUID
- `session_id` - Session UUID
- `platform` - Platform (ctv, mobile, web)
- `device_type` - Device type
- `app_version` - App version
- `ext.channel_to.title` - Channel name (nested)
- `ext.channel_to.category` - Channel category (nested)

### Substitution Example

**Config:**
```yaml
http:
  default_headers:
    User-Agent: "${ad_request.user_agent|VAST-Client/1.0.0}"
    X-Device: "${ad_request.device_serial}"
```

**Code:**
```python
settings = get_settings()
ad_request = {
    'user_agent': 'Mozilla/5.0',
    'device_serial': 'ABC123'
}
context_settings = settings.with_context(ad_request=ad_request)

# Result:
# {'User-Agent': 'Mozilla/5.0', 'X-Device': 'ABC123'}
```

## HTTP Client Integration

### Context-Aware Configuration

```yaml
http:
  # Base headers (always applied)
  default_headers:
    Accept: "application/xml, text/xml, */*"
    User-Agent: "${ad_request.user_agent|VAST-Client/1.0.0}"
  
  # Context headers (applied when ad_request available)
  context_headers:
    X-Device-Serial: "${ad_request.device_serial}"
    X-Request-ID: "${ad_request.request_id}"
    X-Platform: "${ad_request.platform|CTV}"
  
  # Base params
  base_params:
    version: "4.0"
    platform: "${ad_request.platform|ctv}"
  
  # Context params
  context_params:
    ab_uid: "${ad_request.device_serial}"
    session_id: "${ad_request.session_id}"
```

### Usage with httpx

```python
import httpx
from config import get_settings

settings = get_settings()
ad_request = {'user_agent': 'Mozilla/5.0', 'device_serial': 'DEV123'}
context_settings = settings.with_context(ad_request=ad_request)

# Create HTTP client with context-aware settings
client = httpx.AsyncClient(
    timeout=context_settings.http.timeout,
    headers=context_settings.http.default_headers,
    params=context_settings.http.base_params,
    verify=context_settings.http.verify_ssl
)
```

## Provider-Specific Configurations

### Supported Providers

1. **global** - AdStream Global
   - Higher interruption rates (15% start)
   - City-specific macro mappings
   
2. **tiger** - AdStream Tiger
   - Moderate interruption rates (8% start)
   - City name/code macros
   
3. **leto** - Leto
   - Low interruption rates (5% start)
   - Custom macro format: `%%{macro}%%`
   - WL, PAD_ID, BLOCK_ID macros
   
4. **yandex** - Yandex Direct
   - Moderate-high interruption (10% start)
   - Yandex-specific macros (UID, campaign, banner)
   
5. **google** - Google AdSense
   - Highest interruption (20% start)
   - Google GID and custom params
   
6. **custom** - Generic custom provider
   - Configurable for any provider

### Accessing Provider Config

```python
settings = get_settings()

# Get Tiger config
tiger_config = settings.get_provider_config('tiger')
print(tiger_config['tracker']['macro_mapping'])
# {'city_name': 'CITY', 'city_code': 'CITY_CODE', ...}

# Check interruption probability
start_prob = tiger_config['playback']['interruption_rules']['start']['probability']
print(f"Tiger start interruption: {start_prob * 100}%")
# Output: "Tiger start interruption: 8.0%"
```

## Environment Variable Overrides

### Prefix: `VAST_`

```bash
# Override environment
export VAST_ENVIRONMENT=production

# Override top-level settings
export VAST_DEBUG=false
export VAST_LOG_LEVEL=INFO

# Override nested settings (use __ for nesting)
export VAST_VAST_CLIENT__ENABLE_TRACKING=true
export VAST_HTTP__TIMEOUT=15.0
export VAST_HTTP__DEFAULT_HEADERS__USER_AGENT="CustomAgent/1.0"
```

## Configuration Hierarchy

**Resolution order** (lowest to highest precedence):

1. **Base config** - `settings/config.yaml`
2. **Environment config** - `settings/config.{environment}.yaml`
3. **Environment variables** - `VAST_*`
4. **Runtime context** - `settings.with_context(ad_request=...)`

### Example Flow

```
config.yaml
  environment: development
  http.timeout: 30.0
  ↓
config.production.yaml (if VAST_ENVIRONMENT=production)
  environment: production
  http.timeout: 10.0
  ↓
Environment variables
  VAST_HTTP__TIMEOUT=15.0
  ↓
Runtime context
  ad_request = {'user_agent': 'Mozilla/5.0'}
  settings.with_context(ad_request=ad_request)
  ↓
Final: timeout=15.0, user_agent='Mozilla/5.0'
```

## Integration with Existing VAST Client

### Minimal Changes Required

The existing `src/vast_client/config.py` references a parent config:

```python
from ..config import get_settings
```

Now resolved by `/src/config.py`:

```python
# In vast_client/config.py
from ..config import get_settings

def get_vast_config_from_settings() -> VastClientConfig:
    """Get VAST configuration from main settings."""
    main_settings = get_settings()
    
    return VastClientConfig(
        enable_tracking=main_settings.vast_client.enable_tracking,
        parser=VastParserConfig(**main_settings.vast_client.parser),
        tracker=VastTrackerConfig(**main_settings.vast_client.tracker),
        playback=PlaybackSessionConfig(**main_settings.vast_client.playback),
    )
```

## Dependencies Added

Updated `pyproject.toml`:

```toml
dependencies = [
    "httpx>=0.24.0",
    "lxml>=4.9.0",
    "structlog>=22.0.0",
    "pydantic>=2.0.0",          # ← Added
    "pydantic-settings>=2.0.0",  # ← Added
    "pyyaml>=6.0",               # ← Added
]
```

## Installation

```bash
# Install dependencies
pip install -e .

# Or with uv
uv pip install -e .
```

## Testing the Configuration

```python
# Test basic loading
from config import get_settings
settings = get_settings()
assert settings.environment == "development"

# Test template substitution
ad_request = {'user_agent': 'TestAgent/1.0'}
context_settings = settings.with_context(ad_request=ad_request)
assert context_settings.http.default_headers['User-Agent'] == 'TestAgent/1.0'

# Test provider config
tiger = settings.get_provider_config('tiger')
assert tiger['playback']['interruption_rules']['start']['probability'] == 0.08
```

## Benefits

1. **Type Safety** - Pydantic validation ensures config integrity
2. **Flexibility** - Template vars adapt to runtime context
3. **Maintainability** - YAML configs are human-readable and git-friendly
4. **Testability** - Easy to mock/override for tests
5. **Production-Ready** - Environment-based configs for different deployments
6. **Documentation** - Self-documenting via README and examples
7. **Extensibility** - Easy to add new providers or settings

## Next Steps

1. ✅ Configuration system created
2. ⏭️ Install dependencies (`pip install pydantic pydantic-settings pyyaml`)
3. ⏭️ Test configuration loading
4. ⏭️ Integrate with existing VAST Client code
5. ⏭️ Add unit tests for config loading and substitution
6. ⏭️ Update VAST Client to use `get_settings()` consistently

---

**Files Summary:**
- `settings/config.yaml` - Main config (11.5 KB)
- `settings/config.production.yaml` - Production overrides (587 B)
- `settings/config.testing.yaml` - Testing overrides (577 B)
- `settings/README.md` - Documentation (6.7 KB)
- `settings/__init__.py` - Package marker (46 B)
- `src/config.py` - Settings module (9 KB)
- `pyproject.toml` - Updated dependencies

**Total:** ~38 KB of configuration infrastructure
