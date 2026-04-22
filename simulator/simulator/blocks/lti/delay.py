"""simulator.blocks.lti.delay

Unit Delay block spec (discrete-time).

This is the simplest "memory" element and is critical for:
- discrete-time models
- breaking algebraic loops (direct feedthrough cycles)

Params:
- Ts: optional override (seconds). If absent, uses project Ts via normalization/validation.
- z_form: "z^-1" (default) or "z" (future; for now only z^-1)

Compilation:
- python-control: tf([1], [1, 0], dt=Ts) represents z^-1 (one-sample delay).
  In python-control, discrete TF variable is z, so z^-1 is TF with numerator 1 and denominator z.
"""

from __future__ import annotations

from typing import Any, Dict, List

import control

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class UnitDelaySpec:
    type = "delay"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="Unit Delay (z⁻¹)", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="z⁻¹",
            domain="discrete",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[Port(id=f"{block_id}.y", name="y", direction="out", dim=1)],
            params={},  # Ts comes from block.Ts or project meta.Ts
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        # no params for now
        return []

    def to_control(self, block: Block) -> Any:
        if block.domain != "discrete":
            raise ValueError(f"UnitDelay block '{block.id}' must be discrete.")
        if block.Ts is None or block.Ts <= 0:
            raise ValueError(f"UnitDelay block '{block.id}' missing Ts (set project Ts or block Ts).")

        dt = float(block.Ts)

        # One-sample delay: z^-1
        # control.tf uses numerator/denominator in descending powers of z.
        return control.tf([1.0], [1.0, 0.0], dt=dt)
