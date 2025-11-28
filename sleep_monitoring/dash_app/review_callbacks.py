"""Callbacks for the Review tab."""
from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output, html

from sleep_monitoring import config, data_io, metrics

from .theme import COLORS, THEME
from .utils import apply_gap_breaks, empty_figure, format_percentage, format_timestamp_human


def register_review_callbacks(app):
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
            empty_fig = empty_figure("Select a sleep date")
            return ("No sleep date selected", empty_fig, [], empty_fig)

        sleep_date = datetime.fromisoformat(sleep_date_value).date()
        df = data_io.load_session_samples(config.DEFAULT_USER_ID, sleep_date)
        if df.empty:
            empty_fig = empty_figure("No data for selected sleep date")
            return ("No data available", empty_fig, [], empty_fig)

        threshold = int(threshold) if threshold is not None else 90
        min_duration = float(min_duration) if min_duration is not None else 10.0
        smoothing_sec = int(smoothing_sec) if smoothing_sec is not None else 0
        options = options or []
        show_hr = "hr" in options
        show_events = "events" in options

        df = df.sort_values("timestamp_utc")

        spo2_x, spo2_y = apply_gap_breaks(df["timestamp_local"], df["spo2"])
        hr_x, hr_y = apply_gap_breaks(df["timestamp_local"], df["hr"])

        if smoothing_sec > 0 and len(df) > 1:
            w = df.set_index("timestamp_utc")
            df["spo2_ma"] = w["spo2"].rolling(f"{smoothing_sec}s").mean().values
            df["hr_ma"] = w["hr"].rolling(f"{smoothing_sec}s").mean().values

            spo2_ma_x, spo2_ma_y = apply_gap_breaks(df["timestamp_local"], df["spo2_ma"])
            hr_ma_x, hr_ma_y = apply_gap_breaks(df["timestamp_local"], df["hr_ma"])
        else:
            df["spo2_ma"] = None
            df["hr_ma"] = None
            spo2_ma_x = spo2_ma_y = hr_ma_x = hr_ma_y = None

        desats = metrics.compute_desaturations(df, threshold, min_duration)
        summary = metrics.summarize_session(df, threshold, min_duration)

        fig_overlay = make_subplots(specs=[[{"secondary_y": True}]])
        fig_overlay.add_trace(
            go.Scatter(
                x=spo2_x,
                y=spo2_y,
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
                    x=hr_x,
                    y=hr_y,
                    name="HR (raw)",
                    mode="lines",
                    opacity=0.3,
                    line=dict(color=COLORS["hr_raw"]),
                ),
                secondary_y=True,
            )

        if smoothing_sec > 0:
            fig_overlay.add_trace(
                go.Scatter(
                    x=spo2_ma_x,
                    y=spo2_ma_y,
                    name=f"SpO₂ {smoothing_sec}s MA",
                    mode="lines",
                    line=dict(color=COLORS["spo2_ma"], width=2),
                ),
                secondary_y=False,
            )
            if show_hr:
                fig_overlay.add_trace(
                    go.Scatter(
                        x=hr_ma_x,
                        y=hr_ma_y,
                        name=f"HR {smoothing_sec}s MA",
                        mode="lines",
                        line=dict(color=COLORS["hr_ma"], width=2),
                    ),
                    secondary_y=True,
                )

        if show_events and not desats.empty:
            fig_overlay.add_trace(
                go.Scatter(
                    x=desats["start_time_local"],
                    y=[threshold] * len(desats),
                    mode="markers",
                    marker=dict(color=COLORS["event_marker"], size=10, symbol="triangle-down"),
                    name="Desat start",
                ),
                secondary_y=False,
            )

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
            legend=dict(orientation="h", yanchor="top", y=-0.24, xanchor="left", x=0),
            paper_bgcolor=THEME["bg"],
            plot_bgcolor=THEME["bg"],
            font=dict(color=THEME["text"]),
            xaxis=dict(
                type="date",
                rangeselector=dict(
                    buttons=[
                        dict(count=30, label="30 min", step="minute", stepmode="backward"),
                        dict(count=1, label="1 h", step="hour", stepmode="backward"),
                        dict(count=3, label="3 h", step="hour", stepmode="backward"),
                        dict(step="all", label="All"),
                    ],
                    y=1.05,
                    yanchor="bottom",
                    bgcolor="#0f172a",
                    activecolor="#1d4ed8",
                    font=dict(color=THEME["text"], size=11),
                ),
                rangeslider=dict(visible=True),
            ),
            height=520,
        )
        fig_overlay.update_yaxes(title_text="SpO₂ (%)", secondary_y=False, range=[70, 100])
        fig_overlay.update_yaxes(title_text="HR (bpm)", secondary_y=True)

        fig_stacked = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.5, 0.5],
            vertical_spacing=0.05,
        )
        fig_stacked.add_trace(
            go.Scatter(
                x=spo2_x,
                y=spo2_y,
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
                    x=spo2_ma_x,
                    y=spo2_ma_y,
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

        if show_events and not desats.empty:
            fig_stacked.add_trace(
                go.Scatter(
                    x=desats["start_time_local"],
                    y=[threshold] * len(desats),
                    mode="markers",
                    marker=dict(color=COLORS["event_marker"], size=10, symbol="triangle-down"),
                    name="Desat start",
                ),
                row=1,
                col=1,
            )

        if show_hr:
            fig_stacked.add_trace(
                go.Scatter(
                    x=hr_x,
                    y=hr_y,
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
                        x=hr_ma_x,
                        y=hr_ma_y,
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
            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
            paper_bgcolor=THEME["bg"],
            plot_bgcolor=THEME["bg"],
            font=dict(color=THEME["text"]),
            height=520,
            xaxis2=dict(type="date", rangeslider=dict(visible=True)),
        )
        fig_stacked.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
        fig_stacked.update_yaxes(title_text="HR (bpm)", row=2, col=1)

        spo2_mean = summary["spo2_mean"]
        hr_mean = summary["hr_mean"]

        cards = [
            html.Div(
                [
                    html.Div("Analysed duration", className="metric-label"),
                    html.Div(f"{summary['analysed_duration_hours']:.2f} h", className="metric-value"),
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
                        else f"{summary['spo2_min']}% / {format_percentage(spo2_mean)}",
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
                    html.Div(f"{summary['time_below_threshold_sec']:.1f} s", className="metric-value"),
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

        if not desats.empty:
            formatted_events = desats.copy()
            formatted_events["start_time_local"] = formatted_events["start_time_local"].apply(
                format_timestamp_human
            )
            formatted_events["end_time_local"] = formatted_events["end_time_local"].apply(
                format_timestamp_human
            )
            formatted_events["duration_sec"] = formatted_events["duration_sec"].map(lambda v: f"{v:.1f} s")
            formatted_events["nadir_spo2"] = formatted_events["nadir_spo2"].map(
                lambda v: f"{v} %" if v is not None else "n/a"
            )
            formatted_events["mean_spo2"] = formatted_events["mean_spo2"].map(format_percentage)
            events_data = formatted_events.to_dict("records")
        else:
            events_data = []

        return summary_panel, fig_overlay, events_data, fig_stacked
