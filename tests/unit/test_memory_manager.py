"""Pytest coverage for `MemoryManager` async helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from utils.memory_manager import MemoryManager
from utils.error_handling import ExperimentError


@pytest.fixture
def mock_language_manager():
    manager = Mock()
    manager.get.side_effect = lambda key, **kwargs: key.format(**kwargs) if "{" in key else key
    return manager


@pytest.fixture
def mock_agent():
    agent = Mock()
    agent.name = "TestAgent"
    agent.config = Mock(memory_character_limit=1000)
    agent.update_memory = AsyncMock()
    return agent


@pytest.fixture
def participant_context():
    context = Mock()
    context.memory = "Current memory"
    context.memory_character_limit = 1000
    context.bank_balance = 0
    return context


def test_validate_memory_length_success():
    is_valid, length = MemoryManager._validate_memory_length("hello", 10)
    assert is_valid is True
    assert length == 5


def test_validate_memory_length_failure():
    is_valid, length = MemoryManager._validate_memory_length("x" * 20, 10)
    assert is_valid is False
    assert length == 20


def test_create_memory_update_prompt_includes_content(mock_language_manager):
    prompt = MemoryManager._create_memory_update_prompt(
        "existing", "new info", "narrative", mock_language_manager
    )
    assert "existing" in prompt
    assert "new info" in prompt


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_success(mock_agent, participant_context, mock_language_manager):
    mock_agent.update_memory.return_value = "Updated"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        participant_context,
        "round info",
        language_manager=mock_language_manager,
    )

    assert result == "Updated"
    mock_agent.update_memory.assert_awaited()


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_compresses_when_too_long(
    mock_agent, participant_context, mock_language_manager
):
    mock_agent.update_memory.return_value = "A" * 2000

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        participant_context,
        "round info",
        language_manager=mock_language_manager,
    )

    assert "[Memory compressed" in result


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_retries_on_exception(
    mock_agent, participant_context, mock_language_manager
):
    mock_agent.update_memory.side_effect = [Exception("boom"), "Recovered"]

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        participant_context,
        "round info",
        language_manager=mock_language_manager,
        max_retries=2,
    )

    assert result == "Recovered"


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_raises_after_retries(
    mock_agent, participant_context, mock_language_manager
):
    mock_agent.update_memory.side_effect = Exception("fail")

    with pytest.raises(ExperimentError):
        await MemoryManager.prompt_agent_for_memory_update(
            mock_agent,
            participant_context,
            "round info",
            language_manager=mock_language_manager,
            max_retries=1,
        )
