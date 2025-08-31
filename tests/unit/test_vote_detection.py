"""
Consolidated Vote Intention Detection Tests

This module contains comprehensive tests for vote intention detection functionality,
consolidating tests from multiple files into a unified, parametrized test suite.

Functionality tested:
1. Vote intention detection patterns (multilingual)
2. Preference detection in simple mode
3. Vote detection fixes and edge cases  
4. Logger integration with vote detection
5. LLM fallback behavior

Consolidated from:
- test_phase2_vote_intention_detection.py
- test_phase2_preference_detection_simple_mode.py  
- test_vote_detection_fix.py
- test_logger_vote_detection.py
"""

import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.error_handling import ValidationError


class TestVoteDetection:
    """Unified test class for all vote intention detection functionality."""
    
    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for testing."""
        return UtilityAgent(utility_model="gpt-4.1-mini", temperature=0.0)
    
    @pytest.fixture
    def vote_intention_patterns(self):
        """Multilingual vote intention patterns for testing."""
        return {
            "english": {
                "positive": [
                    "Let's vote on this",
                    "I think we should vote now", 
                    "We should vote on the principles",
                    "Let's call for a vote",
                    "I propose we vote",
                    "Should we put this to a vote?",
                    "I suggest we vote",
                    "Time to vote",
                    "Let's have a vote"
                ],
                "negative": [
                    "I vote for principle A",
                    "My vote is maximizing floor",
                    "I'm voting for option B", 
                    "Let's discuss this more",
                    "I prefer principle A",
                    "What do you think?",
                    "I agree with that approach"
                ]
            },
            "spanish": {
                "positive": [
                    "Votemos por esto",
                    "Creo que deberíamos votar ahora",
                    "Deberíamos votar sobre los principios", 
                    "Llamemos a votación",
                    "Propongo que votemos",
                    "¿Deberíamos ponerlo a votación?",
                    "Sugiero que votemos",
                    "Es hora de votar"
                ],
                "negative": [
                    "Voto por el principio A",
                    "Mi voto es maximizar el mínimo",
                    "Estoy votando por la opción B",
                    "Discutamos esto más",
                    "Prefiero el principio A"
                ]
            },
            "mandarin": {
                "positive": [
                    "我们投票吧",
                    "我觉得我们现在应该投票",
                    "我们应该对原则进行投票",
                    "让我们进行投票", 
                    "我提议我们投票",
                    "我们应该投票决定吗？",
                    "我建议我们投票",
                    "该投票了"
                ],
                "negative": [
                    "我投票选择原则A", 
                    "我的投票是最大化最低收入",
                    "我正在投票选择选项B",
                    "让我们进一步讨论",
                    "我更喜欢原则A"
                ]
            }
        }
    
    @pytest.fixture
    def preference_patterns(self):
        """Preference detection patterns for simple mode testing."""
        return {
            "english": [
                "My preference is maximizing floor income",
                "I prefer principle A - maximizing floor",
                "My choice is maximizing the floor income", 
                "I would prefer maximizing floor income approach",
                "My preference: maximizing floor income with no constraints"
            ],
            "spanish": [
                "Mi preferencia es maximizar el ingreso mínimo",
                "Prefiero el principio A - maximizar el mínimo",
                "Mi elección es maximizar el ingreso mínimo",
                "Preferiría el enfoque de maximizar ingresos mínimos"  
            ],
            "mandarin": [
                "我的偏好是最大化最低收入",
                "我更喜欢原则A - 最大化最低收入",
                "我的选择是最大化最低收入",
                "我更喜欢最大化最低收入的方法"
            ]
        }

    # VOTE INTENTION DETECTION TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_positive_vote_intention_patterns(self, utility_agent, vote_intention_patterns, language):
        """Test positive vote intention detection across all languages."""
        positive_patterns = vote_intention_patterns[language]["positive"]
        
        for statement in positive_patterns:
            result = utility_agent.detect_vote_intention_enhanced(statement)
            assert result.wants_to_vote is True, f"Failed to detect vote intention in: {statement}"
            assert result.confidence > 0.7, f"Low confidence for clear vote intention: {statement}"

    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])  
    def test_negative_vote_intention_patterns(self, utility_agent, vote_intention_patterns, language):
        """Test that non-vote-intention statements are properly excluded."""
        negative_patterns = vote_intention_patterns[language]["negative"]
        
        for statement in negative_patterns:
            result = utility_agent.detect_vote_intention_enhanced(statement)
            assert result.wants_to_vote is False, f"False positive vote detection for: {statement}"

    def test_vote_intention_exclusion_patterns(self, utility_agent):
        """Test specific exclusion patterns that prevent false positives."""
        exclusion_cases = [
            # Voting for a specific choice (not initiating vote)
            "I vote for principle A",
            "My vote is maximizing floor income", 
            "I'm voting for option B",
            "I already voted for maximizing average",
            
            # Past tense voting references
            "When we voted last time",
            "The vote we had yesterday",
            "After we voted on principles",
            
            # Hypothetical voting discussions
            "If we were to vote, I would choose A",
            "Before voting, we should discuss",
            "The voting process should be fair",
            
            # General discussion about voting systems
            "Voting is an important democratic process",
            "The voting mechanism works well"
        ]
        
        for statement in exclusion_cases:
            result = utility_agent.detect_vote_intention_enhanced(statement) 
            assert result.wants_to_vote is False, f"False positive exclusion failed for: {statement}"

    def test_ambiguous_vote_intention_edge_cases(self, utility_agent):
        """Test handling of ambiguous statements that could go either way."""
        ambiguous_cases = [
            {
                "statement": "Maybe we should vote?",
                "expected": True,  # Question form suggests vote initiation
                "min_confidence": 0.5
            },
            {
                "statement": "I'm not sure if we should vote",
                "expected": False,  # Uncertainty suggests no clear intention
                "max_confidence": 0.3
            },
            {
                "statement": "What about voting on this?", 
                "expected": True,  # Suggestion in question form
                "min_confidence": 0.6
            },
            {
                "statement": "The vote was close",
                "expected": False,  # Past reference, not intention
                "max_confidence": 0.2
            }
        ]
        
        for case in ambiguous_cases:
            result = utility_agent.detect_vote_intention_enhanced(case["statement"])
            assert result.wants_to_vote == case["expected"], f"Ambiguous case failed: {case['statement']}"
            
            if "min_confidence" in case:
                assert result.confidence >= case["min_confidence"]
            if "max_confidence" in case:
                assert result.confidence <= case["max_confidence"]

    @patch('agents.Runner.run')
    def test_llm_fallback_behavior(self, mock_runner, utility_agent):
        """Test LLM fallback when regex patterns are insufficient."""
        # Configure mock for LLM fallback
        mock_runner.return_value = AsyncMock(return_value="The participant wants to initiate a formal vote: YES")
        
        # Test statement that requires LLM interpretation
        complex_statement = "Given our extensive discussion, perhaps it's time to formalize our decision through a democratic process."
        
        result = utility_agent.detect_vote_intention_enhanced(complex_statement)
        
        # Verify LLM was called for fallback
        mock_runner.assert_called_once()
        assert result.wants_to_vote is True
        assert result.used_llm_fallback is True

    def test_empty_and_invalid_vote_inputs(self, utility_agent):
        """Test handling of empty and invalid inputs."""
        invalid_inputs = ["", "   ", None, "a", "???", "...", "   \n  "]
        
        for invalid_input in invalid_inputs:
            if invalid_input is None:
                with pytest.raises(ValidationError):
                    utility_agent.detect_vote_intention_enhanced(invalid_input)
            else:
                result = utility_agent.detect_vote_intention_enhanced(invalid_input)
                assert result.wants_to_vote is False
                assert result.confidence < 0.1

    def test_case_sensitivity_vote_detection(self, utility_agent):
        """Test that vote detection is case-insensitive."""
        case_variants = [
            "let's vote on this",
            "LET'S VOTE ON THIS", 
            "Let's Vote On This",
            "lEt'S vOtE oN tHiS"
        ]
        
        for statement in case_variants:
            result = utility_agent.detect_vote_intention_enhanced(statement)
            assert result.wants_to_vote is True, f"Case sensitivity issue with: {statement}"

    def test_vote_pattern_priority_ordering(self, utility_agent):
        """Test that vote intention patterns follow correct priority order.""" 
        priority_tests = [
            # Specific vote intention should win over general discussion
            ("Let's vote, though I prefer discussing first", True),
            
            # Clear exclusion should override weak positive patterns  
            ("I vote for A, not suggesting we should all vote", False),
            
            # Strong positive patterns should win in mixed statements
            ("I voted for A before, but now let's vote on B", True)
        ]
        
        for statement, expected_result in priority_tests:
            result = utility_agent.detect_vote_intention_enhanced(statement)
            assert result.wants_to_vote == expected_result, f"Priority test failed for: {statement}"

    # PREFERENCE DETECTION (SIMPLE MODE) TESTS
    @pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
    def test_preference_detection_multilingual(self, utility_agent, preference_patterns, language):
        """Test preference detection in simple mode across languages."""
        patterns = preference_patterns[language]
        
        for statement in patterns:
            result = utility_agent.detect_preference_simple_mode(statement)
            assert result.has_preference is True, f"Failed to detect preference: {statement}"
            assert result.principle is not None, f"Failed to extract principle from: {statement}"

    def test_preference_vs_vote_intention_distinction(self, utility_agent):
        """Test clear distinction between preference statements and vote intentions."""
        preference_statements = [
            "My preference is maximizing floor income",
            "I prefer principle A", 
            "My choice would be maximizing average",
            "I would choose principle B"
        ]
        
        vote_intention_statements = [
            "Let's vote on the principles",
            "We should call for a vote",
            "I think it's time to vote",
            "Should we put this to a vote?"
        ]
        
        # Preference statements should NOT trigger vote intention
        for statement in preference_statements:
            vote_result = utility_agent.detect_vote_intention_enhanced(statement)
            assert vote_result.wants_to_vote is False, f"Preference confused with vote intention: {statement}"
            
            pref_result = utility_agent.detect_preference_simple_mode(statement)
            assert pref_result.has_preference is True, f"Failed to detect preference: {statement}"
        
        # Vote intention statements should NOT be preferences
        for statement in vote_intention_statements:
            vote_result = utility_agent.detect_vote_intention_enhanced(statement)
            assert vote_result.wants_to_vote is True, f"Failed to detect vote intention: {statement}"
            
            pref_result = utility_agent.detect_preference_simple_mode(statement)
            assert pref_result.has_preference is False, f"Vote intention confused with preference: {statement}"

    def test_preference_principle_extraction_accuracy(self, utility_agent):
        """Test accurate principle extraction from preference statements."""
        extraction_cases = [
            ("My preference is maximizing floor income", JusticePrinciple.MAXIMIZING_FLOOR),
            ("I prefer maximizing average income", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("My choice is principle A", JusticePrinciple.MAXIMIZING_FLOOR),
            ("I would prefer option B", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("My preference: maximizing floor with 60% constraint", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        ]
        
        for statement, expected_principle in extraction_cases:
            result = utility_agent.detect_preference_simple_mode(statement)
            assert result.principle == expected_principle, f"Extraction failed for: {statement}"

    @patch('agents.Runner.run')
    def test_vote_detection_llm_error_handling(self, mock_runner, utility_agent):
        """Test error handling when LLM fallback fails."""
        # Configure mock to raise an exception
        mock_runner.side_effect = Exception("LLM API Error")
        
        # Test statement that would normally trigger LLM fallback
        complex_statement = "Perhaps we should consider a more formal approach to decision-making."
        
        # Should gracefully handle LLM errors and fall back to conservative detection
        result = utility_agent.detect_vote_intention_enhanced(complex_statement)
        assert result.wants_to_vote is False  # Conservative fallback
        assert result.error is not None
        assert result.used_llm_fallback is True

    def test_multilingual_vote_detection_consistency(self, utility_agent):
        """Test consistent vote detection behavior across languages."""
        equivalent_statements = [
            ("Let's vote on this", "Votemos por esto", "我们投票吧"),
            ("Should we vote?", "¿Deberíamos votar?", "我们应该投票吗？"),
            ("Time to vote", "Es hora de votar", "该投票了")
        ]
        
        for english, spanish, mandarin in equivalent_statements:
            english_result = utility_agent.detect_vote_intention_enhanced(english)
            spanish_result = utility_agent.detect_vote_intention_enhanced(spanish) 
            mandarin_result = utility_agent.detect_vote_intention_enhanced(mandarin)
            
            # All should have same vote intention detection
            assert english_result.wants_to_vote == spanish_result.wants_to_vote == mandarin_result.wants_to_vote
            
            # Confidence levels should be reasonably similar (within 0.3)
            confidences = [english_result.confidence, spanish_result.confidence, mandarin_result.confidence]
            assert max(confidences) - min(confidences) <= 0.3, f"Confidence inconsistency: {confidences}"

    def test_logger_integration_with_vote_detection(self, utility_agent):
        """Test integration between vote detection and logging systems."""
        # This would typically test that vote detection results are properly logged
        # For now, test that detection works with logging enabled
        
        test_statements = [
            "Let's vote on the principles",
            "My preference is maximizing floor income",
            "I vote for principle A"
        ]
        
        for statement in test_statements:
            # Test vote intention detection with logging context
            vote_result = utility_agent.detect_vote_intention_enhanced(
                statement, 
                participant_name="TestAgent", 
                log_context={"experiment_id": "test", "round": 1}
            )
            
            # Should still work normally with logging context
            assert hasattr(vote_result, 'wants_to_vote')
            assert hasattr(vote_result, 'confidence')
            
            # Test preference detection with logging context  
            if "preference" in statement:
                pref_result = utility_agent.detect_preference_simple_mode(
                    statement,
                    participant_name="TestAgent"
                )
                assert hasattr(pref_result, 'has_preference')

    def test_vote_detection_regression_fixes(self, utility_agent):
        """Test that previously fixed vote detection bugs remain resolved."""
        # Test cases for known bugs that were fixed
        regression_cases = [
            {
                "statement": "I vote for principle A",
                "should_detect_vote_intention": False,  # This is a vote cast, not vote initiation
                "should_detect_preference": True
            },
            {
                "statement": "Let's vote on this together",
                "should_detect_vote_intention": True,   # This is vote initiation
                "should_detect_preference": False
            },
            {
                "statement": "After we voted yesterday, I think principle A is best",
                "should_detect_vote_intention": False,  # Past tense reference
                "should_detect_preference": True
            }
        ]
        
        for case in regression_cases:
            vote_result = utility_agent.detect_vote_intention_enhanced(case["statement"])
            pref_result = utility_agent.detect_preference_simple_mode(case["statement"])
            
            assert vote_result.wants_to_vote == case["should_detect_vote_intention"], \
                f"Vote intention regression for: {case['statement']}"
            
            assert pref_result.has_preference == case["should_detect_preference"], \
                f"Preference detection regression for: {case['statement']}"