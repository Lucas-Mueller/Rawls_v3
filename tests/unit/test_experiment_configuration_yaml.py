"""Unit coverage for ExperimentConfiguration YAML load/save behaviour."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from config import ExperimentConfiguration


@pytest.mark.unit
class TestExperimentConfigurationYAML:
    """Validate YAML-based configuration loading logic."""

    def _write_temp_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(content)
        except Exception:
            os.unlink(path)
            raise
        return path

    def test_loads_expected_fields(self):
        yaml_content = """
        agents:
          - name: "TestAgent1"
            personality: "Analytical"
            model: "gpt-4o-mini"
            temperature: 0.7
            memory_character_limit: 50000
          - name: "TestAgent2"
            personality: "Pragmatic"
            model: "gpt-4o-mini"
            temperature: 0.8
            memory_character_limit: 40000

        phase2_rounds: 5
        distribution_range_phase1: [0.8, 1.5]
        distribution_range_phase2: [0.6, 1.8]
        """
        temp_path = self._write_temp_yaml(yaml_content)
        try:
            config = ExperimentConfiguration.from_yaml(temp_path)
            assert len(config.agents) == 2
            assert [agent.name for agent in config.agents] == ["TestAgent1", "TestAgent2"]
            assert config.agents[1].temperature == 0.8
            assert config.phase2_rounds == 5
            assert config.distribution_range_phase1 == (0.8, 1.5)
            assert config.distribution_range_phase2 == (0.6, 1.8)
        finally:
            os.unlink(temp_path)

    def test_duplicate_agent_names_raise_value_error(self):
        yaml_content = """
        agents:
          - name: "Agent1"
            personality: "Test personality"
            model: "gpt-4o-mini"
            temperature: 0.7
            memory_character_limit: 50000
          - name: "Agent1"
            personality: "Another personality"
            model: "gpt-4o-mini"
            temperature: 0.8
            memory_character_limit: 50000

        phase2_rounds: 5
        distribution_range_phase1: [0.8, 1.5]
        distribution_range_phase2: [0.6, 1.8]
        """
        temp_path = self._write_temp_yaml(yaml_content)
        try:
            with pytest.raises(ValueError):
                ExperimentConfiguration.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ExperimentConfiguration.from_yaml("/tmp/nonexistent_config.yaml")

    def test_round_trip_preserves_core_properties(self):
        yaml_content = """
        agents:
          - name: "TestAgent1"
            personality: "Analytical"
            model: "gpt-4o-mini"
            temperature: 0.7
            memory_character_limit: 50000
          - name: "TestAgent2"
            personality: "Pragmatic"
            model: "gpt-4o-mini"
            temperature: 0.6
            memory_character_limit: 40000

        phase2_rounds: 5
        distribution_range_phase1: [0.8, 1.5]
        """
        source_path = self._write_temp_yaml(yaml_content)
        target_fd, target_path = tempfile.mkstemp(suffix=".yaml")
        os.close(target_fd)
        try:
            config = ExperimentConfiguration.from_yaml(source_path)
            config.to_yaml(target_path)
            reloaded = ExperimentConfiguration.from_yaml(target_path)
            assert [agent.name for agent in reloaded.agents] == ["TestAgent1", "TestAgent2"]
            assert reloaded.phase2_rounds == 5
            assert reloaded.distribution_range_phase1 == (0.8, 1.5)
        finally:
            os.unlink(source_path)
            os.unlink(target_path)

    def test_default_config_is_present_and_valid(self):
        default_path = Path(__file__).resolve().parents[2] / "config" / "default_config.yaml"
        assert default_path.exists(), f"Expected default config at {default_path}"
        config = ExperimentConfiguration.from_yaml(str(default_path))
        assert config.agents, "Default configuration should define agents"
        assert config.phase2_rounds > 0, "Phase 2 rounds should be positive"
        for agent in config.agents:
            assert agent.name
            assert agent.model
            assert agent.memory_character_limit > 0
