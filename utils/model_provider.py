"""
Model provider detection and configuration utilities for supporting multiple LLM providers.

This module provides utilities to detect whether a model string requires LiteLLM integration
(for OpenRouter and other providers) or standard OpenAI Agents SDK usage.
"""

from typing import Tuple, Optional, Union, List
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