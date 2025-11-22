"""Database access and I/O helpers for sleep monitoring."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config, db

LOCAL_TZ = ZoneInfo(config.TIMEZONE)


def init_db(db_path: Path | None = None) -> None:
    """Initialize the SQLite database and default user."""
    db.init_db(db_path)


def compute_sleep_date(dt_utc: datetime) -> date:
    """Compute the sleep_date for a UTC datetime using local time rules.

    A timestamp belongs to the previous date if its local time-of-day is before 12:01pm.
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(LOCAL_TZ)
    cutoff = time(hour=12, minute=1)
    if dt_local.time() < cutoff:
        return (dt_local - timedelta(days=1)).date()
    return dt_local.date()


def get_or_create_session_id(
    user_id: int,
    sleep_date: date,
    *,
    start_time_utc: Optional[datetime] = None,
    db_path: Path | None = None,
) -> int:
    """Return a session ID for the given user and sleep_date, creating if needed."""
    return db.touch_session(
        user_id=user_id,
        sleep_date=sleep_date.isoformat(),
        start_time_utc=start_time_utc,
        db_path=db_path,
    )


def insert_sample(
    session_id: int,
    timestamp_utc: datetime,
    *,
    spo2: Optional[int] = None,
    hr: Optional[int] = None,
    pi: Optional[int] = None,
    movement: Optional[int] = None,
    battery: Optional[int] = None,
    db_path: Path | None = None,
) -> int:
    """Insert a sample row and update the session end time."""
    if timestamp_utc.tzinfo is None:
        timestamp_utc = timestamp_utc.replace(tzinfo=timezone.utc)
    conn = db.get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO samples (session_id, timestamp_utc, spo2, hr, pi, movement, battery)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                timestamp_utc.isoformat(),
                spo2,
                hr,
                pi,
                movement,
                battery,
            ),
        )
        conn.commit()
        db.update_session_end_time(session_id, timestamp_utc, db_path=db_path)
        return cur.lastrowid
    finally:
        conn.close()


def list_sleep_dates(user_id: int = config.DEFAULT_USER_ID, db_path: Path | None = None) -> list[date]:
    """List sleep dates sorted descending for the given user."""
    conn = db.get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sleep_date FROM sessions WHERE user_id = ? ORDER BY sleep_date DESC",
            (user_id,),
        )
        return [date.fromisoformat(row[0]) for row in cur.fetchall()]
    finally:
        conn.close()


def _get_session_id(
    user_id: int,
    sleep_date: date,
    conn: sqlite3.Connection,
) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sessions WHERE user_id = ? AND sleep_date = ?",
        (user_id, sleep_date.isoformat()),
    )
    row = cur.fetchone()
    return row[0] if row else None


def load_session_samples(
    user_id: int,
    sleep_date: date,
    db_path: Path | None = None,
) -> pd.DataFrame:
    """Load samples for a session into a DataFrame."""
    conn = db.get_connection(db_path)
    try:
        session_id = _get_session_id(user_id, sleep_date, conn)
        if session_id is None:
            return pd.DataFrame(
                columns=[
                    "timestamp_utc",
                    "timestamp_local",
                    "spo2",
                    "hr",
                    "pi",
                    "movement",
                    "battery",
                ]
            )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp_utc, spo2, hr, pi, movement, battery
            FROM samples
            WHERE session_id = ?
            ORDER BY timestamp_utc
            """,
            (session_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return pd.DataFrame(
            columns=[
                "timestamp_utc",
                "timestamp_local",
                "spo2",
                "hr",
                "pi",
                "movement",
                "battery",
            ]
        )

    df = pd.DataFrame(rows, columns=["timestamp_utc", "spo2", "hr", "pi", "movement", "battery"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert(LOCAL_TZ)
    return df
