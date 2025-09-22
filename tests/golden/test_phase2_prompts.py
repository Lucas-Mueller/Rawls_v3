"""Structural tests for Phase 2 prompt generation."""
from __future__ import annotations

import pytest

from core.services.discussion_service import DiscussionService
from models import GroupDiscussionState
from tests.utils.prompt_assertions import assert_prompt_contains

pytestmark = pytest.mark.contracts


@pytest.fixture
def english_service(mocker):
    translations = {
        "prompts.phase2_discussion_short_prompt": "Round {round_number} of {max_rounds}.",
        "prompts.phase2_internal_reasoning": "History: {discussion_history} ({round_number}/{max_rounds})",
        "prompts.phase2_internal_reasoning_short": "Round {round_number}/{max_rounds} reasoning",
        "system_messages.discussion.group_composition": "Participants: {participants}",
    }
    manager = mocker.Mock()
    manager.get.side_effect = lambda key, **kwargs: translations[key].format(**kwargs)
    return DiscussionService(manager)


@pytest.fixture
def discussion_state():
    state = GroupDiscussionState()
    state.public_history = "Alice: Hello\nBob: Hi"
    return state


@pytest.mark.parametrize("round_num,max_rounds", [(2, 5), (1, 3)])
def test_discussion_prompt_contains_round_info(english_service, discussion_state, round_num, max_rounds):
    prompt = english_service.build_discussion_prompt(
        discussion_state, round_num=round_num, max_rounds=max_rounds, participant_names=["Alice", "Bob"]
    )
    assert_prompt_contains(prompt, [f"Round {round_num} of {max_rounds}."])


@pytest.mark.parametrize("round_num,max_rounds", [(1, 3), (2, 3)])
def test_internal_reasoning_prompts(english_service, discussion_state, round_num, max_rounds):
    prompt = english_service.build_internal_reasoning_prompt(discussion_state, round_num=round_num, max_rounds=max_rounds)
    if round_num == 1:
        assert "History:" in prompt
    else:
        assert prompt == f"Round {round_num}/{max_rounds} reasoning"
