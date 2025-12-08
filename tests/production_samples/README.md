# Production VAST Samples

This directory contains VAST samples extracted from real production environments.

## Sources

### g.adstrm.ru (Adstream)
- **Endpoint**: `https://g.adstrm.ru/vast3`
- **VAST Versions**: 3.0, 4.0
- **Characteristics**:
  - Frequently returns 204 No Content when no ads available
  - Supports Cyrillic characters in URL parameters
  - Uses standard VAST macro formats: `[MACRO]` and `${MACRO}`
  - Typical ad durations: 5, 10, 15, 20, 30 seconds

## Directory Structure

```
production_samples/
├── __init__.py
├── README.md                       # This file
├── production_metadata.json        # Metadata about samples
├── test_production_samples.py      # Production sample tests
│
└── g.adstrm.ru/                   # Adstream samples (to be added)
    ├── vast3_sample_001.xml
    ├── vast3_sample_002.xml
    └── ...
```

## Sample Collection

### From Production Logs

Samples are extracted from production logs in `~/middleware/logs/*.jsonl`:

**Log Files**:
- `vast_client.jsonl` - VAST client requests/responses (10MB, 12k+ events)
- `vast_tracking.jsonl` - Tracking pixel requests (650KB)
- `vast_player.jsonl` - Playback events (200KB)
- `app.jsonl` - Application-level logs (8.6MB)
- `exceptions.jsonl` - Error logs (8.6MB)

**Key Metrics from Logs**:
- Total VAST requests logged: 11,685+
- Successful responses: 903
- Parser invocations: 903
- Tracker creations: 903
- Empty/204 responses: Frequent

### Extraction Process

To extract production samples:

```bash
# Extract VAST XML responses from logs
cd ~/middleware/logs
grep "response_preview" vast_client.jsonl | \
  jq -r '.response_preview' | \
  grep "<?xml" > sample.xml

# Or find specific provider responses
grep "g.adstrm.ru" app.jsonl | \
  jq -r 'select(.vast_response) | .vast_response' \
  > production_samples/g.adstrm.ru/sample_001.xml
```

### Anonymization

All samples are anonymized:
- Device serials removed/masked
- IP addresses removed
- User-specific identifiers replaced
- Tracking URLs preserved for testing

## Production Test Coverage

### Test Cases

1. **Provider-Specific Tests**
   - g.adstrm.ru VAST3 samples
   - Other production providers

2. **Version Coverage**
   - VAST 3.0 samples
   - VAST 4.0 samples

3. **Edge Cases from Production**
   - 204 No Content responses
   - Cyrillic URL parameters
   - Various duration formats
   - Macro pattern variations

4. **Integration Scenarios**
   - Typical request → parse → track workflow
   - Empty response handling
   - Error recovery

### Running Production Tests

```bash
# Run all production sample tests
pytest tests/production_samples/

# Run specific provider tests
pytest tests/production_samples/test_production_samples.py::TestProductionSamples::test_adstream_vast3_samples

# With verbose output
pytest tests/production_samples/ -v
```

## Adding New Samples

### Manual Addition

1. Extract VAST XML from production logs
2. Anonymize personal data
3. Save to provider subdirectory:
   ```bash
   mkdir -p g.adstrm.ru
   echo '<VAST>...</VAST>' > g.adstrm.ru/sample_XXX.xml
   ```
4. Update `production_metadata.json`
5. Run tests to verify:
   ```bash
   pytest tests/production_samples/
   ```

### Automated Extraction Script

Create `extract_samples.py`:

```python
#!/usr/bin/env python3
"""Extract VAST samples from production logs."""

import json
import re
from pathlib import Path

def extract_vast_responses(log_file, output_dir, provider):
    """Extract VAST XML responses from logs."""
    output_dir = Path(output_dir) / provider
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(log_file) as f:
        count = 0
        for line in f:
            try:
                data = json.loads(line)
                if 'response_preview' in data:
                    xml = data['response_preview']
                    if xml and xml.startswith('<?xml'):
                        # Anonymize and save
                        count += 1
                        output_file = output_dir / f"sample_{count:03d}.xml"
                        output_file.write_text(xml)
            except:
                continue
        
    print(f"Extracted {count} samples to {output_dir}")

# Usage
extract_vast_responses(
    '~/middleware/logs/vast_client.jsonl',
    'tests/production_samples',
    'g.adstrm.ru'
)
```

## Production Characteristics

### g.adstrm.ru Behavior

Based on production logs analysis:

1. **Response Patterns**
   - 200 OK with VAST XML (~77% of requests with valid responses)
   - 204 No Content (frequent when no ads available)
   - Average response size: 3KB
   - Response time: <500ms typically

2. **VAST Structure**
   - Standard IAB VAST 3.0/4.0 structure
   - Inline ads (not wrappers)
   - Linear video ads
   - Standard tracking events (start, quartiles, complete)

3. **URL Parameters**
   - Support for Cyrillic characters (category, genre, etc.)
   - Standard VAST macros in tracking URLs
   - Device and placement information

4. **Device Context**
   - Primary: Smart TV devices
   - Placement: Switchroll (mid-roll/pre-roll)
   - User-Agents: WebOS, Android TV, various Smart TV platforms

## Best Practices

### Test Data Management

1. **Version Control**
   - Commit anonymized samples to git
   - Use `.gitignore` for raw/sensitive data
   - Keep samples small (<10KB each)

2. **Sample Selection**
   - Include edge cases (empty, malformed)
   - Cover different VAST versions
   - Representative of production volume

3. **Updates**
   - Refresh samples periodically (quarterly)
   - Add new providers as needed
   - Update metadata with new findings

### CI/CD Integration

Production samples are optional in CI:

```yaml
# .github/workflows/test.yml
- name: Run production samples tests
  run: pytest tests/production_samples/
  continue-on-error: true  # Optional if samples not available
```

## Troubleshooting

### No Samples Available

If tests skip due to missing samples:

```bash
# Check directory exists
ls -la tests/production_samples/g.adstrm.ru/

# Extract from logs
python extract_samples.py

# Or add manually
echo '<?xml version="1.0"?><VAST>...</VAST>' > \
  tests/production_samples/g.adstrm.ru/sample_001.xml
```

### Sample Parsing Failures

If production samples fail to parse:

1. Check XML validity: `xmllint --noout sample.xml`
2. Enable parser recovery: `recover_on_error=True`
3. Check for encoding issues
4. Review parser logs

## Contributing

To contribute production samples:

1. Extract samples from your production environment
2. **Anonymize all personal/sensitive data**
3. Add to appropriate provider directory
4. Update `production_metadata.json`
5. Add tests if needed
6. Submit pull request

**Important**: Never commit:
- Personal data (IPs, device IDs, etc.)
- Authentication tokens
- Proprietary/confidential information
