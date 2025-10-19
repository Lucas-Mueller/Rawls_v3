"""
Golden tests for Phase 2 service-level prompt outputs.

These tests snapshot the ACTUAL prompts that services return today, before refactoring.
They use REAL LanguageManager with REAL translations to ensure we capture production behavior.

Purpose: Lock in current service outputs to detect unintended changes during the
_current_public_history refactoring (Phase 2 prompt streamlining).
"""

import pytest
from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState
from utils.language_manager import LanguageManager, SupportedLanguage


class TestDiscussionServicePromptGolden:
    """Golden tests for DiscussionService prompt outputs."""

    @pytest.fixture
    def english_service(self):
        """Create DiscussionService with English language manager."""
        language_manager = LanguageManager()
        language_manager.set_language(SupportedLanguage.ENGLISH)
        return DiscussionService(language_manager, Phase2Settings.get_default())

    @pytest.fixture
    def spanish_service(self):
        """Create DiscussionService with Spanish language manager."""
        language_manager = LanguageManager()
        language_manager.set_language(SupportedLanguage.SPANISH)
        return DiscussionService(language_manager, Phase2Settings.get_default())

    @pytest.fixture
    def mandarin_service(self):
        """Create DiscussionService with Mandarin language manager."""
        language_manager = LanguageManager()
        language_manager.set_language(SupportedLanguage.MANDARIN)
        return DiscussionService(language_manager, Phase2Settings.get_default())

    def test_build_discussion_prompt_english(self, english_service):
        """
        Golden test: build_discussion_prompt returns short task prompt in English.

        NOTE: The discussion history and round info are NOT in this prompt.
        They are provided via the context header (set by Phase2Manager before Runner call).
        This service method just returns the task-specific prompt.
        """
        discussion_state = GroupDiscussionState(
            round_number=2,
            public_history="Alice: I prefer principle 2\nBob: I agree with Alice"
        )

        prompt = english_service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob", "Charlie"]
        )

        # This is the ACTUAL production output
        expected = "What is your statement to the group for this round?"
        assert prompt == expected, (
            f"Discussion prompt changed!\n"
            f"Expected: {expected!r}\n"
            f"Got: {prompt!r}\n"
            f"If this change is intentional, update this golden test."
        )

    def test_build_discussion_prompt_spanish(self, spanish_service):
        """Golden test: build_discussion_prompt returns short task prompt in Spanish."""
        discussion_state = GroupDiscussionState(
            round_number=3,
            public_history="Alice: Prefiero el principio 2"
        )

        prompt = spanish_service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=5,
            participant_names=["Alice", "Bob"]
        )

        expected = "¿Cuál es su declaración al grupo para esta ronda?"
        assert prompt == expected, (
            f"Discussion prompt changed!\n"
            f"Expected: {expected!r}\n"
            f"Got: {prompt!r}"
        )

    def test_build_discussion_prompt_mandarin(self, mandarin_service):
        """Golden test: build_discussion_prompt returns short task prompt in Mandarin."""
        discussion_state = GroupDiscussionState(
            round_number=1,
            public_history=""
        )

        prompt = mandarin_service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=10,
            participant_names=["Alice", "Bob", "Charlie", "David"]
        )

        expected = "你在这一轮对小组的陈述是什么？"
        assert prompt == expected, (
            f"Discussion prompt changed!\n"
            f"Expected: {expected!r}\n"
            f"Got: {prompt!r}"
        )

    def test_build_internal_reasoning_prompt_round1_english(self, english_service):
        """
        Golden test: build_internal_reasoning_prompt for round 1.

        Round 1 uses the FULL prompt with Phase 2 explanation.

        NOTE: Even though the service code tries to pass discussion_history to the template,
        the template (prompts.phase2_internal_reasoning) does NOT actually use it.
        History is provided via the context header instead (set by Phase2Manager).
        """
        discussion_state = GroupDiscussionState(
            round_number=1,
            public_history="Alice: I think we should choose principle 1\nBob: I disagree"
        )

        prompt = english_service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=5
        )

        # Check that it contains expected elements
        assert "Round 1" in prompt, "Should mention round number"
        assert "5" in prompt, "Should mention max rounds"
        assert "Phase 2" in prompt, "Should include Phase 2 explanation"
        assert "Group Discussion" in prompt, "Should include discussion header"
        # History is NOT in this prompt (it's in context header instead)
        assert "Alice: I think we should choose principle 1" not in prompt, (
            "History should NOT be in internal reasoning prompt (it's in context header)"
        )

    def test_build_internal_reasoning_prompt_round2plus_english(self, english_service):
        """
        Golden test: build_internal_reasoning_prompt for round 2+ (NO history).

        Rounds 2+ use SHORT prompt without history (history is in context header).
        """
        discussion_state = GroupDiscussionState(
            round_number=3,
            public_history="Alice: Statement 1\nBob: Statement 2"
        )

        prompt = english_service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=5
        )

        # Check that it's the short version
        assert "Round 3" in prompt, "Should mention round number"
        assert "5" in prompt, "Should mention max rounds"
        # Should NOT include full Phase 2 explanation
        assert "Alice: Statement 1" not in prompt, "Should NOT include history in short prompt"

    def test_build_internal_reasoning_prompt_spanish(self, spanish_service):
        """Golden test: internal reasoning prompt in Spanish (round 1)."""
        discussion_state = GroupDiscussionState(
            round_number=1,
            public_history="Alice: Prefiero principio 1"
        )

        prompt = spanish_service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3
        )

        # Check Spanish content
        assert "Ronda 1" in prompt or "ronda 1" in prompt, "Should mention round in Spanish"
        assert "Fase 2" in prompt, "Should include Phase 2 explanation in Spanish"
        # History is NOT in internal reasoning prompt (it's in context header)
        assert "Alice: Prefiero principio 1" not in prompt, (
            "History should NOT be in internal reasoning prompt"
        )

    def test_build_internal_reasoning_prompt_mandarin(self, mandarin_service):
        """Golden test: internal reasoning prompt in Mandarin (round 1)."""
        discussion_state = GroupDiscussionState(
            round_number=1,
            public_history="Alice: 我更喜欢原则1"
        )

        prompt = mandarin_service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=5
        )

        # Check Mandarin content
        assert "1" in prompt, "Should mention round number"
        assert "第二阶段" in prompt or "阶段" in prompt, "Should include Phase 2 explanation in Mandarin"
        # History is NOT in internal reasoning prompt (it's in context header)
        assert "Alice: 我更喜欢原则1" not in prompt, (
            "History should NOT be in internal reasoning prompt"
        )

    def test_format_group_composition_english(self, english_service):
        """Golden test: group composition formatting in English."""
        result = english_service.format_group_composition(["Alice", "Bob", "Charlie"])

        # Check format
        assert "Alice" in result
        assert "Bob" in result
        assert "Charlie" in result
        # Should be "Alice, Bob, and Charlie" format
        assert "," in result, "Should use comma separation"

    def test_format_group_composition_two_participants(self, english_service):
        """Golden test: group composition with only 2 participants."""
        result = english_service.format_group_composition(["Alice", "Bob"])

        assert "Alice" in result
        assert "Bob" in result
        assert " and " in result, "Should use 'and' for two participants"

    def test_format_group_composition_single_participant(self, english_service):
        """Golden test: group composition with single participant."""
        result = english_service.format_group_composition(["Alice"])

        assert "Alice" in result

    def test_format_group_composition_empty(self, english_service):
        """Golden test: group composition with empty list."""
        result = english_service.format_group_composition([])

        assert result == "", "Empty list should return empty string"


class TestValidationConsistency:
    """Test that validation logic remains consistent across refactoring."""

    @pytest.fixture
    def english_service(self):
        language_manager = LanguageManager()
        language_manager.set_language(SupportedLanguage.ENGLISH)
        return DiscussionService(language_manager, Phase2Settings.get_default())

    def test_validate_statement_accepts_valid_english(self, english_service):
        """Validate that reasonable English statements pass validation."""
        statement = "I believe we should choose the maximizing floor principle because it ensures fairness for the worst-off members of our society."

        is_valid = english_service.validate_statement(statement, "Alice", "english")

        assert is_valid, "Valid English statement should pass"

    def test_validate_statement_rejects_empty(self, english_service):
        """Validate that empty statements are rejected."""
        is_valid = english_service.validate_statement("", "Alice", "english")

        assert not is_valid, "Empty statement should fail validation"

    def test_validate_statement_rejects_whitespace_only(self, english_service):
        """Validate that whitespace-only statements are rejected."""
        is_valid = english_service.validate_statement("   \n\t  ", "Alice", "english")

        assert not is_valid, "Whitespace-only statement should fail validation"

    def test_validate_statement_rejects_too_short(self, english_service):
        """Validate that very short statements are rejected."""
        # Minimum length varies by language; English typically requires ~20 chars
        is_valid = english_service.validate_statement("Yes", "Alice", "english")

        assert not is_valid, "Very short statement should fail validation"


# Additional note for future developers:
"""
IMPORTANT: These tests snapshot the CURRENT service behavior before refactoring.

After the Phase 2 prompt streamlining refactoring (replacing _current_public_history
with explicit context.formatted_context_header), these service-level outputs should
remain EXACTLY THE SAME.

If these tests fail after refactoring, it means:
1. Either you accidentally changed service behavior (BAD - revert your changes)
2. Or you intentionally changed prompts (update tests and document why)

The refactoring should NOT change what services return - it should only change
HOW context headers are passed to agents (from side channel to explicit field).
"""
