"""Component tests for the DiscussionService."""
from __future__ import annotations

import pytest

from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState
from tests.support import build_language_manager
from utils.language_manager import SupportedLanguage


@pytest.mark.component
def test_discussion_prompt_generation():
    service = DiscussionService(
        language_manager=build_language_manager(SupportedLanguage.ENGLISH),
        settings=Phase2Settings.get_default(),
    )
    state = GroupDiscussionState(
        current_round=1,
        max_rounds=3,
        discussion_history="Initial",
        statements=[],
        speaking_order=["Alice", "Bob"],
    )
    prompt = service.build_discussion_prompt(state, round_num=1, max_rounds=3, participant_names=["Alice", "Bob"])
    assert "round" in prompt.lower()
    assert "3" in prompt


@pytest.mark.component
def test_internal_reasoning_prompt_shifts_after_first_round():
    service = DiscussionService(
        language_manager=build_language_manager(SupportedLanguage.SPANISH),
        settings=Phase2Settings.get_default(),
    )
    state = GroupDiscussionState(
        current_round=2,
        max_rounds=5,
        discussion_history="Historial",
        statements=[],
        speaking_order=["A", "B"],
    )
    prompt = service.build_internal_reasoning_prompt(state, round_num=2, max_rounds=5)
    normalized = prompt.lower()
    assert "ronda" in normalized or "round" in normalized
    assert "5" in prompt
