"""
Comprehensive unit tests for Phase 2 ballot parsing with post-parse corrections.

Tests the sophisticated ballot parsing logic that handles:
1. LLM JSON parsing with fallback mechanisms
2. Post-parse correction logic for principle c/d mentions
3. Constraint amount extraction and validation
4. Multilingual principle canonicalization
5. Ballot consensus checking with detailed disagreement analysis

Critical parsing vulnerabilities tested:
- "principle a with no additional constraints" -> maximizing_floor (not floor_constraint)
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
                "ballot": "principle a with no additional constraints",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "principle a + no constraints should be maximizing_floor"
            },
            {
                "ballot": "My ballot choice is principle a with no constraints", 
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Extended form should still be maximizing_floor"
            },
            {
                "ballot": "I choose principle a without any constraint",
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
        """Test post-parse correction for principle c/d mentions."""
        
        correction_cases = [
            {
                "ballot": "I vote for principle c with $15000 constraint",
                "raw_principle": "maximizing_average",  # What LLM might parse incorrectly
                "mentions": "principle c",
                "expected_corrected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000
            },
            {
                "ballot": "My choice is principle d with range constraint of $20000",
                "raw_principle": "maximizing_average", 
                "mentions": "principle d",
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
    async def test_llm_json_extraction_robustness(self, mock_runner):
        """Test JSON extraction from various LLM response formats."""
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
            
            # Letter-based (backward compatibility)
            ("a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("b", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("c", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            ("d", JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT),
            
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
    
    def test_fallback_parsing_mechanisms(self):
        """Test fallback parsing when primary methods fail."""
        
        # Test cases where LLM parsing might fail and fallbacks are needed
        fallback_cases = [
            "principle a",  # Simple case
            "I choose maximizing floor income",  # Natural language
            "My ballot is for principle c with $15000",  # Letter + constraint
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