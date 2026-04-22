"""simulator.ui.graph.graph_host

GraphHost embeds the node-graph editor widget (NodeGraphQt / OdenGraphQt).

Key responsibilities (MVP):
- Host the graph widget in a Qt layout.
- Register custom nodes via node_factory.install_nodes_into_graph().
- Support drag & drop from the Library dock.
- Export semantic ProjectIR via session_adapter.graph_to_ir().
- Load from project:
  - if ui_session exists: deserialize (nodes + connections + layout)
  - else: rebuild from ProjectIR (so demo .simproj files render)

Wiring style
------------
NodeGraphQt supports multiple pipe layouts. For a Simulink-like look we want
ORTHOGONAL ("square") wires.

We apply the pipe style using best-effort calls across forks:
- graph.set_pipe_style(PipeLayoutEnum.ANGLE) when available
- viewer.set_pipe_layout(...) / viewer.set_pipe_style(...) as fallbacks

The preferred default is "angled" (orthogonal). It can be overridden via
SettingsStore key: ui/wire_style = {"curved","straight","angled"}.

Smart routing patch (for flipped ports)
---------------------------------------
NodeGraphQt's built-in orthogonal routing assumes OUT ports are on the right and
IN ports are on the left. When you intentionally flip port sides (eg Gain (Flipped)),
the elbows can look odd.

We install a tiny, safe monkey-patch (smart_pipes.install_smart_pipes) that derives
elbow direction from the *actual port side* (relative to node center), so wires
look sane for both standard nodes and flipped-port nodes.

Important notes / pitfalls addressed here
-----------------------------------------
- NodeGraphQt uses graph.acyclic() (a METHOD). Do NOT overwrite it with a bool.
  Use set_acyclic(False) if available to allow feedback loops.
- Selection signals differ by fork; we connect to the viewer scene where possible.
- Connection APIs differ; connect_ports may return None even on success.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple

from PySide6 import QtCore, QtWidgets

from simulator.simulator.blocks.registry import BlockRegistry
from simulator.simulator.core.ir.types import Block, ProjectIR, Wire
from simulator.simulator.log import get_logger
from simulator.simulator.settings import SettingsStore

from .node_factory import create_block_node, install_nodes_into_graph
from .session_adapter import graph_to_ir

# Optional: smart pipe routing patch (safe no-op if backend doesn't match).
try:  # pragma: no cover
    from .smart_pipes import install_smart_pipes
except Exception:  # pragma: no cover
    install_smart_pipes = None  # type: ignore


MIME_BLOCKTYPE = "application/x-simulator-blocktype"


def _safe_call(obj: Any, name: str, *args, **kwargs):
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


def _import_nodegraph() -> tuple[Any, str]:
    """Return (NodeGraphClass, backend_name).

    Default: prefer NodeGraphQt (the canonical upstream).
    Override via env var:
        SIM_GRAPH_BACKEND=nodegraphqt|odengraphqt
    """
    forced = os.environ.get("SIM_GRAPH_BACKEND", "").strip().lower()

    if forced in ("odengraphqt", "oden"):
        try:
            from OdenGraphQt import NodeGraph  # type: ignore
            return NodeGraph, "OdenGraphQt"
        except Exception:
            pass

    if forced in ("nodegraphqt", "nodegraph", "ngqt"):
        try:
            from NodeGraphQt import NodeGraph  # type: ignore
            return NodeGraph, "NodeGraphQt"
        except Exception:
            pass

    # Default preference: NodeGraphQt first.
    try:
        from NodeGraphQt import NodeGraph  # type: ignore
        return NodeGraph, "NodeGraphQt"
    except Exception:
        from OdenGraphQt import NodeGraph  # type: ignore
        return NodeGraph, "OdenGraphQt"


def _pipe_style_value(style_name: str) -> int:
    """Map 'curved'|'straight'|'angled' -> NodeGraphQt pipe style int (best effort)."""
    s = (style_name or "").strip().lower()
    if s not in ("curved", "straight", "angled"):
        s = "angled"

    # Prefer PipeLayoutEnum if available (values differ by version; ANGLE constant is the key).
    for modname in ("NodeGraphQt.constants", "OdenGraphQt.constants"):
        try:
            m = __import__(modname, fromlist=["PipeLayoutEnum"])
            enum = getattr(m, "PipeLayoutEnum", None)
            if enum is None:
                continue
            if s == "angled" and hasattr(enum, "ANGLE"):
                return int(getattr(enum, "ANGLE"))
            if s == "straight" and hasattr(enum, "STRAIGHT"):
                return int(getattr(enum, "STRAIGHT"))
            if s == "curved" and hasattr(enum, "CURVED"):
                return int(getattr(enum, "CURVED"))
        except Exception:
            continue

    # Fallback mapping (matches common NodeGraphQt set_pipe_style docs).
    return {"curved": 0, "straight": 1, "angled": 2}[s]


class GraphHost(QtWidgets.QWidget):
    """Widget that hosts the node editor."""

    sig_selection_changed = QtCore.Signal(object)  # block_id (str) or None
    sig_ir_changed = QtCore.Signal()

    def __init__(
        self,
        *,
        registry: BlockRegistry,
        settings: SettingsStore | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._log = get_logger(__name__)
        self._registry = registry
        self._settings = settings

        NodeGraph, self._backend = _import_nodegraph()
        self._graph = NodeGraph()
        self._log.info("Graph backend: %s", self._backend)

        # Optional smart routing patch (safe no-op if not available).
        try:
            if install_smart_pipes is not None:
                install_smart_pipes(self._log)
        except Exception:
            # Don't ever break startup due to an optional cosmetic patch.
            self._log.debug("smart_pipes install failed", exc_info=True)

        # IMPORTANT: allow feedback loops (best effort across forks)
        self._configure_graph_for_control_systems()

        # Register our custom node classes into the palette.
        install_nodes_into_graph(self._graph, registry=self._registry)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._gw = getattr(self._graph, "widget", None)
        if self._gw is None:
            raise RuntimeError("NodeGraph instance has no .widget attribute; incompatible NodeGraphQt fork?")
        layout.addWidget(self._gw)

        # id counters for auto ids (step1, tf2, ...)
        self._id_counters: dict[str, int] = {}

        self._connect_graph_signals()
        self._install_drop_targets()
        self._try_light_canvas()

        # Apply orthogonal wire style (and any persisted preference).
        self._apply_wire_style_from_settings()

    # -------------------------
    # Properties
    # -------------------------
    @property
    def backend_name(self) -> str:
        return self._backend

    @property
    def graph(self) -> Any:
        return self._graph

    # -------------------------
    # Public API
    # -------------------------
    def set_wire_style(self, style: str) -> None:
        """Set wire style: 'curved'|'straight'|'angled' (orthogonal)."""
        self._apply_wire_style(style)

    def new_project(self) -> None:
        self._clear_graph()
        self.sig_ir_changed.emit()

    def load_from_project(self, *, ir: ProjectIR, ui_session: dict[str, Any]) -> None:
        self._clear_graph()

        loaded = False
        if ui_session:
            try:
                _safe_call(self._graph, "deserialize_session", ui_session)
                loaded = True
            except Exception as e:
                self._log.warning("deserialize_session failed; rebuilding from IR: %s", e)

        if not loaded:
            self._build_graph_from_ir(ir)
            self._frame_all_nodes()

        # Re-apply style after deserialize/rebuild (some forks reset viewer settings).
        self._apply_wire_style_from_settings()

        self.sig_ir_changed.emit()

    def export_project(self) -> tuple[ProjectIR, dict[str, Any]]:
        ui = self._serialize_session()
        ir = graph_to_ir(self._graph, registry=self._registry)
        return ir, ui

    def update_block_params(self, block_id: str, params: dict[str, Any]) -> None:
        node = self._find_node_by_block_id(block_id)
        if not node:
            return

        try:
            if hasattr(node, "set_params"):
                node.set_params(dict(params))  # type: ignore
                return
        except Exception:
            pass

        _safe_call(node, "set_property", "params", dict(params))

    def create_node(
        self,
        block_type: str,
        *,
        block_id: str | None = None,
        pos: Tuple[float, float] | None = None,
        focus: bool = True,
    ) -> str:
        """Create a node and optionally center the view on it."""
        if block_id is None:
            n = self._id_counters.get(block_type, 0) + 1
            self._id_counters[block_type] = n
            block_id = f"{block_type}{n}"

        try:
            before = len(list(_safe_call(self._graph, "all_nodes") or []))
        except Exception:
            before = -1

        # Pull defaults from the registry whenever possible.
        spec = None
        try:
            maybe = getattr(self._registry, "maybe_get", None)
            spec = maybe(block_type) if callable(maybe) else None
        except Exception:
            spec = None

        if spec is not None:
            b = spec.default_block(block_id=block_id)
        else:
            # Fallback if a UI-only node exists but spec isn't registered.
            b = Block(id=block_id, type=block_type, name=block_id, params={}, inputs=[], outputs=[])

        b.name = b.name or block_id

        node = create_block_node(self._graph, registry=self._registry, block=b)

        x, y = pos if pos is not None else self._suggest_drop_pos()
        x, y = self._nudge_if_stacked(x, y)
        self._set_node_pos(node, x, y)

        try:
            after = len(list(_safe_call(self._graph, "all_nodes") or []))
        except Exception:
            after = -1

        self._log.info(
            "Created node %s (%s). all_nodes=%s -> %s placed=(%.1f, %.1f)",
            block_id,
            block_type,
            before,
            after,
            x,
            y,
        )

        if focus:
            self._focus_node(node)

        self.sig_ir_changed.emit()
        return block_id

    # -------------------------
    # Wire style
    # -------------------------
    def _apply_wire_style_from_settings(self) -> None:
        style = "angled"
        if self._settings is not None:
            try:
                style = self._settings.wire_style_name()
            except Exception:
                style = "angled"
        self._apply_wire_style(style)

    def _apply_wire_style(self, style: str) -> None:
        """Best-effort apply wire style across forks."""
        val = _pipe_style_value(style)

        # Try on graph first.
        for name in ("set_pipe_style", "set_pipe_layout", "set_connection_style"):
            try:
                fn = getattr(self._graph, name, None)
                if callable(fn):
                    fn(val)
                    break
            except Exception:
                continue

        # Try on viewer as well (some forks store this on the viewer).
        viewer = self._viewer()
        if viewer is not None:
            for name in ("set_pipe_style", "set_pipe_layout", "set_connection_style"):
                try:
                    fn = getattr(viewer, name, None)
                    if callable(fn):
                        fn(val)
                        break
                except Exception:
                    continue

        # Nudge redraw (safe no-op if not supported).
        try:
            if viewer is not None:
                _safe_call(viewer, "update")
                _safe_call(viewer, "repaint")
        except Exception:
            pass

        self._log.debug("Applied wire style=%s (val=%s)", style, val)

    # -------------------------
    # Drag & drop
    # -------------------------
    def _install_drop_targets(self) -> None:
        """Install an eventFilter on multiple candidate widgets."""
        targets: list[Any] = [self._gw]
        v = self._viewer()
        if v is not None:
            targets.append(v)
            try:
                targets.append(v.viewport())
            except Exception:
                pass

        for t in targets:
            if t is None:
                continue
            try:
                t.setAcceptDrops(True)
                t.installEventFilter(self)
            except Exception:
                continue

    def eventFilter(self, obj: Any, event: Any) -> bool:  # noqa: N802
        try:
            et = event.type()

            if et in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove):
                md = event.mimeData()
                if md and md.hasFormat(MIME_BLOCKTYPE):
                    event.acceptProposedAction()
                    return True

            if et == QtCore.QEvent.Drop:
                md = event.mimeData()
                if md and md.hasFormat(MIME_BLOCKTYPE):
                    bt = bytes(md.data(MIME_BLOCKTYPE)).decode("utf-8").strip()
                    if bt:
                        x, y = self._drop_scene_pos(event)
                        self._log.info("DROP block_type=%s at (%.1f, %.1f)", bt, x, y)
                        self.create_node(bt, pos=(x, y), focus=True)
                    event.acceptProposedAction()
                    return True

        except Exception:
            self._log.exception("Drag/drop handler failed")
            try:
                event.ignore()
            except Exception:
                pass
            return True

        return super().eventFilter(obj, event)

    def _viewer(self) -> Any | None:
        # NodeGraphQt: graph.viewer() exists.
        v = _safe_call(self._graph, "viewer")
        if v is not None:
            return v
        # Some forks expose via widget.viewer().
        maybe = getattr(self._gw, "viewer", None)
        if callable(maybe):
            try:
                return maybe()
            except Exception:
                return None
        return maybe

    def _drop_scene_pos(self, event: Any) -> tuple[float, float]:
        """Convert drop event to scene coordinates robustly using GLOBAL position."""
        viewer = self._viewer()
        if viewer is None:
            return self._suggest_drop_pos()

        gp = None
        try:
            gp = event.globalPosition().toPoint()
        except Exception:
            try:
                gp = event.globalPos()
            except Exception:
                gp = None

        if gp is None:
            return self._suggest_drop_pos()

        try:
            vp = viewer.viewport()
            vp_pos = vp.mapFromGlobal(gp)
            sp = viewer.mapToScene(vp_pos)
            return float(sp.x()), float(sp.y())
        except Exception:
            return self._suggest_drop_pos()

    # -------------------------
    # Graph signals / plumbing
    # -------------------------
    def _connect_graph_signals(self) -> None:
        for sig_name in (
            "node_created",
            "node_deleted",
            "nodes_deleted",
            "connection_created",
            "connection_deleted",
            "data_changed",
            "property_changed",
        ):
            sig = getattr(self._graph, sig_name, None)
            if sig is not None and hasattr(sig, "connect"):
                try:
                    sig.connect(lambda *args, **kwargs: self.sig_ir_changed.emit())
                except Exception:
                    pass

        # Selection: connect to the viewer scene (works for NodeGraphQt).
        try:
            viewer = self._viewer()
            scene = viewer.scene() if viewer is not None else None
            if scene is not None and hasattr(scene, "selectionChanged"):
                scene.selectionChanged.connect(self._on_scene_selection_changed)
        except Exception:
            pass

    def _on_scene_selection_changed(self) -> None:
        block_id: Optional[str] = None
        try:
            sel = _safe_call(self._graph, "selected_nodes") or []
            if isinstance(sel, dict):
                sel = list(sel.values())
            if sel:
                n0 = sel[0]
                if hasattr(n0, "get_block_id"):
                    block_id = n0.get_block_id()  # type: ignore
                else:
                    block_id = _safe_call(n0, "get_property", "block_id")
        except Exception:
            block_id = None
        self.sig_selection_changed.emit(block_id)

    def _clear_graph(self) -> None:
        for m in ("clear_session", "clear"):
            try:
                _safe_call(self._graph, m)
                return
            except Exception:
                pass

        # Fallback
        try:  # pragma: no cover
            for n in list(_safe_call(self._graph, "all_nodes") or []):
                _safe_call(self._graph, "delete_node", n)
        except Exception:
            pass

    def _serialize_session(self) -> dict[str, Any]:
        try:
            ui = _safe_call(self._graph, "serialize_session")
            return ui or {}
        except Exception:
            return {}

    def _find_node_by_block_id(self, block_id: str) -> Any | None:
        try:
            nodes = list(_safe_call(self._graph, "all_nodes") or [])
        except Exception:
            nodes = []
        for n in nodes:
            try:
                if hasattr(n, "get_block_id") and n.get_block_id() == block_id:  # type: ignore
                    return n
            except Exception:
                pass
            if _safe_call(n, "get_property", "block_id") == block_id:
                return n
        return None

    # -------------------------
    # IR -> Graph rebuild
    # -------------------------
    def _build_graph_from_ir(self, ir: ProjectIR) -> None:
        node_by_id: dict[str, Any] = {}

        for i, b in enumerate(ir.blocks):
            try:
                node = create_block_node(self._graph, registry=self._registry, block=b)
            except Exception as e:
                self._log.warning("Failed to create node for block %s (%s): %s", b.id, b.type, e)
                continue
            node_by_id[b.id] = node
            self._set_node_pos(node, float(i * 260), 0.0)

            # update counters so new nodes don't reuse ids
            prefix = "".join([c for c in b.id if not c.isdigit()])
            suffix = "".join([c for c in b.id if c.isdigit()])
            if prefix and suffix.isdigit():
                self._id_counters[prefix] = max(self._id_counters.get(prefix, 0), int(suffix))

        for w in ir.wires:
            try:
                self._connect_wire(w, node_by_id)
            except Exception:
                self._log.debug("Failed to connect wire %s", getattr(w, "id", ""), exc_info=True)
                continue

    def _connect_wire(self, w: Wire, node_by_id: dict[str, Any]) -> None:
        src_bid, src_p = w.src.split(".", 1)
        dst_bid, dst_p = w.dst.split(".", 1)

        src_node = node_by_id.get(src_bid)
        dst_node = node_by_id.get(dst_bid)
        if not src_node or not dst_node:
            return

        out_port = self._get_port(src_node, direction="out", name=src_p)
        in_port = self._get_port(dst_node, direction="in", name=dst_p)
        if out_port is None or in_port is None:
            return

        # NodeGraphQt.connect_ports often returns None even on success.
        for m in ("connect_ports", "connect_port", "connect"):
            fn = getattr(self._graph, m, None)
            if not callable(fn):
                continue
            try:
                fn(out_port, in_port)
                return
            except Exception:
                continue

    def _get_port(self, node: Any, *, direction: str, name: str) -> Any | None:
        if direction == "in":
            # common: node.input('u')
            p = _safe_call(node, "input", name)
            if p is not None:
                return p
            d = _safe_call(node, "inputs")
            if isinstance(d, dict) and name in d:
                return d[name]
        else:
            p = _safe_call(node, "output", name)
            if p is not None:
                return p
            d = _safe_call(node, "outputs")
            if isinstance(d, dict) and name in d:
                return d[name]
        return None

    # -------------------------
    # View helpers
    # -------------------------
    def _suggest_drop_pos(self) -> tuple[float, float]:
        viewer = self._viewer()
        if viewer is not None:
            try:
                vp = viewer.viewport()
                center = vp.rect().center()
                sp = viewer.mapToScene(center)
                return float(sp.x()), float(sp.y())
            except Exception:
                pass
        n = sum(self._id_counters.values()) + 1
        return float(n * 40), float(n * 25)

    def _nudge_if_stacked(self, x: float, y: float) -> tuple[float, float]:
        """If the newest drop is right on top of an existing node, nudge."""
        try:
            nodes = list(_safe_call(self._graph, "all_nodes") or [])
        except Exception:
            nodes = []
        for n in nodes:
            try:
                p = _safe_call(n, "pos")
                if p is None:
                    continue
                nx, ny = float(p[0]), float(p[1])
                if abs(nx - x) < 5 and abs(ny - y) < 5:
                    return x + 40.0, y + 25.0
            except Exception:
                continue
        return x, y

    def _set_node_pos(self, node: Any, x: float, y: float) -> None:
        # NodeGraphQt nodes: set_pos(x, y)
        try:
            if hasattr(node, "set_pos"):
                node.set_pos(x, y)  # type: ignore
                return
        except Exception:
            pass
        # QGraphicsItem style: setPos(x, y)
        try:
            if hasattr(node, "setPos"):
                node.setPos(x, y)  # type: ignore
                return
        except Exception:
            pass
        # Graph helper fallback
        _safe_call(self._graph, "set_node_pos", node, x, y)

    def _focus_node(self, node: Any) -> None:
        viewer = self._viewer()
        if viewer is None:
            return

        try:
            if hasattr(viewer, "center_on"):
                viewer.center_on(node)  # type: ignore
                return
        except Exception:
            pass

        try:
            viewer.fitInView(viewer.sceneRect(), QtCore.Qt.KeepAspectRatio)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _frame_all_nodes(self) -> None:
        viewer = self._viewer()
        if viewer is None:
            return
        try:
            viewer.fitInView(viewer.sceneRect(), QtCore.Qt.KeepAspectRatio)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _try_light_canvas(self) -> None:
        """Make the canvas readable under light theme (best effort)."""
        viewer = self._viewer()
        if viewer is None:
            return

        for target in (viewer, self._graph):
            for name, rgb in (
                ("set_background_color", (250, 250, 250)),
                ("set_grid_color", (215, 215, 215)),
                ("set_secondary_grid_color", (235, 235, 235)),
            ):
                try:
                    _safe_call(target, name, *rgb)
                except Exception:
                    pass

    # -------------------------
    # Backend configuration
    # -------------------------
    def _configure_graph_for_control_systems(self) -> None:
        """Disable acyclic restrictions so feedback loops are allowed.

        NodeGraphQt expects graph.acyclic() to be callable.
        Never do: graph.acyclic = False  (this breaks connections with TypeError)
        """
        # Different forks expose different names.
        for name, args in (
            ("set_acyclic", (False,)),
            ("set_acyclic", (0,)),
            ("set_acyclic_graph", (False,)),
            ("set_allow_cycles", (True,)),
            ("set_allow_cycle", (True,)),
        ):
            fn = getattr(self._graph, name, None)
            if not callable(fn):
                continue
            try:
                fn(*args)
                self._log.debug("Configured graph cycles via %s%r", name, args)
                return
            except Exception:
                continue

        # Last resort: if acyclic is callable, we leave it alone (safe default).
        try:
            a = getattr(self._graph, "acyclic", None)
            if callable(a):
                self._log.debug("Graph exposes acyclic() method; leaving as-is.")
        except Exception:
            pass
