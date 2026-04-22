"""simulator.core.ir.normalize

Normalization passes for ProjectIR.

This module converts a "best effort" IR into a canonical form that compilers
can rely on. It does not attempt heavy semantic interpretation; its job is to:
- ensure empty names are filled
- ensure port ids follow a consistent scheme when possible
- ensure project-level Ts is propagated to blocks/ports where appropriate
- sort blocks/wires for deterministic serialization

Validation should be run either before or after normalization, depending on how
strict your UI export is. Typical flow:

    ir = export_from_ui(...)
    ir = normalize_ir(ir)
    validate_ir(ir)

"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Tuple

from .types import Block, Port, ProjectIR, Wire


def normalize_ir(ir: ProjectIR) -> ProjectIR:
    # Copy-on-write style: build new lists.
    meta = ir.meta

    blocks_out: List[Block] = []
    for b in ir.blocks:
        name = b.name or b.id

        # Apply project Ts if block is discrete or project is discrete and block has no Ts.
        Ts = b.Ts
        dom = b.domain or meta.domain

        if dom == "discrete" and (Ts is None or Ts <= 0):
            Ts = meta.Ts

        # Normalize ports: ensure ids exist and follow "<block>.<portname>" if missing.
        in_ports: List[Port] = []
        for p in b.inputs:
            pid = p.id or f"{b.id}.{p.name}"
            in_ports.append(
                Port(
                    id=pid,
                    name=p.name,
                    direction="in",
                    dim=p.dim,
                    sign=p.sign,
                    tags=dict(p.tags or {}),
                )
            )

        out_ports: List[Port] = []
        for p in b.outputs:
            pid = p.id or f"{b.id}.{p.name}"
            out_ports.append(
                Port(
                    id=pid,
                    name=p.name,
                    direction="out",
                    dim=p.dim,
                    sign=None,  # output signs not used
                    tags=dict(p.tags or {}),
                )
            )

        blocks_out.append(
            Block(
                id=b.id,
                type=b.type,
                name=name,
                domain=b.domain,
                Ts=Ts,
                inputs=in_ports,
                outputs=out_ports,
                params=dict(b.params or {}),
            )
        )

    # Sort blocks by id for stable serialization.
    blocks_out.sort(key=lambda x: x.id)

    # Normalize wires: ensure id exists and tags is dict; sort deterministically.
    wires_out: List[Wire] = []
    for i, w in enumerate(ir.wires):
        wid = w.id or f"w{i}"
        wires_out.append(Wire(id=wid, src=w.src, dst=w.dst, tags=dict(w.tags or {})))
    wires_out.sort(key=lambda x: x.id)

    # Normalize io lists: unique + stable order.
    def uniq_keep_order(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    io_in = uniq_keep_order(list(ir.io_inputs or []))
    io_out = uniq_keep_order(list(ir.io_outputs or []))

    return ProjectIR(meta=meta, blocks=blocks_out, wires=wires_out, io_inputs=io_in, io_outputs=io_out)
