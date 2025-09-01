"""
Phase 2 Voting Integration Tests

Integration tests covering the complete voting flow from discussion
through vote triggering, confirmation, ballot collection, and consensus.

Tests the formal voting system with vote triggering, confirmation, and consensus.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from core.phase2_manager import Phase2Manager
from core.two_stage_voting_manager import TwoStageVotingManager
from experiment_agents import ParticipantAgent, UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from models.experiment_types import GroupDiscussionResult
from config.models import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from utils.language_manager import create_language_manager, SupportedLanguage
from tests.fixtures.simplified_fixtures import TestParticipant, TestStatement


class TestCompleteVotingFlow:
    """Test complete voting flows for the formal voting system."""
    
    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i, name in enumerate(["Alice", "Bob"]):
            agent = MagicMock()
            agent.name = name
            agent.agent = AsyncMock()
            agent.agent.name = name
            participants.append(agent)
        return participants

    @pytest.fixture 
    def language_manager(self):
        """Create language manager."""
        return create_language_manager(SupportedLanguage.ENGLISH)

    @pytest.fixture
    def utility_agent(self, language_manager):
        """Create utility agent."""
        return UtilityAgent(
            utility_model="gpt-4o-mini",
            temperature=0.0,
            experiment_language="english",
            language_manager=language_manager
        )

    @pytest.fixture
    def phase2_config(self):
        """Create Phase 2 configuration."""
        return ExperimentConfiguration(
            phase2_settings=Phase2Settings(
                max_discussion_rounds=5,
                enable_memory_guidance=True,
                memory_guidance_style="structured"
            ),
            agents=[
                AgentConfiguration(name="Alice", personality="Test personality A", model="gpt-4o-mini", language="english"),
                AgentConfiguration(name="Bob", personality="Test personality B", model="gpt-4o-mini", language="english")
            ]
        )

    @pytest.fixture
    def phase2_manager(self, mock_participants, utility_agent, language_manager, phase2_config):
        """Create Phase 2 manager.""" 
        return Phase2Manager(
            participants=mock_participants,
            utility_agent=utility_agent,
            experiment_config=phase2_config,
            language_manager=language_manager
        )


    @pytest.mark.asyncio
    async def test_voting_flow(self, phase2_manager, utility_agent):
        """Test voting flow: discussion → vote trigger → confirmation → ballot → consensus."""
        # System always uses complex mode
        phase2_manager._voting_in_progress = False
        
        # Mock voting trigger detection
        phase2_manager._is_voting_trigger_phrase = MagicMock(return_value=True)
        
        # Mock confirmation phase - all participants agree to vote
        async def mock_conduct_confirmation(*args):
            return True
        phase2_manager._conduct_confirmation_phase = AsyncMock(side_effect=mock_conduct_confirmation)
        
        # Mock ballot collection - all vote for same principle  
        floor_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            certainty=CertaintyLevel.SURE,
            constraint_amount=None,
            reasoning="Best choice"
        )
        
        async def mock_collect_ballots(*args):
            return [floor_choice, floor_choice], True  # All vote for floor, consensus reached
        phase2_manager._collect_secret_ballots = AsyncMock(side_effect=mock_collect_ballots)
        
        # Mock participant contexts and discussion state
        mock_contexts = [MagicMock() for _ in phase2_manager.participants]
        mock_discussion_state = MagicMock()
        mock_discussion_state.vote_triggered = False
        mock_discussion_state.active_vote_in_progress = False
        mock_discussion_state.last_vote_result = None
        mock_discussion_state._consensus_reached = False
        
        # Mock the voting trigger statement
        trigger_statement = "I think we should vote on maximizing floor income now."
        trigger_participant = phase2_manager.participants[0]
        
        # Execute complex voting
        result = await phase2_manager._handle_complex_voting_mode(
            trigger_participant, trigger_statement, mock_discussion_state, mock_contexts
        )
        
        # Verify voting completed successfully
        assert result == True
        assert mock_discussion_state.vote_triggered == True

    @pytest.mark.asyncio 
    async def test_vote_confirmation_failure_returns_to_discussion(self, phase2_manager):
        """Test that failed vote confirmation returns to discussion."""
        # Configure for complex mode
        phase2_manager.config.voting_detection_mode = "complex" 
        phase2_manager._voting_in_progress = False
        
        # Mock voting trigger detection
        phase2_manager._is_voting_trigger_phrase = MagicMock(return_value=True)
        
        # Mock confirmation phase failure - not all participants agree
        async def mock_conduct_confirmation_failure(*args):
            return False
        phase2_manager._conduct_confirmation_phase = AsyncMock(side_effect=mock_conduct_confirmation_failure)
        
        # Mock contexts and discussion state
        mock_contexts = [MagicMock() for _ in phase2_manager.participants]
        mock_discussion_state = MagicMock()
        mock_discussion_state.vote_triggered = False
        mock_discussion_state.active_vote_in_progress = False
        
        trigger_statement = "Let's vote on this principle now."
        trigger_participant = phase2_manager.participants[0]
        
        # Execute complex voting
        result = await phase2_manager._handle_complex_voting_mode(
            trigger_participant, trigger_statement, mock_discussion_state, mock_contexts
        )
        
        # Verify voting failed and returned to discussion
        assert result == False
        assert mock_discussion_state.vote_triggered == True  # Still marked as triggered

    @pytest.mark.asyncio
    async def test_multilingual_voting_flow(self, utility_agent):
        """Test voting flow works consistently across languages."""
        languages = ["english", "spanish", "mandarin"]
        vote_trigger_phrases = {
            "english": "Let's vote on maximizing floor income",
            "spanish": "Votemos por maximizar los ingresos mínimos", 
            "mandarin": "我们投票选择最大化最低收入"
        }
        
        for language in languages:
            # Create language-specific components
            lang_manager = create_language_manager(SupportedLanguage(language.title()))
            lang_utility_agent = UtilityAgent(
                utility_model="gpt-4o-mini",
                temperature=0.0,
                experiment_language=language,
                language_manager=lang_manager
            )
            
            # Mock participants for this language
            mock_participants = []
            for name in ["Alice", "Bob"]:
                participant = MagicMock()
                participant.name = name
                participant.agent = AsyncMock()
                mock_participants.append(participant)
            
            # Create phase2 manager for this language
            config = ExperimentConfiguration(
                phase2_settings=Phase2Settings(max_discussion_rounds=3),
                agents=[
                    AgentConfiguration(name="Alice", personality="Test personality A", model="gpt-4o-mini", language=language),
                    AgentConfiguration(name="Bob", personality="Test personality B", model="gpt-4o-mini", language=language)
                ]
            )
            
            lang_phase2_manager = Phase2Manager(
                participants=mock_participants,
                utility_agent=lang_utility_agent,
                experiment_config=config,
                language_manager=lang_manager
            )
            
            # Test vote trigger detection for this language
            trigger_phrase = vote_trigger_phrases[language]
            is_trigger = lang_phase2_manager._is_voting_trigger_phrase(trigger_phrase)
            
            assert is_trigger == True, f"Vote trigger not detected for {language}: {trigger_phrase}"

    @pytest.mark.asyncio
    async def test_vote_parsing_with_context_regression(self, utility_agent):
        """Regression test for vote parsing disambiguation issue."""
        # This tests our recent fix where responses with voting context
        # should still parse as principle choices, not vote proposals
        
        response_with_voting_context = """
        After our discussion, I choose maximizing floor income. I'm very sure about this.
        I think we should vote on this principle now.
        """
        
        # Mock LLM to return proper principle choice JSON
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "principle": "maximizing_floor",
            "constraint_amount": null,
            "certainty": "very_sure", 
            "reasoning": "Best approach for fairness"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await utility_agent.async_init()
            choice = await utility_agent.parse_principle_choice_enhanced(response_with_voting_context)
            
            # Should parse as principle choice, not fail due to voting context
            assert choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert choice.certainty == CertaintyLevel.VERY_SURE
            assert choice.constraint_amount is None


if __name__ == '__main__':
    pytest.main([__file__])