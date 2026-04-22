#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/dev_run.py

Convenience launcher for local development.

Usage (from machines/simulator):
    python scripts/dev_run.py
    python scripts/dev_run.py --demo unity
    python scripts/dev_run.py --demo nested
    python scripts/dev_run.py --file path/to/project.simproj

Notes:
- This uses the installed package imports (simulator.*). For editable dev:
    pip install -e .
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6 import QtWidgets

from simulator.simulator.settings import SettingsStore
from simulator.simulator.ui.main_window import MainWindow


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", choices=["unity", "nested"], default=None, help="Load a built-in demo project")
    ap.add_argument("--file", default=None, help="Open a .simproj file")
    args = ap.parse_args()

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    settings = SettingsStore()
    win = MainWindow(settings=settings)

    if args.demo == "unity":
        demo = Path(__file__).resolve().parents[1] / "simulator" / "in" / "demos" / "unity_feedback.simproj"
        win.open_project(str(demo))
    elif args.demo == "nested":
        demo = Path(__file__).resolve().parents[1] / "simulator" / "in" / "demos" / "nested_loops.simproj"
        win.open_project(str(demo))
    elif args.file:
        win.open_project(args.file)

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
