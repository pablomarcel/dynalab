"""simulator.ui.graph.node_factory

Node factory.

Responsibilities:
- Map semantic block types (IR) to UI NodeGraphQt node classes.
- Register node classes into a NodeGraph instance.
- Create nodes from IR blocks.

This module should NOT contain graph-to-IR logic (that lives in session_adapter).

Why this exists:
NodeGraphQt fork APIs vary slightly, and the *node type id* used by create_node()
is not always what you'd expect (some forks use NODE_NAME, others use __name__).

So creation is implemented as:
1) Try several plausible type ids (identifier+NODE_NAME, identifier+__name__, etc).
2) If that fails, introspect the graph's registered node types and pick a best match.
3) Log enough debug info to diagnose mismatches quickly.

Updated:
- Supports visual-only block types so they round-trip (save/open/export):
    * gain_flipped
    * tf_flipped
    * sum_glyph
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from simulator.simulator.blocks.registry import BlockRegistry
from simulator.simulator.core.ir.types import Block
from simulator.simulator.log import get_logger

from ..nodes.base_node import SimBaseNode
from ..nodes.delay_node import DelayNode
from ..nodes.gain_node import GainNode
from ..nodes.sink_nodes import ScopeNode, TerminatorNode
from ..nodes.source_nodes import ConstantNode, ImpulseNode, StepNode
from ..nodes.sum_node import SumNode
from ..nodes.tf_node import TFNode

log = get_logger(__name__)


# Optional: flipped gain (visual-only). Keep import safe so existing installs don't break.
try:  # pragma: no cover
    from ..nodes.gain_node_flipped import GainFlippedNode  # type: ignore
except Exception:  # pragma: no cover
    GainFlippedNode = None  # type: ignore

# Optional: flipped TF (visual-only). Keep import safe so existing installs don't break.
try:  # pragma: no cover
    from ..nodes.tf_node_flipped import TFNodeFlipped  # type: ignore
except Exception:  # pragma: no cover
    TFNodeFlipped = None  # type: ignore

# Optional: sum glyph (visual-only). Keep import safe so existing installs don't break.
# We try a couple of class names to stay robust if you rename the node class.
SumGlyphNode = None  # type: ignore
try:  # pragma: no cover
    from ..nodes.sum_node_glyph import SumGlyphNode as _SumGlyphNode  # type: ignore

    SumGlyphNode = _SumGlyphNode  # type: ignore
except Exception:  # pragma: no cover
    try:  # pragma: no cover
        from ..nodes.sum_node_glyph import SumNodeGlyph as _SumNodeGlyph  # type: ignore

        SumGlyphNode = _SumNodeGlyph  # type: ignore
    except Exception:  # pragma: no cover
        SumGlyphNode = None  # type: ignore


# Map block type -> UI node class
_NODE_BY_BLOCKTYPE: Dict[str, Type[SimBaseNode]] = {
    "tf": TFNode,
    "gain": GainNode,
    "sum": SumNode,
    "delay": DelayNode,
    "step": StepNode,
    "impulse": ImpulseNode,
    "constant": ConstantNode,
    "scope": ScopeNode,
    "terminator": TerminatorNode,
}

if GainFlippedNode is not None:
    _NODE_BY_BLOCKTYPE["gain_flipped"] = GainFlippedNode  # type: ignore[assignment]

if TFNodeFlipped is not None:
    _NODE_BY_BLOCKTYPE["tf_flipped"] = TFNodeFlipped  # type: ignore[assignment]

if SumGlyphNode is not None:
    _NODE_BY_BLOCKTYPE["sum_glyph"] = SumGlyphNode  # type: ignore[assignment]


# Friendly defaults (only used if a class forgot to define NODE_NAME)
_NODE_DISPLAY_NAME: Dict[str, str] = {
    "tf": "TF",
    "tf_flipped": "TF (Flipped)",
    "gain": "Gain",
    "gain_flipped": "Gain (Flipped)",
    "sum": "Sum",
    "sum_glyph": "Sum (Glyph)",
    "delay": "z^-1",
    "step": "Step",
    "impulse": "Impulse",
    "constant": "Constant",
    "scope": "Scope",
    "terminator": "Terminator",
}


def _ensure_nodegraph_meta(cls: Type[SimBaseNode], *, block_type: str) -> None:
    """Ensure NodeGraphQt-required metadata exists on node classes."""
    if not getattr(cls, "__identifier__", None):
        # Keep stable identifier across runs (important for create_node(type_id)).
        cls.__identifier__ = "simulator.nodes"  # type: ignore[attr-defined]
    if not getattr(cls, "NODE_NAME", None):
        cls.NODE_NAME = _NODE_DISPLAY_NAME.get(block_type, cls.__name__)  # type: ignore[attr-defined]


def _candidate_type_ids(cls: Type[SimBaseNode]) -> List[str]:
    """Generate a list of plausible node type ids to try with create_node()."""
    ident = getattr(cls, "__identifier__", cls.__module__)
    node_name = getattr(cls, "NODE_NAME", cls.__name__)
    mod = getattr(cls, "__module__", "")
    cname = getattr(cls, "__name__", "")

    cands: List[str] = []

    # Most common NodeGraphQt pattern
    cands.append(f"{ident}.{node_name}")
    # Some forks prefer identifier + class name
    cands.append(f"{ident}.{cname}")
    # Some forks use module path
    if mod:
        cands.append(f"{mod}.{node_name}")
        cands.append(f"{mod}.{cname}")
    # Some forks allow bare names
    cands.append(cname)
    cands.append(str(node_name))

    # De-dupe while preserving order
    out: List[str] = []
    for s in cands:
        if s and s not in out:
            out.append(s)
    return out


def _registered_type_ids(graph: Any) -> List[str]:
    """Best-effort introspection: return list of registered node type ids."""
    # Common public APIs
    for m in ("registered_nodes", "registered_node_types", "node_types", "get_node_types"):
        try:
            v = getattr(graph, m, None)
            if callable(v):
                v = v()
            if isinstance(v, dict):
                return list(v.keys())
            if isinstance(v, (list, tuple, set)):
                return list(v)
        except Exception:
            pass

    # Internal factory (varies by version)
    nf = getattr(graph, "_node_factory", None)
    if nf is not None:
        for attr in ("_nodes", "_node_classes", "nodes", "_node_dict"):
            try:
                d = getattr(nf, attr, None)
                if isinstance(d, dict):
                    return list(d.keys())
            except Exception:
                pass

    return []


def _best_match(needle: str, haystack: List[str]) -> Optional[str]:
    """Pick a best-effort match from registered types."""
    if not haystack:
        return None

    # Exact match
    if needle in haystack:
        return needle

    nlow = needle.lower()
    # Try case-insensitive exact
    for t in haystack:
        if t.lower() == nlow:
            return t

    # Try suffix match (common when identifier differs)
    suffix = "." + nlow.split(".")[-1]
    for t in haystack:
        if t.lower().endswith(suffix):
            return t

    # Try contains match
    for t in haystack:
        if nlow in t.lower():
            return t

    return None


def install_nodes_into_graph(graph: Any, *, registry: BlockRegistry) -> None:
    """Register our custom nodes with the NodeGraph instance."""
    register_fn = getattr(graph, "register_node", None)
    if not callable(register_fn):
        raise RuntimeError("Graph backend has no register_node(); incompatible NodeGraphQt fork?")

    for bt, cls in _NODE_BY_BLOCKTYPE.items():
        _ensure_nodegraph_meta(cls, block_type=bt)
        try:
            register_fn(cls)
        except Exception as e:
            # Do NOT swallow — this tells us immediately when a fork mismatch exists.
            log.exception("register_node failed for %s (%s): %s", cls.__name__, bt, e)
            raise

        # Log what we *intend* to use, plus what the graph actually has.
        intended = _candidate_type_ids(cls)[0]
        types = _registered_type_ids(graph)
        actual = _best_match(intended, types) or intended
        log.info("Registered node: %s", actual)

    # Extra debug: dump a short list of registered types once at startup.
    try:
        types = _registered_type_ids(graph)
        if types:
            preview = ", ".join(types[:12])
            log.debug(
                "Graph registered node types (%d): %s%s",
                len(types),
                preview,
                "" if len(types) <= 12 else ", …",
            )
        else:
            log.debug("Graph registered node types: <unable to introspect>")
    except Exception:
        pass


def create_block_node(graph: Any, *, registry: BlockRegistry, block: Block) -> SimBaseNode:
    """Create a UI node for a given semantic IR block."""
    bt = block.type
    cls = _NODE_BY_BLOCKTYPE.get(bt)
    if cls is None:
        raise KeyError(f"No UI node registered for block type: {bt}")

    _ensure_nodegraph_meta(cls, block_type=bt)

    create_fn = getattr(graph, "create_node", None)
    add_fn = getattr(graph, "add_node", None)

    node: Any = None
    tried: List[str] = []

    # 1) Try plausible type ids (string)
    if callable(create_fn):
        for type_id in _candidate_type_ids(cls):
            tried.append(type_id)
            try:
                node = create_fn(type_id)
                if node is not None:
                    log.debug("create_node succeeded using type_id=%s", type_id)
                    break
            except Exception:
                node = None

    # 2) Try passing the class directly (some forks accept this)
    if node is None and callable(create_fn):
        tried.append(f"<class:{cls.__name__}>")
        try:
            node = create_fn(cls)
        except Exception:
            node = None

    if node is None and callable(add_fn):
        tried.append(f"<add_node:{cls.__name__}>")
        try:
            node = add_fn(cls)
        except Exception:
            node = None

    # 3) If still None, introspect graph registry and retry using best match.
    if node is None and callable(create_fn):
        types = _registered_type_ids(graph)
        if types:
            for type_id in _candidate_type_ids(cls):
                m = _best_match(type_id, types)
                if m and m not in tried:
                    tried.append(m)
                    try:
                        node = create_fn(m)
                        if node is not None:
                            log.debug("create_node succeeded using matched type_id=%s", m)
                            break
                    except Exception:
                        node = None

    if node is None:
        # Provide maximally useful failure context.
        types = _registered_type_ids(graph)
        hint = ""
        if types:
            hint = f"; registered_types_preview={types[:12]}"
        tried_preview = tried if len(tried) <= 12 else tried[:12] + ["…"]
        raise RuntimeError(
            f"Failed to create node via NodeGraph API; type_id tried={tried_preview}{hint}"
        )

    # Configure semantic identity + params
    try:
        if hasattr(node, "set_block_identity"):
            node.set_block_identity(block_id=block.id, block_type=block.type, name=block.name)  # type: ignore
        else:
            try:
                node.set_name(block.name)
            except Exception:
                pass
            try:
                node.set_property("block_id", block.id)
                node.set_property("block_type", block.type)
                node.set_property("name", block.name)
            except Exception:
                pass
    except Exception:
        pass

    # Pass params through
    try:
        if hasattr(node, "set_params"):
            node.set_params(dict(block.params))  # type: ignore
        else:
            node.set_property("params", dict(block.params))
    except Exception:
        pass

    return node  # type: ignore[return-value]
