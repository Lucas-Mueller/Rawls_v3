# Test Acceleration Guide

## Overview

The Frohlich Experiment framework includes an intelligent test acceleration system that transforms development workflows from 90-120 minute test cycles to ultra-fast feedback loops while maintaining comprehensive validation for releases.

## Quick Start

```bash
# Ultra-fast development feedback (7 seconds)
python run_tests.py --mode ultra_fast

# Daily development workflow (5 minutes)
python run_tests.py --mode dev

# CI/CD pipeline (15 minutes)
python run_tests.py --mode ci

# Complete validation (30-45 minutes)
python run_tests.py --mode full
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
python run_tests.py --mode ultra_fast
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
python run_tests.py --mode dev
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
python run_tests.py --mode ci
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
python run_tests.py --mode full
```

## Advanced Options

### Configuration Override

Override the default configuration for any mode:

```bash
python run_tests.py --mode dev --config config/custom.yaml
```

### Language Control

Control the number of languages tested (1, 2, or 3):

```bash
python run_tests.py --mode ci --languages 2
```

### Performance Reporting

Get detailed performance analysis:

```bash
python run_tests.py --mode dev --performance-report
```

### Dry Run

Preview the execution plan without running tests:

```bash
python run_tests.py --mode full --dry-run
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
DEVELOPMENT_MODE=1 python run_tests.py

# Force comprehensive testing in development
FULL_INTEGRATION_TESTS=1 python run_tests.py

# Skip expensive tests even with API keys
SKIP_EXPENSIVE_TESTS=1 python run_tests.py
```

### Configuration Override

```bash
# Use ultra-fast config globally
TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml python run_tests.py

# Control multilingual testing
LIVE_LANGUAGES=1 python run_tests.py  # Single language only
```

### Legacy Environment Variables

```bash
# Force enable/disable live tests
RUN_LIVE_TESTS=1 python run_tests.py

# Language coverage reporting
LANGUAGE_REPORT_PATH=/path/to/report.json python run_tests.py
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

## Backward Compatibility

All existing test execution patterns remain fully supported:

```bash
# Legacy test execution (still works)
python run_tests.py unit
python run_tests.py unit component
python run_tests.py --coverage

# Traditional test types
python run_tests.py component
python run_tests.py integration
python run_tests.py contracts
python run_tests.py live
```

## Development Workflows

### Recommended Daily Workflow

1. **Active development**: `python run_tests.py --mode ultra_fast` (7 seconds)
2. **Feature validation**: `python run_tests.py --mode dev` (5 minutes)
3. **Pre-commit**: `python run_tests.py --mode ci` (15 minutes)
4. **Pre-release**: `python run_tests.py --mode full` (30-45 minutes)

### TDD Workflow

For test-driven development, use ultra-fast mode for rapid iteration:

```bash
# Write test, run ultra-fast validation
python run_tests.py --mode ultra_fast

# Implement feature, validate quickly
python run_tests.py --mode ultra_fast

# Final validation before commit
python run_tests.py --mode dev
```

### CI/CD Integration

Configure your CI pipeline to use appropriate modes:

```yaml
# Example CI configuration
test_fast:
  script: python run_tests.py --mode ci

test_comprehensive:
  script: python run_tests.py --mode full
  only: [main, release/*]
```

## Troubleshooting

### Common Issues

1. **Configuration not found**: Ensure `config/test_ultra_fast.yaml` exists
2. **API key missing**: Set `OPENAI_API_KEY` for component/integration tests
3. **Environment conflicts**: Use `--dry-run` to preview execution plan

### Performance Issues

If tests are slower than expected:

1. Check API key availability (may enable more comprehensive testing)
2. Verify environment variables aren't forcing expensive tests
3. Use `--performance-report` to analyze execution time

### Getting Help

```bash
# Show all available options
python run_tests.py --help

# Preview execution without running
python run_tests.py --mode <mode> --dry-run
```

## Implementation Details

### Architecture

The test acceleration system consists of three main components:

1. **Configuration Optimization**: Ultra-fast configurations with minimal API usage
2. **Strategic Mocking**: Service boundary testing without API calls
3. **Enhanced Test Runner**: Intelligent mode-based execution

### Technical Features

- **Mode-based execution planning**: Predefined test combinations for different scenarios
- **Environment orchestration**: Safe configuration override without conflicts
- **Performance tracking**: Real-time metrics and analysis
- **Backward compatibility**: Full support for legacy test patterns
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