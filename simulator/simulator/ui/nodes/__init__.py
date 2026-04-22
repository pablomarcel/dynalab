"""simulator.ui.nodes

Custom node classes for NodeGraphQt/OdenGraphQt.

Each node class defines:
- display name
- input/output ports
- exposed properties (edited in inspector)
- mapping from UI node -> IR block (block_id, block_type, params)

These nodes are installed into the NodeGraph palette by ui.graph.node_factory.
"""

from __future__ import annotations
