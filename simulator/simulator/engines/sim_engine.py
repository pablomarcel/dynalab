"""simulator.engines.sim_engine

Unified time-domain simulation engine façade.

MVP status:
- not implemented yet (we start with LTI analysis via python-control)
- provides a stable API so UI can call simulate() later without redesign

Future:
- choose a backend: PathSim or bdsim (or both)
- compile IR -> backend model
- execute simulation and return traces for selected scope outputs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from simulator.simulator.core.ir.types import ProjectIR
from .results import SimResult


class SimulationEngineError(RuntimeError):
    pass


def simulate(ir: ProjectIR, *, t_final: float = 10.0, dt: Optional[float] = None) -> SimResult:
    """Run a time-domain simulation.

    Parameters
    ----------
    t_final:
        Final time (seconds).
    dt:
        Time step (for fixed-step sims) or sample time hint.
    """
    raise SimulationEngineError(
        "Simulation engine is not implemented yet. "
        "MVP provides LTI analysis via python-control first."
    )
