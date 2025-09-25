"""Factories for constructing experiment configurations tailored for tests."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

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


def build_minimal_test_configuration(
    *,
    agent_count: int = 2,
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
    rounds: int = 2,
    reasoning_enabled: bool = False,
    memory_limit: int = 5000,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0
) -> ExperimentConfiguration:
    """Create ultra-minimal configuration for fast testing.

    This configuration is optimized for maximum speed:
    - Minimal rounds (2 instead of 10)
    - Reasoning disabled for speed
    - Reduced memory limits
    - Fastest available model
    - Temperature 0 for deterministic responses
    - No randomization in distributions
    """
    # Create minimal agents
    agents = []
    for i in range(agent_count):
        name = ["Alice", "Bob", "Charlie", "Diana", "Eve"][i % 5]
        agents.append(
            AgentConfiguration(
                name=name,
                personality="Test agent",
                model=model,
                temperature=temperature,
                memory_character_limit=memory_limit,
                reasoning_enabled=reasoning_enabled,
                language=language.value.lower(),
            )
        )

    return ExperimentConfiguration(
        language=language.value,
        agents=agents,
        utility_agent_model=model,
        utility_agent_temperature=temperature,
        phase2_rounds=rounds,
        randomize_speaking_order=False,  # Disable for deterministic testing
        speaking_order_strategy="fixed",
        distribution_range_phase1=(1.0, 1.01),  # Minimal randomization for validation
        distribution_range_phase2=(1.0, 1.01),  # Minimal randomization for validation
        memory_guidance_style="structured",
        include_experiment_explanation_each_turn=False,
        phase2_include_internal_reasoning_in_memory=False,
        selective_memory_updates=True,
        memory_update_threshold="minimal",
        seed=42  # Fixed seed for reproducibility
    )


def build_focused_component_config(
    component: str,
    *,
    agent_count: int = 2,
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
    **overrides
) -> ExperimentConfiguration:
    """Create configuration optimized for specific component testing.

    Args:
        component: Component to optimize for ("voting", "discussion", "memory", "parsing", "services")
        agent_count: Number of agents to create
        language: Language for the test
        **overrides: Additional configuration overrides

    Returns:
        Configuration optimized for the specified component
    """
    # Start with minimal config
    config = build_minimal_test_configuration(
        agent_count=agent_count,
        language=language
    )

    # Component-specific optimizations
    component_configs: Dict[str, Dict[str, Any]] = {
        "voting": {
            "phase2_rounds": 3,  # Need a few rounds for voting scenarios
            "memory_limit": 8000,  # Slightly more memory for voting context
        },
        "discussion": {
            "phase2_rounds": 4,  # More rounds for discussion flow
            "memory_limit": 10000,  # More memory for discussion history
            "include_experiment_explanation_each_turn": True,  # Test explanation logic
        },
        "memory": {
            "memory_limit": 15000,  # Higher memory for memory testing
            "memory_guidance_style": "narrative",  # Test narrative style
            "phase2_include_internal_reasoning_in_memory": True,  # Test reasoning inclusion
        },
        "parsing": {
            "rounds": 1,  # Minimal rounds for parsing tests
            "memory_limit": 3000,  # Very minimal memory
            "temperature": 0.1,  # Slight variation for parsing edge cases
        },
        "services": {
            "phase2_rounds": 3,  # Balanced for service interaction testing
            "randomize_speaking_order": True,  # Test randomization in services
            "speaking_order_strategy": "random",
        }
    }

    # Apply component-specific settings
    if component in component_configs:
        component_overrides = component_configs[component]

        # Handle special cases for agent-level settings
        if "memory_limit" in component_overrides:
            memory_limit = component_overrides.pop("memory_limit")
            # Update all agents with new memory limit
            updated_agents = []
            for agent in config.agents:
                updated_agents.append(
                    agent.model_copy(update={"memory_character_limit": memory_limit})
                )
            config = config.model_copy(update={"agents": updated_agents})

        if "temperature" in component_overrides:
            temperature = component_overrides.pop("temperature")
            # Update all agents and utility agent with new temperature
            updated_agents = []
            for agent in config.agents:
                updated_agents.append(
                    agent.model_copy(update={"temperature": temperature})
                )
            config = config.model_copy(update={
                "agents": updated_agents,
                "utility_agent_temperature": temperature
            })

        # Apply remaining configuration overrides
        config = config.model_copy(update=component_overrides)

    # Apply any additional overrides passed as parameters
    if overrides:
        config = config.model_copy(update=overrides)

    return config


def get_test_config_override() -> Optional[str]:
    """Get configuration override from environment variable.

    Returns:
        Path to configuration file if TEST_CONFIG_OVERRIDE is set, None otherwise
    """
    override = os.getenv("TEST_CONFIG_OVERRIDE")
    if override and override.strip():
        return override.strip()
    return None


def build_configuration_for_test_mode(
    mode: str = "dev",
    *,
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
    agent_count: int = 2
) -> ExperimentConfiguration:
    """Build configuration based on test execution mode.

    Args:
        mode: Test execution mode ("ultra_fast", "dev", "ci", "full")
        language: Language for the test
        agent_count: Number of agents to create

    Returns:
        Configuration optimized for the specified mode
    """
    # Check for environment override first
    config_override = get_test_config_override()
    if config_override:
        try:
            config = load_base_configuration(config_override)
            return clone_config_with_language(config, language, agent_count=agent_count)
        except FileNotFoundError:
            # Fall through to mode-based configuration if override file doesn't exist
            pass

    if mode == "ultra_fast":
        return build_minimal_test_configuration(
            agent_count=agent_count,
            language=language,
            rounds=1,  # Absolute minimum
            memory_limit=3000,  # Minimal memory
        )
    elif mode == "dev":
        return build_minimal_test_configuration(
            agent_count=agent_count,
            language=language,
            rounds=2,
            memory_limit=5000,
        )
    elif mode == "ci":
        config = build_minimal_test_configuration(
            agent_count=agent_count,
            language=language,
            rounds=3,
            memory_limit=8000,
            reasoning_enabled=True,  # Enable reasoning for CI
        )
        # Allow some randomization in CI mode
        return config.model_copy(update={
            "distribution_range_phase1": (0.8, 1.2),
            "distribution_range_phase2": (0.8, 1.2),
        })
    elif mode == "full":
        # Use default configuration for full testing
        config = load_base_configuration("config/default_config.yaml")
        return clone_config_with_language(config, language, agent_count=agent_count)
    else:
        # Default to dev mode
        return build_configuration_for_test_mode("dev", language=language, agent_count=agent_count)
