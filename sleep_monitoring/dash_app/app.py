"""Dash UI for live monitoring and review."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import dash
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, Input, Output, dcc, html, dash_table

from sleep_monitoring import config, data_io, metrics

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


# ---------------------------------------------------------------------------
# TAB LAYOUTS
# ---------------------------------------------------------------------------

def _live_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id="live-interval", interval=2000, n_intervals=0),

            # Top metric strip
            html.Div(
                [
                    html.Div(id="live-spo2", className="metric"),
                    html.Div(id="live-hr", className="metric"),
                    html.Div(id="live-battery", className="metric"),
                    html.Div(id="live-last-sample", className="metric"),
                ],
                className="live-metrics",
            ),

            # Controls row
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Window (min)", className="control-label"),
                            dcc.Slider(
                                id="live-window-min",
                                min=10,
                                max=180,
                                step=10,
                                value=30,
                                marks={
                                    10: "10",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                    180: "180",
                                },
                            ),
                        ],
                        className="live-control",
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Smoothing (sec, moving average)",
                                className="control-label",
                            ),
                            dcc.Slider(
                                id="live-smoothing-sec",
                                min=0,
                                max=120,
                                step=5,
                                value=30,
                                marks={
                                    0: "off",
                                    15: "15",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                },
                            ),
                        ],
                        className="live-control",
                    ),
                    html.Div(
                        [
                            html.Label("Signals", className="control-label"),
                            dcc.Checklist(
                                id="live-series",
                                options=[
                                    {"label": "SpO₂", "value": "spo2"},
                                    {"label": "HR", "value": "hr"},
                                ],
                                value=["spo2", "hr"],
                                inline=True,
                                inputStyle={"margin-right": "0.25rem"},
                            ),
                            html.Label(
                                "SpO₂ threshold",
                                className="control-label control-label--small",
                            ),
                            dcc.Slider(
                                id="live-threshold",
                                min=80,
                                max=95,
                                step=1,
                                value=90,
                                marks={80: "80", 85: "85", 90: "90", 95: "95"},
                            ),
                        ],
                        className="live-control live-control--compact",
                    ),
                ],
                className="live-controls",
            ),

            # Main overlaid graph
            dcc.Graph(
                id="live-graph",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px"},
            ),

            # Two-row synced graph (SpO2 top, HR bottom)
            dcc.Graph(
                id="live-graph-stacked",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px", "marginTop": "24px"},
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
            # First row of controls
            html.Div(
                [
                    html.Div(
                        dcc.Dropdown(
                            id="review-sleep-date",
                            options=options,
                            value=default_value,
                            placeholder="Select sleep date",
                            className="dropdown-dark",
                            style={
                                "backgroundColor": "#020617",
                                "color": "#e5e7eb",
                            },
                        ),
                        className="review-control review-control--dropdown",
                    ),
                    html.Div(
                        dcc.Input(
                            id="review-threshold",
                            type="number",
                            value=90,
                            step=1,
                            min=50,
                            max=100,
                            placeholder="Desat threshold",
                            className="input-dark",
                        ),
                        className="review-control",
                    ),
                    html.Div(
                        dcc.Input(
                            id="review-duration",
                            type="number",
                            value=10,
                            step=1,
                            min=1,
                            placeholder="Min duration (s)",
                            className="input-dark",
                        ),
                        className="review-control",
                    ),
                ],
                className="review-controls",
                style={"position": "relative", "zIndex": 10},
            ),

            # Second row of controls
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "Smoothing (sec, moving average)",
                                className="control-label",
                            ),
                            dcc.Slider(
                                id="review-smoothing-sec",
                                min=0,
                                max=120,
                                step=5,
                                value=30,
                                marks={
                                    0: "off",
                                    15: "15",
                                    30: "30",
                                    60: "60",
                                    120: "120",
                                },
                            ),
                        ],
                        className="review-control",
                        style={"position": "relative", "zIndex": 10},
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Display options",
                                className="control-label",
                            ),
                            dcc.Checklist(
                                id="review-options",
                                options=[
                                    {"label": "Show HR", "value": "hr"},
                                    {"label": "Highlight events", "value": "events"},
                                ],
                                value=["hr", "events"],
                                inline=True,
                                inputStyle={"margin-right": "0.25rem"},
                            ),
                        ],
                        className="review-control review-control--compact",
                    ),
                ],
                className="review-controls",
            ),

            html.Div(id="review-summary", className="summary-card"),

            # Main overlaid graph
            dcc.Graph(
                id="review-graph",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px"},
            ),

            # Two-row synced graph
            dcc.Graph(
                id="review-graph-stacked",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px", "marginTop": "24px"},
            ),

            dash_table.DataTable(
                id="review-events",
                columns=[
                    {"name": "Start", "id": "start_time_local"},
                    {"name": "End", "id": "end_time_local"},
                    {"name": "Duration (s)", "id": "duration_sec"},
                    {"name": "Nadir SpO₂", "id": "nadir_spo2"},
                    {"name": "Mean SpO₂", "id": "mean_spo2"},
                ],
                style_header={
                    "backgroundColor": "#111827",
                    "color": "#e5e7eb",
                    "border": "none",
                    "fontWeight": "600",
                },
                style_data={
                    "backgroundColor": "#020617",
                    "color": "#e5e7eb",
                    "border": "none",
                },
                style_table={
                    "overflowX": "auto",
                    "backgroundColor": "#020617",
                },
                style_cell={
                    "padding": "0.4rem",
                    "fontSize": 12,
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
            # Controls row
            html.Div(
                [
                    html.Div(
                        dcc.Dropdown(
                            id="events-sleep-date",
                            options=options,
                            value=default_value,
                            placeholder="Select sleep date",
                            className="dropdown-dark",
                            style={
                                "backgroundColor": "#020617",
                                "color": "#e5e7eb",
                            },
                        ),
                        className="review-control review-control--dropdown",
                    ),
                    html.Div(
                        dcc.Input(
                            id="events-threshold",
                            type="number",
                            value=90,
                            step=1,
                            min=50,
                            max=100,
                            placeholder="Desat threshold",
                            className="input-dark",
                        ),
                        className="review-control",
                    ),
                    html.Div(
                        dcc.Input(
                            id="events-duration",
                            type="number",
                            value=10,
                            step=1,
                            min=1,
                            placeholder="Min duration (s)",
                            className="input-dark",
                        ),
                        className="review-control",
                    ),
                ],
                className="review-controls",
            ),

            # Slider + arrows to pick event index
            html.Div(
                [
                    html.Label("Event index", className="control-label"),
                    html.Div(
                        [
                            html.Button(
                                "◀",
                                id="events-prev",
                                n_clicks=0,
                                style={
                                    "marginRight": "8px",
                                    "padding": "4px 10px",
                                    "backgroundColor": "#111827",
                                    "color": "#e5e7eb",
                                    "border": "1px solid #374151",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                },
                            ),
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
                                style={"flex": 1},
                            ),
                            html.Button(
                                "▶",
                                id="events-next",
                                n_clicks=0,
                                style={
                                    "marginLeft": "8px",
                                    "padding": "4px 10px",
                                    "backgroundColor": "#111827",
                                    "color": "#e5e7eb",
                                    "border": "1px solid #374151",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "4px",
                        },
                    ),
                    html.Div(
                        id="events-selected-summary",
                        className="summary-card",
                        style={"marginTop": "12px"},
                    ),
                    dcc.Store(id="events-selected-index", data=0),
                ],
                className="review-controls",
                style={"marginBottom": "16px"},
            ),

            # Event-focused stacked graph (full night with zoom)
            dcc.Graph(
                id="events-graph",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px"},
            ),
        ],
        className="tab-container",
    )


# ---------------------------------------------------------------------------
# APP LAYOUT
# ---------------------------------------------------------------------------

app.layout = html.Div(
    [
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
                "border": "#111827",
                "primary": "#3b82f6",
                "background": "#020617",
            },
            style={"borderBottom": "1px solid #111827"},
            className="tabs-container",
        ),
        html.Div(id="tab-content"),
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
        spo2_ma = w["spo2"].rolling(f"{smoothing_sec}S").mean()
        hr_ma = w["hr"].rolling(f"{smoothing_sec}S").mean()

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
        height=650,
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
        height=650,
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
        df["spo2_ma"] = w["spo2"].rolling(f"{smoothing_sec}S").mean().values
        df["hr_ma"] = w["hr"].rolling(f"{smoothing_sec}S").mean().values
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
        height=650,
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
        height=650,
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

    spo2_text = "SpO₂ min/mean: "
    if summary["spo2_min"] is not None:
        if spo2_mean is not None:
            spo2_text += f"{summary['spo2_min']} / {spo2_mean:.1f}"
        else:
            spo2_text += f"{summary['spo2_min']} / n/a"
    else:
        spo2_text += "n/a"

    hr_text = "HR min/mean: "
    if summary["hr_min"] is not None:
        if hr_mean is not None:
            hr_text += f"{summary['hr_min']} / {hr_mean:.1f}"
        else:
            hr_text += f"{summary['hr_min']} / n/a"
    else:
        hr_text += "n/a"

    ma_text = (
        "Moving average: off"
        if smoothing_sec <= 0
        else f"Moving average: {smoothing_sec} s"
    )

    summary_list = html.Ul(
        [
            html.Li(
                f"Analysed duration: {summary['analysed_duration_hours']:.2f} h"
            ),
            html.Li(spo2_text),
            html.Li(hr_text),
            html.Li(
                "Time below threshold (s): "
                f"{summary['time_below_threshold_sec']:.1f}"
            ),
            html.Li(f"Events: {summary['events_count']} (ODI {summary['odi']:.2f})"),
            html.Li(ma_text),
        ]
    )

    events_data = desats.to_dict("records") if not desats.empty else []

    return summary_list, fig_overlay, events_data, fig_stacked


# ---------------------------------------------------------------------------
# EVENTS TAB CALLBACK
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("events-index", "max"),
        Output("events-index", "marks"),
        Output("events-selected-summary", "children"),
        Output("events-graph", "figure"),
        Output("events-selected-index", "data"),
    ],
    [
        Input("events-sleep-date", "value"),
        Input("events-threshold", "value"),
        Input("events-duration", "value"),
        Input("events-prev", "n_clicks"),
        Input("events-next", "n_clicks"),
        Input("events-index", "value"),
    ],
    State("events-selected-index", "data"),
)
def update_events_tab(
    sleep_date_value,
    threshold,
    min_duration,
    prev_clicks,
    next_clicks,
    slider_value,
    stored_index,
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

    if not sleep_date_value:
        return (
            0,
            {0: "0"},
            "No sleep date selected",
            _empty_events_fig("Select a sleep date"),
            0,
        )

    sleep_date = datetime.fromisoformat(sleep_date_value).date()
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
    if df.empty:
        return (
            0,
            {0: "0"},
            "No data available",
            _empty_events_fig("No data for selected sleep date"),
            0,
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
            0,
        )

    num_events = len(desats)
    max_idx = num_events - 1

    # Determine current index based on which control fired
    event_index = stored_index or 0

    ctx = dash.callback_context
    triggered_id = (
        ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    )

    if triggered_id == "events-prev":
        event_index = max(event_index - 1, 0)
    elif triggered_id == "events-next":
        event_index = min(event_index + 1, max_idx)
    elif triggered_id == "events-index":
        event_index = slider_value or 0
    else:
        event_index = 0

    if event_index < 0:
        event_index = 0
    if event_index > max_idx:
        event_index = max_idx

    # Slider marks: just first and last
    marks = {0: "0", max_idx: str(max_idx)} if max_idx > 0 else {0: "0"}

    ev = desats.iloc[event_index]

    # Time window for initial zoom: 10 s before start, to event end + 20 s
    start_local = ev["start_time_local"]
    end_local = ev["end_time_local"]
    duration_sec = ev.get("duration_sec", (end_local - start_local).total_seconds())

    window_start = start_local - timedelta(seconds=10)
    window_end = end_local + timedelta(seconds=20)

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
        height=650,
        xaxis2=dict(
            type="date",
            rangeslider=dict(visible=True),
            # Initial zoom centered around the event with a bit of padding
            range=[window_start, window_end],
        ),
    )
    fig.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
    fig.update_yaxes(title_text="HR (bpm)", row=2, col=1)

    # Event summary
    nadir_spo2 = ev.get("nadir_spo2", None)
    mean_spo2 = ev.get("mean_spo2", None)

    summary_items = [
        f"Event {event_index + 1} of {num_events}",
        f"Start (local): {start_local}",
        f"End (local): {end_local}",
        f"Duration: {duration_sec:.1f} s",
        f"Nadir SpO₂: {nadir_spo2}" if nadir_spo2 is not None else "Nadir SpO₂: n/a",
        f"Mean SpO₂ during event: {mean_spo2}"
        if mean_spo2 is not None
        else "Mean SpO₂ during event: n/a",
    ]

    summary_children = html.Ul([html.Li(s) for s in summary_items])

    return max_idx, marks, summary_children, fig, event_index


@app.callback(Output("events-index", "value"), Input("events-selected-index", "data"))
def sync_slider_value(selected_index):
    return selected_index or 0


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
