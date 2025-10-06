# Test Templates

This directory contains reusable test templates for multilingual testing in the Frohlich Experiment system.

## Available Templates

### Unit Tests
- `multilingual_unit_test_template.py` - Template for multilingual unit tests
- `fixture_definition_template.py` - Template for language-specific fixture definitions

### Integration Tests  
- `integration_test_template.py` - Template for cross-language integration tests

### Performance Tests
- `performance_test_template.py` - Template for multilingual performance benchmarks

## Usage

Copy the appropriate template file and customize it for your specific test needs. Each template includes:
- Proper parameterization setup
- Fixture usage examples
- Language-agnostic test patterns
- Documentation and comments

## Quick Start

```bash
# Copy unit test template
cp tests/templates/multilingual_unit_test_template.py tests/unit/test_my_feature.py

# Copy integration test template  
cp tests/templates/integration_test_template.py tests/integration/test_my_integration.py

# Copy performance test template
cp tests/templates/performance_test_template.py tests/performance/test_my_performance.py
```

Edit the copied files to implement your specific test logic.