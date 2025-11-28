"""Reusable UI helpers for the dashboard."""
from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Sequence, Tuple

import plotly.graph_objects as go
from dash import html

from .theme import THEME


def metric_card(target_id: str, title: str, helper: str) -> html.Div:
    """Reusable metric card with label, placeholder value, and helper text."""

    return html.Div(
        [
            html.Div(title, className="metric-label"),
            html.Div(id=target_id, className="metric-value"),
            html.Div(helper, className="metric-help"),
        ],
        className="metric-card",
    )


def format_timestamp_human(dt_value: datetime | None) -> str:
    """Return a readable timestamp for end users."""

    if not isinstance(dt_value, datetime):
        return "—"
    return dt_value.strftime("%b %d, %Y · %I:%M:%S %p")


def format_percentage(value: float | int | None, decimals: int = 2) -> str:
    """Format numeric values as a percentage string with fallback."""

    if value is None:
        return "n/a"
    return f"{value:.{decimals}f} %"


def apply_gap_breaks(
    x_series: Sequence[datetime],
    y_series: Sequence,
    max_gap_seconds: float | None = None,
) -> Tuple[list, list]:
    """Insert break markers when gaps exceed a threshold so lines do not connect."""

    x_list = list(x_series)
    y_list = list(y_series)

    if len(x_list) < 2:
        return x_list, y_list

    deltas = [
        (x_list[i] - x_list[i - 1]).total_seconds() for i in range(1, len(x_list))
    ]

    typical_spacing = median(deltas)
    gap_threshold = max_gap_seconds or max(typical_spacing * 3, 60)

    new_x = [x_list[0]]
    new_y = [y_list[0]]

    for i in range(1, len(x_list)):
        if deltas[i - 1] > gap_threshold:
            new_x.append(x_list[i - 1])
            new_y.append(None)
        new_x.append(x_list[i])
        new_y.append(y_list[i])

    return new_x, new_y


def empty_figure(title: str) -> go.Figure:
    """Create a dark-themed empty figure with a centered title."""

    fig = go.Figure()
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["bg"],
        font=dict(color=THEME["text"]),
    )
    return fig
