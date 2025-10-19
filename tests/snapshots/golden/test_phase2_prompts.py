"""
Golden tests for Phase 2 prompt generation.

These tests create snapshots of prompt content across different languages
to detect unintentional changes during refactoring. They help ensure that
the DiscussionService produces identical prompts to the original Phase2Manager.
"""

import pytest
from unittest.mock import Mock
from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState
from utils.language_manager import LanguageManager, SupportedLanguage


class TestPhase2PromptGolden:
    """Golden tests for Phase 2 prompt generation across languages."""
    
    def setup_method(self):
        """Set up test fixtures with real language managers."""
        # We'll use mock language managers with realistic translations
        self.english_translations = {
            "prompts.phase2_discussion_prompt": (
                "This is round {round_number} of {max_rounds}. Previous discussion:\n"
                "{discussion_history}\n\n"
                "Group participants: {group_participants}\n\n"
                "Please provide your perspective on which justice principle the group should adopt, "
                "considering both your own situation and fairness to all group members. "
                "You may also initiate formal voting if you believe the group is ready to decide."
            ),
            "prompts.phase2_internal_reasoning": (
                "This is round {round_number} of {max_rounds}. Previous discussion:\n"
                "{discussion_history}\n\n"
                "Before making your public statement, think through your reasoning privately. "
                "Consider your income situation, the principles, and what you've heard from others."
            ),
            "system_messages.discussion.group_composition": "The group consists of {participants}",
            "voting_prompts.internal_reasoning_section": "Your internal reasoning:",
            "voting_prompts.reasoning_prompt": "Now provide your public statement:"
        }
        
        self.spanish_translations = {
            "prompts.phase2_discussion_prompt": (
                "Esta es la ronda {round_number} de {max_rounds}. Discusión previa:\n"
                "{discussion_history}\n\n"
                "Participantes del grupo: {group_participants}\n\n"
                "Proporcione su perspectiva sobre qué principio de justicia debe adoptar el grupo, "
                "considerando tanto su propia situación como la equidad para todos los miembros. "
                "También puede iniciar votación formal si cree que el grupo está listo para decidir."
            ),
            "prompts.phase2_internal_reasoning": (
                "Esta es la ronda {round_number} de {max_rounds}. Discusión previa:\n"
                "{discussion_history}\n\n"
                "Antes de hacer su declaración pública, reflexione sobre su razonamiento en privado. "
                "Considere su situación económica, los principios y lo que ha escuchado de otros."
            ),
            "system_messages.discussion.group_composition": "El grupo consiste de {participants}",
            "voting_prompts.internal_reasoning_section": "Su razonamiento interno:",
            "voting_prompts.reasoning_prompt": "Ahora proporcione su declaración pública:"
        }
        
        self.chinese_translations = {
            "prompts.phase2_discussion_prompt": (
                "这是第{round_number}轮，共{max_rounds}轮。之前的讨论：\n"
                "{discussion_history}\n\n"
                "小组参与者：{group_participants}\n\n"
                "请提供您对小组应该采用哪种正义原则的看法，"
                "既要考虑您自己的情况，也要考虑对所有小组成员的公平性。"
                "如果您认为小组准备好做决定，您也可以发起正式投票。"
            ),
            "prompts.phase2_internal_reasoning": (
                "这是第{round_number}轮，共{max_rounds}轮。之前的讨论：\n"
                "{discussion_history}\n\n"
                "在做出公开声明之前，请私下思考您的推理。"
                "考虑您的收入状况、原则以及您从他人那里听到的内容。"
            ),
            "system_messages.discussion.group_composition": "小组由{participants}组成",
            "voting_prompts.internal_reasoning_section": "您的内部推理：",
            "voting_prompts.reasoning_prompt": "现在请提供您的公开声明："
        }
        
    def create_mock_language_manager(self, translations):
        """Create a mock language manager with given translations."""
        manager = Mock()
        manager.get.side_effect = lambda key, **kwargs: translations.get(key, f"[MISSING: {key}]").format(**kwargs)
        return manager
    
    def create_discussion_state(self, history_content=None):
        """Create a discussion state with optional history."""
        state = GroupDiscussionState()
        if history_content:
            state.public_history = history_content
        return state
    
    def test_english_discussion_prompt_golden(self, text_regression):
        """Golden test for English discussion prompt generation."""
        language_manager = self.create_mock_language_manager(self.english_translations)
        service = DiscussionService(language_manager)

        discussion_state = self.create_discussion_state("Alice: I prefer principle A.\nBob: I think principle B is better.")

        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob", "Charlie"]
        )
        text_regression.check(prompt)
    
    def test_spanish_discussion_prompt_golden(self, text_regression):
        """Golden test for Spanish discussion prompt generation."""
        language_manager = self.create_mock_language_manager(self.spanish_translations)
        service = DiscussionService(language_manager)

        discussion_state = self.create_discussion_state("Alice: Prefiero el principio A.\nBob: Creo que el principio B es mejor.")
        
        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"]
        )
        text_regression.check(prompt)
    
    def test_chinese_discussion_prompt_golden(self, text_regression):
        """Golden test for Chinese discussion prompt generation."""
        language_manager = self.create_mock_language_manager(self.chinese_translations)
        service = DiscussionService(language_manager)

        discussion_state = self.create_discussion_state("Alice: 我更喜欢原则A。\nBob: 我认为原则B更好。")
        
        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=4,
            participant_names=["Alice", "Bob", "Charlie", "David"]
        )
        text_regression.check(prompt)
    
    def test_english_internal_reasoning_prompt_golden(self, text_regression):
        """Golden test for English internal reasoning prompt generation."""
        language_manager = self.create_mock_language_manager(self.english_translations)
        service = DiscussionService(language_manager)

        discussion_state = self.create_discussion_state("Previous discussion about principles")

        prompt = service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5
        )
        text_regression.check(prompt)
    
    def test_english_discussion_prompt_with_reasoning_golden(self, text_regression):
        """Golden test for English discussion prompt with internal reasoning included."""
        language_manager = self.create_mock_language_manager(self.english_translations)
        service = DiscussionService(language_manager)

        discussion_state = self.create_discussion_state("Short history")
        internal_reasoning = "I need to consider fairness while protecting my interests."

        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice"],
            internal_reasoning=internal_reasoning
        )
        text_regression.check(prompt)

    def test_discussion_history_section_uses_neutral_formatting(self):
        """Ensure discussion history section avoids markdown emphasis delimiters."""
        manager = LanguageManager()
        manager.set_language(SupportedLanguage.ENGLISH)

        history = "Round 1 / Speaker: Alice Statement: **Bold idea**"
        section = manager.format_phase2_discussion_instructions(
            round_number=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"],
            discussion_history=history,
        )

        lines = section.splitlines()
        assert lines[0] == "--- DISCUSSION HISTORY ---"
        assert "===" not in section
        assert "**" not in section
        assert lines[-1] == "--------------------------"

        # All transcript lines should be indented to render as code block
        transcript_lines = lines[1:-1]
        assert transcript_lines, "Expected transcript content between headers"
        for line in transcript_lines:
            if line.strip():
                assert line.startswith("    "), f"Line not indented: {line!r}"
    
    def test_group_composition_formatting_golden(self):
        """Golden test for group composition formatting across different participant counts."""
        language_manager = self.create_mock_language_manager(self.english_translations)
        service = DiscussionService(language_manager)
        
        # Test single participant
        single = service.format_group_composition(["Alice"])
        assert single == "The group consists of Alice"
        
        # Test two participants
        two = service.format_group_composition(["Alice", "Bob"])
        assert two == "The group consists of Alice and Bob"
        
        # Test three participants
        three = service.format_group_composition(["Alice", "Bob", "Charlie"])
        assert three == "The group consists of Alice, Bob and Charlie"
        
        # Test four participants
        four = service.format_group_composition(["Alice", "Bob", "Charlie", "David"])
        assert four == "The group consists of Alice, Bob, Charlie and David"
    
    def test_empty_history_handling_golden(self, data_regression):
        """Golden test for handling empty or None discussion history."""
        language_manager = self.create_mock_language_manager(self.english_translations)
        service = DiscussionService(language_manager)
        
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
        
        data_regression.check({
            "none_history": prompt,
            "empty_history": prompt2,
        })


class TestPhase2PromptRegression:
    """Regression tests to ensure exact behavior match with original implementation."""
    
    def test_prompt_parameters_preservation(self):
        """Test that all expected parameters are passed to language manager."""
        language_manager = Mock()
        # Set up specific return values for different calls
        def mock_get(key, **kwargs):
            if key == "system_messages.discussion.group_composition":
                return f"The group consists of {kwargs.get('participants', '')}"
            elif key == "prompts.phase2_discussion_prompt":
                return "test prompt"
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
        language_manager.get.assert_any_call(
            "prompts.phase2_discussion_prompt",
            round_number=3,
            max_rounds=5,
            discussion_history="test history",
            group_participants="The group consists of A, B and C"
        )
    
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
            "prompts.phase2_internal_reasoning",
            round_number=2,
            max_rounds=4,
            discussion_history="reasoning history"
        )
