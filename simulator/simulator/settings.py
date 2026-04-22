"""simulator.settings

User settings + defaults.

We store settings via QSettings so it works cross-platform and doesn't require
manual config file management.

Key goals:
- keep app bootstrap simple
- provide a single place for defaults (theme, recent files, wire style, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6 import QtCore

from .log import get_logger


DEFAULT_THEME = "light"  # "dark" | "light"   (MVP: light for visibility)
DEFAULT_WIRE_STYLE = "angled"  # "curved" | "straight" | "angled" (orthogonal)


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def _theme_dir() -> Path:
    return _package_dir() / "ui" / "theme"


@dataclass(frozen=True)
class AppDefaults:
    theme: str = DEFAULT_THEME
    wire_style: str = DEFAULT_WIRE_STYLE
    recent_files_max: int = 10


class SettingsStore:
    """Thin wrapper around QSettings with typed helpers."""

    def __init__(self) -> None:
        self._log = get_logger(__name__)
        self._q = QtCore.QSettings()
        self._defaults = AppDefaults()

    # -----------------------
    # basic get/set utilities
    # -----------------------
    def reset(self) -> None:
        self._q.clear()

    def get_str(self, key: str, default: str = "") -> str:
        v = self._q.value(key, defaultValue=default)
        return str(v)

    def set_str(self, key: str, value: str) -> None:
        self._q.setValue(key, value)

    def get_list(self, key: str, default: Optional[list[str]] = None) -> list[str]:
        if default is None:
            default = []
        v = self._q.value(key, defaultValue=default)
        if v is None:
            return list(default)
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    def set_list(self, key: str, value: list[str]) -> None:
        self._q.setValue(key, value)

    # -----------------------
    # app-level settings
    # -----------------------
    def theme_name(self) -> str:
        t = self.get_str("ui/theme", self._defaults.theme)
        return t if t in ("dark", "light") else self._defaults.theme

    def set_theme_name(self, theme: str) -> None:
        if theme not in ("dark", "light"):
            raise ValueError(f"Invalid theme: {theme}")
        self.set_str("ui/theme", theme)

    def wire_style_name(self) -> str:
        """Wire layout: curved | straight | angled (orthogonal)."""
        v = self.get_str("ui/wire_style", self._defaults.wire_style).strip().lower()
        return v if v in ("curved", "straight", "angled") else self._defaults.wire_style

    def set_wire_style_name(self, style: str) -> None:
        v = (style or "").strip().lower()
        if v not in ("curved", "straight", "angled"):
            raise ValueError(f"Invalid wire style: {style}")
        self.set_str("ui/wire_style", v)

    def load_theme_qss(self) -> str:
        """Return theme QSS content (empty string if missing)."""
        theme = self.theme_name()
        qss_path = _theme_dir() / f"{theme}.qss"
        try:
            return qss_path.read_text(encoding="utf-8")
        except Exception as e:  # pragma: no cover
            self._log.warning("Theme QSS missing (%s): %s", str(qss_path), e)
            return ""

    # -----------------------
    # recent files
    # -----------------------
    def recent_files(self) -> list[str]:
        files = self.get_list("project/recent_files", [])
        out: list[str] = []
        for f in files:
            try:
                p = Path(f).expanduser()
                out.append(str(p))
            except Exception:
                continue
        return out

    def add_recent_file(self, path: str) -> None:
        p = str(Path(path).expanduser().resolve())
        files = [x for x in self.recent_files() if x != p]
        files.insert(0, p)
        files = files[: self._defaults.recent_files_max]
        self.set_list("project/recent_files", files)
