"""
Critical Ballot Parsing Fix Tests - Real World Ballot Formats

Tests exact ballot formats used in real experiments across languages.
Based on Critical_Ballot_Parsing_Fix_Plan.md - addresses systematic misparsing
of real experiment votes where agents say "My ballot choice is maximizing the floor income"
but the system incorrectly parses this as maximizing_average_floor_constraint.

These tests validate the enhanced LLM parsing prompts with disambiguation examples.
"""

import unittest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from utils.error_handling import ValidationError


class TestRealWorldBallotParsing(unittest.TestCase):
    """Test exact ballot formats used in real experiments across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    async def _parse_ballot(self, ballot_text: str, language: str = "english") -> PrincipleChoice:
        """Helper to parse ballot text with language specification."""
        await self.utility_agent.async_init()
        
        # Set the language context for the utility agent
        if hasattr(self.utility_agent, 'language_manager'):
            self.utility_agent.language_manager.set_language(language)
            
        # Parse using the enhanced parsing method
        result_dict = await self.utility_agent.parse_principle_choice_llm(ballot_text)
        
        # Convert to PrincipleChoice if we got a valid result
        if result_dict and 'principle' in result_dict:
            # Map principle name to enum
            principle_name = result_dict['principle']
            principle_mapping = {
                'maximizing_floor': JusticePrinciple.MAXIMIZING_FLOOR,
                'maximizing_average': JusticePrinciple.MAXIMIZING_AVERAGE,
                'maximizing_average_floor_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'maximizing_average_range_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                'maximizing floor': JusticePrinciple.MAXIMIZING_FLOOR,
                'maximizing average': JusticePrinciple.MAXIMIZING_AVERAGE,
                'floor constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'range constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                'maximizing_floor_income': JusticePrinciple.MAXIMIZING_FLOOR,
                'maximizing_average_income': JusticePrinciple.MAXIMIZING_AVERAGE,
            }
            
            principle = principle_mapping.get(principle_name.lower())
            if not principle:
                # Try direct match for other names
                for enum_val in JusticePrinciple:
                    if principle_name.lower() in [enum_val.value.lower(), enum_val.name.lower()]:
                        principle = enum_val
                        break
                        
            if not principle:
                raise ValueError(f"Unknown principle: {principle_name}")
                
            certainty_mapping = {
                'very_unsure': CertaintyLevel.VERY_UNSURE,
                'unsure': CertaintyLevel.UNSURE,
                'sure': CertaintyLevel.SURE,
                'very_sure': CertaintyLevel.VERY_SURE
            }
            
            certainty = certainty_mapping.get(result_dict.get('certainty', 'sure'), CertaintyLevel.SURE)
            
            return PrincipleChoice(
                principle=principle,
                constraint_amount=result_dict.get('constraint_amount'),
                certainty=certainty,
                reasoning=result_dict.get('reasoning', '')
            )
        else:
            raise ValueError(f"Failed to parse ballot: {ballot_text}")
    
    def test_english_real_world_ballots(self):
        """Test English ballot parsing with exact real experiment formats.
        
        These are the exact formats that were systematically misparsed in production,
        where "My ballot choice is maximizing the floor income" was incorrectly parsed
        as maximizing_average_floor_constraint instead of maximizing_floor.
        """
        
        real_ballot_cases = [
            # Basic floor principle - this was the critical failure case
            {
                "ballot": "My ballot choice is maximizing the floor income",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Critical case from experiment_results_20250829_231553.json"
            },
            {
                "ballot": "My ballot choice is maximizing the floor income.",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "With period punctuation"
            },
            
            # Basic average principle
            {
                "ballot": "My ballot choice is maximizing the average income",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Basic average income principle"
            },
            {
                "ballot": "My ballot choice is maximizing the average income.",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Average with period punctuation"
            },
            
            # Floor constraint principle with various constraint amounts
            {
                "ballot": "My ballot choice is maximizing average with floor constraint of $15000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000,
                "description": "Floor constraint without period"
            },
            {
                "ballot": "My ballot choice is maximizing average with floor constraint of $15,000.",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000,
                "description": "Floor constraint with comma and period"
            },
            {
                "ballot": "My ballot choice is maximizing the average income with a floor constraint with a floor constraint of $13,000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 13000,
                "description": "Verbose floor constraint format"
            },
            
            # Range constraint principle
            {
                "ballot": "My ballot choice is maximizing average with range constraint of $20000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 20000,
                "description": "Range constraint format"
            },
            {
                "ballot": "My ballot choice is maximizing the average income with a range constraint with a range constraint of $25,000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 25000,
                "description": "Verbose range constraint format"
            },
            
            # Natural language variations that should parse correctly
            {
                "ballot": "I choose the principle that considers only the welfare of the worst-off",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Natural language floor description"
            },
            {
                "ballot": "My choice is the most just distribution that maximizes the floor income",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Formal floor description"
            }
        ]
        
        async def run_tests():
            for case in real_ballot_cases:
                with self.subTest(case=case["description"]):
                    result = await self._parse_ballot(case["ballot"])
                    
                    self.assertEqual(
                        result.principle, case["expected_principle"],
                        f"Failed for {case['description']}: {case['ballot']} -> "
                        f"Got {result.principle.value}, expected {case['expected_principle'].value}"
                    )
                    self.assertEqual(
                        result.constraint_amount, case["expected_constraint"],
                        f"Constraint amount mismatch for {case['description']}"
                    )
        
        asyncio.run(run_tests())
    
    def test_spanish_real_world_ballots(self):
        """Test Spanish ballot parsing with real experiment formats."""
        
        spanish_ballot_cases = [
            # Basic floor principle in Spanish
            {
                "ballot": "Mi elección de voto es maximización del ingreso mínimo",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Spanish floor income choice"
            },
            {
                "ballot": "Mi elección de voto es maximización del ingreso mínimo.",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Spanish floor income with period"
            },
            
            # Basic average principle in Spanish
            {
                "ballot": "Mi elección de voto es maximización del ingreso promedio",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Spanish average income choice"
            },
            {
                "ballot": "Mi elección de voto es maximización del ingreso promedio.",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Spanish average income with period"
            },
            
            # Floor constraint in Spanish with Euro currency
            {
                "ballot": "Mi elección de voto es maximización del promedio con restricción de ingreso mínimo de €15000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000,
                "description": "Spanish floor constraint with Euro"
            },
            {
                "ballot": "Mi elección de boleta es maximizar los ingresos promedio con restricción de ingreso mínimo con restricción de mínimo de €13,000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 13000,
                "description": "Verbose Spanish floor constraint"
            },
            
            # Range constraint in Spanish
            {
                "ballot": "Mi elección de voto es maximización del promedio con restricción de rango de €20000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 20000,
                "description": "Spanish range constraint"
            },
            
            # Natural language Spanish variations
            {
                "ballot": "Elijo el principio que considera solo el bienestar de los más desfavorecidos",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Spanish natural language floor"
            }
        ]
        
        async def run_tests():
            for case in spanish_ballot_cases:
                with self.subTest(case=case["description"]):
                    result = await self._parse_ballot(case["ballot"], language="spanish")
                    
                    self.assertEqual(
                        result.principle, case["expected_principle"],
                        f"Failed for {case['description']}: {case['ballot']} -> "
                        f"Got {result.principle.value}, expected {case['expected_principle'].value}"
                    )
                    self.assertEqual(
                        result.constraint_amount, case["expected_constraint"],
                        f"Constraint amount mismatch for {case['description']}"
                    )
        
        asyncio.run(run_tests())
    
    def test_mandarin_real_world_ballots(self):
        """Test Mandarin ballot parsing with real experiment formats."""
        
        mandarin_ballot_cases = [
            # Basic floor principle in Mandarin
            {
                "ballot": "我的投票选择是最大化最低收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Mandarin floor income choice"
            },
            {
                "ballot": "我的投票选择是最大化最低收入。",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Mandarin floor income with period"
            },
            
            # Basic average principle in Mandarin
            {
                "ballot": "我的投票选择是最大化平均收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Mandarin average income choice"
            },
            {
                "ballot": "我的投票选择是最大化平均收入。",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Mandarin average income with period"
            },
            
            # Floor constraint in Mandarin with Yuan currency
            {
                "ballot": "我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥15000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000,
                "description": "Mandarin floor constraint with Yuan"
            },
            {
                "ballot": "我的投票选择是在最低收入约束条件下最大化平均收入，最低约束为¥10",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 10,
                "description": "Small Yuan constraint amount"
            },
            
            # Range constraint in Mandarin
            {
                "ballot": "我的投票选择是在范围约束条件下最大化平均收入，约束为¥20000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 20000,
                "description": "Mandarin range constraint"
            },
            
            # Natural language Mandarin variations
            {
                "ballot": "我选择只考虑最弱势者福利的原则",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None,
                "description": "Mandarin natural language floor"
            },
            {
                "ballot": "也许是最大化平均收入的那个？",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None,
                "description": "Uncertain Mandarin average choice"
            }
        ]
        
        async def run_tests():
            for case in mandarin_ballot_cases:
                with self.subTest(case=case["description"]):
                    result = await self._parse_ballot(case["ballot"], language="mandarin")
                    
                    self.assertEqual(
                        result.principle, case["expected_principle"],
                        f"Failed for {case['description']}: {case['ballot']} -> "
                        f"Got {result.principle.value}, expected {case['expected_principle'].value}"
                    )
                    self.assertEqual(
                        result.constraint_amount, case["expected_constraint"],
                        f"Constraint amount mismatch for {case['description']}"
                    )
        
        asyncio.run(run_tests())
    
    def test_critical_disambiguation_scenarios(self):
        """Test the critical disambiguation scenarios that cause systematic errors.
        
        These test the core issue: distinguishing between basic principles and 
        constraint principles when similar language is used.
        """
        
        critical_cases = [
            # English disambiguation
            {
                "ballot": "maximizing THE floor income",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "language": "english",
                "description": "THE indicates basic principle, not constraint"
            },
            {
                "ballot": "maximizing THE average income", 
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "language": "english",
                "description": "THE indicates basic principle, not constraint"
            },
            {
                "ballot": "maximizing average WITH floor constraint",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "language": "english", 
                "description": "WITH indicates constraint principle"
            },
            
            # Spanish disambiguation  
            {
                "ballot": "maximización DEL ingreso mínimo",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "language": "spanish",
                "description": "DEL indicates basic principle, not constraint"
            },
            {
                "ballot": "maximización DEL ingreso promedio",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "language": "spanish",
                "description": "DEL indicates basic principle, not constraint"
            },
            {
                "ballot": "maximización del promedio CON restricción",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "language": "spanish",
                "description": "CON restricción indicates constraint principle"
            },
            
            # Mandarin disambiguation
            {
                "ballot": "最大化最低收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "language": "mandarin", 
                "description": "Direct phrase indicates basic floor principle"
            },
            {
                "ballot": "最大化平均收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "language": "mandarin",
                "description": "Direct phrase indicates basic average principle"
            },
            {
                "ballot": "在最低收入约束条件下最大化平均收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "language": "mandarin",
                "description": "约束条件 indicates constraint principle"
            }
        ]
        
        async def run_tests():
            for case in critical_cases:
                with self.subTest(case=case["description"]):
                    result = await self._parse_ballot(case["ballot"], language=case["language"])
                    
                    self.assertEqual(
                        result.principle, case["expected_principle"],
                        f"Critical disambiguation failed for {case['description']}: "
                        f"{case['ballot']} -> Got {result.principle.value}, "
                        f"expected {case['expected_principle'].value}"
                    )
        
        asyncio.run(run_tests())
    
    def test_constraint_amount_preservation(self):
        """Test that exact constraint amounts are preserved correctly.
        
        The plan specifies: "IMPORTANT: Preserve exact dollar amounts as stated - $10 means 10, not 10000"
        """
        
        constraint_cases = [
            {
                "ballot": "My ballot choice is maximizing average with floor constraint of $10",
                "expected_amount": 10,
                "language": "english",
                "description": "$10 should be 10, not 10000"
            },
            {
                "ballot": "My ballot choice is maximizing average with floor constraint of $15000",
                "expected_amount": 15000,
                "language": "english", 
                "description": "$15000 should be preserved exactly"
            },
            {
                "ballot": "Mi elección es maximización con restricción de €25000",
                "expected_amount": 25000,
                "language": "spanish",
                "description": "Euro amounts should be preserved"
            },
            {
                "ballot": "约束为¥5000的最大化平均收入",
                "expected_amount": 5000,
                "language": "mandarin",
                "description": "Yuan amounts should be preserved"
            }
        ]
        
        async def run_tests():
            for case in constraint_cases:
                with self.subTest(case=case["description"]):
                    result = await self._parse_ballot(case["ballot"], language=case["language"])
                    
                    self.assertEqual(
                        result.constraint_amount, case["expected_amount"],
                        f"Constraint amount not preserved for {case['description']}: "
                        f"Got {result.constraint_amount}, expected {case['expected_amount']}"
                    )
        
        asyncio.run(run_tests())


if __name__ == '__main__':
    unittest.main()