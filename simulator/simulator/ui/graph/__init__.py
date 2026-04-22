"""simulator.ui.graph

Node editor host + UI session/IR adapters.

This layer wraps NodeGraphQt/OdenGraphQt so the rest of the app can treat the
editor like a normal widget with:
- load_from_project(ir, ui_session)
- export_project() -> (ir, ui_session)
- signals for selection and changes
"""

from __future__ import annotations
