"""Effect size helpers for contingency tables used across hypothesis analyses."""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import chi2_contingency


NDArrayFloat = NDArray[np.float64]


def _ensure_2d(contingency: ArrayLike) -> NDArrayFloat:
    """Cast input to a 2D float array and raise if the shape is invalid."""
    table = np.asarray(contingency, dtype=float)
    if table.ndim != 2:
        raise ValueError("contingency must be a 2D array")
    return table


def _prune_empty_rows_cols(contingency: ArrayLike) -> NDArrayFloat:
    """Drop all-zero rows and columns to avoid degenerate chi-square calculations."""
    table = _ensure_2d(contingency)
    if table.size == 0:
        return table

    row_mask = table.sum(axis=1) > 0
    col_mask = table.sum(axis=0) > 0

    if row_mask.all() and col_mask.all():
        return table
    pruned = table[row_mask][:, col_mask]
    if pruned.size == 0:
        # Everything was zero; return an empty 0x0 table to signal no information.
        return np.zeros((0, 0), dtype=float)
    return pruned


def cramers_v(contingency: ArrayLike, *, correction: bool = False) -> float:
    """
    Compute standard Cramér's V for an arbitrary contingency table.

    Args:
        contingency: Raw counts; zero-only rows/columns are dropped automatically.
        correction: Whether to use Yates' continuity correction (disabled by default).

    Returns:
        The Cramér's V effect size in [0, 1].
    """
    table = _prune_empty_rows_cols(contingency)
    if table.size == 0:
        return 0.0

    n = table.sum()
    if n <= 0:
        return 0.0

    r, c = table.shape
    df_min = min(r - 1, c - 1)
    if df_min <= 0:
        return 0.0

    chi2, _, _, _ = chi2_contingency(table, correction=correction)
    return float(np.sqrt((chi2 / n) / df_min))


def bias_corrected_cramers_v(contingency: ArrayLike, *, correction: bool = False) -> float:
    """
    Bergsma & Wicher (2013) bias-corrected Cramér's V.

    Applies finite-sample correction to phi^2 and adjusts effective table
    dimensions so the corrected measure can still reach 1.
    """
    table = _prune_empty_rows_cols(contingency)
    if table.size == 0:
        return 0.0

    n = table.sum()
    if n <= 1:
        return 0.0

    r, c = table.shape
    if min(r - 1, c - 1) <= 0:
        return 0.0

    chi2, _, _, _ = chi2_contingency(table, correction=correction)
    phi2 = chi2 / n
    r1, c1 = r - 1, c - 1

    phi2_corr = max(0.0, phi2 - (r1 * c1) / (n - 1))
    r_corr = r - (r1 * r1) / (n - 1)
    c_corr = c - (c1 * c1) / (n - 1)

    denom = min(r_corr - 1.0, c_corr - 1.0)
    if denom <= 0.0:
        return 0.0

    return float(np.sqrt(phi2_corr / denom))


def bootstrap_cramers_v(
    contingency: ArrayLike,
    *,
    n_bootstrap: int = 5000,
    confidence_level: float = 0.95,
    bias_corrected: bool = True,
    correction: bool = False,
    seed: int | None = 123,
) -> Tuple[NDArrayFloat, float, float]:
    """
    Non-parametric bootstrap for Cramér's V using a multinomial draw.

    Args:
        contingency: Raw counts; zero-only rows/columns are dropped automatically.
        n_bootstrap: Number of bootstrap replicates.
        confidence_level: Percentile CI coverage in (0, 1).
        bias_corrected: Whether to use the bias-corrected statistic.
        correction: Carry through to chi-square computation if Yates correction is desired.
        seed: Random seed for reproducibility.

    Returns:
        A tuple of (bootstrap_values, ci_lower, ci_upper).
    """
    if not (0.0 < confidence_level < 1.0):
        raise ValueError("confidence_level must be in (0, 1)")
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be positive")

    table = _prune_empty_rows_cols(contingency)
    n = int(table.sum())
    if n <= 0:
        return np.array([], dtype=float), 0.0, 0.0

    p = (table / n).ravel()
    if np.any(p < 0):
        raise ValueError("contingency table cannot contain negative counts")

    rng = np.random.default_rng(seed)
    vs = np.empty(n_bootstrap, dtype=float)
    shape = table.shape

    for idx in range(n_bootstrap):
        counts = rng.multinomial(n, p).reshape(shape)
        if bias_corrected:
            vs[idx] = bias_corrected_cramers_v(counts, correction=correction)
        else:
            vs[idx] = cramers_v(counts, correction=correction)

    alpha = 1.0 - confidence_level
    lo, hi = np.quantile(vs, [alpha / 2.0, 1.0 - alpha / 2.0])
    return vs, float(lo), float(hi)


__all__ = [
    "cramers_v",
    "bias_corrected_cramers_v",
    "bootstrap_cramers_v",
]
