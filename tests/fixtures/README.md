# Test Fixtures

This directory contains legacy fixture material that remains for reference and
for manually recreating historical scenarios referenced in the documentation.
Active unit/component suites now rely on factories in `tests/support`, so the
files here are only required when reproducing archived reports or crafting new
fixtures via `tests/templates/fixture_definition_template.py`.

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

These fixtures are **not** loaded by the modern layered suites. They remain only
for occasional manual experiments or when preparing new deterministic fixtures.
When adding new fixtures, prefer the
prompt-harness helpers in `tests/support`; only drop files here if a scenario
must persist alongside documentation.

```python
# Example usage in tests
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures"
config_path = fixtures_dir / "configs" / "test_complex_mode_config.yaml"
```

## Guidelines

- **Do not modify** existing fixture files unless updating linked documentation.
- **Add new fixtures** here only if they need to persist outside the prompt
  harness/config factories.
- **Document** any new fixtures in this README and reference the consuming
  guide or report.
- **Keep fixtures minimal** – prefer generated data via `tests/support`
  utilities for active tests.
