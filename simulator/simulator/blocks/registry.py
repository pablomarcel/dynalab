"""simulator.blocks.registry

Block registry.

The registry is the single source of truth for which block types exist and how to:
- create default IR blocks
- provide UI metadata (name/category/icon)
- compile into engines (analysis/simulation)

This module intentionally does not import UI code.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .spec import BlockSpec


class BlockRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, BlockSpec] = {}

    def register(self, spec: BlockSpec) -> None:
        if spec.type in self._specs:
            raise ValueError(f"Block type already registered: {spec.type}")
        self._specs[spec.type] = spec

    def get(self, block_type: str) -> BlockSpec:
        try:
            return self._specs[block_type]
        except KeyError:
            raise KeyError(f"Unknown block type: {block_type}")

    def maybe_get(self, block_type: str, default: Optional[BlockSpec] = None) -> Optional[BlockSpec]:
        """Return spec if registered else default (non-throwing helper).

        This is used by UI code paths that want to create nodes even when a spec is missing,
        without crashing the app.
        """
        return self._specs.get(block_type, default)

    def has(self, block_type: str) -> bool:
        return block_type in self._specs

    def types(self) -> List[str]:
        return sorted(self._specs.keys())

    def specs(self) -> List[BlockSpec]:
        return [self._specs[t] for t in self.types()]


def default_registry() -> BlockRegistry:
    """Create the default registry with the MVP block set.

    We keep the default set small but composable:
    - step (source)
    - sum (signed summing junction)
    - sum_glyph (signed summing junction with Ogata-style glyph)
    - gain
    - gain_flipped
    - tf (transfer function)
    - tf_flipped
    - delay (unit delay)
    - scope (sink)
    """
    reg = BlockRegistry()

    # Local imports so registry module stays cheap to import.
    from .lti.gain import GainSpec
    from .lti.gain_flipped import GainFlippedSpec
    from .lti.sum import SumSpec
    from .lti.sum_glyph import SumGlyphSpec
    from .lti.tf import TransferFunctionSpec
    from .lti.tf_flipped import TFFlippedSpec
    from .lti.delay import UnitDelaySpec
    from .sources.step import StepSpec
    from .sinks.scope import ScopeSpec

    reg.register(StepSpec())
    reg.register(SumSpec())
    reg.register(SumGlyphSpec())
    reg.register(GainSpec())
    reg.register(GainFlippedSpec())
    reg.register(TransferFunctionSpec())
    reg.register(TFFlippedSpec())
    reg.register(UnitDelaySpec())
    reg.register(ScopeSpec())

    return reg
