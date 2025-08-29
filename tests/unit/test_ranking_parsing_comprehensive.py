#!/usr/bin/env python3
"""
Comprehensive test script to validate the ranking parsing fix works across various formats,
including parsing vulnerability tests to identify and fix parsing errors.
"""
import asyncio
import sys
import os
import unittest
import re
from pathlib import Path
from typing import Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

from models.principle_types import JusticePrinciple, CertaintyLevel
from experiment_agents.utility_agent import UtilityAgent

# Comprehensive test cases covering various response formats
COMPREHENSIVE_TEST_CASES = [
    {
        "name": "Markdown_Style_with_Bold",
        "response": """My ranking of justice principles:

1. **Maximizing the average income with a floor constraint** - Best balance
2. **Maximizing the floor income** - Safety first
3. **Maximizing the average income with a range constraint** - Less appealing  
4. **Maximizing the average income** - Too risky

Overall certainty: very sure""",
        "expected": [(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1), (JusticePrinciple.MAXIMIZING_FLOOR, 2), 
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3), (JusticePrinciple.MAXIMIZING_AVERAGE, 4)],
        "expected_certainty": CertaintyLevel.VERY_SURE
    },
    {
        "name": "Plain_Text_Format",
        "response": """I rank them as follows:

1. Maximizing the average income with a floor constraint
2. Maximizing the floor income
3. Maximizing the average income with a range constraint
4. Maximizing the average income

I am sure about this.""",
        "expected": [(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1), (JusticePrinciple.MAXIMIZING_FLOOR, 2), 
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3), (JusticePrinciple.MAXIMIZING_AVERAGE, 4)],
        "expected_certainty": CertaintyLevel.SURE
    },
    {
        "name": "Different_Order_Test",
        "response": """Here's my preference order:

1. Maximizing the floor income - Most important to protect the vulnerable
2. Maximizing the average income with a floor constraint - Good compromise  
3. Maximizing the average income - Simple but risky
4. Maximizing the average income with a range constraint - Least preferred

Certainty: sure""",
        "expected": [(JusticePrinciple.MAXIMIZING_FLOOR, 1), (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 2), 
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 3), (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 4)],
        "expected_certainty": CertaintyLevel.SURE
    },
    {
        "name": "Short_Names_Format",
        "response": """My ranking:

1. Average with floor constraint
2. Floor maximization  
3. Average maximization
4. Average with range constraint

I'm very sure of this.""",
        "expected": [(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1), (JusticePrinciple.MAXIMIZING_FLOOR, 2), 
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 3), (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 4)],
        "expected_certainty": CertaintyLevel.VERY_SURE
    },
    {
        "name": "Verbose_Format",
        "response": """After careful consideration, my complete ranking is:

1. Maximizing the average income with a floor constraint: This principle offers the best balance between efficiency and equity by ensuring a safety net while still incentivizing productivity.

2. Maximizing the floor income: While this prioritizes the worst-off, it may limit overall economic growth but provides crucial protection.

3. Maximizing the average income with a range constraint: This approach caps inequality but feels less direct than a floor constraint.

4. Maximizing the average income: This pure efficiency approach risks creating severe inequality and leaving people behind.

My overall certainty level: sure

This ranking reflects my belief that we need both growth and protection.""",
        "expected": [(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1), (JusticePrinciple.MAXIMIZING_FLOOR, 2), 
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3), (JusticePrinciple.MAXIMIZING_AVERAGE, 4)],
        "expected_certainty": CertaintyLevel.SURE
    }
]


async def run_comprehensive_test():
    """Run comprehensive tests on the fixed parsing logic."""
    print("Comprehensive Ranking Parsing Test")
    print("=" * 60)
    print("Testing various response formats that agents might use...")
    
    utility_agent = UtilityAgent()
    all_passed = True
    
    for i, test_case in enumerate(COMPREHENSIVE_TEST_CASES):
        print(f"\n🧪 Test {i+1}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Parse the response
            parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(test_case['response'])
            
            # Validate the parsing
            parsing_correct = True
            
            # Check if all expected rankings are present
            for expected_principle, expected_rank in test_case['expected']:
                found = False
                for parsed_principle in parsed_ranking.rankings:
                    if (parsed_principle.principle == expected_principle and 
                        parsed_principle.rank == expected_rank):
                        found = True
                        break
                
                if not found:
                    parsing_correct = False
                    print(f"❌ Missing: {expected_principle.value} at rank {expected_rank}")
            
            # Check certainty
            if parsed_ranking.certainty != test_case['expected_certainty']:
                parsing_correct = False
                print(f"❌ Certainty mismatch: expected {test_case['expected_certainty'].value}, got {parsed_ranking.certainty.value}")
            
            if parsing_correct:
                print("✅ PASSED - All rankings and certainty correct")
            else:
                print("❌ FAILED - Parsing errors detected")
                all_passed = False
                
                # Show details for debugging
                print("   Expected vs Actual:")
                for expected_principle, expected_rank in test_case['expected']:
                    print(f"     {expected_rank}. {expected_principle.value}")
                print("   ---")
                for parsed_principle in parsed_ranking.rankings:
                    print(f"     {parsed_principle.rank}. {parsed_principle.principle.value}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The ranking parsing fix is working correctly.")
        print("✅ The system can now handle various agent response formats.")
        print("✅ Principle identification is accurate across different phrasings.")
        print("✅ Certainty detection works with different expressions.")
    else:
        print("⚠️  Some tests failed. The fix needs additional refinement.")
    
    print("=" * 60)


class TestParsingVulnerabilities(unittest.TestCase):
    """Test class to identify and fix parsing vulnerabilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.utility_agent = UtilityAgent()
        
    async def test_problematic_inputs(self):
        """Test inputs that should cause parsing errors or misidentification."""
        
        # Test cases that should parse as maximizing_floor (principle A) but might not
        floor_inputs = [
            "My ballot choice is principle a with no additional constraints",
            "I choose principle a with no constraints", 
            "My choice is maximizing the floor income with no constraints",
            "Principle a - maximizing floor income, no constraints needed",
            "I vote for principle a without any constraint",
            "My ballot: principle a (maximizing floor) - no constraint amounts",
            "Choice: maximizing floor income, constraint: none",
            "I choose to maximize the floor income with zero constraints"
        ]
        
        # Test cases that should parse as maximizing_average (principle B) but might not
        average_inputs = [
            "My ballot choice is principle b with no constraints",
            "I choose principle b - maximizing average income",
            "My choice is maximizing the average income only", 
            "Principle b without constraints",
            "I vote for maximizing average income with no additional conditions"
        ]
        
        # Test cases that should parse as maximizing_average_floor_constraint (principle C)
        floor_constraint_inputs = [
            "My ballot choice is principle c with a floor constraint of $15000",
            "I choose maximizing average with floor constraint of $20,000",
            "Principle c: maximizing average income with floor constraint $18000"
        ]
        
        # Test cases that should parse as maximizing_average_range_constraint (principle D)  
        range_constraint_inputs = [
            "My ballot choice is principle d with range constraint of $25000",
            "I choose maximizing average with range constraint of $30,000",
            "Principle d: maximizing average income with range constraint $22000"
        ]
        
        await self._test_category("Floor Income (Principle A)", floor_inputs, JusticePrinciple.MAXIMIZING_FLOOR)
        await self._test_category("Average Income (Principle B)", average_inputs, JusticePrinciple.MAXIMIZING_AVERAGE)  
        await self._test_category("Average with Floor Constraint (Principle C)", floor_constraint_inputs, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        await self._test_category("Average with Range Constraint (Principle D)", range_constraint_inputs, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT)
        
    async def _test_category(self, category_name: str, inputs: list, expected_principle: JusticePrinciple):
        """Test a category of inputs."""
        errors = []
        
        for i, test_input in enumerate(inputs, 1):
            try:
                # Use the direct pattern matching method
                choice_data = self.utility_agent._extract_principle_choice_direct(test_input)
                
                if not choice_data:
                    errors.append(f"Test {i}: No principle detected in '{test_input}'")
                else:
                    detected_principle = JusticePrinciple(choice_data['principle'])
                    if detected_principle != expected_principle:
                        errors.append(f"Test {i}: Expected {expected_principle.value}, got {detected_principle.value} for '{test_input}'")
                        
            except Exception as e:
                errors.append(f"Test {i}: Exception - {str(e)} for '{test_input}'")
        
        # Assert no errors found in this category
        if errors:
            self.fail(f"Parsing vulnerabilities found in {category_name}:\n" + "\n".join(errors))
    
    def test_regex_patterns_directly(self):
        """Test the regex patterns directly to identify issues."""
        # Create a test utility agent to get patterns
        utility_agent = UtilityAgent()
        patterns = utility_agent._principle_patterns
        
        # Problematic test cases that have caused issues
        test_cases = [
            ("principle a with no additional constraints", "maximizing_floor"),
            ("My ballot choice is principle a with no constraints", "maximizing_floor"),  
            ("I choose maximizing the floor income with no constraints", "maximizing_floor"),
            ("principle c with a floor constraint of $15000", "maximizing_average_floor_constraint"),
            ("maximizing average with floor constraint of $20000", "maximizing_average_floor_constraint"),
        ]
        
        for test_case, expected_principle in test_cases:
            matches = []
            for principle_name, pattern in patterns.items():
                if pattern.search(test_case):
                    matches.append(principle_name)
            
            # Should have exactly one match, and it should be the expected one
            if len(matches) != 1:
                self.fail(f"Pattern matching issue for '{test_case}': found {len(matches)} matches: {matches}")
            
            if matches[0] != expected_principle:
                self.fail(f"Wrong pattern match for '{test_case}': expected '{expected_principle}', got '{matches[0]}'")
    
    async def test_constraint_amount_extraction_vulnerabilities(self):
        """Test constraint amount extraction for potential vulnerabilities."""
        constraint_test_cases = [
            ("principle c with floor constraint of $10", 10),
            ("principle c with floor constraint of $13,000", 13000),
            ("maximizing average with floor constraint of $25000", 25000),
            ("principle d with range constraint of $30,000", 30000),
            # Edge cases that might cause parsing issues
            ("principle c with floor constraint of 5000", 5000),  # No dollar sign
            ("principle c with floor constraint of $5,000.00", 5000),  # Decimal
        ]
        
        for test_input, expected_amount in constraint_test_cases:
            with self.subTest(input=test_input):
                try:
                    choice_data = self.utility_agent._extract_principle_choice_direct(test_input)
                    self.assertIsNotNone(choice_data, f"Should detect principle in: {test_input}")
                    
                    if 'constraint_amount' in choice_data and choice_data['constraint_amount'] is not None:
                        self.assertEqual(choice_data['constraint_amount'], expected_amount,
                                       f"Expected constraint {expected_amount}, got {choice_data['constraint_amount']} for: {test_input}")
                except Exception as e:
                    self.fail(f"Exception extracting constraint from '{test_input}': {str(e)}")


class TestRankingParsingComprehensive(unittest.TestCase):
    """Comprehensive tests for ranking parsing functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.utility_agent = UtilityAgent()
    
    async def test_comprehensive_ranking_formats(self):
        """Test comprehensive ranking parsing across various formats."""
        for i, test_case in enumerate(COMPREHENSIVE_TEST_CASES):
            with self.subTest(test_name=test_case['name']):
                try:
                    # Parse the response
                    parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(test_case['response'])
                    
                    # Validate the parsing
                    self.assertIsNotNone(parsed_ranking, f"Should parse ranking for {test_case['name']}")
                    
                    # Check if all expected rankings are present
                    for expected_principle, expected_rank in test_case['expected']:
                        found = False
                        for parsed_principle in parsed_ranking.rankings:
                            if (parsed_principle.principle == expected_principle and 
                                parsed_principle.rank == expected_rank):
                                found = True
                                break
                        
                        self.assertTrue(found, f"Missing: {expected_principle.value} at rank {expected_rank} in {test_case['name']}")
                    
                    # Check certainty
                    self.assertEqual(parsed_ranking.certainty, test_case['expected_certainty'],
                                   f"Certainty mismatch in {test_case['name']}: expected {test_case['expected_certainty'].value}, got {parsed_ranking.certainty.value}")
                    
                except Exception as e:
                    self.fail(f"Exception parsing {test_case['name']}: {str(e)}")


class AsyncTestRunner:
    """Helper class to run async tests with unittest."""
    
    def run_async_tests(self):
        """Run all async test methods."""
        vulnerability_test = TestParsingVulnerabilities()
        ranking_test = TestRankingParsingComprehensive()
        
        async def run_all_async():
            await vulnerability_test.test_problematic_inputs()
            await vulnerability_test.test_constraint_amount_extraction_vulnerabilities()
            await ranking_test.test_comprehensive_ranking_formats()
        
        # Run sync tests
        vulnerability_test.test_regex_patterns_directly()
        
        # Run async tests
        asyncio.run(run_all_async())


if __name__ == "__main__":
    # For direct execution, run both the original comprehensive test and new unittest structure
    print("Running comprehensive ranking parsing tests...")
    asyncio.run(run_comprehensive_test())
    
    print("\n" + "="*60)
    print("Running parsing vulnerability tests...")
    runner = AsyncTestRunner()
    try:
        runner.run_async_tests()
        print("✅ All parsing vulnerability tests passed!")
    except Exception as e:
        print(f"❌ Parsing vulnerability test failed: {e}")
        raise