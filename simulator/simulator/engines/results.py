"""simulator.engines.results

Result dataclasses returned by engines.

These keep UI rendering decoupled from engine implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np


@dataclass(frozen=True)
class TFResult:
    tf: Any  # python-control TransferFunction (or MIMO)
    input_label: str
    output_label: str


@dataclass(frozen=True)
class PolesZerosResult:
    poles: np.ndarray
    zeros: np.ndarray


@dataclass(frozen=True)
class BodeResult:
    omega: np.ndarray
    mag: np.ndarray
    phase: np.ndarray


@dataclass(frozen=True)
class StepResult:
    t: np.ndarray
    y: np.ndarray


@dataclass(frozen=True)
class MarginsResult:
    gm: float
    pm: float
    sm: float
    wg: float
    wp: float
    ws: float


@dataclass(frozen=True)
class SimResult:
    t: np.ndarray
    y: np.ndarray
    meta: dict[str, Any] | None = None
