"""simulator.ui.nodes.source_nodes

Source node classes:
- StepNode
- ImpulseNode
- ConstantNode

Conventions:
- Sources have a single output port "y".
- Parameters live in params dict and are exported to ProjectIR.

Normalization:
- Step/Impulse: amplitude -> float, t0 -> float (t0 clamped >= 0)
- Constant: value -> float
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import SimBaseNode


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if f != f:  # NaN
            return default
        if f in (float("inf"), float("-inf")):
            return default
        return f
    except Exception:
        return default


def _clamp_min(x: float, lo: float) -> float:
    return lo if x < lo else x


class StepNode(SimBaseNode):
    NODE_NAME = "Step"

    def init_ports(self) -> None:
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"amplitude": 1.0, "t0": 0.0}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        amp = _to_float(p.get("amplitude", 1.0), default=1.0)
        t0 = _to_float(p.get("t0", 0.0), default=0.0)
        p["amplitude"] = amp
        p["t0"] = _clamp_min(t0, 0.0)
        super().set_params(p)


class ImpulseNode(SimBaseNode):
    NODE_NAME = "Impulse"

    def init_ports(self) -> None:
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"amplitude": 1.0, "t0": 0.0}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        amp = _to_float(p.get("amplitude", 1.0), default=1.0)
        t0 = _to_float(p.get("t0", 0.0), default=0.0)
        p["amplitude"] = amp
        p["t0"] = _clamp_min(t0, 0.0)
        super().set_params(p)


class ConstantNode(SimBaseNode):
    NODE_NAME = "Constant"

    def init_ports(self) -> None:
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"value": 1.0}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        p["value"] = _to_float(p.get("value", 1.0), default=1.0)
        super().set_params(p)
