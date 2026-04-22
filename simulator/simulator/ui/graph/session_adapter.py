"""simulator.ui.graph.session_adapter

Convert between the UI graph (NodeGraphQt/OdenGraphQt) and the semantic IR.

This adapter MUST be robust across NodeGraphQt forks.

Key robustness features
-----------------------
1) Some NodeGraphQt builds do not expose connections reliably via graph.connections()
   / graph.all_connections(). When that happens, we fall back to a deterministic
   approach: walk each output port and use port.connected_ports().

2) Some forks/nodes occasionally fail to persist "block_type" as a custom property.
   We canonicalize block types and provide safe fallbacks based on node class name
   and NODE_NAME, so UI export remains stable.

IO selection (MVP)
------------------
- io_inputs: first Source output port (step/impulse/constant)
- io_outputs: the signal feeding the first Scope input (upstream output port)

Updated:
- Adds support for new visual-only types:
    * gain_flipped
    * tf_flipped
    * sum_glyph
  so they round-trip through save/open/export correctly.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from simulator.simulator.blocks.registry import BlockRegistry
from simulator.simulator.core.ir.types import Block, ProjectIR, Wire


def _safe_call(obj: Any, name: str, *args, **kwargs):
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


# Canonical semantic types used by the IR/registry.
_CANON_TYPES = {
    "tf",
    "tf_flipped",
    "gain",
    "gain_flipped",
    "sum",
    "sum_glyph",
    "delay",
    "step",
    "impulse",
    "constant",
    "scope",
    "terminator",
}

# Common aliases (NODE_NAME / visible labels / class names) -> canonical IR type.
_TYPE_ALIASES: Dict[str, str] = {
    # --- TF ---
    "TF": "tf",
    "TFNode": "tf",
    "TransferFunction": "tf",
    "TransferFunctionSpec": "tf",
    # Flipped TF (visual-only)
    "TF (Flipped)": "tf_flipped",
    "TFNodeFlipped": "tf_flipped",
    "TFFlippedNode": "tf_flipped",
    "TFFlipped": "tf_flipped",

    # --- Gain ---
    "Gain": "gain",
    "GainNode": "gain",
    # Flipped gain (visual-only)
    "Gain (Flipped)": "gain_flipped",
    "GainFlippedNode": "gain_flipped",
    "GainFlipped": "gain_flipped",

    # --- Sum ---
    "Sum": "sum",
    "SumNode": "sum",
    # Sum glyph (visual-only)
    "Sum (Glyph)": "sum_glyph",
    "SumGlyph": "sum_glyph",
    "SumGlyphNode": "sum_glyph",
    "SumNodeGlyph": "sum_glyph",
    "SumNodeGlyph": "sum_glyph",

    # --- Delay ---
    "z^-1": "delay",
    "Delay": "delay",
    "DelayNode": "delay",
    "UnitDelay": "delay",

    # --- Sources ---
    "Step": "step",
    "StepNode": "step",
    "Impulse": "impulse",
    "ImpulseNode": "impulse",
    "Constant": "constant",
    "ConstantNode": "constant",

    # --- Sinks ---
    "Scope": "scope",
    "ScopeNode": "scope",
    "Terminator": "terminator",
    "TerminatorNode": "terminator",
}


def _canon_block_type(s: Optional[str], node: Any = None) -> Optional[str]:
    """Canonicalize a block type string into the IR's expected type names."""
    if s is not None:
        ss = str(s).strip()
        if ss in _TYPE_ALIASES:
            return _TYPE_ALIASES[ss]
        lo = ss.lower()
        if lo in _CANON_TYPES:
            return lo
        for k, v in _TYPE_ALIASES.items():
            if k.lower() == lo:
                return v

    if node is not None:
        try:
            cn = node.__class__.__name__
            if cn in _TYPE_ALIASES:
                return _TYPE_ALIASES[cn]
            if cn.lower() in _CANON_TYPES:
                return cn.lower()
        except Exception:
            pass

        try:
            nn = getattr(node, "NODE_NAME", None)
            if isinstance(nn, str) and nn.strip():
                nn = nn.strip()
                if nn in _TYPE_ALIASES:
                    return _TYPE_ALIASES[nn]
                if nn.lower() in _CANON_TYPES:
                    return nn.lower()
        except Exception:
            pass

    return None


def _registry_get_spec(registry: Any, block_type: str):
    """Best-effort: return BlockSpec or None from a registry of unknown API."""
    fn = getattr(registry, "maybe_get", None)
    if callable(fn):
        try:
            return fn(block_type)
        except Exception:
            return None

    fn = getattr(registry, "get", None)
    if callable(fn):
        try:
            return fn(block_type)
        except TypeError:
            try:
                return fn(block_type, None)
            except Exception:
                return None
        except Exception:
            return None

    try:
        return registry[block_type]
    except Exception:
        return None


def _iter_nodes(graph: Any) -> List[Any]:
    nodes = _safe_call(graph, "all_nodes")
    if nodes is None:
        nodes = _safe_call(graph, "nodes")
    if nodes is None:
        nodes = []
    if isinstance(nodes, dict):
        return list(nodes.values())
    return list(nodes)


def _node_block_id(node: Any) -> Optional[str]:
    for name in ("get_block_id", "block_id"):
        v = getattr(node, name, None)
        if callable(v):
            try:
                out = v()
                if isinstance(out, str) and out:
                    return out.strip()
            except Exception:
                pass
        elif isinstance(v, str) and v:
            return v.strip()

    out = _safe_call(node, "get_property", "block_id")
    if isinstance(out, str) and out:
        return out.strip()

    nm = _safe_call(node, "name")
    if isinstance(nm, str) and nm:
        return nm.strip()
    return None


def _node_block_type(node: Any) -> Optional[str]:
    for name in ("get_block_type", "block_type"):
        v = getattr(node, name, None)
        if callable(v):
            try:
                out = v()
                bt = _canon_block_type(out, node=node)
                if bt:
                    return bt
            except Exception:
                pass
        elif isinstance(v, str) and v:
            bt = _canon_block_type(v, node=node)
            if bt:
                return bt

    out = _safe_call(node, "get_property", "block_type")
    bt = _canon_block_type(out if isinstance(out, str) else None, node=node)
    if bt:
        return bt

    return _canon_block_type(None, node=node)


def _node_params(node: Any) -> Dict[str, Any]:
    out = None
    if hasattr(node, "get_params"):
        try:
            out = node.get_params()  # type: ignore
        except Exception:
            out = None
    if out is None:
        out = _safe_call(node, "get_property", "params")
    if isinstance(out, dict):
        return dict(out)
    return {}


def _node_display_name(node: Any, default: str) -> str:
    nm = _safe_call(node, "get_property", "name")
    if isinstance(nm, str) and nm:
        return nm.strip()
    return default


def _port_name(port: Any) -> Optional[str]:
    for n in ("name", "get_name"):
        v = getattr(port, n, None)
        if callable(v):
            try:
                out = v()
                if isinstance(out, str) and out:
                    return out.strip()
            except Exception:
                pass
        elif isinstance(v, str) and v:
            return v.strip()

    out = _safe_call(port, "get_property", "name")
    if isinstance(out, str) and out:
        return out.strip()

    out = getattr(port, "_name", None)
    if isinstance(out, str) and out:
        return out.strip()
    return None


def _port_node(port: Any) -> Any | None:
    for n in ("node", "get_node", "parent"):
        v = getattr(port, n, None)
        if callable(v):
            try:
                out = v()
                if out is not None:
                    return out
            except Exception:
                pass
        else:
            if v is not None:
                return v
    return None


def _iter_node_ports(node: Any, direction: str) -> List[Any]:
    if direction == "out":
        d = _safe_call(node, "outputs")
        if isinstance(d, dict):
            return list(d.values())
        d = getattr(node, "_outputs", None)
        if isinstance(d, dict):
            return list(d.values())
    else:
        d = _safe_call(node, "inputs")
        if isinstance(d, dict):
            return list(d.values())
        d = getattr(node, "_inputs", None)
        if isinstance(d, dict):
            return list(d.values())
    return []


def _connected_ports(port: Any) -> List[Any]:
    v = getattr(port, "connected_ports", None)
    if callable(v):
        try:
            out = v()
            if isinstance(out, (list, tuple)):
                return list(out)
        except Exception:
            pass
    if isinstance(v, (list, tuple)):
        return list(v)

    v = getattr(port, "connections", None)
    if callable(v):
        try:
            out = v()
            if isinstance(out, (list, tuple)):
                return list(out)
        except Exception:
            pass

    return []


def _iter_connections_graph_api(graph: Any) -> List[Tuple[Any, Any]]:
    conns = None
    for name in ("all_connections", "connections"):
        conns = _safe_call(graph, name)
        if conns is not None:
            break
    if conns is None:
        return []

    if isinstance(conns, dict):
        out: List[Tuple[Any, Any]] = []
        for op, ips in conns.items():
            if ips is None:
                continue
            if isinstance(ips, (list, tuple)):
                for ip in ips:
                    out.append((op, ip))
            else:
                out.append((op, ips))
        return out

    out_list: List[Tuple[Any, Any]] = []
    for item in list(conns):
        if isinstance(item, (list, tuple)):
            if len(item) == 2:
                out_list.append((item[0], item[1]))
                continue
            if len(item) >= 4:
                out_list.append((item[1], item[3]))
                continue

        op = None
        ip = None
        for a, b in (("output_port", "input_port"), ("out_port", "in_port"), ("output", "input")):
            op = _safe_call(item, a)
            ip = _safe_call(item, b)
            if op is not None and ip is not None:
                break
        if op is not None and ip is not None:
            out_list.append((op, ip))

    return out_list


def _iter_connections_port_walk(graph: Any) -> List[Tuple[Any, Any]]:
    out: List[Tuple[Any, Any]] = []
    seen: set[tuple[int, int]] = set()

    for node in _iter_nodes(graph):
        for op in _iter_node_ports(node, "out"):
            for cp in _connected_ports(op):
                cdir = getattr(cp, "direction", None)
                if callable(cdir):
                    try:
                        cdir = cdir()
                    except Exception:
                        cdir = None
                if isinstance(cdir, str) and cdir.lower().startswith("out"):
                    continue

                key = (id(op), id(cp))
                if key in seen:
                    continue
                seen.add(key)
                out.append((op, cp))
    return out


def _iter_connections(graph: Any) -> Iterable[Tuple[Any, Any]]:
    pairs = _iter_connections_graph_api(graph)
    if pairs:
        return pairs
    return _iter_connections_port_walk(graph)


def graph_to_ir(graph: Any, *, registry: BlockRegistry) -> ProjectIR:
    blocks: List[Block] = []
    wires: List[Wire] = []

    for node in _iter_nodes(graph):
        bid = _node_block_id(node)
        btype = _node_block_type(node)
        if not bid or not btype:
            continue

        params = _node_params(node)
        name = _node_display_name(node, default=bid)

        spec = _registry_get_spec(registry, btype)
        if spec is not None:
            blk = spec.default_block(block_id=bid)
        else:
            blk = Block(id=bid, type=btype, name=name, params={}, inputs=[], outputs=[])

        blk.name = name
        blk.params.update(params)

        # Sum variants store signs in params. Copy to input port metadata for completeness.
        if blk.type in {"sum", "sum_glyph"}:
            signs = blk.params.get("signs")
            if isinstance(signs, list) and signs:
                for i, s in enumerate(signs):
                    if i >= len(blk.inputs):
                        break
                    try:
                        blk.inputs[i].sign = int(s)
                    except Exception:
                        pass

        blocks.append(blk)

    wid = 0
    for out_port, in_port in _iter_connections(graph):
        op_name = _port_name(out_port)
        ip_name = _port_name(in_port)
        if not op_name or not ip_name:
            continue

        on = _port_node(out_port)
        inn = _port_node(in_port)
        if on is None or inn is None:
            continue

        obid = _node_block_id(on)
        ibid = _node_block_id(inn)
        if not obid or not ibid:
            continue

        wid += 1
        wires.append(Wire(id=f"w{wid}", src=f"{obid}.{op_name}", dst=f"{ibid}.{ip_name}"))

    io_in: List[str] = []
    io_out: List[str] = []

    for b in blocks:
        if b.type in {"step", "impulse", "constant"} and b.outputs:
            io_in = [f"{b.id}.{b.outputs[0].name}"]
            break

    scope_in = None
    for b in blocks:
        if b.type == "scope" and b.inputs:
            scope_in = f"{b.id}.{b.inputs[0].name}"
            break

    if scope_in is not None:
        for w in wires:
            if w.dst == scope_in:
                io_out = [w.src]
                break

    if not io_out:
        for b in reversed(blocks):
            if b.outputs:
                io_out = [f"{b.id}.{b.outputs[0].name}"]
                break

    return ProjectIR(blocks=blocks, wires=wires, io_inputs=io_in, io_outputs=io_out)
