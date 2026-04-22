"""simulator.ui.nodes.base_node

Base node class for NodeGraphQt/OdenGraphQt custom nodes.

Why the inspector showed (unknown) + "No parameters"
-----------------------------------------------
NodeGraphQt's BaseNode often requires *declaring* custom properties before
set_property/get_property will work. In that case:

- set_property("block_type", "tf") raises -> we swallowed it
- get_property("block_type") then returns None -> we fall back to "unknown"

Result:
- graph_to_ir sees block_type="unknown" and params={}
- inspector can't pick the right editors -> shows "No parameters"

This file fixes that by:
- creating/declaring custom properties (block_id, block_type, params) using
  whatever API the installed NodeGraphQt fork exposes (create_property /
  add_custom_property / add_property ...)
- then setting them safely.

Design goals
- Compatible across forks (NodeGraphQt vs OdenGraphQt).
- Provide stable semantic properties:
    - block_id (str)
    - block_type (str)
    - params (dict)
- Keep subclass API tiny:
    - set NODE_NAME in each subclass
    - implement init_ports()
    - implement default_params()
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import sys


def _import_base_node():
    """Import BaseNode from whichever backend is in use.

    Priority rules:
    1) If a backend module is already imported, prefer that (avoids mismatch).
    2) Else prefer OdenGraphQt if importable, otherwise NodeGraphQt.
    """
    if "OdenGraphQt" in sys.modules:
        try:
            from OdenGraphQt import BaseNode as _BaseNode  # type: ignore
            return _BaseNode, "OdenGraphQt"
        except Exception:
            pass

    if "NodeGraphQt" in sys.modules:
        try:
            from NodeGraphQt import BaseNode as _BaseNode  # type: ignore
            return _BaseNode, "NodeGraphQt"
        except Exception:
            pass

    try:
        from OdenGraphQt import BaseNode as _BaseNode  # type: ignore
        return _BaseNode, "OdenGraphQt"
    except Exception:
        from NodeGraphQt import BaseNode as _BaseNode  # type: ignore
        return _BaseNode, "NodeGraphQt"


_BaseNode, _BACKEND_NAME = _import_base_node()


class SimBaseNode(_BaseNode):
    """Common base class for all simulator nodes."""

    # NodeGraphQt type id is commonly: f"{__identifier__}.{NODE_NAME}" (fork dependent).
    __identifier__ = "simulator.nodes"
    NODE_NAME = "Base"

    def __init__(self, qgraphics_item: Any | None = None) -> None:
        # NodeGraphQt BaseNode supports BaseNode(qgraphics_item=None).
        # Some forks may not accept args; we fall back safely.
        if qgraphics_item is None:
            super().__init__()
        else:
            try:
                super().__init__(qgraphics_item)
            except TypeError:
                super().__init__()

        # Visible title (NodeGraphQt already has a built-in "name" concept).
        try:
            self.set_name(self.NODE_NAME)
        except Exception:
            pass

        # Declare + set the core semantic properties.
        # These MUST exist so session_adapter can export correct block_type + params.
        self._set_prop_safe("block_id", self.name() if callable(getattr(self, "name", None)) else self.NODE_NAME)
        self._set_prop_safe("block_type", "unknown")
        self._set_prop_safe("params", {})

        # Subclass hooks
        self.init_ports()
        self._init_default_params()

    # ----------------------
    # Hooks for subclasses
    # ----------------------
    def init_ports(self) -> None:
        """Create input/output ports. Subclasses override."""
        return

    def default_params(self) -> Dict[str, Any]:
        """Return default params dict. Subclasses override."""
        return {}

    # ----------------------
    # Semantic identity API (used by node_factory + inspector)
    # ----------------------
    def set_block_identity(self, *, block_id: str, block_type: str, name: Optional[str] = None) -> None:
        disp = name or block_id
        self._set_prop_safe("block_id", block_id)
        self._set_prop_safe("block_type", block_type)

        # Also set visible title.
        try:
            self.set_name(disp)
        except Exception:
            pass

    def get_block_id(self) -> str:
        return str(
            self._get_prop_safe(
                "block_id", self.name() if callable(getattr(self, "name", None)) else self.NODE_NAME
            )
        )

    def get_block_type(self) -> str:
        return str(self._get_prop_safe("block_type", "unknown"))

    def get_params(self) -> Dict[str, Any]:
        p = self._get_prop_safe("params", {})
        return dict(p) if isinstance(p, dict) else {}

    def set_params(self, params: Dict[str, Any]) -> None:
        self._set_prop_safe("params", dict(params))

    def update_param(self, key: str, value: Any) -> None:
        p = self.get_params()
        p[key] = value
        self.set_params(p)

    # ----------------------
    # Internal
    # ----------------------
    def _init_default_params(self) -> None:
        defaults = self.default_params()
        if not defaults:
            return
        p = self.get_params()
        for k, v in defaults.items():
            p.setdefault(k, v)
        self.set_params(p)

    def _declare_property_best_effort(self, key: str, value: Any) -> None:
        """Best-effort: declare/create a custom property on NodeGraphQt forks.

        NodeGraphQt has used different APIs over time, including:
        - create_property(name, value, ...)
        - add_custom_property(name, value, ...)
        - add_property(name, value, ...)
        - create_custom_property(name, value, ...)
        This tries them in order and ignores failures.
        """
        for m in ("create_property", "add_custom_property", "add_property", "create_custom_property"):
            fn = getattr(self, m, None)
            if not callable(fn):
                continue
            try:
                fn(key, value)
                return
            except TypeError:
                # Some versions require keyword args.
                try:
                    fn(name=key, value=value)
                    return
                except Exception:
                    continue
            except Exception:
                continue

    def _set_prop_safe(self, key: str, value: Any) -> None:
        """Set a property robustly across forks.

        Strategy:
        1) Try set_property directly.
        2) If it fails, declare the property then try set_property again.
        3) Last-resort: stash into _properties dict if present.
        """
        sp = getattr(self, "set_property", None)
        if callable(sp):
            try:
                sp(key, value)
                return
            except Exception:
                pass

            # try declaring the property then setting again
            self._declare_property_best_effort(key, value)
            try:
                sp(key, value)
                return
            except Exception:
                pass

        # Some forks store custom properties differently; do best-effort.
        try:  # pragma: no cover
            if hasattr(self, "_properties") and isinstance(self._properties, dict):
                self._properties[key] = value
        except Exception:
            pass

    def _get_prop_safe(self, key: str, default: Any = None) -> Any:
        gp = getattr(self, "get_property", None)
        if callable(gp):
            try:
                v = gp(key)
                return default if v is None else v
            except Exception:
                return default

        try:  # pragma: no cover
            if hasattr(self, "_properties") and isinstance(self._properties, dict):
                return self._properties.get(key, default)
        except Exception:
            pass

        return default
