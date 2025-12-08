# VAST Client Test Suite

Comprehensive test suite for the VAST Client package, including unit tests, integration tests, and validation against IAB VAST samples.

## Directory Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_utils.py              # Test utility functions
│
├── unit/                      # Unit tests for individual components
│   ├── __init__.py
│   ├── test_parser.py        # VAST XML parser tests
│   ├── test_tracker.py       # Event tracker tests
│   ├── test_client.py        # VAST client tests
│   └── test_config.py        # Configuration tests
│
├── integration/               # Integration tests for complete workflows
│   ├── __init__.py
│   └── test_client_integration.py
│
├── iab_samples/              # IAB VAST samples validation
│   ├── __init__.py
│   ├── test_iab_samples.py
│   ├── VAST 1-2.0 Samples/
│   ├── VAST 3.0 Samples/
│   ├── VAST 4.0 Samples/
│   ├── VAST 4.1 Samples/
│   └── VAST 4.2 Samples/
│
├── production_samples/        # Real production ad server samples
│   ├── __init__.py
│   ├── README.md
│   ├── production_metadata.json
│   ├── test_production_samples.py
│   └── g.adstrm.ru/          # Adstream samples (add manually)
│
└── fixtures/                  # Test data and fixtures
    ├── __init__.py
    ├── vast_client_config.json
    └── parsed_vast_data.json
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# IAB samples tests only
pytest tests/iab_samples/

# Production samples tests only
pytest tests/production_samples/
```

### Run Tests by Marker
```bash
# Parser tests only
pytest -m parser

# Tracker tests only
pytest -m tracker

# Slow tests excluded
pytest -m "not slow"
```

### Run Specific Test File
```bash
pytest tests/unit/test_parser.py
pytest tests/unit/test_tracker.py
```

### Run Specific Test Function
```bash
pytest tests/unit/test_parser.py::TestVastParser::test_parse_minimal_vast
```

### Run with Coverage
```bash
pytest --cov=vast_client --cov-report=html
```

### Run with Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Failed Tests Only
```bash
pytest --lf  # Last failed
pytest --ff  # Failed first
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation with mocked dependencies.

**`test_parser.py`**
- VAST XML parsing (all versions: 1.0-4.2)
- XPath extraction
- Duration parsing
- Extension handling
- Error recovery
- Custom XPath configuration
- Edge cases (malformed XML, empty responses, etc.)

**`test_tracker.py`**
- Tracker initialization
- Macro substitution ([MACRO] and ${MACRO} formats)
- Static vs dynamic macros
- Event tracking
- Multiple tracking URLs
- HTTP error handling
- Configuration options

**`test_client.py`**
- Client initialization patterns
- Ad request/response handling
- Context manager usage
- Parser integration
- Tracker creation
- Error handling
- Configuration overrides

**`test_config.py`**
- Configuration dataclasses
- Default values
- Custom configurations
- Enum values
- Config validation

### Integration Tests (`tests/integration/`)

Test complete workflows with multiple components working together.

**`test_client_integration.py`**
- End-to-end request → parse → track workflow
- Macro substitution in tracking
- Context manager lifecycle
- Multiple impression tracking
- Error handling and graceful degradation
- Configuration variants

### IAB Samples Tests (`tests/iab_samples/`)

Validate parser against official IAB VAST samples.

**`test_iab_samples.py`**
- Parse all VAST 1.0-4.2 samples
- Validate required fields
- Check tracking event types
- Inline vs wrapper ads
- Linear vs non-linear creatives

## Fixtures

### Configuration Fixtures
- `parser_config`: Default VAST parser configuration
- `tracker_config`: Default tracker configuration
- `session_config`: Default playback session configuration
- `vast_client_config`: Complete VAST client configuration

### Mock Fixtures
- `mock_http_response`: Mock HTTP response
- `mock_http_client`: Mock async HTTP client
- `simulated_time_provider`: Simulated time for testing

### VAST XML Fixtures
- `minimal_vast_xml`: Minimal valid VAST 4.0
- `vast_with_quartiles_xml`: VAST with quartile events
- `vast_with_macros_xml`: VAST with macro placeholders
- `vast_with_error_xml`: VAST with error URLs
- `malformed_vast_xml`: Intentionally malformed XML
- `empty_vast_xml`: Empty VAST response

### Data Fixtures
- `minimal_vast_data`: Parsed VAST data structure
- `load_fixture_file()`: Load fixture from file
- `load_json_fixture()`: Load JSON fixture
- `load_iab_sample()`: Load IAB sample XML

### Component Fixtures
- `vast_parser`: VAST parser instance
- `vast_tracker`: VAST tracker instance
- `vast_client`: VAST client instance
- `tracking_context`: Tracking context for DI

## Test Utilities (`test_utils.py`)

Helper functions for creating test data and assertions:

- `create_mock_http_response()`: Create mock HTTP responses
- `create_mock_http_client()`: Create mock async HTTP client
- `assert_valid_tracking_url()`: Validate tracking URL format
- `assert_valid_vast_structure()`: Validate VAST data structure
- `create_test_vast_xml()`: Generate test VAST XML
- `extract_macro_value()`: Extract parameter from URL
- `count_tracking_urls()`: Count total tracking URLs

## Coverage Goals

Target: **90%+ code coverage** across all modules

### Current Coverage Areas

✅ **Parser** (`parser.py`)
- XML parsing with all VAST versions
- XPath extraction
- Duration parsing
- Extensions handling
- Error recovery modes

✅ **Tracker** (`tracker.py`)
- Event tracking
- Macro substitution
- HTTP request sending
- Error handling
- Configuration options

✅ **Client** (`client.py`)
- Initialization patterns
- Ad requests
- Response handling
- Component integration

✅ **Config** (`config.py`)
- All dataclasses
- Enum values
- Default configurations

✅ **IAB Compatibility**
- All VAST versions (1.0-4.2)
- 75+ official IAB samples

## Writing New Tests

### Unit Test Example

```python
import pytest
from vast_client.parser import VastParser

class TestMyFeature:
    """Test suite for my feature."""

    def test_feature_success(self, vast_parser, minimal_vast_xml):
        """Test successful feature execution."""
        vast_data = vast_parser.parse_vast(minimal_vast_xml)
        assert vast_data["ad_system"] == "Test Ad System"

    @pytest.mark.asyncio
    async def test_async_feature(self, mock_http_client):
        """Test async feature."""
        # Your async test code
        pass
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_complete_workflow(self, vast_client, minimal_vast_xml):
    """Test complete ad serving workflow."""
    # Setup mock response
    mock_response = create_mock_http_response(content=minimal_vast_xml)
    vast_client.client.get.return_value = mock_response

    # Execute workflow
    vast_data = await vast_client.request_ad()
    await vast_client.tracker.track_event("start")

    # Verify results
    assert vast_data is not None
    assert vast_client.tracker is not None
```

### Using Markers

```python
@pytest.mark.slow
@pytest.mark.integration
async def test_slow_integration(self):
    """Mark tests appropriately."""
    pass
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov=vast_client --cov-report=xml --cov-report=term
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Isolation**: Use mocks for external dependencies
2. **Clarity**: One assertion concept per test
3. **Naming**: Descriptive test names (test_feature_scenario_expected)
4. **Fixtures**: Reuse common setup via fixtures
5. **Async**: Use `@pytest.mark.asyncio` for async tests
6. **Markers**: Tag tests for selective execution
7. **Coverage**: Aim for edge cases and error paths
8. **Documentation**: Add docstrings to test classes/functions

## Troubleshooting

### Import Errors
```bash
# Ensure package is installed in development mode
pip install -e .
```

### Async Warnings
```bash
# Make sure pytest-asyncio is installed
pip install pytest-asyncio
```

### Missing Fixtures
```bash
# Check conftest.py is present in test directory
ls tests/conftest.py
```

### IAB Samples Not Found
```bash
# IAB samples should be in tests/iab_samples/
# Download from: https://github.com/InteractiveAdvertisingBureau/VAST_Samples
```

## Contributing

When adding new features:

1. Write unit tests for new components
2. Add integration tests for workflows
3. Update fixtures if needed
4. Maintain >90% coverage
5. Run full test suite before committing

```bash
# Pre-commit checklist
pytest --cov=vast_client --cov-report=term
mypy src/vast_client
ruff check src/vast_client
black src/vast_client tests
```
