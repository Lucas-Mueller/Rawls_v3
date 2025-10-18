# Test Acceleration Guide

## Overview

The Frohlich Experiment framework includes an intelligent test acceleration system that transforms development workflows from 90-120 minute test cycles to ultra-fast feedback loops while maintaining comprehensive validation for releases.

## Quick Start

```bash
# Ultra-fast development feedback (7 seconds)
pytest --mode=ultra_fast

# Daily development workflow (5 minutes)
pytest --mode=dev

# CI/CD pipeline (15 minutes)
pytest --mode=ci

# Complete validation (30-45 minutes)
pytest --mode=full
```

## Performance Improvements

| Mode | Duration | API Calls | Improvement | Use Case |
|------|----------|-----------|-------------|----------|
| Ultra-fast | ~7 seconds | 0 | 99.3% | Daily development |
| Development | ~5 minutes | 20-50 | 95% | Pre-commit validation |
| CI/CD | ~15 minutes | 100-200 | 85% | Automated testing |
| Full | 30-45 minutes | 300-500 | 65% | Release validation |

## Test Execution Modes

### 1. Ultra-Fast Mode (`--mode ultra_fast`)

**Purpose**: Instant feedback during active development

**What it runs**:
- Unit tests only (169 tests)
- No API calls
- Uses optimized configuration (`config/test_ultra_fast.yaml`)

**When to use**:
- During active coding sessions
- Test-driven development
- Rapid iteration cycles

```bash
pytest --mode=ultra_fast
```

### 2. Development Mode (`--mode dev`)

**Purpose**: Comprehensive validation before committing changes

**What it runs**:
- Unit tests (169 tests)
- Component tests (selective)
- Minimal API calls with optimized configurations

**When to use**:
- Before committing code
- Feature development validation
- Local integration testing

```bash
pytest --mode=dev
```

### 3. CI Mode (`--mode ci`)

**Purpose**: Automated testing in CI/CD pipelines

**What it runs**:
- Unit tests
- Component tests
- Integration tests (selective)
- Moderate API usage for validation

**When to use**:
- Automated CI/CD pipelines
- Pull request validation
- Branch merge validation

```bash
pytest --mode=ci
```

### 4. Full Mode (`--mode full`)

**Purpose**: Complete validation for releases

**What it runs**:
- All test suites
- Complete multilingual coverage
- Full API validation
- Comprehensive integration testing

**When to use**:
- Pre-release validation
- Major feature testing
- Comprehensive quality assurance

```bash
pytest --mode=full
```

## Fast Test Suite

The framework includes an ultra-fast test suite (`tests/fast/`) that provides service boundary validation without API calls.

### Running Fast Tests

```bash
# All fast tests (43 tests in 0.04 seconds)
python -m pytest tests/fast/ -v

# Response parsing tests only
python -m pytest tests/fast/test_response_parsing.py -v

# Data flow tests only
python -m pytest tests/fast/test_data_flows.py -v
```

### What Fast Tests Cover

1. **Response Parsing**: Multilingual response validation (English, Spanish, Mandarin)
2. **Data Flows**: Service integration with synthetic data
3. **Service Interfaces**: Protocol-based boundary validation
4. **Consensus Detection**: Deterministic consensus algorithms
5. **Error Handling**: Edge cases and fallback behavior

## Environment Variables

Control test execution behavior with environment variables:

### Test Mode Control

```bash
# Enable development mode (default)
DEVELOPMENT_MODE=1 pytest --mode=dev

# Force comprehensive testing in development
FULL_INTEGRATION_TESTS=1 pytest --mode=ci

# Skip expensive tests even with API keys
SKIP_EXPENSIVE_TESTS=1 pytest --mode=ci
```

### Configuration Override

```bash
# Use ultra-fast config globally
TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml pytest --mode=dev

# Control multilingual testing
LIVE_LANGUAGES=1 pytest --mode=ci
```

### Legacy Environment Variables

```bash
# Force enable/disable live tests
RUN_LIVE_TESTS=1 pytest --mode=full

# Language coverage reporting
LANGUAGE_REPORT_PATH=/path/to/report.json pytest --mode=full
```

## Configuration Files

### Ultra-Fast Configuration (`config/test_ultra_fast.yaml`)

Optimized for maximum speed:

- **2 rounds** (vs 10 default)
- **gpt-4o-mini** model (fastest/cheapest)
- **Reasoning disabled** (major speedup)
- **Reduced memory limits** (5000 vs 25000)
- **Single language** (English only)
- **Deterministic settings** (temperature=0, fixed seed)

Expected **75% API call reduction** compared to default configuration.

### Configuration Factory

The `tests/support/config_factory.py` provides optimized configurations:

```python
from tests.support.config_factory import build_minimal_test_configuration

# Ultra-minimal config for fast testing
config = build_minimal_test_configuration(
    agent_count=2,
    rounds=2,
    reasoning_enabled=False
)

# Component-specific optimization
config = build_focused_component_config("voting", rounds=3)

# Mode-based configuration
config = build_configuration_for_test_mode("ultra_fast")
```

## Mock Testing Framework

The framework includes comprehensive mocking capabilities in `tests/support/mock_utilities.py`.

### Mock Components

1. **MockParticipantAgent**: Realistic agent simulation
2. **MockLanguageManager**: Multilingual support (English, Spanish, Mandarin)
3. **MockUtilityAgent**: Response parsing simulation
4. **MockMemoryService**: Memory management mocking
5. **Service Mocks**: All core services with realistic behavior

### Using Mocks

```python
from tests.support.mock_utilities import (
    create_mock_participants,
    create_multilingual_test_setup,
    MockLanguage
)

# Create mock participants for testing
participants = create_mock_participants(count=3, language=MockLanguage.ENGLISH)

# Full multilingual test setup
setup = create_multilingual_test_setup(
    participant_count=2,
    include_utility_agent=True
)
```

## Pytest Execution Reference

```bash
# Layered presets
pytest --mode=ultra_fast
pytest --mode=dev
pytest --mode=ci
pytest --mode=full

# Marker-based selection
pytest -m "unit"
pytest -m "component and not live"
pytest -m "integration and live"

# Coverage
pytest --mode=ci --cov=. --cov-report=term-missing
```

## Development Workflows

### Recommended Daily Workflow

1. **Active development**: `pytest --mode=ultra_fast` (7 seconds)
2. **Feature validation**: `pytest --mode=dev` (5 minutes)
3. **Pre-commit**: `pytest --mode=ci` (15 minutes)
4. **Pre-release**: `pytest --mode=full` (30-45 minutes)

### TDD Workflow

For test-driven development, loop on the ultra-fast preset:

```bash
# Write test, run ultra-fast validation
pytest --mode=ultra_fast

# Implement feature, validate quickly
pytest --mode=ultra_fast

# Final validation before commit
pytest --mode=dev
```

### CI/CD Integration

Configure your CI pipeline to call pytest directly:

```yaml
# Example CI configuration
test_fast:
  script: pytest --mode=ci

test_comprehensive:
  script: pytest --mode=full
  only: [main, release/*]
```

## Troubleshooting

### Common Issues

1. **Configuration not found**: Ensure `config/test_ultra_fast.yaml` exists
2. **API key missing**: Set `OPENAI_API_KEY` for component/integration tests
3. **Unexpected skips**: Check `--mode` preset and marker filters

### Performance Issues

If tests are slower than expected:

1. Confirm environment variables (`FULL_INTEGRATION_TESTS`, `SKIP_EXPENSIVE_TESTS`) are set as intended
2. Use `pytest -vv --durations=10` to profile slow tests
3. Limit live coverage with `pytest --mode=dev -m "not live"`

### Getting Help

```bash
# Show pytest help with custom options
pytest --help

# Inspect collected tests
pytest --mode=ci --collect-only
```

## Implementation Details

### Architecture

The test acceleration system consists of three main components:

1. **Configuration Optimization**: Ultra-fast configurations with minimal API usage
2. **Strategic Mocking**: Service boundary testing without API calls
3. **Pytest Presets**: Mode-based execution implemented via a custom pytest option

### Technical Features

- **Mode-based execution planning**: Predefined test combinations exposed through `pytest --mode`
- **Environment orchestration**: Safe configuration override using well-scoped environment variables
- **Lightweight wrapper**: `run_tests.py` forwards to pytest for backwards compatibility
- **Mock framework**: Comprehensive mocking with multilingual support

### Files Modified/Added

- Enhanced: `run_tests.py`, `tests/conftest.py`
- Added: `config/test_ultra_fast.yaml`
- Added: `tests/support/config_factory.py`
- Added: `tests/support/language_matrix.py`
- Added: `tests/support/mock_utilities.py`
- Added: `tests/fast/` directory with ultra-fast tests
- Added: Validation tests for configuration integrity

This system successfully transforms the development experience from 90-120 minute test cycles to ultra-fast feedback loops while maintaining comprehensive validation capabilities for releases.
