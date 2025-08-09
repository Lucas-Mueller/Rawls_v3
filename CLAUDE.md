# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Frohlich Experiment**: a multi-agent AI system implementing an experiment to simulate how AI agents interact with principles of justice and income distribution. The system is based on the OpenAI Agents SDK and implements a two-phase experimental design.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running the System
```bash
# Run experiment with default configuration
python main.py

# Run with custom config and output
python main.py config/custom_config.yaml results/my_experiment.json

# Run with specific config file
python main.py my_config.yaml

# Run with language-specific configurations
python main.py config/spanish_config.yaml
python main.py config/mandarin_config.yaml
python main.py config/mixed_models_example.yaml

# Example configurations with different model providers
# OpenAI models (existing behavior)
model: "gpt-4.1-mini"

# OpenRouter models (new LiteLLM integration)  
model: "google/gemini-2.5-flash"
model: "anthropic/claude-3-5-sonnet-20241022"
model: "meta-llama/llama-3.1-70b-instruct"
```

### Testing Commands
```bash
# Run all tests (includes import validation, unit tests, and integration tests)
python run_tests.py

# Run only unit tests
python run_tests.py unit

# Run only integration tests  
python run_tests.py integration

# Run specific test files using unittest
python -m unittest tests.unit.test_memory_manager -v
python -m unittest tests.integration.test_complete_experiment_flow -v
python -m unittest tests.integration.test_error_recovery -v
python -m unittest tests.integration.test_state_consistency -v
```

### Environment Requirements
```bash
# Environment file optional - create .env file in project root if needed:
OPENAI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

**Important**: 
- `OPENAI_API_KEY` is retrieved automatically for OpenAI models (e.g., "gpt-4.1-mini") - set only if needed
- `OPENROUTER_API_KEY` is retrieved automatically for OpenRouter models (e.g., "google/gemini-2.5-flash") - set only if needed
- Both API keys are handled the same way as in Open_Router_Test.py - using `os.getenv()` without strict validation

### Debugging and Development
```bash
# View experiment results and logs
ls experiment_results_*.json

# Check OpenAI trace links in experiment output
# Results include trace URLs for debugging agent interactions

# Monitor error handling during development
# All modules use standardized error categorization with automatic retry logic
```

## System Architecture

### Core Components

1. **Two-Phase Experimental Design**:
   - **Phase 1**: Individual agent familiarization with justice principles (runs in parallel)
   - **Phase 2**: Group discussion and consensus building (runs sequentially)

2. **Agent Types**:
   - **Participant Agents**: Main experimental subjects with configurable personalities, models, and temperatures
   - **Utility Agent**: Specialized agent for processing participant outputs and validating responses

3. **Justice Principles**: Four principles agents must understand and apply:
   - Maximizing floor income
   - Maximizing average income  
   - Maximizing average with floor constraint
   - Maximizing average with range constraint

### Key Features

- **Configuration-driven**: Uses YAML files to specify agent properties, experiment parameters, and distribution ranges
- **Multi-language Support**: Full experimental support for English, Spanish, and Mandarin with translated prompts and agents
- **Agent-Managed Memory**: Agents create and manage their own memory (default 50,000 characters) with complete freedom over structure and content
- **Tracing**: Uses OpenAI Agents SDK tracing with one trace per run
- **Validation**: Built-in validation for agent responses, especially for constraint specifications
- **Randomization**: Dynamic income distributions with configurable multiplier ranges

### Code Architecture

The system follows a modular, service-oriented architecture with clear separation of concerns:

#### Core Structure
- **`main.py`**: Single entry point with command-line argument parsing
- **`config/`**: YAML-based configuration system with Pydantic models
- **`core/`**: Experiment orchestration and phase management
  - `experiment_manager.py`: Main coordinator with OpenAI SDK tracing
  - `phase1_manager.py`: Parallel individual agent familiarization
  - `phase2_manager.py`: Sequential group discussion and consensus
  - `distribution_generator.py`: Dynamic income distribution creation
- **`experiment_agents/`**: AI agent implementations
  - `participant_agent.py`: Main experimental subjects with configurable personalities
  - `utility_agent.py`: Specialized agent for response parsing and validation
- **`models/`**: Pydantic data models for type safety
  - `experiment_types.py`: Core experiment structures (phases, distributions, results)
  - `principle_types.py`: Justice principle choices and rankings
  - `response_types.py`: Agent response schemas and validation
  - `logging_types.py`: Logging and tracing data structures
- **`utils/`**: Supporting utilities
  - `memory_manager.py`: Agent-managed memory with character limits and retry logic
  - `agent_centric_logger.py`: JSON logging system tracking agent inputs/outputs
  - `error_handling.py`: Standardized error categorization with automatic retry mechanisms
  - `language_manager.py`: Multi-language support with translation loading and management
  - `model_provider.py`: Model provider abstraction for OpenAI and OpenRouter integration
- **`tests/`**: Comprehensive testing infrastructure
  - `unit/`: Component-level tests (models, memory manager, distribution generator, logger)
  - `integration/`: End-to-end tests (complete experiment flow, error recovery, state consistency)
  - `integration/fixtures/`: Test fixtures and setup utilities
  - `integration/utils/`: Async testing utilities

#### Key Design Patterns
- **Configuration-driven**: All agent properties, experiment parameters, and distribution ranges specified via YAML
- **Async/Await**: Full async implementation for efficient parallel execution in Phase 1
- **Agent-Managed Memory**: Agents maintain configurable memory (default 50,000 characters) that they update themselves after each step
- **Validation System**: Built-in validation for agent responses, especially constraint specifications
- **Tracing Integration**: Uses OpenAI Agents SDK tracing with one trace per experiment run

#### Reference Documentation
- `knowledge_base/agents_sdk/`: Comprehensive OpenAI Agents SDK documentation and examples
- `master_plan.md`: Complete experimental procedure and detailed system specifications
- `translations/`: Multi-language support files (English, Spanish, Mandarin)

## Development Guidelines

- **Modularity**: System follows service-oriented architecture principles  
- **Testing**: Always run `python run_tests.py` before committing changes - includes import validation, unit tests, and integration tests with comprehensive error handling and state consistency validation
- **Simplicity**: "As simple as possible and as complex as necessary"
- **Logging**: Agent-centric JSON logging system tracking all inputs/outputs
- **Configuration**: All experimental parameters configurable via YAML files
- **Dependencies**: Core dependencies are `openai-agents`, `python-dotenv`, `pydantic`, `PyYAML` plus data analysis libraries (`pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `statsmodels`) - avoid adding unnecessary packages

## Important Implementation Details

### Error Handling & Recovery
- **Standardized Error Framework**: All modules use consistent error categorization (memory, validation, communication, system, experiment logic)
- **Automatic Retry Logic**: Configurable retry mechanisms for recoverable errors with exponential backoff
- **Error Statistics**: Comprehensive error tracking and reporting throughout experiment execution
- **Graceful Degradation**: System handles partial failures and continues when possible

### Experiment Flow
1. **Phase 1** (parallel): Individual agents familiarize with justice principles through 4 rounds of applications
2. **Phase 2** (sequential): Group discussion with random speaking order, voting mechanism, and consensus building  
3. **Results**: Complete JSON output with agent-centric logging and OpenAI trace links
4. **Error Recovery**: Built-in recovery mechanisms for memory limits, agent communication failures, and validation errors

### Agent Configuration
Each participant agent has configurable:
- `name`, `personality`, `model` (e.g., "gpt-4.1-mini")  
- `temperature`, `reasoning_enabled`, `memory_character_limit`
- System automatically creates participant agents from config and validates responses with utility agent

### Memory System
- **Agent-Managed**: Agents create and update their own memory throughout the experiment
- **Character Limit**: Default 50,000 characters (configurable via `memory_character_limit`)
- **Complete Freedom**: Agents decide what to remember and how to structure their memory
- **Error Handling**: 5 retry attempts if memory exceeds character limit, experiment aborts on failure
- **Continuous**: Memory persists across Phase 1 and Phase 2 for complete experimental continuity

### Data Validation
- Income distributions validated for positive values and proper constraint specifications
- Justice principle choices validated (principles c/d require constraint amounts)
- All agent responses parsed and validated by dedicated utility agent

### Model Provider Support
- **OpenAI Models**: Model strings without "/" use standard OpenAI Agents SDK
- **OpenRouter Models**: Model strings with "/" trigger LiteLLM integration
- **Environment Variables**: 
  - `OPENAI_API_KEY`: Retrieved automatically for OpenAI models - set only if needed
  - `OPENROUTER_API_KEY`: Retrieved automatically for OpenRouter models (those containing "/") - set only if needed
- **Mixed Configurations**: Experiments can use different model providers for different agents
- **Utility Agent Configuration**: `utility_agent_model` in config controls model for parser/validator agents

### Multi-Language Support
- **Supported Languages**: English, Spanish, and Mandarin
- **Translation Files**: Located in `translations/` directory with language-specific prompt files
- **Language Configuration**: Use language-specific config files (`spanish_config.yaml`, `mandarin_config.yaml`)
- **Agent Language**: All participant agents conduct the experiment in the configured language
- **Validation**: Utility agents parse responses in the appropriate language

### Output & Tracing
- Results saved as timestamped JSON files: `experiment_results_YYYYMMDD_HHMMSS.json`
- OpenAI tracing enabled: view at `https://platform.openai.com/traces`
- Comprehensive logging with experiment summaries