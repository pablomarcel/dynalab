"""simulator.core.project

Project file IO + migrations.

A project file (recommended extension: *.simproj) typically contains:
- model_ir: semantic IR (ProjectIR)
- ui_session: NodeGraphQt/OdenGraphQt session JSON (layout/zoom/etc.)

This separation keeps semantics stable even if the UI session format evolves.
"""

from __future__ import annotations
