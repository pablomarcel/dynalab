"""simulator.ui.nodes.tf_node_flipped

Transfer Function node with flipped ports (input on RIGHT, output on LEFT).

This is a UI-only change (wiring direction remains output->input as enforced by NodeGraphQt).
Use this node in feedback paths so the signal can visually flow right-to-left.

Ports:
- in: u  (RIGHT)
- out: y (LEFT)

Properties (params dict):
- num: list[float]
- den: list[float]

Implementation detail:
- Uses FlippedPortNodeItem (tf_widget.py) to swap port alignment.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List

from .base_node import SimBaseNode
from .tf_widget import FlippedPortNodeItem


def _to_float_list(v: Any, *, default: List[float]) -> List[float]:
    """Best-effort parse a list of floats from common inspector inputs."""
    if v is None:
        return list(default)

    # Already list-like
    if isinstance(v, (list, tuple)):
        out: List[float] = []
        for x in v:
            try:
                out.append(float(x))
            except Exception:
                pass
        return out if out else list(default)

    # Single number
    if isinstance(v, (int, float)):
        try:
            return [float(v)]
        except Exception:
            return list(default)

    # String parsing
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return list(default)

        # Try Python literal list/tuple first: "[1, 2]" or "(1,2)"
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
            try:
                vv = ast.literal_eval(s)
                return _to_float_list(vv, default=default)
            except Exception:
                # fallthrough to split parsing
                pass

        # Comma/space separated: "1, 2, 3" or "1 2 3"
        parts = [p for p in s.replace(",", " ").split() if p]
        out: List[float] = []
        for p in parts:
            try:
                out.append(float(p))
            except Exception:
                pass
        return out if out else list(default)

    return list(default)


class TFNodeFlipped(SimBaseNode):
    NODE_NAME = "TF (Flipped)"

    def __init__(self) -> None:
        super().__init__(qgraphics_item=FlippedPortNodeItem)

    def init_ports(self) -> None:
        self.add_input("u")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        # Keep unity as a safe default.
        return {"num": [1.0], "den": [1.0]}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        p["num"] = _to_float_list(p.get("num"), default=[1.0])
        p["den"] = _to_float_list(p.get("den"), default=[1.0])

        # Guard against invalid denominator (all zeros / leading zero).
        try:
            if not p["den"] or all(float(x) == 0.0 for x in p["den"]):
                p["den"] = [1.0]
            # leading coeff must be non-zero for control.tf
            if float(p["den"][0]) == 0.0:
                # trim leading zeros
                den = [float(x) for x in p["den"]]
                while den and den[0] == 0.0:
                    den = den[1:]
                p["den"] = den if den else [1.0]
        except Exception:
            p["den"] = [1.0]

        super().set_params(p)
