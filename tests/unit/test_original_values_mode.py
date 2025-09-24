"""Unit coverage for Original Values Mode configuration and distributions."""
from __future__ import annotations

import pytest

from config.models import ExperimentConfiguration, OriginalValuesModeConfig, AgentConfiguration
from core.distribution_generator import DistributionGenerator
from models.experiment_types import IncomeClassProbabilities


@pytest.mark.unit
class TestOriginalValuesMode:
    """Verify Original Values Mode logic without full integration runs."""

    def test_mode_enabled_configuration(self):
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="P1"),
                AgentConfiguration(name="TestAgent2", personality="P2"),
            ],
            original_values_mode=OriginalValuesModeConfig(enabled=True),
        )
        assert config.original_values_mode is not None
        assert config.original_values_mode.enabled is True

    def test_mode_disabled_by_default(self):
        config = ExperimentConfiguration(
            language="English",
            agents=[
                AgentConfiguration(name="TestAgent1", personality="P1"),
                AgentConfiguration(name="TestAgent2", personality="P2"),
            ],
        )
        assert config.original_values_mode is None

    def test_distribution_generator_integration(self):
        sample_set = DistributionGenerator.get_sample_distribution()
        assert len(sample_set.distributions) == 4
        assert sample_set.multiplier == 1.0

        first_dist = sample_set.distributions[0]
        assert first_dist.high == 32000
        assert first_dist.medium == 24000
        assert first_dist.low == 12000

        round1_set = DistributionGenerator.get_original_values_distribution(1)
        round2_set = DistributionGenerator.get_original_values_distribution(2)
        assert len(round1_set.distributions) == 4
        assert len(round2_set.distributions) == 4
        assert round1_set.multiplier == 1.0
        assert round2_set.multiplier == 1.0

    def test_probability_tables(self):
        sample_probs = DistributionGenerator.get_sample_probabilities()
        assert pytest.approx(sample_probs.medium, rel=1e-6) == 0.5
        assert pytest.approx(sample_probs.high, rel=1e-6) == 0.05

        round1 = DistributionGenerator.get_original_values_probabilities(1)
        round3 = DistributionGenerator.get_original_values_probabilities(3)
        assert pytest.approx(round1.medium, rel=1e-6) == 0.4
        assert pytest.approx(round1.high, rel=1e-6) == 0.1
        assert round3.medium > 0.5
        assert round3.high < 0.02

    def test_round_number_validation(self):
        with pytest.raises(ValueError):
            DistributionGenerator.get_original_values_distribution(5)
        with pytest.raises(ValueError):
            DistributionGenerator.get_original_values_probabilities(0)
        valid_dist = DistributionGenerator.get_original_values_distribution(1)
        assert len(valid_dist.distributions) == 4

    def test_all_rounds_have_consistent_structure(self):
        for round_num in range(1, 5):
            dist_set = DistributionGenerator.get_original_values_distribution(round_num)
            probs = DistributionGenerator.get_original_values_probabilities(round_num)
            assert len(dist_set.distributions) == 4
            assert isinstance(probs, IncomeClassProbabilities)
            total = (
                probs.high
                + probs.medium_high
                + probs.medium
                + probs.medium_low
                + probs.low
            )
            assert pytest.approx(total, rel=1e-6) == 1.0

        sample_dist = DistributionGenerator.get_sample_distribution()
        sample_probs = DistributionGenerator.get_sample_probabilities()
        assert len(sample_dist.distributions) == 4
        assert isinstance(sample_probs, IncomeClassProbabilities)
        total = (
            sample_probs.high
            + sample_probs.medium_high
            + sample_probs.medium
            + sample_probs.medium_low
            + sample_probs.low
        )
        assert pytest.approx(total, rel=1e-6) == 1.0
