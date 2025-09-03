"""
Unit tests for model provider utilities.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from utils.model_provider import (
    detect_model_provider,
    create_model_config,
    validate_environment_for_models,
    get_model_provider_info
)
from utils.openrouter_client import get_openrouter_client
from config.models import AgentConfiguration


class TestModelProvider(unittest.TestCase):
    
    def test_detect_model_provider_openai(self):
        """Test detection of OpenAI models (no slash)."""
        model, is_openrouter = detect_model_provider("gpt-4.1-mini")
        self.assertEqual(model, "gpt-4.1-mini")
        self.assertFalse(is_openrouter)
    
    def test_detect_model_provider_openrouter(self):
        """Test detection of OpenRouter models (with slash)."""
        model, is_openrouter = detect_model_provider("google/gemini-2.5-flash")
        self.assertEqual(model, "google/gemini-2.5-flash")
        self.assertTrue(is_openrouter)
    
    def test_detect_model_provider_multiple_slashes(self):
        """Test detection with multiple slashes."""
        model, is_openrouter = detect_model_provider("anthropic/claude-3-5-sonnet-20241022")
        self.assertEqual(model, "anthropic/claude-3-5-sonnet-20241022")
        self.assertTrue(is_openrouter)
    
    @patch('utils.model_provider.OpenAIChatCompletionsModel')
    @patch('utils.model_provider.get_openrouter_client')
    def test_create_model_config_openrouter(self, mock_get_client, mock_openai_model):
        """Test OpenRouter model creation via OpenAIChatCompletionsModel."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance
        
        model_config = create_model_config("google/gemini-2.5-flash")
        
        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="google/gemini-2.5-flash",
            openai_client=mock_client
        )
        self.assertEqual(model_config, mock_instance)
    
    def test_create_model_config_openai(self):
        """Test OpenAI model string passthrough."""
        model_config = create_model_config("gpt-4.1-mini")
        self.assertEqual(model_config, "gpt-4.1-mini")
    
    @patch('utils.model_provider.OpenAIChatCompletionsModel')
    @patch('utils.model_provider.get_openrouter_client')
    def test_create_model_config_openrouter_without_key(self, mock_get_client, mock_openai_model):
        """Test that OpenRouter model is created even without API key in environment."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance
        
        with patch.dict(os.environ, {}, clear=True):
            model_config = create_model_config("google/gemini-2.5-flash")
            
            # Should still create model using get_openrouter_client()
            mock_get_client.assert_called_once()
            mock_openai_model.assert_called_once_with(
                model="google/gemini-2.5-flash",
                openai_client=mock_client
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
            "is_openrouter": False,
            "provider": "OpenAI",
            "requires_env_var": "OPENAI_API_KEY"
        }
        
        self.assertEqual(info, expected)
    
    def test_get_model_provider_info_openrouter(self):
        """Test provider info for OpenRouter models."""
        info = get_model_provider_info("google/gemini-2.5-flash")
        
        expected = {
            "original_model": "google/gemini-2.5-flash",
            "processed_model": "google/gemini-2.5-flash",
            "is_openrouter": True,
            "provider": "OpenRouter",
            "requires_env_var": "OPENROUTER_API_KEY"
        }
        
        self.assertEqual(info, expected)
    
    @patch('utils.model_provider.OpenAIChatCompletionsModel')
    @patch('utils.model_provider.get_openrouter_client')
    def test_temperature_handled_via_model_settings_for_openrouter(self, mock_get_client, mock_openai_model):
        """Test that temperature is handled via ModelSettings for OpenRouter models (not in constructor)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance
        
        # Temperature parameter is not passed to OpenAIChatCompletionsModel constructor
        # It will be handled via ModelSettings in the Agent constructor
        model_config = create_model_config("google/gemini-2.5-flash", temperature=0.8)
        
        # OpenAIChatCompletionsModel should be called without temperature (temperature goes to ModelSettings)
        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="google/gemini-2.5-flash",
            openai_client=mock_client
        )
    
    def test_edge_case_empty_model_string(self):
        """Test behavior with empty model string."""
        model, is_openrouter = detect_model_provider("")
        self.assertEqual(model, "")
        self.assertFalse(is_openrouter)
    
    def test_edge_case_slash_only_model(self):
        """Test behavior with slash-only model string."""
        model, is_openrouter = detect_model_provider("/")
        self.assertEqual(model, "/")
        self.assertTrue(is_openrouter)


if __name__ == '__main__':
    unittest.main()