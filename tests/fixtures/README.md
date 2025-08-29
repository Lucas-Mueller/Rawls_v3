# Test Fixtures

This directory contains test data, configuration files, and sample outputs used by the test suite.

## Directory Structure

### `configs/`
Test configuration files used for various test scenarios:
- `test_complex_mode_config.yaml` - Configuration for testing complex voting detection mode
- `test_invalid_mode.yaml` - Configuration with invalid voting mode for error testing
- `test_config_academic_integrity.yaml` - Configuration for testing academic integrity features

### `test_outputs/`
Sample output files from experiments used for testing:
- `test_complex_mode_output.json` - Sample output from complex mode experiment

## Usage

These fixtures are used by integration and unit tests to provide consistent test data:

```python
# Example usage in tests
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures"
config_path = fixtures_dir / "configs" / "test_complex_mode_config.yaml"
```

## Guidelines

- **Do not modify** existing fixture files unless updating test requirements
- **Add new fixtures** when tests need consistent data
- **Document** any new fixtures in this README
- **Keep fixtures minimal** - only include data necessary for testing