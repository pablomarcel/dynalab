"""simulator.compilers.pathsim_compiler

Placeholder compiler: ProjectIR -> PathSim simulation model.

We are not wiring PathSim in the MVP yet; this module provides:
- a stable API surface so the rest of the app can call into it later
- clear errors explaining what is missing

When you implement this:
- map IR blocks to pathsim building blocks
- build a simulation graph and an execution schedule
- return an object that sim_engine can run and produce traces

PathSim reference docs (for later): https://docs.pathsim.org/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from simulator.simulator.core.ir.normalize import normalize_ir
from simulator.simulator.core.ir.types import ProjectIR
from simulator.simulator.core.ir.validate import validate_ir


class PathSimCompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledPathSimModel:
    model: Any
    port_to_signal: Dict[str, str]


def compile_to_pathsim(ir: ProjectIR) -> CompiledPathSimModel:
    """Compile IR to a PathSim model (not implemented yet)."""
    ir = normalize_ir(ir)
    validate_ir(ir)

    raise PathSimCompileError(
        "PathSim compiler is not implemented yet. "
        "MVP uses python-control for LTI analysis first."
    )
