"""simulator.ui.nodes.delay_node

Unit Delay node (z^-1).

Ports:
- in: u
- out: y

Properties (params dict):
- domain: should be "discrete" for this node
- Ts: optional float override (seconds)

Behavior:
- Ensures params["domain"] is always "discrete" (even if inspector tries to change it).
- Normalizes Ts:
    - None or missing -> None
    - numeric -> float >= 0
    - non-numeric -> None

Note: actual dt selection is enforced during compilation. This is purely a UI node.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base_node import SimBaseNode


def _to_float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except Exception:
        return None
    if f < 0:
        return 0.0
    return f


class DelayNode(SimBaseNode):
    NODE_NAME = "z^-1"

    def init_ports(self) -> None:
        self.add_input("u")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        # Domain is fixed to discrete for a unit delay.
        return {"domain": "discrete", "Ts": None}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        """Override set_params to enforce discrete domain and normalize Ts."""
        p = dict(params) if isinstance(params, dict) else {}

        # Force discrete domain regardless of UI edits.
        p["domain"] = "discrete"

        # Normalize Ts.
        p["Ts"] = _to_float_or_none(p.get("Ts", None))

        super().set_params(p)
