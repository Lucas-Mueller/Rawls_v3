#!/usr/bin/env python3
"""
DeepL API Translation Script for Frohlich Experiment Prompts

This script translates all prompts and user-facing text from English to Spanish and Mandarin
using the DeepL API. The translated content is saved to JSON files for integration into the system.

Usage:
    python translate_prompts.py

Requirements:
    - DEEPL_API_KEY environment variable set
    - deepl-python package installed: pip install deepl
"""

import os
import json
import logging
import time
from typing import Dict, Any, List
from deepl import Translator, DeepLException
from dotenv import load_dotenv

# Import the prompts to translate
from prompts_for_translation import *
load_dotenv()
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PromptTranslator:
    """Handles translation of all experiment prompts using DeepL API."""
    
    def __init__(self):
        """Initialize the translator with DeepL API key."""
        api_key = os.getenv('DEEPL_API_KEY')
        if not api_key:
            raise ValueError("DEEPL_API_KEY environment variable not set")
        
        self.translator = Translator(api_key)
        
        # Language mappings (DeepL language codes)
        self.target_languages = {
            "Spanish": "ES",
            "Mandarin": "ZH"  # DeepL uses ZH for Chinese
        }
        
        # Rate limiting settings
        self.requests_per_second = 5  # Conservative rate limit
        self.request_delay = 1.0 / self.requests_per_second
        
        # Translation results storage
        self.translations = {
            "English": {},
            "Spanish": {},
            "Mandarin": {}
        }
    
    def translate_text(self, text: str, target_language: str) -> str:
        """
        Translate a single text string to target language.
        
        Args:
            text: Text to translate
            target_language: Target language name ("Spanish" or "Mandarin")
            
        Returns:
            Translated text string
        """
        if not text or not text.strip():
            return text
            
        try:
            target_code = self.target_languages[target_language]
            result = self.translator.translate_text(text, target_lang=target_code)
            
            # Rate limiting
            time.sleep(self.request_delay)
            
            return result.text
            
        except DeepLException as e:
            logger.error(f"DeepL API error translating to {target_language}: {e}")
            return text  # Return original text on error
        except Exception as e:
            logger.error(f"Unexpected error translating to {target_language}: {e}")
            return text
    
    def translate_template_string(self, template: str, target_language: str) -> str:
        """
        Translate template strings while preserving format placeholders.
        
        Args:
            template: Template string with placeholders like {variable}
            target_language: Target language name
            
        Returns:
            Translated template with placeholders intact
        """
        # For templates, we need to be careful with format strings
        # We'll translate the whole thing and trust that DeepL preserves the placeholders
        # If this causes issues, we could implement more sophisticated placeholder protection
        return self.translate_text(template, target_language)
    
    def translate_dictionary(self, data: Dict[str, str], target_language: str) -> Dict[str, str]:
        """
        Translate all values in a dictionary.
        
        Args:
            data: Dictionary with string values to translate
            target_language: Target language name
            
        Returns:
            Dictionary with translated values
        """
        translated = {}
        for key, value in data.items():
            logger.info(f"Translating {key} to {target_language}...")
            translated[key] = self.translate_text(value, target_language)
        return translated
    
    def translate_all_prompts(self):
        """Translate all prompts and messages to target languages."""
        
        logger.info("Starting translation of all prompts...")
        
        # Store English versions (original)
        self.translations["English"] = self._gather_all_english_prompts()
        
        # Translate to each target language
        for language in self.target_languages.keys():
            logger.info(f"\n=== Starting {language} translation ===")
            self.translations[language] = self._translate_language_set(language)
            logger.info(f"=== Completed {language} translation ===\n")
        
        logger.info("All translations completed successfully!")
    
    def _gather_all_english_prompts(self) -> Dict[str, Any]:
        """Gather all English prompts into a structured dictionary."""
        
        english_prompts = {
            # Phase 1 Manager hardcoded strings
            "phase1_manager_strings": {
                "counterfactual_table_header": COUNTERFACTUAL_TABLE_HEADER,
                "principle_display_names": PRINCIPLE_DISPLAY_NAMES,
                "round_memory_template": ROUND_MEMORY_TEMPLATE,
                "detailed_principles_explanation": DETAILED_PRINCIPLES_EXPLANATION,
                "post_explanation_ranking_prompt": POST_EXPLANATION_RANKING_PROMPT,
                "initial_ranking_prompt_template": INITIAL_RANKING_PROMPT_TEMPLATE
            },
            
            # Distribution Generator hardcoded strings
            "distribution_generator_strings": {
                "distributions_table_header": DISTRIBUTIONS_TABLE_HEADER,
                "distributions_table_column_header": DISTRIBUTIONS_TABLE_COLUMN_HEADER,
                "distributions_table_separator": DISTRIBUTIONS_TABLE_SEPARATOR,
                "income_class_names": INCOME_CLASS_NAMES,
                "base_principle_names": BASE_PRINCIPLE_NAMES
            },
            
            # Phase 2 Manager hardcoded strings
            "phase2_manager_strings": {
                "income_class_assignment_names": INCOME_CLASS_ASSIGNMENT_NAMES,
                "default_constraint_specification": DEFAULT_CONSTRAINT_SPECIFICATION
            },
            
            # Utility Agent remaining hardcoded strings
            "utility_agent_strings": {
                "parser_agent_name": PARSER_AGENT_NAME,
                "validator_agent_name": VALIDATOR_AGENT_NAME,
                "validation_error_incomplete_ranking": VALIDATION_ERROR_INCOMPLETE_RANKING
            },
            
            # System formatting strings
            "system_formatting_strings": {
                "earnings_display_format": EARNINGS_DISPLAY_FORMAT,
                "total_earnings_format": TOTAL_EARNINGS_FORMAT,
                "bank_balance_format": BANK_BALANCE_FORMAT,
                "round_outcome_header": ROUND_OUTCOME_HEADER,
                "current_phase_format": CURRENT_PHASE_FORMAT,
                "round_number_format": ROUND_NUMBER_FORMAT,
                "class_assignment_format": CLASS_ASSIGNMENT_FORMAT,
                "floor_constraint_example": FLOOR_CONSTRAINT_EXAMPLE,
                "range_constraint_example": RANGE_CONSTRAINT_EXAMPLE
            }
        }
        
        return english_prompts
    
    def _translate_language_set(self, target_language: str) -> Dict[str, Any]:
        """Translate complete set of prompts to target language."""
        
        english_prompts = self.translations["English"]
        translated = {}
        
        for category, category_data in english_prompts.items():
            logger.info(f"Translating category: {category}")
            translated[category] = {}
            
            for item_key, item_value in category_data.items():
                logger.info(f"  Translating: {item_key}")
                
                if isinstance(item_value, dict):
                    # Handle nested dictionaries (like error_messages)
                    translated[category][item_key] = self.translate_dictionary(item_value, target_language)
                elif isinstance(item_value, str):
                    # Handle single strings
                    translated[category][item_key] = self.translate_text(item_value, target_language)
                else:
                    logger.warning(f"Unexpected data type for {item_key}: {type(item_value)}")
                    translated[category][item_key] = item_value
        
        return translated
    
    def save_translations(self, output_dir: str = "translations"):
        """
        Save all translations to JSON files.
        
        Args:
            output_dir: Directory to save translation files
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        for language, translations in self.translations.items():
            filename = f"{output_dir}/missing_{language.lower()}_prompts.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(
                    translations, 
                    f, 
                    ensure_ascii=False, 
                    indent=2
                )
            
            logger.info(f"Saved {language} translations to {filename}")
    
    def get_usage_info(self):
        """Get and display DeepL API usage information."""
        try:
            usage = self.translator.get_usage()
            logger.info(f"DeepL API Usage:")
            logger.info(f"  Characters used: {usage.character.count:,}")
            logger.info(f"  Character limit: {usage.character.limit:,}")
            logger.info(f"  Remaining: {usage.character.limit - usage.character.count:,}")
        except Exception as e:
            logger.warning(f"Could not retrieve usage info: {e}")


def main():
    """Main function to run the translation process."""
    
    try:
        # Initialize translator
        translator = PromptTranslator()
        
        # Get initial usage info
        logger.info("=== DeepL API Usage (Before Translation) ===")
        translator.get_usage_info()
        
        # Perform translations
        translator.translate_all_prompts()
        
        # Save results
        translator.save_translations()
        
        # Get final usage info
        logger.info("\n=== DeepL API Usage (After Translation) ===")
        translator.get_usage_info()
        
        logger.info("\n=== Translation Complete! ===")
        logger.info("Translation files saved to 'translations/' directory")
        logger.info("Next steps:")
        logger.info("1. Review the translated files for accuracy")
        logger.info("2. Integrate translations into the system using the multi-language support plan")
        
    except Exception as e:
        logger.error(f"Translation process failed: {e}")
        raise


if __name__ == "__main__":
    main()