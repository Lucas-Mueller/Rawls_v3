# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Frohlich Experiment is a Python-based framework for conducting experiments with AI agents simulating distributive justice scenarios. It's inspired by economist Norman Frohlich's experiments and implements a "veil of ignorance" scenario where AI agents engage in two-phase experiments to reach consensus on principles of justice.

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

## Multi-Language Support

The framework supports English, Spanish, and Mandarin experiments:
- Prompts are managed via `translations/` JSON files
- Language manager handles localization (`utils/language_manager.py`)
- Agent language preferences configured per-agent in YAML

## Voting Detection Modes

### Simple Mode
- Agents express preferences using "My preference is [principle]" 
- Consensus reached when all agents state matching preferences
- Faster, preference-based detection

### Complex Mode  
- Formal voting system with "Let's vote" triggers
- Two-stage process: vote initiation + confirmation, then secret ballot
- Requires unanimous confirmation and voting participation

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