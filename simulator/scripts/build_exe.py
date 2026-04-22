#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/build_exe.py

Optional PyInstaller build entrypoint.

This script doesn't run PyInstaller automatically in CI; it's a convenience tool.

Usage (from machines/simulator):
    python scripts/build_exe.py --name Simulator

Then run the printed command (or use the returned spec).

Notes:
- Packaging Qt apps can be fiddly; you'll likely need to add datas for:
  - Qt plugins
  - your .qss files and icons (Qt resources)
  - NodeGraphQt/OdenGraphQt resources (if any)
- Start with a one-folder build and iterate.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="simulator", help="Executable name")
    ap.add_argument("--onefile", action="store_true", help="Build a single-file executable (harder)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    entry = root / "simulator" / "app.py"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        f"--name={args.name}",
        "--windowed",
        str(entry),
    ]

    if args.onefile:
        cmd.insert(1, "--onefile")

    # Basic data include: ship demo projects alongside build
    demos_dir = root / "simulator" / "in" / "demos"
    if demos_dir.exists():
        cmd.append(f"--add-data={demos_dir}{Path(':')}{Path('simulator/in/demos')}")

    print("Run this command from the repo root:")
    print("  " + " ".join(shlex.quote(c) for c in cmd))
    print()
    print("If icons/qss are missing, consider adding resources as --add-data as well.")


if __name__ == "__main__":
    main()
