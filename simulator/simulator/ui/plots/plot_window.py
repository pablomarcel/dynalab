"""simulator.ui.plots.plot_window

Separate plot window so plots don't steal real estate from the node canvas.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from simulator.simulator.log import get_logger

from .plot_host import PlotHost


class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._log = get_logger(__name__)
        self.setWindowTitle("Simulator — Plots")
        self.resize(900, 650)

        self.host = PlotHost()
        self.setCentralWidget(self.host)

        # Keep as a tool window so it feels "secondary"
        self.setWindowFlag(QtCore.Qt.Tool, True)
