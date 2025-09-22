"""Contract tests for `DiscussionService`."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState

pytestmark = pytest.mark.contracts


@dataclass
class StubLanguageManager:
    translations: dict

    def get(self, key: str, **kwargs) -> str:
        template = self.translations[key]
        return template.format(**kwargs)


@dataclass
class StubLogger:
    infos: list
    warnings: list

    def log_info(self, message: str) -> None:  # pragma: no cover - log-only helper
        self.infos.append(message)

    def log_warning(self, message: str) -> None:  # pragma: no cover - log-only helper
        self.warnings.append(message)


@pytest.fixture
def language_manager():
    return StubLanguageManager(
        translations={
            "prompts.phase2_discussion_short_prompt": "Round {round_number} of {max_rounds}.",
            "prompts.phase2_internal_reasoning": "History: {discussion_history} ({round_number}/{max_rounds})",
            "prompts.phase2_internal_reasoning_short": "Round {round_number}/{max_rounds} reasoning",
            "system_messages.discussion.group_composition": "Participants: {participants}",
            "discussion_format.round_speaker_format": "Round {round_number}: {speaker_name} said {statement}",
        }
    )


@pytest.fixture
def discussion_state():
    state = GroupDiscussionState()
    state.add_statement("Alice", "Hello")
    return state


def test_discussion_prompt_uses_language_manager(language_manager, discussion_state):
    service = DiscussionService(language_manager)
    prompt = service.build_discussion_prompt(discussion_state, round_num=2, max_rounds=5, participant_names=["Alice", "Bob"])
    assert prompt == "Round 2 of 5."


def test_internal_reasoning_prompt_first_round(language_manager, discussion_state):
    service = DiscussionService(language_manager)
    discussion_state.round_number = 1
    prompt = service.build_internal_reasoning_prompt(discussion_state, round_num=1, max_rounds=3)
    assert "History" in prompt


def test_internal_reasoning_prompt_subsequent_round(language_manager, discussion_state):
    service = DiscussionService(language_manager)
    prompt = service.build_internal_reasoning_prompt(discussion_state, round_num=2, max_rounds=3)
    assert prompt == "Round 2/3 reasoning"


def test_group_composition_formats_list(language_manager):
    service = DiscussionService(language_manager)
    message = service.format_group_composition(["Alice", "Bob", "Charlie"])
    assert message == "Participants: Alice, Bob and Charlie"


def test_validate_statement_checks_length(language_manager):
    settings = Phase2Settings.get_default()
    settings.min_statement_length = {"english": 5}
    logger = StubLogger(infos=[], warnings=[])
    service = DiscussionService(language_manager, settings=settings, logger=logger)

    assert service.validate_statement("Hello world", "Alice", "english") is True
    assert service.validate_statement("Hi", "Alice", "english") is False
    assert any("below minimum" in warning for warning in logger.warnings)
*** End Patch
