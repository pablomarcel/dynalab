"""simulator.core.signals.dimensions

Dimension utilities for the IR.

For MVP, we mostly operate SISO (dim=1). Still, we define a small API so we can
extend to vectors/MIMO later without rewriting validation/compilers.

Dimension representation:
- int: scalar (1) or vector length (n)
- [rows, cols]: matrix signal

Rules (MVP):
- exact match required for connections
- sum block requires all input dims match output dim
"""

from __future__ import annotations

from typing import List, Tuple, Union

from ..ir.types import Dim


def is_matrix(dim: Dim) -> bool:
    return isinstance(dim, list)


def normalize_dim(dim: Dim) -> tuple[int, ...]:
    """Normalize dim to a tuple for hashing/comparison."""
    if isinstance(dim, int):
        return (dim,)
    return tuple(int(x) for x in dim)


def dims_equal(a: Dim, b: Dim) -> bool:
    return normalize_dim(a) == normalize_dim(b)


def sum_output_dim(input_dims: List[Dim]) -> Dim:
    """Compute sum output dimension given input dims (must all match)."""
    if not input_dims:
        return 1
    d0 = input_dims[0]
    for d in input_dims[1:]:
        if not dims_equal(d0, d):
            raise ValueError(f"Sum block input dims do not match: {input_dims}")
    return d0
