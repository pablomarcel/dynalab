"""simulator.ui

PySide6 UI layer.

This package contains:
- MainWindow
- NodeGraphQt/OdenGraphQt editor host
- inspector widgets
- plotting panes

Rule: UI depends on core/blocks/engines. Core/engines must not depend on UI.
"""

from __future__ import annotations
