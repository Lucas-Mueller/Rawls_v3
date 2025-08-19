"""
Translation validation tests to ensure consistency across all supported languages.
"""
import unittest
import json
import os
from pathlib import Path
from utils.language_manager import SupportedLanguage, LanguageManager


class TestTranslationValidation(unittest.TestCase):
    """Test suite for validating translation consistency and completeness."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.language_manager = LanguageManager()
        self.project_root = Path(__file__).parent.parent.parent
        self.translations_dir = self.project_root / "translations"
        
        # Load all translation files
        self.translations = {}
        for language in SupportedLanguage:
            try:
                self.translations[language] = self.language_manager.load_language(language)
            except FileNotFoundError:
                self.fail(f"Translation file missing for {language.value}")
    
    def test_principle_names_consistency(self):
        """Test that all principle names are correctly translated across languages."""
        expected_principles = {
            "maximizing_floor",
            "maximizing_average", 
            "maximizing_average_floor_constraint",
            "maximizing_average_range_constraint"
        }
        
        # Check that all languages have all principle names
        for language, translations in self.translations.items():
            with self.subTest(language=language.value):
                principle_names = translations["common"]["principle_names"]
                
                # Check all expected principles are present
                self.assertEqual(
                    set(principle_names.keys()), 
                    expected_principles,
                    f"Missing or extra principle names in {language.value}"
                )
                
                # Check for critical translation errors
                if language == SupportedLanguage.MANDARIN:
                    # Verify the critical fixes
                    self.assertEqual(
                        principle_names["maximizing_floor"],
                        "最大化最低收入",
                        "Mandarin translation for maximizing_floor is incorrect"
                    )
                    self.assertEqual(
                        principle_names["maximizing_average"],
                        "最大化平均收入", 
                        "Mandarin translation for maximizing_average is incorrect"
                    )
                    self.assertEqual(
                        principle_names["maximizing_average_floor_constraint"],
                        "在最低收入约束条件下最大化平均收入",
                        "Mandarin translation for maximizing_average_floor_constraint is incorrect"
                    )
                    self.assertEqual(
                        principle_names["maximizing_average_range_constraint"],
                        "在范围约束条件下最大化平均收入",
                        "Mandarin translation for maximizing_average_range_constraint is incorrect"
                    )
                
                elif language == SupportedLanguage.SPANISH:
                    # Verify Spanish translations are correct
                    self.assertEqual(
                        principle_names["maximizing_floor"],
                        "Maximizar el ingreso mínimo",
                        "Spanish translation for maximizing_floor is incorrect"
                    )
                    self.assertEqual(
                        principle_names["maximizing_average"],
                        "Maximizar el ingreso promedio",
                        "Spanish translation for maximizing_average is incorrect"
                    )
                
                # Ensure no translations contain literal "floor" or "suelo" errors (except English)
                if language != SupportedLanguage.ENGLISH:
                    for principle_key, principle_translation in principle_names.items():
                        if "floor" in principle_key:
                            # Should not contain literal floor translations in non-English languages
                            if language == SupportedLanguage.MANDARIN:
                                forbidden_terms = ["地板"]  # literal floor in Chinese
                            elif language == SupportedLanguage.SPANISH:
                                forbidden_terms = ["suelo"]  # literal floor in Spanish
                            else:
                                forbidden_terms = []
                            
                            for forbidden in forbidden_terms:
                                self.assertNotIn(
                                    forbidden.lower(),
                                    principle_translation.lower(),
                                    f"Translation for {principle_key} in {language.value} contains literal floor reference: '{principle_translation}'"
                                )
    
    def test_translation_completeness(self):
        """Test that all required translation keys are present in all languages."""
        # Get all keys from English as the reference
        english_translations = self.translations[SupportedLanguage.ENGLISH]
        
        def get_all_keys(d, prefix=""):
            """Recursively get all keys from nested dictionary."""
            keys = set()
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                if isinstance(value, dict):
                    keys.update(get_all_keys(value, full_key))
            return keys
        
        english_keys = get_all_keys(english_translations)
        
        # Check that all other languages have the same keys
        for language in [SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]:
            with self.subTest(language=language.value):
                language_keys = get_all_keys(self.translations[language])
                
                missing_keys = english_keys - language_keys
                extra_keys = language_keys - english_keys
                
                self.assertEqual(
                    len(missing_keys), 0,
                    f"Missing keys in {language.value}: {missing_keys}"
                )
                self.assertEqual(
                    len(extra_keys), 0,
                    f"Extra keys in {language.value}: {extra_keys}"
                )
    
    def test_no_empty_translations(self):
        """Test that no translations are empty strings."""
        for language, translations in self.translations.items():
            with self.subTest(language=language.value):
                self._check_no_empty_values(translations, language.value)
    
    def _check_no_empty_values(self, obj, language_name, path=""):
        """Recursively check that no values are empty strings."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                self._check_no_empty_values(value, language_name, current_path)
        elif isinstance(obj, str):
            self.assertNotEqual(
                obj.strip(), "",
                f"Empty translation found in {language_name} at path: {path}"
            )
    
    def test_principle_consistency_in_prompts(self):
        """Test that principle names are used consistently within prompt texts."""
        for language, translations in self.translations.items():
            with self.subTest(language=language.value):
                principle_names = translations["common"]["principle_names"]
                
                # Check key prompts for consistency
                ranking_prompt = translations["prompts"]["phase1_round0_initial_ranking"]
                application_prompt = translations["prompts"]["phase1_rounds1_4_principle_application"]
                
                # Verify that the principle names from common section match those used in prompts
                if language == SupportedLanguage.MANDARIN:
                    # Check that ranking prompt uses correct principle names
                    self.assertIn("最大化最低收入", ranking_prompt)
                    self.assertIn("最大化平均收入", ranking_prompt)
                    self.assertIn("在最低收入约束条件下最大化平均收入", ranking_prompt)
                    self.assertIn("在范围约束条件下最大化平均收入", ranking_prompt)
                    
                    # Should not contain old incorrect translations
                    self.assertNotIn("最大限度地利用地板", ranking_prompt)
                    self.assertNotIn("最大化平均值", ranking_prompt)


if __name__ == '__main__':
    unittest.main()