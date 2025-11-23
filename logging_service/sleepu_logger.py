#!/usr/bin/env python3
import subprocess
import csv
import re
import datetime as dt
from pathlib import Path

# Paths for your setup
REPO_DIR = Path("/home/ethermious/repos/sleep_monitoring")
VENV_PY = REPO_DIR / "venv" / "bin" / "python"
SCRIPT = REPO_DIR / "sleepu" / "ble" / "viatom-ble.py"

LOG_DIR = Path("/home/ethermious/sleepu_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Command that runs viatom-ble with verbose console output
VIATOM_CMD = [
    str(VENV_PY),
    str(SCRIPT),
    "-v",
    "-c",
]

# Sample line format:
# 2025-11-22 00:50:34.660 [78665] DEBUG SpO2: 98% HR: 70 bpm      PI: 21      Movement: 1     Battery: 52%
LINE_RE = re.compile(
    r"SpO2:\s*(\d+)%\s*HR:\s*(\d+)\s*bpm\s*PI:\s*([\d.]+)\s*Movement:\s*(\d+)\s*Battery:\s*(\d+)%",
    re.IGNORECASE,
)


def get_csv_path(ts: dt.datetime) -> Path:
    return LOG_DIR / f"sleepu_{ts:%Y%m%d}.csv"


def append_row(ts, spo2, hr, pi, movement, battery):
    csv_path = get_csv_path(ts)
    is_new = not csv_path.exists()

    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "spo2", "hr", "pi", "movement", "battery"])
        writer.writerow([ts.isoformat(), spo2, hr, pi, movement, battery])


def main():
    # Run viatom-ble and stream its output
    with subprocess.Popen(
        VIATOM_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as proc:
        for line in proc.stdout:
            # Echo raw output so you can see what is happening
            print(line, end="")

            m = LINE_RE.search(line)
            if not m:
                continue

            spo2 = int(m.group(1))
            hr = int(m.group(2))
            pi = float(m.group(3))
            movement = int(m.group(4))
            battery = int(m.group(5))

            ts = dt.datetime.now()
            append_row(ts, spo2, hr, pi, movement, battery)


if __name__ == "__main__":
    main()
