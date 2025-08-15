"""
Integration tests for Original Values Mode functionality.
"""
import pytest
from config.models import ExperimentConfiguration, OriginalValuesModeConfig, AgentConfiguration
from core.distribution_generator import DistributionGenerator
from core.original_values_data import OriginalValuesData
from models.experiment_types import IncomeClassProbabilities


class TestOriginalValuesMode:
    """Integration test suite for Original Values Mode."""
    
    def test_original_values_mode_enabled_config_loading(self):
        """Test that original values mode configuration loads correctly."""
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="Test personality 1"),
                AgentConfiguration(name="TestAgent2", personality="Test personality 2")
            ],
            original_values_mode=OriginalValuesModeConfig(enabled=True)
        )
        
        assert config.original_values_mode is not None
        assert config.original_values_mode.enabled is True
    
    def test_original_values_mode_disabled_by_default(self):
        """Test that original values mode is disabled by default."""
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="Test personality 1"),
                AgentConfiguration(name="TestAgent2", personality="Test personality 2")
            ]
        )
        
        # Should be None by default
        assert config.original_values_mode is None
    
    def test_distribution_generator_original_values_integration(self):
        """Test that DistributionGenerator correctly uses original values mode."""
        # Test sample distribution retrieval (for explanations)
        sample_distribution_set = DistributionGenerator.get_sample_distribution()
        
        assert len(sample_distribution_set.distributions) == 4
        assert sample_distribution_set.multiplier == 1.0
        
        # Verify these are the exact sample distributions
        first_dist = sample_distribution_set.distributions[0]
        assert first_dist.high == 32000
        assert first_dist.medium_high == 27000
        assert first_dist.medium == 24000
        assert first_dist.medium_low == 13000
        assert first_dist.low == 12000
        
        # Test round-based distribution retrieval (for rounds 1-4)
        round1_set = DistributionGenerator.get_original_values_distribution(1)  # Should get situation A
        round2_set = DistributionGenerator.get_original_values_distribution(2)  # Should get situation B
        
        assert len(round1_set.distributions) == 4
        assert len(round2_set.distributions) == 4
        assert round1_set.multiplier == 1.0
        assert round2_set.multiplier == 1.0
    
    def test_probabilities_retrieval_integration(self):
        """Test that probabilities are correctly retrieved for different rounds."""
        # Test different rounds have different probabilities based on situation mapping
        sample_probs = DistributionGenerator.get_sample_probabilities()  # For explanations
        round1_probs = DistributionGenerator.get_original_values_probabilities(1)  # Situation A
        round3_probs = DistributionGenerator.get_original_values_probabilities(3)  # Situation C
        
        # Verify sample probabilities (5/10/50/25/10)
        assert sample_probs.medium == 0.5
        assert sample_probs.high == 0.05
        
        # Verify round 1 probabilities (situation A: 10/20/40/20/10)
        assert round1_probs.medium == 0.4
        assert round1_probs.high == 0.1
        
        # Verify round 3 probabilities (situation C: extreme inequality)
        assert round3_probs.medium > 0.5  # Should be 0.583333
        assert round3_probs.high < 0.02   # Should be 0.013333
    
    def test_round_number_validation(self):
        """Test that invalid round numbers are properly rejected."""
        with pytest.raises(ValueError, match="Original values mode only supports rounds 1-4"):
            DistributionGenerator.get_original_values_distribution(5)  # Invalid round
        
        with pytest.raises(ValueError, match="Original values mode only supports rounds 1-4"):
            DistributionGenerator.get_original_values_probabilities(0)  # Invalid round
        
        # Valid rounds should work
        valid_dist = DistributionGenerator.get_original_values_distribution(1)
        assert len(valid_dist.distributions) == 4
    
    def test_all_rounds_have_correct_structure(self):
        """Test that all rounds (1-4) have correct structure."""
        # Test round-based retrieval (situations A-D)
        for round_num in range(1, 5):
            # Test distribution retrieval
            distribution_set = DistributionGenerator.get_original_values_distribution(round_num)
            assert len(distribution_set.distributions) == 4
            assert distribution_set.multiplier == 1.0
            
            # Test probability retrieval
            probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
            assert isinstance(probabilities, IncomeClassProbabilities)
            
            # Verify probabilities sum to 1
            total = (probabilities.high + probabilities.medium_high + probabilities.medium + 
                    probabilities.medium_low + probabilities.low)
            assert abs(total - 1.0) < 1e-6
        
        # Test sample data (for explanations)
        sample_dist = DistributionGenerator.get_sample_distribution()
        sample_probs = DistributionGenerator.get_sample_probabilities()
        
        assert len(sample_dist.distributions) == 4
        assert isinstance(sample_probs, IncomeClassProbabilities)
        
        total = (sample_probs.high + sample_probs.medium_high + sample_probs.medium + 
                sample_probs.medium_low + sample_probs.low)
        assert abs(total - 1.0) < 1e-6
    
    def test_phase1_manager_integration_mock(self):
        """Test integration with Phase1Manager logic (mock test)."""
        # Create a config with original values mode enabled
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="Test personality"),
                AgentConfiguration(name="TestAgent2", personality="Test personality")
            ],
            original_values_mode=OriginalValuesModeConfig(enabled=True)
        )
        
        # Test the logic that would be used in Phase1Manager for round 1
        round_num = 1
        if config.original_values_mode and config.original_values_mode.enabled:
            distribution_set = DistributionGenerator.get_original_values_distribution(round_num)
            probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
        else:
            assert False, "Should have entered original values mode branch"
        
        # Verify the results
        assert len(distribution_set.distributions) == 4
        assert isinstance(probabilities, IncomeClassProbabilities)
        assert probabilities.medium == 0.4  # Situation A (round 1)
        assert probabilities.high == 0.1    # Situation A (round 1)
    
    def test_mode_disabled_fallback(self):
        """Test that disabled mode falls back to normal behavior."""
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="Test personality"),
                AgentConfiguration(name="TestAgent2", personality="Test personality")
            ],
            original_values_mode=OriginalValuesModeConfig(enabled=False),
            income_class_probabilities=IncomeClassProbabilities(
                high=0.2, medium_high=0.2, medium=0.2, medium_low=0.2, low=0.2
            )
        )
        
        # Test the logic that would be used in Phase1Manager
        if config.original_values_mode and config.original_values_mode.enabled:
            assert False, "Should not enter original values mode when disabled"
        else:
            # Should use global config probabilities
            probabilities = config.income_class_probabilities
        
        # Verify fallback behavior
        assert probabilities.medium == 0.2  # Equal probabilities from config
        assert probabilities.high == 0.2
    
    def test_logging_integration_mock(self):
        """Test integration with logging system (mock test)."""
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="Test personality"),
                AgentConfiguration(name="TestAgent2", personality="Test personality")
            ],
            original_values_mode=OriginalValuesModeConfig(enabled=True)
        )
        
        # Test the logic that would be used in ExperimentManager
        original_values_enabled = None
        if hasattr(config, 'original_values_mode') and config.original_values_mode:
            original_values_enabled = config.original_values_mode.enabled
        
        # Verify logging values
        assert original_values_enabled is True
    
    def test_round_to_situation_mapping(self):
        """Test that round numbers correctly map to different situations."""
        # Get distributions for different rounds
        dist_set_round1 = DistributionGenerator.get_original_values_distribution(1)  # Situation A
        dist_set_round2 = DistributionGenerator.get_original_values_distribution(2)  # Situation B
        dist_set_round3 = DistributionGenerator.get_original_values_distribution(3)  # Situation C
        dist_set_round4 = DistributionGenerator.get_original_values_distribution(4)  # Situation D
        
        # All should have 4 distributions
        assert len(dist_set_round1.distributions) == 4
        assert len(dist_set_round2.distributions) == 4
        assert len(dist_set_round3.distributions) == 4
        assert len(dist_set_round4.distributions) == 4
        
        # But they should be different (different situations)
        # Round 3 (situation C) should have extreme high income in first distribution
        assert dist_set_round3.distributions[0].high == 100000
        
        # Rounds 1 and 2 should be different from round 3
        assert dist_set_round1.distributions[0].high != dist_set_round3.distributions[0].high
        assert dist_set_round2.distributions[0].high != dist_set_round3.distributions[0].high
    
    def test_extreme_situation_characteristics(self):
        """Test that extreme situations have expected characteristics."""
        # Round 3 (Situation C) should have extreme inequality
        round3_distributions = DistributionGenerator.get_original_values_distribution(3)  # Situation C
        round3_probs = DistributionGenerator.get_original_values_probabilities(3)  # Situation C
        
        # Check for extreme high income in first distribution
        first_dist = round3_distributions.distributions[0]
        assert first_dist.high == 100000, "Round 3 (Situation C) should have $100k high income"
        
        # Check for very low high class probability
        assert round3_probs.high < 0.02, "Round 3 (Situation C) should have very low high class probability"
        assert round3_probs.medium > 0.55, "Round 3 (Situation C) should have high middle class probability"
    
    def test_data_consistency_across_methods(self):
        """Test that direct OriginalValuesData access matches DistributionGenerator methods."""
        # Test round 1 (situation A)
        round_num = 1
        
        # Get data through both paths
        direct_distributions = OriginalValuesData.get_distributions("a")  # Situation A
        direct_probabilities = OriginalValuesData.get_probabilities("a")
        
        generator_dist_set = DistributionGenerator.get_original_values_distribution(round_num)  # Round 1 -> A
        generator_probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
        
        # Verify consistency
        assert len(direct_distributions) == len(generator_dist_set.distributions)
        
        # Compare first distribution
        assert direct_distributions[0].high == generator_dist_set.distributions[0].high
        assert direct_distributions[0].low == generator_dist_set.distributions[0].low
        
        # Compare probabilities
        assert direct_probabilities.high == generator_probabilities.high
        assert direct_probabilities.medium == generator_probabilities.medium