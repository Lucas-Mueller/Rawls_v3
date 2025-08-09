"""
Language Manager for Multi-Language Support in Frohlich Experiment

This module handles loading and retrieving translated prompts and messages
based on the configured language setting.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for the experiment."""
    ENGLISH = "English"
    SPANISH = "Spanish"  
    MANDARIN = "Mandarin"


class LanguageManager:
    """Manages loading and retrieval of translated experiment content."""
    
    def __init__(self, translations_dir: str = "translations"):
        """
        Initialize the language manager.
        
        Args:
            translations_dir: Directory containing translation JSON files
        """
        self.translations_dir = translations_dir
        self.translations_cache: Dict[str, Dict[str, Any]] = {}
        self.current_language = SupportedLanguage.ENGLISH
        
        # Language file mappings
        self.language_files = {
            SupportedLanguage.ENGLISH: "english_prompts.json",
            SupportedLanguage.SPANISH: "spanish_prompts.json", 
            SupportedLanguage.MANDARIN: "mandarin_prompts.json"
        }
    
    def set_language(self, language: SupportedLanguage) -> None:
        """
        Set the current language for the experiment.
        
        Args:
            language: The language to use for all prompts and messages
        """
        if not isinstance(language, SupportedLanguage):
            raise ValueError(f"Unsupported language: {language}")
        
        self.current_language = language
        logger.info(f"Language set to: {language.value}")
    
    def load_language(self, language: SupportedLanguage) -> Dict[str, Any]:
        """
        Load translations for a specific language.
        
        Args:
            language: Language to load
            
        Returns:
            Dictionary containing all translations for the language
            
        Raises:
            FileNotFoundError: If translation file doesn't exist
            json.JSONDecodeError: If translation file is invalid
        """
        if language in self.translations_cache:
            return self.translations_cache[language]
        
        filename = self.language_files[language]
        filepath = os.path.join(self.translations_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Translation file not found: {filepath}. "
                f"Run translate_prompts.py to generate translation files."
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            
            self.translations_cache[language] = translations
            logger.info(f"Loaded translations for {language.value}")
            return translations
            
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in translation file {filepath}: {e}",
                e.doc, e.pos
            )
    
    def get_current_translations(self) -> Dict[str, Any]:
        """
        Get translations for the current language.
        
        Returns:
            Dictionary containing all translations for current language
        """
        return self.load_language(self.current_language)
    
    def get(self, path: str, **format_kwargs) -> str:
        """
        Get a translated string using dot notation path.
        
        Args:
            path: Dot-separated path to the translation (e.g., "common.principle_names.maximizing_floor")
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted string
            
        Raises:
            KeyError: If path doesn't exist
            ValueError: If formatting fails
        """
        try:
            translations = self.get_current_translations()
            
            # Navigate the path
            parts = path.split('.')
            current = translations
            
            for part in parts:
                if not isinstance(current, dict):
                    raise KeyError(f"Cannot navigate further in path '{path}' at '{part}'")
                current = current[part]
            
            # Ensure we have a string result
            if isinstance(current, dict):
                raise ValueError(
                    f"Path '{path}' points to a dictionary, not a string. "
                    f"Available keys: {list(current.keys())}"
                )
            
            # Format template if kwargs provided
            if format_kwargs:
                return current.format(**format_kwargs)
            else:
                return current
                
        except KeyError as e:
            raise KeyError(
                f"Translation path not found: '{path}' in {self.current_language.value}"
            )
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"Failed to format translation at '{path}': {e}"
            )

    def get_prompt(self, category: str, prompt_key: str, **format_kwargs) -> str:
        """
        Get a translated prompt for the current language.
        
        Args:
            category: Category of prompt (e.g., 'phase1_instructions', 'system_messages')
            prompt_key: Specific prompt key within category
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted prompt string
            
        Raises:
            KeyError: If category or prompt_key doesn't exist
            ValueError: If formatting fails
        """
        # Use the new dot notation API internally
        return self.get(f"{category}.{prompt_key}", **format_kwargs)
    
    def get_message(self, category: str, message_group: str, message_key: str, **format_kwargs) -> str:
        """
        Get a translated message from a message group (like error_messages).
        
        Args:
            category: Category containing the message group
            message_group: Group of messages (e.g., 'error_messages')  
            message_key: Specific message key within group
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted message string
        """
        # Use the new dot notation API internally
        return self.get(f"{category}.{message_group}.{message_key}", **format_kwargs)
    
    def get_experiment_explanation(self) -> str:
        """Get the main experiment explanation."""
        return self.get("prompts.experiment_explanation")
    
    def get_phase1_instructions(self, round_number: int) -> str:
        """
        Get Phase 1 instructions for a specific round.
        
        Args:
            round_number: Round number (0, -1, 1-4, 5)
            
        Returns:
            Translated instructions for the round
        """
        if round_number == 0:
            return self.get("prompts.phase1_round0_initial_ranking")
        elif round_number == -1:
            return self.get("prompts.phase1_round_neg1_detailed_explanation")  
        elif 1 <= round_number <= 4:
            return self.get("prompts.phase1_rounds1_4_principle_application", 
                          round_number=round_number)
        elif round_number == 5:
            return self.get("prompts.phase1_round5_final_ranking")
        else:
            return self.get("prompts.fallback_default_phase_instructions")
    
    def get_phase2_instructions(self, round_number: int) -> str:
        """
        Get Phase 2 instructions for group discussion.
        
        Args:
            round_number: Discussion round number
            
        Returns:
            Translated instructions for group discussion
        """
        return self.get("prompts.phase2_group_discussion", 
                       round_number=round_number)
    
    def get_parser_instructions(self) -> str:
        """Get utility agent parser instructions."""
        return self.get("prompts.utility_parser_instructions")
    
    def get_validator_instructions(self) -> str:
        """Get utility agent validator instructions."""
        return self.get("prompts.utility_validator_instructions")
    
    def get_principle_choice_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle choices."""
        return self.get("prompts.utility_parse_principle_choice", 
                       response=response)
    
    def get_principle_ranking_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle rankings."""
        return self.get("prompts.utility_parse_principle_ranking",
                       response=response)
    
    def get_vote_detection_prompt(self, statement: str) -> str:
        """Get prompt for detecting vote proposals."""
        return self.get("prompts.utility_vote_detection", 
                       statement=statement)
    
    def get_constraint_re_prompt(self, participant_name: str, principle_name: str, constraint_type: str) -> str:
        """Get re-prompt for missing constraint specification."""
        return self.get("prompts.utility_constraint_re_prompt",
                       participant_name=participant_name,
                       principle_name=principle_name, 
                       constraint_type=constraint_type)
    
    def get_format_improvement_prompt(self, response: str, parse_type: str) -> str:
        """Get format improvement prompt."""
        if parse_type == 'principle_choice':
            return self.get("prompts.utility_format_improvement_choice",
                           response=response)
        elif parse_type == 'principle_ranking':
            return self.get("prompts.utility_format_improvement_ranking", 
                           response=response)
        else:
            raise ValueError(f"Unknown parse_type: {parse_type}")
    
    def get_error_message(self, error_key: str, **format_kwargs) -> str:
        """Get a translated error message."""
        return self.get(f"prompts.system_error_messages_{error_key}", **format_kwargs)
    
    def get_success_message(self, success_key: str, **format_kwargs) -> str:
        """Get a translated success message."""
        return self.get(f"prompts.system_success_messages_{success_key}", **format_kwargs)
    
    def get_status_message(self, status_key: str, **format_kwargs) -> str:
        """Get a translated status message."""
        return self.get(f"prompts.system_status_messages_{status_key}", **format_kwargs)
    
    def get_justice_principle_name(self, principle_key: str) -> str:
        """Get translated name for a justice principle (for agent-facing content)."""
        return self.get(f"common.principle_names.{principle_key}")
    
    def get_justice_principle_name_english(self, principle_key: str) -> str:
        """Get English name for a justice principle (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get(f"common.principle_names.{principle_key}")
        finally:
            self.set_language(original_lang)
    
    def get_certainty_level_name(self, certainty_key: str) -> str:
        """Get translated name for a certainty level (for agent-facing content)."""
        return self.get(f"common.certainty_levels.{certainty_key}")
    
    def get_certainty_level_name_english(self, certainty_key: str) -> str:
        """Get English name for a certainty level (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get(f"common.certainty_levels.{certainty_key}")
        finally:
            self.set_language(original_lang)
    
    def get_phase_name(self, phase_key: str) -> str:
        """Get translated name for a phase."""
        return self.get(f"common.phase_names.{phase_key}")
    
    def format_context_info(self, name: str, role_description: str, bank_balance: float,
                           phase: str, round_number: int, formatted_memory: str,
                           personality: str, phase_instructions: str) -> str:
        """Format the main context information display."""
        experiment_explanation = self.get_experiment_explanation()
        
        return self.get("prompts.context_context_info_format",
                       name=name,
                       role_description=role_description, 
                       bank_balance=bank_balance,
                       phase=phase,
                       round_number=round_number,
                       formatted_memory=formatted_memory,
                       experiment_explanation=experiment_explanation,
                       personality=personality,
                       phase_instructions=phase_instructions)
    
    def format_memory_section(self, memory: str) -> str:
        """Format the memory section display."""
        if not memory or not memory.strip():
            memory = self.get("prompts.context_memory_empty_placeholder")
        
        return self.get("prompts.context_memory_section_format", 
                       memory=memory)


# Global instance for easy access
_global_language_manager: Optional[LanguageManager] = None


def get_language_manager() -> LanguageManager:
    """
    Get the global language manager instance.
    
    Returns:
        Global LanguageManager instance
    """
    global _global_language_manager
    if _global_language_manager is None:
        _global_language_manager = LanguageManager()
    return _global_language_manager


def set_global_language(language: SupportedLanguage) -> None:
    """
    Set the language for the global language manager.
    
    Args:
        language: Language to set globally
    """
    manager = get_language_manager()
    manager.set_language(language)


def get_english_principle_name(principle_key: str) -> str:
    """
    Get English principle name for system logging (always English).
    
    Args:
        principle_key: The principle key (e.g., "maximizing_floor")
        
    Returns:
        English principle name for logging
    """
    manager = get_language_manager()
    return manager.get_justice_principle_name_english(principle_key)


def get_english_certainty_name(certainty_key: str) -> str:
    """
    Get English certainty level name for system logging (always English).
    
    Args:
        certainty_key: The certainty key (e.g., "very_sure")
        
    Returns:
        English certainty name for logging
    """
    manager = get_language_manager()
    return manager.get_certainty_level_name_english(certainty_key)


def validate_translation_files(translations_dir: str = "translations") -> bool:
    """
    Validate that all required translation files exist and are valid.
    
    Args:
        translations_dir: Directory containing translation files
        
    Returns:
        True if all files are valid, False otherwise
    """
    manager = LanguageManager(translations_dir)
    
    try:
        for language in SupportedLanguage:
            logger.info(f"Validating {language.value} translations...")
            translations = manager.load_language(language)
            
            # Basic validation - check that required top-level sections exist
            required_sections = ["common", "prompts"]
            
            for section in required_sections:
                if section not in translations:
                    logger.error(f"Missing section '{section}' in {language.value}")
                    return False
            
            # Check common subsections
            common_subsections = ["principle_names", "income_classes", "certainty_levels"]
            for subsection in common_subsections:
                if subsection not in translations["common"]:
                    logger.error(f"Missing common.{subsection} in {language.value}")
                    return False
        
        logger.info("All translation files validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Translation validation failed: {e}")
        return False