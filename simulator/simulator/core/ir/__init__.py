"""simulator.core.ir

Intermediate Representation (IR) for block diagrams.

This IR is the semantic model of a project (what the diagram *means*), independent
from any UI session/geometry. The UI layer can be rebuilt/replaced as long as it
can import/export this IR.

Key concepts:
- Blocks own typed input/output ports.
- Wires connect output ports -> input ports.
- Ports can carry semantics such as sign (+/-) for summing junction inputs.
- Metadata defines domain (continuous/discrete) and sample time (Ts) when relevant.
"""

from __future__ import annotations

from .types import Block, Port, Wire, ProjectIR, ProjectMeta

__all__ = [
    "Block",
    "Port",
    "Wire",
    "ProjectIR",
    "ProjectMeta",
]
