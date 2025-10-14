"""Component tests for the DiscussionService."""
from __future__ import annotations

import pytest

from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState, ParticipantContext, ExperimentPhase, ExperimentStage
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
    assert prompt.strip()
    assert "statement" in prompt.lower()


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


@pytest.mark.component
def test_internal_reasoning_prompt_includes_manipulator_target_note_round_one():
    language_manager = build_language_manager(SupportedLanguage.ENGLISH)
    service = DiscussionService(
        language_manager=language_manager,
        settings=Phase2Settings.get_default(),
    )
    state = GroupDiscussionState(round_number=1)

    role_description = "\n".join(
        [
            language_manager.get("manipulator.target_header"),
            language_manager.get("manipulator.target_principle_line", principle="maximizing_floor"),
            language_manager.get("manipulator.target_method_line"),
            language_manager.get("manipulator.target_guidance"),
            "",
            "Base manipulator instructions.",
        ]
    )

    context = ParticipantContext(
        name="Agent_4",
        role_description=role_description,
        bank_balance=0.0,
        memory="",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        memory_character_limit=25000,
        stage=ExperimentStage.DISCUSSION,
    )

    prompt = service.build_internal_reasoning_prompt(
        state,
        round_num=1,
        max_rounds=10,
        context=context,
    )

    expected_note = language_manager.get(
        "manipulator.reasoning_target_reminder",
        principle_name=language_manager.get("common.principle_names.maximizing_floor"),
    )

    assert expected_note in prompt


@pytest.mark.component
def test_internal_reasoning_prompt_uses_clean_history():
    """Test that internal reasoning prompt correctly uses history (stripping now happens at source)."""
    class CaptureLanguageManager:
        def __init__(self):
            self.captured_history = None

        def get(self, key: str, **kwargs):
            if key == "prompts.phase2_internal_reasoning":
                self.captured_history = kwargs.get("discussion_history")
                return "prompt"
            if key == "no_previous_discussion_placeholder":
                return "No previous discussion."
            if key == "discussion_format.round_speaker_format":
                # Simulate the formatting template
                return f"Round {kwargs['round_number']} / Speaker: {kwargs['speaker_name']} Statement: {kwargs['statement']}"
            return ""

    language_manager = CaptureLanguageManager()
    service = DiscussionService(
        language_manager=language_manager,
        settings=Phase2Settings.get_default(),
    )
    state = GroupDiscussionState(round_number=1)

    # Add statements with bold markers - they should be stripped when added
    state.add_statement("Alice", "**Bold** intro", language_manager)
    state.add_statement("Bob", "__Under__ line", language_manager)

    service.build_internal_reasoning_prompt(state, round_num=1, max_rounds=4)

    # Verify history is clean (stripping happened at source)
    assert "**" not in state.public_history
    assert "__" not in state.public_history
    assert "Bold intro" in state.public_history
    assert "Under line" in state.public_history
