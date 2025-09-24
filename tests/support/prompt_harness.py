"""Prompt harness utilities for test suites.

These helpers create real participant and utility agents with predictable
settings so tests can exercise the same LLM pathways used in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from config import AgentConfiguration, ExperimentConfiguration
from experiment_agents import ParticipantAgent, UtilityAgent
from experiment_agents.participant_agent import create_participant_agents_with_dynamic_temperature
from utils.dynamic_model_capabilities import TemperatureCache
from utils.language_manager import LanguageManager, SupportedLanguage, create_language_manager
from utils.seed_manager import SeedManager


@dataclass
class HarnessConfig:
    """Declarative configuration for prompt harness provisioning."""

    language: SupportedLanguage = SupportedLanguage.ENGLISH
    agent_count: int = 2
    initialize_agents: bool = True
    seed: Optional[int] = None


def build_language_manager(language: SupportedLanguage, seed: Optional[int] = None) -> LanguageManager:
    """Return a language manager configured for the requested language."""
    return create_language_manager(language, seed)


async def build_utility_agent(
    model: str,
    temperature: float,
    language: SupportedLanguage,
    language_manager: Optional[LanguageManager] = None,
    initialize: bool = True,
) -> UtilityAgent:
    """Create a utility agent ready for parsing and validation."""
    manager = language_manager or build_language_manager(language)
    utility_agent = UtilityAgent(
        utility_model=model,
        temperature=temperature,
        experiment_language=language.value.lower(),
        language_manager=manager,
        temperature_cache=TemperatureCache(),
    )
    if initialize:
        await utility_agent.async_init()
    return utility_agent


def _coerce_supported_language(value: str) -> SupportedLanguage:
    normalized = value.strip().lower()
    for language in SupportedLanguage:
        if language.value.lower() == normalized:
            return language
    raise ValueError(f"Unsupported language value: {value}")


async def build_participant_agent(
    agent_config: AgentConfiguration,
    experiment_config: Optional[ExperimentConfiguration] = None,
    language_manager: Optional[LanguageManager] = None,
    temperature_cache: Optional[TemperatureCache] = None,
    initialize: bool = True,
) -> ParticipantAgent:
    """Create a single participant agent for use in tests."""
    manager = language_manager or build_language_manager(_coerce_supported_language(agent_config.language))
    cache = temperature_cache or TemperatureCache()
    participant = ParticipantAgent(agent_config, experiment_config, manager, cache)
    if initialize:
        await participant.async_init()
    return participant


async def build_participant_agents(
    agent_configs: Sequence[AgentConfiguration],
    experiment_config: Optional[ExperimentConfiguration] = None,
    language_manager: Optional[LanguageManager] = None,
    initialize: bool = True,
) -> List[ParticipantAgent]:
    """Create participant agents, optionally skipping initialization."""
    if not agent_configs:
        return []

    cache = TemperatureCache()
    manager = language_manager or build_language_manager(
        _coerce_supported_language(agent_configs[0].language)
    )

    if initialize:
        return await create_participant_agents_with_dynamic_temperature(
            list(agent_configs),
            experiment_config=experiment_config,
            language_manager=manager,
            temperature_cache=cache,
        )

    # Manual lightweight construction when initialization is deferred
    participants: List[ParticipantAgent] = []
    for config in agent_configs:
        participant = ParticipantAgent(config, experiment_config, manager, cache)
        participants.append(participant)
    return participants


class PromptHarness:
    """Convenience wrapper bundling prompt-related helpers for tests."""

    def __init__(self, experiment_config: ExperimentConfiguration, seed: Optional[int] = None) -> None:
        self.experiment_config = experiment_config
        self.seed_manager = SeedManager()
        self.seed = seed
        self.temperature_cache = TemperatureCache()
        self._last_localized_config: Optional[ExperimentConfiguration] = None

    def ensure_seed(self) -> int:
        """Ensure a reproducible seed for the harness session."""
        if self.seed is None:
            self.seed = self.seed_manager.initialize_from_config(self.experiment_config)
        return self.seed

    def create_language_manager(self, language: SupportedLanguage) -> LanguageManager:
        """Return a language manager tied to the harness seed."""
        seed = self.ensure_seed()
        return build_language_manager(language, seed)

    def build_localized_config(
        self,
        language: SupportedLanguage,
        agent_overrides: Sequence[AgentConfiguration],
    ) -> ExperimentConfiguration:
        """Produce an experiment configuration adapted for the requested language."""
        localized = self.experiment_config.model_copy(
            update={
                "language": language.value,
                "agents": list(agent_overrides),
            }
        )
        self._last_localized_config = localized
        return localized

    @property
    def last_localized_config(self) -> Optional[ExperimentConfiguration]:
        """Return the most recently generated localized configuration, if any."""
        return self._last_localized_config

    async def create_participants(
        self,
        language: SupportedLanguage,
        agent_count: Optional[int] = None,
        initialize: bool = True,
        preserve_config_languages: bool = False,
    ) -> List[ParticipantAgent]:
        """Provision participant agents based on the harness configuration."""
        count = agent_count or len(self.experiment_config.agents)
        agent_configs = list(self.experiment_config.agents)[:count]
        if count > len(self.experiment_config.agents):
            raise ValueError(
                f"Requested {count} agents but base configuration only defines {len(self.experiment_config.agents)}"
            )
        updated_configs: List[AgentConfiguration] = []
        for idx, config in enumerate(agent_configs):
            if preserve_config_languages:
                lang_value = config.language
                supported = _coerce_supported_language(lang_value)
            else:
                supported = language
                lang_value = supported.value.lower()
            updated_configs.append(
                config.model_copy(update={"language": lang_value})
            )

        effective_language = language if not preserve_config_languages else _coerce_supported_language(agent_configs[0].language)
        language_manager = self.create_language_manager(effective_language)
        localized_config = self.build_localized_config(effective_language, updated_configs)
        if initialize:
            return await create_participant_agents_with_dynamic_temperature(
                updated_configs,
                experiment_config=localized_config,
                language_manager=language_manager,
                temperature_cache=self.temperature_cache,
            )

        participants: List[ParticipantAgent] = []
        for config in updated_configs:
            participant = ParticipantAgent(
                config,
                localized_config,
                language_manager,
                self.temperature_cache,
            )
            participants.append(participant)
        return participants

    async def create_utility_agent(
        self,
        language: SupportedLanguage,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        initialize: bool = True,
    ) -> UtilityAgent:
        """Provision a utility agent aligned with the harness configuration."""
        config_model = model or self.experiment_config.utility_agent_model
        config_temp = temperature if temperature is not None else self.experiment_config.utility_agent_temperature
        manager = self.create_language_manager(language)
        utility = UtilityAgent(
            utility_model=config_model,
            temperature=config_temp,
            experiment_language=language.value.lower(),
            language_manager=manager,
            temperature_cache=self.temperature_cache,
        )
        if initialize:
            await utility.async_init()
        return utility
