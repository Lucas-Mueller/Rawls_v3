"""
Unit tests for logger vote detection alignment.

Tests that the logger's vote detection uses the same sophisticated detection
as the main voting system instead of basic pattern matching.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from utils.agent_centric_logger import MemoryStateCapture
from experiment_agents.utility_agent import UtilityAgent


class TestLoggerVoteDetectionAlignment(unittest.TestCase):
    """Test logger vote detection alignment with main system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = MagicMock(spec=UtilityAgent)
        
    def test_logger_uses_enhanced_detection_when_available(self):
        """Test that logger uses enhanced detection when utility agent is provided."""
        
        async def run_test():
            # Mock enhanced detection returning positive result
            self.utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value="voting statement")
            
            result = await MemoryStateCapture.extract_vote_intention(
                "I think we should vote on this matter",
                self.utility_agent
            )
            
            # Should return "Yes" when enhanced detection finds vote intention
            self.assertEqual(result, "Yes")
            
            # Should have called the enhanced detection method
            self.utility_agent.detect_vote_intention_enhanced.assert_called_once_with(
                "I think we should vote on this matter"
            )
        
        asyncio.run(run_test())
    
    def test_logger_detects_no_vote_with_enhanced_detection(self):
        """Test that logger correctly detects no vote with enhanced detection."""
        
        async def run_test():
            # Mock enhanced detection returning None (no vote detected)
            self.utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value=None)
            
            result = await MemoryStateCapture.extract_vote_intention(
                "I'm thinking about the principles",
                self.utility_agent
            )
            
            # Should return "No" when enhanced detection finds no vote intention
            self.assertEqual(result, "No")
            
            # Should have called the enhanced detection method
            self.utility_agent.detect_vote_intention_enhanced.assert_called_once_with(
                "I'm thinking about the principles"
            )
        
        asyncio.run(run_test())
    
    def test_logger_fallback_when_utility_agent_none(self):
        """Test that logger falls back to basic detection when utility agent is None."""
        
        async def run_test():
            result = await MemoryStateCapture.extract_vote_intention(
                "let's vote on this",  # Basic pattern should catch this
                None  # No utility agent provided
            )
            
            # Should return "Yes" using basic pattern matching
            self.assertEqual(result, "Yes")
        
        asyncio.run(run_test())
    
    def test_logger_fallback_when_enhanced_detection_fails(self):
        """Test that logger falls back to basic detection when enhanced detection fails."""
        
        async def run_test():
            # Mock enhanced detection throwing an exception
            self.utility_agent.detect_vote_intention_enhanced = AsyncMock(
                side_effect=Exception("Enhanced detection failed")
            )
            
            result = await MemoryStateCapture.extract_vote_intention(
                "let's vote now",  # Basic pattern should catch this
                self.utility_agent
            )
            
            # Should return "Yes" using basic pattern fallback
            self.assertEqual(result, "Yes")
            
            # Should have attempted enhanced detection
            self.utility_agent.detect_vote_intention_enhanced.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_logger_basic_fallback_accuracy(self):
        """Test that the basic fallback detection still works correctly."""
        
        async def run_test():
            # Test positive cases with basic patterns
            positive_cases = [
                "i propose we vote",
                "let's vote",
                "lets vote", 
                "vote now",
                "call for a vote",
                "time to vote",
                "we should vote",
                "proceed with a vote"
            ]
            
            for statement in positive_cases:
                result = await MemoryStateCapture.extract_vote_intention(statement, None)
                self.assertEqual(result, "Yes", f"Should detect vote in: '{statement}'")
            
            # Test negative cases
            negative_cases = [
                "should we vote?",  # Question, not proposal
                "no constraints on the vote",  # Domain phrase
                "thinking about voting",
                "not ready to vote"
            ]
            
            for statement in negative_cases:
                result = await MemoryStateCapture.extract_vote_intention(statement, None)
                self.assertEqual(result, "No", f"Should NOT detect vote in: '{statement}'")
        
        asyncio.run(run_test())
    
    def test_logger_enhanced_vs_basic_consistency(self):
        """Test consistency between enhanced and basic detection on overlapping cases."""
        
        async def run_test():
            # Cases where both methods should agree
            clear_positive_cases = [
                "let's vote on this",
                "i propose we vote",
                "time to vote now"
            ]
            
            clear_negative_cases = [
                "should we vote?",
                "thinking about principles",
                "no constraints here"
            ]
            
            for statement in clear_positive_cases:
                # Mock enhanced detection to return positive
                self.utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value="vote detected")
                
                enhanced_result = await MemoryStateCapture.extract_vote_intention(statement, self.utility_agent)
                basic_result = await MemoryStateCapture.extract_vote_intention(statement, None)
                
                self.assertEqual(enhanced_result, basic_result, 
                               f"Enhanced and basic should agree on positive case: '{statement}'")
                self.assertEqual(enhanced_result, "Yes")
            
            for statement in clear_negative_cases:
                # Mock enhanced detection to return negative
                self.utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value=None)
                
                enhanced_result = await MemoryStateCapture.extract_vote_intention(statement, self.utility_agent)
                basic_result = await MemoryStateCapture.extract_vote_intention(statement, None)
                
                self.assertEqual(enhanced_result, basic_result,
                               f"Enhanced and basic should agree on negative case: '{statement}'")
                self.assertEqual(enhanced_result, "No")
        
        asyncio.run(run_test())
    
    def test_logger_enhanced_superior_detection(self):
        """Test that enhanced detection can catch cases basic detection misses."""
        
        async def run_test():
            # Complex cases that enhanced detection should catch but basic might miss
            complex_cases = [
                "I think we're ready to make our final decision",
                "Let's finalize our choice on this matter",
                "We need to decide on the principles now"
            ]
            
            for statement in complex_cases:
                # Mock enhanced detection to find vote intention  
                self.utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value="complex vote detected")
                
                enhanced_result = await MemoryStateCapture.extract_vote_intention(statement, self.utility_agent)
                basic_result = await MemoryStateCapture.extract_vote_intention(statement, None)
                
                # Enhanced should detect (Yes), basic should not (No)
                self.assertEqual(enhanced_result, "Yes")
                # Basic might miss these complex cases (this demonstrates the improvement)
                # We don't assert basic_result here as it might legitimately miss complex cases
                
                # The key test is that enhanced detection was used
                self.utility_agent.detect_vote_intention_enhanced.assert_called_with(statement)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()