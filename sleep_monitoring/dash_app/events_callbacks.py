"""Callbacks for the Events tab."""
from __future__ import annotations

from datetime import datetime, timedelta

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output, State, callback_context, html
from dash.exceptions import PreventUpdate

from sleep_monitoring import config, data_io, metrics

from .theme import COLORS, THEME
from .utils import apply_gap_breaks, empty_figure, format_percentage, format_timestamp_human


def register_events_callbacks(app):
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
    def update_events_tab(sleep_date_value, threshold, min_duration, slider_value):
        if not sleep_date_value:
            return (0, {0: "0"}, "No sleep date selected", empty_figure("Select a sleep date"))

        sleep_date = datetime.fromisoformat(sleep_date_value).date()
        df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)

        if df.empty:
            return (0, {0: "0"}, "No data available", empty_figure("No data for selected sleep date"))

        threshold = int(threshold) if threshold is not None else 90
        min_duration = float(min_duration) if min_duration is not None else 10.0

        df = df.sort_values("timestamp_utc")
        spo2_x, spo2_y = apply_gap_breaks(df["timestamp_local"], df["spo2"])
        hr_x, hr_y = apply_gap_breaks(df["timestamp_local"], df.get("hr", []))
        desats = metrics.compute_desaturations(df, threshold, min_duration)

        if desats.empty:
            return (
                0,
                {0: "0"},
                "No events detected with current settings",
                empty_figure("No desaturation events"),
            )

        num_events = len(desats)
        max_idx = num_events - 1
        event_index = slider_value if slider_value is not None else 0
        event_index = max(0, min(event_index, max_idx))
        marks = {0: "0", max_idx: str(max_idx)} if max_idx > 0 else {0: "0"}

        ev = desats.iloc[event_index]
        start_local = ev["start_time_local"]
        end_local = ev["end_time_local"]
        duration_sec = ev.get("duration_sec", (end_local - start_local).total_seconds())
        window_start = start_local - timedelta(minutes=10)
        window_end = start_local + timedelta(minutes=10)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.05)
        fig.add_trace(
            go.Scatter(
                x=spo2_x,
                y=spo2_y,
                name="SpO₂",
                mode="lines",
                line=dict(color=COLORS["spo2_raw"]),
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
        fig.add_trace(
            go.Scatter(
                x=desats["start_time_local"],
                y=[threshold] * len(desats),
                mode="markers",
                marker=dict(color=COLORS["event_marker"], size=9, symbol="triangle-down"),
                name="Desat start",
            ),
            row=1,
            col=1,
        )

        if "hr" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=hr_x,
                    y=hr_y,
                    name="HR",
                    mode="lines",
                    line=dict(color=COLORS["hr_raw"]),
                ),
                row=2,
                col=1,
            )

        fig.add_vrect(
            x0=start_local,
            x1=end_local,
            fillcolor="rgba(249,115,22,0.15)",
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
            paper_bgcolor=THEME["bg"],
            plot_bgcolor=THEME["bg"],
            font=dict(color=THEME["text"]),
            height=520,
            xaxis2=dict(type="date", rangeslider=dict(visible=True), range=[window_start, window_end]),
        )
        fig.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
        fig.update_yaxes(title_text="HR (bpm)", row=2, col=1)

        hr_min = None
        hr_mean = None
        if "hr" in df.columns:
            event_slice = df[(df["timestamp_local"] >= start_local) & (df["timestamp_local"] <= end_local)]
            if not event_slice.empty and event_slice["hr"].notna().any():
                hr_min = int(event_slice["hr"].min())
                hr_mean = float(event_slice["hr"].mean())

        summary_children = html.Div(
            [
                html.Div(
                    [
                        html.Div(f"Event {event_index + 1} of {num_events}", className="section-title"),
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
                                html.Div(format_timestamp_human(start_local), className="metric-value"),
                                html.Div("Local time when desaturation began.", className="metric-help"),
                            ],
                            className="metric-card",
                        ),
                        html.Div(
                            [
                                html.Div("End", className="metric-label"),
                                html.Div(format_timestamp_human(end_local), className="metric-value"),
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
                                    "n/a" if ev.get("nadir_spo2") is None else f"{ev.get('nadir_spo2')} %",
                                    className="metric-value",
                                ),
                                html.Div("Lowest saturation within the event.", className="metric-help"),
                            ],
                            className="metric-card",
                        ),
                        html.Div(
                            [
                                html.Div("Mean SpO₂", className="metric-label"),
                                html.Div(format_percentage(ev.get("mean_spo2")), className="metric-value"),
                                html.Div("Average saturation across the event window.", className="metric-help"),
                            ],
                            className="metric-card",
                        ),
                        html.Div(
                            [
                                html.Div("HR min / mean", className="metric-label"),
                                html.Div(
                                    "n/a"
                                    if hr_min is None
                                    else f"{hr_min} bpm / {hr_mean:.1f} bpm" if hr_mean is not None else f"{hr_min} bpm / n/a",
                                    className="metric-value",
                                ),
                                html.Div("Heart rate profile during the desaturation.", className="metric-help"),
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
        [Input("events-prev", "n_clicks"), Input("events-next", "n_clicks")],
        [State("events-index", "value"), State("events-index", "max")],
    )
    def step_events(prev_clicks, next_clicks, current_index, max_index):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        current_index = current_index or 0
        max_index = max_index or 0

        if trigger == "events-prev":
            new_index = max(current_index - 1, 0)
        elif trigger == "events-next":
            new_index = min(current_index + 1, max_index)
        else:
            raise PreventUpdate

        return new_index
