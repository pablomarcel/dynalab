"""simulator.ui.plots.bode_plot

Render a Bode plot (magnitude + phase) into a matplotlib Figure.

This module is intentionally UI-only and accepts precomputed data arrays.
It does NOT call python-control plotting helpers (avoids deprecation churn).

Expected inputs
- omega: 1D array (rad/s)
- mag:   1D array (linear magnitude, |G(jw)|)
- phase: 1D array (radians)

Plot conventions
- Magnitude: log-log (omega vs |G(jw)|)
- Phase:     semilogx (omega vs phase [deg])

Implementation note
- We avoid fig.tight_layout() because it can emit warnings with certain backends
  (QtAgg) + shared axes. We use subplots_adjust instead.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
from matplotlib.figure import Figure


def _as_1d(x: Iterable[float]) -> np.ndarray:
    a = np.asarray(list(x), dtype=float)
    return np.squeeze(a)


def render_bode(
    fig: Figure,
    *,
    omega: Iterable[float],
    mag: Iterable[float],
    phase: Iterable[float],
    title: str = "Bode",
) -> Tuple[object, object]:
    """Clear `fig` and render magnitude + phase axes. Returns (ax_mag, ax_phase)."""
    w = _as_1d(omega)
    m = _as_1d(mag)
    ph = _as_1d(phase)

    if w.size == 0:
        fig.clf()
        ax = fig.add_subplot(111)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return ax, ax

    # Ensure sorted by frequency
    idx = np.argsort(w)
    w = w[idx]
    m = m[idx]
    ph = ph[idx]

    ph_deg = np.degrees(ph)

    fig.clf()
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 2], hspace=0.10)

    ax_mag = fig.add_subplot(gs[0, 0])
    ax_phase = fig.add_subplot(gs[1, 0], sharex=ax_mag)

    # Magnitude
    ax_mag.loglog(w, m)
    ax_mag.set_title(f"{title} (magnitude)")
    ax_mag.set_ylabel("|G(jω)|")
    ax_mag.grid(True, which="both")

    # Phase
    ax_phase.semilogx(w, ph_deg)
    ax_phase.set_title(f"{title} (phase)")
    ax_phase.set_ylabel("∠G(jω) [deg]")
    ax_phase.set_xlabel("ω (rad/s)")
    ax_phase.grid(True, which="both")

    # Layout: avoid tight_layout warnings on some backends
    fig.subplots_adjust(left=0.10, right=0.98, top=0.93, bottom=0.10, hspace=0.18)
    return ax_mag, ax_phase
