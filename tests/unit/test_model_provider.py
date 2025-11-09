"""
Unit tests for model provider utilities.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from config.models import AgentConfiguration
from utils.model_provider import (
    create_model_config,
    detect_model_provider,
    get_model_provider_info,
    validate_environment_for_models,
)


class TestModelProvider:
    def test_detect_model_provider_openai(self):
        """Test detection of OpenAI models (no slash)."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=False):
            model, provider = detect_model_provider("gpt-4.1-mini")
        assert model == "gpt-4.1-mini"
        assert provider == "openai"

    def test_detect_model_provider_gemini_with_prefix(self):
        """Test detection of Gemini models with provider prefix (now prioritizes native API)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=False):
            model, provider = detect_model_provider("google/gemini-2.5-flash")
        assert model == "gemini-2.5-flash"  # Strips google/ prefix
        assert provider == "gemini"

    def test_detect_model_provider_multiple_slashes(self):
        """Test detection with multiple slashes."""
        model, provider = detect_model_provider("anthropic/claude-3-5-sonnet-20241022")
        assert model == "anthropic/claude-3-5-sonnet-20241022"
        assert provider == "openrouter"

    def test_detect_model_provider_ollama_prefix(self):
        """Test detection of Ollama models via explicit prefix."""
        model, provider = detect_model_provider("ollama/llama3.2")
        assert model == "llama3.2"
        assert provider == "ollama"

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_openrouter_client")
    def test_create_model_config_openrouter(self, mock_get_client, mock_openai_model):
        """Test OpenRouter model creation via OpenAIChatCompletionsModel."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        model_config = create_model_config("anthropic/claude-3-haiku")

        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="anthropic/claude-3-haiku:nitro",
            openai_client=mock_client,
        )
        assert model_config == mock_instance

    def test_create_model_config_openai(self):
        """Test OpenAI model string passthrough."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=False):
            model_config = create_model_config("gpt-4.1-mini")
        assert model_config == "gpt-4.1-mini"

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_ollama_client")
    def test_create_model_config_ollama(self, mock_get_client, mock_openai_model):
        """Test Ollama model creation via OpenAIChatCompletionsModel."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        model_config = create_model_config("ollama/llama3.2")

        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="llama3.2",
            openai_client=mock_client,
        )
        assert model_config == mock_instance

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_openrouter_client")
    def test_create_model_config_openrouter_without_key(self, mock_get_client, mock_openai_model):
        """Test that OpenRouter model is created even without API key in environment."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        with patch.dict(os.environ, {}, clear=True):
            model_config = create_model_config("anthropic/claude-3-haiku")

        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="anthropic/claude-3-haiku:nitro",
            openai_client=mock_client,
        )
        assert model_config == mock_instance

    def test_validate_environment_no_validation(self):
        """Test that environment validation always passes (no strict validation)."""
        agents = [
            AgentConfiguration(
                name="Alice",
                personality="Test",
                model="gpt-4.1-mini",
            ),
            AgentConfiguration(
                name="Bob",
                personality="Test",
                model="google/gemini-2.5-flash",
            ),
        ]

        with patch.dict(os.environ, {}, clear=True):
            errors = validate_environment_for_models(agents, "gpt-4.1-mini")
        assert errors == []

    def test_validate_environment_empty_always_passes(self):
        """Test that validation always passes even with no environment variables."""
        agents = [
            AgentConfiguration(
                name="Alice",
                personality="Test",
                model="gpt-4.1-mini",
            ),
            AgentConfiguration(
                name="Bob",
                personality="Test",
                model="google/gemini-2.5-flash",
            ),
        ]

        with patch.dict(os.environ, {}, clear=True):
            errors = validate_environment_for_models(agents, "anthropic/claude-3-5-sonnet-20241022")
        assert errors == []  # keys retrieved dynamically

    def test_get_model_provider_info_openai(self):
        """Test provider info for OpenAI models."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=False):
            info = get_model_provider_info("gpt-4.1-mini")

        expected = {
            "original_model": "gpt-4.1-mini",
            "processed_model": "gpt-4.1-mini",
            "is_openrouter": False,
            "provider": "openai",
            "requires_env_var": "OPENAI_API_KEY",
        }

        assert info == expected

    def test_get_model_provider_info_gemini_with_prefix(self):
        """Test provider info for Gemini models with prefix (now prioritizes native API)."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=False):
            info = get_model_provider_info("google/gemini-2.5-flash")

        expected = {
            "original_model": "google/gemini-2.5-flash",
            "processed_model": "gemini-2.5-flash",
            "is_openrouter": False,
            "provider": "gemini",
            "requires_env_var": "GEMINI_API_KEY",
        }

        assert info == expected

    def test_get_model_provider_info_ollama(self):
        """Test provider info for Ollama models."""
        info = get_model_provider_info("ollama/llama3.2")

        expected = {
            "original_model": "ollama/llama3.2",
            "processed_model": "llama3.2",
            "is_openrouter": False,
            "provider": "ollama",
            "requires_env_var": "OLLAMA_BASE_URL (optional)",
        }

        assert info == expected

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_openrouter_client")
    def test_temperature_handled_via_model_settings_for_openrouter(self, mock_get_client, mock_openai_model):
        """Temperature is handled via ModelSettings for OpenRouter models (not constructor)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        create_model_config("anthropic/claude-3-haiku", temperature=0.8)

        mock_get_client.assert_called_once()
        mock_openai_model.assert_called_once_with(
            model="anthropic/claude-3-haiku:nitro",
            openai_client=mock_client,
        )

    def test_edge_case_empty_model_string(self):
        """Test behavior with empty model string."""
        with pytest.raises(ValueError):
            detect_model_provider("")

    def test_edge_case_slash_only_model(self):
        """Test behavior with slash-only model string."""
        model, provider = detect_model_provider("/")
        assert model == "/"
        assert provider == "openrouter"

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_openrouter_client")
    def test_nitro_suffix_addition(self, mock_get_client, mock_openai_model):
        """Test that :nitro suffix is added to OpenRouter models."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        create_model_config("qwen/qwen-2.5-72b-instruct")

        mock_openai_model.assert_called_once_with(
            model="qwen/qwen-2.5-72b-instruct:nitro",
            openai_client=mock_client,
        )

    @patch("utils.model_provider.OpenAIChatCompletionsModel")
    @patch("utils.model_provider.get_openrouter_client")
    def test_nitro_suffix_not_duplicated(self, mock_get_client, mock_openai_model):
        """Test that :nitro suffix is not added if already present."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_instance = MagicMock()
        mock_openai_model.return_value = mock_instance

        create_model_config("qwen/qwen-2.5-72b-instruct:nitro")

        mock_openai_model.assert_called_once_with(
            model="qwen/qwen-2.5-72b-instruct:nitro",
            openai_client=mock_client,
        )

    def test_nitro_suffix_utility_function(self):
        """Test the _append_nitro_suffix utility function directly."""
        from utils.model_provider import _append_nitro_suffix

        assert (
            _append_nitro_suffix("qwen/qwen-2.5-72b-instruct", True)
            == "qwen/qwen-2.5-72b-instruct:nitro"
        )
        assert (
            _append_nitro_suffix("qwen/qwen-2.5-72b-instruct:nitro", True)
            == "qwen/qwen-2.5-72b-instruct:nitro"
        )
        assert _append_nitro_suffix("gpt-4", False) == "gpt-4"
