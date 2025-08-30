"""
Phase 2 Enhanced Disambiguation Tests

Tests the Phase 2 enhancements to Spanish and Mandarin parsing disambiguation,
focusing on edge cases and improved runtime validation patterns.
"""

import unittest
import asyncio
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple


class TestPhase2EnhancedDisambiguation(unittest.TestCase):
    """Test Phase 2 disambiguation enhancements across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    async def _test_parsing_and_validation(self, ballot_text: str, expected_principle: str, language: str = "english") -> bool:
        """Helper to test both parsing and runtime validation."""
        await self.utility_agent.async_init()
        
        # Parse the ballot
        result = await self.utility_agent.parse_principle_choice_llm(ballot_text)
        
        # Check parsing result
        if not result or result['principle'] != expected_principle:
            return False
            
        # Check runtime validation
        is_valid = await self.utility_agent.validate_ballot_parsing_consistency(ballot_text, result, language)
        return is_valid
    
    def test_spanish_enhanced_edge_cases(self):
        """Test Spanish enhanced disambiguation for edge cases."""
        
        spanish_edge_cases = [
            # Basic principle variations that should NOT be parsed as constraints
            ("elijo maximizar los ingresos mínimos", "maximizing_floor"),
            ("prefiero maximizar el promedio", "maximizing_average"),
            ("mi elección de voto es maximizar los ingresos mínimos", "maximizing_floor"),
            ("mi voto es maximizar los ingresos promedio", "maximizing_average"),
            
            # Constraint indicators that SHOULD be parsed as constraints
            ("maximización del promedio con restricción de ingreso mínimo", "maximizing_average_floor_constraint"),
            ("con restricción de rango", "maximizing_average_range_constraint"),
            ("garantizando ingreso mínimo", "maximizing_average_floor_constraint"),
            ("limitando diferencias de ingresos", "maximizing_average_range_constraint")
        ]
        
        async def run_tests():
            for case, expected in spanish_edge_cases:
                with self.subTest(case=case):
                    result = await self._test_parsing_and_validation(case, expected, "spanish")
                    self.assertTrue(result, f"Failed for Spanish case: {case} -> expected {expected}")
        
        asyncio.run(run_tests())
    
    def test_mandarin_enhanced_edge_cases(self):
        """Test Mandarin enhanced disambiguation for edge cases."""
        
        mandarin_edge_cases = [
            # Basic principle variations that should NOT be parsed as constraints
            ("我选择最大化最低收入", "maximizing_floor"),
            ("我倾向最大化平均", "maximizing_average"),
            ("我的投票选择是最大化最低收入", "maximizing_floor"),
            ("我的票是最大化平均收入", "maximizing_average"),
            
            # Constraint indicators that SHOULD be parsed as constraints
            ("在最低收入约束条件下", "maximizing_average_floor_constraint"),
            ("在范围约束条件下", "maximizing_average_range_constraint"),
            ("保证最低收入", "maximizing_average_floor_constraint"),
            ("限制收入差异", "maximizing_average_range_constraint")
        ]
        
        async def run_tests():
            for case, expected in mandarin_edge_cases:
                with self.subTest(case=case):
                    result = await self._test_parsing_and_validation(case, expected, "mandarin")
                    self.assertTrue(result, f"Failed for Mandarin case: {case} -> expected {expected}")
        
        asyncio.run(run_tests())
    
    def test_cross_language_consistency(self):
        """Test that equivalent phrases across languages parse consistently."""
        
        equivalent_phrases = [
            # Basic floor principle
            ("My ballot choice is maximizing the floor income", "english", "maximizing_floor"),
            ("Mi elección de voto es maximización del ingreso mínimo", "spanish", "maximizing_floor"), 
            ("我的投票选择是最大化最低收入", "mandarin", "maximizing_floor"),
            
            # Basic average principle
            ("My ballot choice is maximizing the average income", "english", "maximizing_average"),
            ("Mi elección de voto es maximización del ingreso promedio", "spanish", "maximizing_average"),
            ("我的投票选择是最大化平均收入", "mandarin", "maximizing_average"),
        ]
        
        async def run_tests():
            for phrase, language, expected in equivalent_phrases:
                with self.subTest(phrase=phrase, language=language):
                    result = await self._test_parsing_and_validation(phrase, expected, language)
                    self.assertTrue(result, f"Failed for {language} phrase: {phrase}")
        
        asyncio.run(run_tests())
    
    def test_runtime_validation_accuracy(self):
        """Test that runtime validation correctly identifies parsing mismatches."""
        
        async def test_validation():
            await self.utility_agent.async_init()
            
            # Test case that should validate correctly
            correct_case = "My ballot choice is maximizing the floor income"
            correct_result = {'principle': 'maximizing_floor', 'constraint_amount': None}
            is_valid_correct = await self.utility_agent.validate_ballot_parsing_consistency(
                correct_case, correct_result, 'english'
            )
            self.assertTrue(is_valid_correct, "Should validate correctly parsed result")
            
            # Test case that should fail validation (simulate old bug)
            incorrect_result = {'principle': 'maximizing_average_floor_constraint', 'constraint_amount': None}
            is_valid_incorrect = await self.utility_agent.validate_ballot_parsing_consistency(
                correct_case, incorrect_result, 'english'
            )
            self.assertFalse(is_valid_incorrect, "Should detect parsing mismatch")
        
        asyncio.run(test_validation())


if __name__ == '__main__':
    unittest.main()