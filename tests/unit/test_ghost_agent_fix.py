#!/usr/bin/env python3
"""
Unit tests for the ghost agent fix.
Tests the validation system that prevents agents from contaminating other experiments.
"""

import unittest
import pytest
from models.experiment_types import GroupDiscussionState


@pytest.mark.unit
class TestGhostAgentFix(unittest.TestCase):
    """Unit tests for ghost agent contamination prevention."""
    
    def test_valid_participant_validation(self):
        """Test that valid participants are properly validated."""
        # Create experiment with defined valid participants
        state = GroupDiscussionState()
        state.valid_participants = ["Agent_1", "Agent_2", "Agent_3"]
        
        # Valid agent should be allowed
        state.add_statement("Agent_1", "I prefer maximizing average income")
        self.assertEqual(len(state.statements), 1)
        self.assertIn("Agent_1", state.public_history)
    
    def test_ghost_agent_prevention(self):
        """Test that ghost agents are prevented from contaminating experiments."""
        # Create experiment with 3 agents
        experiment_3_agents = GroupDiscussionState()
        experiment_3_agents.valid_participants = ["Agent_1", "Agent_2", "Agent_3"]
        
        # Add valid statement
        experiment_3_agents.add_statement("Agent_1", "Valid statement")
        
        # Attempt to add statement from non-participant (ghost agent)
        with self.assertRaises(ValueError) as context:
            experiment_3_agents.add_statement("Agent_4", "Ghost agent contamination attempt")
        
        # Verify the error message is appropriate
        self.assertIn("not a valid participant", str(context.exception))
        
        # Verify no contamination occurred
        self.assertEqual(len(experiment_3_agents.statements), 1)
        self.assertNotIn("Agent_4", experiment_3_agents.public_history)
    
    def test_experiment_isolation(self):
        """Test that experiments remain isolated from each other."""
        # Create two separate experiments
        experiment_3_agents = GroupDiscussionState()
        experiment_3_agents.valid_participants = ["Agent_1", "Agent_2", "Agent_3"]
        
        experiment_4_agents = GroupDiscussionState()
        experiment_4_agents.valid_participants = ["Agent_1", "Agent_2", "Agent_3", "Agent_4"]
        
        # Add statements to each experiment
        experiment_3_agents.add_statement("Agent_1", "Statement in 3-agent experiment")
        experiment_4_agents.add_statement("Agent_4", "Statement in 4-agent experiment")
        
        # Verify isolation
        self.assertEqual(len(experiment_3_agents.statements), 1)
        self.assertEqual(len(experiment_4_agents.statements), 1)
        
        # Verify no cross-contamination
        self.assertNotIn("Agent_4", experiment_3_agents.public_history)
        self.assertNotIn("Statement in 4-agent experiment", experiment_3_agents.public_history)
        
        # Verify each experiment has its own content
        self.assertIn("Agent_1", experiment_3_agents.public_history)
        self.assertIn("Agent_4", experiment_4_agents.public_history)
    
    def test_backward_compatibility_no_validation(self):
        """Test that backward compatibility is maintained when no validation is set."""
        # Create state without validation (legacy mode)
        legacy_state = GroupDiscussionState()
        # valid_participants is None by default - should allow any agent
        
        # Any agent name should work in legacy mode
        legacy_state.add_statement("Any_Agent", "This should work in legacy mode")
        legacy_state.add_statement("Random_Name", "This should also work")
        
        self.assertEqual(len(legacy_state.statements), 2)
        self.assertIn("Any_Agent", legacy_state.public_history)
        self.assertIn("Random_Name", legacy_state.public_history)
    
    def test_case_sensitive_validation(self):
        """Test that participant validation is case-sensitive."""
        state = GroupDiscussionState()
        state.valid_participants = ["Agent_1", "Agent_2"]
        
        # Exact case should work
        state.add_statement("Agent_1", "Correct case")
        self.assertEqual(len(state.statements), 1)
        
        # Wrong case should fail
        with self.assertRaises(ValueError):
            state.add_statement("agent_1", "Wrong case")
        
        # Verify only the correct case statement was added
        self.assertEqual(len(state.statements), 1)
    
    def test_empty_valid_participants_list(self):
        """Test behavior with empty valid participants list."""
        state = GroupDiscussionState()
        state.valid_participants = []  # Empty list - no valid participants
        
        # Any agent should be rejected
        with self.assertRaises(ValueError):
            state.add_statement("Agent_1", "Should be rejected")
        
        self.assertEqual(len(state.statements), 0)
    
    def test_participant_list_modification_safety(self):
        """Test that modifying valid_participants list doesn't affect ongoing validation."""
        state = GroupDiscussionState()
        state.valid_participants = ["Agent_1", "Agent_2"]
        
        # Add valid statement
        state.add_statement("Agent_1", "Initial statement")
        
        # Modify valid participants
        state.valid_participants.append("Agent_3")
        
        # New participant should now be valid
        state.add_statement("Agent_3", "Statement from newly added agent")
        
        # Old participants should still be valid
        state.add_statement("Agent_2", "Statement from original agent")
        
        self.assertEqual(len(state.statements), 3)
    
    def test_multiple_statements_same_agent(self):
        """Test that the same valid agent can add multiple statements."""
        state = GroupDiscussionState()
        state.valid_participants = ["Agent_1", "Agent_2"]
        
        # Same agent adds multiple statements
        state.add_statement("Agent_1", "First statement")
        state.add_statement("Agent_1", "Second statement") 
        state.add_statement("Agent_1", "Third statement")
        
        self.assertEqual(len(state.statements), 3)
        
        # Verify all statements are in history
        history = state.public_history
        self.assertIn("First statement", history)
        self.assertIn("Second statement", history)
        self.assertIn("Third statement", history)
    
    def test_mixed_valid_invalid_agents(self):
        """Test mixed scenarios with both valid and invalid agents."""
        state = GroupDiscussionState()
        state.valid_participants = ["Agent_1", "Agent_2"]
        
        # Add valid statements
        state.add_statement("Agent_1", "Valid statement 1")
        state.add_statement("Agent_2", "Valid statement 2")
        
        # Attempt invalid statement
        with self.assertRaises(ValueError):
            state.add_statement("Agent_3", "Invalid statement")
        
        # Add another valid statement
        state.add_statement("Agent_1", "Another valid statement")
        
        # Verify only valid statements were added
        self.assertEqual(len(state.statements), 3)
        self.assertNotIn("Agent_3", state.public_history)
        self.assertNotIn("Invalid statement", state.public_history)


if __name__ == "__main__":
    unittest.main()