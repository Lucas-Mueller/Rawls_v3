"""
Locale Manager for Regional Format Handling

Provides locale-aware parsing and formatting for multilingual Phase 2 operations.
Handles regional variations in number formats, currency symbols, date formats,
and cultural context without hardcoded assumptions.

Supported Locales:
- US: English, USD, MM/DD/YYYY, comma thousands separator
- EU: European languages, EUR, DD/MM/YYYY, period thousands separator  
- ES: Spanish, various currencies, DD/MM/YYYY
- CN: Chinese, CNY/RMB, YYYY-MM-DD, mixed number formats
- MX: Spanish (Mexican), MXN/Peso, DD/MM/YYYY

This module integrates with the existing LanguageManager to provide
comprehensive regional support for the Frohlich Experiment system.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from utils.language_manager import SupportedLanguage

logger = logging.getLogger(__name__)


class SupportedLocale(Enum):
    """Supported locale configurations."""
    US_ENGLISH = "en_US"
    EUROPEAN_ENGLISH = "en_EU"
    SPANISH_SPAIN = "es_ES"
    SPANISH_MEXICO = "es_MX"
    SPANISH_ARGENTINA = "es_AR"
    CHINESE_SIMPLIFIED = "zh_CN"
    CHINESE_TRADITIONAL = "zh_TW"


@dataclass
class LocaleConfiguration:
    """Configuration for a specific locale."""
    locale_code: str
    language: SupportedLanguage
    currency_symbol: str
    currency_codes: List[str]
    number_thousands_separator: str
    number_decimal_separator: str
    date_format: str
    currency_position: str  # "prefix" or "suffix"
    formal_default: bool  # Whether formal language is default
    

class LocaleManager:
    """Manages locale-specific formatting and parsing rules."""
    
    def __init__(self):
        """Initialize the locale manager with predefined configurations."""
        self.locale_configs = self._initialize_locale_configs()
        self.current_locale = SupportedLocale.US_ENGLISH
        self._currency_detection_patterns = self._build_currency_patterns()
        self._number_parsing_patterns = self._build_number_patterns()
    
    def _initialize_locale_configs(self) -> Dict[SupportedLocale, LocaleConfiguration]:
        """Initialize predefined locale configurations."""
        return {
            SupportedLocale.US_ENGLISH: LocaleConfiguration(
                locale_code="en_US",
                language=SupportedLanguage.ENGLISH,
                currency_symbol="$",
                currency_codes=["USD", "US$"],
                number_thousands_separator=",",
                number_decimal_separator=".",
                date_format="%m/%d/%Y",
                currency_position="prefix",
                formal_default=False
            ),
            
            SupportedLocale.EUROPEAN_ENGLISH: LocaleConfiguration(
                locale_code="en_EU", 
                language=SupportedLanguage.ENGLISH,
                currency_symbol="€",
                currency_codes=["EUR"],
                number_thousands_separator=".",
                number_decimal_separator=",",
                date_format="%d/%m/%Y",
                currency_position="prefix",
                formal_default=True
            ),
            
            SupportedLocale.SPANISH_SPAIN: LocaleConfiguration(
                locale_code="es_ES",
                language=SupportedLanguage.SPANISH,
                currency_symbol="€",
                currency_codes=["EUR"],
                number_thousands_separator=".",
                number_decimal_separator=",",
                date_format="%d/%m/%Y", 
                currency_position="prefix",
                formal_default=True
            ),
            
            SupportedLocale.SPANISH_MEXICO: LocaleConfiguration(
                locale_code="es_MX",
                language=SupportedLanguage.SPANISH,
                currency_symbol="$",
                currency_codes=["MXN", "peso", "pesos"],
                number_thousands_separator=",",
                number_decimal_separator=".",
                date_format="%d/%m/%Y",
                currency_position="prefix",
                formal_default=False
            ),
            
            SupportedLocale.SPANISH_ARGENTINA: LocaleConfiguration(
                locale_code="es_AR",
                language=SupportedLanguage.SPANISH,
                currency_symbol="$",
                currency_codes=["ARS", "peso", "pesos"],
                number_thousands_separator=".",
                number_decimal_separator=",",
                date_format="%d/%m/%Y",
                currency_position="prefix",
                formal_default=False
            ),
            
            SupportedLocale.CHINESE_SIMPLIFIED: LocaleConfiguration(
                locale_code="zh_CN",
                language=SupportedLanguage.MANDARIN,
                currency_symbol="¥",
                currency_codes=["CNY", "RMB", "元"],
                number_thousands_separator=",",
                number_decimal_separator=".",
                date_format="%Y-%m-%d",
                currency_position="prefix",
                formal_default=True
            ),
            
            SupportedLocale.CHINESE_TRADITIONAL: LocaleConfiguration(
                locale_code="zh_TW",
                language=SupportedLanguage.MANDARIN,
                currency_symbol="¥",
                currency_codes=["CNY", "RMB", "元"],
                number_thousands_separator=",",
                number_decimal_separator=".",
                date_format="%Y-%m-%d",
                currency_position="prefix",
                formal_default=True
            ),
        }
    
    def _build_currency_patterns(self) -> Dict[str, List[str]]:
        """Build currency detection patterns for all locales."""
        patterns = {}
        
        for locale, config in self.locale_configs.items():
            locale_patterns = [config.currency_symbol]
            locale_patterns.extend(config.currency_codes)
            patterns[locale.value] = locale_patterns
            
        return patterns
    
    def _build_number_patterns(self) -> Dict[str, Dict[str, str]]:
        """Build number parsing patterns for all locales."""
        patterns = {}
        
        for locale, config in self.locale_configs.items():
            patterns[locale.value] = {
                "thousands_sep": config.number_thousands_separator,
                "decimal_sep": config.number_decimal_separator,
                "currency_symbol": config.currency_symbol,
                "currency_position": config.currency_position
            }
            
        return patterns
    
    def set_locale(self, locale: SupportedLocale) -> None:
        """
        Set the current locale for formatting and parsing.
        
        Args:
            locale: The locale to use for all operations
        """
        if locale not in self.locale_configs:
            raise ValueError(f"Unsupported locale: {locale}")
        
        self.current_locale = locale
        logger.info(f"Locale set to: {locale.value}")
    
    def get_current_config(self) -> LocaleConfiguration:
        """Get the configuration for the current locale."""
        return self.locale_configs[self.current_locale]
    
    def detect_locale_from_text(self, text: str) -> Optional[SupportedLocale]:
        """
        Detect the most likely locale based on text content.
        
        Args:
            text: Text to analyze for locale indicators
            
        Returns:
            Most likely locale, or None if cannot determine
        """
        text_lower = text.lower()
        locale_scores = {}
        
        # Score based on currency symbols and codes
        for locale, config in self.locale_configs.items():
            score = 0
            
            # Currency symbol detection
            if config.currency_symbol in text:
                score += 3
                
            # Currency code detection  
            for code in config.currency_codes:
                if code.lower() in text_lower:
                    score += 2
                    
            # Language-specific terms
            if locale.value.startswith("es_"):
                spanish_terms = ["restricción", "límite", "peso", "euro", "dólar"]
                for term in spanish_terms:
                    if term in text_lower:
                        score += 1
                        
            elif locale.value.startswith("zh_"):
                # Chinese characters detection
                chinese_chars = ["约束", "限制", "元", "收入", "最大化"]
                for char in chinese_chars:
                    if char in text:
                        score += 2
                        
            # Number format hints
            if "." in text and "," in text:
                # Determine which is thousands vs decimal separator
                parts = text.split()
                for part in parts:
                    if re.match(r'\d{1,3}\.\d{3},\d{2}', part):  # European style
                        if config.number_thousands_separator == "." and config.number_decimal_separator == ",":
                            score += 2
                    elif re.match(r'\d{1,3},\d{3}\.\d{2}', part):  # US style
                        if config.number_thousands_separator == "," and config.number_decimal_separator == ".":
                            score += 2
                            
            locale_scores[locale] = score
        
        # Return locale with highest score, or None if no clear winner
        if locale_scores:
            best_locale = max(locale_scores, key=locale_scores.get)
            if locale_scores[best_locale] > 0:
                return best_locale
                
        return None
    
    def parse_currency_amount(self, text: str, target_locale: Optional[SupportedLocale] = None) -> Optional[Tuple[float, str]]:
        """
        Parse currency amount from text using locale-specific rules.
        
        Args:
            text: Text containing currency amount
            target_locale: Specific locale to use, or None for auto-detection
            
        Returns:
            Tuple of (amount, currency_code) or None if parsing fails
        """
        if target_locale is None:
            target_locale = self.detect_locale_from_text(text) or self.current_locale
            
        config = self.locale_configs[target_locale]
        
        # Build comprehensive currency pattern
        currency_symbols = [re.escape(config.currency_symbol)]
        currency_symbols.extend([re.escape(code) for code in config.currency_codes])
        currency_pattern = "|".join(currency_symbols)
        
        # Build number pattern based on locale
        if config.number_thousands_separator == "," and config.number_decimal_separator == ".":
            # US style: 1,234.56
            number_pattern = r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        elif config.number_thousands_separator == "." and config.number_decimal_separator == ",":
            # European style: 1.234,56
            number_pattern = r'\d{1,3}(?:\.\d{3})*(?:,\d{2})?'
        else:
            # Fallback: simple number
            number_pattern = r'\d+(?:[.,]\d{2})?'
        
        # Try different currency position patterns
        patterns = [
            fr'({currency_pattern})\s*({number_pattern})',  # Prefix: $1,234
            fr'({number_pattern})\s*({currency_pattern})',  # Suffix: 1,234$
            fr'({number_pattern})\s+({currency_pattern})',  # Suffix with space: 1,234 USD
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                # Determine which group is currency and which is number
                currency_part = None
                number_part = None
                
                for group in groups:
                    if re.match(fr'^({currency_pattern})$', group, re.IGNORECASE):
                        currency_part = group
                    elif re.match(fr'^({number_pattern})$', group):
                        number_part = group
                
                if currency_part and number_part:
                    # Parse the number according to locale rules
                    try:
                        amount = self._parse_number_by_locale(number_part, config)
                        currency_code = self._normalize_currency_code(currency_part, config)
                        return (amount, currency_code)
                    except ValueError:
                        continue
        
        return None
    
    def _parse_number_by_locale(self, number_text: str, config: LocaleConfiguration) -> float:
        """Parse number text according to locale configuration."""
        # Remove spaces
        clean_text = number_text.replace(" ", "")
        
        if config.number_thousands_separator == "," and config.number_decimal_separator == ".":
            # US style: remove commas, parse with period as decimal
            clean_text = clean_text.replace(",", "")
            return float(clean_text)
            
        elif config.number_thousands_separator == "." and config.number_decimal_separator == ",":
            # European style: remove periods (thousands), replace comma with period (decimal)
            # Handle cases like 1.234,56
            if "," in clean_text:
                parts = clean_text.rsplit(",", 1)  # Split on last comma
                if len(parts) == 2:
                    integer_part = parts[0].replace(".", "")  # Remove thousand separators
                    decimal_part = parts[1]
                    clean_text = f"{integer_part}.{decimal_part}"
                    return float(clean_text)
            else:
                # No decimal part, just remove periods
                clean_text = clean_text.replace(".", "")
                return float(clean_text)
        
        # Fallback: try to parse as-is
        try:
            return float(clean_text)
        except ValueError:
            # Try removing all non-digit characters except last period or comma
            digits_only = re.sub(r'[^\d.,]', '', clean_text)
            if '.' in digits_only and ',' in digits_only:
                # Assume last separator is decimal
                if digits_only.rfind('.') > digits_only.rfind(','):
                    digits_only = digits_only.replace(',', '')
                else:
                    digits_only = digits_only.replace('.', '').replace(',', '.')
            elif ',' in digits_only:
                # Assume comma is decimal if only 1-2 digits after it
                comma_pos = digits_only.rfind(',')
                if len(digits_only) - comma_pos - 1 <= 2:
                    digits_only = digits_only.replace(',', '.')
                else:
                    digits_only = digits_only.replace(',', '')
                    
            return float(digits_only)
    
    def _normalize_currency_code(self, currency_text: str, config: LocaleConfiguration) -> str:
        """Normalize currency text to standard currency code."""
        currency_lower = currency_text.lower()
        
        # Map symbols and codes to standard codes
        currency_mapping = {
            "$": "USD",  # Default assumption for $
            "€": "EUR",
            "¥": "CNY",
            "£": "GBP",
            "usd": "USD",
            "eur": "EUR", 
            "cny": "CNY",
            "rmb": "CNY",
            "mxn": "MXN",
            "ars": "ARS",
            "cop": "COP",
            "clp": "CLP",
            "元": "CNY",
            "peso": "MXN",  # Default assumption
            "pesos": "MXN",
        }
        
        # Check for specific locale currency codes first
        for code in config.currency_codes:
            if code.lower() == currency_lower:
                if code.upper() in ["USD", "EUR", "CNY", "MXN", "ARS", "COP", "CLP"]:
                    return code.upper()
                elif code.lower() in ["rmb", "元"]:
                    return "CNY"
                elif code.lower() in ["peso", "pesos"]:
                    return "MXN"  # Default to Mexican peso
        
        # Fallback to general mapping
        return currency_mapping.get(currency_lower, currency_text.upper())
    
    def parse_chinese_number_units(self, text: str) -> Optional[float]:
        """
        Parse Chinese number units (万, 千) to numeric values.
        
        Args:
            text: Text containing Chinese number units
            
        Returns:
            Numeric value or None if parsing fails
        """
        # Chinese number unit patterns
        patterns = [
            (r'(\d+)万(\d+)千', lambda m: int(m.group(1)) * 10000 + int(m.group(2)) * 1000),
            (r'(\d+)万', lambda m: int(m.group(1)) * 10000),
            (r'(\d+)千', lambda m: int(m.group(1)) * 1000),
            (r'(\d+)百', lambda m: int(m.group(1)) * 100),
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(converter(match))
                except ValueError:
                    continue
                    
        return None
    
    def format_currency_amount(self, amount: float, currency_code: str, target_locale: Optional[SupportedLocale] = None) -> str:
        """
        Format currency amount according to locale rules.
        
        Args:
            amount: Numeric amount to format
            currency_code: Currency code (USD, EUR, CNY, etc.)
            target_locale: Target locale, or None for current locale
            
        Returns:
            Formatted currency string
        """
        if target_locale is None:
            target_locale = self.current_locale
            
        config = self.locale_configs[target_locale]
        
        # Format number according to locale
        if config.number_thousands_separator == "," and config.number_decimal_separator == ".":
            # US style
            if amount.is_integer():
                formatted_number = f"{int(amount):,}"
            else:
                formatted_number = f"{amount:,.2f}"
        elif config.number_thousands_separator == "." and config.number_decimal_separator == ",":
            # European style
            if amount.is_integer():
                formatted_number = f"{int(amount):,}".replace(",", ".")
            else:
                formatted_number = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            # Simple format
            formatted_number = f"{amount:,.0f}" if amount.is_integer() else f"{amount:.2f}"
        
        # Add currency symbol/code
        currency_symbol = self._get_currency_symbol(currency_code, config)
        
        if config.currency_position == "prefix":
            return f"{currency_symbol}{formatted_number}"
        else:
            return f"{formatted_number} {currency_symbol}"
    
    def _get_currency_symbol(self, currency_code: str, config: LocaleConfiguration) -> str:
        """Get appropriate currency symbol for the given code and locale."""
        code_to_symbol = {
            "USD": "$",
            "EUR": "€",
            "CNY": "¥",
            "MXN": "$",
            "ARS": "$",
            "COP": "$",
            "GBP": "£",
        }
        
        # Prefer locale's default symbol if it matches the currency
        if currency_code in config.currency_codes or code_to_symbol.get(currency_code) == config.currency_symbol:
            return config.currency_symbol
        
        # Otherwise use standard symbol or code
        return code_to_symbol.get(currency_code, currency_code)
    
    def is_formal_language_expected(self, locale: Optional[SupportedLocale] = None) -> bool:
        """
        Check if formal language is expected by default in the locale.
        
        Args:
            locale: Target locale, or None for current locale
            
        Returns:
            True if formal language is culturally expected
        """
        if locale is None:
            locale = self.current_locale
            
        return self.locale_configs[locale].formal_default
    
    def get_supported_locales_for_language(self, language: SupportedLanguage) -> List[SupportedLocale]:
        """
        Get all supported locales for a given language.
        
        Args:
            language: Target language
            
        Returns:
            List of locales that use the given language
        """
        matching_locales = []
        
        for locale, config in self.locale_configs.items():
            if config.language == language:
                matching_locales.append(locale)
                
        return matching_locales


# Global instance for easy access
_global_locale_manager: Optional[LocaleManager] = None


def get_locale_manager() -> LocaleManager:
    """
    Get the global locale manager instance.
    
    Returns:
        Global LocaleManager instance
    """
    global _global_locale_manager
    if _global_locale_manager is None:
        _global_locale_manager = LocaleManager()
    return _global_locale_manager


def set_global_locale(locale: SupportedLocale) -> None:
    """
    Set the locale for the global locale manager.
    
    Args:
        locale: Locale to set globally
    """
    manager = get_locale_manager()
    manager.set_locale(locale)


def parse_currency_amount_global(text: str) -> Optional[Tuple[float, str]]:
    """
    Parse currency amount using the global locale manager.
    
    Args:
        text: Text containing currency amount
        
    Returns:
        Tuple of (amount, currency_code) or None if parsing fails
    """
    manager = get_locale_manager()
    return manager.parse_currency_amount(text)


def detect_locale_from_text_global(text: str) -> Optional[SupportedLocale]:
    """
    Detect locale from text using the global locale manager.
    
    Args:
        text: Text to analyze
        
    Returns:
        Most likely locale or None
    """
    manager = get_locale_manager()
    return manager.detect_locale_from_text(text)