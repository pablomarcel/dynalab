"""simulator.ui.nodes.gain_node

Gain node.

Ports:
- in: u
- out: y

Properties (params dict):
- k: float

Behavior:
- Normalizes k to a float.
- If k is missing or invalid, falls back to 1.0.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import SimBaseNode


def _to_float(v: Any, default: float = 1.0) -> float:
    try:
        f = float(v)
        # Disallow NaN/Inf without importing math (string check is enough for typical inputs)
        if f != f:  # NaN
            return default
        if f in (float("inf"), float("-inf")):
            return default
        return f
    except Exception:
        return default


class GainNode(SimBaseNode):
    NODE_NAME = "Gain"

    def init_ports(self) -> None:
        self.add_input("u")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"k": 1.0}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        p["k"] = _to_float(p.get("k", 1.0), default=1.0)
        super().set_params(p)
