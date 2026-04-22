"""simulator.blocks.lti.sum_glyph

SUM (Glyph) block spec.

This is a visual-only variant of the semantic SUM block.

Why a separate type?
--------------------
- We want an Ogata/Simulink-style summing junction glyph (circle with Σ and +/−)
  while keeping a clean round-trip through save/open/export.
- Having a distinct block_type ("sum_glyph") lets the UI pick a different node
  class without collapsing into the rectangular "sum".

Params
------
- n_inputs: int (>=2)
- signs: list[int] length == n_inputs, each is +1 or -1

Ports
-----
- inputs: a, b, c, ... (dim=1)
- output: y (dim=1)
- Each input port carries a sign (+1/-1) in Port.sign, same as the normal SUM.

Control backend
---------------
We compile to a static MIMO gain system with D = [[s1, s2, ...]].
This behaves like y = Σ (si * ui).

Implementation note
-------------------
We implement this spec *standalone* (instead of inheriting SumSpec) to avoid
any mismatch in method naming between older/newer SumSpec implementations.
The engine only needs: palette(), default_block(), validate_params(), to_control().

"""

from __future__ import annotations

from typing import Any, Dict, List

import control  # python-control

from simulator.simulator.blocks.spec import PaletteInfo
from simulator.simulator.core.ir.types import Block, Port


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _as_sign(v: Any) -> int:
    try:
        s = int(v)
        return 1 if s >= 0 else -1
    except Exception:
        return 1


def _port_names(n: int) -> List[str]:
    return [chr(ord("a") + i) for i in range(n)]


class SumGlyphSpec:
    type = "sum_glyph"

    def palette(self) -> PaletteInfo:
        return PaletteInfo(category="LTI", display_name="Sum (Glyph)", icon=None)

    def default_block(self, *, block_id: str) -> Block:
        n = 2
        signs = [1, -1]
        ins: List[Port] = []
        for name, sgn in zip(_port_names(n), signs):
            ins.append(
                Port(
                    id=f"{block_id}.{name}",
                    name=name,
                    direction="in",
                    dim=1,
                    sign=int(sgn),
                )
            )

        outs = [Port(id=f"{block_id}.y", name="y", direction="out", dim=1)]

        return Block(
            id=block_id,
            type=self.type,
            name="Σ",
            inputs=ins,
            outputs=outs,
            params={"n_inputs": n, "signs": list(signs)},
        )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errs: List[str] = []

        n = _as_int(params.get("n_inputs"), 2)
        if n < 2:
            errs.append("n_inputs must be >= 2")
        if n > 8:
            errs.append("n_inputs must be <= 8")

        signs = params.get("signs")
        if not isinstance(signs, list):
            errs.append("signs must be a list of +1/-1")
            return errs

        if len(signs) != n:
            errs.append(f"signs length must match n_inputs (got {len(signs)} vs {n})")

        bad = [s for s in signs if _as_sign(s) not in (-1, 1)]
        if bad:
            errs.append(f"signs contains invalid entries: {bad} (must be +1/-1)")

        return errs

    def to_control(self, block: Block) -> Any:
        errs = self.validate_params(block.params)
        if errs:
            raise ValueError(f"Invalid params for sum_glyph block '{block.id}': {errs}")

        n = _as_int(block.params.get("n_inputs"), 2)
        signs_raw = block.params.get("signs")
        signs = [_as_sign(s) for s in (signs_raw if isinstance(signs_raw, list) else [1, -1])]
        while len(signs) < n:
            signs.append(-1 if len(signs) >= 1 else 1)
        signs = signs[:n]

        # Static gain: y = [s1 s2 ...] * u
        D = [[float(s) for s in signs]]  # 1 x n

        input_names = _port_names(n)
        output_names = ["y"]

        # Prefer named I/O if supported by this python-control version.
        sys = None
        try:
            sys = control.ss([], [], [], D, inputs=input_names, outputs=output_names, name=block.id)
        except Exception:
            try:
                sys = control.ss([], [], [], D)
            except Exception:
                # Last resort: use a transfer function for each input and append.
                tfs = [control.tf([float(s)], [1.0]) for s in signs]
                try:
                    sys = control.append(*tfs)
                except Exception:
                    # Give up with the best representation we have.
                    sys = tfs[0]

        # Best-effort naming/labels
        try:
            if hasattr(sys, "name"):
                sys.name = block.id
        except Exception:
            pass
        for attr, val in (("input_labels", input_names), ("output_labels", output_names)):
            try:
                if hasattr(sys, attr):
                    setattr(sys, attr, list(val))
            except Exception:
                pass

        return sys
