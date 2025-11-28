"""Layout for the Events tab."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from dash import dcc, html

from .utils import metric_card


def build_events_layout(sleep_dates: Iterable[date]) -> html.Div:
    options = [{"label": d.strftime("%Y-%m-%d"), "value": d.isoformat()} for d in sleep_dates]
    default_value = options[0]["value"] if options else None

    return html.Div(
        [
            html.Div(
                [
                    html.H2("Event navigation", className="section-title"),
                    html.P(
                        "Step through detected desaturations with context windows and clear highlights.",
                        className="section-desc",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Night to inspect", className="control-label"),
                            html.Div(
                                "Choose a recorded sleep session. Events are detected using the threshold and duration below.",
                                className="control-hint",
                            ),
                            dcc.Dropdown(
                                id="events-sleep-date",
                                options=options,
                                value=default_value,
                                placeholder="Select sleep date",
                                className="dropdown-dark",
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Desaturation threshold (%)", className="control-label"),
                            html.Div(
                                "SpO₂ values below this line are considered part of an event.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="events-threshold",
                                type="number",
                                value=90,
                                step=1,
                                min=50,
                                max=100,
                                placeholder="SpO₂ threshold",
                                className="input-dark",
                                style={"width": "100%", "padding": "10px"},
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Minimum event duration (sec)", className="control-label"),
                            html.Div(
                                "Ignore brief dips and keep focus on clinically meaningful events.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="events-duration",
                                type="number",
                                value=10,
                                step=1,
                                min=1,
                                placeholder="Minimum duration",
                                className="input-dark",
                                style={"width": "100%", "padding": "10px"},
                            ),
                        ],
                        className="control-block",
                    ),
                ],
                className="controls-panel",
            ),
            html.Div(
                [
                    metric_card("events-current", "Current index", "Navigate via arrows or slider."),
                    metric_card("events-count", "Events detected", "Total desaturations with current settings."),
                    metric_card("events-window", "Context window", "10 minutes before and after the event start."),
                ],
                className="summary-grid",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Button("⟵ Prev", id="events-prev", className="nav-button"),
                            html.Button("Next ⟶", id="events-next", className="nav-button"),
                        ],
                        className="nav-buttons",
                    ),
                    dcc.Slider(
                        id="events-index",
                        min=0,
                        max=0,
                        step=1,
                        value=0,
                        marks={0: "0"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="slider-row",
            ),
            html.Div(id="events-selected-summary", className="summary-card"),
            dcc.Graph(
                id="events-graph",
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                style={"height": "520px"},
            ),
        ],
        className="tab-container",
    )
