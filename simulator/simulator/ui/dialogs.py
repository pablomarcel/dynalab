"""simulator.ui.dialogs

Dialog helpers (preferences, about, etc.).

MVP: minimal placeholders. We'll add:
- Preferences dialog (theme, default Ts/domain)
- Block parameter editor dialog (optional; inspector already edits inline)
"""

from __future__ import annotations

from PySide6 import QtWidgets


def show_about(parent: QtWidgets.QWidget | None = None) -> None:
    QtWidgets.QMessageBox.information(
        parent,
        "About Simulator",
        "Simulator\n\nA PySide6 + node-graph based control systems app in Python.",
    )
