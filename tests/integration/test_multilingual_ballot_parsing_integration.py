"""
Multilingual Integration Tests for Critical Ballot Parsing Fixes

Tests the complete multilingual ballot parsing system with enhanced prompts
and runtime validation. Covers full integration across languages including
edge cases, constraint handling, and systematic error prevention.
"""

import unittest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from utils.error_handling import ValidationError


class TestMultilingualBallotParsingIntegration(unittest.TestCase):
    """Integration tests for multilingual ballot parsing with enhanced prompts."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    async def _parse_and_validate(self, ballot_text: str, language: str = "english") -> tuple[PrincipleChoice, bool]:
        """Helper to parse ballot and validate with runtime validation system."""
        await self.utility_agent.async_init()
        
        # Parse the ballot
        parsed_result = await self.utility_agent.parse_principle_choice_llm(ballot_text, language=language)
        
        # Validate with runtime system
        is_consistent = await self.utility_agent.validate_ballot_parsing_consistency(
            ballot_text, parsed_result, language=language
        )
        
        return parsed_result, is_consistent
    
    def test_cross_language_consistency(self):
        """Test that equivalent ballot formats across languages parse to same principles."""
        
        equivalent_ballots = [
            # Floor principle across languages
            {
                "english": "My ballot choice is maximizing the floor income",
                "spanish": "Mi elección de voto es maximización del ingreso mínimo",
                "mandarin": "我的投票选择是最大化最低收入",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR
            },
            
            # Average principle across languages
            {
                "english": "My ballot choice is maximizing the average income", 
                "spanish": "Mi elección de voto es maximización del ingreso promedio",
                "mandarin": "我的投票选择是最大化平均收入",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE
            },
            
            # Floor constraint principle across languages
            {
                "english": "My ballot choice is maximizing average with floor constraint of $15000",
                "spanish": "Mi elección de voto es maximización del promedio con restricción de ingreso mínimo de €15000",
                "mandarin": "我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥15000",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            }
        ]
        
        async def run_tests():
            for case in equivalent_ballots:
                expected_principle = case["expected"]
                
                for language in ["english", "spanish", "mandarin"]:
                    with self.subTest(language=language, case=case[language]):
                        ballot = case[language]
                        result, is_consistent = await self._parse_and_validate(ballot, language)
                        
                        # Assert correct principle parsing
                        self.assertEqual(
                            result.principle, expected_principle,
                            f"Language {language}: '{ballot}' parsed as {result.principle.value}, expected {expected_principle.value}"
                        )
                        
                        # Assert runtime validation passes
                        self.assertTrue(
                            is_consistent,
                            f"Runtime validation failed for {language}: '{ballot}'"
                        )
        
        asyncio.run(run_tests())
    
    def test_constraint_amount_multilingual(self):
        """Test constraint amount parsing across different currencies and formats."""
        
        constraint_cases = [
            # English with USD
            {
                "ballot": "My ballot choice is maximizing average with floor constraint of $25000",
                "language": "english",
                "expected_amount": 25000
            },
            
            # Spanish with Euro
            {
                "ballot": "Mi elección de voto es maximización del promedio con restricción de rango de €18000",
                "language": "spanish", 
                "expected_amount": 18000
            },
            
            # Mandarin with Yuan
            {
                "ballot": "我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥22000",
                "language": "mandarin",
                "expected_amount": 22000
            },
            
            # Mixed formats
            {
                "ballot": "Mi elección es maximización con restricción de €15,000",
                "language": "spanish",
                "expected_amount": 15000
            },
            
            {
                "ballot": "我选择约束为¥30000的原则",
                "language": "mandarin", 
                "expected_amount": 30000
            }
        ]
        
        async def run_tests():
            for case in constraint_cases:
                with self.subTest(case=case["ballot"]):
                    result, is_consistent = await self._parse_and_validate(
                        case["ballot"], case["language"]
                    )
                    
                    self.assertEqual(
                        result.constraint_amount, case["expected_amount"],
                        f"Constraint amount mismatch for '{case['ballot']}': got {result.constraint_amount}, expected {case['expected_amount']}"
                    )
                    
                    self.assertTrue(
                        is_consistent,
                        f"Runtime validation failed for constraint case: '{case['ballot']}'"
                    )
        
        asyncio.run(run_tests())
    
    def test_disambiguation_integration(self):
        """Test critical disambiguation cases with full integration."""
        
        disambiguation_cases = [
            # English - THE vs WITH disambiguation
            {
                "ballot": "maximizing THE floor income",
                "language": "english",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR,
                "description": "THE indicates basic principle"
            },
            {
                "ballot": "maximizing average WITH floor constraint",
                "language": "english", 
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "description": "WITH indicates constraint principle"
            },
            
            # Spanish - DEL vs CON disambiguation
            {
                "ballot": "maximización DEL ingreso promedio",
                "language": "spanish",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE,
                "description": "DEL indicates basic principle"
            },
            {
                "ballot": "maximización del promedio CON restricción de rango",
                "language": "spanish",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "description": "CON indicates constraint principle"
            },
            
            # Mandarin - Direct vs constraint phrase disambiguation
            {
                "ballot": "最大化平均收入",
                "language": "mandarin",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE,
                "description": "Direct phrase indicates basic principle"
            },
            {
                "ballot": "在范围约束条件下最大化平均收入",
                "language": "mandarin",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 
                "description": "Constraint phrase indicates constraint principle"
            }
        ]
        
        async def run_tests():
            for case in disambiguation_cases:
                with self.subTest(case=case["description"]):
                    result, is_consistent = await self._parse_and_validate(
                        case["ballot"], case["language"] 
                    )
                    
                    self.assertEqual(
                        result.principle, case["expected"],
                        f"Disambiguation failed for {case['description']}: '{case['ballot']}' parsed as {result.principle.value}, expected {case['expected'].value}"
                    )
                    
                    self.assertTrue(
                        is_consistent,
                        f"Runtime validation failed for disambiguation case: {case['description']}"
                    )
        
        asyncio.run(run_tests())
    
    def test_systematic_error_prevention(self):
        """Test prevention of the specific systematic errors identified in production."""
        
        # These are the exact cases that were failing in production
        systematic_error_cases = [
            {
                "ballot": "My ballot choice is maximizing the floor income",
                "language": "english",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR,
                "description": "Critical English systematic error case"
            },
            {
                "ballot": "Mi elección de voto es maximización del ingreso mínimo",
                "language": "spanish", 
                "expected": JusticePrinciple.MAXIMIZING_FLOOR,
                "description": "Critical Spanish systematic error case"
            },
            {
                "ballot": "我的投票选择是最大化最低收入",
                "language": "mandarin",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR,
                "description": "Critical Mandarin systematic error case"
            }
        ]
        
        async def run_tests():
            for case in systematic_error_cases:
                with self.subTest(case=case["description"]):
                    result, is_consistent = await self._parse_and_validate(
                        case["ballot"], case["language"]
                    )
                    
                    # This MUST parse correctly - these are the exact cases that were failing
                    self.assertEqual(
                        result.principle, case["expected"],
                        f"SYSTEMATIC ERROR STILL OCCURRING: {case['description']} - '{case['ballot']}' parsed as {result.principle.value}, should be {case['expected'].value}"
                    )
                    
                    # Runtime validation MUST pass
                    self.assertTrue(
                        is_consistent,
                        f"Runtime validation failed for systematic error case: {case['description']}"
                    )
        
        asyncio.run(run_tests())
    
    def test_end_to_end_multilingual_workflow(self):
        """Test complete multilingual ballot parsing workflow."""
        
        workflow_cases = [
            {
                "participant": "Agent_1",
                "language": "english",
                "ballots": [
                    "My ballot choice is maximizing the floor income",
                    "My ballot choice is maximizing average with floor constraint of $15000"
                ]
            },
            {
                "participant": "Agent_2", 
                "language": "spanish",
                "ballots": [
                    "Mi elección de voto es maximización del ingreso promedio",
                    "Mi elección es maximización con restricción de €20000"
                ]
            },
            {
                "participant": "Agent_3",
                "language": "mandarin", 
                "ballots": [
                    "我的投票选择是最大化最低收入",
                    "我选择在范围约束条件下最大化平均收入，约束¥25000"
                ]
            }
        ]
        
        async def run_tests():
            for participant in workflow_cases:
                for i, ballot in enumerate(participant["ballots"]):
                    with self.subTest(participant=participant["participant"], ballot_num=i+1):
                        result, is_consistent = await self._parse_and_validate(
                            ballot, participant["language"]
                        )
                        
                        # All parsing should succeed
                        self.assertIsNotNone(result)
                        self.assertIsNotNone(result.principle)
                        
                        # All runtime validation should pass
                        self.assertTrue(
                            is_consistent,
                            f"Runtime validation failed for {participant['participant']} ballot {i+1}: '{ballot}'"
                        )
                        
                        # Constraint ballots should have constraint amounts
                        if any(constraint_word in ballot.lower() for constraint_word in ["constraint", "restricción", "约束条件"]):
                            self.assertIsNotNone(
                                result.constraint_amount,
                                f"Missing constraint amount for {participant['participant']} ballot {i+1}: '{ballot}'"
                            )
        
        asyncio.run(run_tests())
    
    def test_error_detection_and_recovery(self):
        """Test error detection with runtime validation and recovery mechanisms."""
        
        # These should be detected as problematic by runtime validation
        problematic_cases = [
            # Hypothetical misparsing scenarios that validation should catch
            {
                "ballot": "My ballot choice is maximizing the floor income",
                "language": "english",
                "correct_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "description": "Floor income statement"
            }
        ]
        
        async def run_tests():
            for case in problematic_cases:
                with self.subTest(case=case["description"]):
                    result, is_consistent = await self._parse_and_validate(
                        case["ballot"], case["language"]
                    )
                    
                    # If parsing is correct, validation should pass
                    if result.principle == case["correct_principle"]:
                        self.assertTrue(
                            is_consistent,
                            f"Correct parsing should pass validation: {case['description']}"
                        )
                    else:
                        # If parsing is wrong, validation should catch it
                        self.assertFalse(
                            is_consistent,
                            f"Incorrect parsing should fail validation: {case['description']}"
                        )
        
        asyncio.run(run_tests())


if __name__ == '__main__':
    unittest.main()