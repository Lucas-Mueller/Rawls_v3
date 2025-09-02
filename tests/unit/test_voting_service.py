"""
Unit tests for VotingService.

Tests voting logic including vote initiation, confirmation phases, ballot coordination,
and error handling with comprehensive mocking of dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings
from models import (
    ParticipantContext, GroupDiscussionState, VoteResult,
    PrincipleChoice, JusticePrinciple
)
from experiment_agents import ParticipantAgent


class TestVotingService:
    """Test suite for VotingService functionality."""
    
    def setup_method(self):
        """Set up test fixtures with mock dependencies."""
        # Create mock language manager
        self.language_manager = Mock()
        self.language_manager.get.return_value = "Test message"
        
        # Create mock utility agent
        self.utility_agent = Mock()
        
        # Create mock logger
        self.logger = Mock()
        
        # Create settings
        self.settings = Phase2Settings.get_default()
        
        # Create voting service
        self.voting_service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )
        
        # Create mock participant
        self.participant = Mock()
        self.participant.name = "TestAgent"
        self.participant.agent = Mock()
        
        # Create mock context
        self.context = Mock()
        self.context.name = "TestAgent"
        self.context.interaction_type = "discussion"
        
        # Create mock discussion state
        self.discussion_state = GroupDiscussionState()
        self.discussion_state.public_history = "Previous discussion"
    
    def test_initialization(self):
        """Test VotingService initialization with all parameters."""
        service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )
        
        assert service.language_manager == self.language_manager
        assert service.utility_agent == self.utility_agent
        assert service.settings == self.settings
        assert service.logger == self.logger
    
    def test_initialization_with_defaults(self):
        """Test VotingService initialization with default settings."""
        service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent
        )
        
        assert service.language_manager == self.language_manager
        assert service.utility_agent == self.utility_agent
        assert isinstance(service.settings, Phase2Settings)
        assert service.logger is None
    
    def test_log_info_with_logger(self):
        """Test info logging when logger is available."""
        self.voting_service._log_info("Test message")
        self.logger.log_info.assert_called_once_with("Test message")
    
    def test_log_info_without_logger(self):
        """Test info logging when logger is not available."""
        service = VotingService(self.language_manager, self.utility_agent)
        # Should not raise an exception
        service._log_info("Test message")
    
    def test_log_warning_with_logger(self):
        """Test warning logging when logger is available."""
        self.voting_service._log_warning("Test warning")
        self.logger.log_warning.assert_called_once_with("Test warning")
    
    def test_log_warning_without_logger(self):
        """Test warning logging when logger is not available."""
        service = VotingService(self.language_manager, self.utility_agent)
        # Should not raise an exception
        service._log_warning("Test warning")
    
    def test_get_localized_message_success(self):
        """Test successful localized message retrieval."""
        self.language_manager.get.return_value = "Localized message"
        result = self.voting_service._get_localized_message("test.key", param="value")
        
        assert result == "Localized message"
        self.language_manager.get.assert_called_once_with("test.key", param="value")
    
    def test_get_localized_message_error_fallback(self):
        """Test fallback behavior when localization fails."""
        self.language_manager.get.side_effect = Exception("Translation error")
        result = self.voting_service._get_localized_message("test.key")
        
        assert result == "[MISSING: test.key]"
        self.logger.log_warning.assert_called_once()
        assert "Missing translation key: test.key" in self.logger.log_warning.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_success_yes(self):
        """Test successful vote initiation prompt with Yes response."""
        # Mock successful response
        mock_result = Mock()
        mock_result.final_output = "1"  # Yes response
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (True, None)
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context
            )
            
            assert result is True
            self.utility_agent.detect_numerical_agreement.assert_called_once_with("1")
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_success_no(self):
        """Test successful vote initiation prompt with No response."""
        # Mock successful response
        mock_result = Mock()
        mock_result.final_output = "0"  # No response
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (False, None)
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context
            )
            
            assert result is False
            self.utility_agent.detect_numerical_agreement.assert_called_once_with("0")
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_with_statement(self):
        """Test vote initiation prompt with recent statement context."""
        mock_result = Mock()
        mock_result.final_output = "1"
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (True, None)
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context,
                agent_recent_statement="I think we should vote now"
            )
            
            assert result is True
            # Should use the with_statement prompt
            self.language_manager.get.assert_called_with(
                "prompts.vote_initiation_with_statement_prompt",
                agent_recent_statement="I think we should vote now"
            )
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_parse_error_retry(self):
        """Test retry logic when parse error occurs."""
        mock_result = Mock()
        mock_result.final_output = "invalid response"
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            # First attempt fails, second succeeds
            self.utility_agent.detect_numerical_agreement.side_effect = [
                (False, "Invalid format"),  # First attempt fails
                (True, None)               # Second attempt succeeds
            ]
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context,
                max_retries=2
            )
            
            assert result is True
            assert self.utility_agent.detect_numerical_agreement.call_count == 2
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_all_retries_fail(self):
        """Test fallback to False when all retries fail."""
        mock_result = Mock()
        mock_result.final_output = "invalid response"
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (False, "Invalid format")
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context,
                max_retries=2
            )
            
            assert result is False
            assert self.utility_agent.detect_numerical_agreement.call_count == 2
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_timeout(self):
        """Test timeout handling in vote initiation."""
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context,
                max_retries=1
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_prompt_for_vote_initiation_exception(self):
        """Test exception handling in vote initiation."""
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', side_effect=Exception("Network error")):
            
            result = await self.voting_service.prompt_for_vote_initiation(
                participant=self.participant,
                context=self.context,
                max_retries=1
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_confirmation_phase_all_agree(self):
        """Test confirmation phase when all participants agree."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        
        # Mock successful responses
        mock_result = Mock()
        mock_result.final_output = "1"  # Agree
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (True, None)
            
            result = await self.voting_service.conduct_confirmation_phase(
                participants=participants,
                initiator_name="Alice",
                initiation_statement="Let's vote on this",
                contexts=contexts,
                discussion_state=self.discussion_state
            )
            
            assert result is True
            # Alice should be auto-confirmed, Bob should be prompted
            assert self.utility_agent.detect_numerical_agreement.call_count == 1
    
    @pytest.mark.asyncio
    async def test_conduct_confirmation_phase_some_decline(self):
        """Test confirmation phase when some participants decline."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        
        # Mock Bob declining
        mock_result = Mock()
        mock_result.final_output = "0"  # Decline
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', return_value=mock_result):
            
            self.utility_agent.detect_numerical_agreement.return_value = (False, None)
            
            result = await self.voting_service.conduct_confirmation_phase(
                participants=participants,
                initiator_name="Alice",
                initiation_statement="Let's vote on this",
                contexts=contexts,
                discussion_state=self.discussion_state
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_confirmation_phase_timeout(self):
        """Test confirmation phase with timeout."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        
        with patch('core.services.voting_service.Runner') as mock_runner, \
             patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            
            result = await self.voting_service.conduct_confirmation_phase(
                participants=participants,
                initiator_name="Alice",
                initiation_statement="Let's vote on this",
                contexts=contexts,
                discussion_state=self.discussion_state
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_secret_ballot_consensus_reached(self):
        """Test secret ballot phase with consensus reached."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        # Mock successful vote result
        mock_vote_result = Mock()
        mock_vote_result.consensus_reached = True
        mock_vote_result.agreed_principle = Mock()
        mock_vote_result.agreed_principle.principle = JusticePrinciple.MAXIMIZING_FLOOR
        mock_vote_result.agreed_principle.constraint_amount = None
        
        with patch('core.services.voting_service.TwoStageVotingManager') as MockVotingManager:
            mock_manager = MockVotingManager.return_value
            mock_manager.conduct_full_voting_process.return_value = mock_vote_result
            
            result = await self.voting_service.conduct_secret_ballot(
                participants=participants,
                contexts=contexts,
                discussion_state=self.discussion_state,
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result == mock_vote_result
            assert result.consensus_reached is True
    
    @pytest.mark.asyncio
    async def test_conduct_secret_ballot_no_consensus(self):
        """Test secret ballot phase with no consensus."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        # Mock no consensus vote result
        mock_vote_result = Mock()
        mock_vote_result.consensus_reached = False
        mock_vote_result.disagreement_summary = "Different principle preferences"
        
        with patch('core.services.voting_service.TwoStageVotingManager') as MockVotingManager:
            mock_manager = MockVotingManager.return_value
            mock_manager.conduct_full_voting_process.return_value = mock_vote_result
            
            result = await self.voting_service.conduct_secret_ballot(
                participants=participants,
                contexts=contexts,
                discussion_state=self.discussion_state,
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result == mock_vote_result
            assert result.consensus_reached is False
    
    @pytest.mark.asyncio
    async def test_conduct_secret_ballot_voting_failed(self):
        """Test secret ballot phase when voting process fails."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        with patch('core.services.voting_service.TwoStageVotingManager') as MockVotingManager:
            mock_manager = MockVotingManager.return_value
            mock_manager.conduct_full_voting_process.return_value = None
            
            result = await self.voting_service.conduct_secret_ballot(
                participants=participants,
                contexts=contexts,
                discussion_state=self.discussion_state,
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_conduct_voting_process_full_success(self):
        """Test full voting process with consensus reached."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        initiating_participant = participants[0]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        # Mock all phases succeeding
        mock_vote_result = Mock()
        mock_vote_result.consensus_reached = True
        
        with patch.object(self.voting_service, 'prompt_for_vote_initiation', return_value=True), \
             patch.object(self.voting_service, 'conduct_confirmation_phase', return_value=True), \
             patch.object(self.voting_service, 'conduct_secret_ballot', return_value=mock_vote_result):
            
            result = await self.voting_service.conduct_voting_process(
                participants=participants,
                initiating_participant=initiating_participant,
                contexts=contexts,
                discussion_state=self.discussion_state,
                agent_recent_statement="Let's decide now",
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_conduct_voting_process_no_initiation(self):
        """Test voting process when participant doesn't want to vote."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        initiating_participant = participants[0]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        with patch.object(self.voting_service, 'prompt_for_vote_initiation', return_value=False):
            
            result = await self.voting_service.conduct_voting_process(
                participants=participants,
                initiating_participant=initiating_participant,
                contexts=contexts,
                discussion_state=self.discussion_state,
                agent_recent_statement="Maybe we should continue",
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_voting_process_confirmation_fails(self):
        """Test voting process when confirmation phase fails."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        initiating_participant = participants[0]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        with patch.object(self.voting_service, 'prompt_for_vote_initiation', return_value=True), \
             patch.object(self.voting_service, 'conduct_confirmation_phase', return_value=False):
            
            result = await self.voting_service.conduct_voting_process(
                participants=participants,
                initiating_participant=initiating_participant,
                contexts=contexts,
                discussion_state=self.discussion_state,
                agent_recent_statement="Let's vote",
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_voting_process_no_consensus(self):
        """Test voting process when no consensus is reached."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        initiating_participant = participants[0]
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        # Mock voting result with no consensus
        mock_vote_result = Mock()
        mock_vote_result.consensus_reached = False
        
        with patch.object(self.voting_service, 'prompt_for_vote_initiation', return_value=True), \
             patch.object(self.voting_service, 'conduct_confirmation_phase', return_value=True), \
             patch.object(self.voting_service, 'conduct_secret_ballot', return_value=mock_vote_result):
            
            result = await self.voting_service.conduct_voting_process(
                participants=participants,
                initiating_participant=initiating_participant,
                contexts=contexts,
                discussion_state=self.discussion_state,
                agent_recent_statement="Let's vote",
                error_handler=error_handler,
                utility_agent=utility_agent
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_conduct_voting_process_missing_context(self):
        """Test voting process when initiating participant context is missing."""
        participants = [Mock(name="Alice"), Mock(name="Bob")]
        initiating_participant = Mock(name="Charlie")  # Not in contexts
        contexts = [Mock(name="Alice"), Mock(name="Bob")]
        error_handler = Mock()
        utility_agent = Mock()
        
        result = await self.voting_service.conduct_voting_process(
            participants=participants,
            initiating_participant=initiating_participant,
            contexts=contexts,
            discussion_state=self.discussion_state,
            agent_recent_statement="Let's vote",
            error_handler=error_handler,
            utility_agent=utility_agent
        )
        
        assert result is False
    
    def test_localized_message_integration(self):
        """Test integration with language manager for localized messages."""
        # Test various message keys are requested correctly
        test_keys = [
            "prompts.vote_initiation_prompt",
            "prompts.vote_initiation_with_statement_prompt", 
            "prompts.utility_voting_confirmation_request",
            "system_messages.voting.confirmation_tag",
            "system_messages.voting.all_confirmed",
            "voting_results.consensus_reached",
            "voting_results.no_consensus"
        ]
        
        for key in test_keys:
            self.voting_service._get_localized_message(key)
            # Verify the key was requested (may be called with specific parameters)
            found_call = any(call[0][0] == key for call in self.language_manager.get.call_args_list)
            assert found_call, f"Expected language manager to be called with key: {key}"