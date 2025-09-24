"""
Consolidated Constraint and Ranking Validation Tests

This module contains comprehensive tests for constraint parsing, ranking detection,
and agreement validation functionality across all supported languages.

Functionality tested:
1. Constraint parsing and validation across languages
2. Ranking parsing and comprehension  
3. Vote agreement pattern detection
4. Numerical agreement detection
5. Constraint correction mechanisms

Consolidated from:
- test_multilingual_constraint_parsing.py
- test_ranking_parsing.py  
- test_ranking_parsing_comprehensive.py
- test_vote_agreement_patterns.py
- test_numerical_agreement_detection.py
- test_constraint_correction.py
- test_phase2_spanish_constraints.py
- test_voting_history_structures.py
"""

import pytest
import asyncio
from typing import List, Dict, Any, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.error_handling import ValidationError


class TestConstraintValidation:
    """Unified test class for constraint parsing and validation functionality."""
    
    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for testing."""
        return UtilityAgent(utility_model="gpt-4.1-mini", temperature=0.0)
    
    @pytest.fixture
    def constraint_examples(self):
        """Multilingual constraint examples for testing."""
        return {
            "english": {
                "percentage": [
                    ("with a 60% floor constraint", 60.0),
                    ("constrained at 75 percent", 75.0),
                    ("floor set to 85%", 85.0),
                    ("minimum of 50 percent", 50.0),
                    ("constraint: 65.5%", 65.5)
                ],
                "monetary": [
                    ("with $50,000 floor constraint", 50000.0),
                    ("minimum of $100,000", 100000.0), 
                    ("floor at $75,500", 75500.0),
                    ("constraint of €45,000", 45000.0),
                    ("¥500,000 minimum", 500000.0)
                ],
                "abbreviated": [
                    ("floor of 100k", 100000.0),
                    ("constraint at 250K", 250000.0),
                    ("minimum 1.5M", 1500000.0),
                    ("50k floor", 50000.0)
                ]
            },
            "spanish": {
                "percentage": [
                    ("con una restricción del 60%", 60.0),
                    ("limitado al 75 por ciento", 75.0),
                    ("mínimo establecido en 85%", 85.0),
                    ("restricción: 65.5%", 65.5)
                ],
                "monetary": [
                    ("con restricción de $50,000", 50000.0),
                    ("mínimo de $100,000", 100000.0),
                    ("piso en $75,500", 75500.0),
                    ("restricción de €45,000", 45000.0)
                ]
            },
            "mandarin": {
                "percentage": [
                    ("约束为60%", 60.0),
                    ("限制在75%", 75.0),
                    ("最低约束85%", 85.0),
                    ("约束：65.5%", 65.5)
                ],
                "monetary": [
                    ("约束为$50,000", 50000.0),
                    ("最低$100,000", 100000.0),
                    ("底线$75,500", 75500.0),
                    ("限制€45,000", 45000.0)
                ]
            }
        }
    
    @pytest.fixture
    def ranking_examples(self):
        """Ranking statement examples for testing."""
        return {
            "english": [
                "I rank the principles as follows: A > B > C > D",
                "My ranking: 1. Maximizing floor, 2. Maximizing average, 3. Floor constraint, 4. Average constraint",
                "First choice: A, second: B, third: C, fourth: D",
                "Preference order: maximizing floor > maximizing average > constrained floor > constrained average"
            ],
            "spanish": [
                "Clasifico los principios así: A > B > C > D", 
                "Mi clasificación: 1. Maximizar mínimo, 2. Maximizar promedio, 3. Restricción mínima, 4. Restricción promedio",
                "Primera elección: A, segunda: B, tercera: C, cuarta: D"
            ],
            "mandarin": [
                "我对原则的排序如下：A > B > C > D",
                "我的排序：1. 最大化最低收入，2. 最大化平均收入，3. 约束最低，4. 约束平均",
                "第一选择：A，第二：B，第三：C，第四：D"
            ]
        }

    # CONSTRAINT PARSING TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    @pytest.mark.parametrize("constraint_type", ["percentage", "monetary"])
    def test_multilingual_constraint_extraction(self, utility_agent, constraint_examples, language, constraint_type):
        """Test constraint extraction across languages and formats."""
        if constraint_type not in constraint_examples[language]:
            pytest.skip(f"No {constraint_type} examples for {language}")
            
        examples = constraint_examples[language][constraint_type]
        
        for constraint_text, expected_value in examples:
            full_statement = f"I choose maximizing average income {constraint_text}"
            result = utility_agent.parse_principle_choice_enhanced(full_statement)
            
            assert result.constraint_amount == expected_value, \
                f"Failed to extract {expected_value} from '{constraint_text}' in {language}"
            assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT

    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_abbreviated_constraint_formats(self, utility_agent, constraint_examples, language):
        """Test parsing of abbreviated constraint formats (k, K, M)."""
        if language != "english":  # Currently only testing English abbreviations
            pytest.skip("Abbreviated formats currently only tested in English")
            
        examples = constraint_examples[language]["abbreviated"]
        
        for constraint_text, expected_value in examples:
            full_statement = f"I prefer maximizing with {constraint_text}"
            result = utility_agent.parse_principle_choice_enhanced(full_statement)
            
            assert result.constraint_amount == expected_value, \
                f"Failed to parse abbreviated format: {constraint_text}"

    def test_constraint_validation_edge_cases(self, utility_agent):
        """Test constraint validation with edge cases and invalid inputs."""
        edge_cases = [
            # Valid edge cases
            ("constraint of 0%", 0.0),
            ("100% constraint", 100.0),
            ("constraint: 0.1%", 0.1),
            ("99.99% floor", 99.99),
            
            # Invalid cases that should be handled gracefully
            ("constraint of 150%", None),  # Over 100%
            ("constraint of -10%", None),  # Negative
            ("floor of $0", 0.0),          # Zero dollars (valid)
            ("constraint of $-5000", None) # Negative dollars
        ]
        
        for constraint_text, expected_value in edge_cases:
            full_statement = f"I choose principle C {constraint_text}"
            
            if expected_value is None:
                # Should either fail validation or be handled gracefully
                try:
                    result = utility_agent.parse_principle_choice_enhanced(full_statement)
                    # If it doesn't fail, it should at least not extract invalid constraint
                    assert result.constraint_amount is None or result.constraint_amount >= 0
                except ValidationError:
                    pass  # Expected for invalid constraints
            else:
                result = utility_agent.parse_principle_choice_enhanced(full_statement)
                assert result.constraint_amount == expected_value

    def test_constraint_correction_mechanisms(self, utility_agent):
        """Test automatic constraint correction for common issues.""" 
        correction_cases = [
            # Common formatting issues that should be corrected
            {
                "input": "constraint of 60 %",  # Space before %
                "expected": 60.0,
                "description": "Space handling"
            },
            {
                "input": "constraint: $50,000.00",  # Decimal places
                "expected": 50000.0,
                "description": "Decimal removal"
            },
            {
                "input": "constraint of fifty percent",  # Word form
                "expected": None,  # May not be supported
                "description": "Word form parsing"
            },
            {
                "input": "constraint = 75%",  # Equals instead of 'of'
                "expected": 75.0,
                "description": "Alternative syntax"
            }
        ]
        
        for case in correction_cases:
            full_statement = f"I select maximizing average {case['input']}"
            
            try:
                result = utility_agent.parse_principle_choice_enhanced(full_statement)
                if case["expected"] is not None:
                    assert result.constraint_amount == case["expected"], \
                        f"Correction failed for {case['description']}: {case['input']}"
            except ValidationError:
                if case["expected"] is not None:
                    pytest.fail(f"Unexpected validation error for {case['description']}: {case['input']}")

    # RANKING PARSING TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_ranking_detection_multilingual(self, utility_agent, ranking_examples, language):
        """Test ranking detection across languages."""
        examples = ranking_examples[language]
        
        for ranking_statement in examples:
            result = utility_agent.parse_principle_ranking_enhanced(ranking_statement)
            
            assert result.has_ranking is True, f"Failed to detect ranking in: {ranking_statement}"
            assert len(result.ranking_order) == 4, f"Incomplete ranking extracted from: {ranking_statement}"
            
            # Verify ranking order makes sense (A should typically be first)
            assert JusticePrinciple.MAXIMIZING_FLOOR in result.ranking_order, \
                f"Missing principle A in ranking: {ranking_statement}"

    def test_comprehensive_ranking_formats(self, utility_agent):
        """Test comprehensive ranking format parsing."""
        ranking_formats = [
            # Numeric formats
            {
                "statement": "1. Maximizing floor, 2. Maximizing average, 3. Constrained floor, 4. Constrained average",
                "expected_order": [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT]
            },
            # Letter formats
            {
                "statement": "A > B > C > D",
                "expected_order": [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT]
            },
            # Ordinal formats
            {
                "statement": "First: A, Second: B, Third: C, Fourth: D",
                "expected_order": [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT]
            },
            # Mixed formats
            {
                "statement": "My top choice is maximizing floor (A), then maximizing average (B), followed by constrained options C and D",
                "expected_order": [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT]
            }
        ]
        
        for format_case in ranking_formats:
            result = utility_agent.parse_principle_ranking_enhanced(format_case["statement"])
            
            assert result.has_ranking is True
            # Check that first principle matches expected (most important test)
            assert result.ranking_order[0] == format_case["expected_order"][0], \
                f"First principle mismatch in: {format_case['statement']}"

    def test_partial_ranking_handling(self, utility_agent):
        """Test handling of partial rankings (less than 4 principles)."""
        partial_rankings = [
            "My top two choices are A and B",
            "I prefer A over B",
            "My ranking: 1. Maximizing floor, 2. Maximizing average",
            "First choice: A"
        ]
        
        for partial_statement in partial_rankings:
            result = utility_agent.parse_principle_ranking_enhanced(partial_statement)
            
            # Should still detect as ranking attempt
            assert result.has_ranking is True, f"Failed to detect partial ranking: {partial_statement}"
            # Should have at least some ranking information
            assert len(result.ranking_order) >= 1, f"No ranking extracted from: {partial_statement}"

    # AGREEMENT PATTERN TESTS  
    def test_vote_agreement_pattern_detection(self, utility_agent):
        """Test detection of agreement patterns in group discussions."""
        agreement_patterns = [
            # Direct agreement
            "I agree with Alice's choice",
            "I'm in agreement with Bob on principle A",
            "Yes, I agree with that approach",
            "I concur with the maximizing floor option",
            
            # Consensus language
            "We all seem to agree on principle A",
            "I think we have consensus on maximizing floor",
            "Everyone agrees with this approach",
            
            # Conditional agreement
            "I can agree to that if others do",
            "I'm willing to go along with principle A"
        ]
        
        for statement in agreement_patterns:
            result = utility_agent.detect_agreement_pattern(statement)
            assert result.shows_agreement is True, f"Failed to detect agreement in: {statement}"

    def test_disagreement_pattern_detection(self, utility_agent):
        """Test detection of disagreement patterns."""
        disagreement_patterns = [
            # Direct disagreement
            "I disagree with Alice's choice",
            "I don't agree with that approach",
            "No, I think principle B is better",
            
            # Alternative preferences
            "Actually, I prefer principle C",
            "I have a different opinion on this",
            "I think we should consider other options",
            
            # Uncertainty (not agreement)
            "I'm not sure about that",
            "Maybe we should think more about this"
        ]
        
        for statement in disagreement_patterns:
            result = utility_agent.detect_agreement_pattern(statement)
            assert result.shows_agreement is False, f"False positive agreement detection: {statement}"

    def test_numerical_agreement_detection(self, utility_agent):
        """Test detection of numerical agreement in constraint specifications."""
        numerical_agreement_cases = [
            # Exact agreement
            {
                "statements": ["I choose 60% constraint", "I also choose 60%", "60% works for me"],
                "should_agree": True,
                "expected_value": 60.0
            },
            # Close agreement (within tolerance)
            {
                "statements": ["I choose 60%", "I think 61% is good", "60.5% for me"],
                "should_agree": True,  # Within reasonable tolerance
                "expected_value": 60.0  # Approximate
            },
            # Clear disagreement
            {
                "statements": ["I choose 60%", "I prefer 80%", "50% is better"],
                "should_agree": False,
                "expected_value": None
            }
        ]
        
        for case in numerical_agreement_cases:
            results = []
            for statement in case["statements"]:
                result = utility_agent.parse_principle_choice_enhanced(statement)
                results.append(result)
            
            agreement_result = utility_agent.detect_numerical_agreement(results)
            
            assert agreement_result.has_agreement == case["should_agree"], \
                f"Numerical agreement detection failed for: {case['statements']}"
            
            if case["expected_value"] is not None and agreement_result.has_agreement:
                # Check that agreed value is close to expected
                assert abs(agreement_result.agreed_value - case["expected_value"]) <= 5.0

    # SPANISH CONSTRAINT SPECIALIZATIONS
    def test_spanish_constraint_specializations(self, utility_agent):
        """Test Spanish-specific constraint parsing patterns."""
        spanish_constraints = [
            # Percentage formats in Spanish
            ("con una restricción del sesenta por ciento", 60.0),  # Word form
            ("limitado al 75%", 75.0),                             # Direct format
            ("mínimo establecido en el 85 porciento", 85.0),       # Alternative spelling
            ("restricción: 65,5%", 65.5),                          # Comma decimal
            
            # Monetary formats in Spanish  
            ("con restricción de $50.000", 50000.0),               # Period thousands
            ("mínimo de €45,000", 45000.0),                        # Comma thousands
            ("piso de $100 mil", 100000.0),                        # Word thousands
            
            # Complex Spanish constraint language
            ("con una restricción mínima del 60 por ciento del ingreso promedio", 60.0),
            ("estableciendo un piso del 75% como limitación", 75.0)
        ]
        
        for constraint_text, expected_value in spanish_constraints:
            full_statement = f"Elijo maximizar el promedio {constraint_text}"
            
            try:
                result = utility_agent.parse_principle_choice_enhanced(full_statement)
                if expected_value is not None:
                    assert result.constraint_amount == expected_value, \
                        f"Spanish constraint parsing failed for: {constraint_text}"
            except ValidationError:
                if expected_value is not None:
                    pytest.fail(f"Unexpected parsing failure for Spanish constraint: {constraint_text}")

    def test_voting_history_structure_validation(self, utility_agent):
        """Test validation of voting history data structures."""
        # Test valid voting history structures
        valid_histories = [
            {
                "round": 1,
                "participant": "Alice",  
                "choice": JusticePrinciple.MAXIMIZING_FLOOR,
                "constraint": None,
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "round": 2,
                "participant": "Bob",
                "choice": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "constraint": 65.0,
                "timestamp": "2024-01-01T10:05:00Z"
            }
        ]
        
        # Test invalid voting history structures
        invalid_histories = [
            {"round": 1},  # Missing required fields
            {"participant": "Alice", "choice": "invalid_principle"},  # Invalid principle
            {"round": "invalid", "participant": "Bob", "choice": JusticePrinciple.MAXIMIZING_FLOOR}  # Invalid round
        ]
        
        for valid_history in valid_histories:
            # Should validate without errors
            result = utility_agent.validate_voting_history_entry(valid_history)
            assert result.is_valid is True
        
        for invalid_history in invalid_histories:
            # Should fail validation
            result = utility_agent.validate_voting_history_entry(invalid_history)
            assert result.is_valid is False

    def test_constraint_parsing_regression_prevention(self, utility_agent):
        """Test that previous constraint parsing bugs remain fixed."""
        regression_cases = [
            # Previously misparse "no constraints" as constrained
            {
                "statement": "maximizing floor income with no additional constraints",
                "should_have_constraint": False,
                "principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            
            # Previously failed to extract percentage with spaces
            {
                "statement": "maximizing average with 60 % constraint",
                "should_have_constraint": True,
                "expected_constraint": 60.0
            },
            
            # Previously confused letter references with constraints
            {
                "statement": "I choose A with no constraints",
                "should_have_constraint": False,
                "principle": JusticePrinciple.MAXIMIZING_FLOOR
            }
        ]
        
        for case in regression_cases:
            result = utility_agent.parse_principle_choice_enhanced(case["statement"])
            
            assert result.principle == case["principle"], \
                f"Principle regression for: {case['statement']}"
            
            if case["should_have_constraint"]:
                assert result.constraint_amount is not None, \
                    f"Missing expected constraint for: {case['statement']}"
                if "expected_constraint" in case:
                    assert result.constraint_amount == case["expected_constraint"]
            else:
                assert result.constraint_amount is None, \
                    f"Unexpected constraint detected for: {case['statement']}"