"""simulator.ui.nodes.sink_nodes

Sink node classes:
- ScopeNode
- TerminatorNode

These nodes primarily help with IO selection and diagram cleanliness.

Conventions:
- ScopeNode exposes one input port "u" and stores a user-visible label in params["label"].
- TerminatorNode exposes one input port "u" and has no required params.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import SimBaseNode


def _to_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    try:
        s = str(v)
    except Exception:
        return default
    return s


class ScopeNode(SimBaseNode):
    NODE_NAME = "Scope"

    def init_ports(self) -> None:
        self.add_input("u")

    def default_params(self) -> Dict[str, Any]:
        return {"label": ""}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}
        p["label"] = _to_str(p.get("label", ""), default="")
        super().set_params(p)


class TerminatorNode(SimBaseNode):
    NODE_NAME = "Terminator"

    def init_ports(self) -> None:
        self.add_input("u")

    def default_params(self) -> Dict[str, Any]:
        return {}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        # Keep this permissive; terminator doesn't need params, but allow future metadata.
        p = dict(params) if isinstance(params, dict) else {}
        super().set_params(p)
