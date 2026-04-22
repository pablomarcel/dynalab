"""simulator.blocks.spec

BlockSpec interface.

Each block type defines:
- UI metadata (palette name/category/icon)
- default IR block construction (ports + default params)
- compilation hooks (to python-control, to simulation engines)

The goal is to keep your compilers clean: they ask the spec how to interpret a block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from simulator.simulator.core.ir.types import Block, Port


@dataclass(frozen=True)
class PaletteInfo:
    category: str
    display_name: str
    icon: Optional[str] = None  # path to icon in Qt resources, optional


@runtime_checkable
class BlockSpec(Protocol):
    """Protocol for a block specification."""

    # Unique type string used in IR (e.g. "tf", "sum", "gain")
    type: str

    def palette(self) -> PaletteInfo:
        """How it appears in the UI palette."""

    def default_block(self, *, block_id: str) -> Block:
        """Create a default IR Block instance."""

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Return list of validation errors for params (empty if OK)."""

    # Compilation hooks (optional per engine). For MVP, we implement control only.
    def to_control(self, block: Block) -> Any:
        """Return a python-control component for this block.

        For example:
        - tf -> control.tf(...)
        - gain -> control.tf([k], [1])
        - sum -> control.summing_junction(...)
        - sources/sinks might compile differently (or be handled by compiler).
        """
