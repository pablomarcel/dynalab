"""simulator.blocks.sources

Source block specs (inputs/excitations).

For MVP analysis, sources are mainly used to define IO ports and provide defaults.
For time simulation later, sources will generate time-series signals.

Common sources:
- step
- impulse
- constant
"""

from __future__ import annotations
