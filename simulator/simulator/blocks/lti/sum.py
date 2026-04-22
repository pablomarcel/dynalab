"""simulator.blocks.lti.sum

Summing junction block spec.

This block is essential to represent feedback loops robustly.

Ports:
- inputs: a, b (signed +1/-1). MVP uses 2 inputs, but we keep it extensible.
- output: y

Params:
- n_inputs: int (optional; default 2). UI can rebuild ports when this changes.
- signs: list[int] optional; if provided overrides port.sign defaults.

Compilation:
- For python-control, we return a control.summing_junction(...) system,
  but the compiler will wire it using named signals.

Note:
- python-control summing_junction expects signal names at compile time; our compiler
  will pass them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import control

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


def _default_input_ports(block_id: str, n: int) -> list[Port]:
    ports: list[Port] = []
    for i in range(n):
        name = chr(ord("a") + i)
        sign = +1 if i == 0 else -1  # default: a - b - c - ...
        ports.append(Port(id=f"{block_id}.{name}", name=name, direction="in", dim=1, sign=sign))
    return ports


class SumSpec:
    type = "sum"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="Sum", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="Σ",
            inputs=_default_input_ports(block_id, 2),
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"n_inputs": 2},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []
        n = params.get("n_inputs", 2)
        if not isinstance(n, int) or n < 2:
            errs.append("Param 'n_inputs' must be an int >= 2.")
        signs = params.get("signs")
        if signs is not None:
            if not isinstance(signs, list) or len(signs) != int(n):
                errs.append("Param 'signs' must be a list with length n_inputs.")
            else:
                for s in signs:
                    if s not in (-1, 1):
                        errs.append("Param 'signs' entries must be +1 or -1.")
        return errs

    def to_control(self, block: Block) -> Any:
        # The actual summing_junction needs named signals; we return a callable descriptor
        # that the compiler can finalize. Keeping it simple: return the block itself and
        # let the compiler build summing_junction with correct names.
        return block
