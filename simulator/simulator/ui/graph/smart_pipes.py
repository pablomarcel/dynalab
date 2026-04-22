"""simulator.ui.graph.smart_pipes

Smart pipe routing for NodeGraphQt v0.6.44 to better support *non-standard port sides*.

Why this exists
---------------
NodeGraphQt's default pipe routing assumes the standard convention:
  - OUTPUT ports are on the RIGHT
  - INPUT ports are on the LEFT

With the new Gain (Flipped) node we intentionally place:
  - input on the RIGHT
  - output on the LEFT

NodeGraphQt's `PipeItem._draw_path_horizontal()` uses `start_port.port_type`
(IN vs OUT) to decide whether to offset control points left/right. When ports
are placed on the "unexpected" side, those offsets go the wrong direction,
producing the odd elbows you’re seeing.

This module installs a tiny monkey-patch that determines the offset direction
from the *actual port side* (port center relative to node center), rather than
assuming OUT=right and IN=left.

Safety
------
- Only patches NodeGraphQt if it's importable.
- Only patches once (idempotent).
- Leaves straight pipes unchanged.
- For standard nodes (inputs left, outputs right), the behavior matches the stock
  algorithm, so your existing wiring look stays the same.

Usage
-----
Call once at startup (eg in GraphHost.__init__ after graph created):

    from simulator.simulator.ui.graph.smart_pipes import install_smart_pipes
    install_smart_pipes()

"""

from __future__ import annotations

from typing import Any, Optional


def install_smart_pipes(log: Any | None = None) -> bool:
    """Install the smart routing patch. Returns True if patched."""
    try:
        from NodeGraphQt.qgraphics.pipe import PipeItem  # type: ignore
        from NodeGraphQt.constants import PipeLayoutEnum  # type: ignore
    except Exception:
        return False

    # Already patched?
    if getattr(PipeItem, "_simulator_smart_patch", False):
        return True

    # Try to import Qt bindings used by NodeGraphQt.
    try:
        from Qt import QtCore  # type: ignore
    except Exception:  # pragma: no cover
        from PySide6 import QtCore  # type: ignore

    orig_horizontal = getattr(PipeItem, "_draw_path_horizontal", None)
    orig_vertical = getattr(PipeItem, "_draw_path_vertical", None)
    if not callable(orig_horizontal):
        return False

    def _node_center_x(port: Any) -> Optional[float]:
        try:
            node = port.node
            # sceneBoundingRect is the most reliable for transforms/scale.
            return float(node.sceneBoundingRect().center().x())
        except Exception:
            return None

    def _node_center_y(port: Any) -> Optional[float]:
        try:
            node = port.node
            return float(node.sceneBoundingRect().center().y())
        except Exception:
            return None

    def _side_sign_x(port: Any, port_center_x: float) -> int:
        """-1 for left side, +1 for right side (best-effort)."""
        cx = _node_center_x(port)
        if cx is None:
            # fallback: keep stock convention if we can't compute.
            try:
                # PortTypeEnum.OUT == 2, IN == 1 in NodeGraphQt.
                return 1 if int(getattr(port, "port_type", 0)) != 1 else -1
            except Exception:
                return 1
        return 1 if port_center_x >= cx else -1

    def _side_sign_y(port: Any, port_center_y: float) -> int:
        """-1 for top, +1 for bottom (best-effort)."""
        cy = _node_center_y(port)
        if cy is None:
            try:
                return 1 if int(getattr(port, "port_type", 0)) != 1 else -1
            except Exception:
                return 1
        return 1 if port_center_y >= cy else -1

    def _end_port_for(self: Any, start_port: Any) -> Any | None:
        """Best-effort determine the other port (works for established pipes)."""
        try:
            ip = getattr(self, "input_port", None)
            op = getattr(self, "output_port", None)
            if ip is None or op is None:
                return None
            if start_port is ip:
                return op
            if start_port is op:
                return ip
        except Exception:
            pass
        return None

    def _draw_path_horizontal_smart(self: Any, start_port: Any, pos1: Any, pos2: Any, path: Any) -> None:
        """Patched horizontal routing for CURVED + ANGLE layouts."""
        layout = None
        try:
            layout = self.viewer_pipe_layout()
        except Exception:
            layout = None

        # Keep stock behavior for STRAIGHT or unknown layouts.
        if layout not in (PipeLayoutEnum.CURVED.value, PipeLayoutEnum.ANGLE.value):
            return orig_horizontal(self, start_port, pos1, pos2, path)  # type: ignore[misc]

        end_port = _end_port_for(self, start_port)

        # Determine “outward” direction from actual port side.
        s1 = _side_sign_x(start_port, float(pos1.x()))
        if end_port is not None:
            s2 = _side_sign_x(end_port, float(pos2.x()))
        else:
            # Live pipe fallback: aim outward in the direction of the cursor.
            dx = float(pos2.x()) - float(pos1.x())
            s2 = 1 if dx >= 0 else -1

        if layout == PipeLayoutEnum.CURVED.value:
            ctr_offset_x1, ctr_offset_x2 = float(pos1.x()), float(pos2.x())
            tangent = abs(ctr_offset_x1 - ctr_offset_x2)
            try:
                max_width = float(start_port.node.boundingRect().width())
                tangent = min(tangent, max_width)
            except Exception:
                pass

            ctr_offset_x1 += s1 * tangent
            ctr_offset_x2 += s2 * tangent

            ctr_point1 = QtCore.QPointF(ctr_offset_x1, float(pos1.y()))
            ctr_point2 = QtCore.QPointF(ctr_offset_x2, float(pos2.y()))
            path.cubicTo(ctr_point1, ctr_point2, pos2)
            self.setPath(path)
            return

        # ANGLE / orthogonal:
        ctr_offset_x1, ctr_offset_x2 = float(pos1.x()), float(pos2.x())
        distance = abs(ctr_offset_x1 - ctr_offset_x2) / 2.0

        # Small floor to avoid degenerate elbows when ports are close/same-x.
        if distance < 40.0:
            distance = 40.0

        ctr_offset_x1 += s1 * distance
        ctr_offset_x2 += s2 * distance

        ctr_point1 = QtCore.QPointF(ctr_offset_x1, float(pos1.y()))
        ctr_point2 = QtCore.QPointF(ctr_offset_x2, float(pos2.y()))
        path.lineTo(ctr_point1)
        path.lineTo(ctr_point2)
        path.lineTo(pos2)
        self.setPath(path)

    def _draw_path_vertical_smart(self: Any, start_port: Any, pos1: Any, pos2: Any, path: Any) -> None:
        """Optional: patched vertical routing too (keeps behavior symmetric)."""
        if not callable(orig_vertical):
            return

        layout = None
        try:
            layout = self.viewer_pipe_layout()
        except Exception:
            layout = None

        if layout not in (PipeLayoutEnum.CURVED.value, PipeLayoutEnum.ANGLE.value):
            return orig_vertical(self, start_port, pos1, pos2, path)  # type: ignore[misc]

        end_port = _end_port_for(self, start_port)

        s1 = _side_sign_y(start_port, float(pos1.y()))
        if end_port is not None:
            s2 = _side_sign_y(end_port, float(pos2.y()))
        else:
            dy = float(pos2.y()) - float(pos1.y())
            s2 = 1 if dy >= 0 else -1

        if layout == PipeLayoutEnum.CURVED.value:
            ctr_offset_y1, ctr_offset_y2 = float(pos1.y()), float(pos2.y())
            tangent = abs(ctr_offset_y1 - ctr_offset_y2)
            try:
                max_height = float(start_port.node.boundingRect().height())
                tangent = min(tangent, max_height)
            except Exception:
                pass

            ctr_offset_y1 += s1 * tangent
            ctr_offset_y2 += s2 * tangent

            ctr_point1 = QtCore.QPointF(float(pos1.x()), ctr_offset_y1)
            ctr_point2 = QtCore.QPointF(float(pos2.x()), ctr_offset_y2)
            path.cubicTo(ctr_point1, ctr_point2, pos2)
            self.setPath(path)
            return

        distance = abs(float(pos1.y()) - float(pos2.y())) / 2.0
        if distance < 40.0:
            distance = 40.0

        ctr_point1 = QtCore.QPointF(float(pos1.x()), float(pos1.y()) + s1 * distance)
        ctr_point2 = QtCore.QPointF(float(pos2.x()), float(pos2.y()) + s2 * distance)
        path.lineTo(ctr_point1)
        path.lineTo(ctr_point2)
        path.lineTo(pos2)
        self.setPath(path)

    # Install patch.
    PipeItem._draw_path_horizontal = _draw_path_horizontal_smart  # type: ignore[assignment]
    if callable(orig_vertical):
        PipeItem._draw_path_vertical = _draw_path_vertical_smart  # type: ignore[assignment]

    PipeItem._simulator_smart_patch = True  # type: ignore[attr-defined]

    if log is not None:
        try:
            log.info("Installed smart pipe routing patch (NodeGraphQt)")
        except Exception:
            pass
    return True
