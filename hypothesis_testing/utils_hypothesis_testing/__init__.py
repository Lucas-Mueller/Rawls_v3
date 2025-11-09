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
from .visualizations import (
    plot_floor_constraint_distribution,
    plot_income_composition,
    plot_income_preference_bars,
    plot_long_term_margin,
    plot_long_term_stability,
    plot_long_term_stability_grid,
    plot_preference_stability,
    plot_rounds_to_outcome,
    plot_rounds_to_outcome_grouped,
    plot_floor_constraint_distribution_grouped,
    plot_transition_heatmaps,
    plot_voting_attempts_summary,
)
from .style import (
    BAYREUTH_COLORS,
    BAYREUTH_FIG_SIZES,
    BAYREUTH_FONT_SIZES,
    PRINCIPLE_COLORS,
    PRINCIPLE_DISPLAY_NAMES,
    apply_bayreuth_theme,
    format_principle_label,
    format_principle_labels,
)

__all__ = [
    "list_config_files",
    "select_configs",
    "run_configs_in_parallel",
    "cramers_v",
    "bias_corrected_cramers_v",
    "bootstrap_cramers_v",
    "plot_income_preference_bars",
    "plot_income_composition",
    "plot_rounds_to_outcome",
    "plot_rounds_to_outcome_grouped",
    "plot_floor_constraint_distribution_grouped",
    "plot_floor_constraint_distribution",
    "plot_voting_attempts_summary",
    "plot_preference_stability",
    "plot_transition_heatmaps",
    "plot_long_term_stability",
    "plot_long_term_margin",
    "plot_long_term_stability_grid",
    "BAYREUTH_COLORS",
    "BAYREUTH_FIG_SIZES",
    "BAYREUTH_FONT_SIZES",
    "PRINCIPLE_COLORS",
    "PRINCIPLE_DISPLAY_NAMES",
    "apply_bayreuth_theme",
    "format_principle_label",
    "format_principle_labels",
]
