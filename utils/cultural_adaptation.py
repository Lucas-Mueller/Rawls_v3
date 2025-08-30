"""
Cultural Adaptation Manager for Two-Stage Voting System

This module provides cultural adaptation functions for multilingual support,
specifically handling amount formatting and language register adjustments
across different cultures and languages.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for cultural adaptation."""
    ENGLISH = "English"
    SPANISH = "Spanish"  
    MANDARIN = "Mandarin"


class FormalityLevel(Enum):
    """Language formality levels."""
    FORMAL = "formal"
    NEUTRAL = "neutral" 
    INFORMAL = "informal"


class AmountFormattingManager:
    """
    Manages culture-specific formatting for dollar amounts and numbers.
    
    Provides consistent formatting across different languages and cultures
    while respecting local conventions for number display and currency.
    """
    
    def __init__(self):
        """Initialize the amount formatting manager with cultural rules."""
        # Currency symbol preferences by language
        self.currency_symbols = {
            SupportedLanguage.ENGLISH: "$",
            SupportedLanguage.SPANISH: "$",  # US Dollar is common in experiments
            SupportedLanguage.MANDARIN: "$"  # US Dollar symbol maintained for clarity
        }
        
        # Number formatting preferences by language/culture
        self.number_formats = {
            SupportedLanguage.ENGLISH: {
                "thousands_separator": ",",
                "decimal_separator": ".",
                "currency_position": "prefix"  # $25,000
            },
            SupportedLanguage.SPANISH: {
                "thousands_separator": ",",  # US convention for experiments
                "decimal_separator": ".",    # US convention for experiments
                "currency_position": "prefix"  # $25,000
            },
            SupportedLanguage.MANDARIN: {
                "thousands_separator": ",",  # US convention for experiments
                "decimal_separator": ".",    # US convention for experiments  
                "currency_position": "prefix"  # $25,000
            }
        }
        
        # Range descriptions for different languages
        self.range_descriptions = {
            SupportedLanguage.ENGLISH: {
                "min": "minimum",
                "max": "maximum", 
                "range": "between {min} and {max}",
                "at_least": "at least",
                "no_more_than": "no more than"
            },
            SupportedLanguage.SPANISH: {
                "min": "mínimo",
                "max": "máximo",
                "range": "entre {min} y {max}",
                "at_least": "al menos", 
                "no_more_than": "no más de"
            },
            SupportedLanguage.MANDARIN: {
                "min": "最低",
                "max": "最高",
                "range": "{min}到{max}之间",
                "at_least": "至少",
                "no_more_than": "不超过"
            }
        }
    
    def format_amount(self, amount: int, language: SupportedLanguage, 
                     include_currency: bool = True) -> str:
        """
        Format a dollar amount according to cultural conventions.
        
        Args:
            amount: Dollar amount to format
            language: Target language for formatting
            include_currency: Whether to include currency symbol
            
        Returns:
            Formatted amount string (e.g., "$25,000" or "25,000")
        """
        if not isinstance(amount, (int, float)) or amount < 0:
            logger.warning(f"Invalid amount for formatting: {amount}")
            return str(amount)
        
        # Get formatting rules for language
        format_rules = self.number_formats.get(language, self.number_formats[SupportedLanguage.ENGLISH])
        
        # Format with thousands separator
        thousands_sep = format_rules["thousands_separator"]
        formatted_number = f"{amount:,}".replace(",", thousands_sep)
        
        # Add currency symbol if requested
        if include_currency:
            currency = self.currency_symbols.get(language, "$")
            if format_rules["currency_position"] == "prefix":
                return f"{currency}{formatted_number}"
            else:
                return f"{formatted_number}{currency}"
        
        return formatted_number
    
    def format_amount_range(self, min_amount: int, max_amount: int, 
                           language: SupportedLanguage) -> str:
        """
        Format an amount range according to cultural conventions.
        
        Args:
            min_amount: Minimum dollar amount
            max_amount: Maximum dollar amount  
            language: Target language for formatting
            
        Returns:
            Formatted range string (e.g., "between $1,000 and $100,000")
        """
        descriptions = self.range_descriptions.get(language, self.range_descriptions[SupportedLanguage.ENGLISH])
        
        min_formatted = self.format_amount(min_amount, language)
        max_formatted = self.format_amount(max_amount, language)
        
        return descriptions["range"].format(min=min_formatted, max=max_formatted)
    
    def format_minimum_amount(self, amount: int, language: SupportedLanguage) -> str:
        """
        Format a minimum amount description.
        
        Args:
            amount: Minimum dollar amount
            language: Target language for formatting
            
        Returns:
            Formatted minimum description (e.g., "at least $1,000")
        """
        descriptions = self.range_descriptions.get(language, self.range_descriptions[SupportedLanguage.ENGLISH])
        formatted_amount = self.format_amount(amount, language)
        
        return f"{descriptions['at_least']} {formatted_amount}"
    
    def format_maximum_amount(self, amount: int, language: SupportedLanguage) -> str:
        """
        Format a maximum amount description.
        
        Args:
            amount: Maximum dollar amount
            language: Target language for formatting
            
        Returns:
            Formatted maximum description (e.g., "no more than $100,000")
        """
        descriptions = self.range_descriptions.get(language, self.range_descriptions[SupportedLanguage.ENGLISH])
        formatted_amount = self.format_amount(amount, language)
        
        return f"{descriptions['no_more_than']} {formatted_amount}"
    
    def validate_amount_input(self, input_str: str) -> tuple[Optional[int], Optional[str]]:
        """
        Parse and validate amount input across different cultural formats.
        
        Args:
            input_str: Raw input string to parse
            
        Returns:
            Tuple of (parsed_amount, error_message). Amount is None if invalid.
        """
        if not input_str or not input_str.strip():
            return None, "empty_amount_response"
        
        # Clean the input - remove common currency symbols and whitespace
        cleaned = input_str.strip().replace("$", "").replace("¥", "").replace("€", "")
        
        # Handle different thousand separators
        if "," in cleaned and "." in cleaned:
            # Assume comma is thousands separator and period is decimal
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned and "." not in cleaned:
            # Could be either thousands separator or decimal - assume thousands
            if len(cleaned.split(",")[-1]) == 3:  # Last part has 3 digits - likely thousands
                cleaned = cleaned.replace(",", "")
            else:
                # Likely decimal separator - convert to period
                cleaned = cleaned.replace(",", ".")
        
        # Try to parse as number
        try:
            if "." in cleaned:
                # Has decimal - convert to int (remove decimal part)
                amount = int(float(cleaned))
            else:
                amount = int(cleaned)
            
            # Validate range
            if amount <= 0:
                return None, "amount_must_be_positive"
            elif amount > 1000000:  # 1 million cap for reasonableness
                return None, "amount_too_high"
            elif amount < 1:
                return None, "amount_too_low"
            
            return amount, None
            
        except (ValueError, TypeError):
            return None, "invalid_amount_format"


class LanguageRegisterManager:
    """
    Manages formality levels and language register for different contexts.
    
    Handles appropriate formality levels for error messages, instructions,
    and other text based on cultural norms and experiment context.
    """
    
    def __init__(self):
        """Initialize language register preferences."""
        # Default formality levels by language for different contexts
        self.context_formality = {
            "error_messages": {
                SupportedLanguage.ENGLISH: FormalityLevel.NEUTRAL,
                SupportedLanguage.SPANISH: FormalityLevel.FORMAL,  # More formal culture
                SupportedLanguage.MANDARIN: FormalityLevel.FORMAL  # More formal culture
            },
            "instructions": {
                SupportedLanguage.ENGLISH: FormalityLevel.NEUTRAL,
                SupportedLanguage.SPANISH: FormalityLevel.FORMAL,
                SupportedLanguage.MANDARIN: FormalityLevel.FORMAL
            },
            "confirmations": {
                SupportedLanguage.ENGLISH: FormalityLevel.NEUTRAL,
                SupportedLanguage.SPANISH: FormalityLevel.NEUTRAL,
                SupportedLanguage.MANDARIN: FormalityLevel.NEUTRAL
            }
        }
        
        # Politeness markers by language
        self.politeness_markers = {
            SupportedLanguage.ENGLISH: {
                FormalityLevel.FORMAL: "Please",
                FormalityLevel.NEUTRAL: "",
                FormalityLevel.INFORMAL: ""
            },
            SupportedLanguage.SPANISH: {
                FormalityLevel.FORMAL: "Por favor",
                FormalityLevel.NEUTRAL: "Por favor",
                FormalityLevel.INFORMAL: ""
            },
            SupportedLanguage.MANDARIN: {
                FormalityLevel.FORMAL: "请",
                FormalityLevel.NEUTRAL: "",
                FormalityLevel.INFORMAL: ""
            }
        }
    
    def get_appropriate_formality(self, context: str, language: SupportedLanguage) -> FormalityLevel:
        """
        Get the appropriate formality level for a given context and language.
        
        Args:
            context: Context type (e.g., "error_messages", "instructions")
            language: Target language
            
        Returns:
            Appropriate formality level for the context and language
        """
        context_levels = self.context_formality.get(context, {})
        return context_levels.get(language, FormalityLevel.NEUTRAL)
    
    def add_politeness_marker(self, text: str, context: str, 
                            language: SupportedLanguage) -> str:
        """
        Add appropriate politeness markers to text based on cultural norms.
        
        Args:
            text: Original text
            context: Context type for formality determination
            language: Target language
            
        Returns:
            Text with appropriate politeness markers added
        """
        formality = self.get_appropriate_formality(context, language)
        markers = self.politeness_markers.get(language, {})
        marker = markers.get(formality, "")
        
        if marker and not text.strip().startswith(marker):
            return f"{marker} {text}".strip()
        
        return text


# Global instances for easy access
_amount_formatter: Optional[AmountFormattingManager] = None
_register_manager: Optional[LanguageRegisterManager] = None


def get_amount_formatter() -> AmountFormattingManager:
    """Get the global amount formatting manager instance."""
    global _amount_formatter
    if _amount_formatter is None:
        _amount_formatter = AmountFormattingManager()
    return _amount_formatter


def get_register_manager() -> LanguageRegisterManager:
    """Get the global language register manager instance."""
    global _register_manager
    if _register_manager is None:
        _register_manager = LanguageRegisterManager()
    return _register_manager