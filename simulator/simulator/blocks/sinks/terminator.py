"""simulator.blocks.sinks.terminator

Terminator sink block spec.

Used to explicitly end a signal (avoid dangling wires in the UI).
It has no effect on analysis; it helps users keep diagrams tidy.

Ports:
- u (in)
"""

from __future__ import annotations

from typing import Any, Dict, List

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


class TerminatorSpec:
    type = "terminator"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="Sinks", display_name="Terminator", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        return Block(
            id=block_id,
            type=self.type,
            name="term",
            inputs=[Port(id=f"{block_id}.u", name="u", direction="in", dim=1)],
            outputs=[],
            params={},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return []

    def to_control(self, block: Block) -> Any:
        return None
