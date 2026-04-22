"""simulator.blocks.sources.constant

Constant source block spec.

For LTI analysis:
- treated as an external input (DC input).
  (A constant bias is more meaningful in simulation than TF analysis.)

For simulation later:
- outputs a constant value over time.
"""

from __future__ import annotations

from typing import Any, Dict, List

from simulator.simulator.blocks.params import validate_number
from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class ConstantSpec:
    type = "constant"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="Sources", display_name="Constant", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="const",
            inputs=[],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"value": 1.0},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return validate_number(params, "value")

    def to_control(self, block: Block) -> Any:
        # Handled by compiler as external input / bias; for TF, sources are external.
        return None
