"""simulator.engines

Engine layer:
- runs analysis or simulation given a ProjectIR
- returns structured results suitable for UI rendering

Engines depend on compilers, but should not depend on UI.
"""

from __future__ import annotations
