"""simulator.app

Qt application bootstrap.

This file is intentionally small:
- initialize logging
- load settings / apply theme
- create QApplication + MainWindow
- open optional project

All heavy lifting lives in simulator.ui.*.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets

from .log import configure_logging, get_logger
from .settings import SettingsStore


def run_app(*, debug: bool = False, reset_settings: bool = False, project_path: Optional[str] = None) -> int:
    """Run the desktop application."""
    configure_logging(debug=debug)
    log = get_logger(__name__)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("Simulator")
    app.setOrganizationName("machines")
    app.setOrganizationDomain("machines.local")

    settings = SettingsStore()
    if reset_settings:
        log.warning("Resetting settings as requested.")
        settings.reset()

    # Apply stylesheet/theme early.
    qss = settings.load_theme_qss()
    if qss:
        app.setStyleSheet(qss)

    # Lazy import: UI depends on NodeGraphQt/OdenGraphQt which might be optional during CLI parsing.
    from simulator.ui.main_window import MainWindow

    win = MainWindow(settings=settings)
    win.show()

    if project_path:
        p = Path(project_path).expanduser().resolve()
        if p.exists():
            log.info("Opening project on launch: %s", str(p))
            win.open_project(str(p))
        else:
            log.error("Project file not found: %s", str(p))

    return app.exec()
