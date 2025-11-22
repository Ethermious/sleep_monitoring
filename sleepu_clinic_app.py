#!/usr/bin/env python3
"""
SleepU / Viatom BLE – Clinic-style Oximetry Review App

For reviewing overnight SpO₂ / HR data from SleepU CSV logs.

Assumptions:
- CSV has columns: timestamp, spo2, hr, pi, movement, battery
- One row per sample (typically every ~2 s)
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# =============================================================================
# STEP 1 – CONFIG: where the CSVs live
# =============================================================================
LOG_DIR = Path("/home/ethermious/sleepu_logs")


# =============================================================================
# STEP 2 – Data loading / processing helpers
# =============================================================================
@st.cache_data
def list_log_files(log_dir: Path):
    """Return all SleepU CSV logs sorted by name."""
    files = sorted(log_dir.glob("sleepu_*.csv"))
    return files


@st.cache_data
def load_log(path: Path) -> pd.DataFrame:
    """
    Load one log file and do basic time preprocessing.

    - Parse timestamp
    - Sort by time
    - Compute dt_sec between samples
    """
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    expected = {"spo2", "hr", "pi", "movement", "battery"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {missing}")

    # Basic time delta
    df["dt_sec"] = df["timestamp"].diff().dt.total_seconds()
    if df["dt_sec"].iloc[1:].notna().any():
        median_dt = df["dt_sec"].iloc[1:].median()
    else:
        median_dt = 2.0
    df["dt_sec"] = df["dt_sec"].fillna(median_dt)

    return df


def trim_recording(df: pd.DataFrame, trim_start_min: float, trim_end_min: float) -> pd.DataFrame:
    """
    STEP 2a – Exclude first/last few minutes (settling / wake).

    Typical clinic usage:
    - Remove initial “hook-up / settling” period
    - Remove final “wake / sensor-off” period
    """
    t0 = df["timestamp"].iloc[0]
    t1 = df["timestamp"].iloc[-1]

    t_start = t0 + pd.Timedelta(minutes=trim_start_min)
    t_end = t1 - pd.Timedelta(minutes=trim_end_min)

    if t_end <= t_start:
        # If trims overlap, just return empty frame
        return df.iloc[0:0].copy()

    return df[(df["timestamp"] >= t_start) & (df["timestamp"] <= t_end)].copy()


def apply_artifact_filters(
    df: pd.DataFrame,
    min_spo2: int,
    max_spo2: int,
    min_hr: int,
    max_hr: int,
) -> pd.DataFrame:
    """
    STEP 2b – Very simple artifact filtering: drop implausible values.

    This is intentionally conservative; a sleep lab might add more logic here:
    - Signal quality indices
    - Motion artifacts
    - Pulse search flags, etc.
    """
    m = (
        (df["spo2"].between(min_spo2, max_spo2))
        & (df["hr"].between(min_hr, max_hr))
    )
    return df[m].copy()


def detect_desaturation_events(
    df: pd.DataFrame,
    thresh: int,
    min_duration_sec: float,
):
    """
    STEP 2c – Identify contiguous segments where SpO₂ < thresh.
    Only keep segments whose total duration >= min_duration_sec.

    Returns:
        events_df: DataFrame with columns:
            start_time, end_time, duration_sec, nadir_spo2, mean_spo2
        stats: dict with ODI-style metrics
    """
    if df.empty:
        empty_events = pd.DataFrame(
            columns=["start_time", "end_time", "duration_sec", "nadir_spo2", "mean_spo2"]
        )
        stats = {
            "event_count": 0,
            "odi_per_hour": 0.0,
            "desat_minutes": 0.0,
            "total_minutes": 0.0,
            "desat_pct_time": 0.0,
        }
        return empty_events, stats

    df = df.copy()
    df["desat"] = df["spo2"] < thresh

    # Label contiguous segments where desat is constant (True/False)
    df["seg_id"] = (df["desat"] != df["desat"].shift(fill_value=False)).cumsum()

    segments = []
    total_desat_seconds = 0.0

    for seg_id, seg in df.groupby("seg_id"):
        if not seg["desat"].iloc[0]:
            # Not a desaturation segment
            continue

        duration = seg["dt_sec"].sum()
        if duration < min_duration_sec:
            # Below minimum duration threshold for an "event"
            total_desat_seconds += duration
            continue

        total_desat_seconds += duration
        segments.append(
            {
                "start_time": seg["timestamp"].iloc[0],
                "end_time": seg["timestamp"].iloc[-1],
                "duration_sec": duration,
                "nadir_spo2": seg["spo2"].min(),
                "mean_spo2": seg["spo2"].mean(),
            }
        )

    events_df = pd.DataFrame(segments)

    total_seconds = df["dt_sec"].sum()
    total_minutes = total_seconds / 60.0 if total_seconds > 0 else 0.0
    desat_minutes = total_desat_seconds / 60.0
    desat_pct_time = (total_desat_seconds / total_seconds * 100.0) if total_seconds > 0 else 0.0

    event_count = len(events_df)
    hours = total_seconds / 3600.0 if total_seconds > 0 else 0.0
    odi_per_hour = event_count / hours if hours > 0 else 0.0

    stats = {
        "event_count": event_count,
        "odi_per_hour": odi_per_hour,
        "desat_minutes": desat_minutes,
        "total_minutes": total_minutes,
        "desat_pct_time": desat_pct_time,
    }
    return events_df, stats


# =============================================================================
# STEP 3 – Streamlit app shell
# =============================================================================
st.set_page_config(
    page_title="SleepU Oximetry – Clinic Review",
    layout="wide",
)

st.title("SleepU Oximetry – Clinic Review Dashboard")

files = list_log_files(LOG_DIR)
if not files:
    st.error(f"No CSV logs found in {LOG_DIR}.")
    st.stop()

# Map filenames to date-like labels
options = []
for f in files:
    date_str = f.stem.replace("sleepu_", "")
    options.append((date_str, f))

labels = [o[0] for o in options]
label_to_path = {label: path for label, path in options}

selected_label = st.sidebar.selectbox("Select study (by date)", labels, index=len(labels) - 1)
selected_path = label_to_path[selected_label]
st.sidebar.write(f"File: `{selected_path.name}`")


# =============================================================================
# STEP 4 – Sidebar: analysis & display controls
# =============================================================================
st.sidebar.markdown("### Recording trimming")
trim_start_min = st.sidebar.slider(
    "Exclude first minutes (settling)",
    min_value=0,
    max_value=60,
    value=5,
    step=1,
)
trim_end_min = st.sidebar.slider(
    "Exclude last minutes (wake / disconnection)",
    min_value=0,
    max_value=60,
    value=5,
    step=1,
)

st.sidebar.markdown("### Artifact filters")
min_spo2_valid = st.sidebar.slider("Min valid SpO₂", 50, 95, 70, step=1)
max_spo2_valid = st.sidebar.slider("Max valid SpO₂", 95, 100, 100, step=1)
min_hr_valid = st.sidebar.slider("Min valid HR (bpm)", 30, 80, 40, step=1)
max_hr_valid = st.sidebar.slider("Max valid HR (bpm)", 80, 200, 140, step=5)

st.sidebar.markdown("### Desaturation definition")
desat_thresh = st.sidebar.slider("SpO₂ event threshold (%)", 80, 95, 90, step=1)
min_desat_duration = st.sidebar.slider(
    "Minimum event duration (seconds below threshold)",
    min_value=0,
    max_value=120,
    value=10,
    step=5,
)

st.sidebar.markdown("### Display options")

# NEW: layout toggle – this is your “align button”
view_layout = st.sidebar.radio(
    "SpO₂ / HR display",
    ["Separate timelines", "Combined (aligned)"],
    index=0,
)

# Only meaningful when timelines are separate
show_hr_overlay = st.sidebar.checkbox("Show separate HR timeline", value=True)

show_movement = st.sidebar.checkbox("Show movement index plot", value=True)


# =============================================================================
# STEP 5 – Load and preprocess data
# =============================================================================
df_raw = load_log(selected_path)

if df_raw.empty:
    st.warning("Selected log is empty.")
    st.stop()

# Apply trim
df = trim_recording(df_raw, trim_start_min, trim_end_min)
if df.empty:
    st.warning("All data trimmed away with current start/end settings.")
    st.stop()

# Apply artifact filters
df = apply_artifact_filters(
    df,
    min_spo2=min_spo2_valid,
    max_spo2=max_spo2_valid,
    min_hr=min_hr_valid,
    max_hr=max_hr_valid,
)
if df.empty:
    st.warning("No data left after artifact filtering.")
    st.stop()

# Desaturation events
events_df, desat_stats = detect_desaturation_events(
    df,
    thresh=desat_thresh,
    min_duration_sec=min_desat_duration,
)

# Basic recording metrics
duration = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]
min_spo2 = df["spo2"].min()
mean_spo2 = df["spo2"].mean()
min_hr = df["hr"].min()
max_hr = df["hr"].max()
mean_hr = df["hr"].mean()


# =============================================================================
# STEP 6 – Layout: tabs
# =============================================================================
tab_overview, tab_desats, tab_trends, tab_raw = st.tabs(
    ["Overview", "Desaturations", "Trends & Distributions", "Raw data"]
)


# =============================================================================
# STEP 7 – OVERVIEW TAB
# =============================================================================
with tab_overview:
    st.subheader("Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Analyzed duration", f"{duration}", help="After trimming and artifact filters")
    col2.metric("Min SpO₂", f"{min_spo2:.0f} %")
    col3.metric("Mean SpO₂", f"{mean_spo2:.1f} %")
    col4.metric("Time < threshold", f"{desat_stats['desat_minutes']:.1f} min")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Min HR", f"{min_hr:.0f} bpm")
    col6.metric("Max HR", f"{max_hr:.0f} bpm")
    col7.metric("Mean HR", f"{mean_hr:.1f} bpm")
    col8.metric(
        "ODI (SpO₂ events/hour)",
        f"{desat_stats['odi_per_hour']:.1f}",
        help="Count of SpO₂ desaturation events per hour, using the chosen threshold and minimum duration.",
    )

    st.caption(
        f"Desat definition: SpO₂ < **{desat_thresh}%** for at least **{min_desat_duration} s**, "
        f"after trimming first {trim_start_min} min and last {trim_end_min} min."
    )

    # -------------------------------------------------------------------------
    # STEP 7a – SpO₂ + HR timelines
    #          This is where the “alignment” behavior lives.
    # -------------------------------------------------------------------------
    st.subheader("SpO₂ / HR timeline")

    df_plot = df.copy()
    df_plot["desat_flag"] = df_plot["spo2"] < desat_thresh

    if view_layout == "Combined (aligned)":
        # -----------------------------------------------------
        # Combined figure – single time axis, dual y-axes
        # This keeps SpO₂ and HR perfectly aligned when you zoom.
        # -----------------------------------------------------
        fig_combined = make_subplots(specs=[[{"secondary_y": True}]])
        
        # SpO₂ trace (primary axis)
        fig_combined.add_trace(
            go.Scatter(
                x=df_plot["timestamp"],
                y=df_plot["spo2"],
                name="SpO₂ (%)",
                mode="lines",
            ),
            secondary_y=False,
        )

        # HR trace (secondary axis)
        fig_combined.add_trace(
            go.Scatter(
                x=df_plot["timestamp"],
                y=df_plot["hr"],
                name="Heart rate (bpm)",
                mode="lines",
            ),
            secondary_y=True,
        )

        # Axis labels
        fig_combined.update_xaxes(title_text="Time")
        fig_combined.update_yaxes(title_text="SpO₂ (%)", secondary_y=False)
        fig_combined.update_yaxes(title_text="Heart rate (bpm)", secondary_y=True)

        # Threshold line on SpO₂ axis
        fig_combined.add_hline(
            y=desat_thresh,
            line_dash="dash",
            annotation_text=f"{desat_thresh}% threshold",
            annotation_position="top left",
        )

        # Desaturation segments as shaded bands
        if not events_df.empty:
            for _, ev in events_df.iterrows():
                fig_combined.add_vrect(
                    x0=ev["start_time"],
                    x1=ev["end_time"],
                    fillcolor="rgba(255,0,0,0.1)",
                    line_width=0,
                    annotation_text="desat",
                    annotation_position="top left",
                )

        fig_combined.update_layout(
            title="SpO₂ and HR over time (aligned)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        st.plotly_chart(fig_combined, use_container_width=True)

    else:
        # -----------------------------------------------------
        # Separate plots: SpO₂ first, optional HR below
        # -----------------------------------------------------
        st.markdown("**SpO₂ timeline**")

        fig_spo2 = px.line(
            df_plot,
            x="timestamp",
            y="spo2",
            labels={"timestamp": "Time", "spo2": "SpO₂ (%)"},
        )
        fig_spo2.update_layout(title="SpO₂ over time")

        # Threshold line
        fig_spo2.add_hline(
            y=desat_thresh,
            line_dash="dash",
            annotation_text=f"{desat_thresh}% threshold",
            annotation_position="top left",
        )

        # Mark desat segments
        if not events_df.empty:
            for _, ev in events_df.iterrows():
                fig_spo2.add_vrect(
                    x0=ev["start_time"],
                    x1=ev["end_time"],
                    fillcolor="rgba(255,0,0,0.1)",
                    line_width=0,
                    annotation_text="desat",
                    annotation_position="top left",
                )

        st.plotly_chart(fig_spo2, use_container_width=True)

        # Optional separate HR timeline
        if show_hr_overlay:
            st.subheader("Heart rate timeline (separate)")
            fig_hr = px.line(
                df,
                x="timestamp",
                y="hr",
                labels={"timestamp": "Time", "hr": "Heart rate (bpm)"},
            )
            fig_hr.update_layout(title="Heart rate over time")
            st.plotly_chart(fig_hr, use_container_width=True)


# =============================================================================
# STEP 8 – DESATURATIONS TAB
# =============================================================================
with tab_desats:
    st.subheader("Desaturation events")

    if events_df.empty:
        st.info("No desaturation events detected with the current settings.")
    else:
        # Brief event stats
        st.write(
            f"Detected **{desat_stats['event_count']}** events "
            f"({desat_stats['odi_per_hour']:.1f} per hour)."
        )

        # Display event table
        events_display = events_df.copy()
        events_display["duration_sec"] = events_display["duration_sec"].round(1)
        events_display["nadir_spo2"] = events_display["nadir_spo2"].round(0).astype(int)
        events_display["mean_spo2"] = events_display["mean_spo2"].round(1)

        st.dataframe(
            events_display,
            use_container_width=True,
            hide_index=True,
        )

        # Optional: histogram of event nadirs
        st.markdown("#### Nadir SpO₂ distribution")
        fig_nadir = px.histogram(
            events_display,
            x="nadir_spo2",
            nbins=20,
            labels={"nadir_spo2": "Nadir SpO₂ (%)"},
        )
        fig_nadir.update_layout(bargap=0.05)
        st.plotly_chart(fig_nadir, use_container_width=True)


# =============================================================================
# STEP 9 – TRENDS & DISTRIBUTIONS TAB
# =============================================================================
with tab_trends:
    st.subheader("Trends and distributions")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**SpO₂ distribution**")
        fig_spo2_hist = px.histogram(
            df,
            x="spo2",
            nbins=25,
            labels={"spo2": "SpO₂ (%)"},
        )
        fig_spo2_hist.update_layout(bargap=0.05)
        st.plotly_chart(fig_spo2_hist, use_container_width=True)

    with col_b:
        st.markdown("**Heart rate distribution**")
        fig_hr_hist = px.histogram(
            df,
            x="hr",
            nbins=25,
            labels={"hr": "Heart rate (bpm)"},
        )
        fig_hr_hist.update_layout(bargap=0.05)
        st.plotly_chart(fig_hr_hist, use_container_width=True)

    if show_movement:
        st.subheader("Movement index over time")
        fig_mv = px.line(
            df,
            x="timestamp",
            y="movement",
            labels={"timestamp": "Time", "movement": "Movement index"},
        )
        fig_mv.update_layout(title="Movement index over time")
        st.plotly_chart(fig_mv, use_container_width=True)


# =============================================================================
# STEP 10 – RAW DATA TAB
# =============================================================================
with tab_raw:
    st.subheader("Raw data (after trimming and artifact filters)")
    st.dataframe(df.head(500), use_container_width=True)
    st.caption("Showing first 500 rows of the analyzed segment.")
