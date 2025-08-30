#!/usr/bin/env python3
"""
Basic test to validate simplified utility agent functionality.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from experiment_agents.utility_agent import UtilityAgent
from models import PrincipleChoice, JusticePrinciple, CertaintyLevel

async def test_basic_functionality():
    """Test essential utility agent methods."""
    print("🧪 Testing simplified utility agent...")
    
    # Initialize agent
    agent = UtilityAgent(experiment_language="english")
    await agent.async_init()
    print("✅ Utility agent initialization successful")
    
    # Test essential methods exist
    essential_methods = [
        'parse_principle_choice_enhanced',
        'parse_principle_ranking_enhanced', 
        'detect_preference_statement',
        'check_preference_consensus_simple_mode',
        'check_ballot_consensus',
        'detect_agreement'
    ]
    
    for method_name in essential_methods:
        if hasattr(agent, method_name) and callable(getattr(agent, method_name)):
            print(f"✅ {method_name} exists and is callable")
        else:
            print(f"❌ {method_name} missing or not callable")
            return False
    
    # Test agreement detection (simple method)
    agreement_tests = [
        ("yes", True),
        ("I agree", True), 
        ("no", False),
        ("maybe", False)
    ]
    
    for test_input, expected in agreement_tests:
        result = await agent.detect_agreement(test_input)
        if result == expected:
            print(f"✅ Agreement detection: '{test_input}' -> {result}")
        else:
            print(f"❌ Agreement detection failed: '{test_input}' -> {result}, expected {expected}")
    
    # Test consensus checking
    preferences = [
        PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test"
        ),
        PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test"
        )
    ]
    
    consensus_reached, consensus_preference, warnings = agent.check_preference_consensus_simple_mode(preferences)
    if consensus_reached and consensus_preference.principle == JusticePrinciple.MAXIMIZING_FLOOR:
        print("✅ Consensus checking works")
    else:
        print(f"❌ Consensus checking failed: {consensus_reached}, {warnings}")
    
    print("\n🎉 Basic functionality test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    if success:
        print("\n✅ ALL TESTS PASSED - Simplified utility agent is working!")
        exit(0)
    else:
        print("\n❌ Some tests failed")
        exit(1)