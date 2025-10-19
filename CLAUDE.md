# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Frohlich Experiment is a Python-based framework for conducting experiments with AI agents simulating distributive justice scenarios. It's inspired by economist Norman Frohlich's experiments and implements a "veil of ignorance" scenario where AI agents engage in two-phase experiments to reach consensus on principles of justice.

The framework uses OpenAI Agents SDK for participant agents and integrates sophisticated voting systems, multilingual support, and comprehensive experiment orchestration.

## Core Architecture

### Two-Phase Experiment Structure
- **Phase 1**: Individual agents familiarize themselves with justice principles and their own income assignments
- **Phase 2**: Group discussion where agents reach consensus on a justice principle through formal voting mechanisms

### Key Components
- **FrohlichExperimentManager** (`core/experiment_manager.py`): Orchestrates complete experiments
- **Phase1Manager** (`core/phase1_manager.py`): Manages individual agent deliberation 
- **Phase2Manager** (`core/phase2_manager.py`): Orchestrates group discussion using specialized services
- **Participant Agents** (`experiment_agents/participant_agent.py`): AI agents that participate in experiments
- **Utility Agents** (`experiment_agents/utility_agent.py`): Parser/validator agents for processing responses

### Services-First Architecture
Phase 2 uses a services-first architecture where specialized services handle specific responsibilities:

- **SpeakingOrderService** (`core/services/speaking_order_service.py`): Manages speaking turn orders with finisher restrictions
- **DiscussionService** (`core/services/discussion_service.py`): Handles discussion prompts, statement validation, and history management
- **VotingService** (`core/services/voting_service.py`): Manages vote initiation, confirmation, and ballot coordination
- **MemoryService** (`core/services/memory_service.py`): Provides unified memory management with guidance styles and truncation
- **CounterfactualsService** (`core/services/counterfactuals_service.py`): Handles payoff calculations, counterfactual analysis, and results formatting

The Phase2Manager acts as an orchestrator that delegates specific responsibilities to these services, ensuring clean separation of concerns and maintainability.

#### Services-Always Architecture
The framework has fully migrated to a services-first approach. All Phase 2 operations go through the specialized services - there are no feature flags or legacy pathways. This ensures:
- **Consistent Behavior**: All experiments use the same service-based logic
- **Maintainability**: Changes are made in focused, single-responsibility services
- **Testability**: Services can be tested in isolation with protocol-based dependencies
- **Configurability**: Behavior is controlled through `Phase2Settings` rather than code changes

### Service Ownership and Modification Guide

When adding or modifying Phase 2 behavior, work with the appropriate service rather than modifying Phase2Manager directly:

#### SpeakingOrderService
- **Owns**: Speaking turn management, finisher restrictions, randomization strategies
- **Modify here for**: New speaking order algorithms, finisher rule changes, turn allocation logic
- **Key methods**: `determine_speaking_order()`, `apply_finisher_restrictions()`

#### DiscussionService  
- **Owns**: Discussion prompts, statement validation, history management, group composition formatting
- **Modify here for**: Prompt templates, validation rules, history truncation logic, multilingual support
- **Key methods**: `build_discussion_prompt()`, `validate_statement()`, `manage_discussion_history_length()`
- **Configuration**: Uses `Phase2Settings.public_history_max_length` for history limits

#### VotingService
- **Owns**: Vote initiation, confirmation phases, ballot coordination, consensus validation
- **Modify here for**: Voting workflows, confirmation logic, ballot validation, consensus rules
- **Key methods**: `initiate_voting()`, `coordinate_voting_confirmation()`, `coordinate_secret_ballot()`

#### MemoryService
- **Owns**: All memory updates, guidance style management, content truncation, event routing
- **Modify here for**: Memory update strategies, guidance formatting, truncation algorithms
- **Key methods**: `update_discussion_memory()`, `update_voting_memory()`, `update_results_memory()`

#### CounterfactualsService
- **Owns**: Payoff calculations, counterfactual analysis, results formatting, final rankings
- **Modify here for**: Payoff algorithms, counterfactual logic, results presentation, ranking collection
- **Key methods**: `calculate_payoffs()`, `format_detailed_results()`, `collect_final_rankings()`

### Configuration System
Configuration is YAML-driven with Pydantic models in `config/models.py`. Key settings:
- Agent personalities, models, and language preferences
- Phase 2 behavior via `Phase2Settings` (`config/phase2_settings.py`)
- Memory management and temperature settings
- Reproducibility via seed configuration

#### Phase2Settings Configuration
Phase 2 behavior is controlled through `Phase2Settings` which includes:
- **Discussion History**: Configurable `public_history_max_length` (default: 100,000 characters)
- **Statement Validation**: Minimum lengths, retry attempts, and timeout settings
- **Memory Management**: Compression thresholds and validation strictness
- **Voting Settings**: Timeout values, retry limits, and constraint tolerance
- **Two-Stage Voting**: Structured voting with numerical validation

### Transcript Logging
- **Configuration**: Enable via `transcript_logging.enabled` in experiment YAML; configure output path and capture toggles in `config/models.py`.
- **Captured Data**: Prompts sent to participant agents, optional system instructions, and—when `include_agent_responses: true` (default)—each agent's returned output.
- **Privacy Notice**: Agent responses may contain sensitive or unexpected content; document storage locations and access controls when enabling transcripts.
- **Performance**: Logging is lightweight (string serialization). Instruction capture remains optional (`include_instructions`) due to generation overhead.

## Development Commands

### Running Experiments
```bash
# Run with a configuration file (required)
python main.py config/fast.yaml

# Specify output path
python main.py config/fast.yaml results/my_experiment.json

# Note: There is no default_config.yaml - you must specify a config file
# Use config/fast.yaml for quick testing or create your own
```

### Testing

The framework includes an **intelligent test acceleration system** that provides ultra-fast feedback for development while maintaining comprehensive validation for releases.

#### **Intelligent Test Execution Modes**
```bash
# DEVELOPMENT WORKFLOWS (Ultra-fast feedback)

# Ultra-fast mode: Unit tests only (~7 seconds, 0 API calls)
pytest --mode=ultra_fast

# Development mode: Unit + component tests (~5 minutes, minimal API calls)
pytest --mode=dev

# CI/CD mode: Comprehensive validation (~15 minutes, moderate API calls)
pytest --mode=ci

# Full mode: Complete validation (~30-45 minutes, all API calls)
pytest --mode=full
```

#### **Targeted Test Execution**
```bash
# Scope by directory or marker
pytest tests/unit/test_fast_*                      # Deterministic, no API calls
pytest tests/component -m "component and not live" # Offline component checks
pytest tests/integration -m "integration and live" # Live integration smoke (requires API keys)
pytest tests/snapshots                   # Snapshot/golden suites

# With coverage reporting
pytest --mode=ci --cov=. --cov-report=term-missing
```

#### **Environment-Based Test Control**
```bash
# Development mode (skips expensive tests by default)
DEVELOPMENT_MODE=1 pytest --mode=dev

# Force comprehensive testing in development
pytest --mode=ci --run-live

# Skip expensive tests even with API keys
pytest --mode=ci --skip-expensive

# Use custom configuration globally (consumed by fixtures)
TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml pytest --mode=dev
```

#### **CLI Toggles**
```bash
pytest --run-live                    # enable live suites explicitly
pytest --no-run-live                 # force-skip live suites
pytest --languages=en,es             # restrict parametrised suites to English + Spanish
pytest --languages=all               # force all supported languages
pytest --skip-expensive              # skip tests marked expensive
```

#### **Fast Test Suite (Phase 2 Strategic Mocking)**
```bash
# Run ultra-fast service boundary tests (43 tests in ~0.04 seconds)
python -m pytest tests/unit/test_fast_* -v

# Multilingual response parsing tests (0 API calls)
python -m pytest tests/unit/test_fast_response_parsing.py

# Data flow validation tests (synthetic data)
python -m pytest tests/unit/test_fast_data_flows.py
```

#### **Environment-Based Test Control**
```bash
# Development mode (skips expensive tests by default)
DEVELOPMENT_MODE=1 pytest --mode=dev

# Force comprehensive testing in development
pytest --mode=ci --run-live

# Skip expensive tests even with API keys
pytest --mode=ci --skip-expensive

# Use custom configuration globally
TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml pytest --mode=dev
```

#### **Advanced pytest commands**
```bash
python -m pytest tests/unit/test_specific_file.py -v
python -m pytest -k "test_pattern" -v
python -m pytest tests/unit/ --tb=short

# Language coverage validation
# Component and live tests enforce coverage across english, spanish, mandarin
# Set LANGUAGE_REPORT_PATH environment variable for detailed language test reporting

# Pytest markers (configured in pytest.ini)
python -m pytest -m "not slow"        # Skip slow tests
python -m pytest -m "unit"            # Run only unit tests
python -m pytest -m "integration"     # Run only integration tests
python -m pytest -m "live"            # Run only live endpoint tests

```

#### **Performance Improvements Achieved**
- **Ultra-fast mode**: 99.3% improvement (7.6s vs 90-120 minutes)
- **Fast test suite**: 99.97% improvement (0.04s for 43 tests)
- **Development workflow**: 95% improvement (5min vs 90-120 minutes)
- **CI/CD pipeline**: 85% improvement (15min vs 90-120 minutes)

### Batch Experiment Execution
```bash
# Hypothesis testing framework provides utilities for batch execution
# See hypothesis_testing/utils_hypothesis_testing/runner.py for batch execution utilities
# Experiment configurations organized by hypothesis in hypothesis_testing/ directory:
# - hypothesis_1/: 33 different experimental conditions
# - hypothesis_2/: Cultural variations (American, Chinese)
# - hypothesis_3/: Income inequality variations (low, medium, high)
# - hypothesis_6/: Additional experimental conditions

# Custom batch scripts can leverage utils/experiment_runner.py for automation
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here        # Optional: For native Gemini models
OPENROUTER_API_KEY=your_openrouter_key_here  # Optional: For OpenRouter models

# Optional: Control OpenAI Agents SDK tracing
OPENAI_AGENTS_DISABLE_TRACING=1    # Disable tracing for tests
OPENAI_DISABLE_TRACING=true

# Optional: Test system environment variables
LANGUAGE_REPORT_PATH=/path/to/report.json  # Language coverage reporting

# Test acceleration environment variables
DEVELOPMENT_MODE=1                 # Enable development mode (default: 1)
TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml  # Override configuration globally

# Install R programming language support (for statistical analysis)
# R package "languageserver" is also recommended

# Python 3.11+ is required
```

### Documentation
```bash
# Build Sphinx documentation locally
cd docs
make html

# View built documentation
open _build/html/index.html

# Clean documentation build
make clean
```

The project includes comprehensive Sphinx documentation with GitHub Pages deployment via GitHub Actions.

### Code Quality
The project does not have dedicated linting commands configured. When working on the codebase:
- Follow existing code style and patterns (PEP 8, four-space indents, explicit type hints)
- Use `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_CASE` for constants
- Run the test suite to ensure changes don't break functionality
- Run `pytest --mode=ci` to verify module import integrity before pushing
- See `AGENTS.md` for detailed repository guidelines and commit conventions

#### Testing Requirements for API Access
- **OPENAI_API_KEY** required for live tests and some component/integration tests
- Tests automatically detect API key availability and skip/enable live tests accordingly
- Use `pytest --no-run-live` to force-skip live tests even with API key present
- Component tests require multilingual coverage (English, Spanish, Mandarin) when live tests are enabled

## Multi-Language Support

The framework supports English, Spanish, and Mandarin experiments:
- Prompts are managed via `translations/` JSON files
- Language manager handles localization (`utils/language_manager.py`)
- Agent language preferences configured per-agent in YAML

## Model Provider Support

The framework supports multiple LLM providers with intelligent detection:
- **OpenAI Models**: Native API for `gpt-*`, `o1-*`, `o3-*` models
- **Google Gemini**: Native API for `gemini-*`, `gemma-*` models
- **OpenRouter**: Universal proxy for any model using `provider/model` format
- **Ollama**: Local models via OpenAI-compatible API using `ollama/<model>` prefix

### Using Ollama (Local Models)
```bash
# 1. Start Ollama daemon and pull model
ollama serve &
ollama pull gemma3:1b

# 2. Optional: Override defaults
export OLLAMA_BASE_URL="http://localhost:11434/v1"  # Default
export OLLAMA_API_KEY="ollama"                      # Default

# 3. Configure agent with ollama/ prefix
# In your config YAML: model: "ollama/gemma3:1b"

# 4. Run experiment
python main.py config/sample_ollama_gemma3.yaml
```

See `GEMINI.md` for detailed Gemini setup and usage.

## Voting System

The framework uses a **formal voting system** with structured consensus building, managed entirely through VotingService:

### Formal Voting Process
- **Initiation**: Via end-of-round prompts only ("Do you want to initiate voting?")
- **Confirmation Phase**: All agents must agree to participate (1=Yes, 0=No) 
- **Secret Ballot**: Two-stage structured voting with numerical validation
- **Consensus**: Requires unanimous agreement on principle and constraints
- **Service Integration**: All voting logic handled by VotingService with configurable timeouts and retry limits

## Two-Stage Voting System

The framework implements a sophisticated voting mechanism (`core/two_stage_voting_manager.py`):

### Voting Stages
- **Stage 1**: Numerical principle selection (agents input 1-4)
- **Stage 2**: Amount specification (for principles 3 & 4 requiring floor constraints)

### Key Features
- Deterministic numerical input validation replacing complex LLM-based detection
- Multilingual number format parsing (supports various cultural number formats)
- Integrated with principle name manager for consistent terminology
- Fallback keyword matching system for validation

## Memory Management

The framework includes sophisticated memory management through MemoryService:
- **Unified Management**: All memory updates routed through MemoryService for consistency
- **Character limits**: Per-agent limits to prevent context overflow
- **Guidance styles**: "narrative" or "structured" formatting options
- **Content Truncation**: Configurable truncation with intelligent content preservation
- **Event Routing**: Automatic routing between simple and complex memory update strategies
- **Internal Reasoning**: Optional inclusion of internal reasoning in memory updates
- **Configuration**: Memory behavior controlled through `Phase2Settings`

## Key Data Models

- **JusticePrinciple**: Represents different distributive justice approaches
- **IncomeDistribution**: Handles income class assignments and calculations
- **ExperimentConfiguration**: Pydantic model for all experiment settings
- **Response types**: Structured parsing of agent communications

## Testing Strategy

The testing framework provides **intelligent test acceleration** with layered execution and automatic API key detection. It includes both traditional test types and new ultra-fast mocking-based tests.

### **Traditional Test Layers**
- **Unit tests** (`tests/unit/`): Component-level testing
  - Individual service testing for isolated behavior validation
  - Protocol-based dependency injection for clean service testing
  - Fast execution, no external dependencies (~7 seconds)
- **Component tests** (`tests/component/`): Mid-level integration testing
  - Requires API key for LLM interactions
  - Enforces multilingual coverage (English, Spanish, Mandarin)
  - Language coverage validation with detailed reporting
- **Integration tests** (`tests/integration/`): Cross-component testing
  - End-to-end Phase 2 workflows through services
  - Service interaction and memory consistency validation
  - Heavier multilingual flows requiring API access
- **Snapshot tests** (`tests/snapshots/`): Regression and golden snapshot testing
  - Validates expected behaviors against baseline results
  - Snapshot comparisons for consistent outputs
- **Live tests**: Full system validation with external API calls
  - Most comprehensive validation requiring API access
  - Automatically enabled when OPENAI_API_KEY is present

### **Strategic Mocking Layer (NEW)**
- **Fast tests** (`tests/unit/test_fast_*`): Ultra-fast service boundary testing
  - **43 tests in 0.04 seconds** with 0 API calls
  - **Response parsing tests**: Multilingual response validation with deterministic data
  - **Data flow tests**: Service integration testing with synthetic data
  - **Service interface tests**: Protocol-based boundary validation
  - **Multilingual coverage**: English, Spanish, Mandarin with realistic mock responses

### **Intelligent Test Execution Modes**
The enhanced test runner provides mode-based execution optimized for different development phases:

- **Ultra-fast mode** (`--mode ultra_fast`): Unit tests only (~7 seconds, 99.3% improvement)
- **Development mode** (`--mode dev`): Unit + fast tests (~5 minutes, 95% improvement)
- **CI mode** (`--mode ci`): Comprehensive validation (~15 minutes, 85% improvement)
- **Full mode** (`--mode full`): Complete validation (~30-45 minutes, 65% improvement)

### **Test Configuration System**
- **Configuration factory** (`tests/support/config_factory.py`): Optimized configs for different test scenarios
- **Smart language selection** (`tests/support/language_matrix.py`): Intelligent multilingual testing
- **Mock utilities** (`tests/support/mock_utilities.py`): Comprehensive mocking framework
- **Environment control**: Development-friendly test execution with configurable behavior

### **Test Execution Patterns (Updated)**
- **Daily development**: `pytest --mode=ultra_fast` (7 seconds)
- **Pre-commit**: `pytest --mode=dev` (5 minutes)
- **CI/CD pipeline**: `pytest --mode=ci` (15 minutes)
- **Release validation**: `pytest --mode=full` (30-45 minutes)
- **Service boundary testing**: `python -m pytest tests/unit/test_fast_*` (0.04 seconds)
- **Import validation**: Automatic module import testing across all layers

## Tracing and Observability

- OpenAI Agents SDK tracing for participant agents only (utility agents untraced)
- Trace URLs generated for experiment debugging
- Environment variables control tracing behavior

## Configuration Examples

Common configurations are in `config/`:
- `fast.yaml`: Quick testing configuration (5 rounds) - recommended starting point
- `sample_ollama_gemma3.yaml`: Example Ollama local model configuration
- `test_gemini.yaml`: Example Google Gemini configuration
- `test_mixed_providers.yaml`: Example mixing different model providers
- `gpt_5_disagree.yaml`: Multi-agent disagreement scenario
- `ollama.yaml`: General Ollama configuration example

### **Test-Optimized Configurations**
- `config/test_ultra_fast.yaml`: Maximum speed optimization
  - 2 rounds (vs 10), gpt-4o-mini model, reasoning disabled
  - Single language, deterministic settings, reduced memory limits
  - Expected 75% API call reduction for testing scenarios
- `config/test_gpt_utility.yaml`: GPT-based utility agent testing
- `config/test_retry_*.yaml`: Language-specific retry behavior testing (English, Spanish, Mandarin)

## Project Structure

### Hypothesis Testing Framework
The `hypothesis_testing/` directory contains organized experimental conditions:
- `hypothesis_1/`: 33 different experimental conditions
- `hypothesis_2/`: Cultural variations (American, Chinese)
- `hypothesis_3/`: Income inequality variations (low, medium, high)
- `hypothesis_6/`: Additional experimental conditions
- `utils_hypothesis_testing/`: Shared utilities including `runner.py` for batch execution

### Specialized Components

#### Core Services Architecture
- `core/services/`: Service-based Phase 2 architecture
  - `speaking_order_service.py`: Speaking turn management with finisher restrictions
  - `discussion_service.py`: Discussion prompts, validation, and history management  
  - `voting_service.py`: Vote initiation, confirmation, and ballot coordination
  - `memory_service.py`: Unified memory management with guidance styles
  - `counterfactuals_service.py`: Payoff calculations and results formatting

#### Supporting Components
- `core/two_stage_voting_manager.py`: Advanced voting system with numerical validation
- `core/principle_name_manager.py`: Consistent justice principle terminology
- `config/phase2_settings.py`: Configurable Phase 2 behavior and validation settings
- `utils/cultural_adaptation.py`: Multilingual number formatting and cultural context
- `experiment_agents/`: Participant and utility agent implementations
- `utils/experiment_runner.py`: Utility for batch experiment execution
- `hypothesis_testing/utils_hypothesis_testing/runner.py`: Framework for hypothesis testing workflows

#### **Test Acceleration Infrastructure (NEW)**
- `tests/support/config_factory.py`: Optimized test configuration generation
  - `build_minimal_test_configuration()`: Ultra-minimal configs for fast testing
  - `build_focused_component_config()`: Component-specific optimizations
  - `build_configuration_for_test_mode()`: Mode-based configuration selection
- `tests/support/language_matrix.py`: Smart multilingual testing
  - `smart_parametrize_languages()`: Intelligent language selection (1-3 languages)
- `tests/support/mock_utilities.py`: Comprehensive mocking framework
  - Mock agents, services, and multilingual response patterns
- `tests/unit/test_fast_*`: Ultra-fast service boundary testing (43 tests in 0.04s)
  - `test_response_parsing.py`: Multilingual parsing with deterministic data
  - `test_data_flows.py`: Service integration with synthetic data

## Important Instruction Reminders

- Do what has been asked; stay focused
- Do not create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one  
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested by the User
- ALWAYS USE a systematic approach
- Heavily use detailed and systematic to do lists
- Obey the principle of simplicity, do not overengineer things. Stay effective
