# VAST Parser Usage Guide

## Quick Start

### Legacy Mode (Backward Compatible)

```python
from vast_parser import VASTParser

parser = VASTParser()
result = parser.parse(vast_xml_string)

# Access results
for impression in result['impressions']:
    track_impression(impression)
```

### Enhanced Mode (New Features)

```python
from vast_parser import EnhancedVASTParser
import yaml

# Load configuration
with open('configs/vast_config_adaptive_streaming.yaml') as f:
    config = yaml.safe_load(f)

# Parse with filtering and sorting
parser = EnhancedVASTParser(config)
result = parser.parse(vast_xml_string)

# Access filtered results
hd_video = result['adaptive']['hd'][0]
mobile_video = result['adaptive']['mobile'][0]

# Use in player
player.add_variant(hd_video['url'], hd_video['bitrate'])
```

## Configuration Examples

### Device Targeting

```yaml
media_files:
  desktop:
    xpath: "//vast:MediaFile[@width >= '1280']"
    limit: 1
  
  mobile:
    xpath: "//vast:MediaFile[@width <= '640']"
    limit: 1
```

### Codec Selection

```yaml
media_files:
  h264:
    xpath: "//vast:MediaFile[@codec='H.264']"
  
  hevc:
    xpath: "//vast:MediaFile[@codec='HEVC']"
```

## XPath Filtering

### Supported Attributes
- `@type` - Media type (e.g., 'video/mp4')
- `@width` - Video width in pixels
- `@height` - Video height in pixels
- `@bitrate` - Bitrate in kbps
- `@codec` - Video codec (e.g., 'H.264', 'HEVC')
- `@delivery` - Delivery method (e.g., 'progressive')

### Supported Comparisons
- `=` - Equal to
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `contains()` - Contains substring
- `and` / `or` / `not` - Logical operators

### Examples

```xpath
# Only MP4 videos
//vast:MediaFile[@type='video/mp4']

# Only HD videos
//vast:MediaFile[@width >= '1280']

# High bitrate MP4 videos
//vast:MediaFile[@type='video/mp4'][@bitrate >= '2000']

# Videos with H.264 codec
//vast:MediaFile[contains(@codec, 'H.264')]
```

## Merge Strategies

### append
Add multiple values to a list:

```yaml
tracking:
  impressions:
    xpath: "//vast:Impression/text()"
    merge: append  # Collects all impressions
```

### replace
Keep only the last value:

```yaml
tracking:
  error:
    xpath: "//vast:Error/text()"
    merge: replace  # Only last error
```

### update
Merge dictionary values:

```yaml
metadata:
  ad_system:
    xpath: "//vast:AdSystem"
    merge: update  # Merges with existing
```

## Sorting and Limiting

```yaml
media_files:
  best_quality:
    xpath: "//vast:MediaFile"
    sort_by: "bitrate"        # Sort by this field
    sort_order: "desc"         # Descending order
    limit: 1                   # Keep only first
```

## Testing

Run the test suite:

```bash
pytest tests/test_vast_parser.py -v
```

Expected output:
```
17 passed in 0.52s ✅
```

## API Reference

### VASTParser

```python
parser = VASTParser(namespaces=None)
result = parser.parse(xml_string: str) -> Dict[str, Any]
result = parser.parse_file(filepath: str) -> Dict[str, Any]
```

### EnhancedVASTParser

```python
parser = EnhancedVASTParser(config: Dict, namespaces=None)
result = parser.parse(xml_string: str) -> Dict[str, Any]
json_str = parser.to_json(result: Dict) -> str
```

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
