"""simulator.blocks.lti.tf

Transfer function block spec.

Params:
- num: list[float]
- den: list[float]

Domain/Ts behavior:
- If block/domain is discrete, compiles to a discrete-time TF with dt=Ts.
- If continuous, dt=None.

Ports:
- u (in)
- y (out)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import control  # python-control

from simulator.simulator.core.ir.types import Block, Port
from simulator.simulator.blocks.params import validate_numden
from simulator.simulator.blocks.spec import PaletteInfo


class TransferFunctionSpec:
    type = "tf"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="Transfer Function", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="G(s)",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={"num": [1.0], "den": [1.0, 1.0]},  # 1/(s+1)
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return validate_numden(params)

    def to_control(self, block: Block) -> Any:
        errs = self.validate_params(block.params)
        if errs:
            raise ValueError(f"Invalid params for tf block '{block.id}': {errs}")

        num = [float(x) for x in block.params["num"]]
        den = [float(x) for x in block.params["den"]]

        # Discrete-time support: python-control uses dt for discrete TF.
        dt = None
        dom = block.domain
        Ts = block.Ts
        if dom == "discrete":
            if Ts is None or Ts <= 0:
                raise ValueError(f"Discrete tf block '{block.id}' missing Ts.")
            dt = float(Ts)

        sys = control.tf(num, den, dt=dt)
        return sys
