#!/usr/bin/env python3
"""
Test script for voting history implementation.
Tests the new voting history data structures and AgentCentricLogger methods.
"""

import unittest
import json
from models.logging_types import VotingHistoryLog, VoteRoundDetails, TargetStateStructure, GeneralExperimentInfo
from utils.agent_centric_logger import AgentCentricLogger


class TestVotingHistoryStructures(unittest.TestCase):
    """Test cases for voting history data structures."""
    
    def test_vote_round_details_creation(self):
        """Test VoteRoundDetails structure creation."""
        vote_round = VoteRoundDetails(
            round_number=2,
            vote_type="formal_vote",
            participant_votes=[
                {
                    "participant_name": "Agent_1",
                    "raw_response": "I prefer Maximizing average income",
                    "assessed_choice": "Maximizing average income",
                    "constraint_amount": None,
                    "vote_timestamp": "2024-08-26T14:30:15.123456",
                    "parsing_success": True
                },
                {
                    "participant_name": "Agent_2",
                    "raw_response": "I also choose average income maximization",
                    "assessed_choice": "Maximizing average income", 
                    "constraint_amount": None,
                    "vote_timestamp": "2024-08-26T14:30:16.789012",
                    "parsing_success": True
                }
            ],
            consensus_reached=True,
            agreed_principle="Maximizing average income",
            vote_counts={"Maximizing average income": 2}
        )
        
        self.assertEqual(vote_round.round_number, 2)
        self.assertEqual(vote_round.vote_type, "formal_vote")
        self.assertTrue(vote_round.consensus_reached)
        self.assertEqual(vote_round.agreed_principle, "Maximizing average income")
        self.assertEqual(len(vote_round.participant_votes), 2)
        self.assertEqual(vote_round.vote_counts["Maximizing average income"], 2)
    
    def test_voting_history_log_creation(self):
        """Test VotingHistoryLog structure creation."""
        vote_round = VoteRoundDetails(
            round_number=1,
            vote_type="formal_vote",
            participant_votes=[],
            consensus_reached=True,
            agreed_principle="Maximizing floor income",
            vote_counts={"Maximizing floor income": 2}
        )
        
        voting_history = VotingHistoryLog(
            voting_detection_mode="simple",
            total_vote_attempts=1,
            successful_votes=1,
            vote_rounds=[vote_round]
        )
        
        self.assertEqual(voting_history.voting_detection_mode, "simple")
        self.assertEqual(voting_history.total_vote_attempts, 1)
        self.assertEqual(voting_history.successful_votes, 1)
        self.assertEqual(len(voting_history.vote_rounds), 1)
        self.assertEqual(voting_history.vote_rounds[0].round_number, 1)
    
    def test_target_state_structure_with_voting_history(self):
        """Test TargetStateStructure creation with voting history."""
        # Create voting history
        vote_round = VoteRoundDetails(
            round_number=2,
            vote_type="formal_vote",
            participant_votes=[],
            consensus_reached=True,
            agreed_principle="Test principle",
            vote_counts={"Test principle": 3}
        )
        
        voting_history = VotingHistoryLog(
            voting_detection_mode="complex",
            total_vote_attempts=2,
            successful_votes=1,
            vote_rounds=[vote_round]
        )
        
        # Create general experiment info
        general_info = GeneralExperimentInfo(
            consensus_reached=True,
            max_rounds_phase_2=5,
            rounds_conducted_phase_2=2,
            public_conversation_phase_2="Test conversation",
            final_vote_results={"Agent_1": "Test principle", "Agent_2": "Test principle"},
            config_file_used="test_config.yaml"
        )
        
        # Create target state structure
        target_state = TargetStateStructure(
            general_information=general_info,
            agents=[],
            voting_history=voting_history
        )
        
        self.assertIsNotNone(target_state.voting_history)
        self.assertEqual(target_state.voting_history.voting_detection_mode, "complex")
        self.assertEqual(target_state.voting_history.total_vote_attempts, 2)
        self.assertEqual(len(target_state.voting_history.vote_rounds), 1)
    
    def test_target_state_serialization(self):
        """Test TargetStateStructure serialization with voting history."""
        # Create complete structure
        vote_round = VoteRoundDetails(
            round_number=1,
            vote_type="formal_vote",
            participant_votes=[
                {
                    "participant_name": "Test_Agent",
                    "raw_response": "I choose maximizing floor",
                    "assessed_choice": "Maximizing floor income",
                    "constraint_amount": None,
                    "vote_timestamp": "2024-08-26T15:00:00.000000",
                    "parsing_success": True
                }
            ],
            consensus_reached=True,
            agreed_principle="Maximizing floor income",
            vote_counts={"Maximizing floor income": 1}
        )
        
        voting_history = VotingHistoryLog(
            voting_detection_mode="simple",
            total_vote_attempts=1,
            successful_votes=1,
            vote_rounds=[vote_round]
        )
        
        general_info = GeneralExperimentInfo(
            consensus_reached=True,
            max_rounds_phase_2=3,
            rounds_conducted_phase_2=1,
            public_conversation_phase_2="Test conversation",
            final_vote_results={"Test_Agent": "Maximizing floor income"},
            config_file_used="test_config.yaml"
        )
        
        target_state = TargetStateStructure(
            general_information=general_info,
            agents=[],
            voting_history=voting_history
        )
        
        # Test serialization
        result_dict = target_state.to_dict()
        
        # Verify structure
        self.assertIn('voting_history', result_dict)
        self.assertIn('general_information', result_dict)
        self.assertIn('agents', result_dict)
        
        # Verify voting history details
        vh = result_dict['voting_history']
        self.assertEqual(vh['voting_detection_mode'], "simple")
        self.assertEqual(vh['total_vote_attempts'], 1)
        self.assertEqual(vh['successful_votes'], 1)
        self.assertEqual(len(vh['vote_rounds']), 1)
        
        # Verify vote round details
        first_round = vh['vote_rounds'][0]
        self.assertEqual(first_round['round_number'], 1)
        self.assertEqual(first_round['vote_type'], "formal_vote")
        self.assertTrue(first_round['consensus_reached'])
        self.assertEqual(first_round['agreed_principle'], "Maximizing floor income")
        self.assertEqual(len(first_round['participant_votes']), 1)
        
        # Verify participant vote details
        participant_vote = first_round['participant_votes'][0]
        self.assertEqual(participant_vote['participant_name'], "Test_Agent")
        self.assertEqual(participant_vote['assessed_choice'], "Maximizing floor income")
        self.assertTrue(participant_vote['parsing_success'])


class TestAgentCentricLoggerVotingHistory(unittest.TestCase):
    """Test cases for AgentCentricLogger voting history methods."""
    
    def setUp(self):
        """Set up test logger."""
        self.logger = AgentCentricLogger()
    
    def test_initialize_voting_history(self):
        """Test voting history initialization."""
        self.logger.initialize_voting_history("simple")
        
        self.assertIsNotNone(self.logger.voting_history)
        self.assertEqual(self.logger.voting_history.voting_detection_mode, "simple")
        self.assertEqual(self.logger.voting_history.total_vote_attempts, 0)
        self.assertEqual(self.logger.voting_history.successful_votes, 0)
        self.assertEqual(len(self.logger.voting_history.vote_rounds), 0)
    
    def test_start_vote_round(self):
        """Test starting a vote round."""
        self.logger.initialize_voting_history("complex")
        self.logger.start_vote_round(round_number=2, vote_type="formal_vote")
        
        self.assertIsNotNone(self.logger.current_vote_round)
        self.assertEqual(self.logger.current_vote_round.round_number, 2)
        self.assertEqual(self.logger.current_vote_round.vote_type, "formal_vote")
        self.assertEqual(len(self.logger.current_vote_round.participant_votes), 0)
        self.assertFalse(self.logger.current_vote_round.consensus_reached)
    
    def test_log_vote_response(self):
        """Test logging vote responses."""
        self.logger.initialize_voting_history("simple")
        self.logger.start_vote_round(round_number=1, vote_type="formal_vote")
        
        # Log first response
        self.logger.log_vote_response(
            participant_name="Agent_1",
            raw_response="I prefer maximizing average income",
            assessed_choice="Maximizing average income",
            parsing_success=True
        )
        
        # Log second response
        self.logger.log_vote_response(
            participant_name="Agent_2", 
            raw_response="I also choose average income maximization",
            assessed_choice="Maximizing average income",
            parsing_success=True,
            constraint_amount=15000
        )
        
        # Verify responses logged
        self.assertEqual(len(self.logger.current_vote_round.participant_votes), 2)
        
        # Check first response
        vote1 = self.logger.current_vote_round.participant_votes[0]
        self.assertEqual(vote1["participant_name"], "Agent_1")
        self.assertEqual(vote1["raw_response"], "I prefer maximizing average income")
        self.assertEqual(vote1["assessed_choice"], "Maximizing average income")
        self.assertTrue(vote1["parsing_success"])
        self.assertIsNone(vote1["constraint_amount"])
        
        # Check second response
        vote2 = self.logger.current_vote_round.participant_votes[1]
        self.assertEqual(vote2["participant_name"], "Agent_2")
        self.assertEqual(vote2["constraint_amount"], 15000)
    
    def test_complete_vote_round(self):
        """Test completing a vote round."""
        self.logger.initialize_voting_history("simple")
        self.logger.start_vote_round(round_number=3, vote_type="formal_vote")
        
        # Add some responses
        self.logger.log_vote_response(
            participant_name="Agent_1",
            raw_response="I choose maximizing floor",
            assessed_choice="Maximizing floor income",
            parsing_success=True
        )
        
        # Complete the round
        self.logger.complete_vote_round(
            consensus_reached=True,
            agreed_principle="Maximizing floor income",
            vote_counts={"Maximizing floor income": 1}
        )
        
        # Verify completion
        self.assertEqual(len(self.logger.voting_history.vote_rounds), 1)
        completed_round = self.logger.voting_history.vote_rounds[0]
        
        self.assertEqual(completed_round.round_number, 3)
        self.assertTrue(completed_round.consensus_reached)
        self.assertEqual(completed_round.agreed_principle, "Maximizing floor income")
        self.assertEqual(completed_round.vote_counts["Maximizing floor income"], 1)
        self.assertEqual(len(completed_round.participant_votes), 1)
        
        # Verify counts updated
        self.assertEqual(self.logger.voting_history.total_vote_attempts, 1)
        self.assertEqual(self.logger.voting_history.successful_votes, 1)
        
        # Verify current round reset
        self.assertIsNone(self.logger.current_vote_round)
    
    def test_multiple_vote_rounds(self):
        """Test handling multiple vote rounds."""
        self.logger.initialize_voting_history("complex")
        
        # First round (unsuccessful)
        self.logger.start_vote_round(round_number=1, vote_type="initial_vote")
        self.logger.log_vote_response(
            participant_name="Agent_1",
            raw_response="I'm not sure yet",
            assessed_choice=None,
            parsing_success=False
        )
        self.logger.complete_vote_round(
            consensus_reached=False,
            agreed_principle=None,
            vote_counts={}
        )
        
        # Second round (successful)
        self.logger.start_vote_round(round_number=2, vote_type="formal_vote")
        self.logger.log_vote_response(
            participant_name="Agent_1",
            raw_response="I choose maximizing average",
            assessed_choice="Maximizing average income",
            parsing_success=True
        )
        self.logger.complete_vote_round(
            consensus_reached=True,
            agreed_principle="Maximizing average income",
            vote_counts={"Maximizing average income": 1}
        )
        
        # Verify both rounds tracked
        self.assertEqual(len(self.logger.voting_history.vote_rounds), 2)
        self.assertEqual(self.logger.voting_history.total_vote_attempts, 2)
        self.assertEqual(self.logger.voting_history.successful_votes, 1)
        
        # Verify round details
        first_round = self.logger.voting_history.vote_rounds[0]
        self.assertEqual(first_round.round_number, 1)
        self.assertFalse(first_round.consensus_reached)
        
        second_round = self.logger.voting_history.vote_rounds[1]
        self.assertEqual(second_round.round_number, 2)
        self.assertTrue(second_round.consensus_reached)


if __name__ == "__main__":
    unittest.main()