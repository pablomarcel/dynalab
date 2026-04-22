"""simulator.core.ir.types

Dataclasses defining the Simulator project's Intermediate Representation (IR).

Design goals:
- Human-readable JSON serialization.
- UI-independent semantics (ports, signs, domain, Ts, params).
- Minimal but extensible: we can add fields without breaking old projects
  via schema versioning + migrations.

Notes:
- Port IDs are globally unique strings within a ProjectIR (recommended format: "<block_id>.<port_name>").
- Wire endpoints reference port IDs, not block IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional


Domain = Literal["continuous", "discrete", "hybrid"]  # hybrid reserved for future
PortDir = Literal["in", "out"]

# Keep dims flexible: support SISO now (dim=1) but allow MIMO later.
# dim can be int (scalar/vector length) or [rows, cols] for matrix signals.
Dim = int | list[int]


@dataclass
class ProjectMeta:
    """Project-level metadata."""

    name: str = "Untitled"
    version: int = 1
    domain: Domain = "continuous"
    Ts: Optional[float] = None  # seconds; required for discrete domain


@dataclass
class Port:
    """A typed port on a block."""

    id: str
    name: str
    direction: PortDir
    dim: Dim = 1

    # Summing junction support: sign applies to *input* ports only.
    # For non-sum blocks, keep as None.
    sign: Optional[int] = None  # +1 or -1

    # Optional semantic tags (future): units, bus, datatype, etc.
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Block:
    """A block (node) in the diagram."""

    id: str
    type: str  # e.g., "tf", "sum", "gain", "step", "scope"
    name: str = ""

    # Optional per-block domain/Ts override (e.g., discrete controller in continuous plant)
    domain: Optional[Domain] = None
    Ts: Optional[float] = None

    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)

    # Block parameters (num/den, gain value, etc.). Must be JSON-serializable.
    params: Dict[str, Any] = field(default_factory=dict)

    # UI-only data should *not* be placed here.
    # Keep it in the project file under a separate `ui_session` blob if needed.


@dataclass
class Wire:
    """Connection from an output port to an input port."""

    id: str
    src: str  # src port id
    dst: str  # dst port id

    # Optional tags (e.g., label, bus name)
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectIR:
    """Semantic model of a Simulator project."""

    meta: ProjectMeta = field(default_factory=ProjectMeta)
    blocks: List[Block] = field(default_factory=list)
    wires: List[Wire] = field(default_factory=list)

    # External IO selection for analysis: which signals are considered inputs/outputs
    # These reference *port IDs*.
    io_inputs: List[str] = field(default_factory=list)
    io_outputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ProjectIR":
        """Parse ProjectIR from a dict (no validation here)."""
        meta_d = d.get("meta", {})
        meta = ProjectMeta(
            name=meta_d.get("name", "Untitled"),
            version=int(meta_d.get("version", 1)),
            domain=meta_d.get("domain", "continuous"),
            Ts=meta_d.get("Ts"),
        )

        blocks: List[Block] = []
        for b in d.get("blocks", []):
            inputs = [Port(**p) for p in b.get("inputs", [])]
            outputs = [Port(**p) for p in b.get("outputs", [])]
            blocks.append(
                Block(
                    id=b["id"],
                    type=b["type"],
                    name=b.get("name", ""),
                    domain=b.get("domain"),
                    Ts=b.get("Ts"),
                    inputs=inputs,
                    outputs=outputs,
                    params=b.get("params", {}) or {},
                )
            )

        wires: List[Wire] = []
        for w in d.get("wires", []):
            wires.append(
                Wire(
                    id=w["id"],
                    src=w["src"],
                    dst=w["dst"],
                    tags=w.get("tags", {}) or {},
                )
            )

        return ProjectIR(
            meta=meta,
            blocks=blocks,
            wires=wires,
            io_inputs=list(d.get("io_inputs", []) or []),
            io_outputs=list(d.get("io_outputs", []) or []),
        )
