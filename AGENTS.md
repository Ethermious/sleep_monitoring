# Repository agents

This repository is organized into a set of collaborating agents. Keep their roles and boundaries intact when modifying code. When adding new capabilities, consider whether they belong to an existing agent or warrant a new crew member.

## Agents manager (architect across the repo)
- Responsibilities: monitor the health of the crew, grow or reduce agents as responsibilities shift, and update this document to match reality.
- Guidance: consolidate overlapping responsibilities instead of duplicating logic, and ensure naming and contracts stay aligned with `README.md` and `ARCHITECTURE.md`.

## Ingestion agent (`sleep_monitoring.logger_service`, `sleepu/ble`)
- Responsibilities: communicate with acquisition hardware, stream Wellue SleepU readings, persist raw samples, and enforce retry/backoff behavior.
- Inputs: BLE packets from the SleepU, configuration from `sleep_monitoring.config`.
- Outputs: normalized samples inserted into SQLite and CSV backups; alerts via logging when acquisition degrades.

## Storage agent (`sleep_monitoring.db`, `sleep_monitoring.data_io`)
- Responsibilities: maintain SQLite schemas, compute `sleep_date`, and provide ergonomic data accessors and exports.
- Contract: do not change column names, timestamp handling, or `compute_sleep_date` semantics without updating all callers and migration scripts.
- Guidance: prefer centralized helpers for paths and file formats to keep notebooks/scripts interoperable.

## Metrics agent (`sleep_monitoring.metrics`)
- Responsibilities: desaturation detection, ODI/time-below-threshold, session summaries, and any future derived metrics.
- Contract: preserve function names and signatures; document any new metrics and keep unit boundaries explicit (seconds vs. minutes).
- Guidance: avoid duplicating calculations already provided by storage; metrics should accept clean inputs and return deterministic outputs.

## Dashboard agent (`sleep_monitoring.dash_app`)
- Responsibilities: present live, review, and per-event dashboards. Keep UI pure; computation belongs in data_io/metrics.
- Guidance: reuse shared theming from the dashboard theme module; prefer small, testable helpers for formatting and gap handling. Keep callbacks lean and push side effects into storage/metrics helpers.

## Operations agent (`scripts/` and `systemd/`)
- Responsibilities: migrations, operational utilities, deployment, packaging, and systemd unit files.
- Guidance: keep scripts runnable on Raspberry Pi, avoid heavy dependencies, and document any required environment variables or cron/systemd hooks.

### Coding conventions
- Prefer type hints on public functions.
- Use `logging` over `print` for diagnostics.
- Keep documentation (`README.md`, `ARCHITECTURE.md`, `AGENTS.md`) in sync with structural changes.
- Maintain dark, high-contrast UI consistency for dashboard work.
