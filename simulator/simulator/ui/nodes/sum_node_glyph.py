"""simulator.ui.nodes.sum_node_glyph

SUM node rendered as an Ogata/Simulink-style summing junction glyph (circle + Σ).

This is a *visual-only* block type ("sum_glyph") that behaves exactly like the
normal semantic "sum" block:
- params: n_inputs (int), signs (list[int] of +1/-1)
- semantics: output is the signed sum of inputs

Visuals
-------
- input[0] at 9 o'clock
- input[1] at 6 o'clock
- output   at 3 o'clock

Important
---------
We manage ports explicitly (instead of subclassing a rectangular SumNode) to:
- guarantee the output port is always created
- keep port names stable (a,b,c..., y)
- keep the UI node independent of any SumNode internal implementation

"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_node import SimBaseNode
from .sum_widget import SumGlyphNodeItem


def _sanitize_int(v: Any, *, default: int, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except Exception:
        n = default
    return max(lo, min(hi, n))


def _sanitize_signs(v: Any, n: int) -> List[int]:
    out: List[int] = []
    if isinstance(v, (list, tuple)):
        for x in v:
            try:
                sx = int(x)
            except Exception:
                sx = 1
            out.append(1 if sx >= 0 else -1)
    # defaults: +, -, -, ...
    while len(out) < n:
        out.append(-1 if len(out) >= 1 else 1)
    return out[:n]


class SumGlyphNode(SimBaseNode):
    """UI node for the SUM glyph."""

    NODE_NAME = "Sum (Glyph)"

    def __init__(self) -> None:
        # Your SimBaseNode supports qgraphics_item injection.
        try:
            super().__init__(qgraphics_item=SumGlyphNodeItem)  # type: ignore[call-arg]
        except TypeError:
            super().__init__()  # type: ignore[misc]
            try:
                self.set_view(SumGlyphNodeItem)  # type: ignore[attr-defined]
            except Exception:
                pass

        # Ensure default params exist.
        self._init_default_params()

        # Make the node square so the circle reads as a true circle.
        for fn_name, val in (("set_width", 110), ("set_height", 110), ("set_size", (110, 110))):
            fn = getattr(self, fn_name, None)
            if not callable(fn):
                continue
            try:
                if isinstance(val, tuple):
                    fn(*val)
                else:
                    fn(val)
            except Exception:
                continue

        # Push initial signs to the view.
        try:
            self._update_glyph_signs(self.get_params().get("signs", [1, -1]))
        except Exception:
            pass

    def init_ports(self) -> None:
        # Minimal 2-input sum by default.
        self.add_input("a")
        self.add_input("b")
        self.add_output("y")

    def default_params(self) -> Dict[str, Any]:
        return {"n_inputs": 2, "signs": [1, -1]}

    def set_params(self, params: Dict[str, Any]) -> None:  # type: ignore[override]
        p = dict(params) if isinstance(params, dict) else {}

        n = _sanitize_int(p.get("n_inputs", 2), default=2, lo=2, hi=8)
        signs = _sanitize_signs(p.get("signs", [1, -1]), n)

        p["n_inputs"] = n
        p["signs"] = signs

        # Sync port count to match n_inputs.
        self._sync_input_ports(n)
        self._ensure_output()

        super().set_params(p)

        self._update_glyph_signs(signs)

    # -------------------------
    # Port management
    # -------------------------
    def _sync_input_ports(self, n: int) -> None:
        desired = [chr(ord("a") + i) for i in range(n)]

        existing: List[str] = []
        try:
            ins = self.inputs()  # type: ignore[call-arg]
            if isinstance(ins, dict):
                existing = list(ins.keys())
        except Exception:
            ins = getattr(self, "_inputs", None)
            if isinstance(ins, dict):
                existing = list(ins.keys())

        # Add missing
        for nm in desired:
            if nm in existing:
                continue
            try:
                self.add_input(nm)
            except Exception:
                pass

        # Remove extras (best effort)
        for nm in list(existing):
            if nm in desired:
                continue
            for fn_name in ("delete_input", "remove_input", "del_input"):
                fn = getattr(self, fn_name, None)
                if callable(fn):
                    try:
                        fn(nm)
                        break
                    except Exception:
                        continue

    def _ensure_output(self) -> None:
        try:
            outs = self.outputs()  # type: ignore[call-arg]
            if isinstance(outs, dict) and "y" in outs:
                return
        except Exception:
            outs = getattr(self, "_outputs", None)
            if isinstance(outs, dict) and "y" in outs:
                return
        try:
            self.add_output("y")
        except Exception:
            pass

    # -------------------------
    # View hook
    # -------------------------
    def _update_glyph_signs(self, signs: List[int]) -> None:
        view = getattr(self, "view", None)
        try:
            if callable(view):
                view = view()
        except Exception:
            pass
        try:
            if view is not None and hasattr(view, "set_glyph_signs"):
                view.set_glyph_signs(signs)  # type: ignore[attr-defined]
        except Exception:
            pass
