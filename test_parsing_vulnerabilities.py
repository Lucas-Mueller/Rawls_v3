#!/usr/bin/env python3
"""
Test script to identify and fix parsing vulnerabilities in ballot parsing.

This script tests various problematic input patterns that could cause
the system to misinterpret votes, leading to false consensus failures.
"""
import asyncio
import re
from typing import Dict
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple

class ParsingTester:
    """Test class to identify parsing vulnerabilities."""
    
    def __init__(self):
        self.utility_agent = UtilityAgent()
        
    async def test_problematic_inputs(self):
        """Test inputs that should cause parsing errors."""
        
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
        
        print("🧪 TESTING PARSING VULNERABILITIES")
        print("=" * 60)
        
        await self._test_category("Floor Income (Principle A)", floor_inputs, JusticePrinciple.MAXIMIZING_FLOOR)
        await self._test_category("Average Income (Principle B)", average_inputs, JusticePrinciple.MAXIMIZING_AVERAGE)  
        await self._test_category("Average with Floor Constraint (Principle C)", floor_constraint_inputs, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        await self._test_category("Average with Range Constraint (Principle D)", range_constraint_inputs, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT)
        
    async def _test_category(self, category_name: str, inputs: list, expected_principle: JusticePrinciple):
        """Test a category of inputs."""
        print(f"\n📋 {category_name}")
        print("-" * 40)
        
        errors = []
        
        for i, test_input in enumerate(inputs, 1):
            try:
                # Use the direct pattern matching method
                choice_data = self.utility_agent._extract_principle_choice_direct(test_input)
                
                if not choice_data:
                    errors.append(f"  ❌ Test {i}: No principle detected")
                    print(f"  ❌ Test {i}: No principle detected")
                    print(f"     Input: '{test_input}'")
                else:
                    detected_principle = JusticePrinciple(choice_data['principle'])
                    if detected_principle == expected_principle:
                        print(f"  ✅ Test {i}: Correct - {detected_principle.value}")
                    else:
                        error_msg = f"Test {i}: Expected {expected_principle.value}, got {detected_principle.value}"
                        errors.append(f"  ❌ {error_msg}")
                        print(f"  ❌ {error_msg}")
                        print(f"     Input: '{test_input}'")
                        
                        # Show which pattern matched
                        await self._diagnose_pattern_match(test_input, detected_principle)
                        
            except Exception as e:
                error_msg = f"Test {i}: Exception - {str(e)}"
                errors.append(f"  ❌ {error_msg}")
                print(f"  ❌ {error_msg}")
                print(f"     Input: '{test_input}'")
        
        if errors:
            print(f"\n🚨 {len(errors)} ERRORS in {category_name}:")
            for error in errors:
                print(error)
        else:
            print(f"\n✅ All tests passed for {category_name}")
            
    async def _diagnose_pattern_match(self, test_input: str, detected_principle: JusticePrinciple):
        """Diagnose which pattern incorrectly matched."""
        patterns = self.utility_agent._principle_patterns
        
        print(f"     🔍 Pattern diagnosis:")
        for principle_name, pattern in patterns.items():
            if pattern.search(test_input):
                if principle_name == detected_principle.value:
                    print(f"       ➡️  MATCHED: {principle_name}")
                else:
                    print(f"       ⚠️  Also matches: {principle_name}")
                    
    def test_regex_patterns_directly(self):
        """Test the regex patterns directly to identify issues."""
        print("\n🔬 DIRECT REGEX PATTERN TESTING")
        print("=" * 60)
        
        # Create a test utility agent to get patterns
        utility_agent = UtilityAgent()
        patterns = utility_agent._principle_patterns
        
        # Problematic test cases
        test_cases = [
            "principle a with no additional constraints",
            "My ballot choice is principle a with no constraints",  
            "I choose maximizing the floor income with no constraints",
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: '{test_case}'")
            matches = []
            for principle_name, pattern in patterns.items():
                if pattern.search(test_case):
                    matches.append(principle_name)
                    
            print(f"Matches: {matches}")
            if len(matches) > 1:
                print("⚠️  MULTIPLE MATCHES - This is the problem!")
            elif len(matches) == 1 and matches[0] != 'maximizing_floor':
                print(f"❌ WRONG MATCH - Expected 'maximizing_floor', got '{matches[0]}'")

async def main():
    """Run the parsing vulnerability tests."""
    print("🔍 BALLOT PARSING VULNERABILITY ANALYSIS")
    print("=" * 80)
    print("This script tests for parsing errors that can cause legitimate consensus to fail.")
    print("")
    
    tester = ParsingTester()
    
    # First test regex patterns directly
    tester.test_regex_patterns_directly()
    
    # Then test the full parsing pipeline
    await tester.test_problematic_inputs()
    
    print("\n" + "=" * 80)
    print("🎯 ANALYSIS COMPLETE")
    print("Review the errors above to identify parsing vulnerabilities.")
    print("Focus on cases where the wrong principle is detected.")

if __name__ == "__main__":
    asyncio.run(main())