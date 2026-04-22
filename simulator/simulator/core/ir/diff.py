"""simulator.core.ir.diff

Optional IR diff utilities.

This is useful for:
- unit tests (verify UI export changes what you expect)
- future IR-level undo/redo (separate from NodeGraphQt undo stack)

For MVP, we keep it very lightweight: a stable JSON dict + a shallow diff report.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from .types import ProjectIR


def ir_to_stable_json(ir: ProjectIR) -> str:
    """Serialize IR to a deterministic JSON string."""
    return json.dumps(asdict(ir), sort_keys=True, indent=2)


def dict_diff(a: Dict[str, Any], b: Dict[str, Any], *, path: str = "") -> List[str]:
    """Return list of human-readable differences between dicts."""
    diffs: List[str] = []

    a_keys = set(a.keys())
    b_keys = set(b.keys())

    for k in sorted(a_keys - b_keys):
        diffs.append(f"{path}/{k}: removed")
    for k in sorted(b_keys - a_keys):
        diffs.append(f"{path}/{k}: added")

    for k in sorted(a_keys & b_keys):
        pa = f"{path}/{k}"
        va = a[k]
        vb = b[k]

        if isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(dict_diff(va, vb, path=pa))
        elif isinstance(va, list) and isinstance(vb, list):
            if va != vb:
                diffs.append(f"{pa}: list changed (len {len(va)} -> {len(vb)})")
        else:
            if va != vb:
                diffs.append(f"{pa}: {va!r} -> {vb!r}")

    return diffs


def ir_diff(a: ProjectIR, b: ProjectIR) -> List[str]:
    """Diff two IR objects."""
    da = json.loads(ir_to_stable_json(a))
    db = json.loads(ir_to_stable_json(b))
    return dict_diff(da, db, path="")
