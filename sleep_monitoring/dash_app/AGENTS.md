# Dashboard agent guide

Scope: all files under `sleep_monitoring/dash_app/`.

- Keep visual constants in `theme.py`; do not hardcode colors in callbacks or layouts.
- Prefer pure layout functions (no I/O) in `*_layout.py` modules and data-fetching inside callbacks.
- Reuse helpers from `utils.py` for formatting, metric cards, and gap handling.
- Maintain clean separation: layouts describe structure, callbacks wire data.
- Preserve entry point simplicity: `python -m sleep_monitoring.dash_app.app` must remain valid.
