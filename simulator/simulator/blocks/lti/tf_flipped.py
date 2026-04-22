"""simulator.blocks.lti.tf_flipped

Transfer Function (Flipped) block spec.

This compiles exactly like the normal TF block, but exists as a distinct
block_type so the UI can render it with flipped ports and it can round-trip
through save/open/export.

Params:
- num: list[float]
- den: list[float]

Compiles to python-control TransferFunction: control.tf(num, den)
"""

from __future__ import annotations

from typing import Any, Dict, List

import control  # python-control

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


def _as_float_list(v: Any) -> List[float]:
    if isinstance(v, (list, tuple)):
        out: List[float] = []
        for x in v:
            try:
                out.append(float(x))
            except Exception:
                pass
        return out
    if isinstance(v, (int, float)):
        return [float(v)]
    return []


class TFFlippedSpec:
    type = "tf_flipped"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="TF (Flipped)", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="G(s)",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"num": [1.0], "den": [1.0]},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []

        num = _as_float_list(params.get("num"))
        den = _as_float_list(params.get("den"))

        if not num:
            errs.append("num must be a non-empty list of numbers")
        if not den:
            errs.append("den must be a non-empty list of numbers")
        if den and abs(den[0]) == 0.0:
            errs.append("den leading coefficient must be non-zero")

        # Disallow all-zero denominator
        if den and all(abs(x) == 0.0 for x in den):
            errs.append("den must not be all zeros")

        return errs

    def to_control(self, block: Block) -> Any:
        errs = self.validate_params(block.params)
        if errs:
            raise ValueError(f"Invalid params for tf_flipped block '{block.id}': {errs}")

        num = _as_float_list(block.params.get("num"))
        den = _as_float_list(block.params.get("den"))
        return control.tf(num, den)
