"""
Cultural Adaptation Manager for Two-Stage Voting System

This module provides cultural adaptation functions for multilingual support,
specifically handling amount formatting and language register adjustments
across different cultures and languages.
"""

import logging
import re
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
        Enhanced to extract amounts from verbose text responses.
        
        Args:
            input_str: Raw input string to parse
            
        Returns:
            Tuple of (parsed_amount, error_message). Amount is None if invalid.
        """
        if not input_str or not input_str.strip():
            return None, "empty_amount_response"
        
        # First try: Direct parsing (existing logic for clean inputs)
        result = self._try_direct_parsing(input_str.strip())
        if result[0] is not None:
            return result
        
        # Second try: Extract from verbose text if direct parsing failed
        return self._extract_amount_from_text(input_str)
    
    def _try_direct_parsing(self, input_str: str) -> tuple[Optional[int], Optional[str]]:
        """
        Try direct parsing of clean amount inputs (existing logic).
        """
        # Clean the input - remove common currency symbols and whitespace
        cleaned = input_str.replace("$", "").replace("¥", "").replace("€", "")
        
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
            
            return self._validate_amount_range(amount)
            
        except (ValueError, TypeError):
            return None, "direct_parsing_failed"  # Internal error, will try text extraction
    
    def _extract_amount_from_text(self, text: str) -> tuple[Optional[int], Optional[str]]:
        """
        Extract monetary amounts from verbose text using simplified robust approach.
        Extracts all numbers, normalizes them, and deduplicates identical values.
        """
        # Use a comprehensive approach to find all potential amounts
        normalized_amounts = []
        
        # Pattern 1: Currency symbol with number and optional k
        currency_k_matches = re.finditer(r'[$¥€]\s*(\d[\d,.]*)\s*k\b', text, re.IGNORECASE)
        for match in currency_k_matches:
            amount = self._normalize_and_validate_number(match.group(1), multiply_k=True)
            if amount:
                normalized_amounts.append(amount)
        
        # Pattern 2: Currency symbol with number (no k)  
        currency_matches = re.finditer(r'[$¥€]\s*(\d[\d,.]*)', text, re.IGNORECASE)
        for match in currency_matches:
            # Skip if this was already handled by k pattern
            if not re.search(r'k\b', text[match.end():match.end()+5], re.IGNORECASE):
                amount = self._normalize_and_validate_number(match.group(1))
                if amount:
                    normalized_amounts.append(amount)
        
        # Pattern 3: Number with currency word and optional k
        word_k_matches = re.finditer(r'(\d[\d,.]*)\s*k?\s*(?:dollars?|dólares?|美元|元|USD)\b', text, re.IGNORECASE)
        for match in word_k_matches:
            has_k = 'k' in match.group(0).lower()
            amount = self._normalize_and_validate_number(match.group(1), multiply_k=has_k)
            if amount:
                normalized_amounts.append(amount)
        
        # Pattern 4: Standalone numbers with k
        standalone_k_matches = re.finditer(r'\b(\d[\d,.]*)\s*k\b', text, re.IGNORECASE)
        for match in standalone_k_matches:
            # Only if it's not already covered by currency patterns
            start, end = match.span()
            if not re.search(r'[$¥€]', text[max(0, start-10):start]):
                amount = self._normalize_and_validate_number(match.group(1), multiply_k=True)
                if amount:
                    normalized_amounts.append(amount)
        
        # Pattern 5: Standalone numbers (4+ digits, context-aware)
        standalone_matches = re.finditer(r'\b(\d{4,}[\d,.]*)\b', text, re.IGNORECASE)
        for match in standalone_matches:
            number_str = match.group(1)
            
            # Skip obvious years (1900-2099)
            try:
                num_val = int(number_str.replace(',', '').replace('.', ''))
                if 1900 <= num_val <= 2099:
                    continue
            except ValueError:
                pass
            
            # Skip if near "page", "year", etc.
            context = text[max(0, match.start()-20):match.end()+20].lower()
            if any(word in context for word in ['page', 'year', 'chapter', 'section', 'verse']):
                continue
                
            # Include if in monetary context or seems like a monetary amount
            monetary_context_words = ['constraint', 'amount', 'dollar', 'income', 'floor', 'limit', 'thinking', 'choose', 'prefer', 'select']
            if any(word in context for word in monetary_context_words):
                amount = self._normalize_and_validate_number(number_str)
                if amount:
                    normalized_amounts.append(amount)
        
        # Also try Chinese number extraction if Chinese characters present
        if re.search(r'[\u4e00-\u9fff]', text):
            chinese_amounts = self._extract_chinese_amounts(text)
            normalized_amounts.extend(chinese_amounts)
        
        # Evaluate extracted amounts
        return self._evaluate_extracted_amounts(normalized_amounts)
    
    def _normalize_and_validate_number(self, number_str: str, multiply_k: bool = False) -> Optional[int]:
        """
        Helper method to normalize and validate a number string.
        Returns the integer value if valid, None otherwise.
        """
        try:
            # Clean the number: remove commas and handle periods
            cleaned = number_str.replace(',', '')
            
            # Handle periods - assume decimal if ≤2 digits after period, else remove
            if '.' in cleaned:
                parts = cleaned.split('.')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Decimal format
                    amount = int(float(cleaned))
                else:
                    # Thousand separator format - remove periods
                    amount = int(cleaned.replace('.', ''))
            else:
                amount = int(cleaned)
            
            # Apply k multiplier if needed
            if multiply_k:
                amount *= 1000
            
            # Filter to reasonable amounts
            if 100 <= amount <= 1000000:
                return amount
            
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _extract_chinese_amounts(self, text: str) -> list[int]:
        """
        Extract amounts from Chinese text using non-overlapping approach.
        Process in order of complexity to avoid double-counting.
        """
        amounts = []
        processed_positions = set()  # Track processed character positions
        
        # Pattern 1: Mixed Arabic-Chinese numbers (like 15万) - highest priority
        mixed_pattern = r'(\d+万)(?:\s*(?:美元|元|块))?'
        for match in re.finditer(mixed_pattern, text):
            start, end = match.span()
            if not any(pos in processed_positions for pos in range(start, end)):
                # Extract the number before 万
                num_part = match.group(1).replace('万', '')
                try:
                    base_num = int(num_part)
                    amount = base_num * 10000
                    if 100 <= amount <= 1000000:
                        amounts.append(amount)
                        processed_positions.update(range(start, end))
                except ValueError:
                    continue
        
        # Pattern 2: Complex Chinese numbers like "二万五千美元" - second priority  
        complex_pattern = r'([一二三四五六七八九十万千百]+)(?:\s*(?:美元|元|块))'
        for match in re.finditer(complex_pattern, text):
            start, end = match.span()
            if not any(pos in processed_positions for pos in range(start, end)):
                amount = self._convert_chinese_number(match.group(1))
                if amount and 100 <= amount <= 1000000:
                    amounts.append(amount)
                    processed_positions.update(range(start, end))
        
        # Pattern 3: Simple Chinese numbers with currency - third priority
        simple_patterns = [
            r'([一二三四五六七八九十]+万)(?:\s*(?:美元|元|块))?',  # X万 pattern
            r'([一二三四五六七八九十]+千)(?:\s*(?:美元|元|块))?',  # X千 pattern  
        ]
        
        for pattern in simple_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                if not any(pos in processed_positions for pos in range(start, end)):
                    amount = self._convert_chinese_number(match.group(1))
                    if amount and 100 <= amount <= 1000000:
                        amounts.append(amount)
                        processed_positions.update(range(start, end))
        
        # Pattern 4: Pure Arabic numerals (lowest priority, only if no Chinese context)
        if not amounts:  # Only if we haven't found any Chinese-style amounts
            arabic_pattern = r'(\d{3,})(?:\s*(?:美元|元|块|人民币))'
            for match in re.finditer(arabic_pattern, text):
                start, end = match.span() 
                if not any(pos in processed_positions for pos in range(start, end)):
                    try:
                        amount = int(match.group(1))
                        if 100 <= amount <= 1000000:
                            amounts.append(amount)
                            processed_positions.update(range(start, end))
                    except ValueError:
                        continue
        
        return amounts
    
    def _convert_chinese_number(self, chinese_num: str) -> Optional[int]:
        """
        Convert basic Chinese numbers to integers using simplified approach.
        Handles common patterns like 一万, 五千, 十五万, etc.
        """
        # Basic digit mappings
        digit_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        try:
            # Handle 万 (10,000) patterns
            if '万' in chinese_num:
                base_part = chinese_num.replace('万', '')
                if not base_part:  # Just '万' 
                    return 10000
                elif base_part in digit_map:
                    return digit_map[base_part] * 10000
                elif base_part == '十':
                    return 100000
                elif base_part == '十五':  # 十五万 = 150000
                    return 150000
                else:
                    # Try to parse complex patterns like "二万五千"
                    # First check if there's a 千 part after 万
                    remaining = chinese_num
                    total = 0
                    
                    # Extract 万 part
                    if '万' in remaining:
                        parts = remaining.split('万')
                        wan_part = parts[0]
                        if wan_part in digit_map:
                            total += digit_map[wan_part] * 10000
                        remaining = parts[1] if len(parts) > 1 else ''
                    
                    # Extract 千 part  
                    if '千' in remaining:
                        parts = remaining.split('千')
                        qian_part = parts[0]
                        if qian_part in digit_map:
                            total += digit_map[qian_part] * 1000
                        remaining = parts[1] if len(parts) > 1 else ''
                    
                    # Extract 百 part
                    if '百' in remaining:
                        parts = remaining.split('百')
                        bai_part = parts[0]  
                        if bai_part in digit_map:
                            total += digit_map[bai_part] * 100
                        remaining = parts[1] if len(parts) > 1 else ''
                    
                    # Extract remaining digits
                    if remaining and remaining in digit_map:
                        total += digit_map[remaining]
                    
                    return total if total > 0 else None
            
            # Handle 千 (1,000) patterns  
            elif '千' in chinese_num:
                base_part = chinese_num.replace('千', '')
                if not base_part:  # Just '千'
                    return 1000
                elif base_part in digit_map:
                    return digit_map[base_part] * 1000
                elif base_part == '十':
                    return 10000
                elif len(base_part) == 2:  # Try two-digit combinations
                    if base_part[0] in digit_map and base_part[1] in digit_map:
                        return (digit_map[base_part[0]] * 10 + digit_map[base_part[1]]) * 1000
            
            # Handle 百 (100) patterns
            elif '百' in chinese_num:
                base_part = chinese_num.replace('百', '')
                if not base_part:
                    return 100
                elif base_part in digit_map:
                    return digit_map[base_part] * 100
            
        except (KeyError, ValueError):
            pass
        
        # Return None for patterns we can't parse
        return None
    
    def _evaluate_extracted_amounts(self, amounts: list[int]) -> tuple[Optional[int], Optional[str]]:
        """
        Evaluate a list of extracted amounts with deduplication of identical values.
        This implements the simplified logic: if same number appears multiple times, 
        use it once. Only fail if truly different amounts are found.
        """
        if not amounts:
            return None, "no_amount_found"
        
        # Remove duplicates - if same amount appears multiple times, that's fine
        unique_amounts = list(set(amounts))
        
        if len(unique_amounts) == 1:
            # Single unique amount found (possibly repeated in text)
            return self._validate_amount_range(unique_amounts[0])
        
        # Multiple different amounts found - this is ambiguous
        return None, "multiple_different_amounts_found"
    
    def _validate_amount_range(self, amount: int) -> tuple[Optional[int], Optional[str]]:
        """
        Validate that an amount is within acceptable range.
        """
        if amount <= 0:
            return None, "amount_must_be_positive"
        elif amount > 1000000:  # 1 million cap for reasonableness
            return None, "amount_too_high"
        elif amount < 1:
            return None, "amount_too_low"
        
        return amount, None


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