"""Dash UI for live monitoring and review."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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

    # HR family variant for threshold line
    "spo2_threshold": "#c2d81d",   # HR related threshold line

    # Event markers (desats, etc.)
    "event_marker": "#f97316",   # orange, stands out
}

app = Dash(__name__)
app.title = "Sleep Monitoring"
server = app.server


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

            # Main graph
            dcc.Graph(
                id="live-graph",
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

            dcc.Graph(
                id="review-graph",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
                style={"height": "650px"},
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
            ],
            colors={
                # border under the tab bar
                "border": "#111827",
                # color of the active tab text + top border
                "primary": "#3b82f6",
                # background behind the tabs
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
    return _review_layout()


@app.callback(
    [
        Output("live-spo2", "children"),
        Output("live-hr", "children"),
        Output("live-battery", "children"),
        Output("live-last-sample", "children"),
        Output("live-graph", "figure"),
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
        return ("SpO₂: --", "HR: --", "Battery: --", "Last sample: --", empty_fig)

    latest = df.iloc[-1]
    now_utc = datetime.now(timezone.utc)
    time_since = now_utc - latest["timestamp_utc"]

    window_min = window_min or 30
    window_start = now_utc - timedelta(minutes=int(window_min))
    mask = df["timestamp_utc"] >= window_start
    window_df = df[mask].copy().sort_values("timestamp_utc")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Raw signals (dimmed)
    if "spo2" in (series or []):
        fig.add_trace(
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
        fig.add_trace(
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
    if smoothing_sec and smoothing_sec > 0 and len(window_df) > 1:
        smoothing_sec = int(smoothing_sec)
        w = window_df.set_index("timestamp_utc")
        spo2_ma = w["spo2"].rolling(f"{smoothing_sec}S").mean()
        hr_ma = w["hr"].rolling(f"{smoothing_sec}S").mean()

        if "spo2" in (series or []):
            fig.add_trace(
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
            fig.add_trace(
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
    fig.add_hline(
        y=spo2_threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"{spo2_threshold} % threshold",
        annotation_position="bottom right",
    )

    # Keep live view smooth and avoid jitter from auto-rescaling
    fig.update_layout(
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
        # uirevision tells Plotly “don’t reset user zoom/pan on each update”
        uirevision="live",
        height=650,
        xaxis=dict(
            type="date",
            # No range slider on LIVE view – just a moving window
            rangeslider=dict(visible=False),
        ),
    )
    fig.update_yaxes(title_text="SpO₂ (%)", secondary_y=False, range=[70, 100])
    fig.update_yaxes(title_text="HR (bpm)", secondary_y=True)


    return (
        f"SpO₂: {latest['spo2']}",
        f"HR: {latest['hr']}",
        f"Battery: {latest['battery']}",
        f"Last sample: {int(time_since.total_seconds())} s ago",
        fig,
    )


@app.callback(
    [
        Output("review-summary", "children"),
        Output("review-graph", "figure"),
        Output("review-events", "data"),
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
        return ("No sleep date selected", empty_fig, [])

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
        return ("No data available", empty_fig, [])

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

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Raw traces
    fig.add_trace(
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
        fig.add_trace(
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
        fig.add_trace(
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
            fig.add_trace(
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
        fig.add_trace(
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
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLORS["spo2_threshold"],
        annotation_text=f"Threshold {threshold} %",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=f"Session {sleep_date_value}",
        template="plotly_dark",
        hovermode="x unified",
        # extra top margin so buttons don't sit on top of the plot
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
                    dict(count=30, label="30 min", step="minute", stepmode="backward"),
                    dict(count=1, label="1 h", step="hour", stepmode="backward"),
                    dict(count=3, label="3 h", step="hour", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
                # lift the buttons just above the plot area
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

    fig.update_yaxes(title_text="SpO₂ (%)", secondary_y=False, range=[70, 100])
    fig.update_yaxes(title_text="HR (bpm)", secondary_y=True)

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

    ma_text = "Moving average: off" if smoothing_sec <= 0 else f"Moving average: {smoothing_sec} s"

    summary_list = html.Ul(
        [
            html.Li(f"Analysed duration: {summary['analysed_duration_hours']:.2f} h"),
            html.Li(spo2_text),
            html.Li(hr_text),
            html.Li(
                f"Time below threshold (s): "
                f"{summary['time_below_threshold_sec']:.1f}"
            ),
            html.Li(f"Events: {summary['events_count']} (ODI {summary['odi']:.2f})"),
            html.Li(ma_text),
        ]
    )

    events_data = desats.to_dict("records") if not desats.empty else []

    return summary_list, fig, events_data


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
