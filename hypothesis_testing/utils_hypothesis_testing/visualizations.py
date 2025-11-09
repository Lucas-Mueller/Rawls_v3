"""Shared visualization helpers for descriptive hypothesis notebooks.

Each helper mirrors the styling used in the project notebooks while allowing
callers to override figure titles when needed.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch

from .style import BAYREUTH_COLORS, BAYREUTH_FIG_SIZES, BAYREUTH_FONT_SIZES
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable


ColorMap = Dict[str, str]
FontSizeMap = Dict[str, int]
FigureSizeMap = Dict[str, Tuple[float, float]]
FormatLabelFunc = Callable[[str], str]


def _resolve_title(custom_title: Optional[str], default: str) -> str:
    """Return the caller-specified title if present, otherwise fall back."""
    return custom_title if custom_title is not None else default


def _scale_font_sizes(font_sizes: FontSizeMap, scale: float) -> FontSizeMap:
    """Return a scaled copy of the font size map."""
    if scale == 1.0:
        return dict(font_sizes)
    scaled: FontSizeMap = {}
    for key, value in font_sizes.items():
        if isinstance(value, (int, float)):
            scaled[key] = max(1, int(round(value * scale)))
        else:
            scaled[key] = value
    return scaled


def plot_income_preference_bars(
    summary_df: pd.DataFrame,
    count_long: pd.DataFrame,
    percent_long: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """
    Plot absolute counts and within-income-class shares for switcher analysis.
    """
    if summary_df.empty:
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    category_order = summary_df["Income Class"].tolist()
    palette = [colors["switched"], colors["stayed"]]
    share_long = percent_long.rename(columns={"Percent": "Share"}).copy()
    share_long["Share"] = share_long["Share"].fillna(0)

    fig, axes = plt.subplots(ncols=2, figsize=fig_sizes["double"], sharey=True)

    sns.barplot(
        data=count_long,
        x="Count",
        y="Income Class",
        hue="Preference Group",
        order=category_order,
        hue_order=["Changed Preference", "Maintained Preference"],
        orient="h",
        palette=palette,
        ax=axes[0],
    )
    axes[0].set_title(
        "Absolute Counts",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[0].set_xlabel("Number of Agents", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[0].set_ylabel("Income Class", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[0].grid(axis="x", color=colors["light_gray"], linewidth=0.6)
    if axes[0].legend_:
        axes[0].legend_.remove()

    sns.barplot(
        data=share_long,
        x="Share",
        y="Income Class",
        hue="Preference Group",
        order=category_order,
        hue_order=["Changed Preference", "Maintained Preference"],
        orient="h",
        palette=palette,
        ax=axes[1],
    )
    axes[1].set_title(
        "Within-Group Share",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[1].set_xlabel("Percentage of Group", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[1].set_ylabel("", fontsize=font_sizes["axis_label"])
    axes[1].grid(axis="x", color=colors["light_gray"], linewidth=0.6)

    share_max = share_long["Share"].max() if not share_long.empty else 0
    share_limit = min(100, share_max + 10)
    if share_limit <= 20:
        tick_step = 5
    elif share_limit <= 40:
        tick_step = 10
    else:
        tick_step = 20
    tick_max = share_limit - (share_limit % tick_step) if share_limit >= tick_step else share_limit
    tick_values = np.arange(0, tick_max + tick_step, tick_step)
    axes[1].set_xlim(0, share_limit)
    axes[1].set_xticks(tick_values)
    axes[1].legend(
        title="Preference Group",
        framealpha=0.95,
        edgecolor=colors["medium_gray"],
        loc="lower right",
    )

    for ax in axes:
        ax.spines["left"].set_color(colors["medium_gray"])
        ax.spines["bottom"].set_color(colors["medium_gray"])
        for patch in ax.patches:
            value = patch.get_width()
            if value <= 0:
                continue
            y = patch.get_y() + patch.get_height() / 2
            if ax is axes[0]:
                label = f"{value:.0f}"
                offset = 0.5
            else:
                label = f"{value:.1f}%"
                offset = 1.0
            ax.text(
                value + offset,
                y,
                label,
                va="center",
                ha="left",
                fontsize=font_sizes["annotation"],
                color=colors["dark_gray"],
            )

    figure_title = _resolve_title(
        title,
        f"Income Distribution by Preference Stability ({title_suffix})",
    )
    fig.suptitle(
        figure_title,
        fontsize=font_sizes["title"],
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    plt.show()
    plt.close(fig)


def plot_income_composition(
    count_long: pd.DataFrame,
    composition_percent_long: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot switcher composition by income class with absolute and relative panels."""
    if count_long.empty:
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    palette = [colors["switched"], colors["stayed"]]
    category_order = list(dict.fromkeys(count_long["Income Class"]))

    fig, axes = plt.subplots(ncols=2, figsize=fig_sizes["double"], sharey=True)

    sns.barplot(
        data=count_long,
        x="Count",
        y="Income Class",
        hue="Preference Group",
        order=category_order,
        hue_order=["Changed Preference", "Maintained Preference"],
        orient="h",
        palette=palette,
        ax=axes[0],
    )
    axes[0].set_title(
        "Absolute Counts",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[0].set_xlabel("Number of Agents", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[0].set_ylabel("Income Class", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[0].grid(axis="x", color=colors["light_gray"], linewidth=0.6)
    if axes[0].legend_:
        axes[0].legend_.remove()
    axes[0].spines["left"].set_color(colors["medium_gray"])
    axes[0].spines["bottom"].set_color(colors["medium_gray"])

    legend_handles = [
        Patch(facecolor=colors["switched"], edgecolor=colors["primary_blue"], label="Changed Pref."),
        Patch(facecolor=colors["stayed"], edgecolor=colors["primary_blue"], label="Maintained Pref."),
    ]
    axes[0].legend(
        handles=legend_handles,
        framealpha=0.95,
        edgecolor=colors["medium_gray"],
        loc="upper right",
    )

    tuples: Iterable[Tuple[str, str, float]] = count_long[
        ["Income Class", "Preference Group", "Count"]
    ].itertuples(index=False, name=None)
    for patch, (income_class, group, count) in zip(axes[0].patches, tuples):
        if count <= 0:
            continue
        y = patch.get_y() + patch.get_height() / 2
        width = patch.get_width()
        if (group == "Maintained Preference" and count <= 6) or (
            group == "Changed Preference" and income_class == "Medium-High"
        ):
            x = patch.get_x() + width + 0.8
            ha = "left"
            color = colors["dark_gray"]
        else:
            x = patch.get_x() + width / 2
            ha = "center"
            color = colors["background"]
        axes[0].text(
            x,
            y,
            f"{int(count)}",
            va="center",
            ha=ha,
            fontsize=font_sizes["annotation"] + 1,
            fontweight="bold",
            color=color,
        )

    percent_frame = composition_percent_long.copy()
    percent_frame["Percent"] = percent_frame["Percent"].fillna(0)

    sns.barplot(
        data=percent_frame,
        x="Percent",
        y="Income Class",
        hue="Preference Group",
        order=category_order,
        hue_order=["Changed Preference", "Maintained Preference"],
        orient="h",
        palette=palette,
        ax=axes[1],
    )
    axes[1].set_title(
        "Relative Counts",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[1].set_xlabel("Share of Income Class (%)", fontsize=font_sizes["axis_label"], labelpad=6)
    axes[1].set_ylabel("")
    axes[1].set_xlim(0, 115)
    axes[1].grid(axis="x", color=colors["light_gray"], linewidth=0.6)
    axes[1].spines["left"].set_color(colors["medium_gray"])
    axes[1].spines["bottom"].set_color(colors["medium_gray"])
    axes[1].spines["top"].set_visible(True)
    axes[1].spines["right"].set_visible(True)
    axes[1].spines["right"].set_color(colors["medium_gray"])

    percent_values = percent_frame["Percent"].tolist()
    for patch, percent in zip(axes[1].patches, percent_values):
        if percent <= 0:
            continue
        y = patch.get_y() + patch.get_height() / 2
        if percent >= 30:
            x = patch.get_x() + percent / 2
            ha = "center"
            color = colors["background"]
        else:
            x = patch.get_x() + max(percent - 1.2, 0.8)
            ha = "right"
            color = colors["background"] if percent >= 12 else colors["dark_gray"]
        axes[1].text(
            x,
            y,
            f"{percent:.0f}%",
            va="center",
            ha=ha,
            fontsize=font_sizes["annotation"] + 1,
            fontweight="bold",
            color=color,
        )

    axes[1].legend(
        handles=legend_handles,
        framealpha=0.95,
        edgecolor=colors["medium_gray"],
        loc="upper right",
    )

    figure_title = _resolve_title(
        title,
        f"Switcher Composition by Income Class ({title_suffix})",
    )
    fig.suptitle(
        figure_title,
        fontsize=font_sizes["title"],
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    plt.show()
    plt.close(fig)


def plot_rounds_to_outcome(
    run_metrics: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot histogram of consensus rounds for a cohort."""
    consensus_rounds = run_metrics[
        (run_metrics["consensus_reached"] == True) & run_metrics["rounds_to_outcome"].notna()
    ].copy()
    if consensus_rounds.empty:
        print(f"No consensus runs with recorded round counts for {title_suffix}.")
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    rounds_int = consensus_rounds["rounds_to_outcome"].astype(int)
    max_observed = int(rounds_int.max())
    round_range = list(range(1, max(max_observed, 10) + 1))
    counts = rounds_int.value_counts().reindex(round_range, fill_value=0)

    fig, ax = plt.subplots(figsize=fig_sizes["single"])
    bars = ax.bar(
        counts.index,
        counts.values,
        color=colors["primary_green"],
        edgecolor=colors["dark_gray"],
        alpha=0.85,
        linewidth=1.2,
    )

    for bar, value in zip(bars, counts.values):
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.3,
                f"{int(value)}",
                ha="center",
                va="bottom",
                fontsize=font_sizes["annotation"],
                fontweight="bold",
                color=colors["dark_gray"],
            )

    ax.set_xticks(round_range)
    ax.set_xticklabels([str(r) for r in round_range])
    ax.set_xlim(0.5, round_range[-1] + 0.5)
    ax.set_xlabel("Discussion Rounds", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylabel("Number of Runs", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylim(0, counts.max() + 2.5 if counts.max() > 0 else 1)
    effective_title = _resolve_title(
        title,
        f"Rounds to Consensus Outcome ({title_suffix})",
    )
    ax.set_title(effective_title, fontsize=font_sizes["subtitle"], fontweight="bold", pad=10)

    fig.tight_layout()
    plt.show()
    plt.close(fig)

    rounds_values = rounds_int.values
    print("Consensus Timing Summary:")
    print(f"  Total consensus runs: {len(rounds_values)}")
    print(f"  Range: {rounds_values.min():.0f}-{rounds_values.max():.0f} rounds")
    print(
        f"  Mean: {rounds_values.mean():.2f} rounds  |  Median: {np.median(rounds_values):.0f} rounds"
    )


def plot_rounds_to_outcome_grouped(
    cohort_run_metrics: Sequence[Tuple[str, pd.DataFrame]],
    *,
    language_order: Optional[Sequence[str]] = None,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    bar_width: float = 0.24,
    title: Optional[str] = None,
    legend_loc: str = "upper right",
    font_scale: float = 1.0,
    annotation_fontsize: Optional[float] = None,
    show_title: bool = True,
    group_label: str = "Language",
) -> None:
    """
    Render a grouped bar chart of consensus rounds across cohorts.

    Use `annotation_fontsize` to override the count-label size per bar (default follows Bayreuth scale).
    Set `show_title=False` to suppress the chart title when embedding alongside others.
    Use `group_label` to customize the legend title (default "Language").
    """
    if not cohort_run_metrics:
        print("No cohorts provided for grouped consensus timing plot.")
        return

    colors = colors or BAYREUTH_COLORS
    base_fonts = font_sizes or BAYREUTH_FONT_SIZES
    font_sizes = _scale_font_sizes(base_fonts, font_scale)
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES
    effective_annotation_size = (
        max(1, int(round(annotation_fontsize))) if annotation_fontsize is not None else font_sizes["annotation"]
    )

    # Preserve caller order but allow optional explicit sequencing.
    cohort_map: Dict[str, pd.DataFrame] = {label: df for label, df in cohort_run_metrics}
    ordered_labels: List[str] = []
    if language_order:
        ordered_labels.extend([label for label in language_order if label in cohort_map])
    ordered_labels.extend(label for label in cohort_map.keys() if label not in ordered_labels)

    if not ordered_labels:
        print("No valid run metrics provided for grouped consensus timing plot.")
        return

    counts_by_label: Dict[str, pd.Series] = {}
    max_round_observed = 0
    for label in ordered_labels:
        run_metrics = cohort_map[label]
        if run_metrics is None or run_metrics.empty:
            counts_by_label[label] = pd.Series(dtype=int)
            continue

        cohort_consensus = run_metrics[
            (run_metrics["consensus_reached"] == True) & run_metrics["rounds_to_outcome"].notna()
        ]
        if cohort_consensus.empty:
            counts_by_label[label] = pd.Series(dtype=int)
            continue

        rounds_int = cohort_consensus["rounds_to_outcome"].astype(int)
        if not rounds_int.empty:
            max_round_observed = max(max_round_observed, int(rounds_int.max()))
        counts_by_label[label] = rounds_int.value_counts()

    if max_round_observed == 0:
        print("No consensus runs with recorded round counts across cohorts.")
        return

    max_round = max(10, max_round_observed)
    round_range = list(range(1, max_round + 1))

    palette = [
        colors["primary_green"],
        colors["primary_blue"],
        colors["primary_orange"],
        colors["medium_gray"],
        colors["accent_1"],
    ]
    num_labels = len(ordered_labels)
    if num_labels > len(palette):
        palette = (palette * (num_labels // len(palette) + 1))[:num_labels]
    else:
        palette = palette[:num_labels]

    x = np.array(round_range, dtype=float)
    fig, ax = plt.subplots(figsize=fig_sizes["double"])
    x_offsets = [
        (idx - (num_labels - 1) / 2) * bar_width for idx in range(num_labels)
    ]

    for idx, label in enumerate(ordered_labels):
        counts = counts_by_label[label].reindex(round_range, fill_value=0).astype(int)
        bar_positions = x + x_offsets[idx]
        bars = ax.bar(
            bar_positions,
            counts.values,
            width=bar_width * 0.92,
            color=palette[idx],
            edgecolor=colors["dark_gray"],
            linewidth=0.8,
            alpha=0.9,
            label=label,
        )

        for bar, value in zip(bars, counts.values):
            if value > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.3,
                    f"{int(value)}",
                    ha="center",
                    va="bottom",
                    fontsize=effective_annotation_size,
                    fontweight="bold",
                    color=colors["dark_gray"],
                )

    if show_title:
        effective_title = _resolve_title(
            title,
            "Rounds to Consensus Outcome by Cohort",
        )
        ax.set_title(effective_title, fontsize=font_sizes["title"], fontweight="bold", pad=12)

    ax.set_xlabel("Discussion Rounds", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylabel("Number of Runs", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_xticks(round_range)
    ax.set_xticklabels([str(r) for r in round_range])
    ax.set_xlim(round_range[0] - 0.5, round_range[-1] + 0.5)
    max_count = max(
        (counts_by_label[label].reindex(round_range, fill_value=0).max() for label in ordered_labels),
        default=0,
    )
    ax.set_ylim(0, max_count + 2.5 if max_count > 0 else 1)
    ax.legend(
        title=group_label,
        fontsize=font_sizes["legend"],
        title_fontsize=font_sizes["legend"],
        loc=legend_loc,
        frameon=True,
    )
    ax.grid(axis="y", color=colors["light_gray"], linewidth=0.6)
    ax.spines["left"].set_visible(True)
    ax.spines["bottom"].set_visible(True)
    fig.tight_layout()
    plt.show()
    plt.close(fig)


def plot_floor_constraint_distribution_grouped(
    cohort_vote_rounds: Sequence[Tuple[str, pd.DataFrame]],
    *,
    language_order: Optional[Sequence[str]] = None,
    target_principle_label: str = "Max Floor",
    bin_width: int = 4000,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    bar_width: float = 0.24,
    title: Optional[str] = None,
    legend_loc: str = "upper right",
    font_scale: float = 1.25,
    show_title: bool = True,
    annotation_fontsize: Optional[float] = None,
    group_label: str = "Language",
    use_amount_scale_xticks: bool = False,
    min_bin_value: int = 0,
) -> None:
    """
    Render grouped constraint amounts for a target principle across cohorts.

    Amounts are binned on a continuous axis using fixed-width buckets (default 4k).
    Set `show_title=False` to suppress the chart title when embedding alongside others.
    Use `annotation_fontsize` to override the count labels.
    Toggle `use_amount_scale_xticks` to show ticks as dollar-scaled values instead of range labels.
    Set `min_bin_value` to adjust the starting point of the x-axis (default 0).
    """
    if not cohort_vote_rounds:
        print("No cohorts provided for grouped constraint plot.")
        return

    colors = colors or BAYREUTH_COLORS
    base_fonts = font_sizes or BAYREUTH_FONT_SIZES
    font_sizes = _scale_font_sizes(base_fonts, font_scale)
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES
    effective_annotation_size = (
        max(1, int(round(annotation_fontsize))) if annotation_fontsize is not None else font_sizes["annotation"]
    )

    cohort_map: Dict[str, pd.DataFrame] = {label: df for label, df in cohort_vote_rounds}
    ordered_labels: List[str] = []
    if language_order:
        ordered_labels.extend([label for label in language_order if label in cohort_map])
    ordered_labels.extend(label for label in cohort_map.keys() if label not in ordered_labels)

    if not ordered_labels:
        print("No valid vote round data provided for grouped constraint plot.")
        return

    raw_amounts_by_label: Dict[str, pd.Series] = {}
    max_amount_observed = 0.0

    for label in ordered_labels:
        vote_rounds = cohort_map[label]
        if vote_rounds is None or vote_rounds.empty:
            raw_amounts_by_label[label] = pd.Series(dtype=float)
            continue

        consensus_rounds = vote_rounds[
            (vote_rounds["consensus_reached"] == True)
            & vote_rounds["agreed_constraint"].notna()
            & (vote_rounds["agreed_principle_label"] == target_principle_label)
        ]
        if consensus_rounds.empty:
            raw_amounts_by_label[label] = pd.Series(dtype=float)
            continue

        amounts = consensus_rounds["agreed_constraint"].astype(float)
        if not amounts.empty:
            max_amount_observed = max(max_amount_observed, float(amounts.max()))
        raw_amounts_by_label[label] = amounts

    if max_amount_observed <= 0:
        print(
            f"No consensus rounds with {target_principle_label} constraints found across cohorts."
        )
        return

    if bin_width <= 0:
        raise ValueError("bin_width must be a positive integer.")

    max_edge = int(np.ceil(max_amount_observed / bin_width) * bin_width)
    bin_edges = np.arange(float(min_bin_value), max_edge + bin_width, bin_width, dtype=float)
    if len(bin_edges) < 2:
        bin_edges = np.array([float(min_bin_value), float(min_bin_value + bin_width)], dtype=float)
    num_bins = len(bin_edges) - 1
    bin_indices = list(range(num_bins))

    def _format_bin_label(lower: float, upper: float) -> str:
        lower_k = lower / 1000
        upper_k = upper / 1000
        return f"${lower_k:.0f}k–${upper_k:.0f}k"

    bin_labels = [_format_bin_label(bin_edges[i], bin_edges[i + 1]) for i in range(num_bins)]

    counts_by_label: Dict[str, pd.Series] = {}
    for label in ordered_labels:
        amounts = raw_amounts_by_label[label]
        if amounts.empty:
            counts_by_label[label] = pd.Series(0, index=bin_indices, dtype=int)
            continue
        bucketed = pd.cut(
            amounts,
            bins=bin_edges,
            right=True,
            include_lowest=True,
            labels=bin_indices,
        )
        counts = bucketed.value_counts().reindex(bin_indices, fill_value=0).sort_index()
        counts_by_label[label] = counts.astype(int)

    x = np.arange(num_bins, dtype=float)

    palette = [
        colors["primary_green"],
        colors["primary_blue"],
        colors["primary_orange"],
        colors["medium_gray"],
        colors["accent_1"],
    ]
    num_labels = len(ordered_labels)
    if num_labels > len(palette):
        palette = (palette * (num_labels // len(palette) + 1))[:num_labels]
    else:
        palette = palette[:num_labels]

    fig, ax = plt.subplots(figsize=fig_sizes["double"])
    x_offsets = [
        (idx - (num_labels - 1) / 2) * bar_width for idx in range(num_labels)
    ]

    def format_constraint(amount: float) -> str:
        amount_k = amount / 1000
        if abs(amount_k - round(amount_k)) < 1e-6:
            return f"${int(round(amount_k))}k"
        return f"${amount_k:.1f}k"

    max_count = 0
    for idx, label in enumerate(ordered_labels):
        counts = counts_by_label[label]
        bar_positions = x + x_offsets[idx]
        bars = ax.bar(
            bar_positions,
            counts.values,
            width=bar_width * 0.92,
            color=palette[idx],
            edgecolor=colors["dark_gray"],
            linewidth=0.8,
            alpha=0.9,
            label=label,
        )

        max_count = max(max_count, counts.values.max() if len(counts.values) else 0)
        for bar, value in zip(bars, counts.values):
            if value > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.3,
                    f"{int(value)}",
                    ha="center",
                    va="bottom",
                    fontsize=effective_annotation_size,
                    fontweight="bold",
                    color=colors["dark_gray"],
                )

    if show_title:
        effective_title = _resolve_title(
            title,
            f"{target_principle_label} Constraint Amounts by {group_label}",
        )
        if effective_title:
            ax.set_title(
                effective_title,
                fontsize=font_sizes["title"],
                fontweight="bold",
                pad=12,
            )
    ax.set_xlabel("Constraint Amount", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylabel("Number of Runs", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_xticks(x)
    if use_amount_scale_xticks:
        scale_labels = [f"${int(round(bin_edges[i + 1] / 1000))}k" for i in range(num_bins)]
        ax.set_xticklabels(scale_labels)
    else:
        ax.set_xticklabels(bin_labels)
    ax.set_xlim(x[0] - 0.5, x[-1] + 0.5)
    ax.set_ylim(0, max_count + 2.5 if max_count > 0 else 1)
    ax.legend(
        title=group_label,
        fontsize=font_sizes["legend"],
        title_fontsize=font_sizes["legend"],
        loc=legend_loc,
        frameon=True,
    )
    ax.grid(axis="y", color=colors["light_gray"], linewidth=0.6)
    ax.spines["left"].set_visible(True)
    ax.spines["bottom"].set_visible(True)
    fig.tight_layout()
    plt.show()
    plt.close(fig)


def plot_floor_constraint_distribution(
    vote_rounds: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot histogram of negotiated floor constraints."""
    parameter_votes = vote_rounds[
        (vote_rounds["consensus_reached"] == True) & vote_rounds["agreed_constraint"].notna()
    ]
    if parameter_votes.empty:
        print(f"No successful votes with numeric constraints found for {title_suffix}.")
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    amounts = parameter_votes["agreed_constraint"].values
    bin_width = 1000
    min_amount = 0
    max_amount = int(np.ceil(amounts.max() / bin_width) * bin_width)
    bins = np.arange(min_amount, max_amount + bin_width, bin_width)

    fig, ax = plt.subplots(figsize=fig_sizes["wide_single"])
    counts, bin_edges, _ = ax.hist(
        amounts,
        bins=bins,
        color=colors["primary_green"],
        edgecolor=colors["primary_blue"],
        alpha=0.85,
        linewidth=1.2,
    )
    for count, edge in zip(counts, bin_edges[:-1]):
        if count > 0:
            ax.text(
                edge + bin_width / 2,
                count + 0.4,
                int(count),
                ha="center",
                va="bottom",
                fontsize=font_sizes["annotation"],
                fontweight="bold",
                color=colors["dark_gray"],
            )
    ax.set_xticks(bins)
    ax.set_xticklabels([f"${int(b/1000)}k" for b in bins])
    ax.set_xlabel("Floor Constraint Amount", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylabel("Number of Runs", fontsize=font_sizes["axis_label"], labelpad=10)
    ax.set_ylim(0, counts.max() + 2.5)
    effective_title = _resolve_title(
        title,
        f"Floor Constraint Distribution ({title_suffix})",
    )
    ax.set_title(effective_title, fontsize=font_sizes["subtitle"], fontweight="bold", pad=10)

    fig.tight_layout()
    plt.show()
    plt.close(fig)

    print("Floor Amount Summary:")
    print(f"  Total votes: {len(amounts)}")
    print(f"  Range: ${amounts.min():,.0f} - ${amounts.max():,.0f}")
    print(
        f"  Mean: ${amounts.mean():,.0f}  |  Median: ${np.median(amounts):,.0f}  |  SD: ${amounts.std():,.0f}"
    )


def plot_voting_attempts_summary(
    run_metrics: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot distributions of total vote attempts and success rates."""
    if run_metrics.empty:
        print(f"No voting metrics available for {title_suffix}.")
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    metrics = run_metrics.copy()
    metrics["success_rate"] = metrics.apply(
        lambda row: row["successful_votes"] / row["total_vote_attempts"]
        if row["total_vote_attempts"] not in (None, 0)
        else np.nan,
        axis=1,
    )

    fig, axes = plt.subplots(1, 2, figsize=fig_sizes["double"])

    attempts = metrics["total_vote_attempts"].dropna()
    max_attempts = int(attempts.max()) if not attempts.empty else 0
    attempt_bins = range(0, max_attempts + 2)
    sns.histplot(
        attempts,
        bins=attempt_bins if max_attempts > 0 else 1,
        color=colors["primary_blue"],
        edgecolor=colors["dark_gray"],
        ax=axes[0],
    )
    axes[0].set_title(
        f"Vote Attempts Distribution ({title_suffix})",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[0].set_xlabel("Total Vote Attempts", fontsize=font_sizes["axis_label"])
    axes[0].set_ylabel("Runs", fontsize=font_sizes["axis_label"])

    valid_rates = metrics["success_rate"].dropna()
    rate_bins = np.linspace(0, 1, 11)
    sns.histplot(
        valid_rates,
        bins=rate_bins,
        color=colors["primary_green"],
        edgecolor=colors["dark_gray"],
        ax=axes[1],
    )
    axes[1].set_title(
        f"Success Rate Distribution ({title_suffix})",
        fontsize=font_sizes["subtitle"],
        fontweight="bold",
        pad=8,
    )
    axes[1].set_xlabel("Success Rate", fontsize=font_sizes["axis_label"])
    axes[1].set_ylabel("Runs", fontsize=font_sizes["axis_label"])
    axes[1].set_xlim(0, 1)

    if title is not None:
        fig.suptitle(title, fontsize=font_sizes["title"], fontweight="bold", y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
    else:
        fig.tight_layout()
    plt.show()
    plt.close(fig)

    print("Voting Attempts Summary:")
    if not attempts.empty:
        print(f"  Mean attempts per run: {attempts.mean():.2f}")
        print(f"  Median attempts per run: {attempts.median():.0f}")
    if not valid_rates.empty:
        print(f"  Mean success rate: {valid_rates.mean():.2%}")
        print(f"  Median success rate: {valid_rates.median():.2%}")


def plot_preference_stability(
    transition_df: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Visualise stay vs switch counts across preference waves."""
    if transition_df.empty:
        print(f"No transition data available for {title_suffix}.")
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    transitions = [
        ("wave1", "wave2", "W1→W2"),
        ("wave2", "wave3", "W2→W3"),
        ("wave3", "wave4", "W3→W4"),
    ]
    stability_stats = []
    for from_col, to_col, label in transitions:
        stayed = (transition_df[from_col] == transition_df[to_col]).sum()
        switched = len(transition_df) - stayed
        stability_stats.append({"Transition": label, "Stayed": stayed, "Switched": switched})

    stats_df = pd.DataFrame(stability_stats)
    stats_long = stats_df.melt(
        id_vars="Transition",
        value_vars=["Stayed", "Switched"],
        var_name="Status",
        value_name="Count",
    )

    fig, ax = plt.subplots(figsize=fig_sizes["single"])
    palette = {"Stayed": colors["stayed"], "Switched": colors["switched"]}
    sns.barplot(data=stats_long, x="Transition", y="Count", hue="Status", palette=palette, ax=ax)
    effective_title = _resolve_title(
        title,
        f"Preference Stability Across Waves ({title_suffix})",
    )
    ax.set_title(effective_title, fontsize=font_sizes["subtitle"], fontweight="bold", pad=10)
    ax.set_xlabel("Transition", fontsize=font_sizes["axis_label"])
    ax.set_ylabel("Agents", fontsize=font_sizes["axis_label"])
    ax.legend(framealpha=0.95, edgecolor=colors["medium_gray"])

    fig.tight_layout()
    plt.show()
    plt.close(fig)

    print("Stability Breakdown:")
    for _, row in stats_df.iterrows():
        total = row["Stayed"] + row["Switched"]
        if total > 0:
            pct = row["Stayed"] / total * 100
        else:
            pct = 0.0
        print(f"  {row['Transition']}: {row['Stayed']}/{total} stayed ({pct:.1f}%)")


def plot_transition_heatmaps(
    transition_df: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    principle_display_order: Sequence[str],
    format_principle_label: FormatLabelFunc,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot heatmaps for principle transitions between waves."""
    if transition_df.empty:
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    fig, axes = plt.subplots(1, 3, figsize=fig_sizes["triple"])
    transitions = [
        ("wave1", "wave2", "Wave 1 → 2"),
        ("wave2", "wave3", "Wave 2 → 3"),
        ("wave3", "wave4", "Wave 3 → 4"),
    ]
    stay_stats: List[Tuple[str, int, int]] = []

    for ax, (from_col, to_col, label) in zip(axes, transitions):
        from_series = transition_df[from_col].map(format_principle_label)
        to_series = transition_df[to_col].map(format_principle_label)
        matrix = pd.crosstab(from_series, to_series, margins=False)
        matrix = matrix.reindex(
            index=principle_display_order,
            columns=principle_display_order,
            fill_value=0,
        )
        row_sums = matrix.sum(axis=1)
        matrix_pct = matrix.div(row_sums.replace(0, np.nan), axis=0) * 100

        sns.heatmap(
            matrix,
            annot=False,
            fmt="d",
            cmap="Blues",
            ax=ax,
            cbar=True,
            linewidths=0.8,
            linecolor=colors["light_gray"],
            vmin=0,
            vmax=max(matrix.values.max(), 1),
            cbar_kws={"shrink": 0.8},
        )

        for i, row_label in enumerate(matrix.index):
            for j, col_label in enumerate(matrix.columns):
                count = matrix.iloc[i, j]
                pct = matrix_pct.iloc[i, j]
                text = f"{int(count)}\\n({pct:.0f}%)" if count > 0 and not np.isnan(pct) else ""
                weight = "bold" if i == j and count > 0 else "normal"
                color = "white" if count > matrix.values.max() * 0.6 else colors["dark_gray"]
                ax.text(
                    j + 0.5,
                    i + 0.5,
                    text,
                    ha="center",
                    va="center",
                    fontsize=font_sizes["annotation"] - 1,
                    fontweight=weight,
                    color=color,
                )

        stay = int(matrix.values.diagonal().sum())
        total = int(matrix.values.sum())
        stay_stats.append((label, stay, total))

        ax.set_title(label, fontsize=font_sizes["subtitle"], fontweight="bold", pad=8)
        ax.set_xlabel("To Principle", fontsize=font_sizes["tick_label"])
        ax.set_ylabel("From Principle" if ax == axes[0] else "", fontsize=font_sizes["tick_label"])
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            fontsize=font_sizes["annotation"],
        )
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=font_sizes["annotation"])

    figure_title = _resolve_title(
        title,
        f"Preference Transition Flows ({title_suffix})",
    )
    fig.suptitle(
        figure_title,
        fontsize=font_sizes["title"],
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    plt.show()
    plt.close(fig)

    print("Transition Stay Rates:")
    for label, stay, total in stay_stats:
        pct = stay / total * 100 if total > 0 else 0.0
        print(f"  {label}: {stay}/{total} stayed ({pct:.1f}%)")


def plot_long_term_stability(
    transition_df: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    principle_order: Sequence[str],
    principle_display_order: Sequence[str],
    format_principle_label: FormatLabelFunc,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Visualise wave1 → wave4 stability counts and percentages."""
    if transition_df.empty:
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    counts = pd.crosstab(transition_df["wave1"], transition_df["wave4"], margins=False)
    counts.index = counts.index.map(format_principle_label)
    counts.columns = counts.columns.map(format_principle_label)
    counts = counts.reindex(
        index=principle_display_order,
        columns=principle_display_order,
        fill_value=0,
    )
    percent = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100

    fig, axes = plt.subplots(1, 2, figsize=fig_sizes["double"])

    sns.heatmap(
        counts,
        annot=True,
        fmt="d",
        cmap="Greens",
        ax=axes[0],
        cbar=True,
        linewidths=1.2,
        linecolor="white",
        vmin=0,
        cbar_kws={"shrink": 0.9},
    )
    axes[0].set_title("Counts", fontsize=font_sizes["subtitle"], fontweight="bold", pad=8)

    sns.heatmap(
        percent,
        annot=True,
        fmt=".1f",
        cmap="Greens",
        ax=axes[1],
        cbar=True,
        linewidths=1.2,
        linecolor="white",
        vmin=0,
        vmax=100,
        cbar_kws={"shrink": 0.9},
    )
    axes[1].set_title("Percentages", fontsize=font_sizes["subtitle"], fontweight="bold", pad=8)
    for text in axes[1].texts:
        text.set_text(text.get_text() + "%")

    for ax in axes:
        ax.set_xlabel("Final Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        ax.set_ylabel("Initial Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        ax.set_xticklabels(
            principle_display_order,
            rotation=45,
            ha="right",
            fontsize=font_sizes["annotation"],
        )
        ax.set_yticklabels(
            principle_display_order,
            rotation=0,
            fontsize=font_sizes["annotation"],
        )

    figure_title = _resolve_title(
        title,
        f"Long-Term Preference Stability (Wave 1 → Wave 4) ({title_suffix})",
    )
    fig.suptitle(
        figure_title,
        fontsize=font_sizes["title"],
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    plt.show()
    plt.close(fig)

    print(f"Long-Term Stability (Wave 1 → Wave 4) [{title_suffix}]")
    print("=" * 70)
    total_agents = int(counts.values.sum())
    total_loyal = 0
    for principle_name, display_name in zip(principle_order, principle_display_order):
        starting_count = counts.loc[display_name].sum()
        loyal_count = counts.loc[display_name, display_name]
        loyalty_rate = percent.loc[display_name, display_name]
        total_loyal += loyal_count
        print(
            f"{display_name:25s}: {loyal_count:3.0f}/{starting_count:3.0f} maintained ({loyalty_rate:5.1f}%)"
        )
    overall_loyalty = (total_loyal / total_agents) * 100 if total_agents else 0.0
    print(f"{'OVERALL':25s}: {total_loyal:3.0f}/{total_agents:3.0f} agents ({overall_loyalty:5.1f}%)")


def plot_long_term_margin(
    transition_df: pd.DataFrame,
    *,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    principle_display_order: Sequence[str],
    format_principle_label: FormatLabelFunc,
    title_suffix: str,
    title: Optional[str] = None,
) -> None:
    """Plot counts heatmap with margin totals for long-term stability."""
    if transition_df.empty:
        return

    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    counts = pd.crosstab(transition_df["wave1"], transition_df["wave4"], margins=False)
    counts.index = counts.index.map(format_principle_label)
    counts.columns = counts.columns.map(format_principle_label)
    counts = counts.reindex(
        index=principle_display_order,
        columns=principle_display_order,
        fill_value=0,
    )

    row_totals = counts.sum(axis=1)
    col_totals = counts.sum(axis=0)

    fig, ax = plt.subplots(figsize=fig_sizes["double"])
    sns.heatmap(
        counts,
        annot=True,
        fmt="d",
        cmap="Greens",
        ax=ax,
        cbar=True,
        linewidths=1.2,
        linecolor="white",
        vmin=0,
        cbar_kws={"shrink": 0.9},
    )
    ax.set_xlabel("Final Preference", fontsize=font_sizes["axis_label"], labelpad=8)
    ax.set_ylabel("Initial Preference", fontsize=font_sizes["axis_label"], labelpad=8)
    ax.set_xticklabels(
        principle_display_order,
        rotation=45,
        ha="right",
        fontsize=font_sizes["annotation"],
    )
    ax.set_yticklabels(
        principle_display_order,
        rotation=0,
        fontsize=font_sizes["annotation"],
    )

    num_cols = counts.shape[1]
    for idx, value in enumerate(col_totals):
        ax.text(
            idx + 0.5,
            -0.25,
            f"{int(value)}",
            ha="center",
            va="center",
            fontsize=font_sizes["annotation"] + 1,
            color=colors["dark_gray"],
            fontweight="bold",
        )

    for idx, value in enumerate(row_totals):
        ax.text(
            num_cols + 0.1,
            idx + 0.5,
            f"{int(value)}",
            ha="left",
            va="center",
            fontsize=font_sizes["annotation"] + 1,
            color=colors["dark_gray"],
            fontweight="bold",
        )

    ax.text(
        num_cols + 0.1,
        -0.25,
        "Σ",
        ha="left",
        va="center",
        fontsize=font_sizes["legend"] + 2,
        color=colors["medium_gray"],
        fontweight="bold",
    )

    ax.set_ylim(len(principle_display_order), 0)
    ax.set_xlim(0, num_cols + 0.2)

    figure_title = _resolve_title(
        title,
        f"Long-Term Stability (Counts + Margins) ({title_suffix})",
    )
    fig.suptitle(
        figure_title,
        fontsize=font_sizes["title"],
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    plt.show()
    plt.close(fig)


def plot_long_term_stability_grid(
    transition_datasets: Sequence[Tuple[str, pd.DataFrame]],
    *,
    principle_order: Sequence[str],
    principle_display_order: Sequence[str],
    format_principle_label: FormatLabelFunc,
    title: Optional[str] = None,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
) -> None:
    """Render counts/percentage heatmaps for multiple cohorts in a stacked layout."""
    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    if not transition_datasets:
        print("No cohorts provided for comparison.")
        return

    width, base_height = fig_sizes["double"]
    num_groups = len(transition_datasets)
    fig, axes = plt.subplots(
        nrows=num_groups,
        ncols=2,
        figsize=(width, base_height * num_groups),
        squeeze=False,
    )

    for row_index, (label, transition_df) in enumerate(transition_datasets):
        ax_counts, ax_percent = axes[row_index]

        if transition_df is None or transition_df.empty:
            ax_counts.axis("off")
            ax_percent.axis("off")
            ax_counts.text(
                0.5,
                0.5,
                f"No transition data for {label}.",
                ha="center",
                va="center",
                fontsize=font_sizes["subtitle"],
                color=colors["dark_gray"],
            )
            continue

        counts = pd.crosstab(transition_df["wave1"], transition_df["wave4"], margins=False)
        counts.index = counts.index.map(format_principle_label)
        counts.columns = counts.columns.map(format_principle_label)
        counts = counts.reindex(
            index=principle_display_order,
            columns=principle_display_order,
            fill_value=0,
        )
        percent = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100

        sns.heatmap(
            counts,
            annot=True,
            fmt="d",
            cmap="Greens",
            ax=ax_counts,
            cbar=True,
            linewidths=1.2,
            linecolor="white",
            vmin=0,
            cbar_kws={"shrink": 0.9},
        )
        ax_counts.set_title(
            f"{label}",
            fontsize=font_sizes["subtitle"],
            fontweight="bold",
            pad=8,
        )
        ax_counts.set_xlabel("Final Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        ax_counts.set_ylabel("Initial Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        ax_counts.set_xticklabels(
            principle_display_order,
            rotation=45,
            ha="right",
            fontsize=font_sizes["annotation"],
        )
        ax_counts.set_yticklabels(
            principle_display_order,
            rotation=0,
            fontsize=font_sizes["annotation"],
        )

        sns.heatmap(
            percent,
            annot=True,
            fmt=".1f",
            cmap="Greens",
            ax=ax_percent,
            cbar=True,
            linewidths=1.2,
            linecolor="white",
            vmin=0,
            vmax=100,
            cbar_kws={"shrink": 0.9},
        )
        ax_percent.set_title(
            "Percentages",
            fontsize=font_sizes["subtitle"],
            fontweight="bold",
            pad=8,
        )
        for text in ax_percent.texts:
            text.set_text(text.get_text() + "%")
        ax_percent.set_xlabel("Final Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        ax_percent.set_ylabel("")
        ax_percent.set_xticklabels(
            principle_display_order,
            rotation=45,
            ha="right",
            fontsize=font_sizes["annotation"],
        )
        ax_percent.set_yticklabels(
            [],
            rotation=0,
            fontsize=font_sizes["annotation"],
        )

    if title is not None:
        fig.suptitle(title, fontsize=font_sizes["title"], fontweight="bold", y=0.92)
        fig.tight_layout(rect=[0, 0, 1, 0.90])
    else:
        fig.tight_layout()
    plt.show()
    plt.close(fig)


def plot_long_term_counts_grid(
    transition_datasets: Sequence[Tuple[str, pd.DataFrame]],
    *,
    principle_display_order: Sequence[str],
    format_principle_label: FormatLabelFunc,
    orientation: str = "horizontal",
    title: Optional[str] = None,
    colors: Optional[ColorMap] = None,
    font_sizes: Optional[FontSizeMap] = None,
    fig_sizes: Optional[FigureSizeMap] = None,
    colorbar_mode: str = "per-axis",
    axis_title_fontsize: Optional[float] = None,
) -> None:
    """Render counts-only stability heatmaps for multiple cohorts."""
    colors = colors or BAYREUTH_COLORS
    font_sizes = font_sizes or BAYREUTH_FONT_SIZES
    fig_sizes = fig_sizes or BAYREUTH_FIG_SIZES

    if not transition_datasets:
        print("No cohorts provided for comparison.")
        return

    valid_counts: List[pd.DataFrame] = []
    for label, transition_df in transition_datasets:
        if transition_df is None or transition_df.empty:
            valid_counts.append(pd.DataFrame())
            continue
        counts = pd.crosstab(transition_df["wave1"], transition_df["wave4"], margins=False)
        counts.index = counts.index.map(format_principle_label)
        counts.columns = counts.columns.map(format_principle_label)
        counts = counts.reindex(
            index=principle_display_order,
            columns=principle_display_order,
            fill_value=0,
        )
        valid_counts.append(counts)

    data_max = max((df.values.max() if not df.empty else 0 for df in valid_counts), default=0)

    num_groups = len(transition_datasets)
    orientation = orientation.lower()
    if orientation not in {"horizontal", "vertical"}:
        raise ValueError("orientation must be 'horizontal' or 'vertical'")
    colorbar_mode = colorbar_mode.lower()
    if colorbar_mode not in {"shared", "per-axis"}:
        raise ValueError("colorbar_mode must be 'shared' or 'per-axis'")

    if orientation == "horizontal":
        nrows, ncols = 1, num_groups
        width = fig_sizes["single"][0] * num_groups * 0.5
        height = fig_sizes["single"][1] * 0.9
    else:
        nrows, ncols = num_groups, 1
        width = fig_sizes["single"][0]
        height = fig_sizes["single"][1] * num_groups

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(width, height),
        squeeze=False,
    )
    axes_flat = axes.flatten()

    adjust_kwargs: Dict[str, float] = {}
    if orientation == "horizontal":
        adjust_kwargs["wspace"] = 0.12
    else:
        adjust_kwargs["hspace"] = 0.35

    cbar_ax = None
    colorbar_norm = None
    if colorbar_mode == "shared" and data_max > 0:
        adjust_kwargs["right"] = 0.92
        colorbar_norm = mcolors.Normalize(vmin=0, vmax=data_max if data_max > 0 else 1)

    if adjust_kwargs:
        fig.subplots_adjust(**adjust_kwargs)
    if colorbar_mode == "shared" and data_max > 0:
        cbar_ax = fig.add_axes([0.92, 0.2, 0.02, 0.6])

    for idx, ((label, transition_df), counts, ax) in enumerate(
        zip(transition_datasets, valid_counts, axes_flat)
    ):
        if counts.empty:
            ax.axis("off")
            ax.text(
                0.5,
                0.5,
                f"No transition data for {label}.",
                ha="center",
                va="center",
                fontsize=font_sizes["subtitle"],
                color=colors["dark_gray"],
            )
            continue

        if colorbar_mode == "per-axis":
            show_cbar = data_max > 0
            heatmap_kwargs = {}
        else:
            show_cbar = False
            heatmap_kwargs = {}
        annot_font = max(6, int(font_sizes["annotation"] * 0.9))
        sns.heatmap(
            counts,
            annot=True,
            fmt="d",
            cmap="Greens",
            ax=ax,
            cbar=show_cbar,
            linewidths=1.2,
            linecolor="white",
            vmin=0,
            vmax=data_max if data_max > 0 else None,
            annot_kws={"fontsize": annot_font},
            **heatmap_kwargs,
        )
        ax.set_aspect("equal", adjustable="box")
        matrix_title_size = axis_title_fontsize or font_sizes.get(
            "matrix_title", font_sizes["subtitle"] * 1.5
        )
        ax.set_title(label, fontsize=matrix_title_size, fontweight="bold", pad=8)
        ax.set_xlabel("Final Preference", fontsize=font_sizes["axis_label"], labelpad=8)
        if orientation == "horizontal" and idx > 0:
            ax.set_ylabel("")
            ax.set_yticklabels([])
        else:
            ax.set_ylabel("Initial Preference", fontsize=font_sizes["axis_label"], labelpad=8)
            ax.set_yticklabels(
                principle_display_order,
                rotation=0,
                fontsize=font_sizes["annotation"],
            )
        ax.set_xticklabels(
            principle_display_order,
            rotation=45,
            ha="right",
            fontsize=font_sizes["annotation"],
        )
        if colorbar_mode == "per-axis" and show_cbar:
            ax.collections[0].colorbar.ax.tick_params(labelsize=font_sizes["tick_label"])

        row_totals = counts.sum(axis=1)
        col_totals = counts.sum(axis=0)
        num_cols = counts.shape[1]
        num_rows = counts.shape[0]

        for idx, value in enumerate(col_totals):
            ax.text(
                idx + 0.5,
                -0.3,
                f"{int(value)}",
                ha="center",
                va="center",
                fontsize=font_sizes["annotation"] + 1,
                fontweight="bold",
                color=colors["dark_gray"],
            )

        for idx, value in enumerate(row_totals):
            ax.text(
                num_cols + 0.05,
                idx + 0.5,
                f"{int(value)}",
                ha="left",
                va="center",
                fontsize=font_sizes["annotation"] + 1,
                fontweight="bold",
                color=colors["dark_gray"],
            )

        ax.text(
            num_cols + 0.05,
            -0.3,
            "Σ",
            ha="left",
            va="center",
            fontsize=font_sizes["legend"] + 2,
            fontweight="bold",
            color=colors["medium_gray"],
        )

        ax.set_xlim(-0.01, num_cols + 0.6)
        ax.set_ylim(num_rows, -0.6)

    if colorbar_mode == "shared" and data_max > 0 and cbar_ax is not None:
        sm = ScalarMappable(norm=colorbar_norm, cmap="Greens")
        sm.set_array([])
        fig.colorbar(sm, cax=cbar_ax)

    if title is not None:
        fig.suptitle(title, fontsize=font_sizes["title"], fontweight="bold", y=0.96)
        fig.tight_layout(rect=[0, 0, 0.93 if colorbar_mode == "shared" else 1, 0.92])
    else:
        fig.tight_layout(rect=[0, 0, 0.93 if colorbar_mode == "shared" else 1, 1])
    plt.show()
    plt.close(fig)


__all__ = [
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
    "plot_long_term_counts_grid",
    "plot_long_term_stability_grid",
]
