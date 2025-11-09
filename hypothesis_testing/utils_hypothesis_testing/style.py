"""Centralised Bayreuth visual identity helpers for hypothesis notebooks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

ColorMap = Dict[str, str]
FontSizeMap = Dict[str, int]
FigureSizeMap = Dict[str, tuple[float, float]]

BAYREUTH_COLORS: ColorMap = {
    "primary_green": "#009260",
    "primary_blue": "#48535A",
    "primary_orange": "#7F8990",
    "accent_1": "#EBEBE4",
    "dark_gray": "#48535A",
    "medium_gray": "#7F8990",
    "light_gray": "#EBEBE4",
    "background": "#FFFFFF",
    "stayed": "#009260",
    "switched": "#48535A",
    "highlight": "#009260",
}

PRINCIPLE_COLORS: ColorMap = {
    "Max Avg Income": BAYREUTH_COLORS["primary_green"],
    "Max Avg + Floor": BAYREUTH_COLORS["primary_blue"],
    "Max Avg + Range": BAYREUTH_COLORS["primary_orange"],
    "Max Floor": BAYREUTH_COLORS["accent_1"],
}

PRINCIPLE_DISPLAY_NAMES: Dict[str, str] = {
    "Max Avg Income": "Max. Avg. Income",
    "Max Avg + Floor": "Max. Avg. + Floor",
    "Max Avg + Range": "Max. Avg. + Range",
    "Max Floor": "Max. Floor",
    "Failure": "Failure",
    "None": "None",
}

PRINCIPLE_ORDER: List[str] = [
    "Max Floor",
    "Max Avg Income",
    "Max Avg + Floor",
    "Max Avg + Range",
]

BAYREUTH_FONT_SIZES: FontSizeMap = {
    "title": 14,
    "subtitle": 12,
    "axis_label": 11,
    "tick_label": 10,
    "legend": 10,
    "annotation": 9,
}

FONT_FAMILY = "Latin Modern Roman"


def _register_latin_modern_fonts() -> None:
    """Register Latin Modern Roman fonts from local directory."""
    font_dir = Path(__file__).parent / "fonts"
    if not font_dir.exists():
        return  # Fonts directory doesn't exist; use system default

    for font_file in font_dir.glob("*.otf"):
        try:
            fm.fontManager.addfont(str(font_file))
        except Exception:
            pass  # Silently skip fonts that fail to load

BAYREUTH_FIG_SIZES: FigureSizeMap = {
    "single": (9, 5),
    "double": (12, 5),
    "triple": (14, 5),
    "wide_single": (11, 5),
    "tall": (9, 7),
}

GRID_ALPHA = 0.2
GRID_LINEWIDTH = 0.6
GRID_LINESTYLE = "-"


def _palette_hex() -> List[str]:
    palette_order: Iterable[str] = [
        BAYREUTH_COLORS["primary_green"],
        BAYREUTH_COLORS["primary_blue"],
        BAYREUTH_COLORS["primary_orange"],
        BAYREUTH_COLORS["accent_1"],
    ]
    return list(dict.fromkeys(palette_order))


def apply_bayreuth_theme() -> None:
    """Apply rcParams and seaborn defaults for the Bayreuth identity."""
    _register_latin_modern_fonts()
    plt.rcParams.update(
        {
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "figure.facecolor": BAYREUTH_COLORS["background"],
            "axes.facecolor": BAYREUTH_COLORS["background"],
            "axes.edgecolor": BAYREUTH_COLORS["medium_gray"],
            "axes.linewidth": 1.0,
            "axes.labelsize": BAYREUTH_FONT_SIZES["axis_label"],
            "axes.titlesize": BAYREUTH_FONT_SIZES["title"],
            "axes.titleweight": "bold",
            "axes.labelweight": "normal",
            "axes.labelcolor": BAYREUTH_COLORS["dark_gray"],
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.alpha": GRID_ALPHA,
            "grid.linewidth": GRID_LINEWIDTH,
            "grid.linestyle": GRID_LINESTYLE,
            "grid.color": BAYREUTH_COLORS["light_gray"],
            "xtick.labelsize": BAYREUTH_FONT_SIZES["tick_label"],
            "ytick.labelsize": BAYREUTH_FONT_SIZES["tick_label"],
            "xtick.color": BAYREUTH_COLORS["dark_gray"],
            "ytick.color": BAYREUTH_COLORS["dark_gray"],
            "legend.fontsize": BAYREUTH_FONT_SIZES["legend"],
            "legend.framealpha": 0.95,
            "legend.edgecolor": BAYREUTH_COLORS["medium_gray"],
            "font.family": "sans-serif",
            "font.sans-serif": [FONT_FAMILY],
            "text.color": BAYREUTH_COLORS["dark_gray"],
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    sns.set_theme(style="whitegrid", context="paper", palette=_palette_hex())


def format_principle_label(name: str) -> str:
    """Return display-friendly label for a principle name."""
    return PRINCIPLE_DISPLAY_NAMES.get(name, name)


def format_principle_labels(labels: Iterable[str]) -> List[str]:
    """Vectorised helper to format a sequence of principle names."""
    return [format_principle_label(label) for label in labels]


__all__ = [
    "BAYREUTH_COLORS",
    "PRINCIPLE_COLORS",
    "PRINCIPLE_DISPLAY_NAMES",
    "PRINCIPLE_ORDER",
    "BAYREUTH_FONT_SIZES",
    "BAYREUTH_FIG_SIZES",
    "FONT_FAMILY",
    "apply_bayreuth_theme",
    "format_principle_label",
    "format_principle_labels",
]
