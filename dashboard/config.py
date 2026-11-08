"""Configuration constants, verified competition anchors, and UI theme styling."""

from __future__ import annotations

from typing import Dict, List, Tuple

# Application metadata
APP_TITLE = "JAEGERS — House Edge Experiment Analytics"
APP_SUBTITLE = "Probabilistic Model Intelligence, Evaluation Provenance & Hypothesis Explorer"
APP_ICON = "🎰"

# Official competition conditions and anchors
CONTEST_CONDITIONS: Tuple[str, ...] = ("stable", "short_history", "drift", "shared_change")
PAYOUT_CLASSES: Tuple[int, ...] = (0, 1, 2, 5, 20)
MAX_OFFICIAL_POINTS: float = 60.0
MAX_CONTEST_POINTS: float = 70.0

# Verified development-exposed anchors from HE-03, HE-09, HE-17
ANCHORS = {
    "champion": {
        "name": "Champion (Stacker + Lag Experts + Regimes)",
        "points": 55.121615,
        "mean_brier": 0.365141,
        "commit": "b78abe75",
    },
    "no_signal": {
        "name": "No-Signal Baseline",
        "points": 55.000142,
        "mean_brier": 0.366250,
        "commit": "a1c037a0",
    },
    "causal": {
        "name": "Strict Causal Filtering",
        "points": 54.643349,
        "mean_brier": 0.365445,
        "commit": "c4d8e901",
    },
    "no_stacker": {
        "name": "Single Model (No GBDT Stacker)",
        "points": 52.836210,
        "mean_brier": 0.380450,
        "commit": "d9e8f7a2",
    },
}

# Color palettes for responsive Plotly charts
COLOR_PALETTE: Dict[str, str] = {
    "bg": "#0e1117",
    "card_bg": "#1e222d",
    "paper_bg": "#131722",
    "text": "#e2e8f0",
    "text_muted": "#94a3b8",
    "grid": "#2a2e39",
    "champion": "#f59e0b",
    "primary": "#3b82f6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "purple": "#8b5cf6",
}

CONDITION_COLORS: Dict[str, str] = {
    "stable": "#3b82f6",        # Blue
    "short_history": "#8b5cf6", # Purple
    "drift": "#f97316",         # Orange
    "shared_change": "#ec4899",  # Pink
}

CLASS_COLORS: Dict[int, str] = {
    0: "#64748b",   # Slate (0x)
    1: "#3b82f6",   # Blue (1x)
    2: "#10b981",   # Emerald (2x)
    5: "#f59e0b",   # Amber (5x)
    20: "#ef4444",  # Crimson / Rare Jackpot (20x)
}


def apply_plotly_dark_theme(fig) -> None:
    """Apply consistent dark styling, layout, and font sizing to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_PALETTE["paper_bg"],
        plot_bgcolor=COLOR_PALETTE["paper_bg"],
        font=dict(color=COLOR_PALETTE["text"], family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=COLOR_PALETTE["grid"],
            font=dict(color=COLOR_PALETTE["text"]),
        ),
    )
    fig.update_xaxes(
        gridcolor=COLOR_PALETTE["grid"],
        zerolinecolor=COLOR_PALETTE["grid"],
    )
    fig.update_yaxes(
        gridcolor=COLOR_PALETTE["grid"],
        zerolinecolor=COLOR_PALETTE["grid"],
    )


def format_points(val: float | None) -> str:
    """Format official points score to 4 decimal places with /60 suffix."""
    if val is None:
        return "N/A"
    return f"{val:.4f} / 60"


def format_brier(val: float | None) -> str:
    """Format Brier score to 6 decimal places."""
    if val is None:
        return "N/A"
    return f"{val:.6f}"


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds into clean human-readable string."""
    if seconds is None:
        return "0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    rem_sec = seconds % 60
    return f"{minutes}m {rem_sec:.0f}s"
