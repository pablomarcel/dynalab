"""simulator.compilers

Compilers translate ProjectIR into engine-specific models.

- control_compiler: IR -> python-control interconnect model (LTI analysis)
- pathsim_compiler: IR -> PathSim graph (time simulation, optional)
- bdsim_compiler: IR -> bdsim graph (time simulation, optional)
"""

from __future__ import annotations
