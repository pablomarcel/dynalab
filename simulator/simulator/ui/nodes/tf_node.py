"""simulator.ui.nodes.tf_node

Transfer Function node.

Ports:
- in: u
- out: y

Properties (stored under params dict):
- num: list[float]
- den: list[float]
- domain: optional ("continuous"|"discrete"|None)
- Ts: optional float (seconds) if discrete

This node is a UI representation; compilation uses simulator.blocks.lti.tf spec.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import SimBaseNode


class TFNode(SimBaseNode):
    NODE_NAME = "TF"

    def init_ports(self) -> None:
        # NodeGraphQt uses add_input/add_output with a port name
        self.add_input("u")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        # Default TF: 1/(s+1)
        return {
            "num": [1.0],
            "den": [1.0, 1.0],
            "domain": None,  # None -> treat as continuous unless Ts is provided by compiler rules
            "Ts": None,
        }
