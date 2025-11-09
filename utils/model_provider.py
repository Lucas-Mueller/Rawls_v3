"""
Model provider detection and configuration utilities for supporting multiple LLM providers.

This module provides utilities to detect whether a model string requires LiteLLM integration
(for OpenRouter and other providers) or standard OpenAI Agents SDK usage, along with 
dynamic temperature parameter compatibility detection.
"""

import asyncio
import logging
from typing import Tuple, Optional, Union, List, Dict
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from utils.openrouter_client import get_openrouter_client
from agents.model_settings import ModelSettings
from utils.ollama_client import get_ollama_client
import os

logger = logging.getLogger(__name__)

ENABLE_OPENROUTER_NITRO_SUFFIX = False  # TEMP: flip back to True to restore :nitro suffix

def _append_nitro_suffix(model_string: str, is_openrouter: bool) -> str:
    """
    Append :nitro suffix to OpenRouter models if not already present.
    
    Args:
        model_string: The model identifier
        is_openrouter: Whether this is an OpenRouter model
        
    Returns:
        Model string with :nitro suffix if OpenRouter, unchanged otherwise
    """
    if (
        ENABLE_OPENROUTER_NITRO_SUFFIX
        and is_openrouter
        and not model_string.endswith(":nitro")
    ):
        return f"{model_string}:nitro"
    return model_string


def detect_model_provider(model_string: str) -> Tuple[str, str]:
    """
    Detect model provider based on model name and available API keys.

    Args:
        model_string: Model identifier from configuration

    Returns:
        Tuple of (processed_model_string, provider)
        - provider can be: "openai", "gemini", "openrouter", or "ollama"

    Raises:
        ValueError: If required API key is not available
    """
    model_lower = model_string.lower()

    # Rule 0: Ollama prefix handling (must be checked before generic slash rule)
    if model_lower.startswith("ollama/"):
        processed_model = model_string.split("/", 1)[1].strip()
        if not processed_model:
            raise ValueError(
                "Ollama model string must include a model name after 'ollama/'.\n"
                "Example: 'ollama/llama3.2'"
            )
        return processed_model, "ollama"

    # Rule 0.5: Gemini models - prioritize native API even with prefixes
    if "gemini" in model_lower:
        if os.getenv("GEMINI_API_KEY"):
            # Strip provider prefix if present (e.g., "google/gemini-2.0" -> "gemini-2.0")
            if "/" in model_string:
                processed_model = model_string.split("/", 1)[1].strip()
            else:
                processed_model = model_string
            return processed_model, "gemini"
        raise ValueError(
            f"Gemini model '{model_string}' requires GEMINI_API_KEY.\n"
            f"Solutions:\n"
            f"  1. Set GEMINI_API_KEY environment variable\n"
            f"  2. Remove 'google/' prefix to use OpenRouter"
        )

    # Rule 1: Explicit OpenRouter via "/"
    if "/" in model_string:
        return model_string, "openrouter"

    # Remaining rules operate on prefix checks without provider markers

    # Rule 2a: Gemma models - route to OpenRouter with warning
    if model_lower.startswith("gemma"):
        logger.warning(
            f"⚠️  Gemma model '{model_string}' doesn't support system messages via native API. "
            f"Routing to OpenRouter automatically."
        )
        # Auto-route to OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            return f"google/{model_string}", "openrouter"
        raise ValueError(
            f"Gemma model '{model_string}' requires OPENROUTER_API_KEY.\n"
            f"Note: Gemma models need OpenRouter as they don't support system messages"
        )

    # Rule 2b: Gemini models - use native API
    if model_lower.startswith("gemini"):
        if os.getenv("GEMINI_API_KEY"):
            return model_string, "gemini"
        raise ValueError(
            f"Model '{model_string}' requires GEMINI_API_KEY.\n"
            f"Solutions:\n"
            f"  1. Set GEMINI_API_KEY environment variable\n"
            f"  2. Use 'google/{model_string}' with OPENROUTER_API_KEY"
        )

    # Rule 3: OpenAI models
    if model_lower.startswith(("gpt", "o1", "o3")):
        if os.getenv("OPENAI_API_KEY"):
            return model_string, "openai"
        raise ValueError(
            f"Model '{model_string}' requires OPENAI_API_KEY.\n"
            f"Solutions:\n"
            f"  1. Set OPENAI_API_KEY environment variable\n"
            f"  2. Use 'openai/{model_string}' with OPENROUTER_API_KEY"
        )

    # Unknown models - explicit error
    raise ValueError(
        f"Unknown model '{model_string}'.\n"
        f"Solutions:\n"
        f"  1. Use explicit provider prefix (e.g., 'anthropic/{model_string}')\n"
        f"  2. Use 'ollama/<model>' for local Ollama models (ensure the model is pulled)\n"
        f"  3. Check model name spelling or use an OpenRouter provider prefix"
    )


def detect_model_provider_legacy(model_string: str) -> Tuple[str, bool]:
    """
    Legacy function for backward compatibility.
    Maps new provider detection to old boolean format.

    Args:
        model_string: Model identifier from configuration

    Returns:
        Tuple of (model_string, is_openrouter_model)
    """
    try:
        processed_model, provider = detect_model_provider(model_string)
        return processed_model, (provider == "openrouter")
    except ValueError:
        # For legacy compatibility, treat unknown models as OpenAI
        return model_string, False


def create_model_config(model_string: str, temperature: float = 0.7) -> Union[str, OpenAIChatCompletionsModel]:
    """
    Create appropriate model configuration based on provider.

    Args:
        model_string: Model identifier from configuration
        temperature: Model temperature setting

    Returns:
        Model configuration for the detected provider:
        - String for OpenAI models
        - OpenAIChatCompletionsModel for OpenRouter, Gemini, and Ollama

    Raises:
        ValueError: If required API key is not available
    """
    # Import here to avoid circular dependency
    from utils.gemini_client import get_gemini_client

    # Get provider (raises ValueError if API key missing)
    processed_model, provider = detect_model_provider(model_string)

    if provider == "gemini":
        logger.debug(f"Creating Gemini model config for: {processed_model}")
        # Use OpenAIChatCompletionsModel with Gemini client
        return OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_gemini_client()
        )
    elif provider == "ollama":
        logger.debug(f"Creating Ollama model config for: {processed_model}")
        return OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_ollama_client()
        )
    elif provider == "openrouter":
        logger.debug(f"Creating OpenRouter model config for: {processed_model}")
        return OpenAIChatCompletionsModel(
            model=_append_nitro_suffix(processed_model, True),
            openai_client=get_openrouter_client()
        )
    else:  # openai
        logger.debug(f"Using OpenAI model: {processed_model}")
        return processed_model


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
    try:
        processed_model, provider = detect_model_provider(model_string)

        # Map provider to required environment variable
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "ollama": "OLLAMA_BASE_URL (optional)"
        }

        return {
            "original_model": model_string,
            "processed_model": processed_model,
            "provider": provider,
            "is_openrouter": provider == "openrouter",
            "requires_env_var": env_var_map.get(provider, "UNKNOWN")
        }
    except ValueError as e:
        # Return error info if detection fails
        return {
            "original_model": model_string,
            "processed_model": model_string,
            "provider": "unknown",
            "is_openrouter": False,
            "error": str(e)
        }


async def create_model_config_with_temperature_detection(
    model_string: str, 
    temperature: float = 0.7,
    skip_temperature_test: bool = False,
    temperature_cache=None
) -> Tuple[Union[str, OpenAIChatCompletionsModel], dict]:
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

    try:
        processed_model, provider = detect_model_provider(model_string)
    except ValueError:
        # Maintain legacy fallback behaviour: treat as OpenAI string
        processed_model, provider = model_string, "openai"
    is_openrouter = provider == "openrouter"
    
    # Check if we already know about this model's temperature support
    cached_support = supports_temperature_cached(model_string, temperature_cache)
    
    if cached_support is not None and not skip_temperature_test:
        # Use cached result
        supports_temp = cached_support
        detection_method = "cached"
        test_reason = "Previous test result"
        test_exception = None
    elif not skip_temperature_test:
        # Run dynamic detection
        logger.info(f"Running dynamic temperature detection for {model_string}")
        supports_temp, test_reason, test_exception = await test_temperature_support(model_string, temperature_cache)
        detection_method = "dynamic_test"
    else:
        # Conservative fallback - assume temperature works for non-OpenRouter providers
        supports_temp = provider != "openrouter"
        detection_method = "conservative_fallback"
        test_reason = "Skipped dynamic testing, using conservative assumption"
        test_exception = None
    
    # Create model configuration
    if provider == "openrouter":
        model_config = OpenAIChatCompletionsModel(
            model=_append_nitro_suffix(processed_model, True),
            openai_client=get_openrouter_client()
        )
    elif provider == "gemini":
        from utils.gemini_client import get_gemini_client

        model_config = OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_gemini_client()
        )
    elif provider == "ollama":
        model_config = OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_ollama_client()
        )
    else:
        model_config = processed_model
    
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


def create_model_config_sync(model_string: str, temperature: float = 0.7, temperature_cache=None) -> Tuple[Union[str, OpenAIChatCompletionsModel], dict]:
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
                create_model_config_with_temperature_detection(model_string, temperature, skip_temperature_test=True, temperature_cache=temperature_cache)
            )
            # Since we can't wait for the task in a sync function within an async context,
            # we'll use the conservative fallback immediately
            return _create_conservative_model_config(model_string, temperature, temperature_cache)
        except RuntimeError:
            # No running loop - we can safely use asyncio.run()
            return asyncio.run(
                create_model_config_with_temperature_detection(model_string, temperature, temperature_cache=temperature_cache)
            )
    except Exception as e:
        # Fallback to conservative approach
        logger.warning(f"Failed to run dynamic temperature detection for {model_string}: {e}. Using conservative fallback.")
        return _create_conservative_model_config(model_string, temperature, temperature_cache)


def _create_conservative_model_config(model_string: str, temperature: float = 0.7, temperature_cache=None) -> Tuple[Union[str, OpenAIChatCompletionsModel], dict]:
    """
    Create conservative model configuration without dynamic testing.
    
    Conservative assumption: OpenAI models support temperature, OpenRouter models do not.
    Uses cache if available and known non-supporting models.
    """
    from utils.dynamic_model_capabilities import supports_temperature_cached

    try:
        processed_model, provider = detect_model_provider(model_string)
    except ValueError:
        processed_model, provider = model_string, "openai"
    is_openrouter = provider == "openrouter"
    
    # Check cache first
    cached_support = supports_temperature_cached(model_string, temperature_cache)
    if cached_support is not None:
        supports_temp = cached_support
        detection_method = "cached_result"
        test_reason = "Previous test result from cache"
    else:
        if is_openrouter:
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
    if provider == "openrouter":
        model_config = OpenAIChatCompletionsModel(
            model=_append_nitro_suffix(processed_model, True),
            openai_client=get_openrouter_client()
        )
    elif provider == "gemini":
        from utils.gemini_client import get_gemini_client

        model_config = OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_gemini_client()
        )
    elif provider == "ollama":
        model_config = OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_ollama_client()
        )
    else:
        model_config = processed_model
    
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


async def batch_test_model_temperatures_for_experiment(model_strings: List[str], temperature_cache=None) -> Dict[str, dict]:
    """
    Batch test multiple models for temperature support during experiment startup.
    
    This allows testing all models upfront to provide comprehensive warnings
    before the experiment starts.
    
    Returns:
        Dictionary mapping model_string -> temperature_info
    """
    from utils.dynamic_model_capabilities import batch_test_model_temperatures
    
    return await batch_test_model_temperatures(model_strings, temperature_cache)
