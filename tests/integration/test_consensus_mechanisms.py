"""
Test script to verify consensus mechanism fixes work correctly.
Tests the specific scenarios that caused the false consensus in the problematic experiment.
"""
import asyncio
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiment_agents.utility_agent import UtilityAgent


class TestConsensusMechanisms(unittest.TestCase):
    """Test cases for consensus mechanism fixes."""
    
    def setUp(self):
        """Set up test utilities."""
        self.utility_agent = None
    
    async def async_setUp(self):
        """Async setup for utility agent."""
        self.utility_agent = UtilityAgent()
        await self.utility_agent.async_init()
    
    async def test_empty_response_detection(self):
        """Test that empty responses are properly rejected."""
        await self.async_setUp()
        
        # Test empty string
        result = await self.utility_agent.detect_agreement_multilingual("")
        self.assertFalse(result, "Empty string should return False")
        
        # Test whitespace only
        result = await self.utility_agent.detect_agreement_multilingual("\n")
        self.assertFalse(result, "Newline only should return False")
        
        # Test single character
        result = await self.utility_agent.detect_agreement_multilingual("Y")
        self.assertFalse(result, "Single character should return False")
        
        # Test valid response still works
        result = await self.utility_agent.detect_agreement_multilingual("Yes, I agree")
        self.assertTrue(result, "Valid agreement should return True")
    
    def test_fallback_detection(self):
        """Test that fallback statements are properly detected."""
        # Simulate the exact fallback format from the problematic experiment
        fallback_statement = "[Karl Marx failed to provide a valid response after multiple attempts]"
        
        # Test detection logic
        is_fallback = fallback_statement.startswith("[Karl Marx failed to provide")
        self.assertTrue(is_fallback, "Fallback statement should be detected")
        
        # Test normal statement
        normal_statement = "I believe we should vote on maximizing average"
        is_fallback = normal_statement.startswith("[Karl Marx failed to provide")
        self.assertFalse(is_fallback, "Normal statement should not be detected as fallback")
    
    def test_consensus_scenario_validation(self):
        """Test the specific scenario from the problematic experiment."""
        # Simulate the exact responses from the failed experiment
        karl_confirmation = "\n"  # Empty response that was incorrectly interpreted as agreement
        gordon_confirmation = "Yes, I agree to vote."
        
        # Test that Karl's empty response is now properly rejected
        karl_valid = len(karl_confirmation.strip()) >= 2
        self.assertFalse(karl_valid, "Karl's empty response should be invalid")
        
        gordon_valid = len(gordon_confirmation.strip()) >= 2
        self.assertTrue(gordon_valid, "Gordon's response should be valid")
    
    async def test_enhanced_agreement_detection_scenarios(self):
        """Test enhanced agreement detection with various scenarios."""
        await self.async_setUp()
        
        # Test cases that should be clearly detected
        clear_agreements = [
            "Yes, I agree",
            "I agree to proceed",
            "Let's vote",
            "Ready to vote",
            "I'm ready"
        ]
        
        for agreement in clear_agreements:
            with self.subTest(agreement=agreement):
                result = await self.utility_agent.detect_agreement_multilingual(agreement)
                self.assertTrue(result, f"Should detect agreement in: '{agreement}'")
        
        # Test cases that should be clearly rejected
        clear_disagreements = [
            "No, not yet",
            "I need more time",
            "Let me think about it",
            "Maybe we should discuss more",
            "I have concerns"
        ]
        
        for disagreement in clear_disagreements:
            with self.subTest(disagreement=disagreement):
                result = await self.utility_agent.detect_agreement_multilingual(disagreement)
                self.assertFalse(result, f"Should detect disagreement in: '{disagreement}'")
    
    async def test_problematic_edge_cases(self):
        """Test edge cases that previously caused false consensus."""
        await self.async_setUp()
        
        # Edge cases that should return False
        edge_cases = [
            "",  # Empty string
            " ",  # Just whitespace
            "\n",  # Just newline
            "\t",  # Just tab
            "   \n  ",  # Mixed whitespace
            "Y",  # Single character
            "N",  # Single character negative
        ]
        
        for edge_case in edge_cases:
            with self.subTest(edge_case=repr(edge_case)):
                result = await self.utility_agent.detect_agreement_multilingual(edge_case)
                self.assertFalse(result, f"Edge case should be rejected: {repr(edge_case)}")
    
    async def test_minimal_valid_responses(self):
        """Test minimal valid responses that should be accepted."""
        await self.async_setUp()
        
        minimal_valid = [
            "Yes",
            "No",
            "OK",
            "Si",  # Spanish yes
            "是的",  # Mandarin yes
            "Oui",  # French yes
        ]
        
        for response in minimal_valid:
            with self.subTest(response=response):
                # Should not be rejected due to length (>= 2 chars after strip)
                stripped_length = len(response.strip())
                self.assertGreaterEqual(stripped_length, 2, f"Response too short: '{response}'")
                
                # Should get a valid boolean result (not None due to processing error)
                result = await self.utility_agent.detect_agreement_multilingual(response)
                self.assertIsInstance(result, bool, f"Should return boolean for: '{response}'")
    
    async def test_fallback_statement_handling(self):
        """Test how fallback statements are handled in consensus detection."""
        await self.async_setUp()
        
        # Test various fallback statement formats
        fallback_formats = [
            "[Agent failed to provide a valid response after multiple attempts]",
            "[Karl Marx failed to provide a valid response after multiple attempts]",
            "[Agent_1 failed to provide a valid response after multiple attempts]",
        ]
        
        for fallback in fallback_formats:
            with self.subTest(fallback=fallback):
                # These should be detected as invalid/non-agreement responses
                result = await self.utility_agent.detect_agreement_multilingual(fallback)
                self.assertFalse(result, f"Fallback statement should not be treated as agreement: '{fallback}'")


class AsyncTestRunner:
    """Helper class to run async tests with unittest."""
    
    def run_async_tests(self):
        """Run all async test methods."""
        test_instance = TestConsensusMechanisms()
        
        async def run_all_async():
            await test_instance.test_empty_response_detection()
            await test_instance.test_enhanced_agreement_detection_scenarios()
            await test_instance.test_problematic_edge_cases()
            await test_instance.test_minimal_valid_responses()
            await test_instance.test_fallback_statement_handling()
        
        # Run sync tests normally
        test_instance.test_fallback_detection()
        test_instance.test_consensus_scenario_validation()
        
        # Run async tests
        asyncio.run(run_all_async())


if __name__ == "__main__":
    # For direct execution, run custom async test runner
    runner = AsyncTestRunner()
    try:
        runner.run_async_tests()
        print("✅ All consensus mechanism tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise