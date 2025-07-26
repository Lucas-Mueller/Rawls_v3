"""
Reusable experiment setup and fixtures for integration tests.
Provides standardized test data, mock agents, and controlled experiment execution.
"""
import asyncio
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, AsyncMock

from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import ParticipantAgent, UtilityAgent
from models import (
    DistributionSet, IncomeDistribution, ExperimentResults, 
    Phase1Results, Phase2Results, ParticipantContext, ExperimentPhase,
    PrincipleRanking, RankedPrinciple, PrincipleChoice, JusticePrinciple,
    CertaintyLevel, ApplicationResult, IncomeClass, GroupDiscussionResult
)
from core.distribution_generator import DistributionGenerator


class ExperimentTestFixture:
    """Reusable experiment setup for integration tests."""
    
    @staticmethod
    def create_minimal_config(num_agents: int = 2) -> ExperimentConfiguration:
        """Create minimal viable configuration for testing."""
        agents = []
        personalities = [
            "Analytical and methodical, focused on fairness",
            "Pragmatic and results-oriented, values efficiency", 
            "Empathetic and caring, prioritizes helping others",
            "Strategic and competitive, seeks optimal outcomes"
        ]
        
        for i in range(num_agents):
            agents.append(AgentConfiguration(
                name=f"TestAgent{i+1}",
                personality=personalities[i % len(personalities)],
                model="o3-mini",
                temperature=0.7,
                memory_character_limit=50000,
                reasoning_enabled=True
            ))
        
        return ExperimentConfiguration(
            agents=agents,
            phase2_rounds=5,
            distribution_range_phase1=(0.8, 1.2),
            distribution_range_phase2=(0.9, 1.1)
        )
    
    @staticmethod
    def create_mock_agent_pool(config: ExperimentConfiguration) -> List[ParticipantAgent]:
        """Create pool of mock agents with different personalities."""
        mock_agents = []
        
        for agent_config in config.agents:
            mock_agent = Mock(spec=ParticipantAgent)
            mock_agent.name = agent_config.name
            mock_agent.config = agent_config
            mock_agent.agent = AsyncMock()
            
            # Set up mock memory update
            mock_agent.update_memory = AsyncMock(return_value="Updated memory content")
            
            mock_agents.append(mock_agent)
        
        return mock_agents
    
    @staticmethod
    def create_test_distributions(num_sets: int = 4) -> List[DistributionSet]:
        """Create deterministic distributions for testing."""
        base_distribution = IncomeDistribution(
            high=32000,
            medium_high=27000, 
            medium=24000,
            medium_low=13000,
            low=12000
        )
        
        distributions = []
        for i in range(num_sets):
            multiplier = 1.0 + (i * 0.1)  # 1.0, 1.1, 1.2, 1.3
            
            scaled_dists = []
            for j in range(4):  # 4 distributions per set
                scale_factor = multiplier * (1.0 + j * 0.05)
                scaled_dists.append(IncomeDistribution(
                    high=int(base_distribution.high * scale_factor),
                    medium_high=int(base_distribution.medium_high * scale_factor),
                    medium=int(base_distribution.medium * scale_factor),
                    medium_low=int(base_distribution.medium_low * scale_factor),
                    low=int(base_distribution.low * scale_factor)
                ))
            
            distributions.append(DistributionSet(
                distributions=scaled_dists,
                multiplier=multiplier
            ))
        
        return distributions
    
    @staticmethod
    def create_predetermined_responses() -> Dict[str, Dict[str, List[str]]]:
        """Create predetermined agent responses for controlled testing."""
        return {
            "TestAgent1": {
                "initial_ranking": ["I rank the principles as follows: 1. Maximizing the floor income (Best), 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint (Worst). Overall certainty: sure. I believe protecting the worst-off is most important."],
                "post_explanation_ranking": ["After seeing the examples, I maintain my ranking: 1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure. The examples reinforced my belief in protecting the vulnerable."],
                "principle_applications": [
                    "I choose principle a (maximizing the floor). I am sure about this choice because it helps the worst-off people the most.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice because it balances efficiency with protection.",
                    "I choose principle a (maximizing the floor). I am very sure about this choice after seeing how it protects vulnerable people.",
                    "I choose principle c (maximizing average with floor constraint) with a constraint of $16,000. I am sure about this choice as it provides good balance."
                ],
                "final_ranking": ["My final ranking remains: 1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure. My experience confirmed that protecting the worst-off should be the priority."],
                "discussion_statements": [
                    "Based on my Phase 1 experience, I strongly believe we should choose maximizing the floor income. It consistently helped the most vulnerable people.",
                    "I understand efficiency matters, but we cannot ignore those who are worst off. I propose we vote on maximizing the floor income.",
                    "I maintain that maximizing the floor income is our best choice. It's the most just approach."
                ]
            },
            "TestAgent2": {
                "initial_ranking": ["My ranking: 1. Maximizing average income (Best), 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income (Worst). Overall certainty: sure. Efficiency should be our primary concern."],
                "post_explanation_ranking": ["After the explanation: 1. Maximizing average income, 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: sure. The examples showed how average maximization creates the most total wealth."],
                "principle_applications": [
                    "I choose principle b (maximizing the average). I am sure about this choice because it creates the most total wealth for society.",
                    "I choose principle d (maximizing average with range constraint) with a constraint of $20,000. I am sure about this choice as it maintains efficiency while limiting inequality.",
                    "I choose principle b (maximizing the average). I am very sure about this choice as efficiency is paramount.",
                    "I choose principle d (maximizing average with range constraint) with a constraint of $18,000. I am sure this balances efficiency with fairness."
                ],
                "final_ranking": ["Final ranking: 1. Maximizing average income, 2. Maximizing average with range constraint, 3. Maximizing average with floor constraint, 4. Maximizing the floor income. Overall certainty: very_sure. My experience showed that efficiency creates the most benefit overall."],
                "discussion_statements": [
                    "I believe maximizing average income is best because it creates the most total wealth. We shouldn't sacrifice efficiency for the few.",
                    "While I understand the concern for the worst-off, maximizing average income benefits everyone by creating more resources overall.",
                    "I'm willing to compromise on maximizing average with a range constraint, but pure floor maximization is inefficient."
                ]
            }
        }
    
    @staticmethod
    async def run_controlled_experiment(
        config: ExperimentConfiguration,
        agent_responses: Optional[Dict[str, Dict[str, List[str]]]] = None
    ) -> ExperimentResults:
        """Run experiment with predetermined agent responses."""
        if agent_responses is None:
            agent_responses = ExperimentTestFixture.create_predetermined_responses()
        
        # Create mock experiment manager
        from core.experiment_manager import FrohlichExperimentManager
        manager = FrohlichExperimentManager(config)
        
        # Override participants with mock agents
        mock_agents = ExperimentTestFixture.create_mock_agent_pool(config)
        manager.participants = mock_agents
        
        # Set up predetermined responses
        for i, agent in enumerate(mock_agents):
            agent_name = agent.name
            if agent_name in agent_responses:
                responses = agent_responses[agent_name]
                
                # Create a response iterator
                all_responses = []
                all_responses.extend(responses.get("initial_ranking", []))
                all_responses.extend(responses.get("post_explanation_ranking", []))
                all_responses.extend(responses.get("principle_applications", []))
                all_responses.extend(responses.get("final_ranking", []))
                all_responses.extend(responses.get("discussion_statements", []))
                
                # Set up agent to return predetermined responses
                response_iter = iter(all_responses)
                
                async def mock_runner(*args, **kwargs):
                    try:
                        response = next(response_iter)
                        mock_result = Mock()
                        mock_result.final_output = response
                        return mock_result
                    except StopIteration:
                        mock_result = Mock() 
                        mock_result.final_output = "Default response"
                        return mock_result
                
                # Mock the Runner.run method for this agent
                import unittest.mock
                with unittest.mock.patch('agents.Runner.run', side_effect=mock_runner):
                    pass  # The mock will be active during experiment execution
        
        # Run the experiment
        return await manager.run_complete_experiment()
    
    @staticmethod
    def create_test_principle_choices() -> List[PrincipleChoice]:
        """Create test principle choices for validation testing."""
        return [
            PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR),
            PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_AVERAGE),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                constraint_amount=20000
            )
        ]
    
    @staticmethod
    def create_test_principle_rankings() -> List[PrincipleRanking]:
        """Create test principle rankings for validation testing."""
        return [
            PrincipleRanking(
                rankings=[
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=2),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=3),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                ],
                certainty=CertaintyLevel.VERY_SURE
            ),
            PrincipleRanking(
                rankings=[
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=2),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=4)
                ],
                certainty=CertaintyLevel.SURE
            )
        ]
    
    @staticmethod
    def create_mock_utility_agent() -> UtilityAgent:
        """Create mock utility agent with predetermined parsing results."""
        mock_utility = Mock(spec=UtilityAgent)
        
        # Set up parsing methods
        rankings = ExperimentTestFixture.create_test_principle_rankings()
        choices = ExperimentTestFixture.create_test_principle_choices()
        
        ranking_iter = iter(rankings * 10)  # Repeat rankings as needed
        choice_iter = iter(choices * 10)    # Repeat choices as needed
        
        async def mock_parse_ranking(text):
            try:
                return next(ranking_iter)
            except StopIteration:
                return rankings[0]  # Default to first ranking
        
        async def mock_parse_choice(text):
            try:
                return next(choice_iter)
            except StopIteration:
                return choices[0]  # Default to first choice
        
        mock_utility.parse_principle_ranking_enhanced = AsyncMock(side_effect=mock_parse_ranking)
        mock_utility.parse_principle_choice_enhanced = AsyncMock(side_effect=mock_parse_choice)
        mock_utility.validate_constraint_specification = AsyncMock(return_value=True)
        mock_utility.re_prompt_for_constraint = AsyncMock(return_value="Please specify constraint amount")
        
        return mock_utility
    
    @staticmethod
    def create_test_contexts(config: ExperimentConfiguration) -> List[ParticipantContext]:
        """Create test participant contexts."""
        contexts = []
        
        for agent_config in config.agents:
            context = ParticipantContext(
                name=agent_config.name,
                role_description=agent_config.personality,
                bank_balance=0.0,
                memory="",
                round_number=0,
                phase=ExperimentPhase.PHASE_1,
                memory_character_limit=agent_config.memory_character_limit
            )
            contexts.append(context)
        
        return contexts