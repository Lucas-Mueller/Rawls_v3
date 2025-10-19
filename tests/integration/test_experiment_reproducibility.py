"""
Integration tests for full experiment reproducibility.
"""
from __future__ import annotations

import os
import random
import tempfile
from pathlib import Path

import pytest

from config import ExperimentConfiguration
from core.distribution_generator import DistributionGenerator
from core.experiment_manager import FrohlichExperimentManager
from utils.seed_manager import SeedManager


def _base_config_data() -> dict:
    return {
        "language": "English",
        "agents": [
            {
                "name": "Alice",
                "personality": "Test personality A",
                "model": "gpt-4.1-mini",
                "temperature": 0.0,
                "memory_character_limit": 25000,
                "reasoning_enabled": False,
            },
            {
                "name": "Bob",
                "personality": "Test personality B",
                "model": "gpt-4.1-mini",
                "temperature": 0.0,
                "memory_character_limit": 25000,
                "reasoning_enabled": False,
            },
        ],
        "utility_agent_model": "gpt-4.1-mini",
        "utility_agent_temperature": 0.0,
        "phase2_rounds": 2,
        "distribution_range_phase1": [0.8, 1.2],
        "distribution_range_phase2": [0.8, 1.2],
        "original_values_mode": {"enabled": True},
    }


def test_seed_generation_consistency():
    config1 = ExperimentConfiguration(**_base_config_data())
    config2 = ExperimentConfiguration(**_base_config_data())

    assert config1.get_effective_seed() == config2.get_effective_seed()


def test_explicit_seed_override():
    config1 = ExperimentConfiguration(**_base_config_data())
    generated_seed = config1.get_effective_seed()

    config_with_seed = {**_base_config_data(), "seed": 12345}
    config2 = ExperimentConfiguration(**config_with_seed)

    assert config2.get_effective_seed() == 12345
    assert generated_seed != config2.get_effective_seed()


def test_random_operations_seeded():
    SeedManager.set_experiment_seed(42)
    first = [random.random() for _ in range(10)]

    SeedManager.set_experiment_seed(42)
    second = [random.random() for _ in range(10)]

    SeedManager.set_experiment_seed(123)
    third = [random.random() for _ in range(10)]

    assert first == second
    assert first != third


def test_distribution_generator_reproducibility():
    manager_one = SeedManager()
    manager_one.set_seed(42)
    dist_set1 = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0), random_gen=manager_one.random)

    manager_two = SeedManager()
    manager_two.set_seed(42)
    dist_set2 = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0), random_gen=manager_two.random)

    assert dist_set1.multiplier == dist_set2.multiplier
    assert len(dist_set1.distributions) == len(dist_set2.distributions)
    for first_dist, second_dist in zip(dist_set1.distributions, dist_set2.distributions):
        assert first_dist.model_dump() == second_dist.model_dump()


def test_config_yaml_roundtrip_with_seed(tmp_path: Path):
    config_with_seed = {**_base_config_data(), "seed": 54321}
    config_original = ExperimentConfiguration(**config_with_seed)

    output_path = tmp_path / "config.yaml"
    config_original.to_yaml(str(output_path))

    config_loaded = ExperimentConfiguration.from_yaml(str(output_path))
    assert config_original.get_effective_seed() == config_loaded.get_effective_seed()
    assert config_loaded.seed == 54321


def test_experiment_manager_seed_initialization():
    config = ExperimentConfiguration(**_base_config_data())
    manager = FrohlichExperimentManager(config)
    expected_seed = config.get_effective_seed()

    actual_seed = manager.seed_manager.initialize_from_config(config)
    assert actual_seed == expected_seed
    assert manager.seed_manager.current_seed == expected_seed


def test_distribution_generator_respects_seed_manager_random():
    seed_manager = SeedManager()
    seed_manager.set_seed(123)
    first = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0), random_gen=seed_manager.random)

    seed_manager.set_seed(123)
    second = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0), random_gen=seed_manager.random)

    assert first.multiplier == second.multiplier
    for dist_one, dist_two in zip(first.distributions, second.distributions):
        assert dist_one.model_dump() == dist_two.model_dump()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"),
    reason="API keys required for full experiment test",
)
async def test_full_experiment_reproducibility():
    config_with_seed = {**_base_config_data(), "seed": 99999}
    config = ExperimentConfiguration(**config_with_seed)

    manager = FrohlichExperimentManager(config)
    await manager.async_init()

    assert manager.seed_manager.current_seed == config.get_effective_seed()
