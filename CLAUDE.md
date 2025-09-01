# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Frohlich Experiment is a Python-based framework for conducting experiments with AI agents simulating distributive justice scenarios. It's inspired by economist Norman Frohlich's experiments and implements a "veil of ignorance" scenario where AI agents engage in two-phase experiments to reach consensus on principles of justice.

The framework uses OpenAI Agents SDK for participant agents and integrates sophisticated voting systems, multilingual support, and comprehensive experiment orchestration.

## Core Architecture

### Two-Phase Experiment Structure
- **Phase 1**: Individual agents familiarize themselves with justice principles and their own income assignments
- **Phase 2**: Group discussion where agents reach consensus on a justice principle through either preference-based or formal voting mechanisms

### Key Components
- **FrohlichExperimentManager** (`core/experiment_manager.py`): Orchestrates complete experiments
- **Phase1Manager** (`core/phase1_manager.py`): Manages individual agent deliberation 
- **Phase2Manager** (`core/phase2_manager.py`): Manages group discussion and consensus building
- **Participant Agents** (`experiment_agents/participant_agent.py`): AI agents that participate in experiments
- **Utility Agents** (`experiment_agents/utility_agent.py`): Parser/validator agents for processing responses

### Configuration System
Configuration is YAML-driven with Pydantic models in `config/models.py`. Key settings:
- Agent personalities, models, and language preferences
- Voting detection modes: `"simple"` (preference-based) or `"complex"` (formal voting)
- Memory management and temperature settings
- Reproducibility via seed configuration

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
python run_tests.py integration

# With coverage
python run_tests.py --coverage

# Advanced pytest commands
python -m pytest tests/unit/test_specific_file.py -v
python -m pytest -k "test_pattern" -v
python -m pytest tests/unit/ --tb=short
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
```

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

The framework uses a single **formal voting system** with structured consensus building:

### Formal Voting Process
- **Initiation**: Via end-of-round prompts only ("Do you want to initiate voting?")
- **Confirmation Phase**: All agents must agree to participate (1=Yes, 0=No)
- **Secret Ballot**: Two-stage structured voting with numerical validation
- **Consensus**: Requires unanimous agreement on principle and constraints

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

The framework includes sophisticated memory management:
- Character limits per agent to prevent context overflow
- Memory guidance styles: "narrative" or "structured"
- Optional inclusion of internal reasoning in memory updates

## Key Data Models

- **JusticePrinciple**: Represents different distributive justice approaches
- **IncomeDistribution**: Handles income class assignments and calculations
- **ExperimentConfiguration**: Pydantic model for all experiment settings
- **Response types**: Structured parsing of agent communications

## Testing Strategy

- **Unit tests**: Component-level testing in `tests/unit/`
- **Integration tests**: Cross-component testing in `tests/integration/`
- **Import validation**: Automatic module import testing
- **Multilingual validation**: Translation consistency checks

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
- `core/two_stage_voting_manager.py`: Advanced voting system with numerical validation
- `core/principle_name_manager.py`: Consistent justice principle terminology
- `utils/cultural_adaptation.py`: Multilingual number formatting and cultural context
- `experiment_agents/`: Participant and utility agent implementations
- `utils/experiment_runner.py`: Utility for batch experiment execution
- `hypothesis_testing/utils_hypothesis_testing/runner.py`: Framework for hypothesis testing workflows

## Important-Instruction-Reminders

- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one  
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested by the User