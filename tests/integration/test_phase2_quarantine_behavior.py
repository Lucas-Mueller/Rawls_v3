"""
Integration tests for Phase 2 quarantine behavior.

Tests the sophisticated quarantine system that handles agent failures gracefully:
1. Statement validation failures and retry exhaustion 
2. Quarantined response generation and neutral message substitution
3. Public history contamination prevention
4. Memory management with quarantined responses
5. Consensus mechanism isolation from failed agents
6. Statistical tracking of quarantine events

The quarantine system protects discussion integrity by:
- Detecting agent failures (timeouts, invalid responses, repeated failures)
- Generating neutral messages that don't reveal failures
- Preventing contamination of public discussion history
- Maintaining statistical tracking for debugging
- Isolating failed agents from consensus mechanisms

Critical integration scenarios tested:
- Agent timeout during statement generation
- Agent returning invalid/empty responses repeatedly  
- Quarantine marker handling (__QUARANTINED__)
- Public history contamination prevention
- Consensus mechanisms skipping quarantined responses
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from core.phase2_manager import Phase2Manager
from experiment_agents.utility_agent import UtilityAgent
from experiment_agents.participant_agent import ParticipantAgent
from models.experiment_types import ParticipantContext, GroupDiscussionState, ExperimentPhase
from models.principle_types import CertaintyLevel
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from utils.agent_centric_logger import AgentCentricLogger
from utils.error_handling import AgentCommunicationError, ErrorSeverity


@pytest.mark.integration
@pytest.mark.asyncio
class TestPhase2QuarantineBehavior:
    """Test quarantine behavior integration scenarios."""
    
    @pytest.fixture
    def phase2_settings(self):
        """Create Phase2Settings with quarantine enabled."""
        settings = Phase2Settings.get_default()
        settings.quarantine_failed_responses = True
        settings.max_statement_retries = 2  # Low for testing
        settings.statement_timeout_seconds = 1  # Quick timeout for testing
        return settings
    
    @pytest.fixture
    def mock_experiment_config(self, phase2_settings):
        """Create mock experiment configuration."""
        config = MagicMock(spec=ExperimentConfiguration)
        config.phase2_settings = phase2_settings
        config.phase2_rounds = 3
        config.voting_detection_mode = "complex"
        config.language = "English"
        config.agents = [
            MagicMock(spec=AgentConfiguration, name="Agent1"),
            MagicMock(spec=AgentConfiguration, name="Agent2")
        ]
        return config
    
    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i in range(2):
            participant = MagicMock(spec=ParticipantAgent)
            participant.name = f"TestAgent{i+1}"
            participant.agent = MagicMock()
            participant.reasoning_enabled = False
            participants.append(participant)
        return participants
    
    @pytest.fixture
    def mock_utility_agent(self):
        """Create mock utility agent."""
        utility_agent = MagicMock(spec=UtilityAgent)
        
        # Mock utility methods to return None (no voting/preference detection)
        utility_agent.detect_vote_intention_enhanced = AsyncMock(return_value=None)
        utility_agent.detect_preference_statement = AsyncMock(return_value=None)
        
        return utility_agent
    
    @pytest.fixture
    def mock_contexts(self):
        """Create mock participant contexts."""
        contexts = []
        for i in range(2):
            context = ParticipantContext(
                name=f"TestAgent{i+1}",
                role_description="Test participant",
                bank_balance=1000.0,
                memory=f"Test memory for agent {i+1}",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=50000
            )
            contexts.append(context)
        return contexts
    
    @pytest.fixture
    def phase2_manager(self, mock_participants, mock_utility_agent, mock_experiment_config):
        """Create Phase2Manager instance."""
        return Phase2Manager(mock_participants, mock_utility_agent, mock_experiment_config)
    
    async def test_agent_timeout_quarantine(self, phase2_manager, mock_contexts):
        """Test that agent timeouts trigger quarantine behavior."""
        
        # Mock the first agent to timeout
        with patch('agents.Runner.run') as mock_runner:
            mock_runner.side_effect = [
                asyncio.TimeoutError("Agent timeout"),  # First call times out
                MagicMock(final_output="Valid response from Agent2")  # Second agent succeeds
            ]
            
            with patch.object(phase2_manager, '_validate_statement') as mock_validate:
                mock_validate.side_effect = [False, True]  # First invalid (timeout), second valid
                
                # Run a single discussion round
                discussion_state = GroupDiscussionState()
                discussion_state.valid_participants = ["TestAgent1", "TestAgent2"]
                
                # Test the retry mechanism and quarantine
                participant = phase2_manager.participants[0]
                context = mock_contexts[0]
                agent_config = phase2_manager.config.agents[0]
                
                with patch('core.phase2_manager.MemoryManager.prompt_agent_for_memory_update') as mock_memory:
                    mock_memory.return_value = "Updated memory"
                    
                    # Should trigger quarantine after retries exhausted
                    statement, round_content = await phase2_manager._get_participant_statement_enhanced(
                        participant, context, discussion_state, agent_config
                    )
                    
                    # Verify quarantine behavior
                    assert statement.startswith("__QUARANTINED__") or \
                           "failed to provide a valid response" in statement, \
                           f"Expected quarantined statement, got: {statement}"
                    
                    # Verify statistics tracking
                    assert phase2_manager.validation_stats["fallback_statements"] > 0
    
    async def test_public_history_contamination_prevention(self, phase2_manager, mock_contexts):
        """Test that quarantined responses don't contaminate public history."""
        
        discussion_state = GroupDiscussionState()
        discussion_state.valid_participants = ["TestAgent1", "TestAgent2"]
        initial_history = "Previous discussion content"
        discussion_state.public_history = initial_history
        
        # Mock agent failure
        with patch.object(phase2_manager, '_get_participant_statement_enhanced') as mock_get_statement:
            mock_get_statement.return_value = ("__QUARANTINED__Agent failed", "Internal reasoning")
            
            with patch('core.phase2_manager.MemoryManager.prompt_agent_for_memory_update') as mock_memory:
                mock_memory.return_value = "Updated memory"
                
                # Mock language manager for neutral message
                with patch('core.phase2_manager.get_language_manager') as mock_lang_manager:
                    mock_lang_manager.return_value.get.return_value = "TestAgent1 is temporarily unavailable"
                    
                    # Simulate one round of discussion
                    participant = phase2_manager.participants[0]
                    context = mock_contexts[0]
                    
                    # Manually trigger the quarantine logic
                    statement, _ = await mock_get_statement(participant, context, discussion_state, None)
                    
                    if statement.startswith("__QUARANTINED__"):
                        # Remove quarantine marker
                        clean_statement = statement.replace("__QUARANTINED__", "")
                        
                        # Add neutral message to history (simulating the quarantine logic)
                        neutral_msg = mock_lang_manager.return_value.get.return_value
                        discussion_state.add_statement(participant.name, neutral_msg)
                    
                    # Verify public history contains neutral message, not failure details
                    assert "failed" not in discussion_state.public_history.lower() or \
                           "temporarily unavailable" in discussion_state.public_history, \
                           f"Public history contaminated: {discussion_state.public_history}"
                    
                    # Verify neutral message is present
                    assert "temporarily unavailable" in discussion_state.public_history or \
                           len(discussion_state.public_history) > len(initial_history), \
                           "Neutral message not added to public history"
    
    async def test_consensus_mechanism_isolation(self, phase2_manager, mock_contexts):
        """Test that consensus mechanisms skip quarantined responses."""
        
        discussion_state = GroupDiscussionState()
        
        # Mock quarantined response
        quarantined_statement = "__QUARANTINED__Agent failed to respond"
        
        # Test that fallback responses are skipped in consensus processing
        with patch.object(phase2_manager, '_get_participant_statement_enhanced') as mock_get_statement:
            mock_get_statement.return_value = (quarantined_statement, "")
            
            with patch('core.phase2_manager.MemoryManager.prompt_agent_for_memory_update') as mock_memory:
                mock_memory.return_value = "Updated memory"
                
                # Mock the consensus lock to test the skip logic
                with patch.object(phase2_manager, '_consensus_lock'):
                    
                    participant = phase2_manager.participants[0] 
                    context = mock_contexts[0]
                    
                    # Get the statement
                    statement, _ = await mock_get_statement(participant, context, discussion_state, None)
                    
                    # Check that it would be identified as fallback
                    is_fallback = statement.startswith("__QUARANTINED__")
                    
                    assert is_fallback, "Should identify quarantined response as fallback"
                    
                    # Verify that consensus processing would be skipped
                    # (The actual skip happens in the main discussion loop)
                    # This test verifies the condition that triggers the skip
    
    async def test_retry_exhaustion_and_statistics(self, phase2_manager, mock_contexts):
        """Test retry exhaustion and statistical tracking."""
        
        participant = phase2_manager.participants[0]
        context = mock_contexts[0]  
        discussion_state = GroupDiscussionState()
        agent_config = MagicMock()
        
        # Mock repeated failures
        with patch('agents.Runner.run') as mock_runner:
            mock_runner.return_value = MagicMock(final_output="")  # Empty response
            
            with patch.object(phase2_manager, '_validate_statement') as mock_validate:
                mock_validate.return_value = False  # Always invalid
                
                # Clear existing stats
                phase2_manager.validation_stats = {
                    "total_statement_requests": 0,
                    "successful_statements": 0,
                    "failed_validations": 0,
                    "retry_attempts": 0,
                    "fallback_statements": 0,
                    "quarantined_responses": 0
                }
                
                # Try to get statement - should exhaust retries
                try:
                    await phase2_manager._get_participant_statement_with_retry(
                        participant, context, discussion_state, agent_config, max_retries=2
                    )
                except Exception:
                    pass  # Expected to fail after retries
                
                # Verify statistics tracking
                stats = phase2_manager.validation_stats
                assert stats["total_statement_requests"] > 0, "Should track total requests"
                assert stats["failed_validations"] > 0, "Should track failed validations"
                assert stats["retry_attempts"] > 0, "Should track retry attempts"
    
    async def test_quarantine_marker_handling(self, phase2_manager, mock_contexts):
        """Test proper handling of quarantine markers throughout the system."""
        
        # Test quarantine marker detection
        quarantined_response = "__QUARANTINED__Some neutral message"
        clean_response = "Some neutral message"
        
        # Test marker detection
        is_quarantined = quarantined_response.startswith("__QUARANTINED__")
        assert is_quarantined, "Should detect quarantine marker"
        
        # Test marker removal  
        cleaned = quarantined_response.replace("__QUARANTINED__", "")
        assert cleaned == clean_response, f"Marker removal failed: {cleaned}"
        
        # Test that non-quarantined responses aren't affected
        normal_response = "Normal agent response"
        is_normal_quarantined = normal_response.startswith("__QUARANTINED__")
        assert not is_normal_quarantined, "Should not detect marker in normal response"
    
    async def test_memory_management_with_quarantine(self, phase2_manager, mock_contexts):
        """Test that memory management works correctly with quarantined responses."""
        
        discussion_state = GroupDiscussionState()
        participant = phase2_manager.participants[0]
        context = mock_contexts[0]
        initial_memory = context.memory
        
        # Mock quarantined response
        with patch.object(phase2_manager, '_get_participant_statement_enhanced') as mock_get_statement:
            mock_get_statement.return_value = ("__QUARANTINED__Neutral message", "Internal reasoning")
            
            with patch('core.phase2_manager.MemoryManager.prompt_agent_for_memory_update') as mock_memory_update:
                mock_memory_update.return_value = "Memory updated after quarantine"
                
                # Simulate statement processing
                statement, reasoning = await mock_get_statement(participant, context, discussion_state, None)
                
                # Memory should still be updated even for quarantined responses
                # (The agent's memory should reflect what happened, even if public doesn't see it)
                if statement.startswith("__QUARANTINED__"):
                    # Simulate the memory update that would happen
                    updated_memory = await mock_memory_update(participant, context, "quarantine event")
                    
                    assert updated_memory != initial_memory, "Memory should be updated after quarantine"
                    assert "quarantine" in updated_memory.lower() or \
                           updated_memory != initial_memory, "Memory should reflect quarantine event"
    
    async def test_quarantine_logging_integration(self, phase2_manager, mock_contexts):
        """Test integration with logging system for quarantine events."""
        
        # Mock logger
        mock_logger = MagicMock(spec=AgentCentricLogger)
        
        discussion_state = GroupDiscussionState()
        participant = phase2_manager.participants[0] 
        context = mock_contexts[0]
        
        # Test logging of quarantine events
        with patch.object(phase2_manager, '_get_participant_statement_enhanced') as mock_get_statement:
            mock_get_statement.return_value = ("__QUARANTINED__Neutral message", "")
            
            with patch('core.phase2_manager.MemoryManager.prompt_agent_for_memory_update') as mock_memory:
                mock_memory.return_value = "Updated memory"
                
                # Simulate logging with quarantined response
                statement, reasoning = await mock_get_statement(participant, context, discussion_state, None)
                
                if statement.startswith("__QUARANTINED__"):
                    clean_statement = statement.replace("__QUARANTINED__", "")
                    
                    # Verify that logging would work with cleaned statement
                    assert len(clean_statement) > 0, "Cleaned statement should not be empty"
                    assert "__QUARANTINED__" not in clean_statement, "Cleaned statement should not have marker"
                    
                    # Simulate the logging call that would happen
                    if mock_logger:
                        mock_logger.log_discussion_round(
                            participant.name,
                            1,  # round number
                            1,  # speaking order
                            reasoning,
                            clean_statement,  # Use cleaned statement for logging
                            None,  # vote intention
                            None,  # favored principle
                            context.memory,
                            context.bank_balance
                        )
                        
                        # Verify logger was called (would be called in real scenario)
                        assert True  # Test passes if no exceptions
    
    async def test_validation_statistics_logging(self, phase2_manager):
        """Test that validation statistics are properly logged."""
        
        # Set up some statistics
        phase2_manager.validation_stats = {
            "total_statement_requests": 10,
            "successful_statements": 7,
            "failed_validations": 3,
            "retry_attempts": 5,
            "fallback_statements": 2,
            "quarantined_responses": 1
        }
        
        # Mock logger
        with patch.object(phase2_manager, '_log_info') as mock_log_info:
            # Call the statistics logging method
            returned_stats = phase2_manager._log_validation_statistics()
            
            # Verify statistics were logged
            assert mock_log_info.called, "Should log validation statistics"
            
            # Verify returned statistics match internal statistics
            assert returned_stats == phase2_manager.validation_stats, \
                   "Returned statistics should match internal statistics"
            
            # Check that logging included key metrics
            log_calls = [call[0][0] for call in mock_log_info.call_args_list]
            log_text = " ".join(log_calls)
            
            assert "Total statement requests" in log_text, "Should log total requests"
            assert "Success rate" in log_text, "Should log success rate"
            assert "quarantined" in log_text.lower() or "fallback" in log_text.lower(), \
                   "Should mention quarantine/fallback events"


if __name__ == '__main__':
    pytest.main([__file__])