# YAML Provider Configuration - Quick Reference

## Adding a New Provider (No Code Required!)

### 1. Edit `settings/config.yaml`

```yaml
providers:
  my_provider:
    name: "My Ad Provider"
    description: "Custom ad provider integration"
    
    http_client:
      base_url: "https://api.myprovider.com/vast"
      base_params:
        api_key: "your_key"
        format: "vast3"
      dynamic_params:
        device_id: "${device_serial}"
        user: "${user_agent}"
      base_headers:
        Accept: "application/xml"
      dynamic_headers:
        X-Device-ID: "${device_serial}"
      encoding_config:
        device_id: false
    
    context_preparation:
      device_serial:
        type: "uuid_multi_fields"
        fields: ["MY_PROVIDER", "device_macaddr"]
    
    tracker:
      macro_mapping: {}
      static_macros:
        AD_SERVER: "My Provider"
    
    playback:
      interruption_rules:
        start: {probability: 0.10, min_offset_sec: 0, max_offset_sec: 2}
```

### 2. Use Immediately

```python
from vast_client import build_provider_client

client = await build_provider_client("my_provider", ad_request)
```

That's it! No Python code changes needed.

---

## Template Syntax Cheat Sheet

| Pattern | Example | Result |
|---------|---------|--------|
| Simple | `${user_id}` | Direct value |
| Nested | `${ext.channel.name}` | Dot-notation path |
| Default | `${type\|preroll}` | Fallback if missing |
| Multiple | `${user}-${device}` | Multiple substitutions |

---

## Common Patterns

### Device Serial Generation
```yaml
context_preparation:
  device_serial:
    type: "uuid_multi_fields"
    fields:
      - "PROVIDER_PREFIX"  # Static
      - "device_macaddr"   # From ad_request
      - "user_agent"       # From ad_request
```

### Channel Data Extraction
```yaml
context_preparation:
  channel_extraction:
    name: "ext.channel_to.display_name"
    category: "ext.channel_to.iptvorg_categories"
```
Then use: `${channel.name}` in templates

### IP Pool Selection
```yaml
ip_pools:
  - name: "datacenter"
    strategy: "random"
    ips: ["1.2.3.4", "5.6.7.8"]
    fallback: "1.2.3.4"

context_preparation:
  ip_selection:
    pool: "datacenter"
```
Then use: `${selected_ip}` in headers

### JSON Parameters
```yaml
dynamic_params:
  metadata:
    type: "json"
    value:
      key1: "value1"
      key2: "value2"
```
Result: `?metadata={"key1":"value1","key2":"value2"}`

### Preserve Unicode/Cyrillic
```yaml
base_params:
  city: "Санкт-Петербург"

encoding_config:
  city: false  # Don't URL-encode

### Auto Macro Mapping
```yaml
tracker:
  macro_mapping:
    # Simple: param_name: MACRO_NAME maps to ad_request.param_name
    device_serial: DEVICE_SERIAL  # ad_request.device_serial
    city: CITY                     # ad_request.city
    
    # Nested paths also supported
    channel_name: CHANNEL_NAME    # ad_request.ext.channel_to.name
```

No need to write `"${ad_request.device_serial}"` - it's automatic!
```

---

## API Quick Reference

### Build Provider Client
```python
from vast_client import build_provider_client

client = await build_provider_client(
    provider="global",     # Provider name from YAML
    ad_request={...},      # Context data
    settings=None          # Optional settings override
)
```

### Alternative Factory
```python
from vast_client import EmbedHttpClient

client = await EmbedHttpClient.from_provider_config(
    "global", 
    ad_request
)
```

### Use Client
```python
# Build URL
url = client.build_url()
url_with_extra = client.build_url({"extra_param": "value"})

# Get headers
headers = client.get_headers()
headers_with_extra = client.get_headers({"Extra-Header": "value"})

# Convert formats
config_dict = client.to_dict()
vast_config = client.to_vast_config()

# Fluent API
new_client = client.with_params(param1="value1")
new_client = client.with_headers(Header1="value1")
new_client = client.with_url("https://new-url.com")
```

### Low-Level Loader
```python
from vast_client import ProviderConfigLoader

loader = ProviderConfigLoader()

# Get provider config
config = loader.get_provider_config("global")

# Prepare context
context = loader.prepare_context("global", ad_request)

# Build HTTP config
http_config = loader.build_http_client_config("global", ad_request)
```

### Template Resolution
```python
from vast_client import TemplateResolver

# Resolve single template
result = TemplateResolver.resolve("${user}", context)

# Resolve dictionary
data = {"title": "${user}'s profile"}
result = TemplateResolver.resolve_dict(data, context)
```

---

## Pre-configured Providers

| Provider | Endpoint | Use Case |
|----------|----------|----------|
| `global` | g.adstrm.ru/vast3 | AdStream Global CTV |
| `tiger` | t.adstrm.ru/vast3 | AdStream Tiger CTV |
| `leto` | ssp.rambler.ru/vapirs | Rambler SSP |
| `yandex` | yandex.ru/ads/adfox/... | Yandex AdFox |

---

## Troubleshooting

### Error: Provider not found
**Problem:** `ValueError: Provider 'xyz' not found`  
**Solution:** Check provider name exists in `settings/config.yaml`

### Error: Template not resolved
**Problem:** URL contains `${variable}`  
**Solution:** Ensure ad_request has the required field:
```python
ad_request = {
    "ext": {
        "channel_to": {
            "display_name": "Required Value"
        }
    }
}
```

### Error: Missing context variable
**Problem:** Template uses `${channel.name}` but not available  
**Solution:** Add `channel_extraction` in `context_preparation`:
```yaml
context_preparation:
  channel_extraction:
    name: "ext.channel_to.display_name"
```

---

## Migration from Old Code

### Before (Hardcoded)
```python
from ctv_middleware.vast_helpers import build_global_client
client = await build_global_client(ad_request)
```

### After (YAML-based)
```python
from vast_client import build_provider_client
client = await build_provider_client("global", ad_request)
```

---

## Documentation Links

- **Full Guide:** `YAML_PROVIDER_CONFIG_GUIDE.md`
- **Examples:** `examples/yaml_provider_config_example.py`
- **Implementation:** `YAML_IMPLEMENTATION_COMPLETE.md`
- **Config Schema:** `settings/config.yaml`
