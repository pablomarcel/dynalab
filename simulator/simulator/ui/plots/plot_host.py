"""simulator.ui.plots.plot_host

PlotHost embeds matplotlib in Qt and provides simple plotting helpers used by MainWindow.

Upgrades:
- Bode plot shows magnitude + phase using ui.plots.bode_plot.render_bode().
- Clear() avoids matplotlib warnings that can happen when clearing log-scaled axes.
"""

from __future__ import annotations

from PySide6 import QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy as np

from .bode_plot import render_bode


class PlotHost(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._fig = Figure(figsize=(6, 4), dpi=100)
        self._canvas = FigureCanvas(self._fig)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._ax = self._fig.add_subplot(111)
        self._ax.set_title("Plots")

    def clear(self) -> None:
        # Workaround: matplotlib can warn when clearing figures that contain
        # log-scaled axes (it tries to reset limits to 0..1).
        try:
            for ax in list(self._fig.axes):
                try:
                    if ax.get_xscale() == "log":
                        ax.set_xscale("linear")
                    if ax.get_yscale() == "log":
                        ax.set_yscale("linear")
                    ax.set_xlim(0.0, 1.0)
                    ax.set_ylim(0.0, 1.0)
                except Exception:
                    pass
        except Exception:
            pass

        self._fig.clf()
        self._ax = self._fig.add_subplot(111)
        self._canvas.draw_idle()

    def show_tf(self, tf, *, title: str = "Transfer Function") -> None:
        self.clear()
        self._ax.axis("off")
        self._ax.text(0.01, 0.95, title, transform=self._ax.transAxes, fontsize=12, va="top")
        self._ax.text(0.01, 0.85, str(tf), transform=self._ax.transAxes, family="monospace", va="top")
        self._canvas.draw_idle()

    def show_step(self, t: np.ndarray, y: np.ndarray, *, title: str = "Step Response") -> None:
        self.clear()
        ax = self._ax
        ax.set_title(title)
        ax.set_xlabel("t")
        ax.set_ylabel("y")
        ax.grid(True)
        ax.plot(t, y)
        self._canvas.draw_idle()

    def show_bode(self, omega: np.ndarray, mag: np.ndarray, phase: np.ndarray, *, title: str = "Bode") -> None:
        render_bode(self._fig, omega=omega, mag=mag, phase=phase, title=title)
        self._canvas.draw_idle()

    def show_pz(self, poles: np.ndarray, zeros: np.ndarray, *, title: str = "Poles/Zeros") -> None:
        self.clear()
        ax = self._ax
        ax.set_title(title)
        ax.set_xlabel("Re")
        ax.set_ylabel("Im")
        ax.axhline(0, linewidth=1)
        ax.axvline(0, linewidth=1)
        ax.grid(True)

        if zeros is not None and len(zeros) > 0:
            ax.plot(np.real(zeros), np.imag(zeros), "o", label="zeros")
        if poles is not None and len(poles) > 0:
            ax.plot(np.real(poles), np.imag(poles), "x", label="poles")

        ax.legend()
        self._canvas.draw_idle()
