"""Unit tests for model provider detection utilities."""
from __future__ import annotations

import pytest

from config.models import AgentConfiguration
from utils.model_provider import get_model_provider_info, validate_environment_for_models


@pytest.mark.unit
def test_get_model_provider_info_openai_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    info = get_model_provider_info("gpt-4.1-mini")
    assert info["provider"] == "openai"
    assert info["original_model"] == "gpt-4.1-mini"
    assert info["processed_model"] == "gpt-4.1-mini"
    assert info["requires_env_var"] == "OPENAI_API_KEY"
    assert info["is_openrouter"] is False


@pytest.mark.unit
def test_get_model_provider_info_openrouter_model():
    info = get_model_provider_info("anthropic/claude-3-5-sonnet-20241022")
    assert info["provider"] == "openrouter"
    assert info["processed_model"] == "anthropic/claude-3-5-sonnet-20241022"
    assert info["requires_env_var"] == "OPENROUTER_API_KEY"
    assert info["is_openrouter"] is True


@pytest.mark.unit
def test_get_model_provider_info_ollama_model():
    info = get_model_provider_info("ollama/llama3.2")
    assert info["provider"] == "ollama"
    assert info["processed_model"] == "llama3.2"
    assert info["requires_env_var"] == "OLLAMA_BASE_URL (optional)"
    assert info["is_openrouter"] is False


@pytest.mark.unit
def test_validate_environment_for_models_returns_no_errors(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    agents = [
        AgentConfiguration(name="Alice", personality="A", model="gpt-4.1-mini"),
        AgentConfiguration(name="Bob", personality="B", model="anthropic/claude-3-5-sonnet-20241022"),
    ]

    errors = validate_environment_for_models(agents, "gpt-4.1-mini")
    assert errors == []
