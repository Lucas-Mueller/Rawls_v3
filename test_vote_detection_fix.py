#!/usr/bin/env python3
"""
Test script to verify that the improved vote detection patterns work correctly.
This tests the exact phrases that were used in the failed experiment to ensure they now trigger voting.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import get_language_manager, SupportedLanguage


async def test_vote_detection():
    """Test the enhanced vote detection patterns."""
    
    print("🔄 Testing improved vote detection patterns...")
    
    # Initialize utility agent
    utility_agent = UtilityAgent()
    await utility_agent.async_init()
    
    # Set language to English for testing
    language_manager = get_language_manager()
    language_manager.set_language(SupportedLanguage.ENGLISH)
    
    # Test cases from the failed experiment log
    test_statements = [
        # Original failed cases from the experiment log
        "I propose we proceed with a vote on **maximizing the average income with a floor constraint**.",
        "Since we're aligning on this principle, I propose we proceed with a vote.",
        "I propose we finalize our decision with a vote on this principle.",
        "I propose we proceed with a vote on **maximizing the average income with a floor constraint**.",
        "Once we're all clear, I propose we finalize with a vote on **maximizing the average income with a floor constraint**.",
        "We seem close to consensus on **maximizing the average income with a floor constraint**, with Alice suggesting a floor amount of 5. Let's ensure we're all aligned on this specific value. Is everyone comfortable with the floor amount being set at 5? If so, we can proceed with a final vote.",
        
        # Additional test cases to ensure broad detection
        "I think we're ready to vote now.",
        "Should we take a vote on this principle?",
        "Let's call for a vote.",
        "Time to vote on maximizing average with floor constraint.",
        "I propose we finalize this decision.",
        "Ready to move to voting.",
        "Can we conduct a vote?",
        "Final vote on principle c.",
        
        # Edge cases that should NOT be detected
        "I think voting is important in general.",
        "We should discuss more before any decisions.",
        "My preference is maximizing average with floor constraint.",
        "Let's continue the discussion."
    ]
    
    # Expected results (True = should detect vote, False = should not detect vote)
    expected_results = [
        True, True, True, True, True, True,  # Original failed cases - should all be detected now
        True, True, True, True, True, True, True, True,  # Additional cases - should be detected
        False, False, False, False  # Edge cases - should not be detected
    ]
    
    print(f"\n📋 Testing {len(test_statements)} statements...")
    
    results = []
    for i, statement in enumerate(test_statements):
        try:
            vote_proposal = await utility_agent.extract_vote_from_statement(statement)
            detected = vote_proposal is not None
            expected = expected_results[i]
            
            status = "✅ PASS" if detected == expected else "❌ FAIL"
            print(f"{status} Test {i+1}: {'DETECTED' if detected else 'NOT DETECTED'} (expected {'DETECTED' if expected else 'NOT DETECTED'})")
            
            if detected and vote_proposal:
                print(f"    💬 Proposal: {vote_proposal.proposal_text}")
            
            if detected != expected:
                print(f"    🔍 Statement: '{statement[:100]}{'...' if len(statement) > 100 else ''}'")
            
            results.append(detected == expected)
            
        except Exception as e:
            print(f"❌ FAIL Test {i+1}: ERROR - {e}")
            print(f"    🔍 Statement: '{statement[:100]}{'...' if len(statement) > 100 else ''}'")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n📊 Results Summary:")
    print(f"   Passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 All tests passed! Vote detection is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Vote detection needs further improvement.")
        return False


async def test_specific_failed_patterns():
    """Test the exact patterns that failed in the experiment log."""
    
    print("\n🎯 Testing specific patterns from the failed experiment...")
    
    utility_agent = UtilityAgent()
    await utility_agent.async_init()
    
    # Exact phrases from the experiment log that should have been detected
    failed_phrases = [
        "I propose we proceed with a vote on **maximizing the average income with a floor constraint**.",
        "I propose we finalize with a vote on **maximizing the average income with a floor constraint**.",
        "we can proceed with a final vote",
        "I propose we proceed with a final vote to solidify our choice."
    ]
    
    print(f"Testing {len(failed_phrases)} specific failed patterns...")
    
    all_detected = True
    for i, phrase in enumerate(failed_phrases):
        vote_proposal = await utility_agent.extract_vote_from_statement(phrase)
        detected = vote_proposal is not None
        
        status = "✅ DETECTED" if detected else "❌ NOT DETECTED"
        print(f"  {i+1}. {status}: '{phrase[:80]}{'...' if len(phrase) > 80 else ''}'")
        
        if detected and vote_proposal:
            print(f"      💬 Extracted: {vote_proposal.proposal_text}")
        
        if not detected:
            all_detected = False
    
    return all_detected


async def main():
    """Main test runner."""
    print("🧪 Vote Detection Fix Test")
    print("=" * 50)
    
    try:
        # Run general tests
        general_success = await test_vote_detection()
        
        # Run specific failed pattern tests  
        specific_success = await test_specific_failed_patterns()
        
        # Overall result
        if general_success and specific_success:
            print("\n🎉 SUCCESS: Vote detection fix is working correctly!")
            print("   The voting loop issue should now be resolved.")
            return True
        else:
            print("\n⚠️  PARTIAL SUCCESS: Some patterns still need work.")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)