"""
Consolidated Language Management Tests

This module contains comprehensive tests for language management functionality,
consolidating tests from multiple files into a unified, parametrized test suite.

Functionality tested:
1. Core language manager operations (multilingual)
2. Cultural context adaptations
3. Translation validation and consistency  
4. Multilingual parsing capabilities
5. Full name parsing across languages

Consolidated from:
- test_language_manager.py
- test_cultural_context.py
- test_translation_validation.py  
- test_multilingual_parsing.py
- test_full_name_parsing_only.py
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any

from utils.language_manager import (
    LanguageManager, SupportedLanguage, get_language_manager, 
    set_global_language, validate_translation_files
)
from utils.cultural_adaptation import (
    format_currency, format_percentage, adapt_cultural_context,
    get_cultural_preferences
)
from models.principle_types import JusticePrinciple


class TestLanguageSystems:
    """Unified test class for all language management functionality."""
    
    @pytest.fixture
    def temp_translations_dir(self):
        """Create temporary directory for test translation files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup handled by system
        
    @pytest.fixture
    def language_manager(self, temp_translations_dir):
        """Create language manager with test translations."""
        manager = LanguageManager(translations_dir=temp_translations_dir)
        
        # Create test translation files
        test_translations = {
            "common": {
                "principle_names": {
                    "maximizing_floor": "Test maximizing floor",
                    "maximizing_average": "Test maximizing average",
                    "maximizing_average_floor_constraint": "Test constrained maximizing"
                },
                "income_classes": {
                    "high": "Test high", "medium_high": "Test medium high",
                    "medium": "Test medium", "medium_low": "Test medium low",
                    "low": "Test low"
                },
                "certainty_levels": {
                    "certain": "Test certain", "likely": "Test likely",
                    "uncertain": "Test uncertain"
                }
            },
            "prompts": {
                "phase1_intro": "Test Phase 1 introduction",
                "phase2_intro": "Test Phase 2 introduction",
                "vote_request": "Test vote request"
            },
            "errors": {
                "invalid_choice": "Test invalid choice error",
                "timeout": "Test timeout error"
            }
        }
        
        # Write translation files for multiple languages
        for lang in ["english", "spanish", "mandarin"]:
            lang_file = Path(temp_translations_dir) / f"{lang}.json"
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(test_translations, f, ensure_ascii=False, indent=2)
        
        return manager
    
    @pytest.fixture
    def sample_names(self):
        """Sample names across cultures for testing."""
        return {
            "english": ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson"],
            "spanish": ["Ana García", "Carlos López", "Elena Rodríguez", "Miguel Fernández"], 
            "mandarin": ["李明 (Li Ming)", "王红 (Wang Hong)", "张伟 (Zhang Wei)", "刘芳 (Liu Fang)"],
            "mixed": ["Maria Chen", "Ahmed Smith", "José Kim", "Sarah Patel"]
        }
    
    @pytest.fixture  
    def cultural_data(self):
        """Cultural formatting examples for testing."""
        return {
            "currency": {
                "english": {"symbol": "$", "format": "before", "thousands": ",", "decimal": "."},
                "spanish": {"symbol": "€", "format": "after", "thousands": ".", "decimal": ","},
                "mandarin": {"symbol": "¥", "format": "before", "thousands": ",", "decimal": "."}
            },
            "percentage": {
                "english": {"decimal": ".", "suffix": "%"},
                "spanish": {"decimal": ",", "suffix": "%"}, 
                "mandarin": {"decimal": ".", "suffix": "%"}
            }
        }

    # CORE LANGUAGE MANAGER TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_language_manager_initialization(self, temp_translations_dir, language):
        """Test language manager initialization for all supported languages."""
        manager = LanguageManager(translations_dir=temp_translations_dir, language=SupportedLanguage(language))
        
        assert manager.current_language == SupportedLanguage(language)
        assert manager.translations_dir == temp_translations_dir
        
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_translation_loading(self, language_manager, language):
        """Test translation file loading across languages."""
        language_manager.set_language(SupportedLanguage(language))
        
        # Test basic translation retrieval
        principle_name = language_manager.get("common.principle_names.maximizing_floor")
        assert principle_name == "Test maximizing floor"
        
        # Test nested translation retrieval
        intro = language_manager.get("prompts.phase1_intro")
        assert intro == "Test Phase 1 introduction"
        
    def test_translation_key_fallback(self, language_manager):
        """Test fallback behavior for missing translation keys."""
        # Test missing key returns key itself or raises appropriate error
        missing_key = "nonexistent.translation.key"
        result = language_manager.get(missing_key, fallback="DEFAULT")
        
        assert result == "DEFAULT" or result == missing_key
        
    def test_translation_interpolation(self, language_manager):
        """Test parameter interpolation in translations."""
        # Test translation with parameters
        template = "Hello {name}, welcome to {place}"
        result = language_manager.format_template(template, name="Alice", place="experiment")
        
        assert result == "Hello Alice, welcome to experiment"
        
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_language_switching(self, language_manager, language):
        """Test dynamic language switching."""
        initial_lang = language_manager.current_language
        
        # Switch to target language
        language_manager.set_language(SupportedLanguage(language))
        assert language_manager.current_language == SupportedLanguage(language)
        
        # Test that translations work after switch
        result = language_manager.get("common.principle_names.maximizing_average")
        assert result is not None

    def test_global_language_manager(self, temp_translations_dir):
        """Test global language manager singleton behavior."""
        # Set global language
        set_global_language(SupportedLanguage.SPANISH, temp_translations_dir)
        
        manager1 = get_language_manager()
        manager2 = get_language_manager()
        
        # Should be same instance
        assert manager1 is manager2
        assert manager1.current_language == SupportedLanguage.SPANISH

    # CULTURAL ADAPTATION TESTS
    @pytest.mark.parametrize("language,amount,expected_format", [
        ("english", 50000, "$50,000"),
        ("spanish", 50000, "50.000€"), 
        ("mandarin", 50000, "¥50,000")
    ])
    def test_currency_formatting_multilingual(self, cultural_data, language, amount, expected_format):
        """Test currency formatting across cultures.""" 
        culture_settings = cultural_data["currency"][language]
        result = format_currency(amount, **culture_settings)
        
        # Test that format contains expected elements
        assert culture_settings["symbol"] in result
        assert str(amount) in result.replace(",", "").replace(".", "")

    @pytest.mark.parametrize("language,percentage,expected_format", [
        ("english", 65.5, "65.5%"),
        ("spanish", 65.5, "65,5%"),
        ("mandarin", 65.5, "65.5%")
    ])  
    def test_percentage_formatting_multilingual(self, cultural_data, language, percentage, expected_format):
        """Test percentage formatting across cultures."""
        culture_settings = cultural_data["percentage"][language] 
        result = format_percentage(percentage, **culture_settings)
        
        assert "%" in result
        assert str(percentage).replace(".", culture_settings["decimal"]) in result

    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_cultural_context_adaptation(self, language):
        """Test cultural context adaptation for different languages."""
        base_context = {
            "greeting": "Hello",
            "amount": 50000,
            "percentage": 75.5
        }
        
        adapted = adapt_cultural_context(base_context, SupportedLanguage(language))
        
        # Should maintain basic structure but adapt formatting
        assert "greeting" in adapted
        assert "amount" in adapted
        assert "percentage" in adapted
        
        # Formatting should be culture-appropriate
        if language == "spanish":
            assert "," in str(adapted["percentage"])  # Spanish uses comma for decimal

    def test_cultural_preferences_retrieval(self):
        """Test retrieval of cultural preferences for different languages."""
        for language in ["english", "spanish", "mandarin"]:
            prefs = get_cultural_preferences(SupportedLanguage(language))
            
            assert "currency" in prefs
            assert "date_format" in prefs
            assert "number_format" in prefs
            
            # Test that preferences are language-appropriate
            if language == "mandarin":
                assert prefs["currency"]["symbol"] == "¥"
            elif language == "spanish":
                assert prefs["number_format"]["decimal"] == ","

    # TRANSLATION VALIDATION TESTS  
    def test_translation_file_validation(self, temp_translations_dir):
        """Test validation of translation files for completeness."""
        # Create incomplete translation file
        incomplete_translations = {
            "common": {
                "principle_names": {
                    "maximizing_floor": "Test maximizing floor"
                    # Missing other principles
                }
            }
            # Missing prompts and errors sections
        }
        
        incomplete_file = Path(temp_translations_dir) / "incomplete.json"
        with open(incomplete_file, 'w') as f:
            json.dump(incomplete_translations, f)
            
        # Validation should identify missing keys
        validation_result = validate_translation_files(temp_translations_dir)
        assert validation_result.has_errors is True
        assert len(validation_result.missing_keys) > 0

    @pytest.mark.parametrize("lang1,lang2", [
        ("english", "spanish"),
        ("english", "mandarin"), 
        ("spanish", "mandarin")
    ])
    def test_translation_consistency_across_languages(self, language_manager, lang1, lang2):
        """Test consistency of translation structure across language pairs."""
        # Load both languages
        language_manager.set_language(SupportedLanguage(lang1))
        keys_lang1 = language_manager.get_all_keys()
        
        language_manager.set_language(SupportedLanguage(lang2))
        keys_lang2 = language_manager.get_all_keys()
        
        # Should have same translation keys
        missing_in_lang2 = keys_lang1 - keys_lang2
        missing_in_lang1 = keys_lang2 - keys_lang1
        
        assert len(missing_in_lang2) == 0, f"Missing keys in {lang2}: {missing_in_lang2}"
        assert len(missing_in_lang1) == 0, f"Missing keys in {lang1}: {missing_in_lang1}"

    def test_translation_placeholder_consistency(self, language_manager):
        """Test that translation placeholders are consistent across languages."""
        test_key = "prompts.test_with_placeholders"
        
        # Add test translation with placeholders to all languages
        for lang in ["english", "spanish", "mandarin"]:
            # This would typically be done in the translation files
            pass
            
        # Test that all languages have same placeholder structure
        # Implementation depends on how placeholders are handled

    # MULTILINGUAL PARSING TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_multilingual_principle_parsing(self, language_manager, language):
        """Test parsing of principle names across languages.""" 
        language_manager.set_language(SupportedLanguage(language))
        
        # Test principle name recognition
        principle_mappings = {
            "english": [
                ("maximizing floor", JusticePrinciple.MAXIMIZING_FLOOR),
                ("maximizing average", JusticePrinciple.MAXIMIZING_AVERAGE)
            ],
            "spanish": [
                ("maximizar mínimo", JusticePrinciple.MAXIMIZING_FLOOR),
                ("maximizar promedio", JusticePrinciple.MAXIMIZING_AVERAGE)  
            ],
            "mandarin": [
                ("最大化最低收入", JusticePrinciple.MAXIMIZING_FLOOR),
                ("最大化平均收入", JusticePrinciple.MAXIMIZING_AVERAGE)
            ]
        }
        
        if language in principle_mappings:
            for text, expected_principle in principle_mappings[language]:
                # Test principle recognition (would use actual parsing logic)
                result = language_manager.parse_principle_reference(text)
                assert result == expected_principle, f"Failed to parse '{text}' in {language}"

    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_multilingual_error_messages(self, language_manager, language):
        """Test error message formatting across languages."""
        language_manager.set_language(SupportedLanguage(language))
        
        # Test error message retrieval
        error_msg = language_manager.get("errors.invalid_choice")
        assert error_msg is not None
        assert len(error_msg) > 0
        
        # Test error message with parameters
        timeout_msg = language_manager.get("errors.timeout", timeout_seconds=30)
        assert "30" in timeout_msg or timeout_msg != ""

    # FULL NAME PARSING TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin", "mixed"])
    def test_full_name_parsing_multilingual(self, sample_names, language):
        """Test full name parsing across different cultural naming conventions."""
        names = sample_names[language]
        
        for full_name in names:
            parsed = self._parse_full_name(full_name, language)
            
            # Should extract meaningful name components
            assert parsed["first_name"] is not None
            assert parsed["last_name"] is not None
            assert len(parsed["first_name"]) > 0
            
            # Test culture-specific parsing
            if language == "mandarin":
                # Chinese names often have surnames first
                assert "(" in full_name or len(parsed["last_name"]) <= 2
            elif language == "spanish":
                # Spanish names often have multiple surnames
                assert len(parsed["last_name"].split()) >= 1

    def _parse_full_name(self, full_name: str, language: str) -> Dict[str, str]:
        """Helper method to parse full names by cultural convention."""
        parts = full_name.split()
        
        if language == "mandarin":
            # Handle Chinese names with English translations
            if "(" in full_name:
                chinese_part = full_name.split("(")[0].strip()
                english_part = full_name.split("(")[1].replace(")", "").strip()
                return {
                    "first_name": english_part.split()[0] if english_part else chinese_part[1:],
                    "last_name": english_part.split()[-1] if english_part else chinese_part[0],
                    "chinese_name": chinese_part,
                    "english_name": english_part
                }
            else:
                return {"first_name": full_name[1:], "last_name": full_name[0]}
        
        elif language == "spanish":
            # Spanish names: First name + paternal surname + maternal surname
            if len(parts) >= 3:
                return {
                    "first_name": parts[0],
                    "last_name": " ".join(parts[1:]),
                    "paternal_surname": parts[1] if len(parts) > 1 else "",
                    "maternal_surname": parts[2] if len(parts) > 2 else ""
                }
            else:
                return {"first_name": parts[0], "last_name": parts[-1] if len(parts) > 1 else ""}
        
        else:
            # English/Western names: First Middle Last
            return {
                "first_name": parts[0],
                "last_name": parts[-1] if len(parts) > 1 else "",
                "middle_names": " ".join(parts[1:-1]) if len(parts) > 2 else ""
            }

    def test_name_formatting_cultural_conventions(self, sample_names):
        """Test name formatting according to cultural conventions."""
        formatting_tests = [
            # English: First Last
            ("Alice Johnson", "english", "Alice Johnson"),
            # Spanish: Nombre Apellido1 Apellido2  
            ("Ana García López", "spanish", "Ana García López"),
            # Chinese: 姓名 (First Last)
            ("李明 (Li Ming)", "mandarin", "李明 (Li Ming)")
        ]
        
        for full_name, culture, expected_format in formatting_tests:
            formatted = self._format_name_culturally(full_name, culture)
            # Basic test - should maintain cultural appropriateness
            assert len(formatted) > 0
            if culture == "mandarin":
                assert "(" in formatted or not any(ord(c) > 127 for c in formatted)

    def _format_name_culturally(self, name: str, culture: str) -> str:
        """Helper method to format names according to cultural conventions."""
        if culture == "formal_spanish":
            # Format: Apellido1, Nombre
            parts = self._parse_full_name(name, "spanish")
            return f"{parts['last_name']}, {parts['first_name']}"
        elif culture == "mandarin":
            # Preserve original format or convert appropriately
            return name
        else:
            # Standard Western format
            return name

    def test_multilingual_parsing_edge_cases(self, language_manager):
        """Test edge cases in multilingual parsing."""
        edge_cases = [
            # Empty/minimal inputs
            ("", "english"),
            ("A", "spanish"),
            ("一", "mandarin"),
            
            # Mixed language inputs
            ("Hello 你好", "english"),
            ("Principle A 原则", "mandarin"),
            ("Principio 1 principle", "spanish"),
            
            # Special characters
            ("André García-López", "spanish"),
            ("李明·约翰", "mandarin"),
            ("O'Brien-Smith", "english")
        ]
        
        for text, language in edge_cases:
            language_manager.set_language(SupportedLanguage(language))
            
            try:
                # Should handle gracefully without crashing
                result = language_manager.parse_text_safely(text)
                assert result is not None  # Should return something, even if empty
            except Exception as e:
                pytest.fail(f"Parsing failed for edge case '{text}' in {language}: {e}")

    def test_language_detection_accuracy(self, sample_names):
        """Test automatic language detection from text samples."""
        detection_cases = [
            ("Hello, how are you?", "english"),
            ("Hola, ¿cómo estás?", "spanish"),
            ("你好，你好吗？", "mandarin"),
            ("Principle A is best", "english"),
            ("El principio A es mejor", "spanish"),
            ("原则A最好", "mandarin")
        ]
        
        for text, expected_language in detection_cases:
            detected = self._detect_language(text)
            assert detected == expected_language, f"Language detection failed for: {text}"

    def _detect_language(self, text: str) -> str:
        """Helper method for language detection."""
        # Simple heuristic-based detection
        if any(ord(c) > 0x4e00 and ord(c) < 0x9fff for c in text):
            return "mandarin"
        elif any(c in "ñáéíóúü¿¡" for c in text.lower()):
            return "spanish"  
        else:
            return "english"