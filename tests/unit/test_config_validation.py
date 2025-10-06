"""Configuration validation tests for optimized test configurations."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Any

import pytest

from config import ExperimentConfiguration, AgentConfiguration
from tests.support.config_factory import (
    build_minimal_test_configuration,
    build_focused_component_config,
    build_configuration_for_test_mode,
    load_base_configuration,
)
from utils.language_manager import SupportedLanguage


@pytest.mark.unit
class TestConfigValidation:
    """Validate that optimized configurations are valid and functional."""

    def test_ultra_fast_config_file_loads_successfully(self):
        """Ensure the ultra-fast config file can be loaded without errors."""
        config_path = Path("config/test_ultra_fast.yaml")
        assert config_path.exists(), f"Ultra-fast config should exist at {config_path}"

        # Load and validate the configuration
        config = ExperimentConfiguration.from_yaml(str(config_path))

        # Validate basic properties
        assert config.agents, "Ultra-fast config should define agents"
        assert len(config.agents) == 2, "Ultra-fast config should have exactly 2 agents"
        assert config.phase2_rounds == 2, "Ultra-fast config should have 2 rounds"

        # Validate speed optimizations are present
        assert config.selective_memory_updates is True
        assert config.phase2_include_internal_reasoning_in_memory is False
        assert config.include_experiment_explanation_each_turn is False

        # Validate deterministic settings
        assert config.seed == 42
        for agent in config.agents:
            assert agent.temperature == 0
            assert agent.reasoning_enabled is False
            assert agent.model == "gpt-4o-mini"
            assert agent.memory_character_limit == 5000

    def test_minimal_test_configuration_factory(self):
        """Validate that the minimal test configuration factory produces valid configs."""
        config = build_minimal_test_configuration(
            agent_count=2,
            language=SupportedLanguage.ENGLISH,
            rounds=2,
            reasoning_enabled=False,
            memory_limit=5000,
        )

        # Validate structure
        assert len(config.agents) == 2
        assert config.phase2_rounds == 2
        assert config.language == "English"

        # Validate optimizations
        assert config.randomize_speaking_order is False
        assert config.selective_memory_updates is True
        assert config.phase2_include_internal_reasoning_in_memory is False

        # Validate agent settings
        for agent in config.agents:
            assert agent.memory_character_limit == 5000
            assert agent.reasoning_enabled is False
            assert agent.temperature == 0.0
            assert agent.model == "gpt-4o-mini"

    def test_focused_component_configs_are_valid(self):
        """Validate that focused component configurations are valid for each component."""
        components = ["voting", "discussion", "memory", "parsing", "services"]

        for component in components:
            config = build_focused_component_config(
                component=component,
                agent_count=2,
                language=SupportedLanguage.ENGLISH
            )

            # Basic validation
            assert len(config.agents) == 2, f"Component config '{component}' should have 2 agents"
            assert config.phase2_rounds > 0, f"Component config '{component}' should have positive rounds"
            assert config.language == "English"

            # All agents should have valid settings
            for agent in config.agents:
                assert agent.name
                assert agent.model
                assert agent.memory_character_limit > 0
                assert isinstance(agent.reasoning_enabled, bool)

    def test_configuration_for_test_modes(self):
        """Validate that test mode configurations are valid."""
        modes = ["ultra_fast", "dev", "ci", "full"]

        for mode in modes:
            config = build_configuration_for_test_mode(
                mode=mode,
                language=SupportedLanguage.ENGLISH,
                agent_count=2
            )

            # Basic validation
            assert len(config.agents) == 2, f"Test mode '{mode}' should have 2 agents"
            assert config.phase2_rounds > 0, f"Test mode '{mode}' should have positive rounds"
            assert config.language == "English"

            # Mode-specific validations
            if mode == "ultra_fast":
                assert config.phase2_rounds == 1, "Ultra-fast mode should have 1 round"
                for agent in config.agents:
                    assert agent.memory_character_limit == 3000, "Ultra-fast should have 3000 memory limit"
            elif mode == "dev":
                assert config.phase2_rounds == 2, "Dev mode should have 2 rounds"
                for agent in config.agents:
                    assert agent.memory_character_limit == 5000, "Dev mode should have 5000 memory limit"

    def test_all_configs_have_required_fields(self):
        """Validate that all optimized configs have required fields."""
        # Test factory-generated configs
        configs_to_test = [
            build_minimal_test_configuration(),
            build_focused_component_config("voting"),
            build_configuration_for_test_mode("dev"),
        ]

        # Add file-based config
        ultra_fast_path = Path("config/test_ultra_fast.yaml")
        if ultra_fast_path.exists():
            configs_to_test.append(ExperimentConfiguration.from_yaml(str(ultra_fast_path)))

        for config in configs_to_test:
            # Required fields validation
            assert config.agents, "Config should have agents"
            assert config.phase2_rounds > 0, "Config should have positive phase2_rounds"
            assert config.language, "Config should have language"
            assert config.utility_agent_model, "Config should have utility_agent_model"

            # Agent validation
            for agent in config.agents:
                assert agent.name, "Agent should have name"
                assert agent.personality, "Agent should have personality"
                assert agent.model, "Agent should have model"
                assert agent.memory_character_limit > 0, "Agent should have positive memory limit"
                assert isinstance(agent.temperature, (int, float)), "Agent should have numeric temperature"
                assert isinstance(agent.reasoning_enabled, bool), "Agent should have boolean reasoning_enabled"

    def test_config_schema_validation(self):
        """Validate that configs conform to expected schema constraints."""
        from pydantic import ValidationError

        # Test Pydantic validation by creating config with invalid distribution ranges
        with pytest.raises(ValidationError):
            ExperimentConfiguration(
                language="English",
                agents=[
                    AgentConfiguration(
                        name="Agent1",
                        personality="Test",
                        model="gpt-4o-mini",
                        temperature=0.0,
                        memory_character_limit=5000,
                        reasoning_enabled=True,
                        language="english"
                    )
                ],
                distribution_range_phase1=(2.0, 1.0),  # Should fail - min > max
                distribution_range_phase2=(1.0, 2.0)
            )

        # Test invalid agent configuration
        with pytest.raises(ValidationError):
            AgentConfiguration(
                name="TestAgent",
                personality="Test",
                model="gpt-4o-mini",
                temperature=0.0,
                memory_character_limit=0,  # Should fail - must be gt=0
                reasoning_enabled=True,
                language="english"
            )

    def test_deterministic_config_reproducibility(self):
        """Validate that deterministic configs produce consistent results."""
        # Create two identical configs
        config1 = build_minimal_test_configuration(
            agent_count=2,
            rounds=2,
            memory_limit=5000,
            temperature=0.0
        )

        config2 = build_minimal_test_configuration(
            agent_count=2,
            rounds=2,
            memory_limit=5000,
            temperature=0.0
        )

        # They should be equivalent
        assert config1.seed == config2.seed
        assert config1.phase2_rounds == config2.phase2_rounds
        assert len(config1.agents) == len(config2.agents)

        for i, (agent1, agent2) in enumerate(zip(config1.agents, config2.agents)):
            assert agent1.name == agent2.name, f"Agent {i} name should match"
            assert agent1.temperature == agent2.temperature, f"Agent {i} temperature should match"
            assert agent1.memory_character_limit == agent2.memory_character_limit, f"Agent {i} memory limit should match"


@pytest.mark.unit
class TestConfigPerformanceMetrics:
    """Basic performance validation for optimized configurations."""

    def test_config_loading_performance(self):
        """Measure and validate config loading times."""
        ultra_fast_path = Path("config/test_ultra_fast.yaml")
        if not ultra_fast_path.exists():
            pytest.skip("Ultra-fast config not found")

        # Measure config loading time
        start_time = time.time()
        config = ExperimentConfiguration.from_yaml(str(ultra_fast_path))
        load_time = time.time() - start_time

        # Config loading should be fast (under 100ms for a simple YAML)
        assert load_time < 0.1, f"Config loading took {load_time:.3f}s, expected < 0.1s"

        # Validate it loaded correctly
        assert config.agents
        assert len(config.agents) == 2

    def test_factory_config_creation_performance(self):
        """Measure and validate factory configuration creation times."""
        start_time = time.time()

        # Create multiple configs to test performance
        configs = []
        for _ in range(10):
            config = build_minimal_test_configuration(
                agent_count=2,
                rounds=2,
                memory_limit=5000
            )
            configs.append(config)

        creation_time = time.time() - start_time

        # Factory should create configs quickly (under 50ms for 10 configs)
        assert creation_time < 0.05, f"Factory creation took {creation_time:.3f}s for 10 configs, expected < 0.05s"

        # All configs should be valid
        assert len(configs) == 10
        for config in configs:
            assert len(config.agents) == 2

    def test_optimized_vs_default_config_comparison(self):
        """Compare key metrics between optimized and default configurations."""
        # Load default config
        default_config = load_base_configuration("config/default_config.yaml")

        # Create optimized config
        optimized_config = build_minimal_test_configuration()

        # Compare key performance metrics
        assert optimized_config.phase2_rounds < default_config.phase2_rounds, \
            "Optimized config should have fewer rounds"

        optimized_memory = sum(agent.memory_character_limit for agent in optimized_config.agents)
        default_memory = sum(agent.memory_character_limit for agent in default_config.agents[:len(optimized_config.agents)])
        assert optimized_memory < default_memory, \
            "Optimized config should use less total memory"

        # Speed optimizations should be enabled
        assert optimized_config.selective_memory_updates is True
        assert optimized_config.phase2_include_internal_reasoning_in_memory is False

    def test_config_memory_footprint(self):
        """Validate that optimized configs have reasonable memory footprints."""
        config = build_minimal_test_configuration()

        # Calculate total memory allocation
        total_agent_memory = sum(agent.memory_character_limit for agent in config.agents)

        # Should be reasonable for fast testing (under 20k total)
        assert total_agent_memory <= 20000, \
            f"Total agent memory {total_agent_memory} should be <= 20000 for fast testing"

        # Each agent should have reasonable limits
        for agent in config.agents:
            assert agent.memory_character_limit >= 1000, \
                "Agent memory should be at least 1000 characters"
            assert agent.memory_character_limit <= 15000, \
                "Agent memory should not exceed 15000 characters for fast testing"