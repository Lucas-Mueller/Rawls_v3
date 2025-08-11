"""
Unit tests for model provider utilities.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
from agents.extensions.models.litellm_model import LitellmModel

from utils.model_provider import (
    detect_model_provider,
    create_model_config,
    validate_environment_for_models,
    get_model_provider_info
)
from config.models import AgentConfiguration


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
    
    def test_detect_model_provider_multiple_slashes(self):
        """Test detection with multiple slashes."""
        model, is_litellm = detect_model_provider("anthropic/claude-3-5-sonnet-20241022")
        self.assertEqual(model, "openrouter/anthropic/claude-3-5-sonnet-20241022")
        self.assertTrue(is_litellm)
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch('utils.model_provider.LitellmModel')
    def test_create_model_config_litellm(self, mock_litellm):
        """Test LiteLLM model creation."""
        mock_instance = MagicMock()
        mock_litellm.return_value = mock_instance
        
        model_config = create_model_config("google/gemini-2.5-flash")
        
        mock_litellm.assert_called_once_with(
            model="openrouter/google/gemini-2.5-flash",
            api_key="test-key"
        )
        self.assertEqual(model_config, mock_instance)
    
    def test_create_model_config_openai(self):
        """Test OpenAI model string passthrough."""
        model_config = create_model_config("gpt-4.1-mini")
        self.assertEqual(model_config, "gpt-4.1-mini")
    
    @patch('utils.model_provider.LitellmModel')
    def test_create_model_config_missing_key(self, mock_litellm):
        """Test that LiteLLM model is created even without OpenRouter key (matches Open_Router_Test.py behavior)."""
        mock_instance = MagicMock()
        mock_litellm.return_value = mock_instance
        
        with patch.dict(os.environ, {}, clear=True):
            model_config = create_model_config("google/gemini-2.5-flash")
            
            # Should still create LiteLLM model with None API key (like Open_Router_Test.py)
            mock_litellm.assert_called_once_with(
                model="openrouter/google/gemini-2.5-flash",
                api_key=None
            )
            self.assertEqual(model_config, mock_instance)
    
    def test_validate_environment_no_validation(self):
        """Test that environment validation always passes (no strict validation)."""
        agents = [
            AgentConfiguration(
                name="Alice",
                personality="Test",
                model="gpt-4.1-mini"  # OpenAI
            ),
            AgentConfiguration(
                name="Bob",
                personality="Test",
                model="google/gemini-2.5-flash"  # OpenRouter
            )
        ]
        
        # Should pass regardless of environment variables
        with patch.dict(os.environ, {}, clear=True):
            errors = validate_environment_for_models(agents, "gpt-4.1-mini")
            self.assertEqual(len(errors), 0)
    
    def test_validate_environment_empty_always_passes(self):
        """Test that validation always passes even with no environment variables."""
        agents = [
            AgentConfiguration(
                name="Alice", 
                personality="Test",
                model="gpt-4.1-mini"
            ),
            AgentConfiguration(
                name="Bob",
                personality="Test", 
                model="google/gemini-2.5-flash"
            )
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            errors = validate_environment_for_models(agents, "anthropic/claude-3-5-sonnet-20241022")
            self.assertEqual(len(errors), 0)  # No validation errors - keys retrieved dynamically
    
    def test_get_model_provider_info_openai(self):
        """Test provider info for OpenAI models."""
        info = get_model_provider_info("gpt-4.1-mini")
        
        expected = {
            "original_model": "gpt-4.1-mini",
            "processed_model": "gpt-4.1-mini",
            "is_litellm": False,
            "provider": "OpenAI",
            "requires_env_var": "OPENAI_API_KEY"
        }
        
        self.assertEqual(info, expected)
    
    def test_get_model_provider_info_openrouter(self):
        """Test provider info for OpenRouter models."""
        info = get_model_provider_info("google/gemini-2.5-flash")
        
        expected = {
            "original_model": "google/gemini-2.5-flash",
            "processed_model": "openrouter/google/gemini-2.5-flash",
            "is_litellm": True,
            "provider": "OpenRouter",
            "requires_env_var": "OPENROUTER_API_KEY"
        }
        
        self.assertEqual(info, expected)
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch('utils.model_provider.LitellmModel')
    def test_temperature_handled_via_model_settings_for_litellm(self, mock_litellm):
        """Test that temperature is handled via ModelSettings for LiteLLM models (not in constructor)."""
        mock_instance = MagicMock()
        mock_litellm.return_value = mock_instance
        
        # Temperature parameter is not passed to LiteLLM constructor
        # It will be handled via ModelSettings in the Agent constructor
        model_config = create_model_config("google/gemini-2.5-flash", temperature=0.8)
        
        # LitellmModel should be called without temperature (temperature goes to ModelSettings)
        mock_litellm.assert_called_once_with(
            model="openrouter/google/gemini-2.5-flash",
            api_key="test-key"
        )
    
    def test_edge_case_empty_model_string(self):
        """Test behavior with empty model string."""
        model, is_litellm = detect_model_provider("")
        self.assertEqual(model, "")
        self.assertFalse(is_litellm)
    
    def test_edge_case_slash_only_model(self):
        """Test behavior with slash-only model string."""
        model, is_litellm = detect_model_provider("/")
        self.assertEqual(model, "openrouter//")
        self.assertTrue(is_litellm)


if __name__ == '__main__':
    unittest.main()