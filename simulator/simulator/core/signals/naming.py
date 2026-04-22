"""simulator.core.signals.naming

Deterministic naming helpers.

In a port-graph IR, the most reliable identifiers are port IDs. However, for
engine compilation (especially python-control interconnect), it is convenient
to produce stable "signal names" that can be:
- displayed to the user
- used as named connections in an interconnect graph

Policy:
- default signal name for a port is its port id
- optionally, we can generate shorter aliases for readability
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from ..ir.types import ProjectIR, Port


_SAFE_RE = re.compile(r"[^a-zA-Z0-9_\.:]")


def sanitize_signal_name(name: str) -> str:
    """Make a name safe for engines that dislike spaces/special chars."""
    name = name.strip()
    name = name.replace(" ", "_")
    return _SAFE_RE.sub("_", name)


@dataclass(frozen=True)
class SignalNames:
    """Mapping from port_id -> signal_name."""

    port_to_signal: Dict[str, str]

    def signal_for(self, port_id: str) -> str:
        return self.port_to_signal[port_id]


def build_signal_names(ir: ProjectIR, *, prefer_port_name: bool = False) -> SignalNames:
    """Build deterministic signal names.

    Parameters
    ----------
    prefer_port_name:
        If True, tries to use "<block>_<portname>" instead of full port_id when safe.
        Falls back to port_id if collisions occur.
    """
    mapping: Dict[str, str] = {}

    # Gather all ports.
    ports: List[Port] = []
    for b in ir.blocks:
        ports.extend(b.inputs)
        ports.extend(b.outputs)

    if not prefer_port_name:
        for p in ports:
            mapping[p.id] = sanitize_signal_name(p.id)
        return SignalNames(mapping)

    # Try shorter names, resolve collisions deterministically.
    candidates: Dict[str, str] = {}
    for p in ports:
        # port ids recommended "<block>.<name>"
        if "." in p.id:
            blk, _ = p.id.split(".", 1)
            cand = f"{blk}_{p.name}"
        else:
            cand = p.id
        candidates[p.id] = sanitize_signal_name(cand)

    # Detect collisions
    inv: Dict[str, List[str]] = {}
    for pid, s in candidates.items():
        inv.setdefault(s, []).append(pid)

    for s, pids in inv.items():
        if len(pids) == 1:
            mapping[pids[0]] = s
        else:
            # collision: use full port ids for those ports
            for pid in sorted(pids):
                mapping[pid] = sanitize_signal_name(pid)

    return SignalNames(mapping)
