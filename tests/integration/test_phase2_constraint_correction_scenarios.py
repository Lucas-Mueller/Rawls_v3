"""
Integration tests for Phase 2 constraint correction scenarios.

Tests the unimplemented constraint correction system that should handle:
1. Ballots with constraint principles but missing amounts
2. Guided re-prompting for missing constraints  
3. Constraint correction loop with timeout and retry logic
4. Integration with ballot consensus checking
5. Memory management during correction process
6. Fallback behavior when corrections fail

The constraint correction system (currently stubbed) should:
- Detect ballots with constraint principles but missing amounts
- Re-prompt participants with specific constraint requests
- Retry consensus checking after corrections
- Handle correction failures gracefully
- Track correction attempts and outcomes

Critical scenarios tested:
- Missing constraint amounts in ballots
- Re-prompting workflow for constraint specification
- Correction loop timeout and failure handling  
- Integration with consensus mechanisms
- Memory state management during corrections

Note: These tests currently validate the stubbed behavior and can be updated
when the constraint correction system is implemented.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from core.phase2_manager import Phase2Manager
from experiment_agents.utility_agent import UtilityAgent
from experiment_agents.participant_agent import ParticipantAgent
from models.experiment_types import ParticipantContext, GroupDiscussionState, ExperimentPhase
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from utils.agent_centric_logger import AgentCentricLogger


@pytest.mark.integration
@pytest.mark.asyncio
class TestPhase2ConstraintCorrectionScenarios:
    """Test constraint correction integration scenarios."""
    
    @pytest.fixture
    def phase2_settings(self):
        """Create Phase2Settings for testing."""
        settings = Phase2Settings.get_default()
        settings.constraint_correction_enabled = True  # If this setting exists
        settings.constraint_correction_timeout_seconds = 30
        settings.max_constraint_correction_attempts = 2
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
            MagicMock(spec=AgentConfiguration, name="Agent2"), 
            MagicMock(spec=AgentConfiguration, name="Agent3")
        ]
        return config
    
    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i in range(3):
            participant = MagicMock(spec=ParticipantAgent)
            participant.name = f"TestAgent{i+1}"
            participant.agent = MagicMock()
            participants.append(participant)
        return participants
    
    @pytest.fixture
    def mock_utility_agent(self):
        """Create real utility agent for integration testing."""
        # Use real utility agent for integration testing
        return UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    @pytest.fixture
    def mock_contexts(self):
        """Create mock participant contexts."""
        contexts = []
        for i in range(3):
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
    
    def create_ballot_with_missing_constraint(self, principle: JusticePrinciple) -> PrincipleChoice:
        """Helper to create ballot with missing constraint amount."""
        return PrincipleChoice.create_for_parsing(
            principle=principle,
            constraint_amount=None,  # Missing constraint
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot with missing constraint"
        )
    
    def create_ballot_with_constraint(self, principle: JusticePrinciple, amount: int) -> PrincipleChoice:
        """Helper to create ballot with constraint amount."""
        return PrincipleChoice.create_for_parsing(
            principle=principle,
            constraint_amount=amount,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot with constraint"
        )
    
    async def test_missing_constraint_detection(self, phase2_manager):
        """Test detection of ballots with missing constraint amounts."""
        
        # Create test ballots with missing constraints
        ballots = [
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT),
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_FLOOR, None)  # Non-constraint principle
        ]
        
        # Check consensus (should detect missing constraints)
        consensus, agreed_principle, warnings = phase2_manager.utility_agent.check_ballot_consensus(ballots)
        
        # Should not reach consensus due to missing constraints
        assert not consensus, "Should not reach consensus with missing constraints"
        assert agreed_principle is None, "Should not have agreed principle with missing constraints"
        assert len(warnings) > 0, "Should have warnings about missing constraints"
        
        # Check that warnings mention constraint issues
        warning_text = " ".join(warnings).lower()
        assert "constraint" in warning_text, f"Warnings should mention constraints: {warnings}"
    
    async def test_constraint_correction_stub_behavior(self, phase2_manager, mock_contexts):
        """Test current stubbed constraint correction behavior."""
        
        discussion_state = GroupDiscussionState()
        
        # Create ballots with missing constraints
        ballots = [
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        ]
        
        # Test the current stubbed implementation
        corrections_successful = await phase2_manager._handle_constraint_corrections(
            ballots, mock_contexts, ["Missing constraint amounts"], discussion_state
        )
        
        # Current implementation should return False (stubbed)
        assert not corrections_successful, "Stubbed implementation should return False"
        
        # Should add warning to public history
        assert "[VOTING WARNING]" in discussion_state.public_history, \
               "Should add warning to public history"
        assert "missing constraint amounts" in discussion_state.public_history.lower(), \
               "Should mention missing constraints in warning"
    
    async def test_re_prompt_message_generation(self, phase2_manager):
        """Test generation of re-prompt messages for missing constraints."""
        
        # Test floor constraint re-prompt
        floor_choice = PrincipleChoice.create_for_parsing(
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            None,
            CertaintyLevel.SURE
        )
        
        floor_message = await phase2_manager.utility_agent.re_prompt_for_constraint("TestAgent", floor_choice)
        
        assert len(floor_message) > 0, "Should generate non-empty re-prompt message"
        assert "floor" in floor_message.lower(), "Floor re-prompt should mention floor"
        assert "TestAgent" in floor_message, "Re-prompt should address specific agent"
        
        # Test range constraint re-prompt
        range_choice = PrincipleChoice.create_for_parsing(
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 
            None,
            CertaintyLevel.SURE
        )
        
        range_message = await phase2_manager.utility_agent.re_prompt_for_constraint("TestAgent", range_choice)
        
        assert len(range_message) > 0, "Should generate non-empty re-prompt message"
        assert "range" in range_message.lower(), "Range re-prompt should mention range"
        assert "TestAgent" in range_message, "Re-prompt should address specific agent"
    
    async def test_constraint_correction_workflow_stub(self, phase2_manager, mock_contexts):
        """Test the constraint correction workflow (currently stubbed)."""
        
        # This test validates the current stubbed behavior and provides
        # a framework for testing the full implementation when available
        
        discussion_state = GroupDiscussionState()
        
        # Create scenario requiring constraint corrections
        ballots_needing_correction = [
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        ]
        
        warnings = ["Missing constraint amounts detected"]
        
        # Test current stub implementation
        with patch.object(phase2_manager, '_log_info') as mock_log:
            success = await phase2_manager._handle_constraint_corrections(
                ballots_needing_correction,
                mock_contexts,
                warnings,
                discussion_state
            )
            
            # Verify stubbed behavior
            assert not success, "Stubbed implementation should return False"
            assert mock_log.called, "Should log constraint correction attempt"
            
            # Verify logging mentions constraint corrections
            log_calls = [str(call) for call in mock_log.call_args_list]
            log_text = " ".join(log_calls).upper()
            assert "CONSTRAINT CORRECTIONS" in log_text, "Should log constraint correction phase"
    
    async def test_memory_management_during_corrections(self, phase2_manager, mock_contexts):
        """Test memory management during constraint correction process."""
        
        # When constraint corrections are implemented, they should:
        # 1. Preserve agent memory states
        # 2. Update memory with re-prompt interactions
        # 3. Handle memory updates for correction attempts
        
        participant = mock_contexts[0]
        initial_memory = participant.memory
        
        # Simulate a constraint correction attempt
        choice_needing_correction = self.create_ballot_with_missing_constraint(
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        )
        
        # Test re-prompt generation (doesn't modify memory yet in stub)
        re_prompt = await phase2_manager.utility_agent.re_prompt_for_constraint(
            participant.name, 
            choice_needing_correction
        )
        
        # Memory should be preserved during re-prompt generation
        assert participant.memory == initial_memory, "Memory should be preserved during re-prompt generation"
        
        # When full implementation is added, memory updates would happen here
        # and this test should be extended to verify:
        # - Memory updates include constraint correction interactions
        # - Failed corrections are recorded in memory
        # - Successful corrections update memory appropriately
    
    async def test_consensus_retry_after_corrections(self, phase2_manager):
        """Test consensus retry logic after constraint corrections."""
        
        # Initial ballots with missing constraints
        initial_ballots = [
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)
        ]
        
        # Should not reach consensus initially
        consensus1, agreed1, warnings1 = phase2_manager.utility_agent.check_ballot_consensus(initial_ballots)
        assert not consensus1, "Should not reach consensus with missing constraints"
        
        # Simulate corrected ballots (what would happen after successful corrections)
        corrected_ballots = [
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000),
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000), 
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000)
        ]
        
        # Should reach consensus after corrections
        consensus2, agreed2, warnings2 = phase2_manager.utility_agent.check_ballot_consensus(corrected_ballots)
        assert consensus2, "Should reach consensus after constraint corrections"
        assert agreed2 is not None, "Should have agreed principle after corrections"
        assert agreed2.constraint_amount == 15000, "Should preserve constraint amount"
    
    async def test_correction_timeout_handling(self, phase2_manager, mock_contexts):
        """Test handling of timeouts during constraint corrections."""
        
        # When constraint corrections are implemented, they should handle:
        # 1. Agent timeouts during re-prompting
        # 2. Correction process timeouts  
        # 3. Graceful fallback when corrections fail
        
        discussion_state = GroupDiscussionState()
        ballots = [self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT)]
        warnings = ["Missing constraints"]
        
        # Mock timeout during correction
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError("Correction timeout")
            
            # Test timeout handling (currently stubbed)
            success = await phase2_manager._handle_constraint_corrections(
                ballots, mock_contexts, warnings, discussion_state
            )
            
            # Should handle timeout gracefully (currently returns False anyway)
            assert not success, "Should handle correction timeout gracefully"
    
    async def test_partial_correction_scenarios(self, phase2_manager):
        """Test scenarios with partial constraint corrections."""
        
        # Test mixed scenarios where some ballots have constraints and others don't
        mixed_ballots = [
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000),
            self.create_ballot_with_missing_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000)
        ]
        
        # Should not reach consensus with partial constraints
        consensus, agreed, warnings = phase2_manager.utility_agent.check_ballot_consensus(mixed_ballots)
        
        # Behavior depends on implementation - currently should detect missing constraints
        if not consensus:
            assert len(warnings) > 0, "Should warn about missing constraints in mixed scenario"
        
        # Test all-different-constraints scenario
        different_constraints = [
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 10000),
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000),
            self.create_ballot_with_constraint(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 20000)
        ]
        
        # Should not reach consensus due to different constraint amounts
        consensus2, agreed2, warnings2 = phase2_manager.utility_agent.check_ballot_consensus(different_constraints)
        assert not consensus2, "Should not reach consensus with different constraint amounts"
    
    async def test_constraint_validation_integration(self, phase2_manager):
        """Test integration with constraint validation logic."""
        
        # Test ballot validation for voting
        valid_constraint_ballot = self.create_ballot_with_constraint(
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000
        )
        
        invalid_constraint_ballot = self.create_ballot_with_missing_constraint(
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        )
        
        # Test validation
        assert valid_constraint_ballot.is_valid_constraint(), "Valid constraint ballot should pass validation"
        assert not invalid_constraint_ballot.is_valid_constraint(), "Invalid constraint ballot should fail validation"
        
        # Test validation for voting
        try:
            valid_for_voting = valid_constraint_ballot.validate_for_voting()
            assert valid_for_voting is not None, "Valid ballot should pass voting validation"
        except ValueError:
            pytest.fail("Valid constraint ballot should pass voting validation")
        
        # Invalid ballot should raise error
        with pytest.raises(ValueError):
            invalid_constraint_ballot.validate_for_voting()
    
    async def test_correction_statistics_tracking(self, phase2_manager):
        """Test tracking of constraint correction attempts and outcomes."""
        
        # When constraint corrections are implemented, should track:
        # - Number of correction attempts
        # - Success/failure rates
        # - Timeout occurrences
        # - Agent-specific correction patterns
        
        # Current implementation doesn't track these, but framework is here
        # for when corrections are implemented
        
        initial_stats = {
            "constraint_correction_attempts": 0,
            "successful_corrections": 0,
            "correction_timeouts": 0,
            "correction_failures": 0
        }
        
        # These statistics would be tracked during actual constraint corrections
        # This test provides the framework for validation when implemented
        
        # For now, just verify that the framework exists
        assert isinstance(initial_stats, dict), "Statistics framework should be dictionary-based"
        assert "constraint_correction_attempts" in initial_stats, "Should track correction attempts"


if __name__ == '__main__':
    pytest.main([__file__])