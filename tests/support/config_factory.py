"""Factories for constructing experiment configurations tailored for tests."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import AgentConfiguration, ExperimentConfiguration
from utils.language_manager import SupportedLanguage


def load_base_configuration(path: str | Path = "config/default_config.yaml") -> ExperimentConfiguration:
    """Load an experiment configuration from YAML for use in tests."""
    return ExperimentConfiguration.from_yaml(str(path))


def build_agent_configuration(
    name: str,
    personality: str,
    model: str,
    *,
    temperature: float = 0.0,
    memory_character_limit: int = 25000,
    reasoning_enabled: bool = True,
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
) -> AgentConfiguration:
    """Create a minimal agent configuration for custom test scenarios."""
    return AgentConfiguration(
        name=name,
        personality=personality,
        model=model,
        temperature=temperature,
        memory_character_limit=memory_character_limit,
        reasoning_enabled=reasoning_enabled,
        language=language.value.lower(),
    )


def clone_config_with_language(
    config: ExperimentConfiguration,
    language: SupportedLanguage,
    *,
    agent_count: Optional[int] = None,
) -> ExperimentConfiguration:
    """Return a copy of ``config`` with language-normalised agents."""
    count = agent_count or len(config.agents)
    if count > len(config.agents):
        raise ValueError(
            f"Requested {count} agents but configuration only defines {len(config.agents)}"
        )

    updated_agents = [
        agent.model_copy(update={"language": language.value.lower()})
        for agent in config.agents[:count]
    ]

    return config.model_copy(
        update={
            "language": language.value,
            "agents": updated_agents,
        }
    )


def build_experiment_configuration(
    *,
    base_path: str | Path = "config/default_config.yaml",
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
    agent_count: int = 2,
) -> ExperimentConfiguration:
    """Load the base config and trim it to a lightweight, language-specific version."""
    config = load_base_configuration(base_path)
    return clone_config_with_language(config, language, agent_count=agent_count)
