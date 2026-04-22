"""simulator.blocks.sources.impulse

Impulse source block spec.

For LTI analysis:
- treated as an external input, similar to Step.

For simulation later:
- can be approximated as a short pulse for continuous-time,
  or as a single-sample 1.0 for discrete-time.
"""

from __future__ import annotations

from typing import Any, Dict, List

from simulator.simulator.blocks.params import validate_number
from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class ImpulseSpec:
    type = "impulse"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="Sources", display_name="Impulse", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="impulse",
            inputs=[],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"amplitude": 1.0, "t0": 0.0},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []
        errs += validate_number(params, "amplitude")
        errs += validate_number(params, "t0", min_value=0.0)
        return errs

    def to_control(self, block: Block) -> Any:
        # Sources are handled by the compiler as external inputs.
        return None
