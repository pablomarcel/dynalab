"""simulator.ui.nodes.gain_node_flipped

Gain node with flipped ports (input on RIGHT, output on LEFT).

This is a UI-only change (wiring direction remains output->input as enforced by NodeGraphQt).
Use this node in the *feedback* path so the signal can visually flow right-to-left.

Ports:
- in: u  (RIGHT)
- out: y (LEFT)

Properties (params dict):
- k: float

Implementation detail:
- Uses FlippedPortNodeItem (gain_widget.py) to swap port alignment.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import SimBaseNode
from .gain_node import _to_float
from .gain_widget import FlippedPortNodeItem


class GainFlippedNode(SimBaseNode):
    NODE_NAME = "Gain (Flipped)"

    def __init__(self) -> None:
        # Requires SimBaseNode to accept qgraphics_item (see patched base_node.py).
        super().__init__(qgraphics_item=FlippedPortNodeItem)

    def init_ports(self) -> None:
        # Port logical names remain the same as the normal Gain block.
        self.add_input("u")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"k": 1.0}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        p["k"] = _to_float(p.get("k", 1.0), default=1.0)
        super().set_params(p)
