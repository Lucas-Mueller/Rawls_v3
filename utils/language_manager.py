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
        try:
            translations = self.get_current_translations()
            prompt_template = translations[category][prompt_key]
            
            # Handle nested dictionaries (like error_messages)
            if isinstance(prompt_template, dict):
                raise ValueError(
                    f"Expected string prompt but got dictionary for {category}.{prompt_key}. "
                    f"Use get_message() for dictionary-type prompts."
                )
            
            # Format template if kwargs provided
            if format_kwargs:
                return prompt_template.format(**format_kwargs)
            else:
                return prompt_template
                
        except KeyError as e:
            raise KeyError(
                f"Prompt not found: {category}.{prompt_key} in {self.current_language.value}. "
                f"Available categories: {list(translations.keys())}"
            )
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"Failed to format prompt {category}.{prompt_key}: {e}"
            )
    
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
        try:
            translations = self.get_current_translations()
            message_template = translations[category][message_group][message_key]
            
            # Format template if kwargs provided
            if format_kwargs:
                return message_template.format(**format_kwargs)
            else:
                return message_template
                
        except KeyError as e:
            raise KeyError(
                f"Message not found: {category}.{message_group}.{message_key} "
                f"in {self.current_language.value}"
            )
    
    def get_experiment_explanation(self) -> str:
        """Get the main experiment explanation."""
        return self.get_prompt("experiment_explanation", "broad_experiment_explanation")
    
    def get_phase1_instructions(self, round_number: int) -> str:
        """
        Get Phase 1 instructions for a specific round.
        
        Args:
            round_number: Round number (0, -1, 1-4, 5)
            
        Returns:
            Translated instructions for the round
        """
        if round_number == 0:
            return self.get_prompt("phase1_instructions", "round0_initial_ranking")
        elif round_number == -1:
            return self.get_prompt("phase1_instructions", "round_neg1_detailed_explanation")  
        elif 1 <= round_number <= 4:
            return self.get_prompt("phase1_instructions", "rounds1_4_principle_application", 
                                 round_number=round_number)
        elif round_number == 5:
            return self.get_prompt("phase1_instructions", "round5_final_ranking")
        else:
            return self.get_prompt("fallback", "default_phase_instructions")
    
    def get_phase2_instructions(self, round_number: int) -> str:
        """
        Get Phase 2 instructions for group discussion.
        
        Args:
            round_number: Discussion round number
            
        Returns:
            Translated instructions for group discussion
        """
        return self.get_prompt("phase2_instructions", "group_discussion", 
                             round_number=round_number)
    
    def get_parser_instructions(self) -> str:
        """Get utility agent parser instructions."""
        return self.get_prompt("utility_agent_prompts", "parser_instructions")
    
    def get_validator_instructions(self) -> str:
        """Get utility agent validator instructions."""
        return self.get_prompt("utility_agent_prompts", "validator_instructions")
    
    def get_principle_choice_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle choices."""
        return self.get_prompt("utility_agent_prompts", "parse_principle_choice", 
                             response=response)
    
    def get_principle_ranking_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle rankings."""
        return self.get_prompt("utility_agent_prompts", "parse_principle_ranking",
                             response=response)
    
    def get_vote_detection_prompt(self, statement: str) -> str:
        """Get prompt for detecting vote proposals."""
        return self.get_prompt("utility_agent_prompts", "vote_detection", 
                             statement=statement)
    
    def get_constraint_re_prompt(self, participant_name: str, principle_name: str, constraint_type: str) -> str:
        """Get re-prompt for missing constraint specification."""
        return self.get_prompt("utility_agent_prompts", "constraint_re_prompt",
                             participant_name=participant_name,
                             principle_name=principle_name, 
                             constraint_type=constraint_type)
    
    def get_format_improvement_prompt(self, response: str, parse_type: str) -> str:
        """Get format improvement prompt."""
        if parse_type == 'principle_choice':
            return self.get_prompt("utility_agent_prompts", "format_improvement_choice",
                                 response=response)
        elif parse_type == 'principle_ranking':
            return self.get_prompt("utility_agent_prompts", "format_improvement_ranking", 
                                 response=response)
        else:
            raise ValueError(f"Unknown parse_type: {parse_type}")
    
    def get_error_message(self, error_key: str, **format_kwargs) -> str:
        """Get a translated error message."""
        return self.get_message("system_messages", "error_messages", error_key, **format_kwargs)
    
    def get_success_message(self, success_key: str, **format_kwargs) -> str:
        """Get a translated success message."""
        return self.get_message("system_messages", "success_messages", success_key, **format_kwargs)
    
    def get_status_message(self, status_key: str, **format_kwargs) -> str:
        """Get a translated status message."""
        return self.get_message("system_messages", "status_messages", status_key, **format_kwargs)
    
    def get_justice_principle_name(self, principle_key: str) -> str:
        """Get translated name for a justice principle (for agent-facing content)."""
        return self.get_message("names_and_labels", "justice_principle_names", principle_key)
    
    def get_justice_principle_name_english(self, principle_key: str) -> str:
        """Get English name for a justice principle (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get_message("names_and_labels", "justice_principle_names", principle_key)
        finally:
            self.set_language(original_lang)
    
    def get_certainty_level_name(self, certainty_key: str) -> str:
        """Get translated name for a certainty level (for agent-facing content)."""
        return self.get_message("names_and_labels", "certainty_level_names", certainty_key)
    
    def get_certainty_level_name_english(self, certainty_key: str) -> str:
        """Get English name for a certainty level (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get_message("names_and_labels", "certainty_level_names", certainty_key)
        finally:
            self.set_language(original_lang)
    
    def get_phase_name(self, phase_key: str) -> str:
        """Get translated name for a phase."""
        return self.get_message("names_and_labels", "phase_names", phase_key)
    
    def format_context_info(self, name: str, role_description: str, bank_balance: float,
                           phase: str, round_number: int, formatted_memory: str,
                           personality: str, phase_instructions: str) -> str:
        """Format the main context information display."""
        experiment_explanation = self.get_experiment_explanation()
        
        return self.get_prompt("context_formatting", "context_info_format",
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
            memory = self.get_prompt("context_formatting", "memory_empty_placeholder")
        
        return self.get_prompt("context_formatting", "memory_section_format", 
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
            
            # Basic validation - check that required categories exist
            required_categories = [
                "experiment_explanation",
                "phase1_instructions", 
                "phase2_instructions",
                "utility_agent_prompts",
                "system_messages",
                "context_formatting",
                "names_and_labels"
            ]
            
            for category in required_categories:
                if category not in translations:
                    logger.error(f"Missing category '{category}' in {language.value}")
                    return False
        
        logger.info("All translation files validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Translation validation failed: {e}")
        return False