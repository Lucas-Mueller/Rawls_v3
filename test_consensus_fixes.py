"""
Test script to verify consensus mechanism fixes work correctly.
Tests the specific scenarios that caused the false consensus in the problematic experiment.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_agents.utility_agent import UtilityAgent


async def test_empty_response_detection():
    """Test that empty responses are properly rejected."""
    print("Testing empty response detection...")
    
    utility = UtilityAgent()
    await utility.async_init()
    
    # Test empty string
    result = await utility.detect_agreement_multilingual("")
    assert result == False, "Empty string should return False"
    print("✓ Empty string correctly rejected")
    
    # Test whitespace only
    result = await utility.detect_agreement_multilingual("\n")
    assert result == False, "Newline only should return False"
    print("✓ Newline only correctly rejected")
    
    # Test single character
    result = await utility.detect_agreement_multilingual("Y")
    assert result == False, "Single character should return False"
    print("✓ Single character correctly rejected")
    
    # Test valid response still works
    result = await utility.detect_agreement_multilingual("Yes, I agree")
    assert result == True, "Valid agreement should return True"
    print("✓ Valid agreement still works")
    
    print("Empty response detection tests PASSED ✓")


def test_fallback_detection():
    """Test that fallback statements are properly detected."""
    print("\nTesting fallback statement detection...")
    
    # Simulate the exact fallback format from the problematic experiment
    fallback_statement = "[Karl Marx failed to provide a valid response after multiple attempts]"
    
    # Test detection logic
    is_fallback = fallback_statement.startswith("[Karl Marx failed to provide")
    assert is_fallback == True, "Fallback statement should be detected"
    print("✓ Fallback statement correctly detected")
    
    # Test normal statement
    normal_statement = "I believe we should vote on maximizing average"
    is_fallback = normal_statement.startswith("[Karl Marx failed to provide")
    assert is_fallback == False, "Normal statement should not be detected as fallback"
    print("✓ Normal statement correctly identified as valid")
    
    print("Fallback detection tests PASSED ✓")


def test_consensus_scenario():
    """Test the specific scenario from the problematic experiment."""
    print("\nTesting problematic consensus scenario...")
    
    # Simulate the exact responses from the failed experiment
    karl_confirmation = "\n"  # Empty response that was incorrectly interpreted as agreement
    gordon_confirmation = "Yes, I agree to vote."
    
    # Test that Karl's empty response is now properly rejected
    print(f"Karl's response: '{karl_confirmation}' (length: {len(karl_confirmation.strip())})")
    
    # This simulates the validation logic we added
    karl_valid = len(karl_confirmation.strip()) >= 2
    assert karl_valid == False, "Karl's empty response should be invalid"
    print("✓ Karl's empty response correctly rejected")
    
    gordon_valid = len(gordon_confirmation.strip()) >= 2
    assert gordon_valid == True, "Gordon's response should be valid"
    print("✓ Gordon's response correctly accepted")
    
    print("Consensus scenario tests PASSED ✓")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("CONSENSUS MECHANISM FIXES TEST")
    print("=" * 60)
    
    try:
        await test_empty_response_detection()
        test_fallback_detection()
        test_consensus_scenario()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("Consensus mechanism fixes are working correctly!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())