"""simulator.blocks.lti.saturate

Saturation (nonlinear) block spec.

This block is *not* LTI, so it should not compile to python-control.
It is included as a placeholder for the simulation engine path (PathSim/bdsim).

Params:
- umin: float
- umax: float

Ports:
- u (in)
- y (out)

Compilation:
- to_control(): raises (nonlinear)
- to_pathsim()/to_bdsim(): (future) should create a nonlinear block
"""

from __future__ import annotations

from typing import Any, Dict, List

from simulator.simulator.blocks.params import validate_number, require_keys
from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class SaturationSpec:
    type = "saturate"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="Nonlinear", display_name="Saturation", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="sat",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"umin": -1.0, "umax": 1.0},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []
        errs += require_keys(params, ["umin", "umax"])
        errs += validate_number(params, "umin")
        errs += validate_number(params, "umax")
        if "umin" in params and "umax" in params:
            try:
                if float(params["umin"]) >= float(params["umax"]):
                    errs.append("Param 'umin' must be < 'umax'.")
            except Exception:
                pass
        return errs

    def to_control(self, block: Block) -> Any:
        raise NotImplementedError("Saturation is nonlinear and cannot compile to python-control LTI model yet.")
