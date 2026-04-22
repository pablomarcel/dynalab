"""simulator.compilers.bdsim_compiler

Placeholder compiler: ProjectIR -> bdsim simulation model.

We are not wiring bdsim in the MVP yet; this module provides:
- a stable API surface so the rest of the app can call into it later
- clear errors explaining what is missing

When you implement this:
- map IR blocks to bdsim blocks
- build a bdsim BlockDiagram
- return an object that sim_engine can run and produce traces
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from simulator.simulator.core.ir.normalize import normalize_ir
from simulator.simulator.core.ir.types import ProjectIR
from simulator.simulator.core.ir.validate import validate_ir


class BDSimCompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledBDSimModel:
    model: Any
    port_to_signal: Dict[str, str]


def compile_to_bdsim(ir: ProjectIR) -> CompiledBDSimModel:
    """Compile IR to a bdsim model (not implemented yet)."""
    ir = normalize_ir(ir)
    validate_ir(ir)

    raise BDSimCompileError(
        "bdsim compiler is not implemented yet. "
        "MVP uses python-control for LTI analysis first."
    )
