# Repository agents

This repository is organized into a set of collaborating agents. Keep their roles and boundaries intact when modifying code.

## Ingestion agent (`sleep_monitoring.logger_service`, `sleepu/ble`)
- Responsibilities: communicate with acquisition hardware, stream Wellue SleepU readings, and persist them.
- Inputs: BLE packets from the SleepU, configuration from `sleep_monitoring.config`.
- Outputs: normalized samples inserted into SQLite and CSV backups.

## Storage agent (`sleep_monitoring.db`, `sleep_monitoring.data_io`)
- Responsibilities: maintain SQLite schemas, compute `sleep_date`, and provide ergonomic data accessors.
- Contract: do not change column names, timestamp handling, or `compute_sleep_date` semantics without updating all callers.

## Metrics agent (`sleep_monitoring.metrics`)
- Responsibilities: desaturation detection, ODI/time-below-threshold, and session summaries.
- Contract: preserve function names and signatures; document any new metrics.

## Dashboard agent (`sleep_monitoring.dash_app`)
- Responsibilities: present live, review, and per-event dashboards. Keep UI pure; computation belongs in data_io/metrics.
- Guidance: reuse shared theming from the dashboard theme module; prefer small, testable helpers for formatting and gap handling.

## Operations agent (`scripts/` and `systemd/`)
- Responsibilities: migrations, operational utilities, and systemd unit files.
- Guidance: keep scripts runnable on Raspberry Pi and avoid heavy dependencies.

### Coding conventions
- Prefer type hints on public functions.
- Use `logging` over `print` for diagnostics.
- Keep documentation (`README.md`, `ARCHITECTURE.md`, `AGENTS.md`) in sync with structural changes.
- Maintain dark, high-contrast UI consistency for dashboard work.
