"""
Multilingual Tests for Two-Stage Voting System

This module contains comprehensive tests for the multilingual support
in the two-stage voting system, covering all languages and cultural adaptations.
"""

import pytest
from unittest.mock import Mock, patch
from utils.language_manager import SupportedLanguage, get_language_manager
from utils.cultural_adaptation import (
    AmountFormattingManager, LanguageRegisterManager,
    get_amount_formatter, get_register_manager,
    SupportedLanguage as CulturalLanguage, FormalityLevel
)
from core.principle_name_manager import (
    PrincipleNameManager, PrincipleNumber,
    get_principle_name_manager, clear_principle_name_cache
)


class TestAmountFormattingManager:
    """Test cultural adaptation for amount formatting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = AmountFormattingManager()
    
    def test_format_amount_english(self):
        """Test amount formatting in English."""
        result = self.formatter.format_amount(25000, CulturalLanguage.ENGLISH)
        assert result == "$25,000"
        
        result = self.formatter.format_amount(1000, CulturalLanguage.ENGLISH, include_currency=False)
        assert result == "1,000"
    
    def test_format_amount_spanish(self):
        """Test amount formatting in Spanish."""
        result = self.formatter.format_amount(15000, CulturalLanguage.SPANISH)
        assert result == "$15,000"
        
        result = self.formatter.format_amount(50000, CulturalLanguage.SPANISH, include_currency=False)
        assert result == "50,000"
    
    def test_format_amount_mandarin(self):
        """Test amount formatting in Mandarin."""
        result = self.formatter.format_amount(30000, CulturalLanguage.MANDARIN)
        assert result == "$30,000"
        
        result = self.formatter.format_amount(75000, CulturalLanguage.MANDARIN, include_currency=False)
        assert result == "75,000"
    
    def test_format_amount_range_english(self):
        """Test range formatting in English."""
        result = self.formatter.format_amount_range(1000, 100000, CulturalLanguage.ENGLISH)
        assert "between $1,000 and $100,000" in result
    
    def test_format_amount_range_spanish(self):
        """Test range formatting in Spanish."""
        result = self.formatter.format_amount_range(5000, 50000, CulturalLanguage.SPANISH)
        assert "entre $5,000 y $50,000" in result
    
    def test_format_amount_range_mandarin(self):
        """Test range formatting in Mandarin."""
        result = self.formatter.format_amount_range(10000, 80000, CulturalLanguage.MANDARIN)
        assert "$10,000到$80,000之间" in result
    
    def test_format_minimum_amount(self):
        """Test minimum amount formatting across languages."""
        # English
        result = self.formatter.format_minimum_amount(5000, CulturalLanguage.ENGLISH)
        assert result == "at least $5,000"
        
        # Spanish
        result = self.formatter.format_minimum_amount(5000, CulturalLanguage.SPANISH)
        assert result == "al menos $5,000"
        
        # Mandarin
        result = self.formatter.format_minimum_amount(5000, CulturalLanguage.MANDARIN)
        assert result == "至少 $5,000"
    
    def test_format_maximum_amount(self):
        """Test maximum amount formatting across languages."""
        # English
        result = self.formatter.format_maximum_amount(100000, CulturalLanguage.ENGLISH)
        assert result == "no more than $100,000"
        
        # Spanish
        result = self.formatter.format_maximum_amount(100000, CulturalLanguage.SPANISH)
        assert result == "no más de $100,000"
        
        # Mandarin
        result = self.formatter.format_maximum_amount(100000, CulturalLanguage.MANDARIN)
        assert result == "不超过 $100,000"
    
    def test_validate_amount_input(self):
        """Test amount input validation."""
        # Valid inputs
        amount, error = self.formatter.validate_amount_input("25000")
        assert amount == 25000
        assert error is None
        
        amount, error = self.formatter.validate_amount_input("$15,000")
        assert amount == 15000
        assert error is None
        
        amount, error = self.formatter.validate_amount_input("$50000")
        assert amount == 50000
        assert error is None
        
        # Invalid inputs
        amount, error = self.formatter.validate_amount_input("")
        assert amount is None
        assert error == "empty_amount_response"
        
        amount, error = self.formatter.validate_amount_input("0")
        assert amount is None
        assert error == "amount_must_be_positive"
        
        amount, error = self.formatter.validate_amount_input("abc")
        assert amount is None
        assert error == "no_amount_found"  # Updated to new error type
        
        amount, error = self.formatter.validate_amount_input("1500000")  # Too high
        assert amount is None
        assert error == "amount_too_high"
    
    def test_validate_amount_input_verbose_text(self):
        """Test amount extraction from verbose text responses."""
        # Single amount in verbose text (your original example)
        verbose_text = "Okay, let's go with $10000. I think prioritizing a solid floor of $10,000 is absolutely crucial. Seeing how drastically the average can be skewed by a huge range of incomes – and how easily people at the bottom can be left behind – really solidified that for me. It feels like the most responsible and, frankly, the most *just* approach, especially considering my own situation. It's a starting point, and we can adjust it later if we need to, but $10,000 feels like a good, firm foundation. I think we should vote."
        amount, error = self.formatter.validate_amount_input(verbose_text)
        assert amount == 10000
        assert error is None
        
        # Spanish verbose text
        spanish_text = "Creo que deberíamos elegir $25,000 dólares como nuestro mínimo. Es una cantidad razonable que protegerá a todos."
        amount, error = self.formatter.validate_amount_input(spanish_text)
        assert amount == 25000
        assert error is None
        
        # Multiple identical amounts (should work)
        identical_amounts = "I think $15000 is good, yes fifteen thousand dollars is my choice"
        amount, error = self.formatter.validate_amount_input(identical_amounts)
        assert amount == 15000
        assert error is None
        
        # Multiple different amounts (should fail)
        different_amounts = "I'm torn between $5,000 and $10,000, maybe something like $7,500 would work"
        amount, error = self.formatter.validate_amount_input(different_amounts)
        assert amount is None
        assert error == "multiple_different_amounts_found"
        
        # No amounts in text
        no_amounts = "I think the middle option is the best choice for everyone involved"
        amount, error = self.formatter.validate_amount_input(no_amounts)
        assert amount is None
        assert error == "no_amount_found"
    
    def test_validate_amount_input_chinese_numbers(self):
        """Test Chinese number extraction."""
        # Basic Chinese numbers
        chinese_text_1 = "我选择一万美元作为最低收入"
        amount, error = self.formatter.validate_amount_input(chinese_text_1)
        assert amount == 10000
        assert error is None
        
        chinese_text_2 = "五千美元应该足够了"
        amount, error = self.formatter.validate_amount_input(chinese_text_2)
        assert amount == 5000
        assert error is None
        
        # Arabic numerals in Chinese text
        chinese_with_numbers = "我认为25000美元是一个合理的选择"
        amount, error = self.formatter.validate_amount_input(chinese_with_numbers)
        assert amount == 25000
        assert error is None
    
    def test_validate_amount_input_edge_cases(self):
        """Test edge cases for amount validation."""
        # Very small amounts (below threshold)
        small_amount = "I choose $50 dollars"
        amount, error = self.formatter.validate_amount_input(small_amount)
        assert amount is None
        assert error == "amount_too_low"  # Below 100 threshold
        
        # Amounts with various formatting
        formatted_amounts = [
            "$20,000 dollars",
            "20000",
            "$20000", 
            "twenty thousand dollars would be $20,000"
        ]
        
        for text in formatted_amounts[:3]:  # Skip the last one with text numbers
            amount, error = self.formatter.validate_amount_input(text)
            assert amount == 20000, f"Failed for input: {text}"
            assert error is None, f"Unexpected error for input: {text}"
    
    def test_invalid_amount_handling(self):
        """Test handling of invalid amounts."""
        result = self.formatter.format_amount(-1000, CulturalLanguage.ENGLISH)
        assert result == "-1000"  # Fallback for invalid amount
        
        result = self.formatter.format_amount("invalid", CulturalLanguage.ENGLISH)
        assert result == "invalid"  # Fallback for non-numeric


class TestLanguageRegisterManager:
    """Test language register and formality management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.register_manager = LanguageRegisterManager()
    
    def test_get_appropriate_formality(self):
        """Test formality level determination."""
        # Error messages should be formal in Spanish and Mandarin
        formality = self.register_manager.get_appropriate_formality("error_messages", CulturalLanguage.SPANISH)
        assert formality == FormalityLevel.FORMAL
        
        formality = self.register_manager.get_appropriate_formality("error_messages", CulturalLanguage.MANDARIN)
        assert formality == FormalityLevel.FORMAL
        
        # English should be neutral
        formality = self.register_manager.get_appropriate_formality("error_messages", CulturalLanguage.ENGLISH)
        assert formality == FormalityLevel.NEUTRAL
    
    def test_add_politeness_marker(self):
        """Test politeness marker addition."""
        # Spanish should add "Por favor"
        result = self.register_manager.add_politeness_marker(
            "Respond with a number", "error_messages", CulturalLanguage.SPANISH
        )
        assert result.startswith("Por favor")
        
        # Mandarin should add "请" for formal contexts
        result = self.register_manager.add_politeness_marker(
            "Choose a principle", "instructions", CulturalLanguage.MANDARIN
        )
        assert result.startswith("请")
        
        # English neutral context should not add markers
        result = self.register_manager.add_politeness_marker(
            "Choose a principle", "error_messages", CulturalLanguage.ENGLISH
        )
        assert not result.startswith("Please")


class TestPrincipleNameManager:
    """Test principle name management and translation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock language manager to avoid dependency on translation files
        self.mock_language_manager = Mock()
        self.mock_language_manager.current_language = SupportedLanguage.ENGLISH
        
        # Set up mock translations
        principle_translations = {
            "maximizing_floor": "Maximizing Floor Income",
            "maximizing_average": "Maximizing Average Income", 
            "maximizing_average_floor_constraint": "Maximizing Average with Floor Constraint",
            "maximizing_average_range_constraint": "Maximizing Average with Range Constraint"
        }
        
        def mock_get_justice_principle_name(key):
            return principle_translations.get(key, f"Unknown principle: {key}")
        
        self.mock_language_manager.get_justice_principle_name = mock_get_justice_principle_name
        
        self.principle_manager = PrincipleNameManager(self.mock_language_manager)
    
    def test_get_principle_display_name(self):
        """Test principle display name retrieval."""
        # Test all four principles
        name1 = self.principle_manager.get_principle_display_name(1)
        assert name1 == "Maximizing Floor Income"
        
        name2 = self.principle_manager.get_principle_display_name(2)
        assert name2 == "Maximizing Average Income"
        
        name3 = self.principle_manager.get_principle_display_name(3)
        assert name3 == "Maximizing Average with Floor Constraint"
        
        name4 = self.principle_manager.get_principle_display_name(4)
        assert name4 == "Maximizing Average with Range Constraint"
        
        # Test invalid principle number
        with pytest.raises(ValueError):
            self.principle_manager.get_principle_display_name(5)
    
    def test_get_principle_menu_text(self):
        """Test principle menu text generation."""
        menu = self.principle_manager.get_principle_menu_text()
        
        assert "1. Maximizing Floor Income" in menu
        assert "2. Maximizing Average Income" in menu
        assert "3. Maximizing Average with Floor Constraint" in menu
        assert "4. Maximizing Average with Range Constraint" in menu
    
    def test_requires_constraint_amount(self):
        """Test constraint amount requirement detection."""
        # Principles 1 and 2 should not require constraints
        assert not self.principle_manager.requires_constraint_amount(1)
        assert not self.principle_manager.requires_constraint_amount(2)
        
        # Principles 3 and 4 should require constraints
        assert self.principle_manager.requires_constraint_amount(3)
        assert self.principle_manager.requires_constraint_amount(4)
        
        # Invalid principle number should raise error
        with pytest.raises(ValueError):
            self.principle_manager.requires_constraint_amount(0)
    
    def test_get_constraint_type_name(self):
        """Test constraint type name retrieval."""
        # Mock current language is English
        floor_constraint = self.principle_manager.get_constraint_type_name(3)
        assert "floor" in floor_constraint.lower()
        
        range_constraint = self.principle_manager.get_constraint_type_name(4)
        assert "range" in range_constraint.lower()
        
        # Non-constraint principle should raise error
        with pytest.raises(ValueError):
            self.principle_manager.get_constraint_type_name(1)
    
    @patch('core.principle_name_manager.get_amount_formatter')
    def test_format_principle_with_constraint(self, mock_get_formatter):
        """Test formatting principle with constraint amount."""
        # Mock amount formatter
        mock_formatter = Mock()
        mock_formatter.format_amount.return_value = "$25,000"
        mock_get_formatter.return_value = mock_formatter
        
        # Test floor constraint formatting
        result = self.principle_manager.format_principle_with_constraint(3, 25000)
        assert "Maximizing Average with Floor Constraint" in result
        assert "$25,000" in result
        assert "floor constraint" in result.lower()
        
        # Test range constraint formatting
        result = self.principle_manager.format_principle_with_constraint(4, 50000)
        assert "Maximizing Average with Range Constraint" in result
        
        # Non-constraint principle should raise error
        with pytest.raises(ValueError):
            self.principle_manager.format_principle_with_constraint(1, 25000)
    
    def test_cache_functionality(self):
        """Test caching of principle names."""
        # First call should hit the language manager
        name1 = self.principle_manager.get_principle_display_name(1)
        
        # Second call should use cache
        name2 = self.principle_manager.get_principle_display_name(1)
        assert name1 == name2
        
        # Clear cache and verify it's cleared
        self.principle_manager.clear_cache()
        assert len(self.principle_manager._name_cache) == 0


class TestLanguageManagerIntegration:
    """Test integration between language manager and two-stage voting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = get_language_manager()
        self.original_language = self.language_manager.current_language
    
    def teardown_method(self):
        """Restore original language."""
        self.language_manager.set_language(self.original_language)
    
    def test_get_two_stage_error_message_fallback(self):
        """Test fallback error messages when translations are missing."""
        # Test with a non-existent error type
        message = self.language_manager.get_two_stage_error_message("non_existent_error", 1, 3)
        assert "Invalid response (attempt 1/3)" in message
        assert "Please try again" in message
    
    def test_format_amount_display_fallback(self):
        """Test amount display formatting with fallback."""
        # This should work even without cultural_adaptation import
        result = self.language_manager.format_amount_display(25000)
        assert "$" in result
        assert "25" in result
    
    def test_get_two_stage_timeout_message(self):
        """Test timeout message retrieval."""
        # English
        self.language_manager.set_language(SupportedLanguage.ENGLISH)
        message = self.language_manager.get_two_stage_timeout_message()
        assert "timeout" in message.lower() or "time" in message.lower()
        
        # Spanish
        self.language_manager.set_language(SupportedLanguage.SPANISH)
        message = self.language_manager.get_two_stage_timeout_message()
        assert "tiempo" in message.lower() or "timeout" in message.lower()
        
        # Mandarin
        self.language_manager.set_language(SupportedLanguage.MANDARIN)
        message = self.language_manager.get_two_stage_timeout_message()
        assert len(message) > 0  # Should have some message
    
    def test_validate_two_stage_translations(self):
        """Test validation of two-stage translation completeness."""
        results = self.language_manager.validate_two_stage_translations()
        
        # Should have results for all languages
        assert "English" in results
        assert "Spanish" in results
        assert "Mandarin" in results
        
        # Results should be boolean
        for language, is_valid in results.items():
            assert isinstance(is_valid, bool)


class TestMultilingualIntegration:
    """Test integration across all multilingual components."""
    
    def test_global_instances(self):
        """Test that global instances work correctly."""
        # Amount formatter
        formatter1 = get_amount_formatter()
        formatter2 = get_amount_formatter()
        assert formatter1 is formatter2  # Should be same instance
        
        # Register manager
        register1 = get_register_manager()
        register2 = get_register_manager()
        assert register1 is register2  # Should be same instance
        
        # Principle name manager
        principle1 = get_principle_name_manager()
        principle2 = get_principle_name_manager()
        assert principle1 is principle2  # Should be same instance
    
    def test_principle_name_cache_clearing(self):
        """Test global principle name cache clearing."""
        # Get a principle name to populate cache
        manager = get_principle_name_manager()
        name = manager.get_principle_display_name(1)
        assert len(manager._name_cache) > 0
        
        # Clear cache globally
        clear_principle_name_cache()
        assert len(manager._name_cache) == 0
    
    def test_cross_component_consistency(self):
        """Test consistency across different components."""
        formatter = get_amount_formatter()
        principle_manager = get_principle_name_manager()
        language_manager = get_language_manager()
        
        # Test amount formatting consistency
        amount1 = formatter.format_amount(25000, CulturalLanguage.ENGLISH)
        amount2 = language_manager.format_amount_display(25000)
        
        # Both should include $ and proper formatting
        assert "$" in amount1 and "$" in amount2
        assert "25" in amount1 and "25" in amount2
    
    def test_error_handling_robustness(self):
        """Test error handling across components."""
        # Amount formatter with invalid input
        formatter = get_amount_formatter()
        result = formatter.format_amount("invalid", CulturalLanguage.ENGLISH)
        assert result is not None  # Should not crash
        
        # Principle manager with invalid numbers
        principle_manager = get_principle_name_manager()
        with pytest.raises(ValueError):
            principle_manager.get_principle_display_name(0)
        
        # Language manager with missing keys
        language_manager = get_language_manager()
        message = language_manager.get_two_stage_error_message("invalid_error_type", 1, 3)
        assert "Invalid response" in message  # Should have fallback


class TestTranslationFixtures:
    """Test fixtures for validating actual translation content."""
    
    @pytest.fixture
    def sample_principle_names(self):
        """Sample principle names for testing."""
        return {
            SupportedLanguage.ENGLISH: {
                1: "Maximizing Floor Income",
                2: "Maximizing Average Income", 
                3: "Maximizing Average with Floor Constraint",
                4: "Maximizing Average with Range Constraint"
            },
            SupportedLanguage.SPANISH: {
                1: "Maximizar Ingreso Mínimo",
                2: "Maximizar Ingreso Promedio",
                3: "Maximizar Promedio con Restricción Mínima", 
                4: "Maximizar Promedio con Restricción de Rango"
            },
            SupportedLanguage.MANDARIN: {
                1: "最大化最低收入",
                2: "最大化平均收入",
                3: "在最低收入约束条件下最大化平均收入",
                4: "在范围约束条件下最大化平均收入"
            }
        }
    
    @pytest.fixture  
    def sample_error_messages(self):
        """Sample error messages for testing."""
        return {
            SupportedLanguage.ENGLISH: {
                "respond_with_number_only": "Invalid response (attempt {attempt}/{max_attempts}). You must respond with exactly one number: 1, 2, 3, or 4.",
                "invalid_amount_format": "Invalid amount format (attempt {attempt}/{max_attempts}). You must respond with a positive whole dollar amount."
            },
            SupportedLanguage.SPANISH: {
                "respond_with_number_only": "Respuesta inválida (intento {attempt}/{max_attempts}). Debes responder con exactamente un número: 1, 2, 3, o 4.", 
                "invalid_amount_format": "Formato de cantidad inválido (intento {attempt}/{max_attempts}). Debes responder con una cantidad entera positiva en dólares."
            },
            SupportedLanguage.MANDARIN: {
                "respond_with_number_only": "无效回答（尝试{attempt}/{max_attempts}）。你必须只回答一个数字：1、2、3或4。",
                "invalid_amount_format": "金额格式无效（尝试{attempt}/{max_attempts}）。你必须回答一个正整数美元金额。"
            }
        }
    
    def test_principle_name_completeness(self, sample_principle_names):
        """Test that all principle names are defined for all languages."""
        for language, principles in sample_principle_names.items():
            assert len(principles) == 4
            for num in [1, 2, 3, 4]:
                assert num in principles
                assert len(principles[num]) > 0
    
    def test_error_message_formatting(self, sample_error_messages):
        """Test that error messages support proper formatting."""
        for language, messages in sample_error_messages.items():
            for error_type, template in messages.items():
                # Test that formatting works
                formatted = template.format(attempt=1, max_attempts=3)
                assert "{attempt}" not in formatted  # Placeholder should be replaced
                assert "{max_attempts}" not in formatted  # Placeholder should be replaced
                assert "1" in formatted and "3" in formatted
    
    def test_translation_consistency(self, sample_principle_names, sample_error_messages):
        """Test consistency across all translation sets."""
        # All languages should be represented
        languages = {SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN}
        
        assert set(sample_principle_names.keys()) == languages
        assert set(sample_error_messages.keys()) == languages
        
        # All should have the same structure
        english_principles = set(sample_principle_names[SupportedLanguage.ENGLISH].keys())
        for language in languages:
            lang_principles = set(sample_principle_names[language].keys())
            assert lang_principles == english_principles
        
        english_errors = set(sample_error_messages[SupportedLanguage.ENGLISH].keys())
        for language in languages:
            lang_errors = set(sample_error_messages[language].keys())
            assert lang_errors == english_errors


if __name__ == "__main__":
    pytest.main([__file__])