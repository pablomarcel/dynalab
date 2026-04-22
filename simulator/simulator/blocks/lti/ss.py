"""simulator.blocks.lti.ss

Optional state-space block spec.

This is not required for MVP, but useful for:
- importing identified/linearized models
- building MIMO systems cleanly

Params:
- A: list[list[float]]
- B: list[list[float]]
- C: list[list[float]]
- D: list[list[float]]

For now, we assume SISO unless dims say otherwise.
"""

from __future__ import annotations

from typing import Any, Dict, List

import control  # python-control

from simulator.simulator.core.ir.types import Block, Port
from simulator.simulator.blocks.spec import PaletteInfo


def _is_matrix(x: Any) -> bool:
    return isinstance(x, list) and (len(x) == 0 or isinstance(x[0], list))


def _to_matrix(x: Any, key: str) -> list[list[float]]:
    if not _is_matrix(x):
        raise ValueError(f"Param '{key}' must be a 2D list.")
    return [[float(v) for v in row] for row in x]


class StateSpaceSpec:
    type = "ss"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="State Space", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="SS",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={
                "A": [[-1.0]],
                "B": [[1.0]],
                "C": [[1.0]],
                "D": [[0.0]],
            },
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []
        for k in ("A", "B", "C", "D"):
            if k not in params:
                errs.append(f"Missing required param: {k}")
            else:
                try:
                    _to_matrix(params[k], k)
                except Exception as e:
                    errs.append(str(e))
        return errs

    def to_control(self, block: Block) -> Any:
        errs = self.validate_params(block.params)
        if errs:
            raise ValueError(f"Invalid params for ss block '{block.id}': {errs}")

        A = _to_matrix(block.params["A"], "A")
        B = _to_matrix(block.params["B"], "B")
        C = _to_matrix(block.params["C"], "C")
        D = _to_matrix(block.params["D"], "D")

        dt = None
        if block.domain == "discrete":
            if block.Ts is None or block.Ts <= 0:
                raise ValueError(f"Discrete ss block '{block.id}' missing Ts.")
            dt = float(block.Ts)

        return control.ss(A, B, C, D, dt=dt)
