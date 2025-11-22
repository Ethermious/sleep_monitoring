"""Dash UI for live monitoring and review."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, Input, Output, dcc, html, dash_table

from sleep_monitoring import config, data_io, metrics

app = Dash(__name__)
app.title = "Sleep Monitoring"
server = app.server


def _live_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id="live-interval", interval=2000, n_intervals=0),
            html.Div(
                [
                    html.Div(id="live-spo2", className="metric"),
                    html.Div(id="live-hr", className="metric"),
                    html.Div(id="live-battery", className="metric"),
                    html.Div(id="live-last-sample", className="metric"),
                ],
                className="live-metrics",
            ),
            dcc.Graph(id="live-graph"),
        ]
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
                    dcc.Dropdown(id="review-sleep-date", options=options, value=default_value, placeholder="Select sleep date"),
                    dcc.Input(id="review-threshold", type="number", value=90, step=1, min=50, max=100, placeholder="Desat threshold"),
                    dcc.Input(id="review-duration", type="number", value=10, step=1, min=1, placeholder="Min duration (s)"),
                ],
                className="review-controls",
            ),
            html.Div(id="review-summary"),
            dcc.Graph(id="review-graph"),
            dash_table.DataTable(id="review-events", columns=[
                {"name": "Start", "id": "start_time_local"},
                {"name": "End", "id": "end_time_local"},
                {"name": "Duration (s)", "id": "duration_sec"},
                {"name": "Nadir SpO2", "id": "nadir_spo2"},
                {"name": "Mean SpO2", "id": "mean_spo2"},
            ]),
        ]
    )


app.layout = html.Div(
    [
        dcc.Tabs(
            id="tabs",
            value="tab-live",
            children=[
                dcc.Tab(label="Live", value="tab-live"),
                dcc.Tab(label="Review", value="tab-review"),
            ],
        ),
        html.Div(id="tab-content"),
    ]
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
    Input("live-interval", "n_intervals"),
)
def update_live(_):
    sleep_date = data_io.compute_sleep_date(datetime.now(timezone.utc))
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No live data yet")
        return ("SpO2: --", "HR: --", "Battery: --", "Last sample: --", empty_fig)

    latest = df.iloc[-1]
    now_utc = datetime.now(timezone.utc)
    time_since = now_utc - latest["timestamp_utc"]

    window_start = now_utc - timedelta(minutes=30)
    mask = df["timestamp_utc"] >= window_start
    window_df = df[mask]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=window_df["timestamp_local"], y=window_df["spo2"], name="SpO2", mode="lines+markers"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=window_df["timestamp_local"], y=window_df["hr"], name="HR", mode="lines+markers"),
        secondary_y=True,
    )
    fig.update_layout(title="Live SpO2/HR (last 30 min)")
    fig.update_yaxes(title_text="SpO2", secondary_y=False)
    fig.update_yaxes(title_text="HR", secondary_y=True)

    return (
        f"SpO2: {latest['spo2']}",
        f"HR: {latest['hr']}",
        f"Battery: {latest['battery']}",
        f"Last sample: {int(time_since.total_seconds())}s ago",
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
    ],
)
def update_review(sleep_date_value, threshold, min_duration):
    if not sleep_date_value:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Select a sleep date")
        return ("No sleep date selected", empty_fig, [])

    sleep_date = datetime.fromisoformat(sleep_date_value).date()
    df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data for selected sleep date")
        return ("No data available", empty_fig, [])

    threshold = int(threshold) if threshold is not None else 90
    min_duration = float(min_duration) if min_duration is not None else 10.0

    desats = metrics.compute_desaturations(df, threshold, min_duration)
    summary = metrics.summarize_session(df, threshold, min_duration)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df["timestamp_local"], y=df["spo2"], name="SpO2", mode="lines"), secondary_y=False)
    fig.add_trace(go.Scatter(x=df["timestamp_local"], y=df["hr"], name="HR", mode="lines"), secondary_y=True)

    if not desats.empty:
        fig.add_trace(
            go.Scatter(
                x=desats["start_time_local"],
                y=[threshold] * len(desats),
                mode="markers",
                marker=dict(color="red", size=10, symbol="triangle-down"),
                name="Desat start",
            ),
            secondary_y=False,
        )

    fig.update_layout(title=f"Session {sleep_date_value}")
    fig.update_yaxes(title_text="SpO2", secondary_y=False)
    fig.update_yaxes(title_text="HR", secondary_y=True)

    spo2_mean = summary["spo2_mean"]
    hr_mean = summary["hr_mean"]
    spo2_text = "SpO2 min/mean: "
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

    summary_list = html.Ul(
        [
            html.Li(f"Analysed duration: {summary['analysed_duration_hours']:.2f} h"),
            html.Li(spo2_text),
            html.Li(hr_text),
            html.Li(f"Time below threshold (s): {summary['time_below_threshold_sec']:.1f}"),
            html.Li(f"Events: {summary['events_count']} (ODI {summary['odi']:.2f})"),
        ]
    )

    events_data = desats.to_dict("records") if not desats.empty else []

    return summary_list, fig, events_data


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=False)
