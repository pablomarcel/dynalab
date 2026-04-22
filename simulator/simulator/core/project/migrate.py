"""simulator.core.project.migrate

Project/IR migration utilities.

Right now we only support IR schema v1. This file provides a clean place to:
- detect older/newer versions
- migrate dictionaries to the latest version before parsing into dataclasses

As you evolve the IR, keep migrations *pure* (dict in -> dict out).
"""

from __future__ import annotations

from typing import Any, Dict


class MigrationError(RuntimeError):
    pass


LATEST_IR_VERSION = 1


def migrate_ir_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate an IR dict to the latest supported version."""
    meta = d.get("meta", {}) or {}
    v = int(meta.get("version", 1))

    if v == LATEST_IR_VERSION:
        return d

    if v < 1:
        raise MigrationError(f"Unsupported IR version: {v}")

    # Placeholder for future migrations:
    # if v == 1: ...
    raise MigrationError(f"Cannot migrate IR version {v} to {LATEST_IR_VERSION} (no migration defined).")
