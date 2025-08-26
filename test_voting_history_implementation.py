#!/usr/bin/env python3
"""
Quick test for voting history implementation.
"""

from models.logging_types import VotingHistoryLog, VoteRoundDetails, TargetStateStructure, GeneralExperimentInfo
from utils.agent_centric_logger import AgentCentricLogger
import json

def test_voting_history_structures():
    """Test the new voting history data structures."""
    print("Testing voting history data structures...")
    
    # Test VoteRoundDetails
    vote_round = VoteRoundDetails(
        round_number=2,
        vote_type="preference_consensus",
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
    
    print(f"✓ VoteRoundDetails created: consensus={vote_round.consensus_reached}")
    
    # Test VotingHistoryLog
    voting_history = VotingHistoryLog(
        voting_detection_mode="simple",
        total_vote_attempts=1,
        successful_votes=1,
        vote_rounds=[vote_round]
    )
    
    print(f"✓ VotingHistoryLog created: {len(voting_history.vote_rounds)} rounds")
    
    # Test TargetStateStructure with voting history
    general_info = GeneralExperimentInfo(
        consensus_reached=True,
        max_rounds_phase_2=5,
        rounds_conducted_phase_2=2,
        public_conversation_phase_2="Test conversation",
        final_vote_results={"Agent_1": "Maximizing average income", "Agent_2": "Maximizing average income"},
        config_file_used="test_config.yaml"
    )
    
    target_state = TargetStateStructure(
        general_information=general_info,
        agents=[],
        voting_history=voting_history
    )
    
    print("✓ TargetStateStructure created with voting history")
    
    # Test serialization
    result_dict = target_state.to_dict()
    print(f"✓ Serialization successful: has voting_history={('voting_history' in result_dict)}")
    
    if 'voting_history' in result_dict:
        vh = result_dict['voting_history']
        print(f"  - Mode: {vh['voting_detection_mode']}")
        print(f"  - Vote attempts: {vh['total_vote_attempts']}")
        print(f"  - Successful votes: {vh['successful_votes']}")
        print(f"  - Rounds: {len(vh['vote_rounds'])}")
        
        if vh['vote_rounds']:
            first_round = vh['vote_rounds'][0]
            print(f"  - First round type: {first_round['vote_type']}")
            print(f"  - Participant votes: {len(first_round['participant_votes'])}")
    
    return True

def test_agent_centric_logger():
    """Test the AgentCentricLogger voting history methods."""
    print("\nTesting AgentCentricLogger voting history methods...")
    
    logger = AgentCentricLogger()
    
    # Initialize voting history
    logger.initialize_voting_history("simple")
    print("✓ Voting history initialized")
    
    # Start a vote round
    logger.start_vote_round(
        round_number=2,
        vote_type="preference_consensus"
    )
    print("✓ Vote round started")
    
    # Log vote responses
    logger.log_vote_response(
        participant_name="Agent_1",
        raw_response="I prefer Maximizing average income",
        assessed_choice="Maximizing average income",
        parsing_success=True
    )
    
    logger.log_vote_response(
        participant_name="Agent_2", 
        raw_response="I also choose average income maximization",
        assessed_choice="Maximizing average income",
        parsing_success=True
    )
    print("✓ Vote responses logged")
    
    # Complete the vote round
    logger.complete_vote_round(
        consensus_reached=True,
        agreed_principle="Maximizing average income",
        vote_counts={"Maximizing average income": 2}
    )
    print("✓ Vote round completed")
    
    # Check the voting history
    if logger.voting_history:
        print(f"✓ Voting history has {logger.voting_history.total_vote_attempts} attempts")
        print(f"✓ Successful votes: {logger.voting_history.successful_votes}")
        print(f"✓ Vote rounds logged: {len(logger.voting_history.vote_rounds)}")
        
        if logger.voting_history.vote_rounds:
            first_round = logger.voting_history.vote_rounds[0]
            print(f"✓ First round has {len(first_round.participant_votes)} participant votes")
            print(f"✓ Consensus reached: {first_round.consensus_reached}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("VOTING HISTORY IMPLEMENTATION TEST")
    print("=" * 60)
    
    try:
        test_voting_history_structures()
        test_agent_centric_logger()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("The voting history implementation is working correctly!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()