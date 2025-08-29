"""
Unit tests for constraint correction functionality in Phase 2 voting.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.phase2_manager import Phase2Manager
from experiment_agents import UtilityAgent, ParticipantAgent
from models import PrincipleChoice, JusticePrinciple, ParticipantContext, ExperimentPhase, GroupDiscussionState
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings


class TestConstraintCorrection(unittest.TestCase):
    """Test constraint correction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock participants and utility agent
        self.mock_participant = MagicMock(spec=ParticipantAgent)
        self.mock_participant.name = "TestAgent"
        self.mock_participant.agent = AsyncMock()
        
        self.participants = [self.mock_participant]
        
        # Create utility agent
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
        
        # Create phase 2 manager
        self.mock_config = MagicMock(spec=ExperimentConfiguration)
        self.mock_config.phase2_settings = Phase2Settings.get_default()
        self.mock_config.memory_guidance_style = "narrative"
        
        self.phase2_manager = Phase2Manager(
            participants=self.participants,
            utility_agent=self.utility_agent,
            experiment_config=self.mock_config
        )
        
        # Create test contexts
        self.contexts = [
            ParticipantContext(
                name="TestAgent",
                role_description="Test participant",
                bank_balance=100.0,
                memory="Initial memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=50000
            )
        ]
        
        # Create discussion state
        self.discussion_state = GroupDiscussionState()
        
    def test_constraint_correction_success_floor(self):
        """Test successful constraint correction for floor constraint principle."""
        
        async def run_test():
            # Create ballot with missing constraint
            ballot = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Test ballot"
            )
            ballots = [ballot]
            warnings = ["Ballot missing constraint amount for maximizing_average_floor_constraint"]
            
            # Mock the agent response and extraction
            mock_result = MagicMock()
            mock_result.final_output = "I want a floor constraint of $15,000"
            
            with patch('agents.Runner.run', return_value=mock_result):
                with patch.object(self.utility_agent, '_extract_constraint_amount_flexible', return_value=15000):
                    with patch('utils.memory_manager.MemoryManager.prompt_agent_for_memory_update', return_value="Updated memory"):
                        
                        result = await self.phase2_manager._handle_constraint_corrections(
                            ballots, self.contexts, warnings, self.discussion_state
                        )
                        
                        # Should return True (success)
                        self.assertTrue(result)
                        
                        # Ballot should be updated with constraint amount
                        self.assertEqual(ballot.constraint_amount, 15000)
                        
                        # Discussion state should show success message
                        self.assertIn("Corrected 1 missing constraint amounts", self.discussion_state.public_history)
        
        asyncio.run(run_test())
    
    def test_constraint_correction_success_range(self):
        """Test successful constraint correction for range constraint principle."""
        
        async def run_test():
            # Create ballot with missing constraint
            ballot = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                constraint_amount=None,
                certainty="sure", 
                reasoning="Test ballot"
            )
            ballots = [ballot]
            warnings = ["Ballot missing constraint amount for maximizing_average_range_constraint"]
            
            # Mock the agent response and extraction
            mock_result = MagicMock()
            mock_result.final_output = "I choose a range constraint of $25,000"
            
            with patch('agents.Runner.run', return_value=mock_result):
                with patch.object(self.utility_agent, '_extract_constraint_amount_flexible', return_value=25000):
                    with patch('utils.memory_manager.MemoryManager.prompt_agent_for_memory_update', return_value="Updated memory"):
                        
                        result = await self.phase2_manager._handle_constraint_corrections(
                            ballots, self.contexts, warnings, self.discussion_state
                        )
                        
                        # Should return True (success)
                        self.assertTrue(result)
                        
                        # Ballot should be updated with constraint amount
                        self.assertEqual(ballot.constraint_amount, 25000)
        
        asyncio.run(run_test())
    
    def test_constraint_correction_failure(self):
        """Test constraint correction failure when amount cannot be extracted."""
        
        async def run_test():
            # Create ballot with missing constraint
            ballot = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Test ballot"
            )
            ballots = [ballot]
            warnings = ["Ballot missing constraint amount for maximizing_average_floor_constraint"]
            
            # Mock the agent response and failed extraction
            mock_result = MagicMock()
            mock_result.final_output = "I'm not sure about the exact amount"
            
            with patch('agents.Runner.run', return_value=mock_result):
                with patch.object(self.utility_agent, '_extract_constraint_amount_flexible', return_value=None):
                    
                    result = await self.phase2_manager._handle_constraint_corrections(
                        ballots, self.contexts, warnings, self.discussion_state
                    )
                    
                    # Should return False (failure)
                    self.assertFalse(result)
                    
                    # Ballot should still have no constraint amount
                    self.assertIsNone(ballot.constraint_amount)
                    
                    # Discussion state should show failure message
                    self.assertIn("Could not correct missing constraint amounts", self.discussion_state.public_history)
        
        asyncio.run(run_test())
    
    def test_constraint_correction_no_corrections_needed(self):
        """Test when no ballots need constraint correction."""
        
        async def run_test():
            # Create ballot that doesn't need correction (single ballot to match single participant)
            ballots = [
                PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_FLOOR,  # Doesn't require constraint
                    constraint_amount=None,
                    certainty="sure",
                    reasoning="Test ballot"
                )
            ]
            warnings = []
            
            result = await self.phase2_manager._handle_constraint_corrections(
                ballots, self.contexts, warnings, self.discussion_state
            )
            
            # Should return False since no corrections were made
            self.assertFalse(result)
        
        asyncio.run(run_test())
    
    def test_constraint_correction_timeout(self):
        """Test constraint correction when agent times out."""
        
        async def run_test():
            # Create ballot with missing constraint
            ballot = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Test ballot"
            )
            ballots = [ballot]
            warnings = ["Ballot missing constraint amount for maximizing_average_floor_constraint"]
            
            # Mock timeout
            with patch('agents.Runner.run', side_effect=asyncio.TimeoutError()):
                
                result = await self.phase2_manager._handle_constraint_corrections(
                    ballots, self.contexts, warnings, self.discussion_state
                )
                
                # Should return False (failure due to timeout)
                self.assertFalse(result)
                
                # Ballot should still have no constraint amount
                self.assertIsNone(ballot.constraint_amount)
        
        asyncio.run(run_test())
    
    def test_constraint_correction_mixed_results(self):
        """Test constraint correction with mixed success/failure results."""
        
        async def run_test():
            # Create second participant for this test
            mock_participant2 = MagicMock(spec=ParticipantAgent)
            mock_participant2.name = "TestAgent2"
            mock_participant2.agent = AsyncMock()
            
            # Add second participant temporarily
            original_participants = self.phase2_manager.participants
            self.phase2_manager.participants = [self.participants[0], mock_participant2]
            
            # Create second context
            context2 = ParticipantContext(
                name="TestAgent2",
                role_description="Test participant 2", 
                bank_balance=100.0,
                memory="Initial memory 2",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=50000
            )
            
            # Create ballots with different correction needs
            ballot1 = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Test ballot 1"
            )
            ballot2 = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Test ballot 2"
            )
            
            ballots = [ballot1, ballot2]
            contexts = [self.contexts[0], context2]  # Two contexts for two ballots
            warnings = ["Multiple missing constraint amounts"]
            
            # Mock responses - first succeeds, second fails
            mock_results = [
                MagicMock(final_output="Floor constraint of $15,000"),
                MagicMock(final_output="I don't know the amount")
            ]
            
            def side_effect(*args, **kwargs):
                return mock_results.pop(0)
            
            # Mock extraction - first succeeds, second fails
            extract_results = [15000, None]
            def extract_side_effect(*args, **kwargs):
                return extract_results.pop(0) if extract_results else None
            
            with patch('agents.Runner.run', side_effect=side_effect):
                with patch.object(self.utility_agent, '_extract_constraint_amount_flexible', side_effect=extract_side_effect):
                    with patch('utils.memory_manager.MemoryManager.prompt_agent_for_memory_update', return_value="Updated memory"):
                        
                        result = await self.phase2_manager._handle_constraint_corrections(
                            ballots, contexts, warnings, self.discussion_state
                        )
                        
                        # Should return True since at least one correction was made
                        self.assertTrue(result)
                        
                        # First ballot should be corrected, second should not
                        self.assertEqual(ballot1.constraint_amount, 15000)
                        self.assertIsNone(ballot2.constraint_amount)
                        
                        # Should show success message for partial correction
                        self.assertIn("Corrected 1 missing constraint amounts", self.discussion_state.public_history)
                        
                        # Restore original participants
                        self.phase2_manager.participants = original_participants
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()