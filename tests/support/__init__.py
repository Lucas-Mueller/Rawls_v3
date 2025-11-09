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
    current_language_matrix,
    language_ids,
    parametrize_languages,
)
from .config_factory import (
    load_base_configuration,
    build_experiment_configuration,
    build_minimal_test_configuration,
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
    "current_language_matrix",
    "DEFAULT_LANGUAGE_MATRIX",
    "language_ids",
    "parametrize_languages",
    "load_base_configuration",
    "build_experiment_configuration",
    "build_minimal_test_configuration",
    "build_agent_configuration",
    "clone_config_with_language",
    "capture_process_flow_output",
    "ProcessLogCapture",
]


def __getattr__(name: str):
    if name == "DEFAULT_LANGUAGE_MATRIX":
        from .language_matrix import DEFAULT_LANGUAGE_MATRIX

        return DEFAULT_LANGUAGE_MATRIX
    raise AttributeError(name)
