"""simulator.ui.nodes.sum_widget

Ogata / Simulink-style SUM glyph for NodeGraphQt (tested target: v0.6.44).

Fixes in this revision
----------------------
1) Draw a *true circle* (never an ellipse), even if the node bounding box is not square.
2) Ensure ports are positioned exactly like Simulink:
     - input[0]  at 9 o'clock  (left)   (usually +)
     - input[1]  at 6 o'clock  (bottom) (usually -)
     - output[0] at 3 o'clock  (right)
3) Improve orthogonal wiring into the *bottom* input so the last segment is vertical.
   NodeGraphQt's default orthogonal router tends to treat *all* input ports as
   left-facing, producing a horizontal final segment even when the port is placed
   at the bottom.

   We patch PipeItem drawing in a best-effort, fork-safe, idempotent way:
   - If the destination port has attribute `_simulator_prefer_vertical_entry=True`,
     we override the orthogonal path construction so the final segment into the port
     is vertical.

This patch is intentionally conservative:
- It only affects orthogonal/angled wiring.
- It only affects pipes whose destination port explicitly opts in.
- If NodeGraphQt internals differ, it safely no-ops.

"""

from __future__ import annotations

from typing import Any, List, Optional

from PySide6 import QtCore, QtGui

# Prefer NodeGraphQt, but keep compatibility with forks.
try:  # pragma: no cover
    from NodeGraphQt.qgraphics.node_base import NodeItem  # type: ignore
except Exception:  # pragma: no cover
    from OdenGraphQt.qgraphics.node_base import NodeItem  # type: ignore


# -------------------------
# Pipe routing patch
# -------------------------

def _try_import_pipe() -> tuple[Any, Any] | tuple[None, None]:
    """Best-effort import PipeItem and PipeLayoutEnum for NodeGraphQt/OdenGraphQt."""
    try:  # pragma: no cover
        from NodeGraphQt.qgraphics.pipe import PipeItem  # type: ignore
        from NodeGraphQt.constants import PipeLayoutEnum  # type: ignore

        return PipeItem, PipeLayoutEnum
    except Exception:  # pragma: no cover
        try:
            from OdenGraphQt.qgraphics.pipe import PipeItem  # type: ignore
            from OdenGraphQt.constants import PipeLayoutEnum  # type: ignore

            return PipeItem, PipeLayoutEnum
        except Exception:
            return None, None


def _pipe_layout_angled_value(PipeLayoutEnum: Any) -> int:
    """Return an int that corresponds to ANGLE/ORTHOGONAL layout (best effort)."""
    # Most builds: PipeLayoutEnum.ANGLE is an Enum member.
    try:
        v = getattr(PipeLayoutEnum, "ANGLE")
        return int(getattr(v, "value", v))
    except Exception:
        return 2  # common fallback in NodeGraphQt docs


def install_sum_glyph_pipe_hint_patch() -> bool:
    """Patch orthogonal routing so opted-in destination ports get vertical entry.

    Returns True if patched (or already patched), False if we couldn't patch.
    """
    PipeItem, PipeLayoutEnum = _try_import_pipe()
    if PipeItem is None or PipeLayoutEnum is None:
        return False

    if getattr(PipeItem, "_simulator_sum_glyph_patch_v3", False):
        return True

    angled_val = _pipe_layout_angled_value(PipeLayoutEnum)

    # We try to wrap the most likely internal draw methods used by orthogonal routing.
    candidate_methods = [
        "_draw_path_horizontal",
        "_draw_path_vertical",
        "_draw_path_angled",
        "_draw_path_angle",
        "_draw_path_orthogonal",
    ]

    wrapped_any = False

    def _end_port_for(pipe: Any, start_port: Any) -> Any | None:
        try:
            ip = getattr(pipe, "input_port", None)
            op = getattr(pipe, "output_port", None)
            if ip is None or op is None:
                return None
            return op if start_port is ip else ip
        except Exception:
            return None

    def _viewer_layout(pipe: Any) -> Optional[int]:
        for name in ("viewer_pipe_layout", "pipe_layout", "get_pipe_layout"):
            fn = getattr(pipe, name, None)
            if callable(fn):
                try:
                    v = fn()
                    return int(v)
                except Exception:
                    continue
        return None

    def _force_vertical_entry(path: QtGui.QPainterPath, pos1: QtCore.QPointF, pos2: QtCore.QPointF) -> None:
        """Build a simple orthogonal path whose last segment into pos2 is vertical."""
        # Start at pos1 (path already movedTo by caller in most NodeGraphQt builds).
        # Route: (pos1.x, pos1.y) -> (pos2.x, pos1.y) -> (pos2.x, pos2.y)
        mid = QtCore.QPointF(float(pos2.x()), float(pos1.y()))
        path.lineTo(mid)
        path.lineTo(pos2)

    for meth_name in candidate_methods:
        orig = getattr(PipeItem, meth_name, None)
        if not callable(orig):
            continue

        def _make_wrapper(_orig):
            def _wrapped(self: Any, start_port: Any, pos1: Any, pos2: Any, path: Any) -> None:  # type: ignore[no-untyped-def]
                try:
                    layout = _viewer_layout(self)
                    if layout is not None and layout != angled_val:
                        return _orig(self, start_port, pos1, pos2, path)

                    end_port = _end_port_for(self, start_port)
                    prefer_vert = bool(getattr(end_port, "_simulator_prefer_vertical_entry", False))
                    if not prefer_vert:
                        return _orig(self, start_port, pos1, pos2, path)

                    # Ensure path starts correctly.
                    try:
                        # Some builds already movedTo(pos1) before calling; if not, do it.
                        if path.elementCount() == 0:
                            path.moveTo(pos1)
                    except Exception:
                        pass

                    # Replace with a forced path.
                    try:
                        _force_vertical_entry(path, pos1, pos2)
                        self.setPath(path)
                        return
                    except Exception:
                        # If anything goes wrong, fall back to stock behavior.
                        return _orig(self, start_port, pos1, pos2, path)
                except Exception:
                    return _orig(self, start_port, pos1, pos2, path)

            return _wrapped

        setattr(PipeItem, meth_name, _make_wrapper(orig))
        wrapped_any = True

    if not wrapped_any:
        return False

    PipeItem._simulator_sum_glyph_patch_v3 = True  # type: ignore[attr-defined]
    PipeItem._simulator_sum_glyph_patch_v3_angled_val = angled_val  # type: ignore[attr-defined]
    return True


# -------------------------
# Node item
# -------------------------


class SumGlyphNodeItem(NodeItem):
    """Custom NodeGraphQt QGraphics node item that draws the SUM glyph."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)

        # Hide default title/header text items if they exist.
        for attr in ("_title_item", "_text_item", "_name_item"):
            try:
                it = getattr(self, attr, None)
                if it is not None:
                    it.setVisible(False)
            except Exception:
                pass

        # signs used for drawing (+ near left input, - near bottom input)
        self._glyph_signs: List[int] = [1, -1]

        # Try to keep node square so the circle reads perfectly.
        # Not all forks expose these, so this is best-effort.
        for setter, val in (("set_width", 110), ("set_height", 110)):
            try:
                fn = getattr(self, setter, None)
                if callable(fn):
                    fn(val)
            except Exception:
                pass

        # Install the pipe hint patch once (safe no-op if not supported).
        try:
            install_sum_glyph_pipe_hint_patch()
        except Exception:
            pass

    # ---- public hook (node can call this when params change) ----
    def set_glyph_signs(self, signs: List[int]) -> None:
        try:
            self._glyph_signs = [1 if int(s) >= 0 else -1 for s in (signs or [])]
        except Exception:
            self._glyph_signs = [1, -1]
        try:
            self.update()
        except Exception:
            pass

    # ---- geometry helpers ----
    def _node_wh(self) -> tuple[float, float]:
        w = float(getattr(self, "_width", 110.0) or 110.0)
        h = float(getattr(self, "_height", 110.0) or 110.0)
        try:
            br = self.boundingRect()
            if br.width() > 1 and br.height() > 1:
                w = float(br.width())
                h = float(br.height())
        except Exception:
            pass
        return w, h

    def _circle_rect(self) -> QtCore.QRectF:
        """Return a centered *square* rect so the drawn ellipse is a true circle."""
        w, h = self._node_wh()
        pad = 8.0
        d = max(44.0, min(w, h) - 2.0 * pad)
        x = (w - d) / 2.0
        y = (h - d) / 2.0
        return QtCore.QRectF(x, y, d, d)

    # ---- ports placement ----
    def _align_ports_horizontal(self, v_offset: float) -> None:
        """Place ports at 9/6/3 o'clock."""
        circ = self._circle_rect()
        cx = float(circ.center().x())
        cy = float(circ.center().y())

        inputs = list(getattr(self, "inputs", []) or [])
        outputs = list(getattr(self, "outputs", []) or [])
        if not inputs and not outputs:
            return

        sample = inputs[0] if inputs else outputs[0]
        try:
            port_w = float(sample.boundingRect().width())
            port_h = float(sample.boundingRect().height())
        except Exception:
            port_w = port_h = 12.0
        prx = port_w / 2.0
        pry = port_h / 2.0

        # input[0] @ 9 o'clock
        if len(inputs) >= 1:
            p0 = inputs[0]
            p0.setPos(float(circ.left()) - prx, cy - pry)

        # input[1] @ 6 o'clock
        if len(inputs) >= 2:
            p1 = inputs[1]
            p1.setPos(cx - prx, float(circ.bottom()) - pry)
            # opt-in for vertical entry routing
            try:
                setattr(p1, "_simulator_prefer_vertical_entry", True)
            except Exception:
                pass

        # output[0] @ 3 o'clock
        if len(outputs) >= 1:
            po = outputs[0]
            po.setPos(float(circ.right()) - prx, cy - pry)

        # Hide port name text items (glyph uses + / -).
        for _, text in getattr(self, "_input_items", {}).items():
            try:
                text.setVisible(False)
            except Exception:
                pass
        for _, text in getattr(self, "_output_items", {}).items():
            try:
                text.setVisible(False)
            except Exception:
                pass

        try:
            self.update()
        except Exception:
            pass

    # ---- painting ----
    def paint(self, painter: QtGui.QPainter, option: Any, widget: Any = None) -> None:
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        circ = self._circle_rect()

        # Selection state (best effort).
        try:
            selected = bool(self.isSelected())
        except Exception:
            selected = False

        # Colors: match your dark nodes (and selected outline).
        fill = QtGui.QColor(12, 16, 18)
        border = QtGui.QColor(55, 65, 70)
        if selected:
            border = QtGui.QColor(230, 170, 40)

        painter.setPen(QtGui.QPen(border, 2.0))
        painter.setBrush(QtGui.QBrush(fill))
        painter.drawEllipse(circ)  # ellipse inside square rect => circle

        # Σ
        painter.setPen(QtGui.QPen(QtGui.QColor(225, 230, 235)))
        f = painter.font()
        f.setBold(True)
        f.setPointSize(20)
        painter.setFont(f)
        painter.drawText(circ, QtCore.Qt.AlignCenter, "Σ")

        # + / - near port locations
        signs = self._glyph_signs or [1, -1]
        s0 = int(signs[0]) if len(signs) >= 1 else 1
        s1 = int(signs[1]) if len(signs) >= 2 else -1
        t0 = "+" if s0 >= 0 else "-"
        t1 = "+" if s1 >= 0 else "-"

        f2 = painter.font()
        f2.setBold(True)
        f2.setPointSize(11)
        painter.setFont(f2)

        # Left sign: a bit left of center
        left_rect = QtCore.QRectF(circ.left() + circ.width() * 0.28 - 10, circ.center().y() - 12, 20, 20)
        painter.drawText(left_rect, QtCore.Qt.AlignCenter, t0)

        # Bottom sign: a bit below center
        bot_rect = QtCore.QRectF(circ.center().x() - 10, circ.top() + circ.height() * 0.70, 20, 20)
        painter.drawText(bot_rect, QtCore.Qt.AlignCenter, t1)

        painter.restore()
