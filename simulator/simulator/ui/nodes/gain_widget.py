"""simulator.ui.nodes.gain_widget

Helper graphics item used to create a *flipped* Gain node in NodeGraphQt.

Goal
----
For feedback paths, we want the Gain block to have:
  - input port on the RIGHT
  - output port on the LEFT

NodeGraphQt's default horizontal layout places inputs on the left and outputs on
the right. In NodeGraphQt v0.6.44, that logic lives in:
  NodeGraphQt.qgraphics.node_base.NodeItem._align_ports_horizontal

This file subclasses NodeItem and overrides just that method, swapping the side
placement while keeping the rest of NodeGraphQt intact.

Notes
-----
- We intentionally keep this as a very small override to avoid breaking your app.
- Works for horizontal layout only. Vertical layout is untouched.
"""

from __future__ import annotations

from typing import Any

# Prefer the active backend if a fork is installed.
try:  # pragma: no cover
    from NodeGraphQt.qgraphics.node_base import NodeItem  # type: ignore
    from NodeGraphQt.constants import PortEnum  # type: ignore
except Exception:  # pragma: no cover
    from OdenGraphQt.qgraphics.node_base import NodeItem  # type: ignore
    from OdenGraphQt.constants import PortEnum  # type: ignore


class FlippedPortNodeItem(NodeItem):
    """Node item that swaps port sides in horizontal layout.

    Inputs -> right side
    Outputs -> left side
    """

    def _align_ports_horizontal(self, v_offset: float) -> None:  # noqa: D401
        # This is a surgical mirror of NodeGraphQt v0.6.44 implementation:
        # we swap the X positions (and the text alignment math).
        width = getattr(self, "_width", 0.0)
        txt_offset = PortEnum.CLICK_FALLOFF.value - 2
        spacing = 1

        # --- inputs on RIGHT ---
        inputs = [p for p in self.inputs if p.isVisible()]
        if inputs:
            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            port_x = width - (port_width / 2)
            port_y = v_offset
            for port in inputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing

        # input port text: place LEFT of the port (mirror of default output text)
        for port, text in getattr(self, "_input_items", {}).items():
            try:
                if port.isVisible():
                    txt_width = text.boundingRect().width() - txt_offset
                    txt_x = port.x() - txt_width
                    text.setPos(txt_x, port.y() - 1.5)
            except Exception:
                continue

        # --- outputs on LEFT ---
        outputs = [p for p in self.outputs if p.isVisible()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            port_x = (port_width / 2) * -1
            port_y = v_offset
            for port in outputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing

        # output port text: place RIGHT of the port (mirror of default input text)
        for port, text in getattr(self, "_output_items", {}).items():
            try:
                if port.isVisible():
                    txt_x = port.boundingRect().width() / 2 - txt_offset
                    text.setPos(txt_x, port.y() - 1.5)
            except Exception:
                continue
