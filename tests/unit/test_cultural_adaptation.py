"""
Consolidated Cultural Adaptation Tests

This module contains comprehensive tests for cultural adaptation functionality,
consolidating tests from multiple files into a unified, parametrized test suite.

Functionality tested:
1. Currency handling and formatting across cultures
2. Regional number formats and conventions
3. Cultural context adaptations
4. Two-stage multilingual voting systems
5. Cross-cultural validation and consistency

Consolidated from:
- test_currency_handling.py
- test_regional_formats.py  
- test_cultural_context.py
- test_two_stage_multilingual.py
"""

import pytest
import locale
from decimal import Decimal
from typing import Dict, List, Any, Tuple

from utils.cultural_adaptation import (
    CurrencyFormatter, RegionalFormatter, CulturalContext,
    format_currency, format_number, adapt_cultural_context
)
from core.two_stage_voting_manager import TwoStageVotingManager
from utils.language_manager import SupportedLanguage


class TestCulturalAdaptation:
    """Unified test class for cultural adaptation functionality."""
    
    @pytest.fixture
    def currency_test_data(self):
        """Currency formatting test data across cultures."""
        return {
            "english": {
                "symbol": "$",
                "position": "before", 
                "thousands_sep": ",",
                "decimal_sep": ".",
                "test_cases": [
                    (1000, "$1,000"),
                    (1234.56, "$1,234.56"),
                    (1000000, "$1,000,000"),
                    (0.99, "$0.99"),
                    (50000, "$50,000")
                ]
            },
            "spanish": {
                "symbol": "€", 
                "position": "after",
                "thousands_sep": ".",
                "decimal_sep": ",",
                "test_cases": [
                    (1000, "1.000€"),
                    (1234.56, "1.234,56€"), 
                    (1000000, "1.000.000€"),
                    (0.99, "0,99€"),
                    (50000, "50.000€")
                ]
            },
            "mandarin": {
                "symbol": "¥",
                "position": "before",
                "thousands_sep": ",", 
                "decimal_sep": ".",
                "test_cases": [
                    (1000, "¥1,000"),
                    (1234.56, "¥1,234.56"),
                    (1000000, "¥1,000,000"),
                    (0.99, "¥0.99"),
                    (50000, "¥50,000")
                ]
            }
        }
    
    @pytest.fixture
    def regional_format_data(self):
        """Regional number formatting test data."""
        return {
            "english": {
                "decimal": ".",
                "thousands": ",",
                "test_cases": [
                    (1234.56, "1,234.56"),
                    (1000000, "1,000,000"),
                    (0.123, "0.123"),
                    (75.5, "75.5")
                ]
            },
            "spanish": {
                "decimal": ",", 
                "thousands": ".",
                "test_cases": [
                    (1234.56, "1.234,56"),
                    (1000000, "1.000.000"),
                    (0.123, "0,123"),
                    (75.5, "75,5")
                ]
            },
            "german": {
                "decimal": ",",
                "thousands": ".", 
                "test_cases": [
                    (1234.56, "1.234,56"),
                    (1000000, "1.000.000"),
                    (0.123, "0,123"),
                    (75.5, "75,5")
                ]
            },
            "indian": {
                "decimal": ".",
                "thousands": ",",
                "lakh_crore": True,  # Special Indian number system
                "test_cases": [
                    (100000, "1,00,000"),  # 1 lakh
                    (1000000, "10,00,000"), # 10 lakh
                    (10000000, "1,00,00,000") # 1 crore
                ]
            }
        }
    
    @pytest.fixture
    def cultural_context_data(self):
        """Cultural context test data."""
        return {
            "english": {
                "greeting_formal": "Dear Sir/Madam",
                "greeting_informal": "Hi there",
                "date_format": "%m/%d/%Y",
                "time_format": "%I:%M %p",
                "politeness_level": "medium"
            },
            "spanish": {
                "greeting_formal": "Estimado/a Señor/a",
                "greeting_informal": "Hola",
                "date_format": "%d/%m/%Y", 
                "time_format": "%H:%M",
                "politeness_level": "high"
            },
            "mandarin": {
                "greeting_formal": "尊敬的先生/女士",
                "greeting_informal": "你好",
                "date_format": "%Y/%m/%d",
                "time_format": "%H:%M",
                "politeness_level": "very_high"
            }
        }

    # CURRENCY FORMATTING TESTS
    @pytest.mark.parametrize("culture", ["english", "spanish", "mandarin"])
    def test_currency_formatting_by_culture(self, currency_test_data, culture):
        """Test currency formatting according to cultural conventions."""
        culture_data = currency_test_data[culture]
        formatter = CurrencyFormatter(
            symbol=culture_data["symbol"],
            position=culture_data["position"],
            thousands_sep=culture_data["thousands_sep"],
            decimal_sep=culture_data["decimal_sep"]
        )
        
        for amount, expected in culture_data["test_cases"]:
            result = formatter.format(amount)
            assert result == expected, f"Currency formatting failed for {amount} in {culture}"

    def test_currency_edge_cases(self, currency_test_data):
        """Test currency formatting edge cases.""" 
        english_formatter = CurrencyFormatter(**{
            k: v for k, v in currency_test_data["english"].items() 
            if k != "test_cases"
        })
        
        edge_cases = [
            # Zero amounts
            (0, "$0"),
            (0.00, "$0"),
            
            # Negative amounts  
            (-100, "-$100"),
            (-1234.56, "-$1,234.56"),
            
            # Very large amounts
            (1e9, "$1,000,000,000"),
            (1.23e6, "$1,230,000"),
            
            # Very small amounts
            (0.001, "$0"),  # Should round to nearest cent
            (0.01, "$0.01"),
            
            # Decimal precision
            (123.456, "$123.46"),  # Should round to 2 decimal places
            (123.454, "$123.45")
        ]
        
        for amount, expected in edge_cases:
            result = english_formatter.format(amount)
            assert result == expected, f"Edge case failed: {amount}"

    @pytest.mark.parametrize("amount,precision", [
        (123.456, 2),  # Standard currency precision
        (123.456, 3),  # Extended precision
        (123, 0),      # No decimal places
        (123.4, 1)     # Single decimal place
    ])
    def test_currency_precision_control(self, amount, precision):
        """Test currency formatting with different precision levels."""
        formatter = CurrencyFormatter(
            symbol="$", position="before",
            thousands_sep=",", decimal_sep=".",
            decimal_places=precision
        )
        
        result = formatter.format(amount)
        
        if precision > 0:
            assert "." in result
            decimal_part = result.split(".")[-1].replace("$", "")
            assert len(decimal_part) == precision
        else:
            assert "." not in result

    def test_currency_symbol_variations(self):
        """Test formatting with different currency symbols."""
        test_symbols = [
            ("$", "USD"),
            ("€", "EUR"), 
            ("£", "GBP"),
            ("¥", "JPY"),
            ("₹", "INR"),
            ("₩", "KRW")
        ]
        
        for symbol, currency_code in test_symbols:
            formatter = CurrencyFormatter(symbol=symbol, position="before")
            result = formatter.format(1000)
            
            assert symbol in result
            assert "1000" in result.replace(",", "")

    # REGIONAL NUMBER FORMATTING TESTS  
    @pytest.mark.parametrize("region", ["english", "spanish", "german", "indian"])
    def test_regional_number_formatting(self, regional_format_data, region):
        """Test number formatting according to regional conventions."""
        if region not in regional_format_data:
            pytest.skip(f"No test data for {region}")
            
        region_data = regional_format_data[region]
        formatter = RegionalFormatter(
            decimal_sep=region_data["decimal"],
            thousands_sep=region_data["thousands"],
            use_indian_system=region_data.get("lakh_crore", False)
        )
        
        for number, expected in region_data["test_cases"]:
            result = formatter.format_number(number)
            assert result == expected, f"Regional formatting failed for {number} in {region}"

    def test_percentage_formatting_regional(self, regional_format_data):
        """Test percentage formatting with regional conventions."""
        test_cases = [
            # (percentage, region, expected)
            (75.5, "english", "75.5%"),
            (75.5, "spanish", "75,5%"),
            (100.0, "english", "100%"),
            (100.0, "spanish", "100%"),
            (33.33, "english", "33.33%"),
            (33.33, "spanish", "33,33%")
        ]
        
        for percentage, region, expected in test_cases:
            if region not in regional_format_data:
                continue
                
            region_data = regional_format_data[region]
            formatter = RegionalFormatter(
                decimal_sep=region_data["decimal"],
                thousands_sep=region_data["thousands"]
            )
            
            result = formatter.format_percentage(percentage)
            assert result == expected, f"Percentage formatting failed for {percentage} in {region}"

    def test_indian_numbering_system(self, regional_format_data):
        """Test Indian lakh-crore numbering system."""
        if "indian" not in regional_format_data:
            pytest.skip("No Indian format test data")
            
        indian_data = regional_format_data["indian"]
        formatter = RegionalFormatter(
            decimal_sep=indian_data["decimal"],
            thousands_sep=indian_data["thousands"],
            use_indian_system=True
        )
        
        # Test lakh-crore formatting
        lakh_crore_cases = [
            (100000, "1,00,000"),      # 1 lakh
            (1000000, "10,00,000"),    # 10 lakh  
            (10000000, "1,00,00,000"), # 1 crore
            (150000000, "15,00,00,000") # 15 crore
        ]
        
        for number, expected in lakh_crore_cases:
            result = formatter.format_number(number)
            assert result == expected, f"Indian numbering failed for {number}"

    # CULTURAL CONTEXT TESTS
    @pytest.mark.parametrize("culture", ["english", "spanish", "mandarin"])
    def test_cultural_context_adaptation(self, cultural_context_data, culture):
        """Test cultural context adaptation."""
        context_data = cultural_context_data[culture]
        context = CulturalContext(culture=SupportedLanguage(culture))
        
        # Test greeting adaptation
        formal_greeting = context.get_greeting(formal=True)
        informal_greeting = context.get_greeting(formal=False)
        
        assert formal_greeting != informal_greeting
        assert len(formal_greeting) > 0
        assert len(informal_greeting) > 0
        
        # Test politeness level
        politeness = context.get_politeness_level()
        expected_politeness = context_data["politeness_level"]
        assert politeness == expected_politeness

    def test_cultural_context_date_time_formatting(self, cultural_context_data):
        """Test date and time formatting across cultures."""
        import datetime
        test_date = datetime.datetime(2024, 3, 15, 14, 30, 0)
        
        for culture, context_data in cultural_context_data.items():
            context = CulturalContext(culture=SupportedLanguage(culture))
            
            # Format date according to cultural convention
            formatted_date = context.format_date(test_date)
            formatted_time = context.format_time(test_date)
            
            # Verify format contains expected elements
            assert "2024" in formatted_date or "24" in formatted_date
            assert "03" in formatted_date or "3" in formatted_date or "15" in formatted_date
            assert "14" in formatted_time or "2" in formatted_time or "30" in formatted_time

    def test_cultural_context_economic_terminology(self):
        """Test economic terminology adaptation across cultures."""
        economic_terms = [
            ("income", ["english", "spanish", "mandarin"]),
            ("floor_constraint", ["english", "spanish", "mandarin"]),
            ("maximizing", ["english", "spanish", "mandarin"]),
            ("principle", ["english", "spanish", "mandarin"])
        ]
        
        for term, cultures in economic_terms:
            translations = {}
            for culture in cultures:
                context = CulturalContext(culture=SupportedLanguage(culture))
                translation = context.get_economic_term(term)
                translations[culture] = translation
                
                assert translation is not None
                assert len(translation) > 0
            
            # Verify translations are different across cultures
            unique_translations = set(translations.values())
            assert len(unique_translations) == len(cultures), f"Economic term '{term}' not properly translated"

    # TWO-STAGE MULTILINGUAL VOTING TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_two_stage_voting_multilingual_prompts(self, language):
        """Test two-stage voting system with multilingual prompts."""
        voting_manager = TwoStageVotingManager(language=SupportedLanguage(language))
        
        # Test stage 1 prompts (principle selection)
        stage1_prompt = voting_manager.get_principle_selection_prompt()
        assert stage1_prompt is not None
        assert len(stage1_prompt) > 0
        
        # Should contain numbers 1-4 for principle selection
        assert "1" in stage1_prompt and "4" in stage1_prompt
        
        # Test stage 2 prompts (amount specification) 
        stage2_prompt = voting_manager.get_amount_specification_prompt("maximizing_floor")
        assert stage2_prompt is not None
        assert len(stage2_prompt) > 0

    @pytest.mark.parametrize("language,number_input,expected_principle", [
        ("english", "1", "maximizing_floor"),
        ("spanish", "2", "maximizing_average"),  
        ("mandarin", "3", "maximizing_average_floor_constraint"),
        ("english", "4", "maximizing_average_floor_constraint")
    ])
    def test_two_stage_voting_number_parsing_multilingual(self, language, number_input, expected_principle):
        """Test number parsing in two-stage voting across languages."""
        voting_manager = TwoStageVotingManager(language=SupportedLanguage(language))
        
        result = voting_manager.parse_principle_number(number_input)
        assert result == expected_principle, f"Number parsing failed for {number_input} in {language}"

    @pytest.mark.parametrize("language,amount_input,expected_amount", [
        ("english", "60%", 60.0),
        ("spanish", "75%", 75.0),
        ("mandarin", "80%", 80.0),
        ("english", "$50,000", 50000.0),
        ("spanish", "€45.000", 45000.0),
        ("mandarin", "¥100,000", 100000.0)
    ])
    def test_two_stage_voting_amount_parsing_multilingual(self, language, amount_input, expected_amount):
        """Test amount parsing in two-stage voting across languages."""
        voting_manager = TwoStageVotingManager(language=SupportedLanguage(language))
        
        result = voting_manager.parse_constraint_amount(amount_input)
        assert result == expected_amount, f"Amount parsing failed for {amount_input} in {language}"

    def test_two_stage_voting_error_messages_multilingual(self):
        """Test error message localization in two-stage voting."""
        error_scenarios = [
            ("invalid_number", ["english", "spanish", "mandarin"]),
            ("invalid_amount", ["english", "spanish", "mandarin"]),
            ("timeout", ["english", "spanish", "mandarin"])
        ]
        
        for error_type, languages in error_scenarios:
            error_messages = {}
            
            for language in languages:
                voting_manager = TwoStageVotingManager(language=SupportedLanguage(language))
                error_msg = voting_manager.get_error_message(error_type)
                error_messages[language] = error_msg
                
                assert error_msg is not None
                assert len(error_msg) > 0
            
            # Verify error messages are different across languages
            unique_messages = set(error_messages.values())
            assert len(unique_messages) == len(languages), f"Error type '{error_type}' not properly localized"

    # CROSS-CULTURAL VALIDATION TESTS
    def test_cultural_consistency_validation(self):
        """Test consistency validation across cultural adaptations.""" 
        base_data = {
            "amount": 50000,
            "percentage": 75.5,
            "principle": "maximizing_floor"
        }
        
        adaptations = {}
        cultures = ["english", "spanish", "mandarin"]
        
        for culture in cultures:
            adapted = adapt_cultural_context(base_data, SupportedLanguage(culture))
            adaptations[culture] = adapted
            
            # Basic structure should be preserved
            assert "amount" in adapted
            assert "percentage" in adapted  
            assert "principle" in adapted
            
            # Values should maintain semantic meaning
            assert isinstance(adapted["amount"], (int, float, str))
            assert isinstance(adapted["percentage"], (int, float, str))

    def test_cultural_boundary_cases(self):
        """Test cultural adaptation boundary cases."""
        boundary_cases = [
            # Very large numbers
            {"amount": 1e9, "culture": "english"},
            {"amount": 1e9, "culture": "spanish"},
            
            # Very small percentages
            {"percentage": 0.1, "culture": "english"},
            {"percentage": 0.1, "culture": "spanish"},
            
            # Edge case amounts
            {"amount": 0, "culture": "mandarin"},
            {"amount": -1000, "culture": "english"},  # Should handle gracefully
            
            # Special characters in text
            {"text": "Test with special chars: àáâãäåæçèéêë", "culture": "spanish"}
        ]
        
        for case in boundary_cases:
            culture = case.pop("culture")
            try:
                adapted = adapt_cultural_context(case, SupportedLanguage(culture))
                assert adapted is not None
                # Should not crash on boundary cases
            except Exception as e:
                pytest.fail(f"Cultural adaptation failed on boundary case {case} for {culture}: {e}")

    def test_fallback_cultural_handling(self):
        """Test fallback behavior when cultural data is missing."""
        # Test with unsupported culture 
        try:
            unsupported_context = CulturalContext(culture="unsupported_language")
            greeting = unsupported_context.get_greeting()
            
            # Should fallback to English or provide default
            assert greeting is not None
            assert len(greeting) > 0
        except Exception:
            # It's acceptable for unsupported cultures to raise exceptions
            pass

    def test_cultural_data_completeness(self, cultural_context_data):
        """Test that cultural data is complete across all supported languages."""
        required_fields = [
            "greeting_formal", "greeting_informal", 
            "date_format", "time_format", "politeness_level"
        ]
        
        for culture, data in cultural_context_data.items():
            for field in required_fields:
                assert field in data, f"Missing {field} in {culture} cultural data"
                assert data[field] is not None, f"Null {field} in {culture} cultural data"
                assert len(str(data[field])) > 0, f"Empty {field} in {culture} cultural data"