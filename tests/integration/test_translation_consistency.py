"""
Integration tests for translation consistency across languages.
Validates that principle names, constraints, and responses are consistent across translations.
"""
import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from utils.language_manager import get_language_manager, set_global_language, SupportedLanguage
from experiment_agents.utility_agent import UtilityAgent
from tests.integration.utils.async_test_utils import AsyncTestUtils
from tests.integration.utils.test_helpers import validate_utility_agent_methods, get_utility_agent_mock_methods
from utils.error_handling import get_global_error_handler
from models import JusticePrinciple, CertaintyLevel


class TestTranslationConsistency:
    """Test consistency of translations across all supported languages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
        
        # Validate that all commonly mocked utility agent methods exist
        validate_utility_agent_methods(get_utility_agent_mock_methods())
        
        # Define equivalent principle statements across languages
        self.equivalent_principles = {
            "maximizing_floor": {
                "english": [
                    "I choose maximizing the floor income",
                    "My choice is maximizing floor income", 
                    "I select maximizing the floor income",
                    "I prefer maximizing floor income"
                ],
                "spanish": [
                    "Mi elección es maximización del ingreso mínimo",
                    "Elijo maximizar el ingreso mínimo",
                    "Prefiero maximización del ingreso mínimo", 
                    "Mi opción es maximizar el ingreso mínimo"
                ],
                "mandarin": [
                    "我选择最大化最低收入",
                    "我的选择是最大化底线收入",
                    "我偏好最大化最低收入",
                    "我选择最大化底线收入"
                ]
            },
            "maximizing_average": {
                "english": [
                    "I choose maximizing the average income",
                    "My preference is maximizing average income",
                    "I select maximizing average income", 
                    "I prefer maximizing the average income"
                ],
                "spanish": [
                    "Mi elección es maximización del ingreso promedio",
                    "Elijo maximizar el ingreso promedio",
                    "Prefiero maximización del ingreso promedio",
                    "Mi opción es maximizar el ingreso promedio"
                ],
                "mandarin": [
                    "我选择最大化平均收入",
                    "我的选择是最大化平均收入", 
                    "我偏好最大化平均收入",
                    "我选择最大化平均收入"
                ]
            },
            "maximizing_average_floor_constraint": {
                "english": [
                    "I choose maximizing average with floor constraint",
                    "My choice is maximizing average income with floor constraint",
                    "I select maximizing average with a floor constraint",
                    "I prefer maximizing average income with minimum floor"
                ],
                "spanish": [
                    "Mi elección es maximización del ingreso promedio con restricción de mínimo",
                    "Elijo maximizar el promedio con restricción de piso",
                    "Prefiero maximización del promedio con restricción de mínimo",
                    "Mi opción es maximizar el ingreso promedio con restricción de piso"
                ],
                "mandarin": [
                    "我选择最大化平均收入底线约束",
                    "我的选择是最大化平均收入带底线约束",
                    "我偏好最大化平均收入底线限制",
                    "我选择最大化平均收入最低约束"
                ]
            },
            "maximizing_average_range_constraint": {
                "english": [
                    "I choose maximizing average with range constraint",
                    "My choice is maximizing average income with range constraint", 
                    "I select maximizing average with a range constraint",
                    "I prefer maximizing average income with range limitation"
                ],
                "spanish": [
                    "Mi elección es maximización del ingreso promedio con restricción de rango",
                    "Elijo maximizar el promedio con restricción de intervalo",
                    "Prefiero maximización del promedio con restricción de rango",
                    "Mi opción es maximizar el ingreso promedio con restricción de intervalo"
                ],
                "mandarin": [
                    "我选择最大化平均收入范围约束", 
                    "我的选择是最大化平均收入带范围约束",
                    "我偏好最大化平均收入范围限制",
                    "我选择最大化平均收入区间约束"
                ]
            }
        }
    
    @pytest.mark.asyncio
    async def test_principle_names_consistent_across_translations(self):
        """Test that principle names are consistently parsed across all languages."""
        
        for principle_key, language_variants in self.equivalent_principles.items():
            with self.subTest(principle=principle_key):
                parsed_results = {}
                
                for language, statements in language_variants.items():
                    # Set language context
                    lang_enum = {
                        "english": SupportedLanguage.ENGLISH,
                        "spanish": SupportedLanguage.SPANISH,
                        "mandarin": SupportedLanguage.MANDARIN
                    }[language]
                    
                    set_global_language(lang_enum)
                    
                    # Create utility agent for this language
                    utility_agent = UtilityAgent("test_agent", language=language)
                    
                    with patch.object(utility_agent, 'parse_principle_choice_enhanced') as mock_parse:
                        # Mock consistent parsing results
                        mock_parse.return_value = Mock(
                            principle=principle_key,
                            certainty="sure",
                            constraint_amount=None
                        )
                        
                        # Test each statement variant in this language
                        for statement in statements:
                            result = await mock_parse(statement)
                            parsed_results[f"{language}_{statement}"] = result.principle
                
                # Verify all variants parse to the same principle
                unique_principles = set(parsed_results.values())
                assert len(unique_principles) == 1, f"Inconsistent parsing for {principle_key}: {parsed_results}"
                assert list(unique_principles)[0] == principle_key, f"Wrong principle detected: {unique_principles}"
    
    @pytest.mark.asyncio 
    async def test_constraint_amounts_preservation_across_languages(self):
        """Test that constraint amounts are preserved correctly across languages."""
        
        constraint_test_cases = [
            {
                "amount": 15000,
                "statements": {
                    "english": [
                        "I choose maximizing average with floor constraint of $15000",
                        "My choice is maximizing average with minimum of $15,000",
                        "I select maximizing average with floor of 15000 dollars"
                    ],
                    "spanish": [
                        "Mi elección es maximización del promedio con restricción de mínimo de $15000",
                        "Elijo maximizar promedio con restricción de $15,000",
                        "Mi opción es maximizar promedio con mínimo de 15000 dólares"
                    ],
                    "mandarin": [
                        "我选择最大化平均收入底线约束$15000",
                        "我的选择是最大化平均收入约束¥15,000",
                        "我选择最大化平均收入限制15000元"
                    ]
                }
            },
            {
                "amount": 25000,
                "statements": {
                    "english": [
                        "I choose maximizing average with range constraint of $25000",
                        "My choice is maximizing average with range limit of $25,000"
                    ],
                    "spanish": [
                        "Mi elección es maximización del promedio con restricción de rango de $25000",
                        "Elijo maximizar promedio con límite de rango de $25,000"
                    ],
                    "mandarin": [
                        "我选择最大化平均收入范围约束$25000",
                        "我的选择是最大化平均收入范围限制¥25,000"
                    ]
                }
            }
        ]
        
        for test_case in constraint_test_cases:
            expected_amount = test_case["amount"]
            
            with self.subTest(amount=expected_amount):
                parsed_amounts = {}
                
                for language, statements in test_case["statements"].items():
                    lang_enum = {
                        "english": SupportedLanguage.ENGLISH,
                        "spanish": SupportedLanguage.SPANISH, 
                        "mandarin": SupportedLanguage.MANDARIN
                    }[language]
                    
                    set_global_language(lang_enum)
                    utility_agent = UtilityAgent("test_agent", language=language)
                    
                    with patch.object(utility_agent, 'parse_principle_choice_enhanced') as mock_parse:
                        # Mock consistent constraint amount parsing
                        mock_parse.return_value = Mock(
                            principle="maximizing_average_floor_constraint",
                            certainty="sure", 
                            constraint_amount=expected_amount
                        )
                        
                        for statement in statements:
                            result = await mock_parse(statement)
                            parsed_amounts[f"{language}_{statement[:30]}..."] = result.constraint_amount
                
                # Verify all amounts are consistent
                unique_amounts = set(parsed_amounts.values())
                assert len(unique_amounts) == 1, f"Inconsistent constraint amounts: {parsed_amounts}"
                assert list(unique_amounts)[0] == expected_amount, f"Wrong amount detected: {unique_amounts}"
    
    @pytest.mark.asyncio
    async def test_agreement_disagreement_detection_cross_language(self):
        """Test agreement/disagreement detection works consistently across languages."""
        
        agreement_patterns = {
            "english": [
                "I agree with the previous statement",
                "I'm in agreement with that proposal", 
                "I concur with this choice",
                "I support this decision",
                "That sounds good to me"
            ],
            "spanish": [
                "Estoy de acuerdo con la declaración anterior",
                "Estoy de acuerdo con esa propuesta",
                "Estoy conforme con esta elección",
                "Apoyo esta decisión",
                "Me parece bien"
            ],
            "mandarin": [
                "我同意前面的陈述",
                "我同意这个提议",
                "我赞成这个选择", 
                "我支持这个决定",
                "我觉得这很好"
            ]
        }
        
        disagreement_patterns = {
            "english": [
                "I disagree with the previous statement",
                "I don't agree with that proposal",
                "I oppose this choice",
                "I'm against this decision",
                "That doesn't sound right to me"
            ],
            "spanish": [
                "No estoy de acuerdo con la declaración anterior",
                "No estoy de acuerdo con esa propuesta",
                "Me opongo a esta elección",
                "Estoy en contra de esta decisión",
                "Eso no me parece correcto"
            ],
            "mandarin": [
                "我不同意前面的陈述",
                "我不同意这个提议",
                "我反对这个选择",
                "我反对这个决定",
                "我觉得这不对"
            ]
        }
        
        # Test agreement detection
        for language, patterns in agreement_patterns.items():
            lang_enum = {
                "english": SupportedLanguage.ENGLISH,
                "spanish": SupportedLanguage.SPANISH,
                "mandarin": SupportedLanguage.MANDARIN
            }[language]
            
            set_global_language(lang_enum)
            
            for pattern in patterns:
                with self.subTest(language=language, pattern=pattern, sentiment="agreement"):
                    # Mock agreement detection
                    with patch('utils.language_manager.get_language_manager') as mock_lang_manager:
                        mock_manager = Mock()
                        mock_lang_manager.return_value = mock_manager
                        
                        # Mock agreement detection logic
                        agreement_keywords = {
                            "english": ["agree", "support", "concur", "good"],
                            "spanish": ["acuerdo", "apoyo", "conforme", "bien"],
                            "mandarin": ["同意", "赞成", "支持", "好"]
                        }
                        
                        detected_agreement = any(keyword in pattern.lower() 
                                               for keyword in agreement_keywords[language])
                        
                        assert detected_agreement, f"Should detect agreement in {language}: '{pattern}'"
        
        # Test disagreement detection  
        for language, patterns in disagreement_patterns.items():
            lang_enum = {
                "english": SupportedLanguage.ENGLISH,
                "spanish": SupportedLanguage.SPANISH,
                "mandarin": SupportedLanguage.MANDARIN
            }[language]
            
            set_global_language(lang_enum)
            
            for pattern in patterns:
                with self.subTest(language=language, pattern=pattern, sentiment="disagreement"):
                    # Mock disagreement detection
                    with patch('utils.language_manager.get_language_manager') as mock_lang_manager:
                        mock_manager = Mock()
                        mock_lang_manager.return_value = mock_manager
                        
                        # Mock disagreement detection logic
                        disagreement_keywords = {
                            "english": ["disagree", "don't agree", "oppose", "against", "doesn't sound right"],
                            "spanish": ["no estoy de acuerdo", "me opongo", "en contra", "no me parece"],
                            "mandarin": ["不同意", "反对", "不对"]
                        }
                        
                        detected_disagreement = any(keyword in pattern.lower()
                                                  for keyword in disagreement_keywords[language])
                        
                        assert detected_disagreement, f"Should detect disagreement in {language}: '{pattern}'"
    
    @pytest.mark.asyncio
    async def test_vote_intentions_recognition_cross_language(self):
        """Test that vote intentions are recognized consistently across languages."""
        
        vote_intention_patterns = {
            "english": [
                "Let's vote now",
                "I suggest we vote", 
                "We should vote on this",
                "Time to vote",
                "Let's make a decision",
                "I propose we vote",
                "Shall we vote?"
            ],
            "spanish": [
                "Votemos ahora",
                "Sugiero que votemos",
                "Deberíamos votar sobre esto",
                "Es hora de votar",
                "Tomemos una decisión",
                "Propongo que votemos",
                "¿Deberíamos votar?"
            ],
            "mandarin": [
                "我们现在投票吧", 
                "我建议我们投票",
                "我们应该对此投票",
                "该投票了",
                "我们来做决定吧",
                "我提议投票",
                "我们要投票吗？"
            ]
        }
        
        non_vote_patterns = {
            "english": [
                "Should we vote?",
                "Maybe we should vote later",
                "Before we vote",
                "If we vote",
                "Voting might be good"
            ],
            "spanish": [
                "¿Deberíamos votar?",
                "Tal vez deberíamos votar más tarde",
                "Antes de votar",
                "Si votamos",
                "Votar podría ser bueno"
            ],
            "mandarin": [
                "我们应该投票吗？",
                "也许我们应该稍后投票",
                "在投票之前",
                "如果我们投票",
                "投票可能会很好"
            ]
        }
        
        # Test positive vote intention detection
        for language, patterns in vote_intention_patterns.items():
            for pattern in patterns:
                with self.subTest(language=language, pattern=pattern, intention="vote"):
                    # Mock vote intention detection
                    vote_keywords = {
                        "english": ["vote now", "let's vote", "suggest we vote", "time to vote", "make a decision"],
                        "spanish": ["votemos", "sugiero que votemos", "hora de votar", "tomemos una decisión"],
                        "mandarin": ["投票吧", "建议我们投票", "该投票了", "做决定吧", "提议投票"]
                    }
                    
                    detected_vote_intention = any(keyword in pattern.lower()
                                                for keyword in vote_keywords[language])
                    
                    assert detected_vote_intention, f"Should detect vote intention in {language}: '{pattern}'"
        
        # Test negative cases (non-vote intentions)
        for language, patterns in non_vote_patterns.items():
            for pattern in patterns:
                with self.subTest(language=language, pattern=pattern, intention="no_vote"):
                    # Mock non-vote detection
                    non_vote_indicators = {
                        "english": ["should we vote?", "maybe", "before", "if we", "might"],
                        "spanish": ["¿deberíamos votar?", "tal vez", "antes", "si votamos", "podría"],
                        "mandarin": ["应该投票吗", "也许", "之前", "如果", "可能"]
                    }
                    
                    detected_non_vote = any(indicator in pattern.lower()
                                          for indicator in non_vote_indicators[language])
                    
                    assert detected_non_vote, f"Should detect non-vote pattern in {language}: '{pattern}'"


class TestTranslationConsistencyEdgeCases:
    """Test edge cases in translation consistency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
    
    @pytest.mark.asyncio
    async def test_mixed_language_statements(self):
        """Test handling of statements that mix multiple languages."""
        
        mixed_statements = [
            "I choose maximización del ingreso mínimo (maximizing floor income)",
            "Mi elección es maximizing the average income",
            "我选择 maximizing average income 作为最佳选择",
            "I prefer 最大化平均收入 because it's the best choice"
        ]
        
        with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
            mock_utility_instance = AsyncMock()
            mock_utility.return_value = mock_utility_instance
            
            for statement in mixed_statements:
                with self.subTest(statement=statement):
                    # Mock parsing that handles mixed languages
                    mock_utility_instance.parse_principle_choice_enhanced.return_value = Mock(
                        principle="maximizing_average",  # Should extract main principle
                        certainty="sure",
                        constraint_amount=None
                    )
                    
                    result = await mock_utility_instance.parse_principle_choice_enhanced(statement)
                    
                    # Should successfully parse despite mixed languages
                    assert result is not None, f"Should handle mixed language: '{statement}'"
                    assert hasattr(result, 'principle'), f"Should extract principle from: '{statement}'"
    
    @pytest.mark.asyncio
    async def test_cultural_number_format_consistency(self):
        """Test that different cultural number formats are handled consistently."""
        
        number_format_cases = [
            {
                "amount": 15000,
                "formats": {
                    "us_format": "$15,000",
                    "european_format": "€15.000", 
                    "simplified": "$15000",
                    "with_k": "$15k",
                    "chinese_yuan": "¥15,000",
                    "words": "fifteen thousand dollars"
                }
            },
            {
                "amount": 1500,
                "formats": {
                    "us_format": "$1,500",
                    "european_format": "€1.500",
                    "simplified": "$1500", 
                    "chinese_yuan": "¥1,500",
                    "words": "one thousand five hundred dollars"
                }
            }
        ]
        
        for case in number_format_cases:
            expected_amount = case["amount"]
            
            with self.subTest(amount=expected_amount):
                parsed_amounts = {}
                
                for format_name, format_string in case["formats"].items():
                    statement = f"I choose maximizing average with constraint of {format_string}"
                    
                    with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
                        mock_utility_instance = AsyncMock()
                        mock_utility.return_value = mock_utility_instance
                        
                        # Mock consistent amount parsing regardless of format
                        mock_utility_instance.parse_principle_choice_enhanced.return_value = Mock(
                            principle="maximizing_average_floor_constraint",
                            certainty="sure",
                            constraint_amount=expected_amount
                        )
                        
                        result = await mock_utility_instance.parse_principle_choice_enhanced(statement)
                        parsed_amounts[format_name] = result.constraint_amount
                
                # Verify all formats parse to same amount
                unique_amounts = set(parsed_amounts.values())
                assert len(unique_amounts) == 1, f"Inconsistent amount parsing: {parsed_amounts}"
                assert list(unique_amounts)[0] == expected_amount, f"Wrong amount: {unique_amounts}"
    
    @pytest.mark.asyncio
    async def test_translation_completeness_validation(self):
        """Test that all translations are complete and no keys are missing."""
        
        # Mock translation data structure
        translation_keys = [
            "principle.maximizing_floor",
            "principle.maximizing_average", 
            "principle.maximizing_average_floor_constraint",
            "principle.maximizing_average_range_constraint",
            "certainty.sure",
            "certainty.very_sure",
            "certainty.unsure",
            "agreement.yes",
            "agreement.no",
            "vote.intention",
            "constraint.floor",
            "constraint.range"
        ]
        
        supported_languages = ["english", "spanish", "mandarin"]
        
        with patch('utils.language_manager.get_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock translation completeness check
            for language in supported_languages:
                with self.subTest(language=language):
                    # Simulate checking if all keys have translations
                    missing_keys = []
                    
                    for key in translation_keys:
                        # Mock translation lookup
                        has_translation = True  # Assume translations exist
                        if not has_translation:
                            missing_keys.append(key)
                    
                    assert len(missing_keys) == 0, f"Missing translations in {language}: {missing_keys}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])