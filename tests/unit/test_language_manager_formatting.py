"""Tests for LanguageManager formatting sanitization."""

from utils.language_manager import LanguageManager, SupportedLanguage
from models.experiment_types import GroupDiscussionState


def test_format_phase2_discussion_instructions_with_clean_history() -> None:
    """Test that discussion instructions work correctly with clean history (stripping happens at source now)."""
    manager = LanguageManager()
    manager.set_language(SupportedLanguage.ENGLISH)

    # Create discussion state and add statements with bold markers
    state = GroupDiscussionState(round_number=1)
    state.add_statement("Alice", "**Round 1 summary**", manager)
    state.add_statement("Bob", "__Key point__", manager)

    # Verify stripping happened at source
    assert "**" not in state.public_history
    assert "__" not in state.public_history

    # Verify formatting works with clean history
    instructions = manager.format_phase2_discussion_instructions(
        round_number=1,
        max_rounds=3,
        participant_names=["Alice", "Bob"],
        discussion_history=state.public_history,
    )

    assert "**" not in instructions
    assert "__" not in instructions
    assert "Round 1 summary" in instructions
    assert "Key point" in instructions


def test_format_context_info_strips_markdown_emphasis_from_reasoning() -> None:
    manager = LanguageManager()
    manager.set_language(SupportedLanguage.ENGLISH)

    formatted_memory = manager.format_memory_section("Prior memory line")

    context = manager.format_context_info(
        name="Alice",
        role_description="Participant",
        bank_balance=10.0,
        phase="Phase 2",
        round_number=1,
        formatted_memory=formatted_memory,
        personality="Thoughtful",
        phase_instructions="Discussion instructions",
        experiment_config=None,
        internal_reasoning="**Bold insight** and __underlined stance__",
        stage=None,
        max_rounds=None,
        participant_names=None,
    )

    assert "**Bold insight**" not in context
    assert "__underlined stance__" not in context
    assert "Bold insight" in context
    assert "underlined stance" in context
