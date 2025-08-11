#!/usr/bin/env python3
"""
Comprehensive test script to validate the ranking parsing fix works across various formats.
"""
import asyncio
import sys
import os
from pathlib import Path

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


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())