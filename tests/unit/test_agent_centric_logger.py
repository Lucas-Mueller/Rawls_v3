"""
Unit tests for the AgentCentricLogger and related logging functionality.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from utils.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from models.logging_types import (
    AgentExperimentLog, AgentPhase1Logging, AgentPhase2Logging,
    InitialRankingLog, DemonstrationRoundLog, DiscussionRoundLog,
    GeneralExperimentInfo, TargetStateStructure
)
from experiment_agents import ParticipantAgent
from config import ExperimentConfiguration, AgentConfiguration


class TestAgentCentricLogger:
    """Test the AgentCentricLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = AgentCentricLogger()
        
        # Mock participants
        self.mock_participant1 = Mock(spec=ParticipantAgent)
        self.mock_participant1.name = "Agent1"
        
        self.mock_participant2 = Mock(spec=ParticipantAgent)
        self.mock_participant2.name = "Agent2"
        
        self.participants = [self.mock_participant1, self.mock_participant2]
        
        # Mock config
        self.mock_config = Mock(spec=ExperimentConfiguration)
        self.mock_config.agents = [
            Mock(spec=AgentConfiguration, **{
                'name': 'Agent1',
                'model': 'o3-mini',
                'temperature': 0.7,
                'personality': 'cautious',
                'reasoning_enabled': True
            }),
            Mock(spec=AgentConfiguration, **{
                'name': 'Agent2',
                'model': 'o3-mini',
                'temperature': 0.9,
                'personality': 'optimistic',
                'reasoning_enabled': False
            })
        ]
    
    def test_initialize_experiment(self):
        """Test experiment initialization creates proper structure."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        
        # Check agent logs were created
        assert len(self.logger.agent_logs) == 2
        assert "Agent1" in self.logger.agent_logs
        assert "Agent2" in self.logger.agent_logs
        
        # Check agent 1 structure
        agent1_log = self.logger.agent_logs["Agent1"]
        assert agent1_log.name == "Agent1"
        assert agent1_log.model == "o3-mini"
        assert agent1_log.temperature == 0.7
        assert agent1_log.personality == "cautious"
        assert agent1_log.reasoning_enabled == True
        
        # Check phase structures exist
        assert agent1_log.phase_1 is not None
        assert agent1_log.phase_2 is not None
        assert isinstance(agent1_log.phase_1.demonstrations, list)
        assert len(agent1_log.phase_1.demonstrations) == 0  # Initially empty
    
    def test_log_initial_ranking(self):
        """Test logging initial ranking."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        
        self.logger.log_initial_ranking(
            "Agent1",
            "Ranking: A=1, B=2, C=3, D=4",
            "Very sure",
            "Initial memory state",
            0.0
        )
        
        initial_ranking = self.logger.agent_logs["Agent1"].phase_1.initial_ranking
        assert initial_ranking.principle_ranking_result == "Ranking: A=1, B=2, C=3, D=4"
        assert initial_ranking.confidence_level == "Very sure"
        assert initial_ranking.memory_coming_in_this_round == "Initial memory state"
        assert initial_ranking.bank_balance == 0.0
    
    def test_log_demonstration_round(self):
        """Test logging demonstration rounds."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        
        self.logger.log_demonstration_round(
            "Agent1",
            1,  # round_number
            "Principle A",
            "High",
            25.0,  # payoff
            "B: $20, C: $22, D: $18",
            "Memory before round 1",
            0.0,  # balance_before
            25.0   # balance_after
        )
        
        demonstrations = self.logger.agent_logs["Agent1"].phase_1.demonstrations
        assert len(demonstrations) == 1
        
        demo = demonstrations[0]
        assert demo.number_demonstration_round == 1
        assert demo.choice_principal == "Principle A"
        assert demo.class_put_in == "High"
        assert demo.payoff_received == 25.0
        assert demo.payoff_if_other_principles == "B: $20, C: $22, D: $18"
        assert demo.memory_coming_in_this_round == "Memory before round 1"
        assert demo.bank_balance == 0.0
        assert demo.bank_balance_after_round == 25.0
    
    def test_log_discussion_round(self):
        """Test logging discussion rounds."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        
        self.logger.log_discussion_round(
            "Agent1",
            1,  # round_number
            1,  # speaking_order
            "I think we should choose A",
            "I propose principle A",
            "Yes",  # initiate_vote
            "Principle A",
            "Memory before discussion",
            100.0
        )
        
        rounds = self.logger.agent_logs["Agent1"].phase_2.rounds
        assert len(rounds) == 1
        
        round_log = rounds[0]
        assert round_log.number_discussion_round == 1
        assert round_log.speaking_order == 1
        assert round_log.internal_reasoning == "I think we should choose A"
        assert round_log.public_message == "I propose principle A"
        assert round_log.initiate_vote == "Yes"
        assert round_log.favored_principle == "Principle A"
        assert round_log.memory_coming_in_this_round == "Memory before discussion"
        assert round_log.bank_balance == 100.0
    
    def test_set_general_information(self):
        """Test setting general experiment information."""
        self.logger.set_general_information(
            consensus_reached=True,
            consensus_principle="Principle A",
            public_conversation="Agent1: I like A\nAgent2: Me too",
            final_vote_results={"Agent1": "Principle A", "Agent2": "Principle A"},
            config_file="test_config.yaml"
        )
        
        assert self.logger.general_info is not None
        assert self.logger.general_info.consensus_reached == True
        assert self.logger.general_info.consensus_principle == "Principle A"
        assert "Agent1: I like A" in self.logger.general_info.public_conversation_phase_2
        assert self.logger.general_info.final_vote_results["Agent1"] == "Principle A"
        assert self.logger.general_info.config_file_used == "test_config.yaml"
    
    def test_generate_target_state(self):
        """Test generating target state structure."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        
        # Add some sample data
        self.logger.log_initial_ranking("Agent1", "Test ranking", "Sure", "Memory", 0.0)
        self.logger.log_demonstration_round("Agent1", 1, "A", "High", 25.0, "Alt: B=20", "Mem", 0.0, 25.0)
        
        self.logger.set_general_information(
            consensus_reached=True,
            consensus_principle="Principle A",
            public_conversation="Test conversation",
            final_vote_results={"Agent1": "A", "Agent2": "A"},
            config_file="test.yaml"
        )
        
        target_state = self.logger.generate_target_state()
        
        assert isinstance(target_state, TargetStateStructure)
        assert target_state.general_information.consensus_reached == True
        assert len(target_state.agents) == 2
        
        # Check target format conversion
        target_dict = target_state.to_dict()
        assert "general_information" in target_dict
        assert "agents" in target_dict
        assert target_dict["general_information"]["consensus_reached"] == True
    
    def test_save_to_file(self):
        """Test saving to file."""
        self.logger.initialize_experiment(self.participants, self.mock_config)
        self.logger.set_general_information(
            consensus_reached=False,
            consensus_principle=None,
            public_conversation="No consensus reached",
            final_vote_results={"Agent1": "A", "Agent2": "B"},
            config_file="test.yaml"
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.logger.save_to_file(temp_path)
            
            # Verify file was created and contains expected structure
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert "general_information" in saved_data
            assert "agents" in saved_data
            assert saved_data["general_information"]["consensus_reached"] == False
            assert len(saved_data["agents"]) == 2
            
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestMemoryStateCapture:
    """Test the MemoryStateCapture utility class."""
    
    def test_capture_pre_round_state(self):
        """Test capturing pre-round state."""
        memory, balance = MemoryStateCapture.capture_pre_round_state("test memory", 100.0)
        assert memory == "test memory"
        assert balance == 100.0
    
    def test_format_alternative_payoffs(self):
        """Test formatting alternative payoffs."""
        alt_earnings = {
            "maximizing_floor": 15.0,
            "maximizing_average": 20.0,
            "maximizing_average_floor_constraint": 18.0
        }
        
        formatted = MemoryStateCapture.format_alternative_payoffs(alt_earnings)
        assert "maximizing_floor: $15.00" in formatted
        assert "maximizing_average: $20.00" in formatted
        assert "maximizing_average_floor_constraint: $18.00" in formatted
        
        # Test empty dict
        empty_formatted = MemoryStateCapture.format_alternative_payoffs({})
        assert empty_formatted == "No alternative payoffs calculated"
    
    def test_extract_confidence_from_response(self):
        """Test extracting confidence from response text."""
        assert MemoryStateCapture.extract_confidence_from_response("I am very_sure about this") == "Very sure"
        assert MemoryStateCapture.extract_confidence_from_response("I feel sure") == "Sure"
        assert MemoryStateCapture.extract_confidence_from_response("I have no_opinion") == "No opinion"
        assert MemoryStateCapture.extract_confidence_from_response("I am very unsure") == "Very unsure"
        assert MemoryStateCapture.extract_confidence_from_response("I am unsure") == "Unsure"
        assert MemoryStateCapture.extract_confidence_from_response("Random text") == "Not specified"
    
    def test_extract_vote_intention(self):
        """Test extracting vote intention from response."""
        assert MemoryStateCapture.extract_vote_intention("I call for vote now") == "Yes"
        assert MemoryStateCapture.extract_vote_intention("Let's vote on this") == "Yes"
        assert MemoryStateCapture.extract_vote_intention("I want to initiate vote") == "Yes"
        assert MemoryStateCapture.extract_vote_intention("We should vote now") == "Yes"
        assert MemoryStateCapture.extract_vote_intention("I think we need more discussion") == "No"
        assert MemoryStateCapture.extract_vote_intention("Random statement") == "No"


class TestTargetStateFormat:
    """Test the target state format matches expected structure."""
    
    def test_agent_log_to_target_format(self):
        """Test converting agent log to target format."""
        # Create a minimal agent log with required data
        from models.logging_types import (
            AgentExperimentLog, AgentPhase1Logging, AgentPhase2Logging,
            InitialRankingLog, DetailedExplanationLog, PostExplanationRankingLog,
            FinalRankingLog, PostDiscussionLog
        )
        
        agent_log = AgentExperimentLog(
            name="Test Agent",
            model="o3-mini",
            temperature=0.7,
            personality="test",
            reasoning_enabled=True,
            phase_1=AgentPhase1Logging(
                initial_ranking=InitialRankingLog(
                    principle_ranking_result="A=1, B=2, C=3, D=4",
                    confidence_level="Sure",
                    memory_coming_in_this_round="Initial memory",
                    bank_balance=0.0
                ),
                detailed_explanation=DetailedExplanationLog(
                    response_to_demonstration="Understood principles",
                    memory_coming_in_this_round="Post-explanation memory",
                    bank_balance=0.0
                ),
                ranking_2=PostExplanationRankingLog(
                    principle_ranking_result="A=1, B=2, C=3, D=4",
                    confidence_level="Sure", 
                    memory_coming_in_this_round="Ranking 2 memory",
                    bank_balance=0.0
                ),
                demonstrations=[],
                ranking_3=FinalRankingLog(
                    principle_ranking_result="A=1, B=2, C=3, D=4",
                    confidence_level="Very sure",
                    memory_coming_in_this_round="Final memory",
                    bank_balance=100.0
                )
            ),
            phase_2=AgentPhase2Logging(
                rounds=[],
                post_group_discussion=PostDiscussionLog(
                    class_put_in="High",
                    payoff_received=30.0,
                    final_ranking="A=1, B=2, C=3, D=4",
                    confidence_level="Very sure",
                    memory_coming_in_this_round="Final discussion memory",
                    bank_balance=130.0
                )
            )
        )
        
        target_format = agent_log.to_target_format()
        
        # Verify structure matches target_state.json
        assert "name" in target_format
        assert "model" in target_format
        assert "temperature" in target_format
        assert "personality" in target_format
        assert "reasoning_enabled" in target_format
        assert "phase_1" in target_format
        assert "phase_2" in target_format
        
        # Check phase_1 structure
        phase1 = target_format["phase_1"]
        assert "initial_ranking" in phase1
        assert "detailed_explanation" in phase1
        assert "ranking_2" in phase1
        assert "demonstrations" in phase1
        assert "ranking_3" in phase1
        
        # Check phase_2 structure
        phase2 = target_format["phase_2"]
        assert "rounds" in phase2
        assert "post_group_discussion" in phase2
        
        # Check specific values
        assert target_format["name"] == "Test Agent"
        assert target_format["model"] == "o3-mini"
        assert target_format["temperature"] == 0.7
        assert phase1["initial_ranking"]["confidence_level"] == "Sure"
        assert phase2["post_group_discussion"]["payoff_received"] == 30.0


if __name__ == "__main__":
    pytest.main([__file__])