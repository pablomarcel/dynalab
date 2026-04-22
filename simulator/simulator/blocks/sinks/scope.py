"""simulator.blocks.sinks.scope

Scope sink block spec.

In Simulink, a scope is a visualization sink. For MVP analysis we treat a scope as:
- a named output point the user can choose as an output for TF/step/bode, etc.

Params:
- label: optional string

Ports:
- u (in)

Compilation:
- to_control(): returns None (handled by compiler by selecting io_outputs)
"""

from __future__ import annotations

from typing import Any, Dict, List

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class ScopeSpec:
    type = "scope"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="Sinks", display_name="Scope", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="scope",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[],
            params={"label": ""},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        # nothing strict
        return []

    def to_control(self, block: Block) -> Any:
        return None
