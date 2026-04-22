"""simulator.core.project.project_io

Read/write project files.

Format (v1):
{
  "format": "simproj",
  "format_version": 1,
  "model_ir": { ... ProjectIR dict ... },
  "ui_session": { ... NodeGraphQt/OdenGraphQt session json ... }
}

The UI layer owns ui_session, the core owns model_ir.

We keep this module dependency-light (no NodeGraphQt imports).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..ir.normalize import normalize_ir
from ..ir.types import ProjectIR
from ..ir.validate import validate_ir


class ProjectIOError(RuntimeError):
    pass


def load_simproj(path: str | Path, *, validate: bool = True, normalize: bool = True) -> tuple[ProjectIR, dict[str, Any]]:
    """Load a *.simproj file.

    Returns
    -------
    (ir, ui_session)
    """
    p = Path(path)
    if not p.exists():
        raise ProjectIOError(f"Project file not found: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))

    if data.get("format") != "simproj":
        raise ProjectIOError("Invalid project format (expected format='simproj').")

    fv = int(data.get("format_version", 1))
    if fv != 1:
        raise ProjectIOError(f"Unsupported project format_version: {fv}")

    ir_dict = data.get("model_ir", {})
    ui_session = data.get("ui_session", {}) or {}

    ir = ProjectIR.from_dict(ir_dict)

    if normalize:
        ir = normalize_ir(ir)
    if validate:
        validate_ir(ir)

    return ir, ui_session


def save_simproj(
    path: str | Path,
    *,
    ir: ProjectIR,
    ui_session: Optional[dict[str, Any]] = None,
    validate: bool = True,
    normalize: bool = True,
) -> None:
    """Save a *.simproj file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    ir_out = ir
    if normalize:
        ir_out = normalize_ir(ir_out)
    if validate:
        validate_ir(ir_out)

    payload: dict[str, Any] = {
        "format": "simproj",
        "format_version": 1,
        "model_ir": ir_out.to_dict(),
        "ui_session": ui_session or {},
    }

    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
