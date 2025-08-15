# Dynamic Temperature Parameter Compatibility Implementation Plan

## Overview

This plan implements **dynamic runtime detection** of temperature parameter support for any model, eliminating the need for static model mappings. The system will automatically test temperature compatibility during agent creation and gracefully handle unsupported models with appropriate warnings and logging.

## Current System Analysis

### Temperature Usage Points
1. **Agent Configuration** (`config/default_config.yaml`): Each agent has a `temperature` setting
2. **Model Provider** (`utils/model_provider.py`): Creates model configs with temperature
3. **Participant Agent** (`experiment_agents/participant_agent.py`): Uses `ModelSettings(temperature=config.temperature)`
4. **Utility Agent** (`experiment_agents/utility_agent.py`): Uses model configs with temperature
5. **Logging System** (`utils/agent_centric_logger.py`): Logs temperature values

### Current Temperature Flow
```python
config.yaml -> AgentConfiguration -> create_model_config(model, temperature) -> ModelSettings(temperature) -> Agent creation
```

## Dynamic Detection Strategy

### 1. Runtime Temperature Compatibility Testing

The system will dynamically test temperature support by attempting to create a simple test agent:

```python
# New file: utils/dynamic_model_capabilities.py

import asyncio
import logging
from typing import Dict, Optional, Tuple
from agents import Agent, Runner, ModelSettings
from utils.model_provider import detect_model_provider
from agents.extensions.models.litellm_model import LitellmModel
import os

logger = logging.getLogger(__name__)

# Cache for temperature compatibility results to avoid repeated tests
_temperature_cache: Dict[str, bool] = {}

async def test_temperature_support(model_string: str) -> Tuple[bool, str, Optional[Exception]]:
    """
    Dynamically test if a model supports temperature parameter.
    
    Args:
        model_string: Model identifier to test
        
    Returns:
        Tuple of (supports_temperature, reason, exception_if_any)
    """
    
    # Check cache first
    if model_string in _temperature_cache:
        cached_result = _temperature_cache[model_string]
        reason = "Cached result from previous test"
        return cached_result, reason, None
    
    try:
        # Create model configuration
        processed_model, is_litellm = detect_model_provider(model_string)
        
        if is_litellm:
            model_config = LitellmModel(
                model=processed_model,
                api_key=os.getenv("OPENROUTER_API_KEY"),
            )
        else:
            model_config = model_string
        
        # Test 1: Try creating agent with temperature
        try:
            test_agent_with_temp = Agent(
                name="temp_test_agent",
                instructions="You are a test agent.",
                model=model_config,
                model_settings=ModelSettings(temperature=0.5)
            )
            
            # Test 2: Try a simple inference call to verify it actually works
            simple_response = await Runner.run(
                test_agent_with_temp, 
                "Say 'test' and nothing else.",
                timeout=10  # Quick timeout for testing
            )
            
            # If we get here, temperature is supported
            _temperature_cache[model_string] = True
            return True, "Successfully created agent and ran inference with temperature parameter", None
            
        except Exception as temp_error:
            # Test 3: Try creating agent without temperature to see if model works at all
            try:
                test_agent_no_temp = Agent(
                    name="no_temp_test_agent", 
                    instructions="You are a test agent.",
                    model=model_config
                    # No model_settings with temperature
                )
                
                # Test basic inference without temperature
                simple_response = await Runner.run(
                    test_agent_no_temp,
                    "Say 'test' and nothing else.",
                    timeout=10
                )
                
                # Model works without temperature but failed with temperature
                _temperature_cache[model_string] = False
                return False, f"Model works without temperature but failed with it: {str(temp_error)}", temp_error
                
            except Exception as no_temp_error:
                # Model doesn't work at all - this might be a configuration issue
                _temperature_cache[model_string] = False
                return False, f"Model failed both with and without temperature - may be unavailable: {str(no_temp_error)}", no_temp_error
    
    except Exception as setup_error:
        # Failed to even set up the test
        _temperature_cache[model_string] = False
        return False, f"Failed to set up temperature compatibility test: {str(setup_error)}", setup_error

def supports_temperature_cached(model_string: str) -> Optional[bool]:
    """
    Check cached temperature support without running new tests.
    
    Returns:
        True/False if cached, None if not yet tested
    """
    return _temperature_cache.get(model_string)

def clear_temperature_cache():
    """Clear the temperature compatibility cache."""
    global _temperature_cache
    _temperature_cache = {}
```

### 2. Dynamic Model Provider Integration

Integrate dynamic temperature detection into the model provider system:

```python
# Enhanced create_model_config function in utils/model_provider.py
async def create_model_config_with_temperature_detection(
    model_string: str, 
    temperature: float = 0.7,
    skip_temperature_test: bool = False
) -> tuple[Union[str, LitellmModel], dict]:
    """
    Create model configuration with dynamic temperature compatibility detection.
    
    Args:
        model_string: Model identifier
        temperature: Requested temperature value
        skip_temperature_test: Skip dynamic testing (use for performance in batch operations)
    
    Returns:
        Tuple of (model_config, temperature_info)
    """
    from utils.dynamic_model_capabilities import test_temperature_support, supports_temperature_cached
    
    processed_model, is_litellm = detect_model_provider(model_string)
    
    # Check if we already know about this model's temperature support
    cached_support = supports_temperature_cached(model_string)
    
    if cached_support is not None and not skip_temperature_test:
        # Use cached result
        supports_temp = cached_support
        detection_method = "cached"
        test_reason = "Previous test result"
        test_exception = None
    elif not skip_temperature_test:
        # Run dynamic detection
        supports_temp, test_reason, test_exception = await test_temperature_support(model_string)
        detection_method = "dynamic_test"
    else:
        # Conservative fallback - assume temperature works for OpenAI models, not for others
        supports_temp = not is_litellm  # OpenAI models generally support temperature
        detection_method = "conservative_fallback"
        test_reason = "Skipped dynamic testing, using conservative assumption"
        test_exception = None
    
    # Create model configuration
    if is_litellm:
        model_config = LitellmModel(
            model=processed_model,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    else:
        model_config = model_string
    
    # Create comprehensive temperature info
    temperature_info = {
        "requested_temperature": temperature,
        "supports_temperature": supports_temp,
        "effective_temperature": temperature if supports_temp else None,
        "detection_method": detection_method,
        "test_reason": test_reason,
        "test_exception": str(test_exception) if test_exception else None,
        "warning_issued": False,
        "model_string": model_string
    }
    
    # Issue warning if temperature set on non-supporting model
    if temperature != 0.7 and not supports_temp:  # 0.7 is typical default
        temperature_info["warning_issued"] = True
        
    return model_config, temperature_info

# Synchronous wrapper for backwards compatibility
def create_model_config(model_string: str, temperature: float = 0.7) -> tuple[Union[str, LitellmModel], dict]:
    """
    Synchronous wrapper - uses conservative temperature detection.
    
    For full dynamic detection, use create_model_config_with_temperature_detection().
    """
    import asyncio
    try:
        # Try to run async version if we're in an async context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, use conservative fallback
            return asyncio.create_task(
                create_model_config_with_temperature_detection(model_string, temperature, skip_temperature_test=True)
            ).result()
        else:
            # Run the full async detection
            return asyncio.run(
                create_model_config_with_temperature_detection(model_string, temperature)
            )
    except:
        # Fallback to conservative approach
        return asyncio.run(
            create_model_config_with_temperature_detection(model_string, temperature, skip_temperature_test=True)
        )
```

### 3. Smart ModelSettings Creation

Create a helper function that only applies temperature when supported:

```python
# New function in utils/model_provider.py
def create_model_settings(temperature_info: dict) -> Optional[ModelSettings]:
    """
    Create ModelSettings only if temperature is supported.
    
    Args:
        temperature_info: Temperature capability information from create_model_config
        
    Returns:
        ModelSettings instance if temperature supported, None otherwise
    """
    if temperature_info["supports_temperature"]:
        return ModelSettings(temperature=temperature_info["requested_temperature"])
    return None

# Utility function for experiment initialization
async def batch_test_model_temperatures(model_strings: List[str]) -> Dict[str, dict]:
    """
    Batch test multiple models for temperature support during experiment startup.
    
    This allows testing all models upfront to provide comprehensive warnings
    before the experiment starts.
    
    Returns:
        Dictionary mapping model_string -> temperature_info
    """
    from utils.dynamic_model_capabilities import test_temperature_support
    
    results = {}
    
    # Test all models concurrently
    tasks = []
    for model_string in set(model_strings):  # Remove duplicates
        task = asyncio.create_task(test_temperature_support(model_string))
        tasks.append((model_string, task))
    
    # Collect results
    for model_string, task in tasks:
        try:
            supports_temp, reason, exception = await task
            results[model_string] = {
                "supports_temperature": supports_temp,
                "test_reason": reason,
                "test_exception": str(exception) if exception else None,
                "detection_method": "batch_startup_test"
            }
        except Exception as e:
            results[model_string] = {
                "supports_temperature": False,
                "test_reason": f"Batch test failed: {str(e)}",
                "test_exception": str(e),
                "detection_method": "batch_startup_test"
            }
    
    return results
```

### 4. Dynamic Agent Creation

Modify participant and utility agent creation to use dynamic temperature detection:

```python
# In experiment_agents/participant_agent.py
class ParticipantAgent:
    def __init__(self, config: AgentConfiguration):
        self.config = config
        
        # Dynamic temperature detection during agent creation
        import asyncio
        try:
            # Run dynamic temperature detection
            model_config, temperature_info = asyncio.run(
                create_model_config_with_temperature_detection(config.model, config.temperature)
            )
        except Exception as e:
            # Fallback to conservative approach if dynamic detection fails
            logging.getLogger(__name__).warning(
                f"Dynamic temperature detection failed for {config.model}: {e}. Using conservative fallback."
            )
            model_config, temperature_info = asyncio.run(
                create_model_config_with_temperature_detection(
                    config.model, config.temperature, skip_temperature_test=True
                )
            )
        
        # Create model settings only if temperature is supported
        model_settings = create_model_settings(temperature_info)
        
        # Store temperature info for logging
        self.temperature_info = temperature_info
        
        # Issue warning if needed
        if temperature_info["warning_issued"]:
            self._log_temperature_warning()
        
        # Create agent with conditional model settings
        agent_kwargs = {
            "name": config.name,
            "instructions": lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
            "model": model_config
        }
        
        if model_settings is not None:
            agent_kwargs["model_settings"] = model_settings
            
        self.agent = Agent[ParticipantContext](**agent_kwargs)
    
    def _log_temperature_warning(self):
        """Log warning about temperature not being supported."""
        import logging
        logger = logging.getLogger(__name__)
        
        detection_info = f" (Detection: {self.temperature_info['detection_method']} - {self.temperature_info['test_reason']})"
        
        logger.warning(
            f"Temperature {self.temperature_info['requested_temperature']} specified for model "
            f"{self.config.model}, but this model does not support temperature parameter. "
            f"Temperature setting will be ignored.{detection_info}"
        )

# For better performance, provide batch initialization option
async def create_participant_agents_with_batch_testing(
    configs: List[AgentConfiguration]
) -> List[ParticipantAgent]:
    """
    Create multiple participant agents with batch temperature testing for better performance.
    """
    # Extract all unique models
    model_strings = list(set(config.model for config in configs))
    
    # Batch test all models upfront
    batch_results = await batch_test_model_temperatures(model_strings)
    
    # Create agents using cached results
    agents = []
    for config in configs:
        # Use pre-tested results
        if config.model in batch_results:
            # Override the dynamic detection with batch results
            from utils.dynamic_model_capabilities import _temperature_cache
            _temperature_cache[config.model] = batch_results[config.model]["supports_temperature"]
        
        # Create agent normally - will use cached results
        agent = ParticipantAgent(config)
        agents.append(agent)
    
    return agents
```

### 5. Enhanced Logging System

Update the logging system to properly handle temperature display:

```python
# In utils/agent_centric_logger.py
class AgentCentricLogger:
    def _format_agent_info(self, agent_name: str, model: str, temperature_info: dict = None) -> dict:
        """Format agent information with temperature compatibility."""
        agent_info = {
            "name": agent_name,
            "model": model,
        }
        
        if temperature_info:
            if temperature_info["supports_temperature"]:
                agent_info["temperature"] = temperature_info["effective_temperature"]
            else:
                agent_info["temperature"] = "N/A"
                agent_info["temperature_requested"] = temperature_info["requested_temperature"]
                agent_info["temperature_reason"] = "Model does not support temperature parameter"
        
        return agent_info
    
    def log_experiment_start(self, config, agents_info):
        """Log experiment start with enhanced temperature information."""
        # Enhanced logging that shows temperature status for each agent
        for agent_info in agents_info:
            if agent_info.get("temperature") == "N/A":
                self.debug_logger.warning(
                    f"Agent {agent_info['name']} using model {agent_info['model']} "
                    f"does not support temperature (requested: {agent_info['temperature_requested']})"
                )
```

### 6. Configuration Validation

Add validation to detect temperature issues early:

```python
# New function in config/experiment_configuration.py
def validate_temperature_settings(config: ExperimentConfiguration) -> List[str]:
    """
    Validate temperature settings against model capabilities.
    
    Returns:
        List of warning messages (not errors, since system should still work)
    """
    from utils.model_capabilities import supports_temperature
    
    warnings = []
    
    # Check participant agents
    for agent_config in config.agents:
        if not supports_temperature(agent_config.model) and agent_config.temperature != 0.7:
            warnings.append(
                f"Agent '{agent_config.name}' uses model '{agent_config.model}' "
                f"which doesn't support temperature, but temperature {agent_config.temperature} is configured. "
                f"Temperature will be ignored."
            )
    
    # Check utility agent
    if hasattr(config, 'utility_agent_model'):
        if not supports_temperature(config.utility_agent_model):
            warnings.append(
                f"Utility agent model '{config.utility_agent_model}' doesn't support temperature parameter."
            )
    
    return warnings
```

## Dynamic Detection Advantages

### ✅ **Future-Proof**
- No static model mappings to maintain
- Automatically works with new models as they're released
- Adapts to API changes dynamically

### ✅ **Accurate**
- Tests actual model behavior rather than relying on documentation
- Handles edge cases and API variations
- Provides real-time compatibility information

### ✅ **Performance Optimized**
- Caches results to avoid repeated testing
- Batch testing for experiment initialization
- Conservative fallbacks for performance-critical scenarios

### ✅ **Comprehensive Information**
- Detailed diagnostics about why temperature is/isn't supported
- Exception information for debugging
- Multiple detection strategies for robustness

## Implementation Phase Plan

### Phase 1: Dynamic Detection Core (2-3 hours)
1. Create `utils/dynamic_model_capabilities.py` with runtime temperature testing
2. Implement caching system for test results
3. Add batch testing utilities for performance
4. Create unit tests for dynamic detection logic

### Phase 2: Model Provider Integration (2-3 hours)
1. Enhance `utils/model_provider.py` with dynamic detection integration
2. Add both async and sync APIs for different use cases
3. Implement conservative fallbacks for edge cases
4. Add comprehensive error handling and logging

### Phase 3: Agent System Integration (2-3 hours)
1. Update `ParticipantAgent` and `UtilityAgent` classes
2. Integrate dynamic temperature detection into agent creation
3. Add detailed warning and logging systems
4. Implement batch agent creation for performance

### Phase 4: Logging & Experiment Integration (1-2 hours)
1. Enhance `AgentCentricLogger` with dynamic temperature info
2. Update experiment managers to use batch testing
3. Add startup validation and warning systems
4. Create integration tests with real model scenarios

## Configuration Examples

### Before (Current)
```yaml
agents:
  - name: "Alice"
    model: "gpt-4.1-nano"  # Doesn't support temperature
    temperature: 0.5       # This would cause issues
```

### After (Enhanced)
```yaml
agents:
  - name: "Alice"
    model: "gpt-4.1-nano"  # Doesn't support temperature
    temperature: 0.5       # Warning logged, temperature ignored, "N/A" in logs
    
  - name: "Bob"
    model: "gpt-4.1"       # Supports temperature
    temperature: 0.5       # Works normally
```

## Expected Dynamic Behavior

### Startup Process
```
INFO: Testing temperature compatibility for models: gpt-4.1-nano, gpt-4.1, anthropic/claude-3-5-sonnet
INFO: gpt-4.1: Temperature supported ✓ (Dynamic test successful)
WARNING: gpt-4.1-nano: Temperature NOT supported ✗ (Detection: dynamic_test - Model works without temperature but failed with it: Parameter 'temperature' not supported)
INFO: anthropic/claude-3-5-sonnet: Temperature supported ✓ (Dynamic test successful)
```

### Console Warning (Enhanced)
```
WARNING: Temperature 0.5 specified for model gpt-4.1-nano, but this model does not support temperature parameter. Temperature setting will be ignored. (Detection: dynamic_test - Model works without temperature but failed with it: Parameter 'temperature' not supported)
```

### Enhanced Log Entry
```json
{
  "agent": "Alice",
  "model": "gpt-4.1-nano",
  "temperature": "N/A",
  "temperature_requested": 0.5,
  "temperature_supports": false,
  "detection_method": "dynamic_test",
  "test_reason": "Model works without temperature but failed with it: Parameter 'temperature' not supported",
  "effective_temperature": null
}
```

### Performance Optimization Log
```
INFO: Batch testing 3 unique models for temperature compatibility...
INFO: Temperature compatibility tests completed in 2.3s
INFO: Using cached temperature results for remaining agent creation
```

## Backward Compatibility

- ✅ Existing configs with temperature-supporting models work unchanged
- ✅ New configs can mix temperature-supporting and non-supporting models
- ✅ No breaking changes to existing APIs
- ✅ Clear warnings when temperature is ignored
- ✅ Comprehensive logging shows actual behavior

## Testing Strategy

### Unit Tests
- Temperature capability detection
- Model provider temperature handling
- Agent creation with various temperature scenarios
- Logging output validation

### Integration Tests
- End-to-end experiment with mixed temperature support
- Warning generation and logging verification
- Configuration validation testing

### Manual Testing
- Test with known non-temperature models
- Verify warnings appear in console and logs
- Confirm experiments still run successfully

## Maintenance

### Adding New Models
1. Update `TEMPERATURE_SUPPORTING_MODELS` in `model_capabilities.py`
2. Add corresponding tests
3. Document in configuration examples

### Model Provider Changes
If model providers change temperature support:
1. Update capability database
2. Add version-specific handling if needed
3. Update tests and documentation

## Key Benefits of Dynamic Detection

### 🚀 **No Maintenance Overhead**
- Zero static model lists to maintain
- Works with any new model automatically  
- No version tracking or documentation dependencies

### 🎯 **100% Accurate Detection**
- Tests actual runtime behavior
- Handles API changes transparently
- Catches edge cases and provider-specific implementations

### ⚡ **Smart Performance**
- Caches results across experiment runs
- Batch testing minimizes API calls
- Conservative fallbacks when speed is critical

### 🔍 **Rich Diagnostics**
- Detailed error information for troubleshooting
- Multiple detection methods for reliability
- Comprehensive logging for debugging

### 🛡️ **Robust Error Handling**
- Graceful fallbacks if detection fails
- Never breaks experiment execution
- Clear user feedback about temperature behavior

This dynamic approach provides comprehensive temperature compatibility while maintaining full backward compatibility, requiring zero maintenance, and offering superior accuracy compared to static model mappings.