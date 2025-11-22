"""Logging service that streams data from viatom-ble into SQLite and CSV."""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config, data_io

VERBOSE_LINE = re.compile(
    r"SpO2:\s*(?P<spo2>\d+)%\s+HR:\s*(?P<hr>\d+)\s*bpm\s*PI:\s*(?P<pi>\d+)\s*Movement:\s*(?P<movement>\d+)\s*Battery:\s*(?P<battery>\d+)",
    re.IGNORECASE,
)


class SleepLogger:
    """Capture BLE output and persist to SQLite and CSV backup files."""

    def __init__(self):
        self.current_sleep_date: Optional[str] = None
        self.csv_file: Optional[Path] = None
        self.csv_handle = None
        self.csv_writer: Optional[csv.writer] = None
        self._ensure_environment()

    @staticmethod
    def _ensure_environment() -> None:
        config.CSV_DIR.mkdir(parents=True, exist_ok=True)
        data_io.init_db()

    def _open_csv(self, sleep_date: str) -> None:
        if self.csv_handle:
            self.csv_handle.close()
        filename = config.CSV_DIR / f"sleepu_{sleep_date.replace('-', '')}.csv"
        header_needed = not filename.exists()
        self.csv_handle = open(filename, "a", newline="")
        self.csv_writer = csv.writer(self.csv_handle)
        if header_needed:
            self.csv_writer.writerow(["timestamp_utc", "spo2", "hr", "pi", "movement", "battery"])
        self.current_sleep_date = sleep_date
        self.csv_file = filename

    def _write_csv_row(self, timestamp: datetime, values: dict) -> None:
        if self.csv_writer is None:
            return
        self.csv_writer.writerow(
            [
                timestamp.isoformat(),
                values.get("spo2"),
                values.get("hr"),
                values.get("pi"),
                values.get("movement"),
                values.get("battery"),
            ]
        )
        self.csv_handle.flush()

    def _process_line(self, line: str) -> None:
        match = VERBOSE_LINE.search(line)
        if not match:
            print(f"[logger] Ignoring line: {line.strip()}")
            return

        values = {k: int(v) for k, v in match.groupdict().items()}
        now_utc = datetime.now(timezone.utc)
        sleep_date = data_io.compute_sleep_date(now_utc).isoformat()

        if self.current_sleep_date != sleep_date:
            self._open_csv(sleep_date)

        session_id = data_io.get_or_create_session_id(
            config.DEFAULT_USER_ID, data_io.compute_sleep_date(now_utc), start_time_utc=now_utc
        )
        data_io.insert_sample(
            session_id=session_id,
            timestamp_utc=now_utc,
            spo2=values.get("spo2"),
            hr=values.get("hr"),
            pi=values.get("pi"),
            movement=values.get("movement"),
            battery=values.get("battery"),
        )

        self._write_csv_row(now_utc, values)
        print(
            f"[logger] {now_utc.isoformat()} sleep_date={sleep_date} "
            f"SpO2={values['spo2']} HR={values['hr']} PI={values['pi']}"
        )

    def run(self) -> None:
        """Launch the BLE process and process its output."""
        cmd = ["sudo", str(sys.executable), str(config.VIATOM_BLE_PATH), "-v", "-c"]
        print(f"[logger] Starting BLE process: {' '.join(cmd)}")
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    if not line:
                        break
                    self._process_line(line)
            except KeyboardInterrupt:
                print("[logger] Received interrupt, shutting down.")
            finally:
                proc.terminate()
                if self.csv_handle:
                    self.csv_handle.close()


def main() -> None:
    logger = SleepLogger()
    logger.run()


if __name__ == "__main__":
    main()
