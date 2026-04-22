"""simulator.core.ir.validate

Static validation checks for ProjectIR.

This is intentionally not tied to any engine; it checks:
- unique IDs
- ports exist
- wires connect out -> in
- single-driver rule (each input port has at most 1 incoming wire)
- domain/sample-time sanity
- sum block sign constraints
- (MVP) unconnected input ports on non-source blocks

Validation raises IRValidationError with a list of human-friendly errors.

Notes on Ts / domain:
- Project meta may define a default Ts (ir.meta.Ts) for discrete-time graphs.
- Blocks may override domain/Ts per-block (b.domain, b.Ts).
- Any block with domain == 'discrete' must have Ts either on the block or via ir.meta.Ts.

Notes on unconnected inputs:
- In MVP we treat unconnected inputs on non-source blocks as errors because most
  engines cannot infer a default signal (Simulink sometimes treats missing inputs
  as 0.0 for Sum; you can relax this later).
- If this becomes too strict, consider moving "graph-level validation" into
  engine-specific validation (validate only the subgraph used for the run).

Updated:
- Treats visual-only sum variants (eg. 'sum_glyph') as sum-like for sign validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .types import Block, Port, ProjectIR, Wire


@dataclass
class IRValidationError(Exception):
    errors: List[str]

    def __str__(self) -> str:  # pragma: no cover
        return "IRValidationError:\n" + "\n".join(f"- {e}" for e in self.errors)


# Blocks considered "sources" in MVP (no required input ports).
_SOURCE_TYPES = {"step", "impulse", "constant"}

# Blocks considered "sinks" in MVP.
_SINK_TYPES = {"scope", "terminator"}

# Blocks considered "sum-like" (input ports may carry +1/-1 sign).
_SUM_TYPES = {"sum", "sum_glyph"}


def _is_source_block(b: Block) -> bool:
    return b.type in _SOURCE_TYPES


def _is_sink_block(b: Block) -> bool:
    return b.type in _SINK_TYPES


def _effective_block_ts(b: Block, ir: ProjectIR) -> Optional[float]:
    """Return the effective Ts for a block, considering project meta."""
    if getattr(b, "domain", None) != "discrete":
        return None
    ts = getattr(b, "Ts", None)
    if ts is None:
        ts = getattr(ir.meta, "Ts", None)
    return ts


def validate_ir(ir: ProjectIR) -> None:
    errors: List[str] = []

    # -----------------------
    # meta validation
    # -----------------------
    meta_domain = getattr(ir.meta, "domain", None)
    meta_ts = getattr(ir.meta, "Ts", None)

    if meta_domain == "discrete":
        if meta_ts is None or meta_ts <= 0:
            errors.append("Project domain is 'discrete' but meta.Ts is missing or <= 0.")

    # NOTE: don't error if continuous + Ts is set; treat it as allowed.
    # (Some workflows keep a default Ts around even for continuous analysis.)

    # -----------------------
    # id uniqueness + port maps
    # -----------------------
    block_ids: Set[str] = set()
    port_ids: Set[str] = set()
    wire_ids: Set[str] = set()

    block_by_id: Dict[str, Block] = {}
    port_by_id: Dict[str, Port] = {}

    for b in ir.blocks:
        if b.id in block_ids:
            errors.append(f"Duplicate block id: {b.id}")
        block_ids.add(b.id)
        block_by_id[b.id] = b

        # domain override sanity
        b_domain = getattr(b, "domain", None)
        b_ts = getattr(b, "Ts", None)

        if b_domain == "discrete":
            eff = _effective_block_ts(b, ir)
            if eff is None or eff <= 0:
                errors.append(f"Block '{b.id}' is discrete but has no Ts and project Ts is not set.")
        if b_domain == "continuous" and b_ts is not None:
            # Not fatal, but usually unintended; keep as warning-style error? Here we keep it as an error
            # only if it's clearly invalid (<=0).
            if b_ts <= 0:
                errors.append(f"Block '{b.id}' is continuous but Ts is <= 0.")

        # ports
        for p in (b.inputs + b.outputs):
            if p.id in port_ids:
                errors.append(f"Duplicate port id: {p.id}")
            port_ids.add(p.id)
            port_by_id[p.id] = p

            if p.direction not in ("in", "out"):
                errors.append(f"Port '{p.id}' has invalid direction: {p.direction}")

            if p.sign is not None and p.direction != "in":
                errors.append(f"Port '{p.id}' has sign set but is not an input port.")

            if p.sign is not None and p.sign not in (-1, 1):
                errors.append(f"Port '{p.id}' has invalid sign: {p.sign} (must be +1 or -1).")

    # -----------------------
    # wire validation + build adjacency (incoming/outgoing)
    # -----------------------
    incoming_wires: Dict[str, List[Wire]] = {pid: [] for pid in port_ids}
    outgoing_wires: Dict[str, List[Wire]] = {pid: [] for pid in port_ids}

    for w in ir.wires:
        if w.id in wire_ids:
            errors.append(f"Duplicate wire id: {w.id}")
        wire_ids.add(w.id)

        if w.src not in port_by_id:
            errors.append(f"Wire '{w.id}' src port not found: {w.src}")
            continue
        if w.dst not in port_by_id:
            errors.append(f"Wire '{w.id}' dst port not found: {w.dst}")
            continue

        src = port_by_id[w.src]
        dst = port_by_id[w.dst]

        if src.direction != "out":
            errors.append(f"Wire '{w.id}' src port '{w.src}' is not an output port.")
        if dst.direction != "in":
            errors.append(f"Wire '{w.id}' dst port '{w.dst}' is not an input port.")

        # dimension check (simple): exact match required for now
        if src.dim != dst.dim:
            errors.append(f"Wire '{w.id}' dimension mismatch: {w.src} dim={src.dim} -> {w.dst} dim={dst.dim}")

        incoming_wires[w.dst].append(w)
        outgoing_wires[w.src].append(w)

    # -----------------------
    # single-driver rule
    # -----------------------
    for pid, ws in incoming_wires.items():
        p = port_by_id.get(pid)
        if p and p.direction == "in" and len(ws) > 1:
            errors.append(f"Input port '{pid}' has {len(ws)} incoming wires (must be <= 1).")

    # -----------------------
    # io selection sanity
    # -----------------------
    if not ir.io_inputs:
        errors.append("No io_inputs selected (expected at least one source output port).")

    if not ir.io_outputs:
        errors.append("No io_outputs selected (expected at least one output port feeding a sink).")
    for pid in ir.io_inputs:
        if pid not in port_by_id:
            errors.append(f"io_inputs references unknown port id: {pid}")
        else:
            if port_by_id[pid].direction != "out":
                errors.append(f"io_inputs must reference output ports (got input): {pid}")
    for pid in ir.io_outputs:
        if pid not in port_by_id:
            errors.append(f"io_outputs references unknown port id: {pid}")
        else:
            if port_by_id[pid].direction != "out":
                errors.append(f"io_outputs must reference output ports (got input): {pid}")

    # -----------------------
    # sum block sign sanity
    # -----------------------
    for b in ir.blocks:
        if b.type in _SUM_TYPES:
            if not b.inputs:
                errors.append(f"Sum block '{b.id}' has no input ports.")
            for p in b.inputs:
                if p.sign is None:
                    errors.append(f"Sum block '{b.id}' input port '{p.id}' is missing sign (+1/-1).")

            # If params.signs exists, ensure it matches inputs.
            signs = None
            try:
                signs = b.params.get("signs") if hasattr(b, "params") else None  # type: ignore[attr-defined]
            except Exception:
                signs = None
            if isinstance(signs, list) and b.inputs and len(signs) != len(b.inputs):
                errors.append(
                    f"Sum block '{b.id}' params.signs length={len(signs)} does not match number of inputs={len(b.inputs)}."
                )
            if isinstance(signs, list):
                bad = [s for s in signs if s not in (-1, 1)]
                if bad:
                    errors.append(f"Sum block '{b.id}' params.signs contains invalid entries: {bad} (must be +1/-1).")
        else:
            for p in b.inputs:
                if p.sign is not None:
                    errors.append(
                        f"Non-sum block '{b.id}' input port '{p.id}' has sign set (only sum blocks should use sign)."
                    )

    # -----------------------
    # (MVP) unconnected input ports on non-source blocks
    # -----------------------
    # Build a quick map port_id -> owning block id for messaging.
    owner_by_port: Dict[str, str] = {}
    for b in ir.blocks:
        for p in b.inputs + b.outputs:
            owner_by_port[p.id] = b.id

    for b in ir.blocks:
        if _is_source_block(b):
            continue  # sources have no required inputs
        # For sinks, require inputs only if the user wants to run analysis that depends on them.
        # We'll still flag unconnected sink inputs, because io_outputs selection typically depends on scope being wired.
        for p in b.inputs:
            if incoming_wires.get(p.id) is None:
                continue
            if len(incoming_wires[p.id]) == 0:
                errors.append(
                    f"Unconnected input port '{p.id}' on block '{b.id}'. MVP requires all non-source inputs to be wired."
                )

    if errors:
        raise IRValidationError(errors)
