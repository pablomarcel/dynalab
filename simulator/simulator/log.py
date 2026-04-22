"""simulator.log

Small, dependency-free logging utilities.

- configure_logging() sets up a consistent format for console logging.
- get_logger() returns a module logger.

This keeps logging uniform across UI, core, compilers, engines.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def configure_logging(*, debug: bool = False, level: Optional[int] = None) -> None:
    """Configure root logging.

    Parameters
    ----------
    debug:
        If True, sets level to DEBUG unless `level` is provided.
    level:
        Explicit logging level override (e.g., logging.INFO).
    """
    if level is None:
        level = logging.DEBUG if debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Remove pre-existing handlers to avoid duplicate logs when reloading.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)

    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
