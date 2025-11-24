#!/usr/bin/env python3
"""
SleepU / Viatom BLE Data Visualizer

- Lists all sleepu_YYYYMMDD.csv files in LOG_DIR
- Lets you pick a night
- Shows summary stats and interactive plots (SpO2, HR, PI, movement)
- Live mode: auto-refresh and show only the last N seconds/minutes/hours
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# -------------------------------------------------------------------
# CONFIG: set this to wherever your CSVs live
# On the Pi it'll be: /home/ethermious/sleepu_logs
# After copying to laptop, you might use: Path("./sleepu_logs")
# -------------------------------------------------------------------
LOG_DIR = Path("/home/ethermious/sleepu_logs")


# -------------------------------------------------------------------
# Data loading helpers
# -------------------------------------------------------------------
@st.cache_data
def list_log_files(log_dir: Path):
    files = sorted(log_dir.glob("sleepu_*.csv"))
    return files


@st.cache_data
def load_log(path: Path, mtime: float) -> pd.DataFrame:
    """
    Load and parse one CSV.

    mtime is used as a dummy argument so that when the file changes on disk
    (new rows appended), Streamlit will invalidate the cache and reload.
    """
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Ensure expected columns exist
    expected = {"spo2", "hr", "pi", "movement", "battery"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {missing}")

    return df


def compute_desaturation_stats(df: pd.DataFrame, thresh: int):
    df = df.copy()
    df["desat"] = df["spo2"] < thresh

    # Estimate time between samples using timestamp differences
    df["dt_sec"] = df["timestamp"].diff().dt.total_seconds()
    if df["dt_sec"].iloc[1:].notna().any():
        median_dt = df["dt_sec"].iloc[1:].median()
    else:
        median_dt = 2.0
    df["dt_sec"] = df["dt_sec"].fillna(median_dt)

    desat_seconds = df.loc[df["desat"], "dt_sec"].sum()
    total_seconds = df["dt_sec"].sum()
    desat_minutes = desat_seconds / 60.0
    total_minutes = total_seconds / 60.0 if total_seconds > 0 else 0.0
    desat_pct_time = (desat_seconds / total_seconds * 100.0) if total_seconds > 0 else 0.0

    # Very simple event count: transitions from non-desat -> desat
    df["desat_shift"] = df["desat"].shift(fill_value=False)
    event_count = int(((df["desat"] == True) & (df["desat_shift"] == False)).sum())

    return {
        "desat_seconds": desat_seconds,
        "desat_minutes": desat_minutes,
        "total_minutes": total_minutes,
        "desat_pct_time": desat_pct_time,
        "event_count": event_count,
    }


# -------------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------------
st.set_page_config(
    page_title="SleepU Oximetry Dashboard",
    layout="wide",
)

st.title("SleepU / Viatom Sleep Oximetry Dashboard")

files = list_log_files(LOG_DIR)
if not files:
    st.error(f"No CSV logs found in {LOG_DIR}.")
    st.stop()

# Map filenames to a friendly label (date)
options = []
for f in files:
    # Extract date from filename: sleepu_YYYYMMDD.csv
    date_str = f.stem.replace("sleepu_", "")
    options.append((date_str, f))

labels = [o[0] for o in options]
label_to_path = {label: path for label, path in options}

selected_label = st.sidebar.selectbox("Select night (by date)", labels, index=len(labels) - 1)
selected_path = label_to_path[selected_label]
st.sidebar.write(f"File: `{selected_path.name}`")

# -------------------------------------------------------------------
# View / live controls
# -------------------------------------------------------------------
st.sidebar.markdown("### View mode")
view_mode = st.sidebar.radio("Mode", ["Full night", "Live window"], index=1)

live_mode = st.sidebar.checkbox("Auto-refresh (live-ish)", value=True)
refresh_sec = st.sidebar.slider("Refresh interval (seconds)", 2, 30, 5, step=1)

# Live window size controls with unit selection
st.sidebar.markdown("### Live window size")
window_unit = st.sidebar.radio("Window unit", ["Seconds", "Minutes", "Hours"], index=1)

if window_unit == "Seconds":
    window_value = st.sidebar.slider("Window length (seconds)", 10, 600, 30, step=10)
    window_sec = window_value
    window_label = f"{window_value} seconds"
elif window_unit == "Minutes":
    window_value = st.sidebar.slider("Window length (minutes)", 1, 120, 5, step=1)
    window_sec = window_value * 60
    window_label = f"{window_value} minutes"
else:  # Hours
    window_value = st.sidebar.slider("Window length (hours)", 1, 12, 1, step=1)
    window_sec = window_value * 3600
    window_label = f"{window_value} hours"

# Desaturation threshold
st.sidebar.markdown("### Desaturation threshold")
desat_thresh = st.sidebar.slider("SpO₂ desaturation threshold (%)", min_value=80, max_value=95, value=90, step=1)

# Auto-refresh when live_mode is enabled
if live_mode:
    st_autorefresh(interval=refresh_sec * 1000, key="sleepu_live_refresh")

# -------------------------------------------------------------------
# Load data
# -------------------------------------------------------------------
mtime = selected_path.stat().st_mtime
df = load_log(selected_path, mtime)

if df.empty:
    st.warning("Selected log is empty.")
    st.stop()

# Compute stats on the full data (so far)
duration = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]
stats_desat = compute_desaturation_stats(df, desat_thresh)

min_spo2 = df["spo2"].min()
mean_spo2 = df["spo2"].mean()
min_hr = df["hr"].min()
max_hr = df["hr"].max()
mean_hr = df["hr"].mean()

# -------------------------------------------------------------------
# Determine which slice to plot (full vs live window)
# -------------------------------------------------------------------
df_plot = df.copy()
df_plot["desat"] = df_plot["spo2"] < desat_thresh

if view_mode == "Live window":
    t_end = df_plot["timestamp"].iloc[-1]
    t_start = t_end - pd.Timedelta(seconds=window_sec)
    df_window = df_plot[df_plot["timestamp"] >= t_start].copy()
else:
    df_window = df_plot

if df_window.empty:
    st.warning("No data in selected window yet. Waiting for new samples...")
    st.stop()

# -------------------------------------------------------------------
# Summary cards (based on full data)
# -------------------------------------------------------------------
st.subheader("Summary (entire recording so far)")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Recording duration", f"{duration}", help="Last timestamp minus first timestamp")
col2.metric("Min SpO₂", f"{min_spo2:.0f} %")
col3.metric("Mean SpO₂", f"{mean_spo2:.1f} %")
col4.metric("Events (SpO₂ < threshold)", f"{stats_desat['event_count']}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Min HR", f"{min_hr:.0f} bpm")
col6.metric("Max HR", f"{max_hr:.0f} bpm")
col7.metric("Mean HR", f"{mean_hr:.1f} bpm")
col8.metric(
    "Time below threshold",
    f"{stats_desat['desat_minutes']:.1f} min "
    f"({stats_desat['desat_pct_time']:.1f}% of {stats_desat['total_minutes']:.1f} min)",
)

if view_mode == "Live window":
    st.caption(f"Viewing mode: **Live window** — last **{window_label}**.")
else:
    st.caption("Viewing mode: **Full night** — entire file so far.")

# -------------------------------------------------------------------
# SpO₂ plot
# -------------------------------------------------------------------
st.subheader("SpO₂ over time")

fig_spo2 = px.line(
    df_window,
    x="timestamp",
    y="spo2",
    title="SpO₂ (%)",
    labels={"timestamp": "Time", "spo2": "SpO₂ (%)"},
)

# Add horizontal threshold line
fig_spo2.add_hline(y=desat_thresh, line_dash="dash", annotation_text=f"Threshold {desat_thresh}%")

# Overlay desaturation points
desat_points = df_window[df_window["desat"]]
if not desat_points.empty:
    fig_spo2.add_scatter(
        x=desat_points["timestamp"],
        y=desat_points["spo2"],
        mode="markers",
        name="Desat (< threshold)",
    )

fig_spo2.update_layout(xaxis_rangeslider_visible=(view_mode == "Full night"))
st.plotly_chart(fig_spo2, use_container_width=True)

# -------------------------------------------------------------------
# HR plot
# -------------------------------------------------------------------
st.subheader("Heart rate over time")

fig_hr = px.line(
    df_window,
    x="timestamp",
    y="hr",
    title="Heart rate (bpm)",
    labels={"timestamp": "Time", "hr": "Heart rate (bpm)"},
)
fig_hr.update_layout(xaxis_rangeslider_visible=(view_mode == "Full night"))
st.plotly_chart(fig_hr, use_container_width=True)

# -------------------------------------------------------------------
# PI and movement (optional extra plots)
# -------------------------------------------------------------------
with st.expander("Perfusion index (PI) and movement"):
    col_pi, col_mv = st.columns(2)

    with col_pi:
        fig_pi = px.line(
            df_window,
            x="timestamp",
            y="pi",
            title="Perfusion Index (PI)",
            labels={"timestamp": "Time", "pi": "PI (arbitrary units)"},
        )
        fig_pi.update_layout(xaxis_rangeslider_visible=(view_mode == "Full night"))
        st.plotly_chart(fig_pi, use_container_width=True)

    with col_mv:
        fig_mv = px.line(
            df_window,
            x="timestamp",
            y="movement",
            title="Movement index",
            labels={"timestamp": "Time", "movement": "Movement"},
        )
        fig_mv.update_layout(xaxis_rangeslider_visible=(view_mode == "Full night"))
        st.plotly_chart(fig_mv, use_container_width=True)

# Raw data preview (full df, so far)
with st.expander("Raw data table (first 200 rows of full recording)"):
    st.dataframe(df.head(200))
