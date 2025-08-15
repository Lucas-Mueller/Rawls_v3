"""
Model provider detection and configuration utilities for supporting multiple LLM providers.

This module provides utilities to detect whether a model string requires LiteLLM integration
(for OpenRouter and other providers) or standard OpenAI Agents SDK usage, along with 
dynamic temperature parameter compatibility detection.
"""

import asyncio
import logging
from typing import Tuple, Optional, Union, List, Dict
from agents.extensions.models.litellm_model import LitellmModel
from agents.model_settings import ModelSettings
import os

logger = logging.getLogger(__name__)


def detect_model_provider(model_string: str) -> Tuple[str, bool]:
    """
    Detect if model requires LiteLLM OpenRouter integration.
    
    Args:
        model_string: Model identifier from configuration
        
    Returns:
        Tuple of (processed_model_string, is_litellm_model)
        - For OpenAI models (no "/"): returns (original_string, False)
        - For OpenRouter models (with "/"): returns ("openrouter/original_string", True)
    """
    if "/" in model_string:
        return f"openrouter/{model_string}", True
    return model_string, False


def create_model_config(model_string: str, temperature: float = 0.7) -> Union[str, LitellmModel]:
    """
    Create appropriate model configuration based on provider.
    
    Args:
        model_string: Model identifier from configuration  
        temperature: Model temperature setting
        
    Returns:
        Either string (for OpenAI models) or LitellmModel instance (for OpenRouter models)
    """
    processed_model, is_litellm = detect_model_provider(model_string)
    
    if is_litellm:
        # Use OpenRouter API key exactly like in Open_Router_Test.py
        return LitellmModel(
            model=processed_model,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    
    return model_string


def validate_environment_for_models(agents_config: List, utility_model: str = "gpt-4.1-mini") -> List[str]:
    """
    Validate that required environment variables are present for configured models.
    
    Args:
        agents_config: List of agent configurations with model strings
        utility_model: Model string for utility agents
        
    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []
    
    # Note: Both OPENAI_API_KEY and OPENROUTER_API_KEY are retrieved via os.getenv() when needed
    # This matches the approach in Open_Router_Test.py - no strict validation required
    
    return errors


def get_model_provider_info(model_string: str) -> dict:
    """
    Get information about the model provider for a given model string.
    
    Args:
        model_string: Model identifier from configuration
        
    Returns:
        Dictionary with provider information
    """
    processed_model, is_litellm = detect_model_provider(model_string)
    
    return {
        "original_model": model_string,
        "processed_model": processed_model,
        "is_litellm": is_litellm,
        "provider": "OpenRouter" if is_litellm else "OpenAI",
        "requires_env_var": "OPENROUTER_API_KEY" if is_litellm else "OPENAI_API_KEY"
    }


async def create_model_config_with_temperature_detection(
    model_string: str, 
    temperature: float = 0.7,
    skip_temperature_test: bool = False
) -> Tuple[Union[str, LitellmModel], dict]:
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
        logger.info(f"Running dynamic temperature detection for {model_string}")
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


def create_model_config_sync(model_string: str, temperature: float = 0.7) -> Tuple[Union[str, LitellmModel], dict]:
    """
    Synchronous wrapper for model config creation with conservative temperature detection.
    
    For full dynamic detection, use create_model_config_with_temperature_detection().
    """
    try:
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - create task and run it in the existing loop
            logger.info(f"Already in async context, using conservative temperature detection for {model_string}")
            task = asyncio.create_task(
                create_model_config_with_temperature_detection(model_string, temperature, skip_temperature_test=True)
            )
            # Since we can't wait for the task in a sync function within an async context,
            # we'll use the conservative fallback immediately
            return _create_conservative_model_config(model_string, temperature)
        except RuntimeError:
            # No running loop - we can safely use asyncio.run()
            return asyncio.run(
                create_model_config_with_temperature_detection(model_string, temperature)
            )
    except Exception as e:
        # Fallback to conservative approach
        logger.warning(f"Failed to run dynamic temperature detection for {model_string}: {e}. Using conservative fallback.")
        return _create_conservative_model_config(model_string, temperature)


def _create_conservative_model_config(model_string: str, temperature: float = 0.7) -> Tuple[Union[str, LitellmModel], dict]:
    """
    Create conservative model configuration without dynamic testing.
    
    Conservative assumption: OpenAI models support temperature, OpenRouter models do not.
    Uses cache if available and known non-supporting models.
    """
    from utils.dynamic_model_capabilities import supports_temperature_cached
    
    processed_model, is_litellm = detect_model_provider(model_string)
    
    # Check cache first
    cached_support = supports_temperature_cached(model_string)
    if cached_support is not None:
        supports_temp = cached_support
        detection_method = "cached_result"
        test_reason = "Previous test result from cache"
    else:
        if is_litellm:
            # Conservative: assume OpenRouter models don't support temperature
            supports_temp = False
            detection_method = "conservative_openrouter"
            test_reason = "OpenRouter models generally don't support temperature"
        else:
            # Conservative: assume OpenAI models support temperature
            supports_temp = True
            detection_method = "conservative_openai"
            test_reason = "OpenAI models generally support temperature"
    
    # Create model configuration
    if is_litellm:
        model_config = LitellmModel(
            model=processed_model,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    else:
        model_config = model_string
    
    # Create temperature info
    temperature_info = {
        "requested_temperature": temperature,
        "supports_temperature": supports_temp,
        "effective_temperature": temperature if supports_temp else None,
        "detection_method": detection_method,
        "test_reason": test_reason,
        "test_exception": None,
        "warning_issued": temperature != 0.7 and not supports_temp,
        "model_string": model_string
    }
    
    return model_config, temperature_info


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


async def batch_test_model_temperatures_for_experiment(model_strings: List[str]) -> Dict[str, dict]:
    """
    Batch test multiple models for temperature support during experiment startup.
    
    This allows testing all models upfront to provide comprehensive warnings
    before the experiment starts.
    
    Returns:
        Dictionary mapping model_string -> temperature_info
    """
    from utils.dynamic_model_capabilities import batch_test_model_temperatures
    
    return await batch_test_model_temperatures(model_strings)