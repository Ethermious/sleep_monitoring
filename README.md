# Sleep Monitoring

Tools for collecting, storing, and reviewing Wellue SleepU oximeter data on a Raspberry Pi.

## Repository layout
- `sleep_monitoring/`: primary Python package with the logger, data access helpers, metrics, and the Dash UI code.
- `apps/`: Streamlit / Dash entry points for quick experimentation (`sleepu_clinic_app.py`, `sleepu_dashboard.py`).
- `scripts/`: operational utilities (database migrations) and legacy one-off scripts (`scripts/legacy/sleepu_logger.py`).
- `systemd/`: unit files for running the logger as a service.
- `sleepu/`: vendor BLE script (`sleepu/ble/viatom-ble.py`) invoked by the logger.

## Overview of key modules
- `sleep_monitoring.logger_service`: systemd-friendly logger that streams verbose output from `viatom-ble.py`, stores samples in SQLite, and writes per-sleep-date CSV backups.
- `sleep_monitoring.data_io`: database access helpers and the reusable `compute_sleep_date` rule.
- `sleep_monitoring.metrics`: desaturation detection and summary metrics.
- `sleep_monitoring.dash_app`: Dash UI with Live and Review tabs.
- `scripts/migrate_csv_to_db.py`: import existing CSV logs into SQLite.

## Paths and configuration
Defaults are centralized in `sleep_monitoring/config.py`:
- Database: `/home/ethermious/sleepu_logs/sleepu.db`
- CSV backups: `/home/ethermious/sleepu_logs`
- External BLE script: `/home/ethermious/repos/sleep_monitoring/sleepu/ble/viatom-ble.py`
- Time zone for `sleep_date` mapping: `America/Chicago`

## Sleep date mapping
All timestamps are stored in UTC and mapped to a `sleep_date` using local time:
- If local time-of-day is before 12:01 pm, the sample belongs to the previous date.
- Otherwise, it belongs to the current local date.

## Running the logger
```bash
python -m sleep_monitoring.logger_service
```
The service launches `viatom-ble.py -v -c`, appends rows to SQLite, and writes `sleepu_YYYYMMDD.csv` alongside the database. The logger will create `/home/ethermious/sleepu_logs` (or the configured paths) if missing; ensure the parent directory is writable by the service user to avoid "unable to open database file" errors.

A sample systemd unit is provided at `systemd/sleep_monitoring_logger.service`. Update paths if needed, then install with:
```bash
sudo cp systemd/sleep_monitoring_logger.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sleep_monitoring_logger
```

## Dash application
Run the Dash app for live monitoring and review:
```bash
python -m sleep_monitoring.dash_app.app
```
It exposes a Live tab for the current night and a Review tab for historical sessions.

## Migrating historical CSV logs
Import existing CSV files from the backup directory into SQLite:
```bash
python scripts/migrate_csv_to_db.py --directory /home/ethermious/sleepu_logs
```

## Development
- Python 3.11
- Dependencies defined in `pyproject.toml`
- Code is organized as a Python package inside the repository.
