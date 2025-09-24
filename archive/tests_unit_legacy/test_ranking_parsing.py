"""
Unit tests for ranking parsing functionality.
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set environment variables to avoid missing keys
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

from models.principle_types import JusticePrinciple, CertaintyLevel
from experiment_agents.utility_agent import UtilityAgent


# Test cases based on the actual agent memory from the problematic log
TEST_CASES = [
    {
        "name": "Agent1_Initial_Ranking_Issue",
        "response": """After considering all four principles, here is my ranking from best to worst:

1. **Maximizing the average income with a floor constraint:** This is my top choice. It's a practical balance between encouraging success (maximizing average) and ensuring no one is left in poverty (the floor). As a college student with no income, having a guaranteed minimum is very appealing.

2. **Maximizing the floor income:** My second choice. The safety net is crucial, but I worry that focusing only on the floor might stifle growth and opportunity.

3. **Maximizing the average income with a range constraint:** A less preferred option. It feels more focused on capping the rich than directly lifting the poor, which seems like an indirect way to solve the problem.

4. **Maximizing the average income:** My last choice. I see this as a recipe for extreme inequality, as a few wealthy people could skew the average while many struggle.

Overall certainty: sure

My reasoning is that a "rising tide" doesn't lift boats with holes in them, justifying the need for a floor. I connect my personal financial situation directly to the appeal of a safety net.""",
        "expected_ranking": [
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
            (JusticePrinciple.MAXIMIZING_FLOOR, 2), 
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
            (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
        ],
        "expected_certainty": CertaintyLevel.SURE
    },
    {
        "name": "Agent1_Alternative_Format",
        "response": """Based on my understanding, I would rank these principles as follows:

1. Maximizing the average income with a floor constraint - This balances growth with protection
2. Maximizing the floor income - Ensures nobody is left behind  
3. Maximizing the average income with a range constraint - Less direct approach
4. Maximizing the average income - Too risky for inequality

I am very sure about this ranking.""",
        "expected_ranking": [
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
            (JusticePrinciple.MAXIMIZING_FLOOR, 2),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3), 
            (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
        ],
        "expected_certainty": CertaintyLevel.VERY_SURE
    }
]


@pytest.mark.asyncio
async def test_ranking_parsing():
    """Test the current ranking parsing logic."""
    # Initialize utility agent
    utility_agent = UtilityAgent()
    
    for i, test_case in enumerate(TEST_CASES):
        # Parse the response
        parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(test_case['response'])
        
        # Assert all rankings are correct
        assert len(parsed_ranking.rankings) == len(test_case['expected_ranking']), \
            f"Test case {i+1} ({test_case['name']}): Expected {len(test_case['expected_ranking'])} rankings, got {len(parsed_ranking.rankings)}"
        
        # Check each expected ranking
        for expected_principle, expected_rank in test_case['expected_ranking']:
            found_match = False
            for parsed_principle in parsed_ranking.rankings:
                if (parsed_principle.principle == expected_principle and 
                    parsed_principle.rank == expected_rank):
                    found_match = True
                    break
            assert found_match, \
                f"Test case {i+1} ({test_case['name']}): Expected {expected_principle.value} at rank {expected_rank}, but not found in parsed results"
        
        # Check certainty
        assert parsed_ranking.certainty == test_case['expected_certainty'], \
            f"Test case {i+1} ({test_case['name']}): Expected certainty {test_case['expected_certainty'].value}, got {parsed_ranking.certainty.value}"


@pytest.mark.asyncio
async def test_enhanced_parsing():
    """Test enhanced parsing with better logic."""
    utility_agent = UtilityAgent()
    
    for i, test_case in enumerate(TEST_CASES):
        # Use direct pattern matching first
        ranking_data = await utility_agent._extract_ranking_direct(test_case['response'])
        
        # Assert that direct pattern matching works for our test cases
        assert ranking_data is not None, f"Test case {i+1} ({test_case['name']}): Direct pattern matching should succeed"
        assert len(ranking_data['rankings']) == len(test_case['expected_ranking']), \
            f"Test case {i+1} ({test_case['name']}): Expected {len(test_case['expected_ranking'])} rankings in direct extraction"
        assert ranking_data['certainty'] == test_case['expected_certainty'].value, \
            f"Test case {i+1} ({test_case['name']}): Expected certainty {test_case['expected_certainty'].value} in direct extraction"


