"""
Unit tests for experiment reproducibility functionality.
"""
import tempfile
from unittest.mock import patch

import pytest

from config import ExperimentConfiguration
from utils.seed_manager import SeedManager


def _make_config_data() -> dict:
    return {
        "language": "English",
        "agents": [
            {
                "name": "Agent_1",
                "personality": "Test personality A",
                "model": "gpt-4.1-mini",
                "temperature": 0.7,
                "memory_character_limit": 50000,
                "reasoning_enabled": True,
            },
            {
                "name": "Agent_2",
                "personality": "Test personality B",
                "model": "gpt-4.1-mini",
                "temperature": 0.5,
                "memory_character_limit": 50000,
                "reasoning_enabled": False,
            },
        ],
        "utility_agent_model": "gpt-4.1-mini",
        "phase2_rounds": 10,
    }


def test_set_experiment_seed_valid():
    """Test setting a valid seed."""
    SeedManager.set_experiment_seed(12345)

    import random

    first_value = random.random()
    SeedManager.set_experiment_seed(12345)
    second_value = random.random()

    assert first_value == second_value


@pytest.mark.parametrize("invalid_seed", (-1, "not_an_int", 2**31))
def test_set_experiment_seed_invalid(invalid_seed):
    """Test setting invalid seeds raises ValueError."""
    with pytest.raises(ValueError):
        SeedManager.set_experiment_seed(invalid_seed)


def test_validate_seed():
    """Test seed validation function."""
    assert SeedManager.validate_seed(0)
    assert SeedManager.validate_seed(12345)
    assert SeedManager.validate_seed(2**31 - 1)

    assert not SeedManager.validate_seed(-1)
    assert not SeedManager.validate_seed(2**31)
    assert not SeedManager.validate_seed("invalid")
    assert not SeedManager.validate_seed(3.14)


def test_generate_seed_from_config_deterministic():
    """Test that same configuration generates same seed."""
    config_data = _make_config_data()
    config1 = ExperimentConfiguration(**config_data)
    config2 = ExperimentConfiguration(**config_data)

    seed1 = SeedManager.generate_seed_from_config(config1)
    seed2 = SeedManager.generate_seed_from_config(config2)

    assert seed1 == seed2
    assert isinstance(seed1, int)
    assert 0 <= seed1 < 2**31


def test_generate_seed_from_config_different():
    """Test that different configurations generate different seeds."""
    config_data1 = _make_config_data()
    config_data2 = {**config_data1, "phase2_rounds": 20}

    config1 = ExperimentConfiguration(**config_data1)
    config2 = ExperimentConfiguration(**config_data2)

    seed1 = SeedManager.generate_seed_from_config(config1)
    seed2 = SeedManager.generate_seed_from_config(config2)

    assert seed1 != seed2


def test_get_effective_seed_explicit():
    """Test get_effective_seed with explicit seed."""
    config_data = {**_make_config_data(), "seed": 42}
    config = ExperimentConfiguration(**config_data)
    assert config.get_effective_seed() == 42


def test_get_effective_seed_generated():
    """Test get_effective_seed with generated seed."""
    config = ExperimentConfiguration(**_make_config_data())
    seed = config.get_effective_seed()

    assert isinstance(seed, int)
    assert 0 <= seed < 2**31
    assert seed == config.get_effective_seed()  # stable


def test_seed_validation_in_config():
    """Test that invalid seeds are rejected in configuration."""
    config_data = {**_make_config_data(), "seed": -1}

    with pytest.raises(Exception):
        ExperimentConfiguration(**config_data)


def test_from_yaml_with_seed():
    """Test loading configuration with seed from YAML."""
    config_yaml = """
language: "English"
seed: 12345
agents:
  - name: "Agent_1"
    personality: "Test personality A"
    model: "gpt-4.1-mini"
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true
  - name: "Agent_2"
    personality: "Test personality B"
    model: "gpt-4.1-mini"
    temperature: 0.5
    memory_character_limit: 50000
    reasoning_enabled: false
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 10
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        temp_file.write(config_yaml)
        temp_file.flush()

        config = ExperimentConfiguration.from_yaml(temp_file.name)
        assert config.seed == 12345
        assert config.get_effective_seed() == 12345


def test_from_yaml_without_seed():
    """Test loading configuration without seed from YAML."""
    config_yaml = """
language: "English"
agents:
  - name: "Agent_1"
    personality: "Test personality A"
    model: "gpt-4.1-mini"
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true
  - name: "Agent_2"
    personality: "Test personality B"
    model: "gpt-4.1-mini"
    temperature: 0.5
    memory_character_limit: 50000
    reasoning_enabled: false
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 10
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        temp_file.write(config_yaml)
        temp_file.flush()

        config = ExperimentConfiguration.from_yaml(temp_file.name)
        assert config.seed is None

        effective_seed = config.get_effective_seed()
        assert isinstance(effective_seed, int)
        assert 0 <= effective_seed < 2**31
