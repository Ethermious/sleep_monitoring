"""Dash UI for live monitoring and review.

The app is now modular: layouts live in dedicated files, callbacks are grouped by
workflow, and theme tokens come from :mod:`sleep_monitoring.dash_app.theme`.
Entry remains unchanged: ``python -m sleep_monitoring.dash_app.app``.
"""
from __future__ import annotations

from dash import Dash, Input, Output

from sleep_monitoring import config, data_io

from .layouts import build_root_layout, resolve_tab_layout
from .live_callbacks import register_live_callbacks
from .review_callbacks import register_review_callbacks
from .events_callbacks import register_events_callbacks
from .theme import APP_ASSETS_PATH, APP_TITLE


def register_tab_router(app: Dash) -> None:
    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_tab(tab_value: str):
        sleep_dates = data_io.list_sleep_dates(config.DEFAULT_USER_ID)
        return resolve_tab_layout(tab_value, sleep_dates)


def create_app() -> Dash:
    app = Dash(__name__, assets_folder=str(APP_ASSETS_PATH))
    app.title = APP_TITLE
    app.config.suppress_callback_exceptions = True
    app.layout = build_root_layout()

    register_tab_router(app)
    register_live_callbacks(app)
    register_review_callbacks(app)
    register_events_callbacks(app)

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
