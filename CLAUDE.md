# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Frohlich Experiment**: a multi-agent AI system implementing experiments to simulate how AI agents interact with principles of justice and income distribution. The system uses the OpenAI Agents SDK and implements a two-phase experimental design:

- **Phase 1**: Individual agent familiarization with justice principles (parallel execution)
- **Phase 2**: Group discussion and consensus building (sequential execution)

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Core dependencies: openai-agents[litellm], python-dotenv, pydantic, PyYAML
# Analysis libraries: pandas, numpy, matplotlib, seaborn, scipy, statsmodels, plotly
# Additional: tqdm, diagrams
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

### Jupyter Notebook Execution
```python
# For Jupyter notebook environments, use the experiment_runner utility
from utils.experiment_runner import (
    generate_random_config, 
    run_experiment, 
    run_experiments_parallel,
    generate_and_save_configs
)

# Generate and run a single experiment
config = generate_random_config(num_agents=3, num_rounds=20)
results = run_experiment(config)

# Generate multiple config files (useful for batch experiments)
generate_and_save_configs(num_configs=10, save_path="hypothesis_2_&_4/configs/condition_1")

# Run multiple experiments in parallel
config_files = ["path/to/config1.yaml", "path/to/config2.yaml"]
results = run_experiments_parallel(config_files, max_parallel=5)
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

# Results include trace URLs for debugging agent interactions at:
# https://platform.openai.com/traces
```

## System Architecture

The system follows a modular, service-oriented architecture with the following **key design patterns**:

- **Configuration-driven**: All agent properties, experiment parameters, and distribution ranges specified via YAML
- **Async/Await**: Full async implementation for efficient parallel execution in Phase 1
- **Agent-Managed Memory**: Agents maintain configurable memory (default 50,000 characters) that they update themselves after each step
- **Validation System**: Built-in validation for agent responses, especially constraint specifications
- **Tracing Integration**: Uses OpenAI Agents SDK tracing with one trace per experiment run

### Core Components

- **Agent Types**:
  - **Participant Agents**: Main experimental subjects with configurable personalities, models, and temperatures
  - **Utility Agent**: Specialized agent for processing participant outputs and validating responses

- **Justice Principles**: Four principles agents must understand and apply:
  - Maximizing floor income, maximizing average income  
  - Maximizing average with floor constraint, maximizing average with range constraint

### Key Features

- **Multi-language Support**: Full experimental support for English, Spanish, and Mandarin
- **Original Values Mode**: Fixed predefined distributions for experimental consistency  
- **Model Provider Support**: Both OpenAI models and OpenRouter models (via LiteLLM) with mixed configurations

### Directory Structure

- **`main.py`**: Single entry point with command-line argument parsing
- **`config/`**: YAML-based configuration system with Pydantic models
- **`core/`**: Experiment orchestration and phase management
  - `experiment_manager.py`: Main coordinator with OpenAI SDK tracing
  - `phase1_manager.py`, `phase2_manager.py`: Phase-specific execution logic
  - `distribution_generator.py`: Dynamic income distribution creation
  - `original_values_data.py`: Predefined distribution situations for experimental consistency
- **`experiment_agents/`**: AI agent implementations
  - `participant_agent.py`: Main experimental subjects with configurable personalities
  - `utility_agent.py`: Specialized agent for response parsing and validation
- **`models/`**: Pydantic data models for type safety (experiment_types, principle_types, response_types, logging_types)
- **`utils/`**: Supporting utilities (memory_manager, agent_centric_logger, error_handling, language_manager, model_provider, experiment_runner)
- **`tests/`**: Unit and integration tests with fixtures and async testing utilities
- **`translations/`**: Multi-language support files (English, Spanish, Mandarin)
- **`hypothesis_2_&_4/`**: Experimental condition directory with batch configs and analysis notebooks

## Development Guidelines

- **Testing**: Always run `python run_tests.py` before committing changes
- **Configuration**: All experimental parameters configurable via YAML files
- **Dependencies**: Core dependencies are `openai-agents[litellm]`, `python-dotenv`, `pydantic`, `PyYAML` plus data analysis libraries - avoid adding unnecessary packages

## Important Implementation Details

### Original Values Mode

The system supports an "Original Values Mode" for Phase 1 that uses predefined distribution sets instead of randomly generated ones. This mode is useful for experimental consistency and comparison studies.

#### Configuration
```yaml
# Enable original values mode
original_values_mode:
  enabled: true                    # Use predefined distributions
  situation: "sample"              # Choose situation: sample, a, b, c, d
```

#### Available Situations
- **Sample**: Baseline distributions with standard 5/10/50/25/10 probability weighting
- **Situation A**: Higher upper-class probability (10%) with 10/20/40/20/10 weighting
- **Situation B**: Higher medium-low probability with 6.3/20.8/28.3/34.5/10 weighting  
- **Situation C**: Extreme high-income outlier with 1.3/4.3/58.3/26/10 weighting
- **Situation D**: Graduated middle-class focus with 5/20.8/28.3/35.8/10 weighting

#### Behavior
- **Phase 1**: Uses predefined distributions and situation-specific probabilities
- **Phase 2**: Uses normal dynamic generation (unaffected)
- **Logging**: Mode and situation are tracked in experiment results
- **Backward Compatibility**: Mode disabled by default; existing experiments unchanged

### Experiment Flow
1. **Phase 1** (parallel): Individual agents familiarize with justice principles through 4 rounds of applications
2. **Phase 2** (sequential): Group discussion with random speaking order, voting mechanism, and consensus building  
3. **Results**: Complete JSON output with agent-centric logging and OpenAI trace links

### Agent Configuration
Each participant agent has configurable:
- `name`, `personality`, `model` (e.g., "gpt-4.1-mini")  
- `temperature`, `reasoning_enabled`, `memory_character_limit`
- System automatically creates participant agents from config and validates responses with utility agent

### Error Handling & Recovery
- **Standardized Error Framework**: All modules use consistent error categorization with automatic retry logic
- **Error Statistics**: Comprehensive error tracking and reporting throughout experiment execution
- **Graceful Degradation**: System handles partial failures and continues when possible

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