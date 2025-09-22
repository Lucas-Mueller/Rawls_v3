"""
Integration tests for two-stage voting workflow.

Tests the complete Phase 2 workflow with two-stage voting system,
ensuring proper integration of all components.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from core.phase2_manager import Phase2Manager
from core.two_stage_voting_manager import TwoStageVotingManager
from experiment_agents.participant_agent import ParticipantAgent
from experiment_agents.utility_agent import UtilityAgent
from models.experiment_types import ParticipantContext, GroupDiscussionState
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from config import ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.language_manager import create_language_manager


class TestTwoStageVotingIntegration:
    """Integration tests for two-stage voting system."""

    @pytest.fixture
    def phase2_settings(self):
        """Create Phase2Settings for testing."""
        return Phase2Settings(
            two_stage_voting_enabled=True,
            two_stage_max_retries=3,
            two_stage_timeout_seconds=30.0,
            amount_range_validation=True,
            amount_min_reasonable=1000,
            amount_max_reasonable=100000
        )

    @pytest.fixture
    def experiment_config(self, phase2_settings):
        """Create experiment configuration for testing."""
        config = Mock(spec=ExperimentConfiguration)
        config.phase2_settings = phase2_settings
        config.memory_guidance_style = "narrative"
        return config

    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i, name in enumerate(["Alice", "Bob"]):
            participant = Mock(spec=ParticipantAgent)
            participant.name = name
            participant.agent = Mock()
            participants.append(participant)
        return participants

    @pytest.fixture
    def mock_contexts(self):
        """Create mock participant contexts."""
        contexts = []
        for name in ["Alice", "Bob"]:
            context = Mock(spec=ParticipantContext)
            context.memory = f"{name}'s memory"
            contexts.append(context)
        return contexts

    @pytest.fixture
    def utility_agent(self):
        """Create mock utility agent."""
        return Mock(spec=UtilityAgent)

    @pytest.fixture
    def discussion_state(self):
        """Create mock discussion state."""
        state = Mock(spec=GroupDiscussionState)
        state.round_number = 1
        state.vote_triggered = False
        state.active_vote_in_progress = False
        state.last_vote_result = None
        return state

    @pytest.fixture
    def phase2_manager(self, mock_participants, utility_agent, experiment_config):
        """Create Phase2Manager for testing."""
        return Phase2Manager(
            participants=mock_participants,
            utility_agent=utility_agent,
            experiment_config=experiment_config
        )

    @pytest.fixture
    def logger(self):
        """Create mock logger."""
        return Mock(spec=AgentCentricLogger)

    @pytest.fixture
    def two_stage_manager(self, mock_participants, logger, phase2_settings):
        """Create TwoStageVotingManager for testing."""
        # Create a mock language manager
        mock_language_manager = Mock()
        mock_language_manager.get_two_stage_principle_selection_prompt = Mock(return_value="Select principle (1-4):")
        mock_language_manager.get_two_stage_amount_specification_prompt = Mock(return_value="Specify amount:")
        mock_language_manager.get_two_stage_error_message = Mock(return_value="Invalid input")
        mock_language_manager.get_two_stage_timeout_message = Mock(return_value="Timeout")
        
        return TwoStageVotingManager(
            participants=mock_participants,
            language_manager=mock_language_manager,
            logger=logger,
            settings=phase2_settings
        )

    @pytest.mark.asyncio
    async def test_voting_trigger_phrase_detection(self, phase2_manager):
        """Test that voting trigger phrases are correctly detected."""
        # English phrases
        assert phase2_manager._is_voting_trigger_phrase("I think we should vote now")
        assert phase2_manager._is_voting_trigger_phrase("Let's vote on this principle")
        assert phase2_manager._is_voting_trigger_phrase("Ready to vote!")
        
        # Spanish phrases
        assert phase2_manager._is_voting_trigger_phrase("Votemos por el principio")
        assert phase2_manager._is_voting_trigger_phrase("Es hora de votar")
        
        # Mandarin phrases  
        assert phase2_manager._is_voting_trigger_phrase("我们投票吧")
        assert phase2_manager._is_voting_trigger_phrase("开始投票")
        
        # Non-voting statements
        assert not phase2_manager._is_voting_trigger_phrase("I think the floor principle is good")
        assert not phase2_manager._is_voting_trigger_phrase("What do you think?")
        assert not phase2_manager._is_voting_trigger_phrase("This is interesting")

    @pytest.mark.asyncio
    async def test_principle_selection_validation(self, two_stage_manager):
        """Test principle selection validation logic."""
        # Valid selections
        assert two_stage_manager._validate_principle_selection("1") == (1, None)
        assert two_stage_manager._validate_principle_selection("2") == (2, None)
        assert two_stage_manager._validate_principle_selection("3") == (3, None)
        assert two_stage_manager._validate_principle_selection("4") == (4, None)
        
        # Invalid selections
        assert two_stage_manager._validate_principle_selection("5")[0] is None
        assert two_stage_manager._validate_principle_selection("0")[0] is None
        assert two_stage_manager._validate_principle_selection("one")[0] is None
        assert two_stage_manager._validate_principle_selection("1.")[0] is None
        assert two_stage_manager._validate_principle_selection("")[0] is None

    @pytest.mark.asyncio
    async def test_amount_specification_validation(self, two_stage_manager):
        """Test amount specification validation logic."""
        # Valid amounts
        assert two_stage_manager._validate_amount_specification("15000") == (15000, None)
        assert two_stage_manager._validate_amount_specification("$25000") == (25000, None)
        assert two_stage_manager._validate_amount_specification("50,000") == (50000, None)
        
        # Invalid amounts
        assert two_stage_manager._validate_amount_specification("0")[0] is None
        assert two_stage_manager._validate_amount_specification("-5000")[0] is None
        assert two_stage_manager._validate_amount_specification("25.5")[0] is None
        assert two_stage_manager._validate_amount_specification("twenty thousand")[0] is None
        assert two_stage_manager._validate_amount_specification("")[0] is None

    @pytest.mark.asyncio
    async def test_convert_to_principle_choice(self, two_stage_manager):
        """Test conversion from ParticipantVote to PrincipleChoice."""
        from core.two_stage_voting_manager import ParticipantVote
        
        # Test principle 1 (no constraint)
        vote1 = ParticipantVote(
            participant_name="Alice",
            principle_num=1,
            constraint_amount=None
        )
        choice1 = two_stage_manager._convert_to_principle_choice(vote1)
        assert choice1.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert choice1.constraint_amount is None
        assert choice1.certainty == CertaintyLevel.SURE
        
        # Test principle 3 (with constraint)
        vote3 = ParticipantVote(
            participant_name="Bob",
            principle_num=3,
            constraint_amount=15000
        )
        choice3 = two_stage_manager._convert_to_principle_choice(vote3)
        assert choice3.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        assert choice3.constraint_amount == 15000
        assert choice3.certainty == CertaintyLevel.SURE

    @pytest.mark.asyncio
    async def test_consensus_checking(self, two_stage_manager):
        """Test consensus checking logic in vote results."""
        from core.two_stage_voting_manager import ParticipantVote
        
        # Test consensus reached - same principle and constraint
        participant_votes = [
            ParticipantVote("Alice", 3, 15000),
            ParticipantVote("Bob", 3, 15000)
        ]
        
        principle_choices = [
            two_stage_manager._convert_to_principle_choice(vote) 
            for vote in participant_votes
        ]
        
        vote_result = two_stage_manager._create_vote_result(participant_votes, principle_choices)
        assert vote_result.consensus_reached
        assert vote_result.agreed_principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        assert vote_result.agreed_principle.constraint_amount == 15000
        
        # Test no consensus - different principles
        participant_votes_no_consensus = [
            ParticipantVote("Alice", 1, None),
            ParticipantVote("Bob", 2, None)
        ]
        
        principle_choices_no_consensus = [
            two_stage_manager._convert_to_principle_choice(vote) 
            for vote in participant_votes_no_consensus
        ]
        
        vote_result_no_consensus = two_stage_manager._create_vote_result(
            participant_votes_no_consensus, principle_choices_no_consensus
        )
        assert not vote_result_no_consensus.consensus_reached
        assert vote_result_no_consensus.agreed_principle is None

    @pytest.mark.asyncio
    async def test_memory_content_builders(self):
        """Test memory content builder functions."""
        from utils.memory_content import (
            build_two_stage_voting_principle_selection_delta,
            build_two_stage_voting_amount_specification_delta,
            build_two_stage_voting_complete_delta
        )
        
        # Test principle selection memory
        principle_memory = build_two_stage_voting_principle_selection_delta(
            participant_name="Alice",
            principle_num=2,
            principle_display_name="Maximizing Average Income",
            attempts_used=1,
            success=True,
            raw_response="2"
        )
        assert "Stage 1: Principle Selection" in principle_memory
        assert "Selected: 2" in principle_memory
        assert "Maximizing Average Income" in principle_memory
        
        # Test amount specification memory
        amount_memory = build_two_stage_voting_amount_specification_delta(
            participant_name="Bob",
            principle_display_name="Maximizing Average with Floor Constraint",
            constraint_amount=25000,
            attempts_used=2,
            success=True,
            raw_response="$25000"
        )
        assert "Stage 2: Amount Specification" in amount_memory
        assert "Specified: $25,000" in amount_memory
        assert "Attempts: 2" in amount_memory
        
        # Test complete voting memory
        complete_memory = build_two_stage_voting_complete_delta(
            participant_name="Charlie",
            principle_num=4,
            principle_display_name="Maximizing Average with Range Constraint",
            constraint_amount=30000,
            consensus_reached=True,
            agreed_principle="maximizing_average_range_constraint",
            total_stages=2,
            total_attempts=3
        )
        assert "Two-Stage Voting Complete" in complete_memory
        assert "Your vote: 4" in complete_memory
        assert "$30,000 constraint" in complete_memory
        assert "Group consensus: YES" in complete_memory

    @pytest.mark.asyncio
    async def test_logger_integration(self, logger):
        """Test AgentCentricLogger integration with two-stage voting."""
        # Test success logging
        logger.log_two_stage_voting_success("Alice", "principle_selection", "1", 1, 1)
        assert logger.log_two_stage_voting_success.called
        
        # Test retry logging
        logger.log_two_stage_voting_retry("Bob", "amount_specification", "invalid", "invalid_format", 2)
        assert logger.log_two_stage_voting_retry.called
        
        # Test failure logging
        logger.log_two_stage_voting_failure("Charlie", "principle_selection", 3)
        assert logger.log_two_stage_voting_failure.called

    @pytest.mark.asyncio
    async def test_phase2_manager_trigger_detection_integration(
        self, phase2_manager, mock_participants, discussion_state, mock_contexts
    ):
        """Test integration between Phase2Manager and trigger detection."""
        # Mock the confirmation phase to succeed
        phase2_manager._conduct_confirmation_phase = AsyncMock(return_value=True)
        
        # Mock the TwoStageVotingManager to return a successful result
        mock_vote_result = Mock()
        mock_vote_result.consensus_reached = True
        mock_vote_result.agreed_principle = Mock()
        mock_vote_result.agreed_principle.principle = Mock()
        mock_vote_result.agreed_principle.principle.value = "maximizing_floor"
        mock_vote_result.agreed_principle.constraint_amount = None
        mock_vote_result.vote_counts = {"maximizing_floor_none": 2}
        
        with patch('core.phase2_manager.TwoStageVotingManager') as MockTwoStageVotingManager:
            mock_manager = MockTwoStageVotingManager.return_value
            mock_manager.conduct_full_voting_process = AsyncMock(return_value=mock_vote_result)
            
            # Test voting trigger detection and processing
            result = await phase2_manager._handle_complex_voting_mode(
                participant=mock_participants[0],
                statement="Let's vote on the principles now",
                discussion_state=discussion_state,
                contexts=mock_contexts
            )
            
            assert result is True  # Consensus reached
            assert discussion_state.vote_triggered is True
            assert discussion_state.last_vote_result == mock_vote_result
            
            # Verify TwoStageVotingManager was called
            MockTwoStageVotingManager.assert_called_once()
            mock_manager.conduct_full_voting_process.assert_called_once_with(
                mock_contexts, discussion_state
            )

    @pytest.mark.asyncio 
    async def test_non_voting_statement_ignored(
        self, phase2_manager, mock_participants, discussion_state, mock_contexts
    ):
        """Test that non-voting statements are properly ignored."""
        result = await phase2_manager._handle_complex_voting_mode(
            participant=mock_participants[0],
            statement="I think the floor principle is really good for society",
            discussion_state=discussion_state,
            contexts=mock_contexts
        )
        
        assert result is False  # No voting initiated
        assert discussion_state.vote_triggered is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
