"""
Discussion Service for Phase 2 Discussion Management.

Handles discussion prompts, statement validation, and group composition formatting
with multilingual support and language-aware validation.
"""

from typing import List, Optional, Protocol
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState


class LanguageProvider(Protocol):
    """Protocol for language managers that provide localized messages."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized message with substitutions."""
        ...


class Logger(Protocol):
    """Protocol for logging information and warnings."""
    def log_info(self, message: str) -> None:
        """Log an info message."""
        ...
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...


class DiscussionService:
    """
    Manages discussion prompts, statement validation, and group composition formatting.
    
    Provides centralized discussion/reasoning prompt generation with multilingual support
    and language-aware statement validation.
    """
    
    def __init__(self, language_manager: LanguageProvider, settings: Optional[Phase2Settings] = None,
                 logger: Optional[Logger] = None):
        """
        Initialize discussion service.
        
        Args:
            language_manager: For localized message retrieval
            settings: Phase 2 settings for validation rules (optional)
            logger: For logging info and warnings (optional)
        """
        self.language_manager = language_manager
        self.settings = settings or Phase2Settings.get_default()
        self.logger = logger
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger is available."""
        if self.logger:
            self.logger.log_info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log warning message if logger is available."""
        if self.logger:
            self.logger.log_warning(message)
    
    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            # Return English fallback or key name
            return f"[MISSING: {key}]"
    
    def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                               max_rounds: int, participant_names: List[str],
                               internal_reasoning: str = "") -> str:
        """
        Build localized discussion prompt with history and group composition.
        
        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds
            participant_names: List of participant names for group composition
            internal_reasoning: Optional internal reasoning to include
            
        Returns:
            Formatted discussion prompt with group composition and reasoning
        """
        language_manager = self.language_manager
        
        # Generate group composition
        group_participants = self.format_group_composition(participant_names)
        
        # Always use complex mode prompts (formal voting system)
        base_prompt = language_manager.get("prompts.phase2_discussion_prompt",
                                          round_number=round_num,
                                          max_rounds=max_rounds,
                                          discussion_history=discussion_state.public_history or "No previous discussion.",
                                          group_participants=group_participants)
        
        # If internal reasoning is provided, include it in the prompt
        if internal_reasoning and internal_reasoning.strip():
            return f"{base_prompt}\n\n{self._get_localized_message('voting_prompts.internal_reasoning_section')}\n{internal_reasoning}\n================================\n\n{self._get_localized_message('voting_prompts.reasoning_prompt')}"
        else:
            return base_prompt
    
    def build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                                      max_rounds: int) -> str:
        """
        Build prompt for internal reasoning before public statement.
        
        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds
            
        Returns:
            Formatted internal reasoning prompt
        """
        language_manager = self.language_manager
        
        return language_manager.get("prompts.phase2_internal_reasoning",
                                   round_number=round_num,
                                   max_rounds=max_rounds,
                                   discussion_history=discussion_state.public_history or "No previous discussion.")
    
    def format_group_composition(self, participant_names: List[str]) -> str:
        """
        Format localized group composition message.
        
        Args:
            participant_names: List of participant names
            
        Returns:
            Formatted group composition message with proper localization
        """
        if not participant_names:
            return ""
        
        if len(participant_names) == 1:
            participant_list = participant_names[0]
        else:
            # Format as "A, B, and C" or "A and B"
            participant_list = ", ".join(participant_names[:-1]) + f" and {participant_names[-1]}"
        
        return self._get_localized_message(
            "system_messages.discussion.group_composition", 
            participants=participant_list
        )
    
    def validate_statement(self, statement: str, participant_name: str, language: str) -> bool:
        """
        Validate that a statement is non-empty and meaningful with language awareness.
        
        Reuses existing validation logic with language-aware minimum length checking.
        
        Args:
            statement: The statement to validate
            participant_name: Name of the participant for logging
            language: Language being used (for appropriate minimum length)
            
        Returns:
            True if statement is valid, False otherwise
        """
        if not statement:
            self._log_warning(f"Empty statement received from {participant_name}")
            return False
            
        if not statement.strip():
            self._log_warning(f"Whitespace-only statement received from {participant_name}")
            return False
        
        # Get language-appropriate minimum length
        min_length = self.settings.get_min_statement_length(language)
        
        # Count actual characters (handle multi-byte characters properly)
        statement_length = len(statement.strip())
        
        # Check for minimum meaningful content 
        if statement_length < min_length:
            self._log_warning(f"Statement too short from {participant_name}: '{statement.strip()[:50]}...' ({statement_length} chars, min: {min_length})")
            return False
            
        self._log_info(f"Valid statement received from {participant_name} ({statement_length} characters, language: {language})")
        return True
    
    def is_cjk_language(self, language: str) -> bool:
        """
        Check if language uses CJK characters.
        
        Args:
            language: Language name to check
            
        Returns:
            True if language uses CJK characters
        """
        return self.settings.is_cjk_language(language)
    
    def get_min_statement_length(self, language: str) -> int:
        """
        Get minimum statement length based on language.
        
        Args:
            language: Language name
            
        Returns:
            Minimum character length for valid statements in this language
        """
        return self.settings.get_min_statement_length(language)