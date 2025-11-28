"""Top-level layout assembly for the dashboard."""
from __future__ import annotations

from dash import dcc, html

from .theme import THEME
from .live_layout import build_live_layout
from .review_layout import build_review_layout
from .events_layout import build_events_layout


def build_root_layout():
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Sleep monitoring dashboard", className="page-title"),
                            html.Div(
                                "Live bedside view, nightly reviews, and per-event investigation in one place.",
                                className="page-subtitle",
                            ),
                        ],
                        className="page-header",
                    ),
                    dcc.Tabs(
                        id="tabs",
                        value="tab-live",
                        children=[
                            dcc.Tab(
                                label="Live",
                                value="tab-live",
                                className="tab",
                                selected_className="tab--selected",
                            ),
                            dcc.Tab(
                                label="Review",
                                value="tab-review",
                                className="tab",
                                selected_className="tab--selected",
                            ),
                            dcc.Tab(
                                label="Events",
                                value="tab-events",
                                className="tab",
                                selected_className="tab--selected",
                            ),
                        ],
                        colors={
                            "border": THEME["border"],
                            "primary": THEME["accent"],
                            "background": THEME["bg"],
                        },
                        style={"borderBottom": f"1px solid {THEME['border']}"},
                        className="tabs-container",
                    ),
                    html.Div(id="tab-content"),
                ]
            ),
        ],
        className="app-container",
    )


def resolve_tab_layout(tab_value: str, sleep_dates: list) -> html.Div:
    if tab_value == "tab-live":
        return build_live_layout()
    if tab_value == "tab-review":
        return build_review_layout(sleep_dates)
    if tab_value == "tab-events":
        return build_events_layout(sleep_dates)
    return build_live_layout()
