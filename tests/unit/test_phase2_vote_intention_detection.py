"""
Comprehensive unit tests for Phase 2 vote intention detection.

Tests the sophisticated parsing logic in UtilityAgent.detect_vote_intention_enhanced()
that determines when participants want to trigger formal voting in complex mode.

Critical areas tested:
1. Positive vote intention patterns (English/Chinese)
2. Exclusion patterns that prevent false positives
3. LLM fallback behavior when regex fails
4. Edge cases and ambiguous statements
5. Multilingual support consistency
"""

import unittest
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.error_handling import ValidationError


class TestVoteIntentionDetection(unittest.TestCase):
    """Test vote intention detection patterns and fallback logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    def test_positive_english_patterns(self):
        """Test positive vote intention patterns in English."""
        positive_cases = [
            # Direct voting proposals
            "Let's vote on this",
            "I think we should vote now",
            "We should vote on the principles",
            "Let's call for a vote",
            "I propose we vote",
            "Time to vote",
            "Should we vote?",
            "Let's make a formal vote",
            
            # Natural decision language  
            "I think we're ready to decide",
            "Let's make our decision now",
            "We need to reach a decision",
            "Time to make our choice",
            "Let's finalize our choice",
            
            # Consensus-triggering phrases
            "Let's move to voting",
            "I suggest we vote",
            "We should take a vote",
            "Can we vote now?",
        ]
        
        for statement in positive_cases:
            with self.subTest(statement=statement):
                # Use async test helper
                result = asyncio.run(self._detect_vote_intention(statement))
                self.assertTrue(result, f"Should detect vote intention in: '{statement}'")
    
    def test_positive_chinese_patterns(self):
        """Test positive vote intention patterns in Chinese."""
        chinese_positive_cases = [
            "我们投票吧",
            "现在投票吧",
            "我认为我们应该投票",
            "是时候投票了",
            "让我们投票",
            "我们应该投票决定",
            "投票表决吧",
            "开始投票程序",
        ]
        
        for statement in chinese_positive_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_vote_intention(statement))
                self.assertTrue(result, f"Should detect vote intention in Chinese: '{statement}'")
    
    def test_exclusion_patterns(self):
        """Test exclusion patterns that prevent false positives."""
        exclusion_cases = [
            # Questions about voting (not proposals)
            "Should we vote later?",
            "Do you think we should vote?", 
            "When should we vote?",
            "How should we vote?",
            "What if we vote?",
            
            # Need more discussion
            "We need more discussion before voting",
            "I don't think we should vote yet",
            "Not ready to vote",
            "We need to discuss more",
            "More discussion needed",
            
            # Conditional statements
            "If we vote later",
            "After we vote",
            "Before we vote",
            "Unless we vote",
            
            # Past/future references
            "We voted last time",
            "We will vote eventually",
            "We might vote later",
        ]
        
        for statement in exclusion_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_vote_intention(statement))
                self.assertFalse(result, f"Should NOT detect vote intention in: '{statement}'")
    
    def test_ambiguous_edge_cases(self):
        """Test ambiguous statements that could go either way."""
        ambiguous_cases = [
            # Borderline cases - test for consistency
            ("Voting would be good", False),  # Conditional, not proposal
            ("We could vote now", False),     # Possibility, not decision
            ("Maybe we should vote", False),  # Uncertain, not decisive
            ("Let's think about voting", False), # Discussion, not action
            ("Voting is the next step", True),   # Clear intention
            ("Time for the vote", True),         # Clear timing signal
        ]
        
        for statement, expected in ambiguous_cases:
            with self.subTest(statement=statement, expected=expected):
                result = asyncio.run(self._detect_vote_intention(statement))
                self.assertEqual(result, expected, 
                               f"Expected {expected} for ambiguous case: '{statement}'")
    
    @patch('experiment_agents.utility_agent.Runner.run')
    async def test_llm_fallback_behavior(self, mock_runner):
        """Test LLM fallback when regex patterns don't match."""
        await self.utility_agent.async_init()
        
        # Mock LLM responses
        test_cases = [
            ("Some complex statement that doesn't match patterns", "VOTE_DETECTED", True),
            ("Another complex statement", "NO_VOTE_DETECTED", False),
            ("Edge case statement", "VOTE_DETECTED: clear intention", True),
        ]
        
        for statement, llm_response, expected in test_cases:
            with self.subTest(statement=statement):
                # Mock the LLM response
                mock_result = MagicMock()
                mock_result.final_output = llm_response
                mock_runner.return_value = mock_result
                
                result = await self.utility_agent.detect_vote_intention_enhanced(statement)
                
                if expected:
                    self.assertIsNotNone(result, f"LLM should detect vote intention in: '{statement}'")
                else:
                    self.assertIsNone(result, f"LLM should NOT detect vote intention in: '{statement}'")
    
    def test_multilingual_consistency(self):
        """Test that equivalent statements in different languages are handled consistently."""
        equivalent_sets = [
            # Vote proposals
            {
                "english": "Let's vote",
                "chinese": "我们投票吧", 
                "expected": True
            },
            # Discussion continuation
            {
                "english": "We need more discussion",
                "chinese": "我们需要更多讨论",
                "expected": False  
            }
        ]
        
        for equiv_set in equivalent_sets:
            expected = equiv_set["expected"]
            
            # Test English
            if "english" in equiv_set:
                result = asyncio.run(self._detect_vote_intention(equiv_set["english"]))
                self.assertEqual(result, expected, 
                               f"English consistency failed for: '{equiv_set['english']}'")
            
            # Test Chinese  
            if "chinese" in equiv_set:
                result = asyncio.run(self._detect_vote_intention(equiv_set["chinese"]))
                self.assertEqual(result, expected,
                               f"Chinese consistency failed for: '{equiv_set['chinese']}'")
    
    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        invalid_inputs = [
            "",           # Empty string
            "   ",        # Whitespace only
            "\n\t",       # Only whitespace characters
            None,         # None input (if handled)
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=repr(invalid_input)):
                if invalid_input is None:
                    # Skip None test if not supported
                    continue
                    
                result = asyncio.run(self._detect_vote_intention(invalid_input))
                self.assertFalse(result, f"Should return False for invalid input: {repr(invalid_input)}")
    
    def test_case_sensitivity(self):
        """Test that detection is case-insensitive."""
        case_variants = [
            "LET'S VOTE",
            "Let's Vote", 
            "let's vote",
            "lEt'S vOtE",
        ]
        
        for variant in case_variants:
            with self.subTest(variant=variant):
                result = asyncio.run(self._detect_vote_intention(variant))
                self.assertTrue(result, f"Case sensitivity failed for: '{variant}'")
    
    def test_pattern_order_priority(self):
        """Test that exclusion patterns take priority over positive patterns."""
        conflict_cases = [
            # Should be excluded despite containing positive keywords
            "Should we vote or discuss more?",  # Question form
            "We need discussion before we vote",  # Discussion priority
            "If we vote later, what happens?",    # Conditional
        ]
        
        for statement in conflict_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_vote_intention(statement))
                self.assertFalse(result, 
                               f"Exclusion should override positive patterns in: '{statement}'")
    
    @patch('experiment_agents.utility_agent.Runner.run')
    async def test_llm_error_handling(self, mock_runner):
        """Test handling of LLM errors during fallback."""
        await self.utility_agent.async_init()
        
        # Test LLM timeout/error scenario
        mock_runner.side_effect = asyncio.TimeoutError("LLM timeout")
        
        result = await self.utility_agent.detect_vote_intention_enhanced("Some complex statement")
        self.assertIsNone(result, "Should return None when LLM fails")
    
    async def _detect_vote_intention(self, statement: str) -> bool:
        """Helper method for async vote intention detection."""
        await self.utility_agent.async_init()
        result = await self.utility_agent.detect_vote_intention_enhanced(statement)
        return result is not None


if __name__ == '__main__':
    unittest.main()