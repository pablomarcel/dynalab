"""simulator.ui.inspector.editors

Optional specialized editors for common block parameters.

MVP uses generic JSON/text editing (InspectorPanel). This module provides reusable
widgets we can swap in later for a nicer experience.

Included (simple):
- VectorEditor: edit list[float] as comma/space-separated numbers (also accepts JSON list).
- NumDenEditor: edit numerator/denominator for TF blocks.

NOTE
----
InspectorPanel expects TF editor to provide a .value() method returning
{"num": [...], "den": [...]}.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from PySide6 import QtCore, QtWidgets


class VectorEditor(QtWidgets.QLineEdit):
    """Edit a list of floats as a comma/space-separated string.

    Accepts:
      - "1, 2, 3"
      - "1 2 3"
      - "1;2;3"
      - "[1, 2, 3]" (JSON list)

    Emits valueChanged(list[float]) when editing finishes.
    """

    valueChanged = QtCore.Signal(list)

    def __init__(self, values: Optional[list[float]] = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("e.g. 1, 2, 3")
        self.setValues(values or [])
        self.editingFinished.connect(self._emit)

    def values(self) -> list[float]:
        txt = (self.text() or "").strip()
        if not txt:
            return []

        # JSON list support
        if txt.startswith("[") and txt.endswith("]"):
            try:
                arr = json.loads(txt)
                if isinstance(arr, list):
                    return [float(x) for x in arr]
            except Exception:
                pass

        # Split by comma/semicolon/whitespace
        t = txt.replace(";", ",").replace("\n", " ").replace("\t", " ")
        parts = [p for p in re.split(r"[ ,]+", t) if p]
        out: list[float] = []
        for part in parts:
            out.append(float(part))
        return out

    # Alias used by some generic collection paths.
    def value(self) -> list[float]:  # noqa: D401
        """Return the current list of floats."""
        return self.values()

    def setValues(self, values: list[float]) -> None:
        self.setText(", ".join(str(float(v)) for v in values))

    def _emit(self) -> None:
        try:
            self.valueChanged.emit(self.values())
        except Exception:
            # Keep UI forgiving; validation happens on Apply.
            pass


class NumDenEditor(QtWidgets.QWidget):
    """Edit TF numerator/denominator."""

    valueChanged = QtCore.Signal(list, list)  # num, den

    def __init__(
        self,
        *,
        num: Optional[list[float]] = None,
        den: Optional[list[float]] = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._num = VectorEditor(num or [])
        self._den = VectorEditor(den or [])

        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("num", self._num)
        form.addRow("den", self._den)

        self._num.valueChanged.connect(lambda _: self._emit())
        self._den.valueChanged.connect(lambda _: self._emit())

    def num(self) -> list[float]:
        return self._num.values()

    def den(self) -> list[float]:
        return self._den.values()

    def value(self) -> dict[str, list[float]]:
        """Return TF params dict compatible with InspectorPanel."""
        return {"num": self.num(), "den": self.den()}

    def setNumDen(self, num: list[float], den: list[float]) -> None:
        self._num.setValues(num)
        self._den.setValues(den)

    def _emit(self) -> None:
        self.valueChanged.emit(self.num(), self.den())
