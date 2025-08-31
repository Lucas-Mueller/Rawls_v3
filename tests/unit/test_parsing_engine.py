"""
Consolidated Ballot and Principle Parsing Tests

This module contains comprehensive tests for all ballot parsing functionality,
consolidating tests from multiple files into a unified, parametrized test suite.

Functionality tested:
1. Ballot parsing with multilingual support
2. Principle detection and constraint extraction  
3. Real-world parsing scenarios and edge cases
4. Parsing corrections and vulnerability fixes
5. Multilingual constraint parsing

Consolidated from:
- test_ballot_parsing.py
- test_phase2_ballot_parsing_corrections.py  
- test_real_world_ballot_parsing.py
- test_multilingual_constraint_parsing.py
"""

import pytest
import asyncio
from typing import List, Dict, Any
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.error_handling import ValidationError


class TestParsingEngine:
    """Unified test class for ballot and principle parsing functionality."""
    
    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for testing."""
        return UtilityAgent(utility_model="gpt-4.1-mini", temperature=0.0)
    
    @pytest.fixture
    def sample_ballots(self):
        """Sample ballot statements across languages for testing."""
        return {
            "english": [
                "I choose maximizing the floor income with no additional constraints",
                "I vote for principle b - maximizing average income",
                "My choice is c - maximizing the floor, with a 60% constraint",
                "I select d - maximizing average with floor constraint of $50,000"
            ],
            "spanish": [
                "Elijo maximizar el ingreso mínimo sin restricciones adicionales", 
                "Voto por el principio b - maximizar el ingreso promedio",
                "Mi elección es c - maximizar el mínimo, con una restricción del 60%",
                "Selecciono d - maximizar el promedio con restricción mínima de $50,000"
            ],
            "mandarin": [
                "我选择最大化最低收入，不附加额外约束",
                "我投票选择原则b - 最大化平均收入", 
                "我的选择是c - 最大化最低收入，约束为60%",
                "我选择d - 最大化平均收入，最低约束为$50,000"
            ]
        }

    # BALLOT PARSING CORE FUNCTIONALITY
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    @pytest.mark.asyncio
    async def test_principle_detection_multilingual(self, utility_agent, sample_ballots, language):
        """Test principle detection across all supported languages."""
        ballots = sample_ballots[language]
        
        # Test principle A detection (maximizing floor, no constraints)
        result = await utility_agent.parse_principle_choice_enhanced(ballots[0])
        assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert result.constraint_amount is None
        
        # Test principle B detection (maximizing average)  
        result = await utility_agent.parse_principle_choice_enhanced(ballots[1])
        assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE
        
        # Test principle C detection (maximizing floor with percentage constraint)
        result = await utility_agent.parse_principle_choice_enhanced(ballots[2])
        assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        
        # Test principle D detection (maximizing average with floor constraint)
        result = await utility_agent.parse_principle_choice_enhanced(ballots[3])
        assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT

    def test_principle_a_no_constraints_vulnerability_fix(self, utility_agent):
        """Test the specific vulnerability where 'no constraints' was misparse as constrained principle."""
        # These are the exact phrases that caused the parsing failure
        problematic_statements = [
            "maximizing the floor income with no additional constraints",
            "I choose a - maximizing the floor income with no additional constraints", 
            "My preference is maximizing the floor, no constraints specified",
            "I select principle A: maximizing floor income without constraints"
        ]
        
        for statement in problematic_statements:
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR, f"Failed for: {statement}"
            assert result.constraint_amount is None, f"Incorrectly detected constraint for: {statement}"

    def test_letter_based_principle_detection(self, utility_agent):
        """Test detection of principles referenced by letter (a, b, c, d)."""
        letter_cases = [
            ("a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("b", JusticePrinciple.MAXIMIZING_AVERAGE), 
            ("c", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            ("d", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            ("principle a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("I choose B", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("My vote is c", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        ]
        
        for statement, expected_principle in letter_cases:
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, f"Failed for letter: {statement}"

    @pytest.mark.parametrize("constraint_text,expected_amount", [
        ("60%", 60.0),
        ("75 percent", 75.0), 
        ("$50,000", 50000.0),
        ("€45,000", 45000.0),
        ("¥500,000", 500000.0),
        ("50k", 50000.0),
        ("100K", 100000.0),
        ("2.5 million", 2500000.0)
    ])
    def test_constraint_amount_extraction(self, utility_agent, constraint_text, expected_amount):
        """Test extraction of constraint amounts from various formats."""
        statement = f"I choose maximizing average with floor constraint of {constraint_text}"
        result = utility_agent.parse_principle_choice_enhanced(statement)
        
        assert result.constraint_amount == expected_amount, f"Failed to extract {expected_amount} from {constraint_text}"

    def test_no_constraints_vs_with_constraints_distinction(self, utility_agent):
        """Test proper distinction between constrained and unconstrained principles."""
        # No constraints - should be MAXIMIZING_FLOOR
        no_constraint_statements = [
            "maximizing the floor income with no additional constraints",
            "maximizing floor without constraints", 
            "principle a with no restrictions",
            "maximizing floor, unconstrained"
        ]
        
        for statement in no_constraint_statements:
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert result.constraint_amount is None
        
        # With constraints - should be MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        with_constraint_statements = [
            "maximizing the floor with 60% constraint",
            "principle c with floor constraint of $50,000",
            "maximizing average with floor at 75%",
            "constrained maximization at $100,000 floor"
        ]
        
        for statement in with_constraint_statements:
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            assert result.constraint_amount is not None

    def test_real_world_parsing_scenarios(self, utility_agent):
        """Test parsing of realistic participant responses."""
        real_world_cases = [
            {
                "statement": "After careful consideration, I believe we should go with maximizing the floor income approach without any additional constraints, as it provides the strongest safety net for everyone.",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None
            },
            {
                "statement": "My analysis suggests that option C - maximizing the floor income with a constraint set at 65% - offers the best balance between equality and incentives.",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 65.0
            },
            {
                "statement": "I'm leaning towards the maximizing average income principle (option B) because it encourages overall productivity while still being fair.",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None
            }
        ]
        
        for case in real_world_cases:
            result = utility_agent.parse_principle_choice_enhanced(case["statement"])
            assert result.principle == case["expected_principle"]
            assert result.constraint_amount == case["expected_constraint"]

    def test_edge_cases_and_ambiguous_phrasing(self, utility_agent):
        """Test handling of edge cases and ambiguous statements."""
        edge_cases = [
            # Empty or minimal statements
            ("a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("principle", None),  # Too ambiguous
            ("", None),
            
            # Multiple principles mentioned
            ("I'm torn between a and b, but I'll go with a", JusticePrinciple.MAXIMIZING_FLOOR),
            
            # Contradictory statements
            ("maximizing floor with no constraints but actually 50%", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            
            # Unusual formatting
            ("   a   ", JusticePrinciple.MAXIMIZING_FLOOR),
            ("A.", JusticePrinciple.MAXIMIZING_FLOOR),
            ("(a)", JusticePrinciple.MAXIMIZING_FLOOR)
        ]
        
        for statement, expected_principle in edge_cases:
            if expected_principle is None:
                with pytest.raises(ValidationError):
                    utility_agent.parse_principle_choice_enhanced(statement)
            else:
                result = utility_agent.parse_principle_choice_enhanced(statement)
                assert result.principle == expected_principle

    @pytest.mark.parametrize("language,statement_template", [
        ("spanish", "Elijo el principio {letter} - {description}"),
        ("mandarin", "我选择原则{letter} - {description}"),
        ("english", "I choose principle {letter} - {description}")
    ])
    def test_multilingual_consistency(self, utility_agent, language, statement_template):
        """Test that parsing works consistently across languages."""
        # Test that the same logical principle is detected regardless of language
        descriptions = {
            "spanish": ["maximizar ingresos mínimos", "maximizar ingresos promedio"],
            "mandarin": ["最大化最低收入", "最大化平均收入"], 
            "english": ["maximizing floor income", "maximizing average income"]
        }
        
        for i, desc in enumerate(descriptions[language][:2]):
            letter = ['a', 'b'][i]
            expected = [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE][i]
            
            statement = statement_template.format(letter=letter, description=desc)
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected

    def test_pattern_matching_order_priority(self, utility_agent):
        """Test that pattern matching follows the correct priority order."""
        # More specific patterns should match before general ones
        priority_tests = [
            # Specific constraint should win over general floor maximization
            ("maximizing floor income with 60% constraint", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            
            # Letter reference should be clear
            ("Even though I like maximizing average, I choose a", JusticePrinciple.MAXIMIZING_FLOOR),
            
            # "No constraints" should override other constraint patterns  
            ("maximizing average with floor constraint, but actually no constraints", JusticePrinciple.MAXIMIZING_FLOOR)
        ]
        
        for statement, expected_principle in priority_tests:
            result = utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, f"Priority test failed for: {statement}"

    def test_parsing_corrections_and_regressions(self, utility_agent):
        """Test that previous parsing bugs remain fixed."""
        # Test cases that previously caused issues
        regression_cases = [
            # The original vulnerability that was fixed
            {
                "statement": "maximizing the floor income with no additional constraints", 
                "should_be": JusticePrinciple.MAXIMIZING_FLOOR,
                "should_not_be": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            
            # Spanish parsing corrections
            {
                "statement": "maximizar el ingreso mínimo sin restricciones adicionales",
                "should_be": JusticePrinciple.MAXIMIZING_FLOOR, 
                "should_not_be": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            
            # Mandarin parsing corrections
            {
                "statement": "最大化最低收入，不附加额外约束",
                "should_be": JusticePrinciple.MAXIMIZING_FLOOR,
                "should_not_be": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            }
        ]
        
        for case in regression_cases:
            result = utility_agent.parse_principle_choice_enhanced(case["statement"])
            assert result.principle == case["should_be"], f"Regression: {case['statement']}"
            assert result.principle != case["should_not_be"], f"False positive: {case['statement']}"

    def test_comprehensive_constraint_extraction_scenarios(self, utility_agent):
        """Test comprehensive constraint extraction across various formats and languages."""
        constraint_scenarios = [
            # English constraint formats
            ("maximizing with 60% floor constraint", 60.0),
            ("principle c with $50,000 minimum", 50000.0),
            ("constrained at 75 percent", 75.0),
            ("floor set to 100k", 100000.0),
            
            # Spanish constraint formats  
            ("maximizar con restricción del 65%", 65.0),
            ("principio con mínimo de $75,000", 75000.0),
            ("restricción en el 70 por ciento", 70.0),
            
            # Mandarin constraint formats
            ("约束为60%", 60.0),
            ("最低约束为$50,000", 50000.0),
            ("限制在75%", 75.0),
            
            # Edge cases in constraint extraction
            ("constraint: 55.5%", 55.5),
            ("floor = $1,250,000", 1250000.0),
            ("minimum at €100K", 100000.0)
        ]
        
        for statement, expected_amount in constraint_scenarios:
            full_statement = f"I choose maximizing average income with {statement}"
            result = utility_agent.parse_principle_choice_enhanced(full_statement)
            
            assert result.constraint_amount == expected_amount, f"Failed constraint extraction for: {statement}"
            assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT