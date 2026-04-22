"""simulator.ui.plots.polezero_plot

Standalone pole-zero plotting helper.
"""

from __future__ import annotations

import numpy as np


def plot_pz(ax, poles: np.ndarray, zeros: np.ndarray) -> None:
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
