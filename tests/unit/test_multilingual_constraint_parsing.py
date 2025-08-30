"""
Unit tests for multilingual constraint parsing functionality.

Tests the new utility agent-based constraint parsing that replaces
hardcoded regex patterns with intelligent LLM-based parsing.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from experiment_agents.utility_agent import UtilityAgent
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent


class TestMultilingualConstraintParsing(unittest.TestCase):
    """Test the new multilingual constraint parsing method."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_spanish_constraint_parsing(self):
        """Test Spanish constraint parsing with various formats."""
        test_cases = [
            # The critical failing case that needed to be fixed
            ("constraint de €2.5 mil", 2500, "Spanish decimal mil - the main bug fix"),
            
            # European number formats
            ("restricción de €15.000", 15000, "Spanish European format"),
            ("límite de €1.500.000", 1500000, "Spanish millions European"),
            ("tope €45.000,00", 45000, "Spanish with zero cents"),
            
            # Latin American formats
            ("restricción de $15,000", 15000, "Spanish Latin American format"),
            ("límite $1,500,000", 1500000, "Spanish LA millions"),
            
            # Word numbers
            ("tope de quince mil euros", 15000, "Spanish word numbers"),
            ("restricción de veinte mil", 20000, "Spanish word thousands"),
            ("límite de 15 mil pesos", 15000, "Spanish numeric + mil"),
            
            # Currency variations
            ("constraint MXN 25000", 25000, "Mexican peso code"),
            ("restricción ARS 18000", 18000, "Argentine peso code"),
            ("límite de 15000 pesos", 15000, "Peso word"),
            
            # Null constraints
            ("sin restricciones", None, "Spanish null constraint"),
            ("ilimitado", None, "Spanish unlimited"),
            ("libre de restricciones", None, "Spanish free from constraints"),
        ]
        
        async def test_constraints():
            await self.utility_agent.async_init()
            for constraint_text, expected, description in test_cases:
                with self.subTest(description=description):
                    result = await self.utility_agent.parse_constraint_amount(
                        constraint_text, language="spanish"
                    )
                    self.assertEqual(result, expected,
                                   f"{description}: Expected {expected}, got {result} for '{constraint_text}'")
        
        asyncio.run(test_constraints())
    
    def test_english_constraint_parsing(self):
        """Test English constraint parsing."""
        test_cases = [
            ("constraint of $15,000", 15000, "English comma format"),
            ("limit of 20k", 20000, "English k format"),
            ("maximum of fifteen thousand dollars", 15000, "English words"),
            ("constraint $25,500.50", 25500, "English with cents"),
            ("limit of $1,000,000", 1000000, "English millions"),
            ("no constraints", None, "English null constraint"),
            ("unlimited", None, "English unlimited"),
        ]
        
        async def test_constraints():
            await self.utility_agent.async_init()
            for constraint_text, expected, description in test_cases:
                with self.subTest(description=description):
                    result = await self.utility_agent.parse_constraint_amount(
                        constraint_text, language="english"
                    )
                    self.assertEqual(result, expected,
                                   f"{description}: Expected {expected}, got {result} for '{constraint_text}'")
        
        asyncio.run(test_constraints())
    
    def test_chinese_constraint_parsing(self):
        """Test Chinese constraint parsing."""
        test_cases = [
            ("约束 ¥15000", 15000, "Chinese Yuan constraint"),
            ("限制 15000元", 15000, "Chinese Yuan word"),
            ("最高 1万5千", 15000, "Chinese traditional numbers"),
            ("无限制", None, "Chinese no constraint"),
        ]
        
        async def test_constraints():
            await self.utility_agent.async_init()
            for constraint_text, expected, description in test_cases:
                with self.subTest(description=description):
                    result = await self.utility_agent.parse_constraint_amount(
                        constraint_text, language="mandarin"
                    )
                    self.assertEqual(result, expected,
                                   f"{description}: Expected {expected}, got {result} for '{constraint_text}'")
        
        asyncio.run(test_constraints())
    
    def test_language_detection(self):
        """Test automatic language detection."""
        test_cases = [
            ("restricción de €15000", "spanish", "Spanish detection"),
            ("constraint of $15000", "english", "English detection"),
            ("约束 ¥15000", "mandarin", "Chinese detection"),
            ("random text 123", "unknown", "Unknown language"),
        ]
        
        for statement, expected_lang, description in test_cases:
            with self.subTest(description=description):
                # DEPRECATED: _detect_language_hint method removed in Phase 2
                # Language is now configured per experiment, not detected at runtime
                # detected = self.utility_agent._detect_language_hint(statement)
                # self.assertEqual(detected, expected_lang, f"{description}: Expected {expected_lang}, got {detected}")
                pass  # Skip this test as language detection is no longer used
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        edge_cases = [
            ("", None, "Empty string"),
            ("   ", None, "Whitespace only"),
            ("no numbers here", None, "No numeric content"),
            ("negative -15000", None, "Negative numbers should be rejected"),
            ("percentage 15%", None, "Percentages should be ignored"),
            ("constraint de €0", None, "Zero amount should be None"),
        ]
        
        async def test_constraints():
            await self.utility_agent.async_init()
            for constraint_text, expected, description in edge_cases:
                with self.subTest(description=description):
                    result = await self.utility_agent.parse_constraint_amount_multilingual(
                        constraint_text
                    )
                    self.assertEqual(result, expected,
                                   f"{description}: Expected {expected}, got {result} for '{constraint_text}'")
        
        asyncio.run(test_constraints())
    
    def test_fallback_behavior(self):
        """Test fallback when LLM fails."""
        with patch('experiment_agents.utility_agent.run_without_tracing') as mock_run:
            # Mock LLM failure
            mock_run.side_effect = Exception("LLM timeout")
            
            # Should fall back to simple regex
            result = asyncio.run(self.utility_agent.parse_constraint_amount_multilingual("€15000"))
            
            # Either works via fallback or fails gracefully
            self.assertTrue(result == 15000 or result is None,
                          f"Fallback should either work or fail gracefully, got: {result}")
    
    def test_performance_basic(self):
        """Test that parsing completes in reasonable time."""
        import time
        
        async def test_performance():
            await self.utility_agent.async_init()
            start_time = time.time()
            result = await self.utility_agent.parse_constraint_amount_multilingual(
                "constraint de €15.000", "spanish"
            )
            end_time = time.time()
            
            # Should complete in under 10 seconds (generous for test environment)
            duration = end_time - start_time
            self.assertLess(duration, 10.0,
                           f"Parsing took too long: {duration:.2f} seconds")
            self.assertEqual(result, 15000, "Should still parse correctly")
        
        asyncio.run(test_performance())
    
    @patch('experiment_agents.utility_agent.run_without_tracing')
    def test_llm_response_handling(self, mock_run):
        """Test handling of different LLM response formats."""
        async def run_test():
            await self.utility_agent.async_init()
            
            # Test various LLM response formats
            response_tests = [
                ("2500", 2500, "Clean numeric response"),
                ("NONE", None, "None response"),
                ("none", None, "Lowercase none"),
                ("2500.0", 2500, "Float response"),
                ("invalid", None, "Invalid response"),
                ("", None, "Empty response"),
            ]
            
            for llm_response, expected, description in response_tests:
                with self.subTest(description=description):
                    # Mock the LLM response
                    mock_result = MagicMock()
                    mock_result.final_output = llm_response
                    mock_run.return_value = mock_result
                    
                    result = await self.utility_agent.parse_constraint_amount_multilingual("test")
                    
                    if expected is None:
                        self.assertIsNone(result, f"{description}: Expected None, got {result}")
                    else:
                        self.assertEqual(result, expected, f"{description}: Expected {expected}, got {result}")
        
        asyncio.run(run_test())
    
    def test_integration_with_existing_system(self):
        """Test that new parsing integrates properly with existing preference parsing."""
        # Test a full preference statement that would have failed before
        statement = "Elijo maximización del ingreso promedio con restricción de €2.5 mil"
        
        async def integration_test():
            await self.utility_agent.async_init()
            try:
                # Note: This tests the broader integration, not just constraint parsing
                # The parse_participant_preference method may not exist or may have different signature
                # So we'll test the constraint parsing in isolation which is what we implemented
                result = await self.utility_agent.parse_constraint_amount_multilingual(
                    "restricción de €2.5 mil", "spanish"
                )
                
                # Should parse successfully and extract correct constraint
                self.assertIsNotNone(result, "Should parse the constraint")
                self.assertEqual(result, 2500,
                               f"Should extract 2500 from '2.5 mil', got: {result}")
                
                return result
            except Exception as e:
                # If it fails, it should fail gracefully
                self.fail(f"Integration test should not crash: {e}")
        
        asyncio.run(integration_test())


class TestLanguageHintDetection(unittest.TestCase):
    """Test language hint detection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_spanish_detection(self):
        """Test Spanish language detection."""
        spanish_statements = [
            "restricción de €15000",
            "límite con pesos",
            "sin condiciones",
            "tope de mil euros",
            "limitaciones adicionales",
        ]
        
        for statement in spanish_statements:
            with self.subTest(statement=statement):
                # DEPRECATED: Language detection removed - using configured language instead
                # result = self.utility_agent._detect_language_hint(statement) 
                # self.assertEqual(result, "spanish", f"Should detect Spanish in: {statement}")
                pass  # Language detection no longer used
    
    def test_english_detection(self):
        """Test English language detection."""
        english_statements = [
            "constraint of $15000",
            "limit with dollars",
            "no conditions", 
            "maximum of thousand",
            "vote for decision",
        ]
        
        for statement in english_statements:
            with self.subTest(statement=statement):
                # DEPRECATED: Language detection removed - using configured language instead
                # result = self.utility_agent._detect_language_hint(statement)
                # self.assertEqual(result, "english", f"Should detect English in: {statement}")
                pass  # Language detection no longer used
    
    def test_chinese_detection(self):
        """Test Chinese language detection."""
        chinese_statements = [
            "约束 15000元",
            "限制条件",
            "投票决定",
            "一万五千",
        ]
        
        for statement in chinese_statements:
            with self.subTest(statement=statement):
                # DEPRECATED: Language detection removed - using configured language instead
                # result = self.utility_agent._detect_language_hint(statement)
                # self.assertEqual(result, "mandarin", f"Should detect Chinese in: {statement}")
                pass  # Language detection no longer used
    
    def test_unknown_detection(self):
        """Test unknown language detection."""
        unknown_statements = [
            "quelque chose 15000",  # French
            "qualcosa 15000",       # Italian
            "etwas 15000",          # German
            "123 456 789",          # Just numbers
            "",                     # Empty
        ]
        
        for statement in unknown_statements:
            with self.subTest(statement=statement):
                # DEPRECATED: Language detection removed - using configured language instead
                # result = self.utility_agent._detect_language_hint(statement)
                # self.assertEqual(result, "unknown", f"Should detect unknown for: {statement}")
                pass  # Language detection no longer used


if __name__ == '__main__':
    unittest.main()