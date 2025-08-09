"""
Unit tests for the language manager system.
"""

import unittest
import os
import tempfile
import json
from pathlib import Path

from utils.language_manager import (
    LanguageManager, SupportedLanguage, get_language_manager, 
    set_global_language, validate_translation_files
)


class TestLanguageManager(unittest.TestCase):
    """Test cases for the LanguageManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test translation files
        self.test_dir = tempfile.mkdtemp()
        self.manager = LanguageManager(translations_dir=self.test_dir)
        
        # Create complete test translation data with new flattened structure
        self.test_translations = {
            "common": {
                "principle_names": {
                    "maximizing_floor": "Test maximizing floor",
                    "maximizing_average": "Test maximizing average"
                },
                "income_classes": {
                    "high": "Test high",
                    "medium_high": "Test medium high",
                    "medium": "Test medium",
                    "medium_low": "Test medium low",
                    "low": "Test low"
                },
                "certainty_levels": {
                    "sure": "Test sure",
                    "very_sure": "Test very sure"
                }
            },
            "prompts": {
                "experiment_explanation": "Test experiment explanation",
                "phase1_round0_initial_ranking": "Test initial ranking instructions",
                "phase1_round_neg1_detailed_explanation": "Test detailed explanation",
                "phase1_rounds1_4_principle_application": "Test principle application",
                "phase1_round5_final_ranking": "Test final ranking",
                "phase2_group_discussion": "Test group discussion instructions",
                "utility_parser_instructions": "Test parser instructions",
                "utility_validator_instructions": "Test validator instructions",
                "utility_parse_principle_choice": "Test parse choice prompt",
                "utility_parse_principle_ranking": "Test parse ranking prompt",
                "utility_vote_detection": "Test vote detection prompt",
                "utility_constraint_re_prompt": "Test constraint re-prompt",
                "utility_format_improvement_choice": "Test format improvement choice",
                "utility_format_improvement_ranking": "Test format improvement ranking",
                "system_error_messages_memory_limit_exceeded": "Test memory limit error",
                "system_success_messages_choice_accepted": "Test choice accepted",
                "system_status_messages_phase1_starting": "Test phase 1 starting",
                "context_memory_section_format": "Test memory format",
                "context_memory_empty_placeholder": "Test empty placeholder",
                "context_context_info_format": "Test context format",
                "fallback_default_phase_instructions": "Test default instructions"
            }
        }
        
        # Create test translation files
        for language in SupportedLanguage:
            filename = f"{language.value.lower()}_prompts.json"
            filepath = os.path.join(self.test_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.test_translations, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_language_switching(self):
        """Test that language switching works correctly."""
        # Test default language
        self.assertEqual(self.manager.current_language, SupportedLanguage.ENGLISH)
        
        # Test switching to Spanish
        self.manager.set_language(SupportedLanguage.SPANISH)
        self.assertEqual(self.manager.current_language, SupportedLanguage.SPANISH)
        
        # Test switching to Mandarin
        self.manager.set_language(SupportedLanguage.MANDARIN)
        self.assertEqual(self.manager.current_language, SupportedLanguage.MANDARIN)
        
        # Test invalid language raises error
        with self.assertRaises(ValueError):
            self.manager.set_language("InvalidLanguage")
    
    def test_translation_loading(self):
        """Test that translation files can be loaded correctly."""
        for language in SupportedLanguage:
            translations = self.manager.load_language(language)
            self.assertIsInstance(translations, dict)
            self.assertIn("common", translations)
            self.assertIn("prompts", translations)
    
    def test_prompt_retrieval(self):
        """Test that prompts can be retrieved correctly."""
        # Test old API (still supported)
        explanation = self.manager.get_prompt("prompts", "experiment_explanation")
        self.assertEqual(explanation, "Test experiment explanation")
        
        # Test new API
        explanation_new = self.manager.get("prompts.experiment_explanation")
        self.assertEqual(explanation_new, "Test experiment explanation")
        
        # Test common section
        principle = self.manager.get("common.principle_names.maximizing_floor")
        self.assertEqual(principle, "Test maximizing floor")
    
    def test_prompt_formatting(self):
        """Test that prompts with format strings work correctly."""
        # For this test we need a prompt with format placeholders
        test_translations_with_format = self.test_translations.copy()
        test_translations_with_format["prompts"]["formatted_prompt"] = "Hello {name}, your score is {score}"
        
        # Update test files with formatted prompt
        for language in SupportedLanguage:
            filename = f"{language.value.lower()}_prompts.json"
            filepath = os.path.join(self.test_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(test_translations_with_format, f, ensure_ascii=False, indent=2)
        
        # Clear cache to force reload
        self.manager.translations_cache.clear()
        
        # Test formatted prompt with old API
        formatted = self.manager.get_prompt("prompts", "formatted_prompt", 
                                          name="Alice", score=95)
        self.assertEqual(formatted, "Hello Alice, your score is 95")
        
        # Test formatted prompt with new API
        formatted_new = self.manager.get("prompts.formatted_prompt", name="Alice", score=95)
        self.assertEqual(formatted_new, "Hello Alice, your score is 95")
    
    def test_message_retrieval(self):
        """Test that nested messages can be retrieved correctly."""
        # The old get_message API doesn't work the same way anymore since we flattened the structure
        # Just test the new API
        error_msg = self.manager.get("prompts.system_error_messages_memory_limit_exceeded")
        self.assertEqual(error_msg, "Test memory limit error")
    
    def test_convenience_methods(self):
        """Test convenience methods work correctly."""
        # Test experiment explanation
        explanation = self.manager.get_experiment_explanation()
        self.assertEqual(explanation, "Test experiment explanation")
        
        # Test phase1 instructions
        instructions = self.manager.get_phase1_instructions(0)
        self.assertEqual(instructions, "Test initial ranking instructions")
        
        # Test error message
        error = self.manager.get_error_message("memory_limit_exceeded")
        self.assertEqual(error, "Test memory limit error")
        
        # Test justice principle name
        principle_name = self.manager.get_justice_principle_name("maximizing_floor")
        self.assertEqual(principle_name, "Test maximizing floor")
    
    def test_missing_translation_handling(self):
        """Test behavior when translation files are missing."""
        # Create manager pointing to non-existent directory
        bad_manager = LanguageManager(translations_dir="/nonexistent/path")
        
        # Should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            bad_manager.load_language(SupportedLanguage.ENGLISH)
    
    def test_global_language_manager(self):
        """Test global language manager functionality."""
        # Get global manager
        global_manager = get_language_manager()
        self.assertIsInstance(global_manager, LanguageManager)
        
        # Test setting global language
        original_lang = global_manager.current_language
        try:
            set_global_language(SupportedLanguage.SPANISH)
            self.assertEqual(global_manager.current_language, SupportedLanguage.SPANISH)
        finally:
            # Reset to original language
            global_manager.set_language(original_lang)
    
    def test_translation_file_validation(self):
        """Test translation file validation."""
        # Should pass with our complete test files
        is_valid = validate_translation_files(self.test_dir)
        self.assertTrue(is_valid)
        
        # Test with missing files
        bad_dir = tempfile.mkdtemp()
        try:
            is_valid = validate_translation_files(bad_dir)
            self.assertFalse(is_valid)
        finally:
            import shutil
            shutil.rmtree(bad_dir, ignore_errors=True)


class TestLanguageManagerIntegration(unittest.TestCase):
    """Integration tests for language manager with other components."""
    
    def test_configuration_integration(self):
        """Test that language manager integrates with configuration system."""
        from config.models import ExperimentConfiguration
        from utils.language_manager import SupportedLanguage
        
        # Test valid language configuration
        config_data = {
            "language": "Spanish",
            "agents": [
                {"name": "Alice", "personality": "Test personality"},
                {"name": "Bob", "personality": "Test personality"}
            ]
        }
        
        config = ExperimentConfiguration(**config_data)
        self.assertEqual(config.language, "Spanish")
        
        # Test that it can be converted to SupportedLanguage
        language_enum = SupportedLanguage(config.language)
        self.assertEqual(language_enum, SupportedLanguage.SPANISH)
    
    def test_invalid_language_configuration(self):
        """Test handling of invalid language in configuration."""
        from config.models import ExperimentConfiguration
        
        config_data = {
            "language": "InvalidLanguage",
            "agents": [
                {"name": "Alice", "personality": "Test personality"},
                {"name": "Bob", "personality": "Test personality"}
            ]
        }
        
        # Should raise validation error
        with self.assertRaises(ValueError):
            ExperimentConfiguration(**config_data)


if __name__ == '__main__':
    unittest.main()