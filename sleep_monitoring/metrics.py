"""Metrics and event detection for sleep monitoring."""
from __future__ import annotations

from datetime import timedelta
from typing import Dict

import pandas as pd


def _estimate_sample_interval(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    deltas = df["timestamp_local"].diff().dropna().dt.total_seconds()
    if deltas.empty:
        return 0.0
    return float(deltas.median())


def compute_desaturations(df: pd.DataFrame, threshold: int, min_duration_sec: float) -> pd.DataFrame:
    """Detect desaturation events below ``threshold`` lasting at least ``min_duration_sec``."""
    if df.empty or "spo2" not in df:
        return pd.DataFrame(
            columns=[
                "start_time_local",
                "end_time_local",
                "duration_sec",
                "nadir_spo2",
                "mean_spo2",
            ]
        )

    df_sorted = df.sort_values("timestamp_local")
    df_sorted = df_sorted.dropna(subset=["spo2", "timestamp_local"]).copy()
    if df_sorted.empty:
        return pd.DataFrame(columns=["start_time_local", "end_time_local", "duration_sec", "nadir_spo2", "mean_spo2"])

    sample_interval = _estimate_sample_interval(df_sorted)
    df_sorted["below"] = df_sorted["spo2"] < threshold
    df_sorted["group"] = df_sorted["below"].ne(df_sorted["below"].shift()).cumsum()

    events = []
    for _, group_df in df_sorted.groupby("group"):
        if not group_df["below"].iloc[0]:
            continue
        start_time = group_df["timestamp_local"].iloc[0]
        end_time = group_df["timestamp_local"].iloc[-1]
        duration = (end_time - start_time).total_seconds() + sample_interval
        if duration < min_duration_sec:
            continue
        events.append(
            {
                "start_time_local": start_time,
                "end_time_local": end_time + timedelta(seconds=sample_interval),
                "duration_sec": duration,
                "nadir_spo2": int(group_df["spo2"].min()),
                "mean_spo2": float(group_df["spo2"].mean()),
            }
        )

    return pd.DataFrame(events)


def compute_time_below_threshold(df: pd.DataFrame, threshold: int) -> Dict[str, float]:
    """Calculate total time and fraction spent below the SpO2 threshold."""
    if df.empty:
        return {"total_seconds_below": 0.0, "fraction_of_analysed_time": 0.0}

    df_sorted = df.sort_values("timestamp_local")
    sample_interval = _estimate_sample_interval(df_sorted)
    df_sorted["below"] = df_sorted["spo2"] < threshold
    df_sorted["group"] = df_sorted["below"].ne(df_sorted["below"].shift()).cumsum()

    total_below = 0.0
    for _, group_df in df_sorted.groupby("group"):
        if not group_df["below"].iloc[0]:
            continue
        start_time = group_df["timestamp_local"].iloc[0]
        end_time = group_df["timestamp_local"].iloc[-1]
        total_below += (end_time - start_time).total_seconds() + sample_interval

    analysed_duration = analysed_duration_seconds(df_sorted)
    fraction = (total_below / analysed_duration) if analysed_duration else 0.0
    return {"total_seconds_below": total_below, "fraction_of_analysed_time": fraction}


def analysed_duration_seconds(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    df_sorted = df.sort_values("timestamp_local")
    start = df_sorted["timestamp_local"].iloc[0]
    end = df_sorted["timestamp_local"].iloc[-1]
    return (end - start).total_seconds()


def compute_odi(events_df: pd.DataFrame, analysed_duration_hours: float) -> float:
    """Compute ODI as events per hour."""
    if analysed_duration_hours <= 0:
        return 0.0
    return float(len(events_df) / analysed_duration_hours)


def summarize_session(
    df: pd.DataFrame,
    threshold: int,
    min_duration_sec: float,
) -> Dict[str, float]:
    """Generate summary metrics for a session."""
    if df.empty:
        return {
            "analysed_duration_hours": 0.0,
            "spo2_min": None,
            "spo2_mean": None,
            "hr_min": None,
            "hr_mean": None,
            "time_below_threshold_sec": 0.0,
            "time_below_threshold_fraction": 0.0,
            "events_count": 0,
            "odi": 0.0,
        }

    df_sorted = df.sort_values("timestamp_local")
    analysed_hours = analysed_duration_seconds(df_sorted) / 3600.0
    desats = compute_desaturations(df_sorted, threshold, min_duration_sec)
    below_stats = compute_time_below_threshold(df_sorted, threshold)

    return {
        "analysed_duration_hours": analysed_hours,
        "spo2_min": int(df_sorted["spo2"].min()) if df_sorted["spo2"].notna().any() else None,
        "spo2_mean": float(df_sorted["spo2"].mean()) if df_sorted["spo2"].notna().any() else None,
        "hr_min": int(df_sorted["hr"].min()) if df_sorted["hr"].notna().any() else None,
        "hr_mean": float(df_sorted["hr"].mean()) if df_sorted["hr"].notna().any() else None,
        "time_below_threshold_sec": below_stats["total_seconds_below"],
        "time_below_threshold_fraction": below_stats["fraction_of_analysed_time"],
        "events_count": int(len(desats)),
        "odi": compute_odi(desats, analysed_hours),
    }
