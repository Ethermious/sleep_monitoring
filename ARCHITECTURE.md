# Architecture

High-level flow from sensor to dashboard:

1. **Ingestion (logger_service + sleepu/ble)**
   - `sleep_monitoring.logger_service` launches the vendor BLE script (`sleepu/ble/viatom-ble.py`).
   - Parsed samples include SpO₂, heart rate (HR), perfusion index (PI), movement, and battery where available.
   - Samples are written to SQLite via `sleep_monitoring.db` and mirrored to per-date CSV backups.

2. **Storage and access (`sleep_monitoring.data_io`)**
   - Centralizes `compute_sleep_date` (UTC → local date with the noon cutoff) to keep nightly grouping consistent.
   - Provides helpers to list sessions, insert samples, and load full DataFrames with `timestamp_local` included.

3. **Metrics (`sleep_monitoring.metrics`)**
   - Event detection via `compute_desaturations` using configurable thresholds and minimum durations.
   - Session summarization through `summarize_session`, including time-below-threshold and ODI computations.

4. **Dash dashboard (`sleep_monitoring.dash_app`)**
   - `theme.py` defines the dark palette and accent colors used everywhere.
   - `layouts.py` builds the shell and tab routing; tab layout files (`live_layout.py`, `review_layout.py`, `events_layout.py`) are pure UI.
   - Callback modules (`live_callbacks.py`, `review_callbacks.py`, `events_callbacks.py`) fetch data through `data_io` and compute metrics through `metrics` without redefining business logic.
   - Entry point remains `python -m sleep_monitoring.dash_app.app` which constructs the Dash instance via `create_app()`.

## Extending the system
- **New sensors:** add columns to the database schema and extend `data_io` to surface them; update `theme.py` with new colors before visualizing.
- **Additional metrics:** implement in `metrics.py` and wire into callbacks; keep function signatures stable.
- **New dashboards:** reuse the pattern of pure layouts + thin callbacks, sourcing data from `data_io` and calculations from `metrics`.
