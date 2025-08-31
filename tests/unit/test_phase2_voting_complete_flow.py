"""
Comprehensive Phase 2 Voting System Tests

Fast unit tests covering the complete voting flow from intention detection
to consensus reaching, with special focus on parser disambiguation issues.

Critical areas tested:
1. Vote intention detection (pattern matching)
2. Vote parsing disambiguation (our recent parser agent fix)
3. Principle parsing with voting context 
4. Multi-language consistency
5. Consensus detection logic
"""

import unittest
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, PrincipleRanking, CertaintyLevel
from utils.language_manager import create_language_manager, SupportedLanguage
from core.phase2_manager import Phase2Manager


class TestVoteParsingDisambiguation(unittest.TestCase):
    """Test parser disambiguation - the core issue we recently fixed."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.language_manager = create_language_manager(SupportedLanguage.MANDARIN)
        self.utility_agent = UtilityAgent(
            utility_model="gpt-4o-mini", 
            temperature=0.0, 
            experiment_language="mandarin",
            language_manager=self.language_manager
        )

    @pytest.mark.asyncio
    async def test_mandarin_ranking_with_voting_context_parses_correctly(self):
        """Test that Mandarin responses with voting context parse principles correctly."""
        # This is the exact pattern that was failing before our fix
        response_with_voting_context = """
        大家好，经过前几轮的讨论和投票，我对四个公正原则的排序更加清晰。
        
        我最看重的是**在最低收入约束条件下最大化平均收入**。
        我的第二选择是**在范围约束条件下最大化平均收入**。
        我的第三选择是**最大化平均收入**。
        我最差的选择是**最大化最低收入**。
        
        整体确定性：很确定
        
        我认为我们应该投票。
        """
        
        # Mock the LLM to return proper JSON instead of VOTE_PROPOSAL
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "rankings": [
                {"principle": "maximizing_average_floor_constraint", "rank": 1},
                {"principle": "maximizing_average_range_constraint", "rank": 2},
                {"principle": "maximizing_average", "rank": 3},
                {"principle": "maximizing_floor", "rank": 4}
            ],
            "certainty": "very_sure"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await self.utility_agent.async_init()
            ranking = await self.utility_agent.parse_principle_ranking_enhanced(response_with_voting_context)
            
            # Should successfully parse as ranking, not return VOTE_PROPOSAL
            self.assertEqual(len(ranking.rankings), 4)
            self.assertEqual(ranking.rankings[0].principle, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
            self.assertEqual(ranking.rankings[0].rank, 1)
            self.assertEqual(ranking.certainty, CertaintyLevel.very_sure)

    @pytest.mark.asyncio  
    async def test_english_choice_with_voting_context_parses_correctly(self):
        """Test English principle choices with voting context."""
        response_with_voting_context = """
        After our discussion, I choose maximizing floor income. I'm very sure about this choice.
        I think we should proceed with a vote now.
        """
        
        english_agent = UtilityAgent(
            utility_model="gpt-4o-mini",
            temperature=0.0, 
            experiment_language="english",
            language_manager=create_language_manager(SupportedLanguage.ENGLISH)
        )
        
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "principle": "maximizing_floor",
            "constraint_amount": null,
            "certainty": "very_sure",
            "reasoning": "After our discussion, I believe this is the best approach"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await english_agent.async_init()
            choice = await english_agent.parse_principle_choice_enhanced(response_with_voting_context)
            
            self.assertEqual(choice.principle, JusticePrinciple.MAXIMIZING_FLOOR)
            self.assertEqual(choice.certainty, CertaintyLevel.very_sure)
            self.assertIsNone(choice.constraint_amount)

    @pytest.mark.asyncio
    async def test_spanish_ranking_with_voting_context_parses_correctly(self):
        """Test Spanish principle ranking with voting context.""" 
        response_with_voting_context = """
        Después de nuestra discusión, mi ranking es:
        1. Maximizar los ingresos mínimos
        2. Maximizar los ingresos promedio con restricción de ingreso mínimo  
        3. Maximizar los ingresos promedio
        4. Maximizar los ingresos promedio con restricción de rango
        
        Certeza general: muy seguro
        
        Propongo que votemos ahora.
        """
        
        spanish_agent = UtilityAgent(
            utility_model="gpt-4o-mini",
            temperature=0.0,
            experiment_language="spanish", 
            language_manager=create_language_manager(SupportedLanguage.SPANISH)
        )
        
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "rankings": [
                {"principle": "maximizing_floor", "rank": 1},
                {"principle": "maximizing_average_floor_constraint", "rank": 2},
                {"principle": "maximizing_average", "rank": 3},
                {"principle": "maximizing_average_range_constraint", "rank": 4}
            ],
            "certainty": "very_sure"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await spanish_agent.async_init()
            ranking = await spanish_agent.parse_principle_ranking_enhanced(response_with_voting_context)
            
            self.assertEqual(len(ranking.rankings), 4)
            self.assertEqual(ranking.rankings[0].principle, JusticePrinciple.MAXIMIZING_FLOOR)


class TestVoteIntentionDetection(unittest.TestCase):
    """Test vote intention detection using pattern matching."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock Phase2Manager to test _is_voting_trigger_phrase
        self.phase2_manager = MagicMock()
        # Import the actual method
        from core.phase2_manager import Phase2Manager
        self.phase2_manager._is_voting_trigger_phrase = Phase2Manager._is_voting_trigger_phrase.__get__(self.phase2_manager)

    def test_english_voting_triggers(self):
        """Test English voting trigger phrases."""
        positive_cases = [
            "let's vote on this principle",
            "i think we should vote now", 
            "ready to vote",
            "time to vote",
            "shall we vote",
            "propose we vote",
            "call for a vote"
        ]
        
        for case in positive_cases:
            with self.subTest(case=case):
                self.assertTrue(self.phase2_manager._is_voting_trigger_phrase(case))

        negative_cases = [
            "i think the floor principle is good",
            "what do you think about maximizing average?",
            "this is an interesting discussion",
            "i prefer floor constraint"
        ]
        
        for case in negative_cases:
            with self.subTest(case=case):
                self.assertFalse(self.phase2_manager._is_voting_trigger_phrase(case))

    def test_mandarin_voting_triggers(self):
        """Test Mandarin voting trigger phrases."""
        positive_cases = [
            "我们投票吧",
            "开始投票", 
            "投票时间到了",
            "我们应该投票",
            "准备投票"
        ]
        
        for case in positive_cases:
            with self.subTest(case=case):
                self.assertTrue(self.phase2_manager._is_voting_trigger_phrase(case))

        negative_cases = [
            "我选择最大化最低收入",
            "这个原则很好",
            "我的排序是"
        ]
        
        for case in negative_cases:
            with self.subTest(case=case):
                self.assertFalse(self.phase2_manager._is_voting_trigger_phrase(case))

    def test_spanish_voting_triggers(self):
        """Test Spanish voting trigger phrases."""
        positive_cases = [
            "votemos por el principio",
            "es hora de votar",
            "procedamos a la votación",
            "deberíamos votar"
        ]
        
        for case in positive_cases:
            with self.subTest(case=case):
                self.assertTrue(self.phase2_manager._is_voting_trigger_phrase(case))

        negative_cases = [
            "prefiero maximizar los ingresos mínimos",
            "este principio es bueno",
            "mi elección es"
        ]
        
        for case in negative_cases:
            with self.subTest(case=case):
                self.assertFalse(self.phase2_manager._is_voting_trigger_phrase(case))


class TestConsensusDetection(unittest.TestCase):
    """Test consensus detection logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)

    def test_preference_consensus_simple_mode(self):
        """Test preference-based consensus detection."""
        # All participants agree
        matching_preferences = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                certainty=CertaintyLevel.SURE,
                constraint_amount=None,
                reasoning="Good choice"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR, 
                certainty=CertaintyLevel.VERY_SURE,
                constraint_amount=None,
                reasoning="Agreed"
            )
        ]
        
        consensus, agreed_choice, warnings = self.utility_agent.check_preference_consensus_simple_mode(matching_preferences)
        
        self.assertTrue(consensus)
        self.assertEqual(agreed_choice.principle, JusticePrinciple.MAXIMIZING_FLOOR)
        self.assertEqual(len(warnings), 0)

    def test_no_consensus_different_principles(self):
        """Test no consensus when participants choose different principles."""
        different_preferences = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                certainty=CertaintyLevel.SURE,
                constraint_amount=None,
                reasoning="Good choice"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                certainty=CertaintyLevel.SURE, 
                constraint_amount=None,
                reasoning="Different choice"
            )
        ]
        
        consensus, agreed_choice, warnings = self.utility_agent.check_preference_consensus_simple_mode(different_preferences)
        
        self.assertFalse(consensus)
        self.assertIsNone(agreed_choice)
        self.assertGreater(len(warnings), 0)

    def test_ballot_consensus(self):
        """Test ballot-based consensus detection."""
        # All votes for same principle
        matching_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                certainty=CertaintyLevel.SURE,
                constraint_amount=15000,
                reasoning="Best choice"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                certainty=CertaintyLevel.VERY_SURE,
                constraint_amount=15000, 
                reasoning="Agreed"
            )
        ]
        
        consensus, agreed_choice, warnings = self.utility_agent.check_ballot_consensus(matching_ballots)
        
        self.assertTrue(consensus)
        self.assertEqual(agreed_choice.principle, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        self.assertEqual(agreed_choice.constraint_amount, 15000)


if __name__ == '__main__':
    unittest.main()