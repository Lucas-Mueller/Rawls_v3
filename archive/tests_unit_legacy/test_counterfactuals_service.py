"""
Unit tests for CounterfactualsService.

Tests the unified counterfactuals and payoff calculation service for consistent
payoff calculations, counterfactual analysis, results formatting, and final rankings.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.services.counterfactuals_service import CounterfactualsService
from config.phase2_settings import Phase2Settings
from models.experiment_types import ParticipantContext, ExperimentPhase
from models import GroupDiscussionResult, PrincipleChoice, JusticePrinciple, PrincipleRanking, RankedPrinciple, CertaintyLevel
from experiment_agents.participant_agent import ParticipantAgent


class TestCounterfactualsServiceInitialization:
    """Test CounterfactualsService initialization and configuration."""
    
    def test_counterfactuals_service_init_with_required_dependencies(self):
        """Test CounterfactualsService initializes with required dependencies."""
        language_manager = Mock()
        settings = Phase2Settings()
        
        service = CounterfactualsService(language_manager, settings)
        
        assert service.language_manager == language_manager
        assert service.settings == settings
        assert service.seed_manager is None  # Optional
        assert service.logger is not None  # Should have default logger
    
    def test_counterfactuals_service_init_with_optional_dependencies(self):
        """Test CounterfactualsService accepts optional dependencies."""
        language_manager = Mock()
        settings = Phase2Settings()
        custom_logger = Mock()
        seed_manager = Mock()
        
        service = CounterfactualsService(language_manager, settings, custom_logger, seed_manager)
        
        assert service.logger == custom_logger
        assert service.seed_manager == seed_manager


class TestCounterfactualsServicePayoffCalculation:
    """Test payoff calculation functionality."""
    
    @pytest.fixture
    def counterfactuals_service(self):
        """Create CounterfactualsService for testing."""
        language_manager = Mock()
        settings = Phase2Settings()
        logger = Mock()
        seed_manager = Mock()
        return CounterfactualsService(language_manager, settings, logger, seed_manager)
    
    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i in range(2):
            participant = Mock(spec=ParticipantAgent)
            participant.name = f"Agent{i}"
            participants.append(participant)
        return participants
    
    @pytest.fixture
    def mock_config(self):
        """Create mock experiment configuration."""
        config = Mock()
        config.distribution_range_phase2 = Mock()
        config.income_class_probabilities = Mock()
        return config
    
    @pytest.fixture
    def mock_discussion_result_consensus(self):
        """Create mock discussion result with consensus."""
        result = Mock(spec=GroupDiscussionResult)
        result.consensus_reached = True
        
        agreed_principle = Mock(spec=PrincipleChoice)
        agreed_principle.principle = JusticePrinciple.MAXIMIZING_FLOOR
        agreed_principle.constraint_amount = 5000
        result.agreed_principle = agreed_principle
        
        return result
    
    @pytest.fixture
    def mock_discussion_result_no_consensus(self):
        """Create mock discussion result without consensus."""
        result = Mock(spec=GroupDiscussionResult)
        result.consensus_reached = False
        result.agreed_principle = None
        return result
    
    @pytest.mark.asyncio
    async def test_apply_group_principle_with_consensus(self, counterfactuals_service, mock_participants, mock_config, mock_discussion_result_consensus):
        """Test applying group principle with consensus."""
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            # Mock distribution generation
            mock_distribution_set = Mock()
            mock_dist_gen.generate_dynamic_distribution.return_value = mock_distribution_set
            
            # Mock principle application
            mock_chosen_distribution = Mock()
            mock_explanation = "Test explanation"
            mock_dist_gen.apply_principle_to_distributions.return_value = (mock_chosen_distribution, mock_explanation)
            
            # Mock payoff calculation
            from models import IncomeClass
            mock_dist_gen.calculate_payoff.return_value = (IncomeClass.HIGH, 15000.0)
            
            # Mock counterfactuals calculation
            with patch.object(counterfactuals_service, 'calculate_phase2_counterfactuals', new_callable=AsyncMock) as mock_counterfactuals:
                mock_counterfactuals.return_value = {"Agent0": {"principle1": 12000}, "Agent1": {"principle1": 13000}}
                
                payoffs, assigned_classes, alternative_earnings, distribution_set = await counterfactuals_service.apply_group_principle_and_calculate_payoffs(
                    mock_discussion_result_consensus, mock_config, mock_participants
                )
                
                # Verify results
                assert len(payoffs) == 2
                assert len(assigned_classes) == 2
                assert len(alternative_earnings) == 2
                
                assert payoffs["Agent0"] == 15000.0
                assert payoffs["Agent1"] == 15000.0
                assert assigned_classes["Agent0"] == IncomeClass.HIGH.value
                assert assigned_classes["Agent1"] == IncomeClass.HIGH.value
                
                # Verify distribution generation was called
                mock_dist_gen.generate_dynamic_distribution.assert_called_once_with(mock_config.distribution_range_phase2)
                
                # Verify principle application was called
                mock_dist_gen.apply_principle_to_distributions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_group_principle_without_consensus(self, counterfactuals_service, mock_participants, mock_config, mock_discussion_result_no_consensus):
        """Test applying random assignment without consensus."""
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            # Mock distribution generation
            mock_distribution_set = Mock()
            mock_distribution_set.distributions = [Mock(), Mock()]
            mock_dist_gen.generate_dynamic_distribution.return_value = mock_distribution_set
            
            # Mock seed manager choice
            counterfactuals_service.seed_manager.random.choice.return_value = mock_distribution_set.distributions[0]
            
            # Mock payoff calculation  
            from models import IncomeClass
            mock_dist_gen.calculate_payoff.side_effect = [(IncomeClass.MEDIUM, 10000.0), (IncomeClass.LOW, 8000.0)]
            
            # Mock counterfactuals calculation
            with patch.object(counterfactuals_service, 'calculate_phase2_counterfactuals', new_callable=AsyncMock) as mock_counterfactuals:
                mock_counterfactuals.return_value = {"Agent0": {"principle1": 9000}, "Agent1": {"principle1": 7500}}
                
                payoffs, assigned_classes, alternative_earnings, distribution_set = await counterfactuals_service.apply_group_principle_and_calculate_payoffs(
                    mock_discussion_result_no_consensus, mock_config, mock_participants
                )
                
                # Verify results
                assert len(payoffs) == 2
                assert payoffs["Agent0"] == 10000.0
                assert payoffs["Agent1"] == 8000.0
                assert assigned_classes["Agent0"] == IncomeClass.MEDIUM.value
                assert assigned_classes["Agent1"] == IncomeClass.LOW.value
                
                # Verify random selection was used
                assert counterfactuals_service.seed_manager.random.choice.call_count == 2
    
    @pytest.mark.asyncio
    async def test_apply_group_principle_error_handling(self, counterfactuals_service, mock_participants, mock_config, mock_discussion_result_consensus):
        """Test error handling in payoff calculation."""
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            # Mock exception during distribution generation
            mock_dist_gen.generate_dynamic_distribution.side_effect = Exception("Distribution generation failed")
            
            with pytest.raises(Exception, match="Distribution generation failed"):
                await counterfactuals_service.apply_group_principle_and_calculate_payoffs(
                    mock_discussion_result_consensus, mock_config, mock_participants
                )
            
            # Verify warning was logged
            assert counterfactuals_service.logger.warning.called


class TestCounterfactualsServiceCounterfactualCalculation:
    """Test counterfactual calculation functionality."""
    
    @pytest.fixture
    def counterfactuals_service(self):
        """Create CounterfactualsService for testing."""
        language_manager = Mock()
        settings = Phase2Settings()
        logger = Mock()
        return CounterfactualsService(language_manager, settings, logger)
    
    @pytest.mark.asyncio
    async def test_calculate_phase2_counterfactuals_basic(self, counterfactuals_service):
        """Test basic counterfactuals calculation."""
        mock_distribution_set = Mock()
        assigned_classes = {"Agent0": "high", "Agent1": "medium"}
        
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            mock_alternative_earnings = {
                "maximizing_floor": 10000.0,
                "maximizing_average": 12000.0,
                "maximizing_average_with_floor": 11000.0,
                "maximizing_average_with_range": 11500.0
            }
            mock_dist_gen.calculate_alternative_earnings_by_principle_fixed_class.return_value = mock_alternative_earnings
            
            result = await counterfactuals_service.calculate_phase2_counterfactuals(
                mock_distribution_set, assigned_classes
            )
            
            # Verify results
            assert len(result) == 2
            assert "Agent0" in result
            assert "Agent1" in result
            assert result["Agent0"] == mock_alternative_earnings
            assert result["Agent1"] == mock_alternative_earnings
            
            # Verify distribution generator was called for each participant
            assert mock_dist_gen.calculate_alternative_earnings_by_principle_fixed_class.call_count == 2
    
    @pytest.mark.asyncio
    async def test_calculate_phase2_counterfactuals_with_enum_format(self, counterfactuals_service):
        """Test counterfactuals calculation with enum string format."""
        mock_distribution_set = Mock()
        assigned_classes = {"Agent0": "IncomeClass.high", "Agent1": "IncomeClass.medium"}
        
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            mock_alternative_earnings = {"principle1": 10000.0}
            mock_dist_gen.calculate_alternative_earnings_by_principle_fixed_class.return_value = mock_alternative_earnings
            
            result = await counterfactuals_service.calculate_phase2_counterfactuals(
                mock_distribution_set, assigned_classes
            )
            
            # Verify results
            assert len(result) == 2
            assert result["Agent0"] == mock_alternative_earnings
            assert result["Agent1"] == mock_alternative_earnings
    
    @pytest.mark.asyncio
    async def test_calculate_phase2_counterfactuals_error_handling(self, counterfactuals_service):
        """Test error handling in counterfactuals calculation."""
        mock_distribution_set = Mock()
        assigned_classes = {"Agent0": "invalid_class"}
        
        with pytest.raises(Exception):
            await counterfactuals_service.calculate_phase2_counterfactuals(
                mock_distribution_set, assigned_classes
            )
        
        # Verify warning was logged
        assert counterfactuals_service.logger.warning.called


class TestCounterfactualsServiceDetailedResults:
    """Test detailed results formatting functionality."""
    
    @pytest.fixture
    def counterfactuals_service(self):
        """Create CounterfactualsService with mocked language manager."""
        language_manager = Mock()
        # Mock language manager responses
        language_manager.get.side_effect = lambda key, **kwargs: {
            'results.phase2_header': 'Phase 2 Results',
            'common.income_classes.high': 'High Income',
            'common.income_classes.medium': 'Medium Income',
            'common.income_classes.low': 'Low Income',
            'results.assigned_income_class': 'Assigned to {class_name} income class',
            'voting_results.consensus_reached': 'Consensus reached on {principle_name}',
            'phase2_no_consensus': 'No consensus reached',
            'results.counterfactuals_header': 'Alternative earnings under each principle',
            'principles.maximizing_floor': 'Maximizing Floor Income',
            'principles.maximizing_average': 'Maximizing Average Income',
            'principles.maximizing_average_with_floor': 'Maximizing Average with Floor',
            'principles.maximizing_average_with_range': 'Maximizing Average with Range',
            'common.principle_names.maximizing_floor': 'Maximizing Floor Income',
            'common.principle_names.maximizing_average': 'Maximizing Average Income',
            'common.principle_names.maximizing_average_with_floor': 'Maximizing Average with Floor',
            'common.principle_names.maximizing_average_with_range': 'Maximizing Average with Range'
        }.get(key, f"MISSING:{key}").format(**kwargs)
        
        settings = Phase2Settings()
        logger = Mock()
        return CounterfactualsService(language_manager, settings, logger)
    
    @pytest.fixture
    def mock_consensus_result(self):
        """Create mock consensus result."""
        result = Mock(spec=GroupDiscussionResult)
        result.consensus_reached = True
        
        agreed_principle = Mock(spec=PrincipleChoice)  
        agreed_principle.principle = Mock()
        agreed_principle.principle.value = "maximizing_floor"  # Use slug format
        result.agreed_principle = agreed_principle
        
        return result
    
    @pytest.fixture
    def mock_no_consensus_result(self):
        """Create mock no consensus result."""
        result = Mock(spec=GroupDiscussionResult)
        result.consensus_reached = False
        result.agreed_principle = None
        return result
    
    @pytest.mark.asyncio
    async def test_build_detailed_results_with_consensus(self, counterfactuals_service, mock_consensus_result):
        """Test building detailed results with consensus."""
        alternative_earnings = {
            'maximizing_floor': 10000.0,
            'maximizing_average': 12000.0,
            'maximizing_average_with_floor': 11000.0,
            'maximizing_average_with_range': 11500.0
        }
        
        # Create a mock distribution_set that is iterable
        mock_distribution_set = Mock()
        mock_distribution_set.distributions = [Mock(), Mock()]  # Make it iterable
        
        # Mock the comprehensive earnings display to avoid Mock comparison issues
        with patch.object(counterfactuals_service, '_build_comprehensive_earnings_display') as mock_comprehensive:
            mock_comprehensive.return_value = "Alternative earnings under each principle:\n- Maximizing Floor Income: $10000.00\n- Maximizing Average Income: $12000.00"
        
            result = await counterfactuals_service.build_detailed_results(
                participant_name="Alice",
                final_earnings=15000.0,
                assigned_class="high",
                alternative_earnings=alternative_earnings,
                consensus_result=mock_consensus_result,
                distribution_set=mock_distribution_set,
                lang_manager=counterfactuals_service.language_manager
            )
        
        # Verify content structure
        assert "Phase 2 Results: $15000.00" in result
        assert "Assigned to High Income income class" in result
        assert "Consensus reached on Maximizing Floor Income." in result
        assert "Alternative earnings under each principle:" in result
        assert "- Maximizing Floor Income: $10000.00" in result
        assert "- Maximizing Average Income: $12000.00" in result
    
    @pytest.mark.asyncio
    async def test_build_detailed_results_without_consensus(self, counterfactuals_service, mock_no_consensus_result):
        """Test building detailed results without consensus."""
        alternative_earnings = {
            'maximizing_floor': 9000.0,
            'maximizing_average': 11000.0
        }
        
        # Create a mock distribution_set that is iterable  
        mock_distribution_set = Mock()
        mock_distribution_set.distributions = [Mock(), Mock()]  # Make it iterable
        
        # Mock the comprehensive earnings display to avoid Mock comparison issues
        with patch.object(counterfactuals_service, '_build_comprehensive_earnings_display') as mock_comprehensive:
            mock_comprehensive.return_value = "Alternative earnings under each principle:\n- Maximizing Floor: $9000.00\n- Maximizing Average: $11000.00"
        
            result = await counterfactuals_service.build_detailed_results(
                participant_name="Bob",
                final_earnings=12000.0,
                assigned_class="medium",
                alternative_earnings=alternative_earnings,
                consensus_result=mock_no_consensus_result,
                distribution_set=mock_distribution_set,
                lang_manager=counterfactuals_service.language_manager
            )
        
        # Verify content structure
        assert "Phase 2 Results: $12000.00" in result
        assert "No consensus reached." in result
        assert "Alternative earnings under each principle:" in result
    
    @pytest.mark.asyncio
    async def test_build_detailed_results_error_fallback(self, counterfactuals_service, mock_consensus_result):
        """Test error handling in detailed results building."""
        # Mock language manager to raise exception
        counterfactuals_service.language_manager.get.side_effect = Exception("Translation error")
        
        alternative_earnings = {"principle1": 10000.0}
        
        # Create a mock distribution_set that is iterable
        mock_distribution_set = Mock()
        mock_distribution_set.distributions = [Mock(), Mock()]  # Make it iterable
        
        result = await counterfactuals_service.build_detailed_results(
            participant_name="Charlie",
            final_earnings=13000.0,
            assigned_class="high",
            alternative_earnings=alternative_earnings,
            consensus_result=mock_consensus_result,
            distribution_set=mock_distribution_set,
            lang_manager=counterfactuals_service.language_manager
        )
        
        # Should fall back to basic format
        assert "Phase 2 results: $13000.00. Income class: high." == result
        assert counterfactuals_service.logger.warning.called


class TestCounterfactualsServiceFinalRankings:
    """Test final rankings collection functionality."""
    
    @pytest.fixture
    def counterfactuals_service(self):
        """Create CounterfactualsService for testing."""
        language_manager = Mock()
        language_manager.get.return_value = "Mocked message"
        settings = Phase2Settings()
        logger = Mock()
        return CounterfactualsService(language_manager, settings, logger)
    
    @pytest.fixture
    def mock_participants(self):
        """Create mock participant agents."""
        participants = []
        for i in range(2):
            participant = Mock(spec=ParticipantAgent)
            participant.name = f"Agent{i}"
            participants.append(participant)
        return participants
    
    @pytest.fixture
    def mock_contexts(self):
        """Create mock participant contexts."""
        contexts = []
        for i in range(2):
            context = ParticipantContext(
                name=f"Agent{i}",
                role_description="Test participant",
                bank_balance=1000.0,
                memory="Initial memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2
            )
            contexts.append(context)
        return contexts
    
    @pytest.fixture
    def mock_config(self):
        """Create mock experiment configuration."""
        config = Mock()
        config.agents = [Mock(), Mock()]  # Two agent configs
        config.phase2_enhanced_transparency = None  # Default to enhanced
        return config
    
    @pytest.mark.asyncio
    async def test_collect_final_rankings_enhanced_transparency(self, counterfactuals_service, mock_participants, mock_contexts, mock_config):
        """Test collecting final rankings with enhanced transparency."""
        discussion_result = Mock(spec=GroupDiscussionResult)
        discussion_result.consensus_reached = True
        
        payoff_results = {"Agent0": 15000.0, "Agent1": 12000.0}
        assigned_classes = {"Agent0": "high", "Agent1": "medium"}
        alternative_earnings_by_agent = {
            "Agent0": {"principle1": 14000.0},
            "Agent1": {"principle1": 11000.0}
        }
        
        utility_agent = Mock()
        
        # Mock build_detailed_results
        with patch.object(counterfactuals_service, 'build_detailed_results', new_callable=AsyncMock) as mock_build_results:
            mock_build_results.return_value = "Detailed results content"
            
            # Mock _get_final_ranking_task_streamlined  
            with patch.object(counterfactuals_service, '_get_final_ranking_task_streamlined', new_callable=AsyncMock) as mock_get_ranking:
                mock_ranking = Mock(spec=PrincipleRanking)
                mock_get_ranking.return_value = mock_ranking
                
                result = await counterfactuals_service.collect_final_rankings_streamlined(
                    contexts=mock_contexts,
                    participants=mock_participants,
                    utility_agent=utility_agent,
                    payoff_results=payoff_results,
                    assigned_classes=assigned_classes
                )
                
                # Verify results
                assert len(result) == 2
                assert "Agent0" in result
                assert "Agent1" in result
                assert result["Agent0"] is not None
                assert result["Agent1"] is not None
                
                # Verify detailed results were NOT built (streamlined method doesn't build them)
                assert mock_build_results.call_count == 0
    
    @pytest.mark.asyncio
    async def test_collect_final_rankings_basic_transparency(self, counterfactuals_service, mock_participants, mock_contexts, mock_config):
        """Test collecting final rankings with basic transparency."""
        # Configure for basic transparency
        mock_config.phase2_enhanced_transparency = Mock()
        mock_config.phase2_enhanced_transparency.enabled = False
        
        discussion_result = Mock(spec=GroupDiscussionResult)
        discussion_result.consensus_reached = False
        
        payoff_results = {"Agent0": 10000.0, "Agent1": 9000.0}
        assigned_classes = {"Agent0": "medium", "Agent1": "low"}
        alternative_earnings_by_agent = {"Agent0": {}, "Agent1": {}}
        
        utility_agent = Mock()
        
        # Mock _get_final_ranking_task_streamlined
        with patch.object(counterfactuals_service, '_get_final_ranking_task_streamlined', new_callable=AsyncMock) as mock_get_ranking:
            mock_ranking = Mock(spec=PrincipleRanking)
            mock_get_ranking.return_value = mock_ranking
            
            result = await counterfactuals_service.collect_final_rankings_streamlined(
                contexts=mock_contexts,
                participants=mock_participants,
                utility_agent=utility_agent,
                payoff_results=payoff_results,
                assigned_classes=assigned_classes
            )
            
            # Verify results
            assert len(result) == 2
            assert len(result) == 2
            assert all(ranking is not None for ranking in result.values())
    
    @pytest.mark.asyncio
    async def test_get_final_ranking_task_success(self, counterfactuals_service):
        """Test successful final ranking task."""
        participant = Mock(spec=ParticipantAgent)
        participant.name = "TestAgent"
        participant.agent = Mock()  # Add agent attribute
        participant.update_memory = AsyncMock(return_value="Updated memory")
        
        ranking_response = Mock()
        ranking_response.content = "Ranking response"
        participant.get_final_ranking = AsyncMock(return_value=ranking_response)
        
        context = Mock()
        context.bank_balance = 1000.0
        agent_config = Mock()
        agent_config.temperature = 0.7
        
        utility_agent = Mock()
        mock_ranking = Mock(spec=PrincipleRanking)
        utility_agent.parse_principle_ranking_enhanced = AsyncMock(return_value=mock_ranking)
        
        # Mock Runner.run
        from agents import Runner
        mock_runner_result = Mock()
        mock_runner_result.final_output = "Ranking response"
        
        # Mock language manager to avoid KeyError
        counterfactuals_service.language_manager.get.return_value = "Test ranking prompt"
        
        with patch.object(Runner, 'run', new_callable=AsyncMock) as mock_runner:
            mock_runner.return_value = mock_runner_result
        
            result = await counterfactuals_service._get_final_ranking_task(
                participant, context, agent_config, "Results content", utility_agent
            )
        
        # Verify result
        assert result is not None
        
        # Verify calls
        participant.update_memory.assert_called_once_with("Results content", 1000.0)
        utility_agent.parse_principle_ranking_enhanced.assert_called_once_with("Ranking response")
    
    @pytest.mark.asyncio
    async def test_get_final_ranking_task_error_fallback(self, counterfactuals_service):
        """Test error handling in final ranking task."""
        participant = Mock(spec=ParticipantAgent)
        participant.name = "TestAgent"
        participant.update_memory = AsyncMock(side_effect=Exception("Memory update failed"))
        
        context = Mock()
        agent_config = Mock()
        utility_agent = Mock()
        
        result = await counterfactuals_service._get_final_ranking_task(
            participant, context, agent_config, "Results content", utility_agent
        )
        
        # Should return default ranking
        assert isinstance(result, PrincipleRanking)
        assert len(result.rankings) == 4
        assert result.rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert result.rankings[1].principle == JusticePrinciple.MAXIMIZING_AVERAGE
        assert result.rankings[2].principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        assert result.rankings[3].principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        assert result.certainty == CertaintyLevel.NO_OPINION
        
        # Verify warning was logged
        assert counterfactuals_service.logger.warning.called


if __name__ == '__main__':
    pytest.main([__file__])