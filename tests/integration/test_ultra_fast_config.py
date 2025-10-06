"""Integration test for ultra-fast configuration validation."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from config import ExperimentConfiguration
from experiment_agents import create_participant_agent
from models import IncomeDistribution
from tests.support.config_factory import (
    build_minimal_test_configuration,
    build_configuration_for_test_mode,
    load_base_configuration
)


@pytest.mark.integration
class TestUltraFastConfigIntegration:
    """Integration tests validating ultra-fast configurations work end-to-end."""

    def test_ultra_fast_config_file_creates_valid_agents(self):
        """Validate that the ultra-fast config file can create working agents."""
        config_path = Path("config/test_ultra_fast.yaml")
        if not config_path.exists():
            pytest.skip("Ultra-fast config file not found")

        config = ExperimentConfiguration.from_yaml(str(config_path))

        # Ensure we have the OpenAI API key for agent creation
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for agent creation")

        # Test agent creation
        agents_created = []
        for agent_config in config.agents:
            agent = create_participant_agent(
                agent_config=agent_config,
                income_distribution=IncomeDistribution(),
                memory_character_limit=agent_config.memory_character_limit,
                experiment_config=config
            )
            agents_created.append(agent)

        # Validate agents were created successfully
        assert len(agents_created) == 2
        for agent in agents_created:
            assert agent is not None
            # Basic functionality test - agent should have a name
            assert hasattr(agent, 'name')

    def test_minimal_config_factory_creates_working_agents(self):
        """Test that factory-created minimal configs can create working agents."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for agent creation")

        config = build_minimal_test_configuration(
            agent_count=2,
            rounds=1,  # Absolute minimum for fast testing
            memory_limit=3000
        )

        # Test agent creation with factory config
        agents_created = []
        for agent_config in config.agents:
            agent = create_participant_agent(
                agent_config=agent_config,
                income_distribution=IncomeDistribution(),
                memory_character_limit=agent_config.memory_character_limit,
                experiment_config=config
            )
            agents_created.append(agent)

        assert len(agents_created) == 2
        for agent in agents_created:
            assert agent is not None

    def test_ultra_fast_mode_performance_baseline(self):
        """Validate that ultra-fast mode provides measurable performance improvements."""
        # Create ultra-fast config
        ultra_fast_config = build_configuration_for_test_mode("ultra_fast")

        # Create dev config for comparison
        dev_config = build_configuration_for_test_mode("dev")

        # Basic performance metrics comparison
        assert ultra_fast_config.phase2_rounds <= dev_config.phase2_rounds, \
            "Ultra-fast should have same or fewer rounds than dev"

        ultra_fast_memory = sum(agent.memory_character_limit for agent in ultra_fast_config.agents)
        dev_memory = sum(agent.memory_character_limit for agent in dev_config.agents)
        assert ultra_fast_memory <= dev_memory, \
            "Ultra-fast should use same or less memory than dev"

        # Validate speed optimizations are enabled
        assert ultra_fast_config.selective_memory_updates is True
        assert ultra_fast_config.phase2_include_internal_reasoning_in_memory is False

    def test_config_loading_performance_benchmark(self):
        """Benchmark configuration loading times to validate performance improvements."""
        config_files_to_test = []

        # Add ultra-fast config if it exists
        ultra_fast_path = Path("config/test_ultra_fast.yaml")
        if ultra_fast_path.exists():
            config_files_to_test.append(("ultra_fast_file", str(ultra_fast_path)))

        # Add default config for comparison
        default_path = Path("config/default_config.yaml")
        if default_path.exists():
            config_files_to_test.append(("default_file", str(default_path)))

        if not config_files_to_test:
            pytest.skip("No config files found for performance testing")

        loading_times = {}

        for config_name, config_path in config_files_to_test:
            start_time = time.time()
            config = ExperimentConfiguration.from_yaml(config_path)
            load_time = time.time() - start_time
            loading_times[config_name] = load_time

            # Validate config loaded successfully
            assert config.agents
            assert len(config.agents) > 0

            # All loading should be fast (under 1 second)
            assert load_time < 1.0, f"Config {config_name} loading took {load_time:.3f}s, expected < 1.0s"

        # If we have both configs, ultra-fast should load at least as quickly as default
        if "ultra_fast_file" in loading_times and "default_file" in loading_times:
            ultra_time = loading_times["ultra_fast_file"]
            default_time = loading_times["default_file"]
            # Both should be fast, but ultra-fast shouldn't be significantly slower
            assert ultra_time <= default_time * 2, \
                f"Ultra-fast loading ({ultra_time:.3f}s) should not be significantly slower than default ({default_time:.3f}s)"

    def test_factory_config_creation_performance(self):
        """Benchmark factory configuration creation times."""
        start_time = time.time()

        # Create multiple configs to test sustained performance
        configs_created = []
        for i in range(5):
            config = build_minimal_test_configuration(
                agent_count=2,
                rounds=1,
                memory_limit=3000
            )
            configs_created.append(config)

        creation_time = time.time() - start_time

        # Factory should be fast (under 100ms for 5 configs)
        assert creation_time < 0.1, f"Factory creation took {creation_time:.3f}s for 5 configs, expected < 0.1s"

        # Validate all configs are valid
        assert len(configs_created) == 5
        for config in configs_created:
            assert len(config.agents) == 2
            assert config.phase2_rounds == 1

    def test_configuration_determinism(self):
        """Validate that deterministic configurations produce consistent results."""
        # Create two identical deterministic configs
        config1 = build_minimal_test_configuration(
            agent_count=2,
            rounds=1,
            memory_limit=5000,
            temperature=0.0
        )

        config2 = build_minimal_test_configuration(
            agent_count=2,
            rounds=1,
            memory_limit=5000,
            temperature=0.0
        )

        # They should have identical critical properties
        assert config1.seed == config2.seed
        assert config1.phase2_rounds == config2.phase2_rounds

        for i, (agent1, agent2) in enumerate(zip(config1.agents, config2.agents)):
            assert agent1.temperature == agent2.temperature, f"Agent {i} temperature mismatch"
            assert agent1.memory_character_limit == agent2.memory_character_limit, f"Agent {i} memory mismatch"
            assert agent1.reasoning_enabled == agent2.reasoning_enabled, f"Agent {i} reasoning mismatch"

    def test_config_serialization_round_trip(self):
        """Test that optimized configs can be serialized and deserialized correctly."""
        original_config = build_minimal_test_configuration(
            agent_count=2,
            rounds=2,
            memory_limit=5000
        )

        # Serialize to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_path = temp_file.name
            original_config.to_yaml(temp_path)

        try:
            # Deserialize from file
            reloaded_config = ExperimentConfiguration.from_yaml(temp_path)

            # Validate key properties are preserved
            assert len(reloaded_config.agents) == len(original_config.agents)
            assert reloaded_config.phase2_rounds == original_config.phase2_rounds
            assert reloaded_config.seed == original_config.seed

            for i, (orig_agent, reloaded_agent) in enumerate(zip(original_config.agents, reloaded_config.agents)):
                assert orig_agent.name == reloaded_agent.name, f"Agent {i} name mismatch after round-trip"
                assert orig_agent.temperature == reloaded_agent.temperature, f"Agent {i} temperature mismatch"
                assert orig_agent.memory_character_limit == reloaded_agent.memory_character_limit, f"Agent {i} memory mismatch"

        finally:
            # Clean up temp file
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    @pytest.mark.skip(reason="Requires API calls and is more expensive - enable for thorough validation")
    def test_ultra_fast_config_end_to_end_functionality(self):
        """End-to-end test that ultra-fast config can run a minimal experiment."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for end-to-end test")

        config = build_minimal_test_configuration(
            agent_count=2,
            rounds=1,  # Absolute minimum
            memory_limit=3000,
            reasoning_enabled=False  # Critical for speed
        )

        # This would require importing and running the full experiment manager
        # Skipped by default as it's expensive, but validates complete workflow
        pytest.skip("End-to-end test requires full experiment execution - manually enable when needed")