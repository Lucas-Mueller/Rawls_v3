"""
Principle Name Manager for Two-Stage Voting System

This module manages principle name translations and display for the two-stage
voting system, providing consistent principle naming across all supported languages.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from utils.language_manager import SupportedLanguage
from utils.cultural_adaptation import get_amount_formatter, SupportedLanguage as CulturalLanguage

logger = logging.getLogger(__name__)


class PrincipleNumber(Enum):
    """Enumeration mapping principle numbers to their types."""
    ONE = 1      # Maximizing Floor Income
    TWO = 2      # Maximizing Average Income  
    THREE = 3    # Maximizing Average with Floor Constraint
    FOUR = 4     # Maximizing Average with Range Constraint


class PrincipleNameManager:
    """
    Manages principle name translations and formatting for two-stage voting.
    
    Provides centralized management of principle names, descriptions, and
    menu formatting across all supported languages.
    """
    
    def __init__(self, language_manager: Any = None):
        """
        Initialize the principle name manager.
        
        Args:
            language_manager: LanguageManager instance, uses global if None
        """
        self.language_manager = language_manager
        self.amount_formatter = get_amount_formatter()
        
        # Principle key mappings (from language manager)
        self.principle_keys = {
            PrincipleNumber.ONE: "maximizing_floor",
            PrincipleNumber.TWO: "maximizing_average", 
            PrincipleNumber.THREE: "maximizing_average_floor_constraint",
            PrincipleNumber.FOUR: "maximizing_average_range_constraint"
        }
        
        # Principles that require constraint amounts
        self.constraint_principles = {PrincipleNumber.THREE, PrincipleNumber.FOUR}
        
        # Cache for translated names to improve performance
        self._name_cache = {}
    
    def get_principle_display_name(self, principle_num: int, language: Optional[SupportedLanguage] = None) -> str:
        """
        Get the localized display name for a principle.
        
        Args:
            principle_num: Principle number (1-4)
            language: Target language, uses current language if None
            
        Returns:
            Translated principle name
            
        Raises:
            ValueError: If principle_num is invalid
        """
        if principle_num not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid principle number: {principle_num}. Must be 1-4.")
        
        principle_enum = PrincipleNumber(principle_num)
        
        # Use current language if none specified
        if language is None:
            language = self.language_manager.current_language
        
        # Check cache first
        cache_key = (principle_enum, language)
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        # Get principle key and retrieve translation
        principle_key = self.principle_keys[principle_enum]
        
        try:
            # Get translated name from language manager
            translated_name = self.language_manager.get_justice_principle_name(principle_key)
            
            # Cache the result
            self._name_cache[cache_key] = translated_name
            
            return translated_name
            
        except Exception as e:
            logger.warning(f"Failed to get translated name for principle {principle_num}: {e}")
            # Fallback to English names
            fallback_names = {
                PrincipleNumber.ONE: "Maximizing Floor Income",
                PrincipleNumber.TWO: "Maximizing Average Income",
                PrincipleNumber.THREE: "Maximizing Average with Floor Constraint",
                PrincipleNumber.FOUR: "Maximizing Average with Range Constraint"
            }
            return fallback_names[principle_enum]
    
    def get_principle_menu_text(self, language: Optional[SupportedLanguage] = None) -> str:
        """
        Get the complete principle selection menu text for two-stage voting.
        
        Args:
            language: Target language, uses current language if None
            
        Returns:
            Formatted menu text with numbered options
        """
        if language is None:
            language = self.language_manager.current_language
        
        menu_lines = []
        for num in [1, 2, 3, 4]:
            principle_name = self.get_principle_display_name(num, language)
            menu_lines.append(f"{num}. {principle_name}")
        
        return "\n".join(menu_lines)
    
    def get_principle_description(self, principle_num: int, 
                                 language: Optional[SupportedLanguage] = None,
                                 include_constraint_note: bool = True) -> str:
        """
        Get a detailed description of a principle.
        
        Args:
            principle_num: Principle number (1-4)
            language: Target language, uses current language if None  
            include_constraint_note: Whether to include constraint requirement note
            
        Returns:
            Detailed principle description
        """
        if language is None:
            language = self.language_manager.current_language
        
        principle_name = self.get_principle_display_name(principle_num, language)
        
        # Map to cultural language enum for amount formatting
        cultural_lang = self._map_to_cultural_language(language)
        
        # Base descriptions by principle
        if principle_num == 1:
            description = self._get_floor_description(language)
        elif principle_num == 2:
            description = self._get_average_description(language)
        elif principle_num == 3:
            description = self._get_floor_constraint_description(language, include_constraint_note)
        elif principle_num == 4:
            description = self._get_range_constraint_description(language, include_constraint_note)
        else:
            raise ValueError(f"Invalid principle number: {principle_num}")
        
        return f"**{principle_name}**: {description}"
    
    def requires_constraint_amount(self, principle_num: int) -> bool:
        """
        Check if a principle requires a constraint amount specification.
        
        Args:
            principle_num: Principle number (1-4)
            
        Returns:
            True if principle requires constraint amount
        """
        if principle_num not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid principle number: {principle_num}")
        
        return PrincipleNumber(principle_num) in self.constraint_principles
    
    def get_constraint_type_name(self, principle_num: int, 
                                language: Optional[SupportedLanguage] = None) -> str:
        """
        Get the constraint type name for constrained principles.
        
        Args:
            principle_num: Principle number (must be 3 or 4)
            language: Target language, uses current language if None
            
        Returns:
            Constraint type name (e.g., "floor constraint", "range constraint")
            
        Raises:
            ValueError: If principle doesn't require constraints
        """
        if not self.requires_constraint_amount(principle_num):
            raise ValueError(f"Principle {principle_num} does not require constraints")
        
        if language is None:
            language = self.language_manager.current_language
        
        # Get constraint type names from translations
        if principle_num == 3:
            return self._get_constraint_type_translation("floor", language)
        elif principle_num == 4:
            return self._get_constraint_type_translation("range", language)
    
    def format_principle_with_constraint(self, principle_num: int, constraint_amount: int,
                                       language: Optional[SupportedLanguage] = None) -> str:
        """
        Format a principle choice with its constraint amount.
        
        Args:
            principle_num: Principle number (must be 3 or 4)
            constraint_amount: Dollar amount for constraint
            language: Target language, uses current language if None
            
        Returns:
            Formatted principle choice with constraint
            
        Raises:
            ValueError: If principle doesn't require constraints
        """
        if not self.requires_constraint_amount(principle_num):
            raise ValueError(f"Principle {principle_num} does not require constraints")
        
        if language is None:
            language = self.language_manager.current_language
        
        principle_name = self.get_principle_display_name(principle_num, language)
        constraint_type = self.get_constraint_type_name(principle_num, language)
        
        # Map to cultural language and format amount
        cultural_lang = self._map_to_cultural_language(language) 
        formatted_amount = self.amount_formatter.format_amount(constraint_amount, cultural_lang)
        
        # Create formatted string based on language
        if language == SupportedLanguage.ENGLISH:
            return f"{principle_name} with a {constraint_type} of {formatted_amount}"
        elif language == SupportedLanguage.SPANISH:
            return f"{principle_name} con una restricción de {constraint_type} de {formatted_amount}"
        elif language == SupportedLanguage.MANDARIN:
            if principle_num == 3:
                return f"{principle_name}，最低收入约束为{formatted_amount}"
            else:  # principle_num == 4
                return f"{principle_name}，收入范围约束为{formatted_amount}"
        
        # Fallback
        return f"{principle_name} ({constraint_type}: {formatted_amount})"
    
    def clear_cache(self):
        """Clear the internal name cache."""
        self._name_cache.clear()
        logger.debug("Principle name cache cleared")
    
    def _map_to_cultural_language(self, language: SupportedLanguage) -> CulturalLanguage:
        """Map LanguageManager language to CulturalLanguage enum."""
        mapping = {
            SupportedLanguage.ENGLISH: CulturalLanguage.ENGLISH,
            SupportedLanguage.SPANISH: CulturalLanguage.SPANISH,
            SupportedLanguage.MANDARIN: CulturalLanguage.MANDARIN
        }
        return mapping.get(language, CulturalLanguage.ENGLISH)
    
    def _get_floor_description(self, language: SupportedLanguage) -> str:
        """Get floor principle description."""
        descriptions = {
            SupportedLanguage.ENGLISH: "Choose the distribution that maximizes the lowest income in society",
            SupportedLanguage.SPANISH: "Elegir la distribución que maximiza el ingreso más bajo en la sociedad", 
            SupportedLanguage.MANDARIN: "选择使社会最低收入最大化的分配方式"
        }
        return descriptions.get(language, descriptions[SupportedLanguage.ENGLISH])
    
    def _get_average_description(self, language: SupportedLanguage) -> str:
        """Get average principle description."""
        descriptions = {
            SupportedLanguage.ENGLISH: "Choose the distribution that maximizes the average income",
            SupportedLanguage.SPANISH: "Elegir la distribución que maximiza el ingreso promedio",
            SupportedLanguage.MANDARIN: "选择使平均收入最大化的分配"
        }
        return descriptions.get(language, descriptions[SupportedLanguage.ENGLISH])
    
    def _get_floor_constraint_description(self, language: SupportedLanguage, include_note: bool) -> str:
        """Get floor constraint principle description."""
        base_descriptions = {
            SupportedLanguage.ENGLISH: "Maximize average income while ensuring everyone gets at least a specified minimum",
            SupportedLanguage.SPANISH: "Maximizar el ingreso promedio mientras se asegura que todos obtengan al menos un mínimo especificado",
            SupportedLanguage.MANDARIN: "在确保每个人至少获得规定的最低收入的同时最大化平均收入"
        }
        
        if not include_note:
            return base_descriptions.get(language, base_descriptions[SupportedLanguage.ENGLISH])
        
        constraint_notes = {
            SupportedLanguage.ENGLISH: " (specify amount)",
            SupportedLanguage.SPANISH: " (especificar cantidad)",
            SupportedLanguage.MANDARIN: "（需指定金额）"
        }
        
        base = base_descriptions.get(language, base_descriptions[SupportedLanguage.ENGLISH])
        note = constraint_notes.get(language, constraint_notes[SupportedLanguage.ENGLISH])
        return base + note
    
    def _get_range_constraint_description(self, language: SupportedLanguage, include_note: bool) -> str:
        """Get range constraint principle description."""
        base_descriptions = {
            SupportedLanguage.ENGLISH: "Maximize average income while keeping the gap between richest and poorest within a specified limit",
            SupportedLanguage.SPANISH: "Maximizar el ingreso promedio manteniendo la brecha entre los más ricos y los más pobres dentro de un límite especificado",
            SupportedLanguage.MANDARIN: "在将最富与最穷之间的差距保持在规定限度内的同时最大化平均收入"
        }
        
        if not include_note:
            return base_descriptions.get(language, base_descriptions[SupportedLanguage.ENGLISH])
        
        constraint_notes = {
            SupportedLanguage.ENGLISH: " (specify amount)",
            SupportedLanguage.SPANISH: " (especificar cantidad)", 
            SupportedLanguage.MANDARIN: "（需指定金额）"
        }
        
        base = base_descriptions.get(language, base_descriptions[SupportedLanguage.ENGLISH])
        note = constraint_notes.get(language, constraint_notes[SupportedLanguage.ENGLISH])
        return base + note
    
    def _get_constraint_type_translation(self, constraint_type: str, language: SupportedLanguage) -> str:
        """Get translated constraint type name."""
        translations = {
            "floor": {
                SupportedLanguage.ENGLISH: "floor constraint",
                SupportedLanguage.SPANISH: "restricción de ingreso mínimo",
                SupportedLanguage.MANDARIN: "最低收入约束"
            },
            "range": {
                SupportedLanguage.ENGLISH: "range constraint", 
                SupportedLanguage.SPANISH: "restricción de rango",
                SupportedLanguage.MANDARIN: "范围约束"
            }
        }
        
        type_translations = translations.get(constraint_type, {})
        return type_translations.get(language, f"{constraint_type} constraint")


# Global instance for easy access
_global_principle_name_manager: Optional[PrincipleNameManager] = None


def get_principle_name_manager() -> PrincipleNameManager:
    """
    Get the global principle name manager instance.
    
    Returns:
        Global PrincipleNameManager instance
    """
    global _global_principle_name_manager
    if _global_principle_name_manager is None:
        _global_principle_name_manager = PrincipleNameManager()
    return _global_principle_name_manager


def clear_principle_name_cache():
    """Clear the principle name cache (useful when language changes)."""
    global _global_principle_name_manager
    if _global_principle_name_manager is not None:
        _global_principle_name_manager.clear_cache()