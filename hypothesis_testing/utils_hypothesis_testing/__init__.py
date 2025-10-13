"""Utilities for running Hypothesis testing batches.

This package provides helpers to discover configs and run them in parallel
with logging and deterministic output paths for later analysis.
"""

from .runner import (
    list_config_files,
    select_configs,
    run_configs_in_parallel,
)
from .statistics import (
    bias_corrected_cramers_v,
    bootstrap_cramers_v,
    cramers_v,
)

__all__ = [
    "list_config_files",
    "select_configs",
    "run_configs_in_parallel",
    "cramers_v",
    "bias_corrected_cramers_v",
    "bootstrap_cramers_v",
]
