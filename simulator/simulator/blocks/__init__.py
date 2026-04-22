"""simulator.blocks

Block library definitions.

Blocks are plugins that define:
- ports (inputs/outputs + semantics)
- parameters (schema + defaults)
- compilation hooks to various engines (python-control, pathsim, bdsim)

The UI layer builds node widgets from these specs, and the compilers turn IR
into runnable/analysable models.
"""

from __future__ import annotations

from .registry import BlockRegistry, default_registry

__all__ = ["BlockRegistry", "default_registry"]
