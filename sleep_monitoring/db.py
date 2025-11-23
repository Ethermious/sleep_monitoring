"""Database helpers and schema creation for Sleep Monitoring."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled.

    This helper also ensures the parent directory exists and raises a clear error
    if SQLite cannot open the file (commonly because the path is not writable).
    """
    path = Path(db_path) if db_path is not None else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(path)
    except sqlite3.OperationalError as exc:  # pragma: no cover - defensive
        raise sqlite3.OperationalError(
            f"Unable to open database at {path}. Ensure the directory exists and is writable."
        ) from exc

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Ensure the database exists with required tables and indexes."""
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                notes TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                sleep_date TEXT NOT NULL,
                start_time_utc TEXT,
                end_time_utc TEXT,
                created_at_utc TEXT NOT NULL,
                note TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                timestamp_utc TEXT NOT NULL,
                spo2 INTEGER,
                hr INTEGER,
                pi INTEGER,
                movement INTEGER,
                battery INTEGER
            );
            """
        )
        cur.execute(
            """CREATE INDEX IF NOT EXISTS idx_samples_session_time
            ON samples(session_id, timestamp_utc);"""
        )
        cur.execute(
            """CREATE INDEX IF NOT EXISTS idx_sessions_sleep_date
            ON sessions(sleep_date);"""
        )
        conn.commit()
        _ensure_default_user(conn)
    finally:
        conn.close()


def _ensure_default_user(conn: sqlite3.Connection, user_id: int = config.DEFAULT_USER_ID) -> None:
    """Insert a default user record if it does not exist."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (id, name, notes) VALUES (?, ?, ?)",
            (user_id, "default", "primary user"),
        )
        conn.commit()


def touch_session(
    user_id: int,
    sleep_date: str,
    *,
    start_time_utc: Optional[datetime] = None,
    db_path: Path | None = None,
) -> int:
    """Get or create a session record and return its ID.

    If creating a new session, start and end times are initialized to ``start_time_utc``
    when provided.
    """
    conn = get_connection(db_path)
    try:
        _ensure_default_user(conn, user_id)
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM sessions WHERE user_id = ? AND sleep_date = ?",
            (user_id, sleep_date),
        )
        row = cur.fetchone()
        now_iso = datetime.now(timezone.utc).isoformat()
        if row:
            return row["id"]

        cur.execute(
            """
            INSERT INTO sessions (user_id, sleep_date, start_time_utc, end_time_utc, created_at_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                sleep_date,
                start_time_utc.isoformat() if start_time_utc else None,
                start_time_utc.isoformat() if start_time_utc else None,
                now_iso,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_session_end_time(session_id: int, end_time_utc: datetime, db_path: Path | None = None) -> None:
    """Update the end time for a session."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE sessions SET end_time_utc = ? WHERE id = ?",
            (end_time_utc.isoformat(), session_id),
        )
        conn.commit()
    finally:
        conn.close()
