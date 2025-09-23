"""Shared test infrastructure helpers for the Frohlich Experiment.

This package centralises utilities that keep the new test architecture
consistent: prompt harnesses for real agents, language matrices,
configuration factories, and logging capture helpers.
"""

from .prompt_harness import (
    PromptHarness,
    build_language_manager,
    build_utility_agent,
    build_participant_agent,
    build_participant_agents,
)
from .language_matrix import (
    ALL_LANGUAGES,
    DEFAULT_LANGUAGE_MATRIX,
    language_ids,
    parametrize_languages,
)
from .config_factory import (
    load_base_configuration,
    build_experiment_configuration,
    build_agent_configuration,
    clone_config_with_language,
)
from .process_capture import (
    capture_process_flow_output,
    ProcessLogCapture,
)

__all__ = [
    "PromptHarness",
    "build_language_manager",
    "build_utility_agent",
    "build_participant_agent",
    "build_participant_agents",
    "ALL_LANGUAGES",
    "DEFAULT_LANGUAGE_MATRIX",
    "language_ids",
    "parametrize_languages",
    "load_base_configuration",
    "build_experiment_configuration",
    "build_agent_configuration",
    "clone_config_with_language",
    "capture_process_flow_output",
    "ProcessLogCapture",
]
