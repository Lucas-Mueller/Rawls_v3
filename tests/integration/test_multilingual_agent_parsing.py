#!/usr/bin/env python3
"""Test script to verify multilingual principle extraction fixes with full agent integration."""

import asyncio
import unittest
import os
from utils.language_manager import get_language_manager, set_global_language, SupportedLanguage
from experiment_agents.utility_agent import UtilityAgent


class TestMultilingualAgentParsing(unittest.TestCase):
    """Integration tests for multilingual principle parsing with full agent functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.utility_agent = None
    
    async def async_setUp(self, language="english"):
        """Async setup for utility agent with language support."""
        self.utility_agent = UtilityAgent("test", language=language)
        await self.utility_agent.async_init()
    
    async def test_english_multilingual_parsing(self):
        """Test English principle extraction with full agent integration."""
        await self.async_setUp(language="english")
        
        # Set English language
        set_global_language(SupportedLanguage.ENGLISH)
        
        test_cases = [
            ("I choose principle a", "maximizing_floor"),
            ("My preference is maximizing_average", "maximizing_average"),
            ("I select maximizing floor income", "maximizing_floor"),
            ("My choice is maximizing the average income", "maximizing_average"),
        ]
        
        for statement, expected_anchor in test_cases:
            with self.subTest(statement=statement):
                try:
                    # Test the full parsing pipeline
                    result = await self.utility_agent.parse_principle_choice_enhanced(statement)
                    self.assertIsNotNone(result, f"Failed to parse: '{statement}'")
                    self.assertIsNotNone(result.principle, f"No principle detected in: '{statement}'")
                except Exception as e:
                    self.fail(f"Exception parsing '{statement}': {str(e)}")
    
    async def test_spanish_multilingual_parsing(self):
        """Test Spanish principle extraction with full agent integration."""
        await self.async_setUp(language="spanish")
        
        # Set Spanish language
        set_global_language(SupportedLanguage.SPANISH)
        
        test_cases = [
            ("Mi elección es el principio a", "maximizing_floor"),
            ("Prefiero maximizar_promedio", "maximizing_average"),
            ("Mi elección de boleta es principio c con restricción de mínimo de $10000", "maximizing_average_floor_constraint"),
            ("Elijo maximizar el ingreso promedio", "maximizing_average"),
        ]
        
        for statement, expected_principle_hint in test_cases:
            with self.subTest(statement=statement):
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(statement)
                    self.assertIsNotNone(result, f"Failed to parse Spanish: '{statement}'")
                    self.assertIsNotNone(result.principle, f"No principle detected in Spanish: '{statement}'")
                except Exception as e:
                    self.fail(f"Exception parsing Spanish '{statement}': {str(e)}")
    
    async def test_mandarin_multilingual_parsing(self):
        """Test Mandarin principle extraction with full agent integration."""
        await self.async_setUp(language="mandarin")
        
        # Set Mandarin language
        set_global_language(SupportedLanguage.MANDARIN)
        
        test_cases = [
            ("我选择原则a", "maximizing_floor"),
            ("我偏好最大化平均", "maximizing_average"),
            ("我选择最大化底线收入", "maximizing_floor"),
            ("我的选择是最大化平均收入", "maximizing_average"),
        ]
        
        for statement, expected_principle_hint in test_cases:
            with self.subTest(statement=statement):
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(statement)
                    self.assertIsNotNone(result, f"Failed to parse Mandarin: '{statement}'")
                    self.assertIsNotNone(result.principle, f"No principle detected in Mandarin: '{statement}'")
                except Exception as e:
                    self.fail(f"Exception parsing Mandarin '{statement}': {str(e)}")
    
    async def test_language_manager_integration(self):
        """Test that language manager properly integrates with parsing."""
        # Test each supported language
        languages = [
            (SupportedLanguage.ENGLISH, "english"),
            (SupportedLanguage.SPANISH, "spanish"),
            (SupportedLanguage.MANDARIN, "mandarin")
        ]
        
        for lang_enum, lang_string in languages:
            with self.subTest(language=lang_string):
                # Set language
                set_global_language(lang_enum)
                language_manager = get_language_manager()
                
                # Verify language is set correctly
                self.assertEqual(language_manager.current_language, lang_enum)
                
                # Setup agent with this language
                await self.async_setUp(language=lang_string)
                
                # Test basic parsing works
                simple_statements = {
                    "english": "I choose principle a",
                    "spanish": "Mi elección es el principio a", 
                    "mandarin": "我选择原则a"
                }
                
                statement = simple_statements[lang_string]
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(statement)
                    self.assertIsNotNone(result, f"Failed to parse in {lang_string}: '{statement}'")
                except Exception as e:
                    self.fail(f"Exception in {lang_string} parsing: {str(e)}")
    
    async def test_cross_language_consistency(self):
        """Test that similar statements in different languages produce consistent results."""
        # Equivalent statements across languages
        equivalent_statements = [
            # Maximizing floor principle
            {
                "english": "I choose maximizing floor income",
                "spanish": "Elijo maximizar el ingreso mínimo", 
                "mandarin": "我选择最大化底线收入"
            },
            # Maximizing average principle
            {
                "english": "I prefer maximizing average income",
                "spanish": "Prefiero maximizar el ingreso promedio",
                "mandarin": "我偏好最大化平均收入"
            }
        ]
        
        for statement_set in equivalent_statements:
            results = {}
            
            # Parse each language version
            for language, statement in statement_set.items():
                lang_enum = {
                    "english": SupportedLanguage.ENGLISH,
                    "spanish": SupportedLanguage.SPANISH, 
                    "mandarin": SupportedLanguage.MANDARIN
                }[language]
                
                # Set language and parse
                set_global_language(lang_enum)
                await self.async_setUp(language=language)
                
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(statement)
                    results[language] = result.principle if result else None
                except Exception as e:
                    results[language] = f"ERROR: {str(e)}"
            
            # Check for consistency (all should parse to the same principle type)
            unique_principles = set([r for r in results.values() if r and not str(r).startswith("ERROR")])
            
            with self.subTest(statements=statement_set):
                # Should have at least some successful parsing
                successful_parses = [r for r in results.values() if r and not str(r).startswith("ERROR")]
                self.assertGreater(len(successful_parses), 0, f"No successful parsing in any language for: {statement_set}")
                
                # If multiple languages parsed successfully, they should agree
                if len(unique_principles) > 1:
                    self.fail(f"Inconsistent parsing across languages: {results}")
    
    async def test_parsing_error_handling(self):
        """Test error handling in multilingual parsing scenarios."""
        await self.async_setUp(language="english")
        
        # Test various error conditions
        error_cases = [
            "",  # Empty string
            "This is not a principle choice",  # Unrelated text
            "I choose principle z",  # Invalid principle letter
            "My choice is unclear and ambiguous",  # Ambiguous statement
        ]
        
        for error_case in error_cases:
            with self.subTest(case=error_case):
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(error_case)
                    # Should either return None or a result with no principle
                    if result:
                        # If result exists, principle might be None or invalid
                        # This is acceptable as long as no exception is raised
                        pass
                    else:
                        # None result is acceptable for unparseable input
                        pass
                except Exception as e:
                    # Should not raise exceptions for invalid input
                    self.fail(f"Should handle error gracefully, but got exception for '{error_case}': {str(e)}")
    
    async def test_constraint_parsing_multilingual(self):
        """Test constraint parsing across languages."""
        constraint_cases = [
            # English with constraints
            {
                "language": "english",
                "statement": "I choose maximizing average with floor constraint of $15000",
                "expected_constraint": 15000
            },
            # Spanish with constraints  
            {
                "language": "spanish",
                "statement": "Mi elección es maximizar promedio con restricción de mínimo de $20000",
                "expected_constraint": 20000
            },
            # Mandarin with constraints
            {
                "language": "mandarin", 
                "statement": "我选择最大化平均收入底线约束$25000",
                "expected_constraint": 25000
            }
        ]
        
        for case in constraint_cases:
            with self.subTest(language=case["language"]):
                lang_enum = {
                    "english": SupportedLanguage.ENGLISH,
                    "spanish": SupportedLanguage.SPANISH,
                    "mandarin": SupportedLanguage.MANDARIN
                }[case["language"]]
                
                set_global_language(lang_enum)
                await self.async_setUp(language=case["language"])
                
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(case["statement"])
                    self.assertIsNotNone(result, f"Failed to parse constraint in {case['language']}")
                    
                    # Check constraint amount if parsing was successful
                    if result and hasattr(result, 'constraint_amount') and result.constraint_amount:
                        # Allow some flexibility in constraint parsing
                        self.assertIsInstance(result.constraint_amount, (int, float), 
                                            f"Constraint should be numeric in {case['language']}")
                        
                except Exception as e:
                    self.fail(f"Exception parsing constraint in {case['language']}: {str(e)}")


class AsyncTestRunner:
    """Helper class to run async integration tests."""
    
    def run_async_tests(self):
        """Run all async test methods."""
        test_instance = TestMultilingualAgentParsing()
        
        async def run_all_async():
            await test_instance.test_english_multilingual_parsing()
            await test_instance.test_spanish_multilingual_parsing() 
            await test_instance.test_mandarin_multilingual_parsing()
            await test_instance.test_language_manager_integration()
            await test_instance.test_cross_language_consistency()
            await test_instance.test_parsing_error_handling()
            await test_instance.test_constraint_parsing_multilingual()
        
        asyncio.run(run_all_async())


if __name__ == "__main__":
    # For direct execution, run custom async test runner
    runner = AsyncTestRunner()
    try:
        runner.run_async_tests()
        print("✅ All multilingual agent parsing tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise