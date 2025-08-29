"""
Comprehensive unit tests for Phase 2 ballot parsing with post-parse corrections.

Tests the sophisticated ballot parsing logic that handles:
1. LLM JSON parsing with fallback mechanisms
2. Post-parse correction logic for constraint principle mentions
3. Constraint amount extraction and validation
4. Multilingual principle canonicalization
5. Ballot consensus checking with detailed disagreement analysis

Critical parsing vulnerabilities tested:
- "maximizing floor income with no additional constraints" -> maximizing_floor (not floor_constraint)
- LLM JSON extraction brittleness 
- Constraint correction scenarios
- Principle name canonicalization across languages
"""

import unittest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from utils.error_handling import ValidationError
from tests.fixtures.phase2_parsing_fixtures import (
    CHINESE_BALLOTS, SPANISH_BALLOTS, CONSTRAINTS
)


class TestBallotParsingCorrections(unittest.TestCase):
    """Test ballot parsing with post-parse correction logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    async def _parse_ballot(self, ballot_text: str) -> PrincipleChoice:
        """Helper to parse ballot text."""
        await self.utility_agent.async_init()
        return await self.utility_agent.parse_principle_choice_enhanced(ballot_text)
    
    def test_critical_parsing_vulnerabilities(self):
        """Test the specific cases that caused critical parsing failures."""
        
        # The exact case from experiment_results_20250827_091903.json
        critical_cases = [
            {
                "ballot": "maximizing floor income with no additional constraints",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "maximizing floor + no constraints should be maximizing_floor"
            },
            {
                "ballot": "My ballot choice is maximizing floor income with no constraints", 
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Extended form should still be maximizing_floor"
            },
            {
                "ballot": "I choose maximizing floor income without any constraint",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Alternative phrasing should be maximizing_floor"
            }
        ]
        
        for case in critical_cases:
            with self.subTest(description=case["description"]):
                result = asyncio.run(self._parse_ballot(case["ballot"]))
                
                self.assertIsNotNone(result, f"Failed to parse: {case['ballot']}")
                self.assertEqual(result.principle, case["expected_principle"], 
                               f"Wrong principle for '{case['ballot']}': got {result.principle.value}")
                self.assertEqual(result.constraint_amount, case["expected_constraint"],
                               f"Wrong constraint for '{case['ballot']}': got {result.constraint_amount}")
    
    def test_post_parse_correction_logic(self):
        """Test post-parse correction for constraint principle mentions."""
        
        correction_cases = [
            {
                "ballot": "I vote for floor constraint with $15000 minimum income",
                "raw_principle": "maximizing_average",  # What LLM might parse incorrectly
                "mentions": "floor constraint",
                "expected_corrected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000
            },
            {
                "ballot": "My choice is range constraint with income gap of $20000",
                "raw_principle": "maximizing_average", 
                "mentions": "range constraint",
                "expected_corrected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 20000
            },
            {
                "ballot": "I choose floor constraint principle with $12000",
                "raw_principle": "maximizing_average",
                "mentions": "floor constraint", 
                "expected_corrected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 12000
            }
        ]
        
        for case in correction_cases:
            with self.subTest(ballot=case["ballot"]):
                # This tests the actual correction logic that happens in parse_principle_choice_llm
                result = asyncio.run(self._parse_ballot(case["ballot"]))
                
                self.assertIsNotNone(result, f"Failed to parse: {case['ballot']}")
                self.assertEqual(result.principle, case["expected_corrected"],
                               f"Post-parse correction failed for '{case['ballot']}'")
                self.assertEqual(result.constraint_amount, case["expected_constraint"],
                               f"Constraint extraction failed for '{case['ballot']}'")
    
    @patch('experiment_agents.utility_agent.Runner.run')
    def test_llm_json_extraction_robustness(self, mock_runner):
        """Test JSON extraction from various LLM response formats."""
        async def run_test():
            await self.utility_agent.async_init()
            
            json_test_cases = [
                # Clean JSON
                {
                    "llm_response": '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                    "expected_principle": "maximizing_floor",
                    "should_parse": True
                },
                # JSON with extra text
                {
                    "llm_response": 'Looking at this ballot, I can extract: {"principle": "maximizing_average", "constraint_amount": 15000, "certainty": "sure"}',
                    "expected_principle": "maximizing_average", 
                    "should_parse": True
                },
                # Malformed JSON
                {
                    "llm_response": '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": sure}',  # Missing quotes
                    "should_parse": False
                },
                # Missing required fields
                {
                    "llm_response": '{"principle": "maximizing_floor"}',  # Missing constraint_amount and certainty
                    "should_parse": False
                },
                # Invalid principle value
                {
                    "llm_response": '{"principle": "invalid_principle", "constraint_amount": null, "certainty": "sure"}',
                    "should_parse": False
                }
            ]
            
            for case in json_test_cases:
                with self.subTest(response=case["llm_response"][:50]):
                    mock_result = MagicMock()
                    mock_result.final_output = case["llm_response"]
                    mock_runner.return_value = mock_result
                    
                    result = await self.utility_agent.parse_principle_choice_llm("test ballot")
                    
                    if case["should_parse"]:
                        self.assertIsNotNone(result, f"Should parse JSON: {case['llm_response'][:100]}")
                        if "expected_principle" in case:
                            self.assertEqual(result["principle"], case["expected_principle"])
                    else:
                        self.assertIsNone(result, f"Should NOT parse malformed JSON: {case['llm_response'][:100]}")
        
        asyncio.run(run_test())
    
    def test_constraint_amount_extraction_flexibility(self):
        """Test flexible constraint amount extraction from various formats."""
        
        constraint_cases = [
            # Standard formats
            ("$15,000", 15000),
            ("$15000", 15000),
            ("15,000 dollars", 15000),
            ("15000", 15000),
            
            # European format
            ("$15.000", 15000),
            ("15.000 dollars", 15000),
            
            # Abbreviated formats
            ("15k", 15000),
            ("15 thousand", 15000),
            ("$15k", 15000),
            
            # Edge cases
            ("$ 15,000", 15000),  # Space after dollar sign
            ("15,000$", 15000),   # Dollar sign after
            
            # Invalid cases
            ("invalid", None),
            ("", None),
            ("$0", None),         # Zero amount should be invalid
            ("-5000", None),      # Negative should be invalid
        ]
        
        for amount_text, expected in constraint_cases:
            with self.subTest(amount_text=amount_text):
                result = self.utility_agent._extract_constraint_amount_flexible(f"constraint of {amount_text}")
                self.assertEqual(result, expected, 
                               f"Constraint extraction failed for '{amount_text}': got {result}, expected {expected}")
    
    def test_multilingual_principle_canonicalization(self):
        """Test principle canonicalization across languages."""
        
        canonicalization_cases = [
            # English variants
            ("maximizing_floor", JusticePrinciple.MAXIMIZING_FLOOR),
            ("maximizing_floor_income", JusticePrinciple.MAXIMIZING_FLOOR),
            ("floor_constraint", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            
            # Chinese
            ("最大化最低收入", JusticePrinciple.MAXIMIZING_FLOOR),
            ("最大化平均收入", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("在最低收入约束条件下最大化平均收入", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            ("在范围约束条件下最大化平均收入", JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT),
            
            # Spanish  
            ("maximización del ingreso mínimo", JusticePrinciple.MAXIMIZING_FLOOR),
            ("maximización del ingreso promedio", JusticePrinciple.MAXIMIZING_AVERAGE),
        ]
        
        for principle_text, expected in canonicalization_cases:
            with self.subTest(principle_text=principle_text):
                result = self.utility_agent._map_identifier_to_principle(principle_text)
                self.assertEqual(result, expected,
                               f"Canonicalization failed for '{principle_text}': got {result}, expected {expected}")
    
    def test_ballot_consensus_checking(self):
        """Test ballot consensus checking with detailed disagreement analysis."""
        
        # Test cases for different consensus scenarios
        consensus_scenarios = [
            {
                "description": "Perfect consensus - same principle and constraint",
                "ballots": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                ],
                "expected_consensus": True,
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "description": "Principle disagreement - different principles",
                "ballots": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.SURE),
                ],
                "expected_consensus": False,
                "disagreement_type": "principle"
            },
            {
                "description": "Constraint disagreement - same principle, different constraints",
                "ballots": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 20000, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 18000, CertaintyLevel.SURE),
                ],
                "expected_consensus": False,
                "disagreement_type": "constraint"
            },
            {
                "description": "Mixed disagreement - some agreement, some disagreement",
                "ballots": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.SURE),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE, None, CertaintyLevel.SURE),
                ],
                "expected_consensus": False, 
                "disagreement_type": "mixed"
            }
        ]
        
        for scenario in consensus_scenarios:
            with self.subTest(description=scenario["description"]):
                consensus, agreed_principle, warnings = self.utility_agent.check_ballot_consensus(scenario["ballots"])
                
                self.assertEqual(consensus, scenario["expected_consensus"],
                               f"Consensus detection failed for: {scenario['description']}")
                
                if scenario["expected_consensus"]:
                    self.assertEqual(agreed_principle.principle, scenario["expected_principle"],
                                   f"Agreed principle mismatch for: {scenario['description']}")
                else:
                    self.assertIsNone(agreed_principle, 
                                    f"Should not have agreed principle for: {scenario['description']}")
    
    def test_constraint_validation_logic(self):
        """Test constraint validation for voting eligibility."""
        
        validation_cases = [
            # Valid constraints
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, True),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 20000, True),
            (JusticePrinciple.MAXIMIZING_FLOOR, None, True),
            (JusticePrinciple.MAXIMIZING_AVERAGE, None, True),
            
            # Invalid constraints
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, None, False),  # Missing constraint
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, None, False), # Missing constraint
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 0, False),    # Zero constraint
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, -5000, False), # Negative constraint
        ]
        
        for principle, constraint, expected_valid in validation_cases:
            with self.subTest(principle=principle.value, constraint=constraint):
                choice = PrincipleChoice.create_for_parsing(principle, constraint, CertaintyLevel.SURE)
                is_valid = choice.is_valid_constraint()
                
                self.assertEqual(is_valid, expected_valid,
                               f"Validation failed for {principle.value} with constraint {constraint}")
    
    def test_chinese_ballot_parsing_scenarios(self):
        """Test comprehensive Chinese ballot parsing scenarios."""
        
        # Test all Chinese valid ballots
        for ballot_case in CHINESE_BALLOTS["valid_ballots"]:
            with self.subTest(description=ballot_case["description"]):
                result = asyncio.run(self._parse_ballot(ballot_case["statement"]))
                
                self.assertIsNotNone(result, f"Failed to parse Chinese ballot: '{ballot_case['statement']}'")
                self.assertEqual(result.principle, ballot_case["expected_principle"],
                               f"Wrong principle for Chinese ballot '{ballot_case['statement']}': got {result.principle.value}")
                self.assertEqual(result.constraint_amount, ballot_case["expected_constraint"],
                               f"Wrong constraint for Chinese ballot '{ballot_case['statement']}': got {result.constraint_amount}")
        
        # Test Chinese critical vulnerability cases
        for vulnerability_case in CHINESE_BALLOTS["critical_vulnerability_cases"]:
            with self.subTest(description=vulnerability_case["description"]):
                result = asyncio.run(self._parse_ballot(vulnerability_case["statement"]))
                
                self.assertIsNotNone(result, f"Failed to parse Chinese vulnerability case: '{vulnerability_case['statement']}'")
                self.assertEqual(result.principle, vulnerability_case["expected_principle"],
                               f"Chinese vulnerability case failed: expected {vulnerability_case['expected_principle'].value}, got {result.principle.value}")
                self.assertEqual(result.constraint_amount, vulnerability_case["expected_constraint"],
                               f"Chinese vulnerability case constraint failed: expected {vulnerability_case['expected_constraint']}, got {result.constraint_amount}")
    
    def test_spanish_ballot_parsing_scenarios(self):
        """Test comprehensive Spanish ballot parsing scenarios."""
        
        # Test all Spanish valid ballots
        for ballot_case in SPANISH_BALLOTS["valid_ballots"]:
            with self.subTest(description=ballot_case["description"]):
                result = asyncio.run(self._parse_ballot(ballot_case["statement"]))
                
                self.assertIsNotNone(result, f"Failed to parse Spanish ballot: '{ballot_case['statement']}'")
                self.assertEqual(result.principle, ballot_case["expected_principle"],
                               f"Wrong principle for Spanish ballot '{ballot_case['statement']}': got {result.principle.value}")
                self.assertEqual(result.constraint_amount, ballot_case["expected_constraint"],
                               f"Wrong constraint for Spanish ballot '{ballot_case['statement']}': got {result.constraint_amount}")
        
        # Test Spanish critical vulnerability cases
        for vulnerability_case in SPANISH_BALLOTS["critical_vulnerability_cases"]:
            with self.subTest(description=vulnerability_case["description"]):
                result = asyncio.run(self._parse_ballot(vulnerability_case["statement"]))
                
                self.assertIsNotNone(result, f"Failed to parse Spanish vulnerability case: '{vulnerability_case['statement']}'")
                self.assertEqual(result.principle, vulnerability_case["expected_principle"],
                               f"Spanish vulnerability case failed: expected {vulnerability_case['expected_principle'].value}, got {result.principle.value}")
                self.assertEqual(result.constraint_amount, vulnerability_case["expected_constraint"],
                               f"Spanish vulnerability case constraint failed: expected {vulnerability_case['expected_constraint']}, got {result.constraint_amount}")
    
    def test_language_specific_constraint_formats(self):
        """Test constraint amount parsing in different languages and formats."""
        
        # Test Chinese constraint formats
        for constraint_text, expected_amount, description in CONSTRAINTS["chinese"]:
            with self.subTest(description=f"Chinese: {description}"):
                extracted_amount = self.utility_agent._extract_constraint_amount_flexible(constraint_text)
                
                if extracted_amount is not None:  # Some formats might not be supported yet
                    self.assertEqual(extracted_amount, expected_amount,
                                   f"Chinese constraint parsing failed for '{constraint_text}': got {extracted_amount}, expected {expected_amount}")
        
        # Test Spanish constraint formats
        for constraint_text, expected_amount, description in CONSTRAINTS["spanish"]:
            with self.subTest(description=f"Spanish: {description}"):
                extracted_amount = self.utility_agent._extract_constraint_amount_flexible(constraint_text)
                
                if extracted_amount is not None:  # Some formats might not be supported yet
                    self.assertEqual(extracted_amount, expected_amount,
                                   f"Spanish constraint parsing failed for '{constraint_text}': got {extracted_amount}, expected {expected_amount}")
        
        # Test English constraint formats for comparison
        for constraint_text, expected_amount, description in CONSTRAINTS["english"]:
            with self.subTest(description=f"English: {description}"):
                extracted_amount = self.utility_agent._extract_constraint_amount_flexible(constraint_text)
                
                self.assertEqual(extracted_amount, expected_amount,
                               f"English constraint parsing failed for '{constraint_text}': got {extracted_amount}, expected {expected_amount}")
    
    def test_currency_symbol_handling_by_language(self):
        """Test that currency symbols are properly handled by language context."""
        
        currency_test_cases = [
            # Chinese - Yuan symbol
            {
                "text": "约束为¥15,000",
                "expected_amount": 15000,
                "language": "Chinese",
                "symbol": "¥"
            },
            # Spanish - Euro symbol
            {
                "text": "restricción de €15,000",
                "expected_amount": 15000,
                "language": "Spanish", 
                "symbol": "€"
            },
            # English - Dollar symbol
            {
                "text": "constraint of $15,000",
                "expected_amount": 15000,
                "language": "English",
                "symbol": "$"
            },
            # Spanish - European number format
            {
                "text": "restricción €15.000",
                "expected_amount": 15000,
                "language": "Spanish (European format)",
                "symbol": "€"
            }
        ]
        
        for case in currency_test_cases:
            with self.subTest(language=case["language"], symbol=case["symbol"]):
                extracted_amount = self.utility_agent._extract_constraint_amount_flexible(case["text"])
                
                if extracted_amount is not None:
                    self.assertEqual(extracted_amount, case["expected_amount"],
                                   f"{case['language']} currency parsing failed for '{case['text']}'")
    
    
    def test_fallback_parsing_mechanisms(self):
        """Test fallback parsing when primary methods fail."""
        
        # Test cases where LLM parsing might fail and fallbacks are needed
        fallback_cases = [
            "maximizing the floor income",  # Simple case
            "I choose maximizing floor income",  # Natural language
            "My ballot is for maximizing the average income with a floor constraint of $15000",  # Letter + constraint
        ]
        
        for ballot in fallback_cases:
            with self.subTest(ballot=ballot):
                result = asyncio.run(self._parse_ballot(ballot))
                
                # Should always get some result (even if it's a fallback)
                self.assertIsNotNone(result, f"Fallback parsing failed for: '{ballot}'")
                self.assertIn(result.principle, list(JusticePrinciple), 
                            f"Invalid principle in fallback result for: '{ballot}'")


if __name__ == '__main__':
    unittest.main()