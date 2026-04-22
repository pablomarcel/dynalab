"""simulator.core.signals.sample_time

Sample-time (Ts) utilities.

For MVP:
- project meta.domain controls default interpretation.
- If domain is discrete, meta.Ts is required.
- Blocks may override Ts for multi-rate (future). For now, we only *check*.

Later:
- implement rate transition blocks
- implement Ts propagation through graph
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..ir.types import ProjectIR, Block, Wire


@dataclass(frozen=True)
class TsInfo:
    """Resolved Ts information for blocks."""

    project_domain: str
    project_Ts: Optional[float]
    block_Ts: Dict[str, Optional[float]]  # block_id -> resolved Ts


def resolve_block_ts(ir: ProjectIR) -> TsInfo:
    """Resolve each block's effective Ts.

    Rule:
    - effective domain = block.domain or project.domain
    - if effective domain is discrete => Ts = block.Ts or project.Ts
    - if effective domain is continuous => Ts = None (ignored)
    """
    project_dom = ir.meta.domain
    project_Ts = ir.meta.Ts

    out: Dict[str, Optional[float]] = {}
    for b in ir.blocks:
        dom = b.domain or project_dom
        if dom == "discrete":
            out[b.id] = b.Ts if (b.Ts is not None and b.Ts > 0) else project_Ts
        else:
            out[b.id] = None

    return TsInfo(project_domain=project_dom, project_Ts=project_Ts, block_Ts=out)


def check_multirate_compatibility(ir: ProjectIR) -> List[str]:
    """Return warnings/errors about multi-rate wiring.

    MVP behavior:
    - if two discrete blocks with different Ts are directly connected, warn.
    - if discrete connects to continuous or vice versa, warn (until rate-transition blocks exist).
    """
    msgs: List[str] = []
    tsinfo = resolve_block_ts(ir)

    # Map port->block for endpoints.
    port_to_block: Dict[str, str] = {}
    for b in ir.blocks:
        for p in b.inputs + b.outputs:
            port_to_block[p.id] = b.id

    block_by_id: Dict[str, Block] = {b.id: b for b in ir.blocks}

    def eff_domain(bid: str) -> str:
        b = block_by_id[bid]
        return b.domain or ir.meta.domain

    for w in ir.wires:
        sb = port_to_block.get(w.src)
        db = port_to_block.get(w.dst)
        if not sb or not db:
            continue

        dom_s = eff_domain(sb)
        dom_d = eff_domain(db)

        if dom_s != dom_d:
            msgs.append(
                f"Wire '{w.id}' connects {sb}({dom_s}) -> {db}({dom_d}). "
                "Add explicit rate transition / discretization blocks (future)."
            )
            continue

        if dom_s == "discrete":
            Ts_s = tsinfo.block_Ts.get(sb)
            Ts_d = tsinfo.block_Ts.get(db)
            if Ts_s and Ts_d and abs(Ts_s - Ts_d) > 1e-12:
                msgs.append(
                    f"Wire '{w.id}' connects discrete blocks with different Ts: "
                    f"{sb}(Ts={Ts_s}) -> {db}(Ts={Ts_d}). Add a rate transition block (future)."
                )

    return msgs
