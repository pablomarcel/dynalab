"""simulator.blocks.params

Lightweight parameter schema helpers.

We avoid pulling in heavy deps (pydantic) for MVP. Instead, specs can use these
helpers to validate common parameter shapes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def require_keys(params: Dict[str, Any], keys: Sequence[str]) -> List[str]:
    errs: List[str] = []
    for k in keys:
        if k not in params:
            errs.append(f"Missing required param: {k}")
    return errs


def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_number(params: Dict[str, Any], key: str, *, min_value: float | None = None) -> List[str]:
    errs: List[str] = []
    if key not in params:
        return errs
    v = params[key]
    if not is_number(v):
        errs.append(f"Param '{key}' must be a number (got {type(v).__name__}).")
        return errs
    if min_value is not None and float(v) < min_value:
        errs.append(f"Param '{key}' must be >= {min_value} (got {v}).")
    return errs


def validate_numden(params: Dict[str, Any], *, num_key: str = "num", den_key: str = "den") -> List[str]:
    errs: List[str] = []
    for k in (num_key, den_key):
        if k not in params:
            errs.append(f"Missing required param: {k}")
            continue
        v = params[k]
        if not isinstance(v, list) or not v:
            errs.append(f"Param '{k}' must be a non-empty list of numbers.")
            continue
        for i, a in enumerate(v):
            if not is_number(a):
                errs.append(f"Param '{k}[{i}]' must be a number (got {type(a).__name__}).")
    # denominator sanity: leading term non-zero if provided
    if den_key in params and isinstance(params[den_key], list) and params[den_key]:
        if float(params[den_key][0]) == 0.0:
            errs.append(f"Param '{den_key}[0]' must be non-zero.")
    return errs
