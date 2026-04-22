"""simulator.core.signals

Signal-level utilities that operate on the IR:
- naming: deterministic internal signal IDs/labels
- dimensions: scalar/vector/mimo rules + future bus support
- sample_time: Ts propagation and rate-transition checks

These utilities are used by validation, normalization, and compilers.
"""

from __future__ import annotations
