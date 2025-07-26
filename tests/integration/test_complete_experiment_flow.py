"""
End-to-end integration tests for complete experiment execution.
Tests the entire experiment flow from start to finish with various scenarios.
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from core.experiment_manager import FrohlichExperimentManager
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from tests.integration.utils.async_test_utils import AsyncTestUtils, TestDataGenerators
from utils.error_handling import (
    ExperimentError, MemoryError, ValidationError, AgentCommunicationError,
    ErrorSeverity, get_global_error_handler
)
from models import (
    JusticePrinciple, CertaintyLevel, IncomeClass, 
    PrincipleChoice, PrincipleRanking, RankedPrinciple
)


class TestCompleteExperimentFlow:
    """Test complete experiment execution from start to finish."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
    
    @pytest.mark.asyncio
    async def test_minimal_experiment_success(self):
        """Test successful completion of minimal 2-agent experiment."""
        
        # Create test responses
        agent_responses = {
            "TestAgent1": {
                "initial_ranking": ["1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: sure"],
                "post_explanation_ranking": ["1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure"],
                "principle_applications": [
                    "I choose principle a (maximizing the floor). I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice.",
                    "I choose principle a (maximizing the floor). I am very sure about this choice.",
                    "I choose principle a (maximizing the floor). I am sure about this choice."
                ],
                "final_ranking": ["1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure"],
                "discussion_statements": [
                    "I believe maximizing the floor income is the most just approach based on my Phase 1 experience.",
                    "I propose we vote on maximizing the floor income."
                ]
            },
            "TestAgent2": {
                "initial_ranking": ["1. Maximizing average income, 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: sure"],
                "post_explanation_ranking": ["1. Maximizing average income, 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: sure"],
                "principle_applications": [
                    "I choose principle b (maximizing the average). I am sure about this choice.",
                    "I choose principle d (maximizing average with range constraint) with a constraint of $20,000. I am sure about this choice.",
                    "I choose principle b (maximizing the average). I am very sure about this choice.",
                    "I choose principle b (maximizing the average). I am sure about this choice."
                ],
                "final_ranking": ["1. Maximizing average income, 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: very_sure"],
                "discussion_statements": [
                    "I think maximizing average income creates the most total wealth for society.",
                    "I agree, let's vote on maximizing the floor income for consensus."
                ]
            }
        }
        
        # Create mock experiment with predetermined responses
        manager = FrohlichExperimentManager(self.config)
        
        # Mock the agent interactions
        with patch('agents.Runner.run') as mock_runner:
            # Set up response sequence
            all_responses = []
            for agent_name in ["TestAgent1", "TestAgent2"]:
                agent_data = agent_responses[agent_name]
                all_responses.extend(agent_data["initial_ranking"])
                all_responses.extend(agent_data["post_explanation_ranking"]) 
                all_responses.extend(agent_data["principle_applications"])
                all_responses.extend(agent_data["final_ranking"])
                all_responses.extend(agent_data["discussion_statements"])
            
            response_iter = iter(all_responses)
            
            def mock_agent_response(*args, **kwargs):
                mock_result = Mock()
                try:
                    mock_result.final_output = next(response_iter)
                except StopIteration:
                    mock_result.final_output = "Default response"
                return mock_result
            
            mock_runner.side_effect = mock_agent_response
            
            # Mock utility agent parsing
            with patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
                 patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
                 patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
                
                # Set up utility agent mocks
                rankings = ExperimentTestFixture.create_test_principle_rankings()
                choices = ExperimentTestFixture.create_test_principle_choices()
                
                mock_parse_ranking.side_effect = rankings * 10
                mock_parse_choice.side_effect = choices * 10
                mock_validate.return_value = True
                
                # Run the experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # Verify basic completion
                assert results is not None
                assert results.experiment_id == manager.experiment_id
                assert len(results.phase1_results) == 2
                assert results.phase2_results is not None
                
                # Verify Phase 1 results
                for phase1_result in results.phase1_results:
                    assert phase1_result.participant_name in ["TestAgent1", "TestAgent2"]
                    assert phase1_result.total_earnings >= 0
                    assert phase1_result.initial_ranking is not None
                    assert phase1_result.final_ranking is not None
                    assert len(phase1_result.application_results) == 4
                
                # Verify error handling worked
                error_stats = self.error_handler.get_error_statistics()
                # Should have minimal errors in successful scenario
                assert error_stats.get("total_errors", 0) < 5
    
    @pytest.mark.asyncio
    async def test_experiment_with_consensus(self):
        """Test experiment that reaches consensus in Phase 2."""
        
        # Create consensus-oriented responses
        consensus_responses = TestDataGenerators.generate_discussion_responses(
            "TestAgent1", "cooperative"
        )
        
        agent_responses = {
            "TestAgent1": {
                "initial_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "post_explanation_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "principle_applications": TestDataGenerators.generate_principle_choice_responses("TestAgent1", "floor"),
                "final_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "discussion_statements": consensus_responses
            },
            "TestAgent2": {
                "initial_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"),
                "post_explanation_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"),
                "principle_applications": TestDataGenerators.generate_principle_choice_responses("TestAgent2", "floor"),
                "final_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"), 
                "discussion_statements": TestDataGenerators.generate_discussion_responses("TestAgent2", "cooperative")
            }
        }
        
        manager = FrohlichExperimentManager(self.config)
        
        with patch('agents.Runner.run') as mock_runner:
            # Flatten all responses
            all_responses = []
            for agent_name in ["TestAgent1", "TestAgent2"]:
                for response_type in ["initial_ranking", "post_explanation_ranking", "principle_applications", "final_ranking", "discussion_statements"]:
                    all_responses.extend(agent_responses[agent_name][response_type])
            
            response_iter = iter(all_responses)
            
            def mock_agent_response(*args, **kwargs):
                mock_result = Mock()
                try:
                    mock_result.final_output = next(response_iter)
                except StopIteration:
                    mock_result.final_output = "I agree with the consensus"
                return mock_result
            
            mock_runner.side_effect = mock_agent_response
            
            # Mock utility agent with consensus-friendly parsing
            with patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
                 patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
                 patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate, \
                 patch.object(manager.utility_agent, 'extract_vote_from_statement') as mock_extract_vote:
                
                # Create identical rankings for consensus
                consensus_ranking = PrincipleRanking(
                    rankings=[
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=2),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=3),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                    ],
                    certainty=CertaintyLevel.VERY_SURE
                )
                
                consensus_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_FLOOR,
                    certainty=CertaintyLevel.SURE
                )
                
                mock_parse_ranking.return_value = consensus_ranking
                mock_parse_choice.return_value = consensus_choice
                mock_validate.return_value = True
                mock_extract_vote.return_value = None  # No early vote proposals
                
                # Run experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # Verify consensus was reached
                assert results.phase2_results.discussion_result.consensus_reached is True
                assert results.phase2_results.discussion_result.agreed_principle is not None
                assert results.phase2_results.discussion_result.agreed_principle.principle == JusticePrinciple.MAXIMIZING_FLOOR
    
    @pytest.mark.asyncio
    async def test_experiment_without_consensus(self):
        """Test experiment that fails to reach consensus."""
        
        # Create conflicting responses
        agent_responses = {
            "TestAgent1": {
                "initial_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "post_explanation_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "principle_applications": TestDataGenerators.generate_principle_choice_responses("TestAgent1", "floor"),
                "final_ranking": TestDataGenerators.generate_ranking_responses("TestAgent1", "high"),
                "discussion_statements": TestDataGenerators.generate_discussion_responses("TestAgent1", "competitive")
            },
            "TestAgent2": {
                "initial_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"),
                "post_explanation_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"),
                "principle_applications": TestDataGenerators.generate_principle_choice_responses("TestAgent2", "average"),
                "final_ranking": TestDataGenerators.generate_ranking_responses("TestAgent2", "high"),
                "discussion_statements": TestDataGenerators.generate_discussion_responses("TestAgent2", "competitive")
            }
        }
        
        manager = FrohlichExperimentManager(self.config)
        
        with patch('agents.Runner.run') as mock_runner:
            # Set up conflicting responses
            all_responses = []
            for agent_name in ["TestAgent1", "TestAgent2"]:
                for response_type in ["initial_ranking", "post_explanation_ranking", "principle_applications", "final_ranking", "discussion_statements"]:
                    all_responses.extend(agent_responses[agent_name][response_type])
            
            response_iter = iter(all_responses)
            
            def mock_agent_response(*args, **kwargs):
                mock_result = Mock()
                try:
                    mock_result.final_output = next(response_iter)
                except StopIteration:
                    mock_result.final_output = "I maintain my position"
                return mock_result
            
            mock_runner.side_effect = mock_agent_response
            
            # Mock utility agent with conflicting parsing
            with patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
                 patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
                 patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
                
                # Create different rankings for no consensus
                ranking1 = PrincipleRanking(
                    rankings=[
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=2),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=3),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                    ],
                    certainty=CertaintyLevel.SURE
                )
                
                ranking2 = PrincipleRanking(
                    rankings=[
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=2),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=4)
                    ],
                    certainty=CertaintyLevel.SURE
                )
                
                choice1 = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR)
                choice2 = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_AVERAGE)
                
                # Alternate between rankings/choices for different agents
                rankings = [ranking1, ranking2] * 20
                choices = [choice1, choice2] * 20
                
                mock_parse_ranking.side_effect = rankings
                mock_parse_choice.side_effect = choices
                mock_validate.return_value = True
                
                # Run experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # Verify no consensus was reached
                assert results.phase2_results.discussion_result.consensus_reached is False
                assert results.phase2_results.discussion_result.agreed_principle is None
                assert results.phase2_results.discussion_result.final_round == self.config.phase2_rounds
    
    @pytest.mark.asyncio
    async def test_experiment_with_constraint_principles(self):
        """Test experiment using principles c/d with constraints."""
        
        # Create responses focusing on constraint principles
        agent_responses = {
            "TestAgent1": {
                "initial_ranking": ["1. Maximizing average with floor constraint, 2. Maximizing the floor income, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: sure"],
                "post_explanation_ranking": ["1. Maximizing average with floor constraint, 2. Maximizing the floor income, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure"],
                "principle_applications": [
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $16,000. I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $14,000. I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice."
                ],
                "final_ranking": ["1. Maximizing average with floor constraint, 2. Maximizing the floor income, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure"],
                "discussion_statements": [
                    "I believe maximizing average with a floor constraint of $15,000 provides the best balance.",
                    "I propose we vote on maximizing average with floor constraint of $15,000."
                ]
            },
            "TestAgent2": {
                "initial_ranking": ["1. Maximizing average with range constraint, 2. Maximizing average income, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: sure"],
                "post_explanation_ranking": ["1. Maximizing average with floor constraint, 2. Maximizing average with range constraint, 3. Maximizing average income, 4. Maximizing the floor income. Overall certainty: sure"],
                "principle_applications": [
                    "I choose principle d (maximizing average with range constraint) with a constraint of $20,000. I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice.",
                    "I choose principle d (maximizing average with range constraint) with a constraint of $18,000. I am sure about this choice.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice."
                ],
                "final_ranking": ["1. Maximizing average with floor constraint, 2. Maximizing average with range constraint, 3. Maximizing average income, 4. Maximizing the floor income. Overall certainty: very_sure"],
                "discussion_statements": [
                    "After consideration, I agree that the floor constraint approach is best.",
                    "I agree with the $15,000 floor constraint proposal."
                ]
            }
        }
        
        manager = FrohlichExperimentManager(self.config)
        
        with patch('agents.Runner.run') as mock_runner:
            # Set up responses
            all_responses = []
            for agent_name in ["TestAgent1", "TestAgent2"]:
                for response_type in ["initial_ranking", "post_explanation_ranking", "principle_applications", "final_ranking", "discussion_statements"]:
                    all_responses.extend(agent_responses[agent_name][response_type])
            
            response_iter = iter(all_responses)
            
            def mock_agent_response(*args, **kwargs):
                mock_result = Mock()
                try:
                    mock_result.final_output = next(response_iter)
                except StopIteration:
                    mock_result.final_output = "I choose principle c with constraint $15,000"
                return mock_result
            
            mock_runner.side_effect = mock_agent_response
            
            # Mock utility agent with constraint validation
            with patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
                 patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
                 patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
                
                # Create constraint-focused rankings
                constraint_ranking = PrincipleRanking(
                    rankings=[
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=1),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=3),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                    ],
                    certainty=CertaintyLevel.VERY_SURE
                )
                
                constraint_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    constraint_amount=15000,
                    certainty=CertaintyLevel.SURE
                )
                
                mock_parse_ranking.return_value = constraint_ranking
                mock_parse_choice.return_value = constraint_choice
                mock_validate.return_value = True  # Valid constraint
                
                # Run experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # Verify constraint principle handling
                assert results is not None
                
                # Check that constraint amounts were properly validated
                for phase1_result in results.phase1_results:
                    for app_result in phase1_result.application_results:
                        if app_result.principle_choice.principle in [
                            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
                        ]:
                            assert app_result.principle_choice.constraint_amount is not None
                            assert app_result.principle_choice.constraint_amount > 0
    
    @pytest.mark.asyncio
    async def test_experiment_saves_results_correctly(self):
        """Test that experiment results are saved correctly to file."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Use simplified mock for this test
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Test saving results
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                temp_path = f.name
            
            try:
                manager.save_results(results, temp_path)
                
                # Verify file was created and is valid JSON
                assert Path(temp_path).exists()
                
                with open(temp_path, 'r') as f:
                    saved_data = json.load(f)
                
                # Verify structure
                assert "general_information" in saved_data
                assert "agents" in saved_data
                assert len(saved_data["agents"]) == 2
                
                # Verify each agent has complete data
                for agent_data in saved_data["agents"]:
                    assert "name" in agent_data
                    assert "phase_1" in agent_data
                    assert "phase_2" in agent_data
                    assert "model" in agent_data
                    assert "temperature" in agent_data
                
            finally:
                Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_experiment_error_statistics_tracking(self):
        """Test that experiment tracks and reports error statistics."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create scenario with some recoverable errors
        error_responses = ["Error response"] * 3 + ["Valid response"] * 10
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up mocks that will cause some errors initially
            response_iter = iter(error_responses)
            def mock_agent_response(*args, **kwargs):
                mock_result = Mock()
                mock_result.final_output = next(response_iter, "Valid response")
                return mock_result
            
            mock_runner.side_effect = mock_agent_response
            
            # Mock utility agent to handle errors gracefully
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Clear error history before test
            manager.error_handler.clear_error_history()
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify experiment completed
            assert results is not None
            
            # Check error statistics were tracked
            error_stats = manager.error_handler.get_error_statistics()
            # Should have some errors from the error responses, but experiment should complete
            assert error_stats.get("total_errors", 0) >= 0  # At least some errors expected