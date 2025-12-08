# Production Sample Extraction Guide

## Overview

This guide explains how to extract real VAST samples from production logs for testing.

## Prerequisites

- Production logs available at `~/middleware/logs/*.jsonl`
- Python 3.10+
- Write access to `tests/production_samples/`

## Quick Start

### Extract Samples

```bash
cd /home/pv/repos/vast_client/tests
python extract_production_samples.py
```

This will:
1. Read `~/middleware/logs/vast_client.jsonl`
2. Extract VAST XML responses
3. Anonymize personal data (device IDs, IPs, etc.)
4. Save to `tests/production_samples/g.adstrm.ru/`
5. Deduplicate based on content hash

### Run Tests

```bash
# Run production sample tests
pytest tests/production_samples/

# Run specific test
pytest tests/production_samples/test_production_samples.py::TestProductionSamples::test_adstream_vast3_samples
```

## Production Log Analysis

### Current Production Data (from ~/middleware/logs/)

Based on the logs at `~/middleware/logs/`:

**Log Files**:
- `vast_client.jsonl` - 10.3MB, 12,000+ events
- `vast_tracking.jsonl` - 653KB, tracking requests
- `vast_player.jsonl` - 202KB, playback events
- `app.jsonl` - 8.6MB, application logs
- `exceptions.jsonl` - 8.6MB, error logs

**Key Statistics**:
- Total VAST requests: 11,685+
- Successful VAST responses: 903
- Primary ad server: `g.adstrm.ru/vast3`
- Common response: 204 No Content (when no ads)
- Average VAST response size: 3KB

### Provider Information

**g.adstrm.ru (Adstream)**
- Endpoint: `https://g.adstrm.ru/vast3`
- VAST versions: 3.0, 4.0
- Characteristics:
  - Frequently returns 204 when no ads available
  - Supports Cyrillic parameters (category, genre)
  - Uses standard VAST macros: `[MACRO]` and `${MACRO}`
  - Typical durations: 5, 10, 15, 20, 30 seconds

## Manual Sample Extraction

If the script doesn't work, extract manually:

### Method 1: From vast_client.jsonl

```bash
cd ~/middleware/logs

# Find XML responses
grep "response_preview" vast_client.jsonl | \
  jq -r '.response_preview' | \
  grep "<?xml" > sample.xml

# Or use jq to extract specific fields
cat vast_client.jsonl | \
  jq -r 'select(.vast_response) | .vast_response' | \
  head -1 > sample_001.xml
```

### Method 2: Interactive inspection

```bash
# View log structure
head -1 ~/middleware/logs/vast_client.jsonl | jq .

# Find specific events
grep "vast.request.completed" ~/middleware/logs/vast_client.jsonl | head -1 | jq .

# Search for provider
grep "g.adstrm.ru" ~/middleware/logs/app.jsonl | head -1 | jq .
```

## Anonymization

**IMPORTANT**: Always anonymize production data before committing!

The extraction script automatically anonymizes:
- Device IDs → `ANONYMIZED`
- IP addresses → `ANONYMIZED`
- Serial numbers → `ANONYMIZED`
- Personal tracking URLs → `ANONYMIZED_ID`

### Manual Anonymization

If adding samples manually:

```bash
# Replace sensitive data
sed -i 's/device_id=[a-f0-9-]\+/device_id=ANONYMIZED/g' sample.xml
sed -i 's/ip=[0-9.]\+/ip=ANONYMIZED/g' sample.xml
sed -i 's/serial=[a-f0-9-]\+/serial=ANONYMIZED/g' sample.xml
```

## Directory Structure

After extraction:

```
tests/production_samples/
├── g.adstrm.ru/
│   ├── vast_sample_001_a1b2c3d4.xml
│   ├── vast_sample_002_e5f6g7h8.xml
│   └── ...
├── production_metadata.json
└── test_production_samples.py
```

## Validation

Verify extracted samples:

```bash
# Check XML validity
xmllint --noout tests/production_samples/g.adstrm.ru/*.xml

# Count samples
ls tests/production_samples/g.adstrm.ru/ | wc -l

# Preview sample
head -20 tests/production_samples/g.adstrm.ru/vast_sample_001_*.xml

# Run tests
pytest tests/production_samples/ -v
```

## Troubleshooting

### No samples extracted

**Problem**: Script reports 0 samples extracted

**Solutions**:
1. Check log file exists: `ls -lh ~/middleware/logs/vast_client.jsonl`
2. Verify log format: `head -1 ~/middleware/logs/vast_client.jsonl | jq .`
3. Look for XML in logs: `grep "<?xml" ~/middleware/logs/vast_client.jsonl | wc -l`

### Parser errors

**Problem**: Tests fail with XML parsing errors

**Solutions**:
1. Enable recovery mode in test: `VastParserConfig(recover_on_error=True)`
2. Validate XML: `xmllint --noout sample.xml`
3. Check encoding: `file sample.xml`

### Permission errors

**Problem**: Cannot write to production_samples directory

**Solutions**:
```bash
chmod -R u+w tests/production_samples/
mkdir -p tests/production_samples/g.adstrm.ru
```

## Adding More Providers

To add samples from other providers:

1. Identify provider in logs:
```bash
grep "base_url" ~/middleware/logs/app.jsonl | \
  jq -r '.base_url' | sort | uniq
```

2. Create provider directory:
```bash
mkdir -p tests/production_samples/provider_name
```

3. Extract samples:
```bash
# Modify script or extract manually
grep "provider_name" ~/middleware/logs/*.jsonl | ...
```

4. Update metadata:
```json
{
  "providers": [
    {
      "name": "Provider Name",
      "url": "provider.com",
      "endpoint": "https://provider.com/vast",
      "vast_versions": ["4.0"],
      "notes": "Any special characteristics"
    }
  ]
}
```

5. Add tests:
```python
def test_provider_samples(self, production_samples_dir, vast_parser):
    """Test provider_name samples."""
    provider_dir = production_samples_dir / "provider_name"
    # ... test logic
```

## Best Practices

### Data Privacy
- ✅ Always anonymize before committing
- ✅ Remove personal data (IDs, IPs, emails)
- ✅ Mask tracking URLs with personal info
- ✅ Review samples before git commit

### Sample Selection
- ✅ Include variety (different durations, events)
- ✅ Cover edge cases (empty, errors)
- ✅ Keep samples small (<10KB)
- ✅ Deduplicate similar responses

### Maintenance
- ✅ Update samples quarterly
- ✅ Add new providers as needed
- ✅ Remove outdated samples
- ✅ Keep metadata current

## CI/CD Considerations

Production samples are **optional** in CI:

```yaml
# GitHub Actions
- name: Run production tests
  run: pytest tests/production_samples/
  continue-on-error: true  # Don't fail if samples missing
```

## Support

For issues:
1. Check `tests/production_samples/README.md`
2. Review extraction script: `tests/extract_production_samples.py`
3. Inspect production logs manually
4. Contact team lead for log access

## Security Notes

**DO NOT COMMIT**:
- ❌ Raw production logs
- ❌ Unmodified samples with personal data
- ❌ API keys or authentication tokens
- ❌ Internal URLs or sensitive endpoints

**ALWAYS**:
- ✅ Anonymize all personal data
- ✅ Review before commit
- ✅ Use `.gitignore` for sensitive files
- ✅ Follow data privacy policies
