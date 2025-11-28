"""Shared visual design tokens for the dashboard.

All colors and spacing decisions originate here so layouts and callbacks stay
consistent and easy to adjust for clinical readability.
"""
from __future__ import annotations

from pathlib import Path

APP_TITLE = "Sleep Monitoring"
APP_ASSETS_PATH = Path(__file__).parent / "assets"

THEME = {
    "bg": "#020617",
    "panel": "#0b1224",
    "card": "#0f172a",
    "text": "#e5e7eb",
    "muted": "#9ca3af",
    "border": "#1f2937",
    "accent": "#3b82f6",
}

COLORS = {
    # SpO2 family (green)
    "spo2_raw": "#22c55e",  # SpO2 raw
    "spo2_ma": "#16a34a",  # SpO2 moving average

    # Heart rate family (blue)
    "hr_raw": "#3b82f6",  # HR raw
    "hr_ma": "#60a5fa",  # HR moving average

    # SpO2 threshold line
    "spo2_threshold": "#c2d81d",

    # Event markers (desats, etc.)
    "event_marker": "#f97316",  # orange, stands out
}
