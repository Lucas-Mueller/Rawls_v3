"""
Principle Keywords Mapping System

Provides unified multilingual keyword matching for justice principle identification.
Used as a fallback when numerical input (1-4) fails in the two-stage voting system.
"""

import re
from typing import Optional, Dict, List, Tuple
from enum import Enum


class SupportedLanguage(Enum):
    """Supported languages for keyword matching."""
    ENGLISH = "english"
    SPANISH = "spanish"
    MANDARIN = "mandarin"


# Core principle keyword mappings for all supported languages
PRINCIPLE_KEYWORDS = {
    'english': {
        1: {
            'primary': ['floor', 'minimum', 'lowest', 'bottom'],
            'descriptive': ['worst off', 'most disadvantaged', 'poorest', 'least well off'],
            'phrases': ['maximizing floor', 'maximizing minimum', 'maximizing lowest',
                       'maximize floor income', 'maximize minimum income'],
            'negatives': ['not average', 'not constraint', 'not range']
        },
        2: {
            'primary': ['average', 'mean', 'total'],
            'descriptive': ['aggregate', 'sum', 'overall', 'society total'],
            'phrases': ['maximizing average', 'maximize average income', 'maximizing total',
                       'maximize overall income', 'maximize society income'],
            'negatives': ['not constraint', 'not floor', 'not range', 'no constraint']
        },
        3: {
            'primary': ['floor constraint', 'minimum constraint', 'guaranteed minimum'],
            'descriptive': ['average with floor', 'constrained by floor', 'floor first'],
            'phrases': ['maximizing average with floor constraint', 'maximize average floor constraint',
                       'average income with minimum constraint', 'average subject to floor'],
            'constraint_indicators': ['with floor', 'floor of', 'minimum of', 'guarantee', 'floor constraint']
        },
        4: {
            'primary': ['range constraint', 'gap constraint', 'difference constraint'],
            'descriptive': ['average with range', 'constrained by range', 'limited difference'],
            'phrases': ['maximizing average with range constraint', 'maximize average range constraint',
                       'average income with range limit', 'average subject to range'],
            'constraint_indicators': ['with range', 'range of', 'gap of', 'difference of', 'range constraint']
        }
    },
    
    'spanish': {
        1: {
            'primary': ['mínimo', 'más bajo', 'piso'],
            'descriptive': ['peor situado', 'más desfavorecido', 'más pobre', 'menos favorecido'],
            'phrases': ['maximizar mínimo', 'maximización mínimo', 'maximizar piso',
                       'maximizar ingreso mínimo', 'maximización ingreso mínimo'],
            'negatives': ['no promedio', 'no restricción', 'no rango']
        },
        2: {
            'primary': ['promedio', 'media', 'total'],
            'descriptive': ['agregado', 'suma', 'general', 'total sociedad'],
            'phrases': ['maximizar promedio', 'maximización promedio', 'maximizar total',
                       'maximizar ingreso promedio', 'maximización ingreso promedio'],
            'negatives': ['no restricción', 'no mínimo', 'no rango', 'sin restricción']
        },
        3: {
            'primary': ['restricción mínimo', 'restricción piso', 'mínimo garantizado'],
            'descriptive': ['promedio con mínimo', 'restringido por mínimo', 'mínimo primero'],
            'phrases': ['maximizar promedio con restricción mínimo', 'maximización promedio restricción mínimo',
                       'ingreso promedio con restricción mínima', 'promedio sujeto a mínimo'],
            'constraint_indicators': ['con mínimo', 'mínimo de', 'garantizar', 'restricción mínimo']
        },
        4: {
            'primary': ['restricción rango', 'restricción diferencia', 'restricción brecha'],
            'descriptive': ['promedio con rango', 'restringido por rango', 'diferencia limitada'],
            'phrases': ['maximizar promedio con restricción rango', 'maximización promedio restricción rango',
                       'ingreso promedio con límite rango', 'promedio sujeto a rango'],
            'constraint_indicators': ['con rango', 'rango de', 'brecha de', 'diferencia de', 'restricción rango']
        }
    },
    
    'mandarin': {
        1: {
            'primary': ['最低', '最小', '底线'],
            'descriptive': ['最差', '最弱势', '最贫困', '最不利'],
            'phrases': ['最大化最低', '最低收入最大化', '最大化底线',
                       '最大化最低收入', '最低收入最大化'],
            'negatives': ['非平均', '非约束', '非范围']
        },
        2: {
            'primary': ['平均', '均值', '总体'],
            'descriptive': ['汇总', '总和', '整体', '社会总体'],
            'phrases': ['最大化平均', '平均收入最大化', '最大化总体',
                       '最大化平均收入', '平均收入最大化'],
            'negatives': ['无约束', '非最低', '非范围', '没有约束']
        },
        3: {
            'primary': ['最低约束', '底线约束', '保证最低'],
            'descriptive': ['约束下平均', '最低约束条件', '底线优先'],
            'phrases': ['在最低收入约束条件下最大化平均收入', '最低约束下平均最大化',
                       '约束最低的平均收入', '受最低约束的平均'],
            'constraint_indicators': ['约束条件下', '最低约束', '保证最低', '约束为', '底线约束']
        },
        4: {
            'primary': ['范围约束', '差距约束', '区间约束'],
            'descriptive': ['约束下平均', '范围约束条件', '差距限制'],
            'phrases': ['在范围约束条件下最大化平均收入', '范围约束下平均最大化',
                       '约束范围的平均收入', '受范围约束的平均'],
            'constraint_indicators': ['约束条件下', '范围约束', '差距约束', '约束为', '范围限制']
        }
    }
}


class PrincipleKeywordMatcher:
    """Handles keyword-based principle identification across languages."""
    
    def __init__(self):
        self.keywords = PRINCIPLE_KEYWORDS
        
    def detect_language_from_text(self, text: str) -> SupportedLanguage:
        """
        Attempt to detect language from text content.
        
        Args:
            text: Text to analyze for language indicators
            
        Returns:
            Detected SupportedLanguage enum value, defaults to ENGLISH
        """
        text_lower = text.lower()
        
        # Check for Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return SupportedLanguage.MANDARIN
            
        # Check for Spanish indicators
        spanish_indicators = ['maximizar', 'restricción', 'promedio', 'mínimo', 'ingreso']
        if any(indicator in text_lower for indicator in spanish_indicators):
            return SupportedLanguage.SPANISH
            
        # Default to English
        return SupportedLanguage.ENGLISH
    
    def match_principle_from_keywords(
        self, 
        text: str, 
        language: Optional[SupportedLanguage] = None
    ) -> Tuple[Optional[int], float]:
        """
        Match principle number from text using keyword analysis.
        
        Args:
            text: Text to analyze for principle keywords
            language: Language to use for matching, auto-detected if None
            
        Returns:
            Tuple of (principle_number, confidence_score)
            - principle_number: 1-4 if matched, None if no match
            - confidence_score: 0.0-1.0 indicating match confidence
        """
        if not text:
            return None, 0.0
            
        if language is None:
            language = self.detect_language_from_text(text)
            
        text_lower = text.lower().strip()
        language_key = language.value
        
        if language_key not in self.keywords:
            # Fallback to English if language not supported
            language_key = 'english'
        
        principle_scores = {}
        
        for principle_num in [1, 2, 3, 4]:
            score = self._calculate_principle_score(
                text_lower, 
                self.keywords[language_key][principle_num]
            )
            if score > 0:
                principle_scores[principle_num] = score
        
        if not principle_scores:
            return None, 0.0
            
        # Return principle with highest score
        best_principle = max(principle_scores, key=principle_scores.get)
        best_score = principle_scores[best_principle]
        
        # Only return if confidence is above minimum threshold
        min_confidence = 0.3
        if best_score >= min_confidence:
            return best_principle, best_score
        else:
            return None, best_score
    
    def _calculate_principle_score(self, text: str, keyword_groups: Dict[str, List[str]]) -> float:
        """
        Calculate match score for a specific principle's keywords.
        
        Args:
            text: Lowercase text to analyze
            keyword_groups: Dictionary of keyword categories for the principle
            
        Returns:
            Score between 0.0 and 1.0 indicating match strength
        """
        total_score = 0.0
        max_possible_score = 0.0
        
        # Weight different keyword categories
        weights = {
            'primary': 1.0,
            'descriptive': 0.8,
            'phrases': 1.2,
            'constraint_indicators': 3.0,  # Much higher weight for constraint indicators
            'negatives': -0.5  # Negative weight for exclusion terms
        }
        
        for category, keywords in keyword_groups.items():
            category_weight = weights.get(category, 0.5)
            max_possible_score += abs(category_weight)
            
            for keyword in keywords:
                if keyword.lower() in text:
                    total_score += category_weight
                    # Only count first match in each category to avoid over-weighting
                    break
        
        # Normalize score
        if max_possible_score > 0:
            normalized_score = max(0.0, total_score / max_possible_score)
            return min(1.0, normalized_score)
        else:
            return 0.0
    
    def get_principle_keywords_for_language(self, language: SupportedLanguage) -> Dict[int, Dict[str, List[str]]]:
        """
        Get all principle keywords for a specific language.
        
        Args:
            language: Target language
            
        Returns:
            Dictionary mapping principle numbers to keyword groups
        """
        language_key = language.value
        return self.keywords.get(language_key, self.keywords['english'])
    
    def validate_principle_choice_with_keywords(
        self, 
        text: str, 
        expected_principle: int,
        language: Optional[SupportedLanguage] = None
    ) -> bool:
        """
        Validate that text content matches expected principle choice.
        
        Useful for cross-checking numerical choices against descriptive text.
        
        Args:
            text: Text content to validate
            expected_principle: Expected principle number (1-4)
            language: Language to use for validation
            
        Returns:
            True if text content aligns with expected principle
        """
        detected_principle, confidence = self.match_principle_from_keywords(text, language)
        
        if detected_principle is None:
            return False  # Could not determine principle from text
            
        return detected_principle == expected_principle and confidence >= 0.5


# Global instance for easy import
principle_keyword_matcher = PrincipleKeywordMatcher()


# Convenience functions for easy import
def match_principle_from_text(
    text: str, 
    language: Optional[SupportedLanguage] = None
) -> Tuple[Optional[int], float]:
    """
    Convenience function to match principle from text.
    
    Args:
        text: Text to analyze
        language: Language to use, auto-detected if None
        
    Returns:
        Tuple of (principle_number, confidence_score)
    """
    return principle_keyword_matcher.match_principle_from_keywords(text, language)


def detect_language_from_response(text: str) -> SupportedLanguage:
    """
    Convenience function to detect language from response text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Detected SupportedLanguage
    """
    return principle_keyword_matcher.detect_language_from_text(text)


def get_principle_keywords(language: SupportedLanguage) -> Dict[int, Dict[str, List[str]]]:
    """
    Convenience function to get principle keywords for a language.
    
    Args:
        language: Target language
        
    Returns:
        Dictionary mapping principle numbers to keyword groups
    """
    return principle_keyword_matcher.get_principle_keywords_for_language(language)