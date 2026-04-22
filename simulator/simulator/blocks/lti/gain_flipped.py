"""simulator.blocks.lti.gain_flipped

Gain (Flipped) block spec.

This compiles exactly like the normal Gain block (static gain k), but exists as a
distinct block_type so the UI can render it with flipped ports.

Params:
- k: float

Compiles to python-control as a static gain transfer function k.
"""

from __future__ import annotations

from typing import Any, Dict, List

import control  # python-control

from simulator.simulator.blocks.params import validate_number
from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class GainFlippedSpec:
    type = "gain_flipped"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="Gain (Flipped)", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="K",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"k": 1.0},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: list[str] = []
        errs += validate_number(params, "k")
        return errs

    def to_control(self, block: Block) -> Any:
        errs = self.validate_params(block.params)
        if errs:
            raise ValueError(f"Invalid params for gain_flipped block '{block.id}': {errs}")

        k = float(block.params["k"])
        return control.tf([k], [1.0])
