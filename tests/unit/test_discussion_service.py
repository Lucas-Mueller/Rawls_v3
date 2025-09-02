"""
Unit tests for DiscussionService.

Tests prompt building, statement validation, and group composition formatting.
"""

import pytest
from unittest.mock import Mock
from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState


class MockLanguageManager:
    """Mock language manager for testing."""
    
    def __init__(self):
        self.translations = {
            "prompts.phase2_discussion_prompt": "Round {round_number}/{max_rounds}. History: {discussion_history}. Group: {group_participants}. Please discuss.",
            "prompts.phase2_internal_reasoning": "Round {round_number}/{max_rounds}. History: {discussion_history}. Think internally.",
            "system_messages.discussion.group_composition": "The group consists of {participants}",
            "voting_prompts.internal_reasoning_section": "Your internal reasoning:",
            "voting_prompts.reasoning_prompt": "Now make your public statement:"
        }
        
    def get(self, key: str, **kwargs) -> str:
        """Get localized message with substitutions."""
        template = self.translations.get(key, f"[MISSING: {key}]")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"[ERROR: Missing parameter {e} for key {key}]"


class TestDiscussionService:
    """Test DiscussionService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager()
        self.settings = Phase2Settings()
        self.logger = Mock()
        
        self.service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger
        )
        
        # Create mock discussion state
        self.discussion_state = GroupDiscussionState()
        self.discussion_state.public_history = "Alice: I prefer principle A.\nBob: I like principle B."
    
    def test_build_discussion_prompt_basic(self):
        """Test basic discussion prompt building."""
        prompt = self.service.build_discussion_prompt(
            discussion_state=self.discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob", "Charlie"]
        )
        
        expected = "Round 2/5. History: Alice: I prefer principle A.\nBob: I like principle B.. Group: The group consists of Alice, Bob and Charlie. Please discuss."
        assert prompt == expected
    
    def test_build_discussion_prompt_with_reasoning(self):
        """Test discussion prompt with internal reasoning included."""
        internal_reasoning = "I think we should focus on fairness."
        
        prompt = self.service.build_discussion_prompt(
            discussion_state=self.discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"],
            internal_reasoning=internal_reasoning
        )
        
        base_expected = "Round 1/3. History: Alice: I prefer principle A.\nBob: I like principle B.. Group: The group consists of Alice and Bob. Please discuss."
        reasoning_section = "\n\nYour internal reasoning:\nI think we should focus on fairness.\n================================\n\nNow make your public statement:"
        
        assert prompt == base_expected + reasoning_section
    
    def test_build_discussion_prompt_empty_reasoning(self):
        """Test discussion prompt with empty internal reasoning (should be ignored)."""
        prompt = self.service.build_discussion_prompt(
            discussion_state=self.discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice", "Bob"],
            internal_reasoning="   "  # Whitespace only
        )
        
        expected = "Round 1/3. History: Alice: I prefer principle A.\nBob: I like principle B.. Group: The group consists of Alice and Bob. Please discuss."
        assert prompt == expected
    
    def test_build_discussion_prompt_no_history(self):
        """Test discussion prompt with no previous history."""
        empty_state = GroupDiscussionState()
        
        prompt = self.service.build_discussion_prompt(
            discussion_state=empty_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice"]
        )
        
        expected = "Round 1/3. History: No previous discussion.. Group: The group consists of Alice. Please discuss."
        assert prompt == expected
    
    def test_build_internal_reasoning_prompt(self):
        """Test internal reasoning prompt building."""
        prompt = self.service.build_internal_reasoning_prompt(
            discussion_state=self.discussion_state,
            round_num=2,
            max_rounds=4
        )
        
        expected = "Round 2/4. History: Alice: I prefer principle A.\nBob: I like principle B.. Think internally."
        assert prompt == expected
    
    def test_format_group_composition_single_participant(self):
        """Test group composition formatting with single participant."""
        result = self.service.format_group_composition(["Alice"])
        expected = "The group consists of Alice"
        assert result == expected
    
    def test_format_group_composition_two_participants(self):
        """Test group composition formatting with two participants."""
        result = self.service.format_group_composition(["Alice", "Bob"])
        expected = "The group consists of Alice and Bob"
        assert result == expected
    
    def test_format_group_composition_multiple_participants(self):
        """Test group composition formatting with multiple participants."""
        result = self.service.format_group_composition(["Alice", "Bob", "Charlie", "David"])
        expected = "The group consists of Alice, Bob, Charlie and David"
        assert result == expected
    
    def test_format_group_composition_empty_list(self):
        """Test group composition formatting with empty participant list."""
        result = self.service.format_group_composition([])
        assert result == ""
    
    def test_validate_statement_valid_english(self):
        """Test statement validation with valid English statement."""
        statement = "I think we should consider principle A because it's more fair."
        result = self.service.validate_statement(statement, "Alice", "English")
        
        assert result is True
        self.logger.log_info.assert_called_with(
            "Valid statement received from Alice (62 characters, language: English)"
        )
    
    def test_validate_statement_valid_cjk(self):
        """Test statement validation with valid CJK statement."""
        # Chinese text that's shorter but valid for CJK
        statement = "我觉得原则A更公平"  # 9 characters
        result = self.service.validate_statement(statement, "李华", "Chinese")
        
        assert result is True
        self.logger.log_info.assert_called_with(
            "Valid statement received from 李华 (9 characters, language: Chinese)"
        )
    
    def test_validate_statement_too_short_english(self):
        """Test statement validation with too short English statement."""
        statement = "Yes"  # Only 3 characters, default minimum is 10
        result = self.service.validate_statement(statement, "Alice", "English")
        
        assert result is False
        self.logger.log_warning.assert_called_with(
            "Statement too short from Alice: 'Yes...' (3 chars, min: 10)"
        )
    
    def test_validate_statement_too_short_cjk(self):
        """Test statement validation with too short CJK statement."""
        statement = "好"  # Only 1 character, CJK minimum is 5
        result = self.service.validate_statement(statement, "李华", "Chinese")
        
        assert result is False
        self.logger.log_warning.assert_called_with(
            "Statement too short from 李华: '好...' (1 chars, min: 5)"
        )
    
    def test_validate_statement_empty(self):
        """Test statement validation with empty statement."""
        result = self.service.validate_statement("", "Alice", "English")
        
        assert result is False
        self.logger.log_warning.assert_called_with(
            "Empty statement received from Alice"
        )
    
    def test_validate_statement_whitespace_only(self):
        """Test statement validation with whitespace-only statement."""
        result = self.service.validate_statement("   \n\t  ", "Alice", "English")
        
        assert result is False
        self.logger.log_warning.assert_called_with(
            "Whitespace-only statement received from Alice"
        )
    
    def test_validate_statement_with_leading_trailing_whitespace(self):
        """Test statement validation handles leading/trailing whitespace correctly."""
        statement = "   This is a valid statement with whitespace   "
        result = self.service.validate_statement(statement, "Alice", "English")
        
        assert result is True
        # Should count trimmed length (41 characters after stripping)
        self.logger.log_info.assert_called_with(
            "Valid statement received from Alice (41 characters, language: English)"
        )
    
    def test_is_cjk_language(self):
        """Test CJK language detection."""
        assert self.service.is_cjk_language("Chinese") is True
        assert self.service.is_cjk_language("Mandarin") is True
        assert self.service.is_cjk_language("Japanese") is True
        assert self.service.is_cjk_language("Korean") is True
        assert self.service.is_cjk_language("English") is False
        assert self.service.is_cjk_language("Spanish") is False
    
    def test_get_min_statement_length(self):
        """Test minimum statement length retrieval."""
        assert self.service.get_min_statement_length("English") == 10
        assert self.service.get_min_statement_length("Chinese") == 5
        assert self.service.get_min_statement_length("Mandarin") == 5
        assert self.service.get_min_statement_length("Spanish") == 10
    
    def test_missing_translation_key_handling(self):
        """Test handling of missing translation keys."""
        # Create a mock language manager that raises an exception
        mock_lang_manager = Mock()
        mock_lang_manager.get.side_effect = Exception("Translation key not found")
        
        service = DiscussionService(
            language_manager=mock_lang_manager,
            settings=self.settings,
            logger=self.logger
        )
        
        result = service._get_localized_message("missing.key")
        
        assert "[MISSING: missing.key]" in result
        # Check that warning was logged for missing key  
        self.logger.log_warning.assert_called_with(
            "Missing translation key: missing.key - Translation key not found"
        )
    
    def test_service_without_logger(self):
        """Test service functionality without logger."""
        service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings
        )
        
        # Should not crash when trying to log
        result = service.validate_statement("This is a valid statement", "Alice", "English")
        assert result is True
    
    def test_service_with_default_settings(self):
        """Test service functionality with default settings."""
        service = DiscussionService(language_manager=self.language_manager)
        
        # Should use default Phase2Settings
        assert service.settings.min_statement_length == 10
        assert service.settings.min_statement_length_cjk == 5


class TestDiscussionServiceEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = Mock()
        self.service = DiscussionService(self.language_manager)
    
    def test_language_manager_exception_handling(self):
        """Test handling of language manager exceptions."""
        # Configure mock to raise exception
        self.language_manager.get.side_effect = Exception("Translation error")
        
        result = self.service._get_localized_message("some.key", param="value")
        assert result == "[MISSING: some.key]"
    
    def test_build_prompt_with_none_history(self):
        """Test prompt building with None history."""
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = None
        
        # Mock the language manager to return predictable results
        def mock_get(key, **kwargs):
            if key == "prompts.phase2_discussion_prompt":
                return f"Mocked prompt with history: {kwargs.get('discussion_history', '')}"
            elif key == "system_messages.discussion.group_composition":
                return f"Group: {kwargs.get('participants', '')}"
            return f"[{key}]"
        
        self.language_manager.get.side_effect = mock_get
        
        prompt = self.service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=1,
            max_rounds=3,
            participant_names=["Alice"]
        )
        
        # Should handle None history gracefully by converting to "No previous discussion."
        assert "Mocked prompt with history: No previous discussion." in prompt