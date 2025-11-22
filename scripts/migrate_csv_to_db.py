"""Migrate historical CSV logs into SQLite using sleep_date mapping."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from sleep_monitoring import config, data_io


EXPECTED_COLUMNS = ["timestamp", "spo2", "hr", "pi", "movement", "battery"]


def migrate_file(path: Path, user_id: int) -> None:
    print(f"[migrate] Loading {path}")
    df = pd.read_csv(path)
    if "timestamp_utc" in df.columns:
        df.rename(columns={"timestamp_utc": "timestamp"}, inplace=True)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} in {path}")

    cache: dict[str, set[datetime]] = {}

    for _, row in df.iterrows():
        ts = datetime.fromisoformat(str(row["timestamp"])).replace(tzinfo=timezone.utc)
        sleep_date = data_io.compute_sleep_date(ts)
        date_key = sleep_date.isoformat()
        if date_key not in cache:
            existing = data_io.load_session_samples(user_id, sleep_date)
            cache[date_key] = set(existing["timestamp_utc"]) if not existing.empty else set()
        if ts in cache[date_key]:
            continue

        session_id = data_io.get_or_create_session_id(user_id, sleep_date, start_time_utc=ts)
        data_io.insert_sample(
            session_id=session_id,
            timestamp_utc=ts,
            spo2=int(row.get("spo2")) if not pd.isna(row.get("spo2")) else None,
            hr=int(row.get("hr")) if not pd.isna(row.get("hr")) else None,
            pi=int(row.get("pi")) if not pd.isna(row.get("pi")) else None,
            movement=int(row.get("movement")) if not pd.isna(row.get("movement")) else None,
            battery=int(row.get("battery")) if not pd.isna(row.get("battery")) else None,
        )
        cache[date_key].add(ts)
    print(f"[migrate] Completed {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import historical CSVs into SQLite")
    parser.add_argument("--directory", type=Path, default=config.CSV_DIR, help="Directory containing CSV logs")
    parser.add_argument("--user", type=int, default=config.DEFAULT_USER_ID, help="User ID")
    args = parser.parse_args()

    data_io.init_db()

    for csv_path in sorted(args.directory.glob("*.csv")):
        migrate_file(csv_path, args.user)


if __name__ == "__main__":
    main()
