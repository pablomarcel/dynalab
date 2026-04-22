"""simulator.__main__

Entry point for:
- `python -m simulator`
- console script `simulator` (configured in pyproject.toml)

This keeps startup logic small and delegates to simulator.app.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="simulator",
        description="PySide6 block-diagram simulator (Simulink-style) for the machines project.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    p.add_argument(
        "--reset-settings",
        action="store_true",
        help="Reset stored user settings before launching the app.",
    )
    p.add_argument(
        "--project",
        type=str,
        default=None,
        help="Optional path to a .simproj project file to open on launch.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Local import so argparse works even if GUI deps fail to import.
    from .app import run_app

    return run_app(
        debug=args.debug,
        reset_settings=args.reset_settings,
        project_path=args.project,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
