"""simulator.ui.nodes.sum_node

Summing junction node.

Ports:
- in: a, b (MVP default)
- out: y

Properties (params dict):
- n_inputs: int (>=2)
- signs: list[int] length n_inputs with entries +1/-1

MVP behavior:
- default signs = [+1, -1]
- if n_inputs > 2, the node will auto-create additional inputs: c, d, e, ...
- if signs length doesn't match n_inputs, it is normalized at init-time.

Notes:
- UI editors should modify params["n_inputs"] and params["signs"]
  and then call node.set_params(...) which persists into graph->IR export.
- This node only provides the UI representation; compilation uses the IR.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_node import SimBaseNode


def _input_labels(n: int) -> List[str]:
    """Return input port labels for n inputs: a,b,c,d,..."""
    letters = []
    base = ord("a")
    for i in range(max(0, n)):
        letters.append(chr(base + i))
    return letters


class SumNode(SimBaseNode):
    NODE_NAME = "Sum"

    def init_ports(self) -> None:
        # Determine desired port count from defaults (or existing params if set very early by backend).
        # At this stage, base_node has created an empty params dict; default_params are applied next.
        # So we create MVP ports here (a,b) and later _init_default_params will ensure params exist.
        self.add_input("a")
        self.add_input("b")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"n_inputs": 2, "signs": [1, -1]}

    # ----------------------
    # Optional helpers
    # ----------------------
    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        """Override set_params to keep ports and signs consistent."""
        # Normalize and persist
        fixed = self._normalize_sum_params(dict(params))
        super().set_params(fixed)

        # Make sure the node has enough input ports if n_inputs increased.
        try:
            n_inputs = int(fixed.get("n_inputs", 2))
        except Exception:
            n_inputs = 2
        self._ensure_input_ports(n_inputs)

    # ----------------------
    # Internal
    # ----------------------
    def _normalize_sum_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # n_inputs
        n = params.get("n_inputs", 2)
        try:
            n = int(n)
        except Exception:
            n = 2
        n = max(2, n)
        params["n_inputs"] = n

        # signs
        signs = params.get("signs", [1, -1])
        if not isinstance(signs, list):
            signs = [1, -1]

        # coerce to +/-1 and pad/trim to length n
        out: List[int] = []
        for s in signs:
            try:
                si = int(s)
            except Exception:
                si = 1
            out.append(1 if si >= 0 else -1)

        if len(out) < n:
            # pad with +1 by default
            out.extend([1] * (n - len(out)))
        if len(out) > n:
            out = out[:n]

        # enforce at least one +1 to avoid a "all minus" weirdness (optional safety)
        if all(v < 0 for v in out):
            out[0] = 1

        params["signs"] = out
        return params

    def _ensure_input_ports(self, n_inputs: int) -> None:
        """Ensure the node has n_inputs input ports named a,b,c,..."""
        # NodeGraphQt provides inputs() -> dict and add_input(name).
        existing = {}
        try:
            ex = getattr(self, "inputs", None)
            existing = ex() if callable(ex) else ex  # type: ignore[assignment]
        except Exception:
            existing = {}
        if not isinstance(existing, dict):
            existing = {}

        labels = _input_labels(n_inputs)

        # Add missing ports
        for name in labels:
            if name in existing:
                continue
            try:
                self.add_input(name)
            except Exception:
                # if add_input fails, don't crash the app
                break

        # NOTE: we intentionally do NOT delete ports if n_inputs shrinks,
        # because NodeGraphQt deletion APIs vary and deleting ports with
        # existing wires can corrupt graph state. A later UX pass can handle this.

