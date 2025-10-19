"""
Unit tests for agent-managed memory system.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
from unittest.mock import AsyncMock, Mock, patch

import pytest

from models import ExperimentPhase
from utils.error_handling import MemoryError
from utils.memory_manager import MemoryManager


@pytest.fixture
def mock_agent():
    agent = Mock()
    agent.name = "TestAgent"
    agent.config = Mock()
    agent.config.memory_character_limit = 1000
    agent.update_memory = AsyncMock()
    return agent


@pytest.fixture
def mock_context():
    context = Mock()
    context.memory = "Current memory content"
    context.memory_character_limit = 1000
    context.round_number = 2
    context.phase = ExperimentPhase.PHASE_2
    context.bank_balance = 0.0
    return context


def test_validate_memory_length_valid():
    memory = "This is a short memory"
    is_valid, length = MemoryManager._validate_memory_length(memory, 1000)
    assert is_valid is True
    assert length == len(memory)


def test_validate_memory_length_invalid():
    memory = "A" * 1500
    is_valid, length = MemoryManager._validate_memory_length(memory, 1000)
    assert is_valid is False
    assert length == 1500


def test_create_memory_update_prompt(mock_agent):
    current_memory = "Previous memory content"
    round_content = "New round information"

    language_manager = Mock()
    language_manager.get.side_effect = lambda key, **kwargs: (
        "Test prompt with {current_memory} and {round_content}. "
        "Return your complete updated memory."
    ).format(**kwargs)

    prompt = MemoryManager._create_memory_update_prompt(
        current_memory, round_content, "narrative", language_manager
    )

    assert "Previous memory content" in prompt
    assert "New round information" in prompt
    assert "Return your complete updated memory" in prompt


def test_create_memory_update_prompt_empty_memory():
    language_manager = Mock()
    language_manager.get.side_effect = lambda key, **kwargs: {
        "prompts.memory_narrative_update_prompt": (
            "Test prompt with {current_memory} and {round_content}. "
            "Return your complete updated memory."
        ),
        "prompts.memory_empty_memory_placeholder": "(Empty)",
    }.get(key, key).format(**kwargs)

    prompt = MemoryManager._create_memory_update_prompt(
        "", "New round information", "narrative", language_manager
    )

    assert "(Empty)" in prompt


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_explicit_metadata(mock_agent, mock_context):
    mock_agent.update_memory.return_value = "Updated memory content"
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        mock_context,
        "Test round content",
        language_manager=language_manager,
        round_number=7,
        phase=ExperimentPhase.PHASE_1,
    )

    assert result == "Updated memory content"
    mock_agent.update_memory.assert_awaited_once()
    _, kwargs = mock_agent.update_memory.call_args
    assert kwargs.get("phase") == ExperimentPhase.PHASE_1
    assert kwargs.get("round_number") == 7


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_success(mock_agent, mock_context):
    mock_agent.update_memory.return_value = "Updated memory content"
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        mock_context,
        "Test round content",
        language_manager=language_manager,
    )

    assert result == "Updated memory content"
    mock_agent.update_memory.assert_awaited_once()
    _, kwargs = mock_agent.update_memory.call_args
    assert kwargs.get("phase") == ExperimentPhase.PHASE_2
    assert kwargs.get("round_number") == 2


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_length_exceeded_then_compression(mock_agent, mock_context):
    mock_agent.update_memory.return_value = "A" * 1500
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        mock_context,
        "Test round content",
        language_manager=language_manager,
    )

    assert "[Memory compressed due to length limit]" in result
    assert mock_agent.update_memory.call_count == 1


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_with_tolerance_compression(mock_agent, mock_context):
    mock_agent.update_memory.return_value = "A" * 1500
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        mock_context,
        "Test round content",
        max_retries=3,
        language_manager=language_manager,
    )

    assert "[Memory compressed due to length limit]" in result
    assert mock_agent.update_memory.call_count == 1


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_exception_then_success(mock_agent, mock_context):
    mock_agent.update_memory.side_effect = [
        Exception("Test error"),
        "Updated memory content",
    ]
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        mock_agent,
        mock_context,
        "Test round content",
        language_manager=language_manager,
    )

    assert result == "Updated memory content"
    assert mock_agent.update_memory.call_count == 2


@pytest.mark.asyncio
async def test_compress_memory_with_utility_agent_truncation_respects_target():
    utility_agent = Mock()
    utility_agent.parser_agent = Mock()

    language_manager = Mock()
    language_manager.get.return_value = "Compression prompt"

    mock_result = Mock()
    mock_result.final_output = "X" * 120

    with patch(
        "experiment_agents.utility_agent.run_without_tracing",
        new=AsyncMock(return_value=mock_result),
    ):
        compressed = await MemoryManager._compress_memory_with_utility_agent(
            utility_agent,
            memory_content="Y" * 150,
            target_length=40,
            language_manager=language_manager,
            agent_name="TestAgent",
        )

    assert len(compressed) <= 40
    assert "[Memory" in compressed


@pytest.mark.asyncio
async def test_compress_memory_with_utility_agent_exception_respects_target():
    utility_agent = Mock()
    utility_agent.parser_agent = Mock()

    language_manager = Mock()
    language_manager.get.return_value = "Compression prompt"

    with patch(
        "experiment_agents.utility_agent.run_without_tracing",
        new=AsyncMock(side_effect=Exception("fail")),
    ):
        compressed = await MemoryManager._compress_memory_with_utility_agent(
            utility_agent,
            memory_content="Y" * 150,
            target_length=40,
            language_manager=language_manager,
            agent_name="TestAgent",
        )

    assert len(compressed) <= 40
    assert "[Memory" in compressed


@pytest.mark.asyncio
async def test_prompt_agent_for_memory_update_persistent_exception(mock_agent, mock_context):
    mock_agent.update_memory.side_effect = Exception("Persistent error")
    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    with pytest.raises(MemoryError):
        await MemoryManager.prompt_agent_for_memory_update(
            mock_agent,
            mock_context,
            "Test round content",
            max_retries=2,
            language_manager=language_manager,
        )

    assert mock_agent.update_memory.call_count == 2


def test_memory_error_creation():
    from utils.error_handling import ErrorSeverity

    error = MemoryError("Memory too long", ErrorSeverity.RECOVERABLE, {"length": 1500, "limit": 1000})
    assert "Memory too long" in str(error)
    assert error.severity == ErrorSeverity.RECOVERABLE
    assert error.context["length"] == 1500
    assert error.context["limit"] == 1000


class TestMemoryManagerTemplateSelection:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.current_memory = "Previous memory content"
        self.round_content = "New round information"
        self.language_manager = Mock()
        self.language_manager.get.side_effect = self._language_lookup

    def _language_lookup(self, key: str, **kwargs) -> str:
        templates = {
            "prompts.memory_narrative_update_prompt": (
                "Narrative template with Recent Activity:\n{current_memory}\n\nRecent Activity:\n{round_content}"
            ),
            "prompts.memory_memory_update_prompt": (
                "Structured template with Recent Activity:\n{current_memory}\n\nRecent Activity:\n{round_content}"
            ),
            "prompts.memory_narrative_update_prompt_no_recent_activity": (
                "Narrative template with Your Recent Reasoning:\n{current_memory}\n\n"
                "Your Recent Reasoning and Statement:\n{round_content}"
            ),
            "prompts.memory_memory_update_prompt_no_recent_activity": (
                "Structured template with Your Recent Reasoning:\n{current_memory}\n\n"
                "Your Recent Reasoning and Statement:\n{round_content}"
            ),
            "prompts.memory_empty_memory_placeholder": "(Empty)",
        }
        template = templates.get(key)
        if template is None:
            raise KeyError(f"Template key '{key}' not found")
        return template.format(**kwargs)

    def test_discussion_interaction_types_use_no_recent_activity_templates(self):
        for interaction_type in ("internal_reasoning", "statement"):
            prompt = MemoryManager._create_memory_update_prompt(
                self.current_memory,
                self.round_content,
                "narrative",
                self.language_manager,
                interaction_type,
            )
            assert "Your Recent Reasoning and Statement:" in prompt
            assert "Recent Activity:" not in prompt

    def test_discussion_interaction_types_structured_style(self):
        for interaction_type in ("internal_reasoning", "statement"):
            prompt = MemoryManager._create_memory_update_prompt(
                self.current_memory,
                self.round_content,
                "structured",
                self.language_manager,
                interaction_type,
            )
            assert "Your Recent Reasoning and Statement:" in prompt
            assert "Recent Activity:" not in prompt

    def test_non_discussion_interaction_types_use_standard_templates(self):
        for interaction_type in ("vote_prompt", "vote_confirmation", "ballot", "other_type"):
            prompt = MemoryManager._create_memory_update_prompt(
                self.current_memory,
                self.round_content,
                "narrative",
                self.language_manager,
                interaction_type,
            )
            assert "Recent Activity:" in prompt
            assert "Your Recent Reasoning and Statement:" not in prompt

    def test_none_interaction_type_uses_standard_templates(self):
        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory,
            self.round_content,
            "narrative",
            self.language_manager,
            None,
        )
        assert "Recent Activity:" in prompt
        assert "Your Recent Reasoning and Statement:" not in prompt

    def test_fallback_when_no_recent_activity_template_missing(self):
        def missing_template(key: str, **kwargs):
            if "_no_recent_activity" in key:
                raise KeyError(key)
            return self._language_lookup(key, **kwargs)

        self.language_manager.get.side_effect = missing_template

        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory,
            self.round_content,
            "narrative",
            self.language_manager,
            "statement",
        )
        assert "Recent Activity:" in prompt
        assert "Your Recent Reasoning and Statement:" not in prompt

    def test_fallback_handles_attribute_error(self):
        def attribute_error(key: str, **kwargs):
            if "_no_recent_activity" in key:
                raise AttributeError("missing template")
            return self._language_lookup(key, **kwargs)

        self.language_manager.get.side_effect = attribute_error

        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory,
            self.round_content,
            "structured",
            self.language_manager,
            "internal_reasoning",
        )
        assert "Recent Activity:" in prompt
        assert "Your Recent Reasoning and Statement:" not in prompt

    def test_empty_memory_handling_with_discussion_types(self):
        prompt = MemoryManager._create_memory_update_prompt(
            "",
            self.round_content,
            "narrative",
            self.language_manager,
            "statement",
        )
        assert "(Empty)" in prompt
        assert "Your Recent Reasoning and Statement:" in prompt

    def test_template_selection_preserves_guidance_styles(self):
        for style in ("narrative", "structured"):
            prompt = MemoryManager._create_memory_update_prompt(
                self.current_memory,
                self.round_content,
                style,
                self.language_manager,
                "internal_reasoning",
            )
            assert "Your Recent Reasoning and Statement:" in prompt
            assert "Recent Activity:" not in prompt

    def test_template_content_validation_all_languages(self):
        translations_dir = Path(__file__).resolve().parents[2] / "translations"
        language_files = [
            translations_dir / "english_prompts.json",
            translations_dir / "spanish_prompts.json",
            translations_dir / "mandarin_prompts.json",
        ]
        required_templates = {
            "memory_narrative_update_prompt",
            "memory_narrative_update_prompt_no_recent_activity",
            "memory_memory_update_prompt",
            "memory_memory_update_prompt_no_recent_activity",
        }

        for language_file in language_files:
            with language_file.open(encoding="utf-8") as fh:
                data = json.load(fh)
            prompts_section = data.get("prompts", {})
            assert required_templates.issubset(prompts_section), (
                f"Missing templates in {language_file}: "
                f"{required_templates - prompts_section.keys()}"
            )

    def test_error_handling_doesnt_break_memory_flow(self):
        failing_manager = Mock()
        failing_manager.get.side_effect = Exception("Complete failure")

        with pytest.raises(Exception):
            MemoryManager._create_memory_update_prompt(
                self.current_memory,
                self.round_content,
                "narrative",
                failing_manager,
                "statement",
            )


@pytest.mark.asyncio
async def test_async_memory_update_flow():
    agent = Mock()
    agent.name = "TestAgent"
    agent.config = Mock()
    agent.config.memory_character_limit = 100
    agent.update_memory = AsyncMock(return_value="Short memory")

    context = Mock()
    context.memory = "Previous"
    context.memory_character_limit = 100
    context.bank_balance = 50.0
    context.round_number = 1
    context.phase = ExperimentPhase.PHASE_1

    language_manager = Mock()
    language_manager.get.return_value = "Test prompt template"

    result = await MemoryManager.prompt_agent_for_memory_update(
        agent,
        context,
        "New content",
        language_manager=language_manager,
    )

    assert result == "Short memory"
    agent.update_memory.assert_called_once()


@pytest.mark.asyncio
async def test_interaction_type_parameter_passing():
    agent = Mock()
    agent.name = "TestAgent"
    agent.config = Mock()
    agent.config.memory_character_limit = 1000
    agent.update_memory = AsyncMock(return_value="Updated memory")

    context = Mock()
    context.memory = "Previous memory"
    context.memory_character_limit = 1000
    context.bank_balance = 100.0
    context.round_number = 1
    context.phase = ExperimentPhase.PHASE_1

    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    with patch.object(MemoryManager, "_create_memory_update_prompt", return_value="Mocked prompt") as mock_prompt:
        await MemoryManager.prompt_agent_for_memory_update(
            agent,
            context,
            "Round content",
            language_manager=language_manager,
            interaction_type="statement",
        )

    mock_prompt.assert_called_once()
    args, _ = mock_prompt.call_args
    assert args[:5] == ("Previous memory", "Round content", "narrative", language_manager, "statement")
    assert args[5] == context.round_number
    assert args[6] == "phase_1"


@pytest.mark.asyncio
async def test_interaction_type_parameter_with_different_guidance_styles():
    agent = Mock()
    agent.name = "TestAgent"
    agent.config = Mock()
    agent.config.memory_character_limit = 1000
    agent.update_memory = AsyncMock(return_value="Updated memory")

    context = Mock()
    context.memory = "Previous memory"
    context.memory_character_limit = 1000
    context.bank_balance = 100.0
    context.round_number = 1
    context.phase = ExperimentPhase.PHASE_1

    language_manager = Mock()
    language_manager.get.return_value = "Mock prompt template"

    guidance_styles = ("narrative", "structured")
    interaction_types: Iterable[str | None] = ("internal_reasoning", "statement", "vote_prompt", None)

    for guidance_style in guidance_styles:
        for interaction_type in interaction_types:
            agent.update_memory.reset_mock()
            with patch.object(MemoryManager, "_create_memory_update_prompt", return_value="Mocked prompt") as mock_prompt:
                await MemoryManager.prompt_agent_for_memory_update(
                    agent,
                    context,
                    "Round content",
                    memory_guidance_style=guidance_style,
                    language_manager=language_manager,
                    interaction_type=interaction_type,
                )

            mock_prompt.assert_called_once()
            args, _ = mock_prompt.call_args
            assert args[:3] == ("Previous memory", "Round content", guidance_style)
            assert args[3] is language_manager
            assert args[4] == interaction_type
            assert args[5] == context.round_number
            assert args[6] == "phase_1"
