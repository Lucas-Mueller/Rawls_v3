"""
Dynamic model capability detection for runtime temperature parameter support testing.

This module provides utilities to dynamically test whether models support the temperature
parameter by creating test agents and running simple inference calls.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple, List
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
    
    logger.info(f"Testing temperature support for model: {model_string}")
    
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
            logger.debug(f"Creating test agent with temperature for {model_string}")
            test_agent_with_temp = Agent(
                name="temp_test_agent",
                instructions="You are a test agent. Respond concisely.",
                model=model_config,
                model_settings=ModelSettings(temperature=0.5)
            )
            
            # Test 2: Try a simple inference call to verify it actually works
            logger.debug(f"Running test inference with temperature for {model_string}")
            simple_response = await asyncio.wait_for(
                Runner.run(test_agent_with_temp, "Say 'test' and nothing else."),
                timeout=30  # 30 second timeout for testing
            )
            
            # If we get here, temperature is supported
            logger.info(f"✅ {model_string}: Temperature supported (test successful)")
            _temperature_cache[model_string] = True
            return True, "Successfully created agent and ran inference with temperature parameter", None
            
        except Exception as temp_error:
            logger.debug(f"Temperature test failed for {model_string}: {temp_error}")
            
            # Test 3: Try creating agent without temperature to see if model works at all
            try:
                logger.debug(f"Creating test agent without temperature for {model_string}")
                test_agent_no_temp = Agent(
                    name="no_temp_test_agent", 
                    instructions="You are a test agent. Respond concisely.",
                    model=model_config
                    # No model_settings with temperature
                )
                
                # Test basic inference without temperature
                logger.debug(f"Running test inference without temperature for {model_string}")
                simple_response = await asyncio.wait_for(
                    Runner.run(test_agent_no_temp, "Say 'test' and nothing else."),
                    timeout=30
                )
                
                # Model works without temperature but failed with temperature
                logger.warning(f"⚠️  {model_string}: Temperature NOT supported (works without temperature)")
                _temperature_cache[model_string] = False
                return False, f"Model works without temperature but failed with it: {str(temp_error)}", temp_error
                
            except Exception as no_temp_error:
                # Model doesn't work at all - this might be a configuration issue
                logger.error(f"❌ {model_string}: Model failed both with and without temperature")
                _temperature_cache[model_string] = False
                return False, f"Model failed both with and without temperature - may be unavailable: {str(no_temp_error)}", no_temp_error
    
    except Exception as setup_error:
        # Failed to even set up the test
        logger.error(f"❌ {model_string}: Failed to set up temperature test: {setup_error}")
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
    _temperature_cache.clear()
    logger.info("Temperature compatibility cache cleared")

async def batch_test_model_temperatures(model_strings: List[str]) -> Dict[str, dict]:
    """
    Batch test multiple models for temperature support during experiment startup.
    
    This allows testing all models upfront to provide comprehensive warnings
    before the experiment starts.
    
    Returns:
        Dictionary mapping model_string -> temperature_info
    """
    results = {}
    unique_models = list(set(model_strings))  # Remove duplicates
    
    if not unique_models:
        return results
    
    logger.info(f"Batch testing {len(unique_models)} unique models for temperature compatibility...")
    start_time = asyncio.get_event_loop().time()
    
    # Test all models concurrently
    tasks = []
    for model_string in unique_models:
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
            logger.error(f"Batch test failed for {model_string}: {e}")
            results[model_string] = {
                "supports_temperature": False,
                "test_reason": f"Batch test failed: {str(e)}",
                "test_exception": str(e),
                "detection_method": "batch_startup_test"
            }
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    logger.info(f"Temperature compatibility tests completed in {duration:.1f}s")
    
    return results

async def create_agent_with_temperature_retry(
    agent_class, 
    model_string: str, 
    temperature: Optional[float],
    agent_kwargs: dict
) -> tuple:
    """
    Create agent with automatic temperature error handling and retry.
    
    Process:
    1. Check cache first - if model known to not support temperature, skip it
    2. Try creating agent with temperature
    3. If temperature error during first use → Add to cache → Recreate agent without temperature
    4. Return (agent, temperature_info)
    
    Args:
        agent_class: Agent class to instantiate
        model_string: Model identifier for cache lookup
        temperature: Requested temperature (None to skip)
        agent_kwargs: Base kwargs for agent creation
        
    Returns:
        Tuple of (agent, temperature_info_dict)
    """
    from utils.model_provider import detect_model_provider
    from agents.extensions.models.litellm_model import LitellmModel
    from agents import ModelSettings
    
    # Step 1: Check cache first
    cached_support = supports_temperature_cached(model_string)
    
    if cached_support is False:
        # We know this model doesn't support temperature - skip it from the start
        logger.info(f"Cache: {model_string} doesn't support temperature, creating agent without temperature")
        
        # Create agent without temperature
        agent = agent_class(**agent_kwargs)
        
        temp_info = {
            "requested_temperature": temperature,
            "supports_temperature": False,
            "effective_temperature": None,
            "detection_method": "cached_no_support",
            "was_retried": False,
            "error_message": None
        }
        
        return agent, temp_info
    
    # Step 2: Create model config
    processed_model, is_litellm = detect_model_provider(model_string)
    
    if is_litellm:
        model_config = LitellmModel(
            model=processed_model,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    else:
        model_config = model_string
    
    # Prepare agent kwargs with model
    final_kwargs = agent_kwargs.copy()
    final_kwargs["model"] = model_config
    
    # Step 3: Try with temperature first (if temperature provided and not known to fail)
    if temperature is not None and cached_support is not False:
        try:
            logger.debug(f"Creating agent with temperature {temperature} for {model_string}")
            
            # Add temperature to model settings
            final_kwargs["model_settings"] = ModelSettings(temperature=temperature)
            
            # Create agent
            agent = agent_class(**final_kwargs)
            
            # Test the agent with a simple call to trigger any temperature errors
            test_prompt = "Say 'test' and nothing else."
            
            # Try with context first (for ParticipantAgent), fallback to without context
            try:
                from models import ParticipantContext, ExperimentPhase
                test_context = ParticipantContext(
                    name="test_agent",
                    role_description="Test agent for temperature detection",
                    bank_balance=0.0,
                    memory="",
                    round_number=0,
                    phase=ExperimentPhase.PHASE_1,
                    memory_character_limit=1000
                )
                await Runner.run(agent, test_prompt, context=test_context)
            except Exception as ctx_error:
                # If context doesn't work, try without context (for regular Agent)
                try:
                    await Runner.run(agent, test_prompt)
                except Exception as no_ctx_error:
                    # Re-raise the original context error since that's more likely to be the intended usage
                    raise ctx_error
            
            # Success with temperature - update cache if not already known
            if cached_support is None:
                _temperature_cache[model_string] = True
                logger.info(f"✅ {model_string} supports temperature (discovered during creation)")
            
            temp_info = {
                "requested_temperature": temperature,
                "supports_temperature": True,
                "effective_temperature": temperature,
                "detection_method": "successful_creation",
                "was_retried": False,
                "error_message": None
            }
            
            return agent, temp_info
            
        except Exception as e:
            error_message = str(e)
            
            # Step 4: Check if this is the specific temperature error
            if is_temperature_not_supported_error(e):
                logger.warning(f"🔄 {model_string}: Temperature not supported error detected - recreating without temperature")
                
                # Step 5: Add to cache immediately
                _temperature_cache[model_string] = False
                logger.info(f"Added {model_string} to no-temperature-support cache")
                
                # Step 6: Retry without temperature
                try:
                    logger.info(f"Recreating agent without temperature for {model_string}")
                    
                    # Remove temperature from kwargs
                    retry_kwargs = agent_kwargs.copy()
                    retry_kwargs["model"] = model_config
                    # Don't add model_settings with temperature
                    
                    agent = agent_class(**retry_kwargs)
                    
                    # Test the agent without temperature
                    test_prompt = "Say 'test' and nothing else."
                    
                    # Try with context first (for ParticipantAgent), fallback to without context
                    try:
                        from models import ParticipantContext, ExperimentPhase
                        test_context = ParticipantContext(
                            name="test_agent",
                            role_description="Test agent for temperature detection",
                            bank_balance=0.0,
                            memory="",
                            round_number=0,
                            phase=ExperimentPhase.PHASE_1,
                            memory_character_limit=1000
                        )
                        await Runner.run(agent, test_prompt, context=test_context)
                    except Exception as ctx_error:
                        # If context doesn't work, try without context (for regular Agent)
                        try:
                            await Runner.run(agent, test_prompt)
                        except Exception as no_ctx_error:
                            # Re-raise the original context error since that's more likely to be the intended usage
                            raise ctx_error
                    
                    logger.info(f"✅ {model_string}: Success after removing temperature parameter")
                    
                    temp_info = {
                        "requested_temperature": temperature,
                        "supports_temperature": False,
                        "effective_temperature": None,
                        "detection_method": "error_retry_success",
                        "was_retried": True,
                        "error_message": f"Temperature not supported: {error_message}"
                    }
                    
                    return agent, temp_info
                    
                except Exception as retry_error:
                    logger.error(f"❌ {model_string}: Failed even after removing temperature: {retry_error}")
                    raise retry_error
            else:
                # Different error - re-raise
                logger.error(f"❌ {model_string}: Non-temperature related error: {error_message}")
                raise e
    
    # Step 7: No temperature requested or known not to support - create without temperature
    else:
        logger.debug(f"Creating agent without temperature for {model_string}")
        agent = agent_class(**final_kwargs)
        
        temp_info = {
            "requested_temperature": temperature,
            "supports_temperature": cached_support if cached_support is not None else True,  # Assume true if no temp requested
            "effective_temperature": None,
            "detection_method": "no_temperature_requested",
            "was_retried": False,
            "error_message": None
        }
        
        return agent, temp_info


def is_temperature_not_supported_error(exception: Exception) -> bool:
    """
    Check if an exception is the specific 'temperature not supported' error.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if this is a temperature not supported error
    """
    error_message = str(exception).lower()
    
    # Check for the specific error patterns
    temperature_error_patterns = [
        "unsupported parameter: 'temperature'",
        "temperature is not supported with this model",
        "temperature parameter is not supported",
        "invalid parameter: temperature"
    ]
    
    return any(pattern in error_message for pattern in temperature_error_patterns)


def get_temperature_cache_info() -> dict:
    """Get information about the current temperature cache state."""
    return {
        "cached_models": len(_temperature_cache),
        "models": dict(_temperature_cache),
        "supported_models": [k for k, v in _temperature_cache.items() if v],
        "unsupported_models": [k for k, v in _temperature_cache.items() if not v]
    }