"""Dash UI for live monitoring and review.

This module keeps the data contracts with :mod:`sleep_monitoring.config`,
:mod:`sleep_monitoring.data_io`, and :mod:`sleep_monitoring.metrics` while
offering a clearer, more guided experience across Live, Review, and Events
workflows. The layout favors a dark, high-contrast theme and descriptive
controls so clinicians and lay users can quickly understand what they are
adjusting.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import dash
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, Input, Output, State, dcc, html, dash_table
from dash.exceptions import PreventUpdate



from sleep_monitoring import config, data_io, metrics


# ---------------------------------------------------------------------------
# VISUAL DESIGN
# ---------------------------------------------------------------------------
THEME = {
    "bg": "#020617",
    "panel": "#0b1224",
    "card": "#0f172a",
    "text": "#e5e7eb",
    "muted": "#9ca3af",
    "border": "#1f2937",
    "accent": "#3b82f6",
}

# Color palette for consistent grouping
COLORS = {
    # SpO2 family (green)
    "spo2_raw": "#22c55e",       # SpO2 raw
    "spo2_ma": "#16a34a",        # SpO2 moving average

    # Heart rate family (blue)
    "hr_raw": "#3b82f6",         # HR raw
    "hr_ma": "#60a5fa",          # HR moving average

    # SpO2 threshold line
    "spo2_threshold": "#c2d81d",

    # Event markers (desats, etc.)
    "event_marker": "#f97316",   # orange, stands out
}

app = Dash(__name__)
app.title = "Sleep Monitoring"
server = app.server
# Allow callbacks whose components only appear inside certain tabs
app.config.suppress_callback_exceptions = True


def _metric_card(target_id: str, title: str, helper: str) -> html.Div:
    """Reusable metric card with label, value placeholder, and helper text."""

    return html.Div(
        [
            html.Div(title, className="metric-label"),
            html.Div(id=target_id, className="metric-value"),
            html.Div(helper, className="metric-help"),
        ],
        className="metric-card",
    )


# ---------------------------------------------------------------------------
# TAB LAYOUTS
# ---------------------------------------------------------------------------

def _live_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id="live-interval", interval=2000, n_intervals=0),

            html.Div(
                [
                    html.H2("Live monitoring", className="section-title"),
                    html.P(
                        "Follow live SpO₂ and HR with a calm, stable view. "
                        "Choose how much history to keep on screen and whether "
                        "to smooth noisy signals.",
                        className="section-desc",
                    ),
                ]
            ),

            # Top metric strip
            html.Div(
                [
                    _metric_card("live-spo2", "Current SpO₂", "Latest measured oxygen saturation."),
                    _metric_card("live-hr", "Current heart rate", "Beats per minute from the latest sample."),
                    _metric_card("live-battery", "Sensor battery", "Reported battery level from the device."),
                    _metric_card(
                        "live-last-sample",
                        "Last received sample",
                        "Time since the most recent data point arrived.",
                    ),
                ],
                className="live-metrics",
            ),

            # Controls row
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
                                marks={
                                    10: "10 min",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                    180: "180",
                                },
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
                                marks={
                                    0: "off",
                                    15: "15 s",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                },
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
                            html.Label("SpO₂ alert threshold", className="control-label", style={"marginTop": "8px"}),
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
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
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
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "520px"},
            ),
        ],
        className="tab-container",
    )


def _review_layout() -> html.Div:
    sleep_dates = data_io.list_sleep_dates()
    options = [
        {"label": d.strftime("%Y-%m-%d"), "value": d.isoformat()} for d in sleep_dates
    ]
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
                                style={
                                    "backgroundColor": THEME["bg"],
                                    "color": THEME["text"],
                                },
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
                                    {"label": "Highlight desaturation events", "value": "events"},
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
                                marks={
                                    0: "off",
                                    15: "15 s",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                },
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
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
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
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
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
                style_table={
                    "overflowX": "auto",
                    "backgroundColor": THEME["bg"],
                },
                style_cell={
                    "padding": "0.6rem",
                    "fontSize": 13,
                },
            ),
        ],
        className="tab-container",
    )


def _events_layout() -> html.Div:
    """Events tab: cycle through desaturation events with a slider + arrows."""
    sleep_dates = data_io.list_sleep_dates()
    options = [
        {"label": d.strftime("%Y-%m-%d"), "value": d.isoformat()} for d in sleep_dates
    ]
    default_value = options[0]["value"] if options else None

    return html.Div(
        [
            html.Div(
                [
                    html.H2("Event navigator", className="section-title"),
                    html.P(
                        "Step through each detected desaturation event with a focused context window and summary card.",
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
                                "Choose a recorded night before stepping through individual events.",
                                className="control-hint",
                            ),
                            dcc.Dropdown(
                                id="events-sleep-date",
                                options=options,
                                value=default_value,
                                placeholder="Select sleep date",
                                className="dropdown-dark",
                                style={
                                    "backgroundColor": THEME["bg"],
                                    "color": THEME["text"],
                                },
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("SpO₂ threshold (%)", className="control-label"),
                            html.Div(
                                "Events are detected when SpO₂ stays below this line for the minimum duration.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="events-threshold",
                                type="number",
                                value=90,
                                step=1,
                                min=50,
                                max=100,
                                placeholder="Desat threshold",
                                className="input-dark",
                                style={"width": "100%", "padding": "10px"},
                            ),
                        ],
                        className="control-block",
                    ),
                    html.Div(
                        [
                            html.Label("Minimum duration (sec)", className="control-label"),
                            html.Div(
                                "Ignore brief dips shorter than this duration.",
                                className="control-hint",
                            ),
                            dcc.Input(
                                id="events-duration",
                                type="number",
                                value=10,
                                step=1,
                                min=1,
                                placeholder="Min duration (s)",
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
                    html.Label("Event selector", className="control-label"),
                    html.Div(
                        "Use the arrow buttons for discrete navigation or drag the slider handle to jump to an index.",
                        className="control-hint",
                    ),
                    html.Div(
                        [
                            html.Button(
                                "◀",
                                id="events-prev",
                                n_clicks=0,
                                style={"padding": "8px 12px", "fontSize": "16px"},
                                title="Previous event",
                            ),
                            html.Div(
                                dcc.Slider(
                                    id="events-index",
                                    min=0,
                                    max=0,
                                    step=1,
                                    value=0,
                                    marks={0: "0"},
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                ),
                                style={"flex": 1, "padding": "0 8px"},
                            ),
                            html.Button(
                                "▶",
                                id="events-next",
                                n_clicks=0,
                                style={"padding": "8px 12px", "fontSize": "16px"},
                                title="Next event",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                        },
                    ),
                ],
                className="control-block",
                style={"marginBottom": "12px"},
            ),

            html.Div(
                id="events-selected-summary",
                className="summary-card",
                style={"marginBottom": "12px"},
            ),

            # Event-focused stacked graph (full night with zoom)
            dcc.Graph(
                id="events-graph",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "520px"},
            ),
        ],
        className="tab-container",
    )


# ---------------------------------------------------------------------------
# APP LAYOUT
# ---------------------------------------------------------------------------

app.layout = html.Div(
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
                            label="Live", value="tab-live", className="tab", selected_className="tab--selected"
                        ),
                        dcc.Tab(
                            label="Review", value="tab-review", className="tab", selected_className="tab--selected"
                        ),
                        dcc.Tab(
                            label="Events", value="tab-events", className="tab", selected_className="tab--selected"
                        ),
                    ],
                    colors={
                        "border": "#111827",
                        "primary": "#3b82f6",
                        "background": "#020617",
                    },
                    style={"borderBottom": "1px solid #111827"},
                    className="tabs-container",
                ),
                html.Div(id="tab-content"),
            ]
        ),
    ],
    className="app-container",
)


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab_value: str):
    if tab_value == "tab-live":
        return _live_layout()
    if tab_value == "tab-review":
        return _review_layout()
    if tab_value == "tab-events":
        return _events_layout()
    return _live_layout()


# ---------------------------------------------------------------------------
# LIVE TAB CALLBACK
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("live-spo2", "children"),
        Output("live-hr", "children"),
        Output("live-battery", "children"),
        Output("live-last-sample", "children"),
        Output("live-graph", "figure"),
        Output("live-graph-stacked", "figure"),
    ],
    [
        Input("live-interval", "n_intervals"),
        Input("live-window-min", "value"),
        Input("live-smoothing-sec", "value"),
        Input("live-series", "value"),
        Input("live-threshold", "value"),
    ],
)
def update_live(_, window_min, smoothing_sec, series, spo2_threshold):
    sleep_date = data_io.compute_sleep_date(datetime.now(timezone.utc))
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No live data yet",
            template="plotly_dark",
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font=dict(color="#e5e7eb"),
        )
        return (
            "SpO₂: --",
            "HR: --",
            "Battery: --",
            "Last sample: --",
            empty_fig,
            empty_fig,
        )

    latest = df.iloc[-1]
    now_utc = datetime.now(timezone.utc)
    time_since = now_utc - latest["timestamp_utc"]

    window_min = window_min or 30
    window_start = now_utc - timedelta(minutes=int(window_min))
    mask = df["timestamp_utc"] >= window_start
    window_df = df[mask].copy().sort_values("timestamp_utc")

    # Overlaid figure (existing behavior)
    fig_overlay = make_subplots(specs=[[{"secondary_y": True}]])

    # Raw signals (dimmed)
    if "spo2" in (series or []):
        fig_overlay.add_trace(
            go.Scatter(
                x=window_df["timestamp_local"],
                y=window_df["spo2"],
                name="SpO₂ (raw)",
                mode="lines+markers",
                opacity=0.4,
                line=dict(color=COLORS["spo2_raw"]),
                marker=dict(color=COLORS["spo2_raw"]),
            ),
            secondary_y=False,
        )

    if "hr" in (series or []):
        fig_overlay.add_trace(
            go.Scatter(
                x=window_df["timestamp_local"],
                y=window_df["hr"],
                name="HR (raw)",
                mode="lines+markers",
                opacity=0.4,
                line=dict(color=COLORS["hr_raw"]),
                marker=dict(color=COLORS["hr_raw"]),
            ),
            secondary_y=True,
        )

    # Moving average smoothing
    spo2_ma = None
    hr_ma = None
    if smoothing_sec and smoothing_sec > 0 and len(window_df) > 1:
        smoothing_sec = int(smoothing_sec)
        w = window_df.set_index("timestamp_utc")
        spo2_ma = w["spo2"].rolling(f"{smoothing_sec}s").mean()
        hr_ma = w["hr"].rolling(f"{smoothing_sec}s").mean()


        if "spo2" in (series or []):
            fig_overlay.add_trace(
                go.Scatter(
                    x=window_df["timestamp_local"],
                    y=spo2_ma,
                    name=f"SpO₂ {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["spo2_ma"], width=2),
                ),
                secondary_y=False,
            )

        if "hr" in (series or []):
            fig_overlay.add_trace(
                go.Scatter(
                    x=window_df["timestamp_local"],
                    y=hr_ma,
                    name=f"HR {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["hr_ma"], width=2),
                ),
                secondary_y=True,
            )

    spo2_threshold = spo2_threshold or 90
    fig_overlay.add_hline(
        y=spo2_threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"{spo2_threshold} % threshold",
        annotation_position="bottom right",
    )

    fig_overlay.update_layout(
        title=f"Live SpO₂ / HR - last {int(window_min)} min",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=100),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0
        ),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
        uirevision="live",
        height=520,
        xaxis=dict(
            type="date",
            rangeslider=dict(visible=False),
        ),
    )
    fig_overlay.update_yaxes(title_text="SpO₂ (%)", secondary_y=False, range=[70, 100])
    fig_overlay.update_yaxes(title_text="HR (bpm)", secondary_y=True)

    # Stacked two-row figure
    fig_stacked = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.05,
    )

    # Row 1: SpO2
    if "spo2" in (series or []):
        fig_stacked.add_trace(
            go.Scatter(
                x=window_df["timestamp_local"],
                y=window_df["spo2"],
                name="SpO₂ (raw)",
                mode="lines+markers",
                opacity=0.4,
                line=dict(color=COLORS["spo2_raw"]),
                marker=dict(color=COLORS["spo2_raw"]),
            ),
            row=1,
            col=1,
        )
        if spo2_ma is not None:
            fig_stacked.add_trace(
                go.Scatter(
                    x=window_df["timestamp_local"],
                    y=spo2_ma,
                    name=f"SpO₂ {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["spo2_ma"], width=2),
                ),
                row=1,
                col=1,
            )
        fig_stacked.add_hline(
            y=spo2_threshold,
            line_dash="dash",
            line_color=COLORS["spo2_threshold"],
            annotation_text=f"{spo2_threshold} %",
            annotation_position="bottom right",
            row=1,
            col=1,
        )

    # Row 2: HR
    if "hr" in (series or []):
        fig_stacked.add_trace(
            go.Scatter(
                x=window_df["timestamp_local"],
                y=window_df["hr"],
                name="HR (raw)",
                mode="lines+markers",
                opacity=0.4,
                line=dict(color=COLORS["hr_raw"]),
                marker=dict(color=COLORS["hr_raw"]),
            ),
            row=2,
            col=1,
        )
        if hr_ma is not None:
            fig_stacked.add_trace(
                go.Scatter(
                    x=window_df["timestamp_local"],
                    y=hr_ma,
                    name=f"HR {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["hr_ma"], width=2),
                ),
                row=2,
                col=1,
            )

    fig_stacked.update_layout(
        title=f"Live stacked view - last {int(window_min)} min",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=60),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0
        ),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
        uirevision="live-stacked",
        height=520,
        xaxis=dict(
            type="date",
            rangeslider=dict(visible=False),
        ),
    )
    fig_stacked.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
    fig_stacked.update_yaxes(title_text="HR (bpm)", row=2, col=1)

    return (
        f"SpO₂: {latest['spo2']}",
        f"HR: {latest['hr']}",
        f"Battery: {latest['battery']}",
        f"Last sample: {int(time_since.total_seconds())} s ago",
        fig_overlay,
        fig_stacked,
    )


# ---------------------------------------------------------------------------
# REVIEW TAB CALLBACK
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("review-summary", "children"),
        Output("review-graph", "figure"),
        Output("review-events", "data"),
        Output("review-graph-stacked", "figure"),
    ],
    [
        Input("review-sleep-date", "value"),
        Input("review-threshold", "value"),
        Input("review-duration", "value"),
        Input("review-smoothing-sec", "value"),
        Input("review-options", "value"),
    ],
)
def update_review(sleep_date_value, threshold, min_duration, smoothing_sec, options):
    if not sleep_date_value:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Select a sleep date",
            template="plotly_dark",
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font=dict(color="#e5e7eb"),
        )
        return ("No sleep date selected", empty_fig, [], empty_fig)

    sleep_date = datetime.fromisoformat(sleep_date_value).date()
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data for selected sleep date",
            template="plotly_dark",
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font=dict(color="#e5e7eb"),
        )
        return ("No data available", empty_fig, [], empty_fig)

    threshold = int(threshold) if threshold is not None else 90
    min_duration = float(min_duration) if min_duration is not None else 10.0
    smoothing_sec = int(smoothing_sec) if smoothing_sec is not None else 0
    options = options or []
    show_hr = "hr" in options
    show_events = "events" in options

    df = df.sort_values("timestamp_utc")

    # Rolling means if requested
    if smoothing_sec > 0 and len(df) > 1:
        w = df.set_index("timestamp_utc")
        df["spo2_ma"] = w["spo2"].rolling(f"{smoothing_sec}s").mean().values
        df["hr_ma"] = w["hr"].rolling(f"{smoothing_sec}s").mean().values

    else:
        df["spo2_ma"] = None
        df["hr_ma"] = None

    desats = metrics.compute_desaturations(df, threshold, min_duration)
    summary = metrics.summarize_session(df, threshold, min_duration)

    # Overlaid figure
    fig_overlay = make_subplots(specs=[[{"secondary_y": True}]])

    # Raw traces
    fig_overlay.add_trace(
        go.Scatter(
            x=df["timestamp_local"],
            y=df["spo2"],
            name="SpO₂ (raw)",
            mode="lines",
            opacity=0.3,
            line=dict(color=COLORS["spo2_raw"]),
        ),
        secondary_y=False,
    )

    if show_hr:
        fig_overlay.add_trace(
            go.Scatter(
                x=df["timestamp_local"],
                y=df["hr"],
                name="HR (raw)",
                mode="lines",
                opacity=0.3,
                line=dict(color=COLORS["hr_raw"]),
            ),
            secondary_y=True,
        )

    # Moving averages
    if smoothing_sec > 0:
        fig_overlay.add_trace(
            go.Scatter(
                x=df["timestamp_local"],
                y=df["spo2_ma"],
                name=f"SpO₂ {smoothing_sec}s MA",
                mode="lines",
                line=dict(color=COLORS["spo2_ma"], width=2),
            ),
            secondary_y=False,
        )
        if show_hr:
            fig_overlay.add_trace(
                go.Scatter(
                    x=df["timestamp_local"],
                    y=df["hr_ma"],
                    name=f"HR {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["hr_ma"], width=2),
                ),
                secondary_y=True,
            )

    # Desaturation markers
    if show_events and not desats.empty:
        fig_overlay.add_trace(
            go.Scatter(
                x=desats["start_time_local"],
                y=[threshold] * len(desats),
                mode="markers",
                marker=dict(
                    color=COLORS["event_marker"],
                    size=10,
                    symbol="triangle-down",
                ),
                name="Desat start",
            ),
            secondary_y=False,
        )

    # Threshold line
    fig_overlay.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"Threshold {threshold} %",
        annotation_position="bottom right",
    )

    fig_overlay.update_layout(
        title=f"Session {sleep_date_value}",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=100, b=120),
        legend=dict(
            orientation="h", yanchor="top", y=-0.24, xanchor="left", x=0
        ),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
        xaxis=dict(
            type="date",
            rangeselector=dict(
                buttons=[
                    dict(
                        count=30,
                        label="30 min",
                        step="minute",
                        stepmode="backward",
                    ),
                    dict(
                        count=1,
                        label="1 h",
                        step="hour",
                        stepmode="backward",
                    ),
                    dict(
                        count=3,
                        label="3 h",
                        step="hour",
                        stepmode="backward",
                    ),
                    dict(step="all", label="All"),
                ],
                y=1.05,
                yanchor="bottom",
                bgcolor="#0f172a",
                activecolor="#1d4ed8",
                font=dict(color="#e5e7eb", size=11),
            ),
            rangeslider=dict(visible=True),
        ),
        height=520,
    )

    fig_overlay.update_yaxes(
        title_text="SpO₂ (%)", secondary_y=False, range=[70, 100]
    )
    fig_overlay.update_yaxes(title_text="HR (bpm)", secondary_y=True)

    # Stacked figure with rangeslider and event markers
    fig_stacked = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.05,
    )

    # Row 1: SpO2
    fig_stacked.add_trace(
        go.Scatter(
            x=df["timestamp_local"],
            y=df["spo2"],
            name="SpO₂ (raw)",
            mode="lines",
            opacity=0.3,
            line=dict(color=COLORS["spo2_raw"]),
        ),
        row=1,
        col=1,
    )
    if smoothing_sec > 0:
        fig_stacked.add_trace(
            go.Scatter(
                x=df["timestamp_local"],
                y=df["spo2_ma"],
                name=f"SpO₂ {smoothing_sec}s MA",
                mode="lines",
                line=dict(color=COLORS["spo2_ma"], width=2),
            ),
            row=1,
            col=1,
        )
    fig_stacked.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"{threshold} %",
        annotation_position="bottom right",
        row=1,
        col=1,
    )

    # Event markers in stacked view (top panel)
    if show_events and not desats.empty:
        fig_stacked.add_trace(
            go.Scatter(
                x=desats["start_time_local"],
                y=[threshold] * len(desats),
                mode="markers",
                marker=dict(
                    color=COLORS["event_marker"],
                    size=10,
                    symbol="triangle-down",
                ),
                name="Desat start",
            ),
            row=1,
            col=1,
        )

    # Row 2: HR
    if show_hr:
        fig_stacked.add_trace(
            go.Scatter(
                x=df["timestamp_local"],
                y=df["hr"],
                name="HR (raw)",
                mode="lines",
                opacity=0.3,
                line=dict(color=COLORS["hr_raw"]),
            ),
            row=2,
            col=1,
        )
        if smoothing_sec > 0:
            fig_stacked.add_trace(
                go.Scatter(
                    x=df["timestamp_local"],
                    y=df["hr_ma"],
                    name=f"HR {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["hr_ma"], width=2),
                ),
                row=2,
                col=1,
            )

    fig_stacked.update_layout(
        title=f"Session {sleep_date_value} - stacked view",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=80, b=80),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0
        ),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
        height=520,
        xaxis2=dict(
            type="date",
            rangeslider=dict(visible=True),
        ),
    )
    fig_stacked.update_yaxes(
        title_text="SpO₂ (%)", row=1, col=1, range=[70, 100]
    )
    fig_stacked.update_yaxes(title_text="HR (bpm)", row=2, col=1)

    spo2_mean = summary["spo2_mean"]
    hr_mean = summary["hr_mean"]

    cards = [
        html.Div(
            [
                html.Div("Analysed duration", className="metric-label"),
                html.Div(
                    f"{summary['analysed_duration_hours']:.2f} h",
                    className="metric-value",
                ),
                html.Div("Hours of data included in this review.", className="metric-help"),
            ],
            className="metric-card",
        ),
        html.Div(
            [
                html.Div("SpO₂ min / mean", className="metric-label"),
                html.Div(
                    "n/a"
                    if summary["spo2_min"] is None
                    else f"{summary['spo2_min']} / {spo2_mean:.1f}" if spo2_mean is not None else f"{summary['spo2_min']} / n/a",
                    className="metric-value",
                ),
                html.Div("Lowest and average SpO₂ across the night.", className="metric-help"),
            ],
            className="metric-card",
        ),
        html.Div(
            [
                html.Div("HR min / mean", className="metric-label"),
                html.Div(
                    "n/a"
                    if summary["hr_min"] is None
                    else f"{summary['hr_min']} / {hr_mean:.1f}" if hr_mean is not None else f"{summary['hr_min']} / n/a",
                    className="metric-value",
                ),
                html.Div("Heart rate range for the session.", className="metric-help"),
            ],
            className="metric-card",
        ),
        html.Div(
            [
                html.Div("Time below threshold", className="metric-label"),
                html.Div(
                    f"{summary['time_below_threshold_sec']:.1f} s",
                    className="metric-value",
                ),
                html.Div("Seconds with SpO₂ below the chosen limit.", className="metric-help"),
            ],
            className="metric-card",
        ),
        html.Div(
            [
                html.Div("Events / ODI", className="metric-label"),
                html.Div(
                    f"{summary['events_count']} events · ODI {summary['odi']:.2f}",
                    className="metric-value",
                ),
                html.Div("Number of desaturations and the Oxygen Desaturation Index.", className="metric-help"),
            ],
            className="metric-card",
        ),
        html.Div(
            [
                html.Div("Smoothing", className="metric-label"),
                html.Div(
                    "Off" if smoothing_sec <= 0 else f"{smoothing_sec} s moving average",
                    className="metric-value",
                ),
                html.Div("Applies equally to SpO₂ and HR when enabled.", className="metric-help"),
            ],
            className="metric-card",
        ),
    ]

    summary_panel = html.Div(
        [
            html.Div(
                [
                    html.Div("Session overview", className="section-title"),
                    html.Div(
                        f"Threshold {threshold}% · Minimum duration {min_duration:.0f}s",
                        className="section-desc",
                    ),
                ]
            ),
            html.Div(cards, className="summary-grid"),
        ],
        className="summary-card",
    )

    events_data = desats.to_dict("records") if not desats.empty else []

    return summary_panel, fig_overlay, events_data, fig_stacked


# ---------------------------------------------------------------------------
# EVENTS TAB CALLBACK (basic version: slider only)
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("events-index", "max"),
        Output("events-index", "marks"),
        Output("events-selected-summary", "children"),
        Output("events-graph", "figure"),
    ],
    [
        Input("events-sleep-date", "value"),
        Input("events-threshold", "value"),
        Input("events-duration", "value"),
        Input("events-index", "value"),
    ],
)
def update_events_tab(
    sleep_date_value,
    threshold,
    min_duration,
    slider_value,
):
    # Base empty figure
    def _empty_events_fig(title: str) -> go.Figure:
        f = go.Figure()
        f.update_layout(
            title=title,
            template="plotly_dark",
            paper_bgcolor="#020617",
            plot_bgcolor="#020617",
            font=dict(color="#e5e7eb"),
        )
        return f

    # No date selected
    if not sleep_date_value:
        return (
            0,
            {0: "0"},
            "No sleep date selected",
            _empty_events_fig("Select a sleep date"),
        )

    sleep_date = datetime.fromisoformat(sleep_date_value).date()
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)

    if df.empty:
        return (
            0,
            {0: "0"},
            "No data available",
            _empty_events_fig("No data for selected sleep date"),
        )

    threshold = int(threshold) if threshold is not None else 90
    min_duration = float(min_duration) if min_duration is not None else 10.0

    df = df.sort_values("timestamp_utc")
    desats = metrics.compute_desaturations(df, threshold, min_duration)

    if desats.empty:
        return (
            0,
            {0: "0"},
            "No events detected with current settings",
            _empty_events_fig("No desaturation events"),
        )

    num_events = len(desats)
    max_idx = num_events - 1

    # Current index driven only by slider, default to 0
    event_index = slider_value if slider_value is not None else 0

    # Clamp to valid range
    if event_index < 0:
        event_index = 0
    if event_index > max_idx:
        event_index = max_idx

    # Slider marks: first and last
    marks = {0: "0", max_idx: str(max_idx)} if max_idx > 0 else {0: "0"}

    ev = desats.iloc[event_index]

    # Time window for initial zoom: 10 min before, 10 min after event start
    start_local = ev["start_time_local"]
    end_local = ev["end_time_local"]
    duration_sec = ev.get(
        "duration_sec", (end_local - start_local).total_seconds()
    )

    window_start = start_local - timedelta(minutes=10)
    window_end = start_local + timedelta(minutes=10)

    # Full-night stacked figure with rangeslider and event markers
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.05,
    )

    # Row 1: SpO2 full session
    fig.add_trace(
        go.Scatter(
            x=df["timestamp_local"],
            y=df["spo2"],
            name="SpO₂",
            mode="lines+markers",
            line=dict(color=COLORS["spo2_raw"]),
            marker=dict(color=COLORS["spo2_raw"]),
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"{threshold} %",
        annotation_position="bottom right",
        row=1,
        col=1,
    )

    # All event start markers
    fig.add_trace(
        go.Scatter(
            x=desats["start_time_local"],
            y=[threshold] * len(desats),
            mode="markers",
            marker=dict(
                color=COLORS["event_marker"],
                size=9,
                symbol="triangle-down",
            ),
            name="Desat start",
        ),
        row=1,
        col=1,
    )

    # Row 2: HR full session
    if "hr" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp_local"],
                y=df["hr"],
                name="HR",
                mode="lines+markers",
                line=dict(color=COLORS["hr_raw"]),
                marker=dict(color=COLORS["hr_raw"]),
            ),
            row=2,
            col=1,
        )

    # Highlight selected event window across both rows
    fig.add_vrect(
        x0=start_local,
        x1=end_local,
        fillcolor="rgba(249,115,22,0.15)",  # soft orange
        line_width=0,
        row="all",
        col=1,
    )

    fig.update_layout(
        title=(
            f"Event {event_index + 1} / {num_events} "
            f"({start_local.strftime('%H:%M:%S')} - {end_local.strftime('%H:%M:%S')})"
        ),
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=80, b=80),
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        font=dict(color="#e5e7eb"),
        height=520,
        xaxis2=dict(
            type="date",
            rangeslider=dict(visible=True),
            range=[window_start, window_end],
        ),
    )
    fig.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
    fig.update_yaxes(title_text="HR (bpm)", row=2, col=1)

    # Event summary
    nadir_spo2 = ev.get("nadir_spo2", None)
    mean_spo2 = ev.get("mean_spo2", None)

    summary_children = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        f"Event {event_index + 1} of {num_events}",
                        className="section-title",
                    ),
                    html.Div(
                        f"Context window: {window_start.strftime('%H:%M')}–{window_end.strftime('%H:%M')}",
                        className="section-desc",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Start", className="metric-label"),
                            html.Div(str(start_local), className="metric-value"),
                            html.Div("Local time when desaturation began.", className="metric-help"),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div("End", className="metric-label"),
                            html.Div(str(end_local), className="metric-value"),
                            html.Div("Local time when recovery finished.", className="metric-help"),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div("Duration", className="metric-label"),
                            html.Div(f"{duration_sec:.1f} s", className="metric-value"),
                            html.Div("Length of time below threshold.", className="metric-help"),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div("Nadir SpO₂", className="metric-label"),
                            html.Div(
                                "n/a" if nadir_spo2 is None else str(nadir_spo2),
                                className="metric-value",
                            ),
                            html.Div("Lowest saturation within the event.", className="metric-help"),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div("Mean SpO₂", className="metric-label"),
                            html.Div(
                                "n/a" if mean_spo2 is None else str(mean_spo2),
                                className="metric-value",
                            ),
                            html.Div("Average saturation across the event window.", className="metric-help"),
                        ],
                        className="metric-card",
                    ),
                ],
                className="summary-grid",
            ),
        ],
        className="summary-card",
    )

    return max_idx, marks, summary_children, fig

@app.callback(
    Output("events-index", "value"),
    [
        Input("events-prev", "n_clicks"),
        Input("events-next", "n_clicks"),
    ],
    [
        State("events-index", "value"),
        State("events-index", "max"),
    ],
)
def step_events(prev_clicks, next_clicks, current_index, max_index):
    # Only react when a button is actually clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # Default values
    if current_index is None:
        current_index = 0
    if max_index is None:
        max_index = 0

    if trigger == "events-prev":
        new_index = max(current_index - 1, 0)
    elif trigger == "events-next":
        new_index = min(current_index + 1, max_index)
    else:
        raise PreventUpdate

    return new_index






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
