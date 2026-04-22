"""simulator.ui.plots.step_plot

Standalone step-response plotting helper.
"""

from __future__ import annotations

import numpy as np


def plot_step(ax, t: np.ndarray, y: np.ndarray) -> None:
    ax.set_xlabel("t")
    ax.set_ylabel("y")
    ax.grid(True)
    ax.plot(t, y)
