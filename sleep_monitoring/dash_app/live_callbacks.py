"""Callbacks for the Live tab."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output

from sleep_monitoring import config, data_io

from .theme import COLORS, THEME
from .utils import apply_gap_breaks, empty_figure


def register_live_callbacks(app):
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
            empty_fig = empty_figure("No live data yet")
            return ("SpO₂: --", "HR: --", "Battery: --", "Last sample: --", empty_fig, empty_fig)

        latest = df.iloc[-1]
        now_utc = datetime.now(timezone.utc)
        time_since = now_utc - latest["timestamp_utc"]

        window_min = window_min or 30
        window_start = now_utc - timedelta(minutes=int(window_min))
        mask = df["timestamp_utc"] >= window_start
        window_df = df[mask].copy().sort_values("timestamp_utc")

        fig_overlay = make_subplots(specs=[[{"secondary_y": True}]])

        spo2_x, spo2_y = apply_gap_breaks(window_df["timestamp_local"], window_df["spo2"])
        hr_x, hr_y = apply_gap_breaks(window_df["timestamp_local"], window_df["hr"])

        if "spo2" in (series or []):
            fig_overlay.add_trace(
                go.Scatter(
                    x=spo2_x,
                    y=spo2_y,
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
                    x=hr_x,
                    y=hr_y,
                    name="HR (raw)",
                    mode="lines+markers",
                    opacity=0.4,
                    line=dict(color=COLORS["hr_raw"]),
                    marker=dict(color=COLORS["hr_raw"]),
                ),
                secondary_y=True,
            )

        spo2_ma = None
        hr_ma = None
        spo2_ma_x = spo2_ma_y = hr_ma_x = hr_ma_y = None
        if smoothing_sec and smoothing_sec > 0 and len(window_df) > 1:
            smoothing_sec = int(smoothing_sec)
            w = window_df.set_index("timestamp_utc")
            spo2_ma = w["spo2"].rolling(f"{smoothing_sec}s").mean()
            hr_ma = w["hr"].rolling(f"{smoothing_sec}s").mean()

            spo2_ma_x, spo2_ma_y = apply_gap_breaks(window_df["timestamp_local"], spo2_ma)
            hr_ma_x, hr_ma_y = apply_gap_breaks(window_df["timestamp_local"], hr_ma)

            if "spo2" in (series or []):
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

            if "hr" in (series or []):
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
            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
            paper_bgcolor=THEME["bg"],
            plot_bgcolor=THEME["bg"],
            font=dict(color=THEME["text"]),
            uirevision="live",
            height=520,
            xaxis=dict(type="date", rangeslider=dict(visible=False)),
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

        if "spo2" in (series or []):
            fig_stacked.add_trace(
                go.Scatter(
                    x=spo2_x,
                    y=spo2_y,
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
                        x=spo2_ma_x,
                        y=spo2_ma_y,
                        name=f"SpO₂ {smoothing_sec}s MA",
                        mode="lines",
                        line=dict(color=COLORS["spo2_ma"], width=2),
                    ),
                    row=1,
                    col=1,
                )

        if "hr" in (series or []):
            fig_stacked.add_trace(
                go.Scatter(
                    x=hr_x,
                    y=hr_y,
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
                        x=hr_ma_x,
                        y=hr_ma_y,
                        name=f"HR {smoothing_sec}s MA",
                        mode="lines",
                        line=dict(color=COLORS["hr_ma"], width=2),
                    ),
                    row=2,
                    col=1,
                )

        fig_stacked.add_hline(
            y=spo2_threshold,
            line_dash="dash",
            line_color=COLORS["spo2_threshold"],
            annotation_text=f"{spo2_threshold} % threshold",
            annotation_position="bottom right",
            row=1,
            col=1,
        )

        fig_stacked.update_layout(
            title=f"Live SpO₂ / HR - stacked view",  # title retained for consistency
            template="plotly_dark",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=60, b=100),
            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
            paper_bgcolor=THEME["bg"],
            plot_bgcolor=THEME["bg"],
            font=dict(color=THEME["text"]),
            height=520,
            xaxis2=dict(type="date", rangeslider=dict(visible=False)),
        )
        fig_stacked.update_yaxes(title_text="SpO₂ (%)", row=1, col=1, range=[70, 100])
        fig_stacked.update_yaxes(title_text="HR (bpm)", row=2, col=1)

        return (
            f"SpO₂: {latest['spo2'] if latest['spo2'] is not None else '--'} %",
            f"HR: {latest['hr'] if latest['hr'] is not None else '--'} bpm",
            f"Battery: {latest['battery'] if latest['battery'] is not None else '--'} %",
            f"Last sample: {int(time_since.total_seconds())} s ago",
            fig_overlay,
            fig_stacked,
        )
