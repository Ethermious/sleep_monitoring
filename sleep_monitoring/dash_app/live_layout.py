"""Layout for the Live tab."""
from __future__ import annotations

from dash import dcc, html

from .theme import THEME
from .utils import metric_card


def build_live_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id="live-interval", interval=2000, n_intervals=0),
            html.Div(
                [
                    html.H2("Live monitoring", className="section-title"),
                    html.P(
                        "Follow live SpO₂ and HR with a calm, stable view. Choose how much "
                        "history to keep on screen and whether to smooth noisy signals.",
                        className="section-desc",
                    ),
                ]
            ),
            html.Div(
                [
                    metric_card(
                        "live-spo2", "Current SpO₂", "Latest measured oxygen saturation."
                    ),
                    metric_card(
                        "live-hr", "Current heart rate", "Beats per minute from the latest sample."
                    ),
                    metric_card(
                        "live-battery", "Sensor battery", "Reported battery level from the device."
                    ),
                    metric_card(
                        "live-last-sample",
                        "Last received sample",
                        "Time since the most recent data point arrived.",
                    ),
                ],
                className="live-metrics",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Display window", className="control-label"),
                            html.Div(
                                "How much recent data to keep visible (minutes).",
                                className="control-hint",
                            ),
                            dcc.Slider(
                                id="live-window-min",
                                min=10,
                                max=180,
                                step=10,
                                value=30,
                                marks={10: "10 min", 30: "30", 60: "60", 120: "120", 180: "180"},
                                tooltip={"placement": "bottom"},
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Smoothing", className="control-label"),
                            html.Div(
                                "Optional moving average to reduce jitter. 0 turns smoothing off.",
                                className="control-hint",
                            ),
                            dcc.Slider(
                                id="live-smoothing-sec",
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
                    html.Div(
                        [
                            html.Label("Signals & alerting", className="control-label"),
                            html.Div(
                                "Pick which series to show and set the SpO₂ safety threshold.",
                                className="control-hint",
                            ),
                            dcc.Checklist(
                                id="live-series",
                                options=[
                                    {"label": "SpO₂", "value": "spo2"},
                                    {"label": "Heart rate", "value": "hr"},
                                ],
                                value=["spo2", "hr"],
                                inline=True,
                                inputStyle={"margin-right": "0.25rem"},
                                labelStyle={"marginRight": "12px", "color": THEME["text"]},
                            ),
                            html.Label(
                                "SpO₂ alert threshold", className="control-label", style={"marginTop": "8px"}
                            ),
                            html.Div(
                                "Values below this line will be highlighted as potential desaturations.",
                                className="control-hint",
                            ),
                            dcc.Slider(
                                id="live-threshold",
                                min=80,
                                max=95,
                                step=1,
                                value=90,
                                marks={80: "80%", 85: "85", 90: "90", 95: "95"},
                                tooltip={"placement": "bottom"},
                            ),
                        ],
                        className="control-block",
                    ),
                ],
                className="controls-panel",
            ),
            html.Div(
                [
                    html.H3("Overlaid view", className="section-title"),
                    html.P(
                        "SpO₂ and HR share a common time axis for quick correlation. Hover to inspect precise values.",
                        className="section-desc",
                    ),
                ]
            ),
            dcc.Graph(
                id="live-graph",
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                style={"height": "520px"},
            ),
            html.Div(
                [
                    html.H3("Stacked view", className="section-title"),
                    html.P(
                        "Independent scales keep each signal legible while staying aligned in time.",
                        className="section-desc",
                    ),
                ]
            ),
            dcc.Graph(
                id="live-graph-stacked",
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                style={"height": "520px"},
            ),
        ],
        className="tab-container",
    )
