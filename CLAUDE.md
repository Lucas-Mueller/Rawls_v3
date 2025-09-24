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

## Development Commands

### Running Experiments
```bash
# Basic experiment with default config
python main.py

# Custom configuration
python main.py config/custom_config.yaml

# Custom config with output path
python main.py config/custom_config.yaml results/my_experiment.json
```

### Testing
```bash
# Run all tests
python run_tests.py

# Specific test types
python run_tests.py unit
python run_tests.py component  # Component tests with language coverage enforcement
python run_tests.py integration
python run_tests.py contracts  # Contract/regression tests
python run_tests.py live       # Live tests requiring API keys

# With coverage
python run_tests.py --coverage

# Advanced pytest commands
python -m pytest tests/unit/test_specific_file.py -v
python -m pytest -k "test_pattern" -v
python -m pytest tests/unit/ --tb=short

# Standalone issue-specific test scripts (located in project root)
python test_compromise_forgetting_issue.py
python test_dynamic_tool_logging.py
python test_keyword_fix.py
python test_memory_optimization.py
python test_parallel_execution.py
python test_selective_memory_updates.py
```

### Batch Experiment Execution
```bash
# Run all condition 1 experiments from hypothesis testing directory
python run_condition_1_experiments.py
```

This script automatically runs all YAML configurations in sequence and saves results to organized directories with descriptive names.

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
OPENAI_API_KEY=your_key_here

# Install R programming language support (for statistical analysis)
# R package "languageserver" is also recommended
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
- Follow existing code style and patterns
- Run the test suite to ensure changes don't break functionality
- Use the import test in `run_tests.py` to verify module integrity

## Multi-Language Support

The framework supports English, Spanish, and Mandarin experiments:
- Prompts are managed via `translations/` JSON files
- Language manager handles localization (`utils/language_manager.py`)
- Agent language preferences configured per-agent in YAML

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

- **Unit tests**: Component-level testing in `tests/unit/`
  - Individual service testing for isolated behavior validation
  - Protocol-based dependency injection for clean service testing
- **Integration tests**: Cross-component testing in `tests/integration/`
  - End-to-end Phase 2 workflows through services
  - Service interaction and memory consistency validation
- **Import validation**: Automatic module import testing
- **Multilingual validation**: Translation consistency checks
- **Service Testing**: Focused testing of service responsibilities and boundaries

## Tracing and Observability

- OpenAI Agents SDK tracing for participant agents only (utility agents untraced)
- Trace URLs generated for experiment debugging
- Environment variables control tracing behavior

## Configuration Examples

Common configurations are in `config/`:
- `default_config.yaml`: Standard two-agent setup
- `fast_config.yaml`: Reduced rounds for quick testing
- Language-specific configs for Spanish/Mandarin experiments

## Project Structure

### Hypothesis Testing Framework
The `hypothesis_testing/` directory contains organized experimental conditions:
- `hypothesis_1/`: 33 different experimental conditions
- `hypothesis_2/`: Cultural variations (American, Chinese) with 34+ conditions each
- `hypothesis_3/`: Income inequality variations (low, medium, high) with 34+ conditions each

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

## Important Instruction Reminders

- Do what has been asked; stay focused
- Do not create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one  
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested by the User
- ALWAYS USE a systematic approach
- Heavily use detailed and systematic to do lists
- Obey the principle of simplicity, do not overengineer things. Stay effective

