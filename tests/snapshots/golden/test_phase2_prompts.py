"""
Golden tests for Phase 2 prompt generation.

These tests create snapshots of prompt content across different languages
to detect unintentional changes during refactoring. They help ensure that
the DiscussionService produces identical prompts to the original Phase2Manager.
"""

import json
from pathlib import Path
import pytest
from unittest.mock import Mock
from core.services.discussion_service import DiscussionService
from models import GroupDiscussionState
from utils.language_manager import LanguageManager, SupportedLanguage, create_language_manager

SNAPSHOT_DIR = Path(__file__).with_suffix("").parent / "test_phase2_prompts"


def assert_snapshot(name: str, content: str) -> None:
    path = SNAPSHOT_DIR / f"{name}.txt"
    expected = path.read_text(encoding="utf-8")
    assert content == expected


def assert_json_snapshot(name: str, payload: dict) -> None:
    path = SNAPSHOT_DIR / f"{name}.json"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert payload == expected


class TestPhase2PromptGolden:
    """Golden tests for Phase 2 prompt generation across languages."""

    def _create_service(self, language: SupportedLanguage) -> tuple[DiscussionService, LanguageManager]:
        """Create a discussion service and language manager for the requested language."""
        manager = create_language_manager(language)
        service = DiscussionService(manager)
        return service, manager
    
    def create_discussion_state(self, history_content=None):
        """Create a discussion state with optional history."""
        state = GroupDiscussionState()
        if history_content:
            state.public_history = history_content
        return state
    
    def test_english_discussion_prompt_golden(self):
        """Golden test for English discussion prompt generation."""
        service, _ = self._create_service(SupportedLanguage.ENGLISH)

        discussion_state = self.create_discussion_state("Alice: I prefer principle A.\nBob: I think principle B is better.")

        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob", "Charlie"]
        )
        assert_snapshot("test_english_discussion_prompt_golden", prompt)
    
    def test_spanish_discussion_prompt_golden(self):
        """Golden test for Spanish discussion prompt generation."""
        service, _ = self._create_service(SupportedLanguage.SPANISH)

        discussion_state = self.create_discussion_state("Alice: Prefiero el principio A.\nBob: Creo que el principio B es mejor.")
        
        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"]
        )
        assert_snapshot("test_spanish_discussion_prompt_golden", prompt)
    
    def test_chinese_discussion_prompt_golden(self):
        """Golden test for Chinese discussion prompt generation."""
        service, _ = self._create_service(SupportedLanguage.MANDARIN)

        discussion_state = self.create_discussion_state("Alice: 我更喜欢原则A。\nBob: 我认为原则B更好。")
        
        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=4,
            participant_names=["Alice", "Bob", "Charlie", "David"]
        )
        assert_snapshot("test_chinese_discussion_prompt_golden", prompt)
    
    def test_english_internal_reasoning_prompt_golden(self):
        """Golden test for English internal reasoning prompt generation."""
        service, _ = self._create_service(SupportedLanguage.ENGLISH)

        discussion_state = self.create_discussion_state("Previous discussion about principles")

        prompt = service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5
        )
        assert_snapshot("test_english_internal_reasoning_prompt_golden", prompt)
    
    def test_english_discussion_prompt_with_reasoning_golden(self):
        """Golden test for English discussion prompt with internal reasoning included."""
        service, _ = self._create_service(SupportedLanguage.ENGLISH)

        discussion_state = self.create_discussion_state("Short history")
        internal_reasoning = "I need to consider fairness while protecting my interests."

        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice"],
            internal_reasoning=internal_reasoning
        )
        assert_snapshot("test_english_discussion_prompt_with_reasoning_golden", prompt)

    def test_discussion_history_section_uses_neutral_formatting(self):
        """Ensure discussion history section avoids markdown emphasis delimiters."""
        manager = create_language_manager(SupportedLanguage.ENGLISH)

        history = "Round 1 / Speaker: Alice Statement: **Bold idea**"
        section = manager.format_phase2_discussion_instructions(
            round_number=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"],
            discussion_history=history,
        )

        lines = section.splitlines()
        assert lines[0] == "--- Discussion History ---"
        assert "===" not in section
        assert "**" not in section
        assert lines[-1] == "--------------------------"
        assert "Round 1 / Speaker: Alice Statement: Bold idea" in section
    
    def test_group_composition_formatting_golden(self):
        """Golden test for group composition formatting across different participant counts."""
        service, manager = self._create_service(SupportedLanguage.ENGLISH)
        
        # Test single participant
        single = service.format_group_composition(["Alice"])
        expected_single = manager.get(
            "system_messages.discussion.group_composition",
            participants="Alice",
        )
        assert single == expected_single
        
        # Test two participants
        two = service.format_group_composition(["Alice", "Bob"])
        two_list = manager.get(
            "common.list_formatting.two_items",
            first="Alice",
            second="Bob",
        )
        expected_two = manager.get(
            "system_messages.discussion.group_composition",
            participants=two_list,
        )
        assert two == expected_two
        
        # Test three participants
        three = service.format_group_composition(["Alice", "Bob", "Charlie"])
        three_list = manager.get(
            "common.list_formatting.three_plus_items",
            items=", ".join(["Alice", "Bob"]),
            last="Charlie",
        )
        expected_three = manager.get(
            "system_messages.discussion.group_composition",
            participants=three_list,
        )
        assert three == expected_three
        
        # Test four participants
        four = service.format_group_composition(["Alice", "Bob", "Charlie", "David"])
        four_list = manager.get(
            "common.list_formatting.three_plus_items",
            items=", ".join(["Alice", "Bob", "Charlie"]),
            last="David",
        )
        expected_four = manager.get(
            "system_messages.discussion.group_composition",
            participants=four_list,
        )
        assert four == expected_four
    
    def test_empty_history_handling_golden(self):
        """Golden test for handling empty or None discussion history."""
        service, _ = self._create_service(SupportedLanguage.ENGLISH)
        
        # Test with None history
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = None
        
        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=2,
            participant_names=["Alice", "Bob"]
        )
        
        # Test with empty string history (should still use "No previous discussion.")
        discussion_state.public_history = ""
        prompt2 = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=2,
            participant_names=["Alice", "Bob"]
        )
        
        assert_json_snapshot(
            "test_empty_history_handling_golden",
            {"none_history": prompt, "empty_history": prompt2},
        )


class TestPhase2PromptRegression:
    """Regression tests to ensure exact behavior match with original implementation."""
    
    def test_prompt_parameters_preservation(self):
        """Test that all expected parameters are passed to language manager."""
        language_manager = Mock()
        # Set up specific return values for different calls
        def mock_get(key, **kwargs):
            if key == "system_messages.discussion.group_composition":
                return f"The group consists of {kwargs.get('participants', '')}"
            if key == "common.list_formatting.two_items":
                return f"{kwargs.get('first')} and {kwargs.get('second')}"
            if key == "common.list_formatting.three_plus_items":
                items = kwargs.get('items', '')
                last = kwargs.get('last', '')
                return f"{items}, and {last}" if items else last
            if key == "prompts.phase2_discussion_prompt":
                return "test prompt"
            if key == "prompts.phase2_discussion_short_prompt":
                return "test short prompt"
            return f"[{key}]"
        
        language_manager.get.side_effect = mock_get
        
        service = DiscussionService(language_manager)
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "test history"
        
        service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=5,
            participant_names=["A", "B", "C"]
        )
        
        # Verify that language manager was called with correct parameters
        language_manager.get.assert_any_call("prompts.phase2_discussion_short_prompt")
    
    def test_internal_reasoning_parameters_preservation(self):
        """Test that internal reasoning prompt parameters are preserved."""
        language_manager = Mock()
        language_manager.get.return_value = "reasoning prompt"
        
        service = DiscussionService(language_manager)
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "reasoning history"
        
        service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=4
        )
        
        language_manager.get.assert_called_with(
            "prompts.phase2_internal_reasoning_short",
            round_number=2,
            max_rounds=4
        )
