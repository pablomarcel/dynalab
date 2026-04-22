"""simulator.compilers.control_compiler

Compile ProjectIR -> python-control interconnected I/O system.

Philosophy:
- The IR defines blocks/ports/wires (semantics).
- Compilation assigns *signal names* to connected ports so that python-control's
  `interconnect()` can wire subsystems automatically by matching signal names.
- Summing junctions are compiled using `control.summing_junction()` so that
  sign (+/-) is explicit and loops (including nested loops) work naturally.

MVP scope:
- SISO (dim=1)
- single-rate continuous OR single-rate discrete (project-wide)
- supported blocks: tf, ss, gain, sum, delay, step/impulse/constant (as external inputs),
  scope/terminator (ignored for dynamics, but used for selecting I/O by port).

Important implementation notes:
- NodeGraphQt forks can occasionally export port ids with stray whitespace.
  This compiler defensively normalizes wire endpoints by stripping whitespace.
- The "MVP requires all non-source inputs to be wired" check now uses the
  *normalized* wire endpoints and produces a more helpful error message that
  includes nearby wires for debugging.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import control  # python-control

from simulator.simulator.blocks.registry import BlockRegistry, default_registry
from simulator.simulator.core.ir.normalize import normalize_ir
from simulator.simulator.core.ir.types import Block, ProjectIR, Wire
from simulator.simulator.core.ir.validate import validate_ir
from simulator.simulator.core.signals.naming import build_signal_names


class ControlCompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledControlModel:
    """Result of compiling a ProjectIR into python-control."""

    system: Any  # InterconnectedSystem (LinearICSystem if all linear)
    port_to_signal: Dict[str, str]  # port_id -> compiled signal name
    inputs: List[str]               # overall system input signal names
    outputs: List[str]              # overall system output signal names
    subsystems: Dict[str, Any]      # block_id -> compiled subsystem (when present)


def _norm_pid(pid: str) -> str:
    """Normalize a port id string (defensive)."""
    return pid.strip()


def _norm_wire(w: Wire) -> Wire:
    """Return a copy-like view of the wire with normalized endpoints."""
    # Wire is a dataclass in core.ir.types; create a new Wire to avoid mutating user object.
    return Wire(id=w.id, src=_norm_pid(w.src), dst=_norm_pid(w.dst))


def _effective_domain(ir: ProjectIR, b: Block) -> str:
    return (b.domain or ir.meta.domain)


def _effective_dt(ir: ProjectIR, b: Block) -> float:
    """Return python-control timebase (dt). Continuous -> 0.0; Discrete -> Ts."""
    dom = _effective_domain(ir, b)
    if dom != "discrete":
        return 0.0  # python-control convention for continuous time

    Ts = b.Ts if (b.Ts is not None and b.Ts > 0) else ir.meta.Ts
    if Ts is None or Ts <= 0:
        raise ControlCompileError(
            f"Discrete block '{b.id}' is missing Ts (set project Ts or block Ts)."
        )
    return float(Ts)


def _collect_ports(ir: ProjectIR) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """Return (port_id->block_id, out_port_ids, in_port_ids)."""
    port_to_block: Dict[str, str] = {}
    out_ports: Dict[str, str] = {}
    in_ports: Dict[str, str] = {}

    for b in ir.blocks:
        for p in b.inputs:
            port_to_block[p.id] = b.id
            in_ports[p.id] = b.id
        for p in b.outputs:
            port_to_block[p.id] = b.id
            out_ports[p.id] = b.id

    return port_to_block, out_ports, in_ports


def _build_port_signal_map(ir: ProjectIR) -> Dict[str, str]:
    """Assign signal names to ports, propagating output names through wires.

    Rule:
    - every output port gets a unique base signal name
    - every input port that has an incoming wire adopts the driving output's signal name
    - unconnected input ports remain with their own name
    """
    names = build_signal_names(ir, prefer_port_name=True)
    _, out_ports, in_ports = _collect_ports(ir)

    port_signal: Dict[str, str] = {}

    # base names for outputs
    for out_pid in out_ports.keys():
        port_signal[_norm_pid(out_pid)] = names.signal_for(out_pid)

    # propagate along wires (single-driver for inputs enforced by validate_ir)
    for w0 in ir.wires:
        w = _norm_wire(w0)
        if w.src in port_signal:
            port_signal[w.dst] = port_signal[w.src]

    # standalone names for remaining inputs (better error messages)
    for in_pid in in_ports.keys():
        in_pid_n = _norm_pid(in_pid)
        if in_pid_n not in port_signal:
            port_signal[in_pid_n] = names.signal_for(in_pid)

    return port_signal


def _assert_single_rate(ir: ProjectIR) -> None:
    """MVP: enforce project-wide single domain + single Ts for discrete."""
    dom = ir.meta.domain
    if dom == "discrete" and (ir.meta.Ts is None or ir.meta.Ts <= 0):
        raise ControlCompileError("Project domain is discrete but meta.Ts is missing/invalid.")

    for b in ir.blocks:
        bdom = _effective_domain(ir, b)
        if bdom != dom:
            raise ControlCompileError(
                f"MVP compiler requires single-domain projects. Block '{b.id}' has domain '{bdom}' "
                f"but project domain is '{dom}'."
            )
        if dom == "discrete":
            # block.Ts may override, but MVP: must match project Ts if provided
            if b.Ts is not None and ir.meta.Ts is not None and abs(float(b.Ts) - float(ir.meta.Ts)) > 1e-12:
                raise ControlCompileError(
                    f"MVP compiler requires single-rate discrete projects. Block '{b.id}' Ts={b.Ts} "
                    f"differs from project Ts={ir.meta.Ts}."
                )


def _label_lti_system(sys: Any, *, name: str, inputs: list[str], outputs: list[str], dt: float) -> Any:
    """Ensure the system has correct input/output signal names and timebase."""
    try:
        if isinstance(sys, control.TransferFunction):
            return control.tf(sys, dt=dt, inputs=inputs, outputs=outputs, name=name)
        if isinstance(sys, control.StateSpace):
            return control.ss(sys, dt=dt, inputs=inputs, outputs=outputs, name=name)
    except Exception as e:
        raise ControlCompileError(f"Failed to relabel system '{name}': {e}")

    # Fallback: try setting attributes
    try:  # pragma: no cover
        sys.name = name
        sys.input_labels = inputs
        sys.output_labels = outputs
        sys.dt = dt
        return sys
    except Exception as e:  # pragma: no cover
        raise ControlCompileError(f"Failed to set IO labels for '{name}': {e}")


def _compile_sum_block(b: Block, port_signal: Dict[str, str], *, dt: float) -> Any:
    if not b.outputs:
        raise ControlCompileError(f"Sum block '{b.id}' has no output ports.")
    yname = port_signal[_norm_pid(b.outputs[0].id)]

    in_names: list[str] = []
    for p in b.inputs:
        base = port_signal[_norm_pid(p.id)]
        if p.sign is None:
            raise ControlCompileError(f"Sum block '{b.id}' input '{p.id}' missing sign (+1/-1).")
        if p.sign == -1:
            in_names.append(f"-{base}")
        else:
            in_names.append(base)

    return control.summing_junction(inputs=in_names, output=yname, name=b.id, dt=dt)


def _incoming_map(ir: ProjectIR) -> Dict[str, int]:
    """Build incoming wire counts per *normalized* dst port id."""
    incoming: Dict[str, int] = {}
    for w0 in ir.wires:
        w = _norm_wire(w0)
        incoming[w.dst] = incoming.get(w.dst, 0) + 1
    return incoming


def _debug_wires_for_block(ir: ProjectIR, block_id: str, limit: int = 12) -> list[str]:
    """Return a small list of wire strings that mention a block id (best effort)."""
    out: list[str] = []
    needle = f"{block_id}."
    for w0 in ir.wires:
        w = _norm_wire(w0)
        if needle in w.src or needle in w.dst:
            out.append(f"{w.id}: {w.src} -> {w.dst}")
            if len(out) >= limit:
                break
    return out


def compile_to_control(
    ir: ProjectIR,
    *,
    registry: Optional[BlockRegistry] = None,
    check_unused: bool = False,
    require_all_inputs_wired: bool = True,
) -> CompiledControlModel:
    """Compile a ProjectIR to an interconnected python-control system.

    Parameters
    ----------
    ir:
        The semantic diagram model.
    registry:
        Block registry used to interpret block types. If None, uses default_registry().
    check_unused:
        If True, enable python-control's unused signal checking (can warn/error).
    require_all_inputs_wired:
        MVP behavior: if True, raise when any non-source input port has zero incoming wires.
        If False, the compiler will allow floating inputs (useful for debugging),
        but python-control interconnect may still fail if signals are undriven.
    """
    ir = normalize_ir(ir)
    validate_ir(ir)
    _assert_single_rate(ir)

    reg = registry or default_registry()
    port_signal = _build_port_signal_map(ir)
    incoming = _incoming_map(ir)

    subsystems: Dict[str, Any] = {}
    syslist: list[Any] = []

    project_dt: float = float(ir.meta.Ts) if ir.meta.domain == "discrete" else 0.0

    for b in ir.blocks:
        dom = _effective_domain(ir, b)
        dt = project_dt if dom == "discrete" else 0.0

        # Skip pure sink blocks (no dynamics).
        if b.type in ("scope", "terminator"):
            continue

        # Sources are treated as external inputs; nothing to add to syslist.
        if b.type in ("step", "impulse", "constant"):
            continue

        if not reg.has(b.type):
            raise ControlCompileError(f"Unknown/unsupported block type: {b.type} (block id: {b.id})")

        # Ensure all block inputs are connected (except blocks with zero inputs)
        if require_all_inputs_wired:
            for p in b.inputs:
                pid = _norm_pid(p.id)
                if incoming.get(pid, 0) == 0:
                    nearby = _debug_wires_for_block(ir, b.id)
                    hint = ""
                    if nearby:
                        hint = " Nearby wires:\n  - " + "\n  - ".join(nearby)
                    raise ControlCompileError(
                        f"Unconnected input port '{p.id}' on block '{b.id}'. "
                        "MVP requires all non-source inputs to be wired."
                        + hint
                    )

        if b.type == "sum":
            sys = _compile_sum_block(b, port_signal, dt=dt)
            subsystems[b.id] = sys
            syslist.append(sys)
            continue

        spec = reg.get(b.type)
        sys0 = spec.to_control(b)
        if sys0 is None:
            raise ControlCompileError(f"Block '{b.id}' ({b.type}) did not compile to a control system.")

        in_labels = [port_signal[_norm_pid(p.id)] for p in b.inputs]
        out_labels = [port_signal[_norm_pid(p.id)] for p in b.outputs]

        sys = _label_lti_system(sys0, name=b.id, inputs=in_labels, outputs=out_labels, dt=dt)
        subsystems[b.id] = sys
        syslist.append(sys)

    # Determine overall I/O.
    if not ir.io_inputs:
        raise ControlCompileError("ProjectIR.io_inputs is empty. Select at least one external input port.")
    if not ir.io_outputs:
        raise ControlCompileError("ProjectIR.io_outputs is empty. Select at least one output port to observe.")

    inputs = [port_signal[_norm_pid(pid)] for pid in ir.io_inputs]
    outputs = [port_signal[_norm_pid(pid)] for pid in ir.io_outputs]

    # Interconnect by matching signal names.
    try:
        sys_ic = control.interconnect(
            syslist,
            inputs=inputs,
            outputs=outputs,
            dt=project_dt if ir.meta.domain == "discrete" else 0.0,
            check_unused=check_unused,
        )
    except Exception as e:
        raise ControlCompileError(f"python-control interconnect failed: {e}")

    return CompiledControlModel(
        system=sys_ic,
        port_to_signal=port_signal,
        inputs=inputs,
        outputs=outputs,
        subsystems=subsystems,
    )
