"""Layout for the Review tab."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from dash import dcc, html, dash_table

from .theme import THEME

from .theme import THEME


def build_review_layout(sleep_dates: Iterable[date]) -> html.Div:
    options = [{"label": d.strftime("%Y-%m-%d"), "value": d.isoformat()} for d in sleep_dates]
    default_value = options[0]["value"] if options else None

    return html.Div(
        [
            html.Div(
                [
                    html.H2("Nightly review", className="section-title"),
                    html.P(
                        "Browse recorded nights, review desaturation metrics, and zoom into periods of concern.",
                        className="section-desc",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Night to review", className="control-label"),
                            html.Div(
                                "Pick one sleep session. The newest night is pre-selected when available.",
                                className="control-hint",
                            ),
                            dcc.Dropdown(
                                id="review-sleep-date",
                                options=options,
                                value=default_value,
                                placeholder="Select sleep date",
                                className="dropdown-dark",
                                style={"backgroundColor": THEME["bg"], "color": THEME["text"]},
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Desaturation threshold (%)", className="control-label"),
                            html.Div(
                                "Values below this level count toward time below threshold and ODI.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="review-threshold",
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
                                "Shortest SpO₂ drop to consider a desaturation event.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="review-duration",
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
                    html.Div(
                        [
                            html.Label("Display options", className="control-label"),
                            html.Div(
                                "Toggle heart rate visibility and highlight detected events on the graphs.",
                                className="control-hint",
                            ),
                            dcc.Checklist(
                                id="review-options",
                                options=[
                                    {"label": "Show heart rate", "value": "hr"},
                                    {"label": "Show detected events", "value": "events"},
                                ],
                                value=["hr", "events"],
                                inline=False,
                                inputStyle={"margin-right": "0.25rem"},
                                labelStyle={"display": "block", "marginBottom": "6px", "color": THEME["text"]},
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Signal smoothing", className="control-label"),
                            html.Div(
                                "Apply a moving average (seconds). Set to 0 to keep the raw traces only.",
                                className="control-hint",
                            ),
                            dcc.Slider(
                                id="review-smoothing-sec",
                                min=0,
                                max=120,
                                step=5,
                                value=30,
                                marks={0: "off", 15: "15 s", 30: "30", 60: "60", 120: "120"},
                                tooltip={"placement": "bottom"},
                            ),
                        ],
                        className="control-block",
                    ),
                ],
                className="controls-panel",
            ),
            html.Div(id="review-summary", className="summary-card"),
            html.Div(
                [
                    html.H3("Overlaid overnight view", className="section-title"),
                    html.P(
                        "SpO₂ with optional heart rate shown on a shared time axis. Use the rangeslider to zoom.",
                        className="section-desc",
                    ),
                ]
            ),
            dcc.Graph(
                id="review-graph",
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                style={"height": "520px"},
            ),
            html.Div(
                [
                    html.H3("Stacked overnight view", className="section-title"),
                    html.P(
                        "Separate axes keep both signals clear while staying synchronized in time.",
                        className="section-desc",
                    ),
                ]
            ),
            dcc.Graph(
                id="review-graph-stacked",
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                style={"height": "520px"},
            ),
            html.Div(
                [
                    html.H3("Detected desaturation events", className="section-title"),
                    html.P(
                        "Each row marks a detected event using the current threshold and duration settings.",
                        className="section-desc",
                    ),
                ]
            ),
            dash_table.DataTable(
                id="review-events",
                columns=[
                    {"name": "Start (local)", "id": "start_time_local"},
                    {"name": "End (local)", "id": "end_time_local"},
                    {"name": "Duration (s)", "id": "duration_sec"},
                    {"name": "Nadir SpO₂", "id": "nadir_spo2"},
                    {"name": "Mean SpO₂", "id": "mean_spo2"},
                ],
                style_header={
                    "backgroundColor": "#111827",
                    "color": THEME["text"],
                    "border": "none",
                    "fontWeight": "600",
                },
                style_data={
                    "backgroundColor": THEME["bg"],
                    "color": THEME["text"],
                    "border": "none",
                },
                style_table={"overflowX": "auto", "backgroundColor": THEME["bg"]},
                style_cell={"padding": "0.6rem", "fontSize": 13},
            ),
        ],
        className="tab-container",
    )
