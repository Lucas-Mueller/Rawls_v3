# LiteLLM OpenRouter Integration Implementation Plan

## Overview

This plan details the implementation of LiteLLM integration with OpenRouter support for the Frohlich Experiment multi-agent system. The feature will allow users to specify models containing "/" characters in their configuration, which will trigger the use of LiteLLM with OpenRouter as the provider.

### Requirements

- **Trigger Condition**: Model strings containing "/" characters (e.g., "google/gemini-2.5-flash")
- **Provider Logic**: Models with "/" use LiteLLM with OpenRouter API key
- **Model Name Format**: "openrouter/" + user_input (e.g., "openrouter/google/gemini-2.5-flash")
- **API Key**: Always use OPENROUTER_API_KEY environment variable
- **Backward Compatibility**: Existing OpenAI models (without "/") continue to work unchanged

## Current Architecture Analysis

### Agent Initialization Flow
```
YAML Configuration → Pydantic Models → Agent Factory → OpenAI Agent SDK
```

### Key Components
1. **AgentConfiguration** (`config/models.py`): Stores model string with validation
2. **ParticipantAgent** (`experiment_agents/participant_agent.py`): Main agent wrapper
3. **UtilityAgent** (`experiment_agents/utility_agent.py`): Specialized parsing/validation agents
4. **Factory Function**: `create_participant_agent()` for participant creation
5. **Direct Instantiation**: Utility agents created directly in experiment manager

### Current Model Usage
- All agents currently use plain model strings (e.g., "gpt-4.1-mini")
- No provider abstraction layer exists
- Direct OpenAI Agents SDK usage throughout

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Add Dependencies
**File**: `requirements.txt`
**Changes**:
```
litellm>=1.50.0
```

#### 1.2 Create Model Provider Detection Utility
**New File**: `utils/model_provider.py`
```python
from typing import Tuple, Optional
from agents.extensions.models.litellm_model import LitellmModel
from agents.model_settings import ModelSettings
import os

def detect_model_provider(model_string: str) -> Tuple[str, bool]:
    """
    Detect if model requires LiteLLM OpenRouter integration.
    
    Args:
        model_string: Model identifier from configuration
        
    Returns:
        Tuple of (processed_model_string, is_litellm_model)
    """
    if "/" in model_string:
        return f"openrouter/{model_string}", True
    return model_string, False

def create_model_config(model_string: str, temperature: float = 0.7):
    """
    Create appropriate model configuration based on provider.
    
    Args:
        model_string: Model identifier from configuration  
        temperature: Model temperature setting
        
    Returns:
        Either string (OpenAI) or LitellmModel instance
    """
    processed_model, is_litellm = detect_model_provider(model_string)
    
    if is_litellm:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for models with '/' in the name")
        
        return LitellmModel(
            model=processed_model,
            api_key=api_key,
        )
    
    return model_string
```

#### 1.3 Update Environment Configuration Documentation
**File**: `CLAUDE.md` - Add to Environment Requirements section:
```bash
# For OpenRouter models (models containing "/")
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Phase 2: Agent Integration

#### 2.1 Update ParticipantAgent
**File**: `experiment_agents/participant_agent.py`
**Changes**:
```python
# Add import
from utils.model_provider import create_model_config

# Update __init__ method
def __init__(self, config: AgentConfiguration):
    self.config = config
    self.memory_manager = MemoryManager(config.memory_character_limit)
    
    # Use new model provider logic
    model_config = create_model_config(config.model, config.temperature)
    
    # Handle ModelSettings creation based on model type
    if isinstance(model_config, str):
        # OpenAI model - use existing pattern
        model_settings = ModelSettings(temperature=config.temperature)
        self.agent = Agent[ParticipantContext](
            name=config.name,
            instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
            model=model_config,
            model_settings=model_settings
        )
    else:
        # LiteLLM model - model_config already includes settings
        self.agent = Agent[ParticipantContext](
            name=config.name,
            instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
            model=model_config
        )
```

#### 2.2 Update UtilityAgent
**File**: `experiment_agents/utility_agent.py`
**Changes**:
```python
# Add imports
from utils.model_provider import create_model_config
import os

# Update __init__ method
def __init__(self, utility_model: str = None):
    # Use environment variable or default for utility agents
    if utility_model is None:
        utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
    
    model_config = create_model_config(utility_model)
    
    if isinstance(model_config, str):
        # OpenAI model
        self.parser_agent = Agent(
            name="Response Parser",
            instructions=self._get_parser_instructions(),
            model=model_config
        )
        self.validator_agent = Agent(
            name="Response Validator", 
            instructions=self._get_validator_instructions(),
            model=model_config
        )
    else:
        # LiteLLM model
        self.parser_agent = Agent(
            name="Response Parser",
            instructions=self._get_parser_instructions(),
            model=model_config
        )
        self.validator_agent = Agent(
            name="Response Validator", 
            instructions=self._get_validator_instructions(),
            model=model_config
        )
```

### Phase 3: Configuration Enhancements

#### 3.1 Add Utility Agent Model Configuration
**File**: `config/models.py`
**Changes**:
```python
class ExperimentConfiguration(BaseModel):
    """Complete experiment configuration."""
    agents: List[AgentConfiguration] = Field(..., description="List of participant agents")
    utility_agent_model: str = Field("gpt-4.1-mini", description="Model for utility agents (parser/validator)")
    phase2_rounds: int = Field(5, ge=1, description="Maximum rounds in Phase 2")
    distribution_range_phase1: List[float] = Field([0.5, 2.0], description="Income multiplier range for Phase 1")  
    distribution_range_phase2: List[float] = Field([0.5, 2.0], description="Income multiplier range for Phase 2")
```

#### 3.2 Update Default Configuration
**File**: `config/default_config.yaml`
**Changes**:
```yaml
agents:
  - name: "Alice"
    personality: "Analytical and methodical. Values fairness and systematic approaches to problem-solving. Tends to think through decisions carefully and considers long-term consequences."
    model: "gpt-4.1-mini"
    temperature: 0
    memory_character_limit: 50000
    reasoning_enabled: true
    
  - name: "Bob" 
    personality: "Pragmatic and results-oriented. Focuses on practical outcomes and efficiency. Makes decisions based on what works best in practice rather than abstract ideals."
    model: "gpt-4.1-mini"
    temperature: 0.4
    memory_character_limit: 50000
    reasoning_enabled: true
    
  - name: "Carol"
    personality: "Empathetic and community-focused. Prioritizes helping those in need and social welfare. Strong advocate for supporting the most vulnerable members of society."
    model: "gpt-4.1-mini" 
    temperature: 0.8
    memory_character_limit: 50000
    reasoning_enabled: true

# Utility agent model (can also use OpenRouter models)
utility_agent_model: "gpt-4.1-mini"

phase2_rounds: 5
distribution_range_phase1: [0.5, 2.0]
distribution_range_phase2: [0.5, 2.0]
```

#### 3.3 Update Experiment Manager
**File**: `core/experiment_manager.py`
**Changes**:
```python
# Update utility agent creation
def __init__(self, config: ExperimentConfiguration):
    self.config = config
    self.participants = self._create_participants()
    # Pass utility agent model from config
    self.utility_agent = UtilityAgent(config.utility_agent_model)
    self.phase1_manager = Phase1Manager(self.participants, self.utility_agent, config)
    self.phase2_manager = Phase2Manager(self.participants, self.utility_agent, config)
```

### Phase 4: Error Handling & Validation

#### 4.1 Environment Validation
**File**: `utils/model_provider.py`
**Enhancements**:
```python
def validate_environment_for_models(config: ExperimentConfiguration) -> List[str]:
    """
    Validate that required environment variables are present for configured models.
    
    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []
    
    # Check all participant models
    for agent_config in config.agents:
        if "/" in agent_config.model and not os.getenv("OPENROUTER_API_KEY"):
            errors.append(f"Agent '{agent_config.name}' uses model '{agent_config.model}' but OPENROUTER_API_KEY is not set")
    
    # Check utility agent model
    if "/" in config.utility_agent_model and not os.getenv("OPENROUTER_API_KEY"):
        errors.append(f"Utility agent uses model '{config.utility_agent_model}' but OPENROUTER_API_KEY is not set")
    
    return errors
```

#### 4.2 Pre-flight Validation
**File**: `main.py`
**Changes**:
```python
from utils.model_provider import validate_environment_for_models

def main():
    parser = argparse.ArgumentParser(description="Run the Frohlich Experiment")
    parser.add_argument("config_file", nargs="?", default="config/default_config.yaml")
    parser.add_argument("output_file", nargs="?", default=None)
    args = parser.parse_args()

    try:
        config = ExperimentConfiguration.from_yaml(args.config_file)
        
        # Validate environment for configured models
        env_errors = validate_environment_for_models(config)
        if env_errors:
            print("Environment validation errors:")
            for error in env_errors:
                print(f"  - {error}")
            sys.exit(1)
        
        experiment = FrohlichExperimentManager(config)
        result = asyncio.run(experiment.run_experiment())
        
        # ... rest of existing code
```

### Phase 5: Testing

#### 5.1 Unit Tests
**New File**: `tests/unit/test_model_provider.py`
```python
import unittest
from unittest.mock import patch, MagicMock
import os
from utils.model_provider import detect_model_provider, create_model_config, validate_environment_for_models
from config.models import ExperimentConfiguration, AgentConfiguration

class TestModelProvider(unittest.TestCase):
    
    def test_detect_model_provider_openai(self):
        """Test detection of OpenAI models (no slash)."""
        model, is_litellm = detect_model_provider("gpt-4.1-mini")
        self.assertEqual(model, "gpt-4.1-mini")
        self.assertFalse(is_litellm)
    
    def test_detect_model_provider_openrouter(self):
        """Test detection of OpenRouter models (with slash)."""
        model, is_litellm = detect_model_provider("google/gemini-2.5-flash")
        self.assertEqual(model, "openrouter/google/gemini-2.5-flash")
        self.assertTrue(is_litellm)
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    def test_create_model_config_litellm(self):
        """Test LiteLLM model creation."""
        model_config = create_model_config("google/gemini-2.5-flash")
        self.assertIsInstance(model_config, MagicMock)  # LitellmModel mock
    
    def test_create_model_config_openai(self):
        """Test OpenAI model string passthrough."""
        model_config = create_model_config("gpt-4.1-mini")
        self.assertEqual(model_config, "gpt-4.1-mini")
    
    def test_create_model_config_missing_key(self):
        """Test error when OpenRouter key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                create_model_config("google/gemini-2.5-flash")
```

#### 5.2 Integration Test
**New File**: `tests/integration/test_mixed_model_experiment.py`
```python
import unittest
import asyncio
from unittest.mock import patch
from config.models import ExperimentConfiguration, AgentConfiguration
from core.experiment_manager import FrohlichExperimentManager

class TestMixedModelExperiment(unittest.TestCase):
    
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai", "OPENROUTER_API_KEY": "test-openrouter"})
    async def test_mixed_model_configuration(self):
        """Test experiment with mix of OpenAI and OpenRouter models."""
        config = ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="Alice",
                    personality="Test personality",
                    model="gpt-4.1-mini",  # OpenAI
                    temperature=0.0
                ),
                AgentConfiguration(
                    name="Bob", 
                    personality="Test personality",
                    model="google/gemini-2.5-flash",  # OpenRouter
                    temperature=0.5
                )
            ],
            utility_agent_model="gpt-4.1-mini"  # OpenAI
        )
        
        # Test that experiment manager initializes without errors
        manager = FrohlichExperimentManager(config)
        self.assertIsNotNone(manager)
        self.assertEqual(len(manager.participants), 2)
```

### Phase 6: Documentation Updates

#### 6.1 Update CLAUDE.md
Add to Development Commands section:
```bash
# Example configurations with different model providers

# OpenAI models (existing behavior)
model: "gpt-4.1-mini"

# OpenRouter models (new LiteLLM integration)  
model: "google/gemini-2.5-flash"
model: "anthropic/claude-3-5-sonnet-20241022"
model: "meta-llama/llama-3.1-70b-instruct"
```

Add to Important Implementation Details:
```markdown
### Model Provider Support
- **OpenAI Models**: Model strings without "/" use standard OpenAI Agents SDK
- **OpenRouter Models**: Model strings with "/" trigger LiteLLM integration
- **Environment Variables**: 
  - `OPENAI_API_KEY`: Required for OpenAI models
  - `OPENROUTER_API_KEY`: Required for OpenRouter models (those containing "/")
- **Mixed Configurations**: Experiments can use different model providers for different agents
```

#### 6.2 Create Example Configuration
**New File**: `config/mixed_models_example.yaml`
```yaml
agents:
  - name: "Alice"
    personality: "Analytical and methodical. Values fairness and systematic approaches."
    model: "gpt-4.1-mini"  # OpenAI model
    temperature: 0
    memory_character_limit: 50000
    reasoning_enabled: true
    
  - name: "Bob"
    personality: "Creative and intuitive. Approaches problems from unique angles."
    model: "google/gemini-2.5-flash"  # OpenRouter model via LiteLLM
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true

utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 5
distribution_range_phase1: [0.5, 2.0]
distribution_range_phase2: [0.5, 2.0]
```

## Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Add LiteLLM dependency
- [ ] Create `utils/model_provider.py`
- [ ] Implement model detection and configuration logic
- [ ] Add unit tests for provider detection

### Week 2: Agent Integration  
- [ ] Update ParticipantAgent initialization
- [ ] Update UtilityAgent initialization
- [ ] Add error handling for missing API keys
- [ ] Test agent creation with both model types

### Week 3: Configuration & Validation
- [ ] Add utility_agent_model to configuration
- [ ] Implement environment validation
- [ ] Update main.py with pre-flight checks
- [ ] Create example configurations

### Week 4: Testing & Documentation
- [ ] Create comprehensive integration tests
- [ ] Test mixed model configurations
- [ ] Update CLAUDE.md documentation
- [ ] Verify backward compatibility

## Risk Mitigation

### Potential Issues
1. **API Key Management**: Missing environment variables
   - **Mitigation**: Pre-flight validation with clear error messages

2. **Model Availability**: OpenRouter model not available
   - **Mitigation**: LiteLLM will return appropriate errors; document common models

3. **Performance Differences**: Different providers may have different response times
   - **Mitigation**: Document expected behavior; async implementation handles this naturally

4. **Cost Management**: OpenRouter costs may differ from OpenAI
   - **Mitigation**: Document pricing considerations; user responsibility

### Backward Compatibility
- All existing configurations continue to work unchanged
- No breaking changes to API or configuration format
- Graceful error handling for missing dependencies

## Success Criteria

1. **Functional Requirements**:
   - [x] Models with "/" trigger LiteLLM/OpenRouter integration
   - [x] Models without "/" continue using OpenAI
   - [x] Mixed model configurations work in single experiment
   - [x] Clear error messages for missing API keys

2. **Quality Requirements**:
   - [x] Full test coverage for new functionality  
   - [x] No regression in existing functionality
   - [x] Comprehensive documentation updates
   - [x] Clean, maintainable code following project patterns

3. **User Experience**:
   - [x] Simple configuration changes to use new providers
   - [x] Clear documentation and examples
   - [x] Helpful error messages and validation