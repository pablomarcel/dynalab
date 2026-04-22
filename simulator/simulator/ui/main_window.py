"""simulator.ui.main_window

Main application window.

This version includes:
- Delete selected nodes/wires (robust across NodeGraphQt forks)
- Explicit IO selection (Set as Input/Output)
- Debounced graph->IR export to avoid UI lag
- Wire Style menu to persist "Orthogonal (Square)" wiring.

Fix in this revision
--------------------
NodeGraphQt deletion APIs often return None even on success. The previous logic
treated None as failure and executed a fallback per-item delete, which could
double-delete nodes and trigger NodeGraphQt undo-stack KeyError crashes.

We treat "no exception" as success, regardless of return value, and we only
fall back when an exception is raised.

Updated:
- Adds "TF (Flipped)" to the Library palette (block_type: tf_flipped).
- Adds "Sum (Glyph)" to the Library palette (block_type: sum_glyph).
- UI polish (no functional changes):
  * Better first-launch dock sizing (Inspector is given a sensible width).
  * Minimum dock widths so panels don't collapse into unusable slivers.
  * Light styling for dock titles + library tree for a cleaner first impression.
  * Slightly larger toolbar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any, List

from PySide6 import QtCore, QtGui, QtWidgets

from simulator.simulator.blocks.registry import default_registry
from simulator.simulator.core.ir.types import ProjectIR
from simulator.simulator.core.project.project_io import load_simproj, save_simproj
from simulator.simulator.engines import control_engine
from simulator.simulator.log import get_logger
from simulator.simulator.settings import SettingsStore

from .graph.graph_host import GraphHost, MIME_BLOCKTYPE
from .inspector.inspector_panel import InspectorPanel
from .plots.plot_window import PlotWindow


def _icons_dir() -> Path:
    return Path(__file__).resolve().parent / "theme" / "icons"


def _icon(name: str) -> QtGui.QIcon:
    p = _icons_dir() / name
    if p.exists():
        return QtGui.QIcon(str(p))
    return QtGui.QIcon()


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, dict):
        return list(x.values())
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _call_ok(obj: Any, name: str, *args, **kwargs) -> bool:
    fn = getattr(obj, name, None)
    if not callable(fn):
        return False
    try:
        fn(*args, **kwargs)
        return True
    except Exception:
        return False


class BlockLibrary(QtWidgets.QTreeWidget):
    """Block palette: drag onto canvas or double-click to add."""

    sig_add_block = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setExpandsOnDoubleClick(True)
        self.setIndentation(14)
        self.setUniformRowHeights(True)
        self.setAnimated(True)

        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)

        self._build_tree()
        self.expandAll()
        self.itemDoubleClicked.connect(self._on_double_click)

        # Light styling for a cleaner palette (keeps app theme-independent).
        self.setStyleSheet(
            """
            QTreeWidget {
                border: none;
                background: transparent;
            }
            QTreeWidget::item {
                padding: 4px 2px;
            }
            QTreeWidget::item:selected {
                background: rgba(45, 125, 255, 0.20);
                color: black;
            }
            """
        )

    def _build_tree(self) -> None:
        self.clear()

        def add_cat(name: str):
            it = QtWidgets.QTreeWidgetItem([name])
            it.setFlags(it.flags() & ~QtCore.Qt.ItemIsSelectable)
            font = it.font(0)
            font.setBold(True)
            it.setFont(0, font)
            self.addTopLevelItem(it)
            return it

        def add_item(parent_it, label: str, block_type: str):
            it = QtWidgets.QTreeWidgetItem([label])
            it.setData(0, QtCore.Qt.UserRole, block_type)
            parent_it.addChild(it)

        src = add_cat("Sources")
        add_item(src, "Step", "step")
        add_item(src, "Impulse", "impulse")
        add_item(src, "Constant", "constant")

        lti = add_cat("LTI")
        add_item(lti, "TF       ( -> )", "tf")
        add_item(lti, "TF       ( <- )", "tf_flipped")
        add_item(lti, "Gain     ( -> )", "gain")
        add_item(lti, "Gain     ( <- )", "gain_flipped")
        add_item(lti, "Sum      ( ☐ )", "sum")
        add_item(lti, "Sum      ( ◯ )", "sum_glyph")
        add_item(lti, "z^-1     (Delay)", "delay")

        snk = add_cat("Sinks")
        add_item(snk, "Scope", "scope")
        add_item(snk, "Terminator", "terminator")

    def _block_type_from_item(self, item: QtWidgets.QTreeWidgetItem) -> str | None:
        bt = item.data(0, QtCore.Qt.UserRole)
        return bt if isinstance(bt, str) and bt else None

    def _on_double_click(self, item: QtWidgets.QTreeWidgetItem, col: int) -> None:
        bt = self._block_type_from_item(item)
        if bt:
            self.sig_add_block.emit(bt)

    def startDrag(self, supported_actions: QtCore.Qt.DropActions) -> None:  # noqa: N802
        item = self.currentItem()
        if item is None:
            return
        bt = self._block_type_from_item(item)
        if not bt:
            return

        md = QtCore.QMimeData()
        md.setData(MIME_BLOCKTYPE, bt.encode("utf-8"))

        drag = QtGui.QDrag(self)
        drag.setMimeData(md)
        drag.exec(QtCore.Qt.CopyAction)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *, settings: SettingsStore) -> None:
        super().__init__()
        self._log = get_logger(__name__)
        self._settings = settings
        self._registry = default_registry()

        self._current_path: Optional[str] = None
        self._ir: ProjectIR = ProjectIR()
        self._ui_session: dict = {}

        self._plot_win: PlotWindow | None = None
        self._selected_block_id: Optional[str] = None

        # Debounced sync timer (prevents re-export storm while dragging)
        self._sync_timer = QtCore.QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self._sync_from_ui)

        self.setWindowTitle("Simulator")
        self.resize(1500, 900)

        # General dock UX.
        self.setDockOptions(
            QtWidgets.QMainWindow.AnimatedDocks
            | QtWidgets.QMainWindow.AllowTabbedDocks
            | QtWidgets.QMainWindow.AllowNestedDocks
        )

        # Central: graph/canvas (pass settings so GraphHost can apply orthogonal wiring)
        self.graph = GraphHost(registry=self._registry, settings=self._settings)
        self.setCentralWidget(self.graph)

        # Left: library
        self.library = BlockLibrary()
        self.library.sig_add_block.connect(self._on_add_block)

        self._dock_lib = QtWidgets.QDockWidget("Library", self)
        self._dock_lib.setWidget(self.library)
        self._dock_lib.setObjectName("dock_library")
        self._dock_lib.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self._dock_lib.setMinimumWidth(220)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._dock_lib)

        # Right: inspector
        self.inspector = InspectorPanel(registry=self._registry)

        self._dock_ins = QtWidgets.QDockWidget("Inspector", self)
        self._dock_ins.setWidget(self.inspector)
        self._dock_ins.setObjectName("dock_inspector")
        self._dock_ins.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        self._dock_ins.setMinimumWidth(220)  # prevents tiny inspector on first launch
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock_ins)

        # Signals
        self.graph.sig_selection_changed.connect(self._on_selection_changed)
        self.inspector.sig_block_updated.connect(self._on_block_updated)
        self.graph.sig_ir_changed.connect(self._on_ir_changed)

        self._apply_window_styles()
        self._build_actions()

        restored = self._restore_ui_state()
        if not restored:
            self._apply_default_dock_sizes()

        self._update_status()

    # --------------------
    # Styling
    # --------------------
    def _apply_window_styles(self) -> None:
        # Subtle dock title + toolbar polish. Keep it light and theme-independent.
        self.setStyleSheet(
            """
            QDockWidget::title {
                padding: 6px 8px;
                font-weight: 700;
                background: rgba(0,0,0,0.03);
                border-bottom: 1px solid rgba(0,0,0,0.06);
            }
            QToolBar {
                spacing: 6px;
                padding: 4px;
            }
            """
        )

    def _apply_default_dock_sizes(self) -> None:
        """Apply sane first-launch dock sizes.

        Qt restores previous sizes via QSettings. If no state exists yet,
        we set reasonable defaults so the Inspector is usable immediately.
        """
        try:
            docks = [self._dock_lib, self._dock_ins]
            sizes = [260, 260]
            self.resizeDocks(docks, sizes, QtCore.Qt.Horizontal)
        except Exception:
            pass

    # --------------------
    # Project IO
    # --------------------
    def open_project(self, path: str) -> None:
        ir, ui = load_simproj(path, validate=True, normalize=True)
        self._current_path = str(Path(path).resolve())
        self._ir = ir
        self._ui_session = ui
        self.graph.load_from_project(ir=ir, ui_session=ui)
        self._settings.add_recent_file(self._current_path)
        self._update_title()
        self._update_status()

    def _sync_from_ui(self) -> None:
        self._ir, self._ui_session = self.graph.export_project()
        self._update_status()

    # --------------------
    # UI actions
    # --------------------
    def _build_actions(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        act_new = QtGui.QAction(_icon("add.svg"), "New", self)
        act_open = QtGui.QAction(_icon("open.svg"), "Open…", self)
        act_save = QtGui.QAction(_icon("save.svg"), "Save", self)
        act_save_as = QtGui.QAction("Save As…", self)
        act_quit = QtGui.QAction("Quit", self)

        act_new.triggered.connect(self._on_new)
        act_open.triggered.connect(self._on_open)
        act_save.triggered.connect(self._on_save)
        act_save_as.triggered.connect(self._on_save_as)
        act_quit.triggered.connect(self.close)

        file_menu.addActions([act_new, act_open, act_save, act_save_as])
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        edit_menu = menubar.addMenu("&Edit")

        act_delete = QtGui.QAction("Delete Selected", self)
        act_delete.setShortcut(QtGui.QKeySequence.Delete)
        act_delete.triggered.connect(self._on_delete_selected)
        self.addAction(act_delete)

        act_delete_bs = QtGui.QAction("Delete Selected", self)
        act_delete_bs.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Backspace))
        act_delete_bs.triggered.connect(self._on_delete_selected)
        self.addAction(act_delete_bs)

        act_set_in = QtGui.QAction("Set as Input", self)
        act_set_in.setShortcut(QtGui.QKeySequence("Ctrl+Shift+I"))
        act_set_in.triggered.connect(self._on_set_as_input)
        self.addAction(act_set_in)

        act_set_out = QtGui.QAction("Set as Output", self)
        act_set_out.setShortcut(QtGui.QKeySequence("Ctrl+Shift+O"))
        act_set_out.triggered.connect(self._on_set_as_output)
        self.addAction(act_set_out)

        edit_menu.addActions([act_delete, act_set_in, act_set_out])

        run_menu = menubar.addMenu("&Run")
        act_tf = QtGui.QAction(_icon("run.svg"), "Closed-loop TF", self)
        act_bode = QtGui.QAction(_icon("bode.svg"), "Bode", self)
        act_step = QtGui.QAction(_icon("step.svg"), "Step", self)
        act_pz = QtGui.QAction("Poles/Zeros", self)

        act_tf.triggered.connect(self._on_run_tf)
        act_bode.triggered.connect(self._on_run_bode)
        act_step.triggered.connect(self._on_run_step)
        act_pz.triggered.connect(self._on_run_pz)

        run_menu.addActions([act_tf, act_bode, act_step, act_pz])

        view_menu = menubar.addMenu("&View")
        act_plots = QtGui.QAction("Show Plots Window", self)
        act_plots.triggered.connect(self._ensure_plot_window)
        view_menu.addAction(act_plots)

        wire_menu = view_menu.addMenu("Wire Style")
        grp = QtGui.QActionGroup(self)
        grp.setExclusive(True)

        def add_wire_action(label: str, value: str):
            a = QtGui.QAction(label, self)
            a.setCheckable(True)
            a.setData(value)
            grp.addAction(a)
            wire_menu.addAction(a)
            a.triggered.connect(lambda checked, v=value: self._on_wire_style(v))
            return a

        a_curved = add_wire_action("Curved", "curved")
        a_straight = add_wire_action("Straight", "straight")
        a_angled = add_wire_action("Orthogonal (Square)", "angled")

        cur = self._settings.wire_style_name()
        {"curved": a_curved, "straight": a_straight, "angled": a_angled}.get(cur, a_angled).setChecked(True)

        tb = self.addToolBar("Main")
        tb.setObjectName("toolbar_main")
        tb.setMovable(False)
        tb.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        # Slightly bigger toolbar (requested)
        tb.setIconSize(QtCore.QSize(24, 24))
        tb.setStyleSheet("QToolButton { padding: 6px 10px; font-size: 13px; }")
        tb.setFixedHeight(44)

        tb.addAction(act_new)
        tb.addAction(act_open)
        tb.addAction(act_save)
        tb.addSeparator()
        tb.addAction(act_tf)
        tb.addAction(act_bode)
        tb.addAction(act_step)

    def _on_wire_style(self, style: str) -> None:
        try:
            self._settings.set_wire_style_name(style)
        except Exception:
            pass
        try:
            self.graph.set_wire_style(style)
        except Exception:
            pass

    def _restore_ui_state(self) -> bool:
        """Restore QSettings geometry/state. Returns True if a state was restored."""
        q = QtCore.QSettings()
        geo = q.value("ui/main_window_geometry")
        st = q.value("ui/main_window_state")
        restored = False
        if geo is not None:
            try:
                self.restoreGeometry(geo)
                restored = True
            except Exception:
                pass
        if st is not None:
            try:
                self.restoreState(st)
                restored = True
            except Exception:
                pass
        return restored

    def _persist_ui_state(self) -> None:
        q = QtCore.QSettings()
        q.setValue("ui/main_window_geometry", self.saveGeometry())
        q.setValue("ui/main_window_state", self.saveState())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self._persist_ui_state()
        super().closeEvent(event)

    def _update_title(self) -> None:
        if self._current_path:
            self.setWindowTitle(f"Simulator — {Path(self._current_path).name}")
        else:
            self.setWindowTitle("Simulator — Untitled")

    def _update_status(self) -> None:
        inp = self._ir.io_inputs[0] if self._ir.io_inputs else "∅"
        out = self._ir.io_outputs[0] if self._ir.io_outputs else "∅"
        self.statusBar().showMessage(f"Graph backend: {self.graph.backend_name}    IO: {out}/{inp}")

    # --------------------
    # Signals
    # --------------------
    def _on_add_block(self, block_type: str) -> None:
        try:
            self.graph.create_node(block_type, focus=True)
            self._sync_from_ui()
        except Exception as e:
            self._show_error("Add block failed", str(e))

    def _on_selection_changed(self, block_id: str | None) -> None:
        self._selected_block_id = block_id
        try:
            self._sync_from_ui()
        except Exception:
            pass

        if not block_id:
            self.inspector.clear()
            return

        blk = next((b for b in self._ir.blocks if b.id == block_id), None)
        if blk is None:
            self.inspector.clear()
            return
        self.inspector.set_block(blk)

    def _on_block_updated(self, block_id: str, new_params: dict) -> None:
        for b in self._ir.blocks:
            if b.id == block_id:
                b.params.update(new_params)
                break
        self.graph.update_block_params(block_id, new_params)
        blk = next((b for b in self._ir.blocks if b.id == block_id), None)
        if blk is not None:
            self.inspector.set_block(blk)

    def _on_ir_changed(self) -> None:
        if not self._sync_timer.isActive():
            self._sync_timer.start(35)

    # --------------------
    # Edit actions
    # --------------------
    def _on_delete_selected(self) -> None:
        g = self.graph.graph

        pipes = _as_list(_call_ok(g, "selected_pipes") and g.selected_pipes() or None)
        if not pipes:
            pipes = _as_list(_safe_selected(g, ["selected_connections", "selected_pipes"]))
        nodes = _as_list(_safe_selected(g, ["selected_nodes"]))

        if pipes:
            if not _call_ok(g, "delete_pipes", pipes):
                for p in list(pipes):
                    if not _call_ok(g, "delete_pipe", p):
                        _call_ok(g, "delete_connection", p)

        if nodes:
            if not _call_ok(g, "delete_nodes", nodes):
                model_nodes = None
                try:
                    model = getattr(g, "model", None)
                    model_nodes = getattr(model, "nodes", None) if model else None
                except Exception:
                    model_nodes = None

                for n in list(nodes):
                    try:
                        nid = getattr(n, "id", None)
                        nid = nid() if callable(nid) else nid
                        if isinstance(model_nodes, dict) and nid is not None and nid not in model_nodes:
                            continue
                        _call_ok(g, "delete_node", n)
                    except Exception:
                        continue

        _call_ok(g, "clear_selection")
        self._selected_block_id = None
        self.inspector.clear()
        self._sync_from_ui()

    def _on_set_as_input(self) -> None:
        if not self._selected_block_id:
            return
        self._sync_from_ui()
        blk = next((b for b in self._ir.blocks if b.id == self._selected_block_id), None)
        if blk is None or not blk.outputs:
            self._show_error("Set Input", "Select a block with an output port.")
            return
        self._ir.io_inputs = [f"{blk.id}.{blk.outputs[0].name}"]
        self._update_status()

    def _on_set_as_output(self) -> None:
        if not self._selected_block_id:
            return
        self._sync_from_ui()
        blk = next((b for b in self._ir.blocks if b.id == self._selected_block_id), None)
        if blk is None:
            return

        if blk.type == "scope" and blk.inputs:
            target = f"{blk.id}.{blk.inputs[0].name}"
            for w in self._ir.wires:
                if w.dst == target:
                    self._ir.io_outputs = [w.src]
                    self._update_status()
                    return
            self._show_error("Set Output", "Scope input is not connected.")
            return

        if blk.outputs:
            self._ir.io_outputs = [f"{blk.id}.{blk.outputs[0].name}"]
            self._update_status()
            return

        self._show_error("Set Output", "Select a block with an output port (or a wired Scope).")

    # --------------------
    # File actions
    # --------------------
    def _on_new(self) -> None:
        self._current_path = None
        self._ir = ProjectIR()
        self._ui_session = {}
        self.graph.new_project()
        self._update_title()
        self._update_status()

    def _on_open(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Project", "", "Simulator Project (*.simproj)")
        if not path:
            return
        self.open_project(path)

    def _on_save(self) -> None:
        self._sync_from_ui()
        if not self._current_path:
            return self._on_save_as()
        save_simproj(self._current_path, ir=self._ir, ui_session=self._ui_session, validate=True, normalize=True)
        self._settings.add_recent_file(self._current_path)
        self._update_title()

    def _on_save_as(self) -> None:
        self._sync_from_ui()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Project As", "", "Simulator Project (*.simproj)")
        if not path:
            return
        if not path.endswith(".simproj"):
            path += ".simproj"
        self._current_path = path
        self._on_save()

    # --------------------
    # Plot window
    # --------------------
    def _ensure_plot_window(self) -> PlotWindow:
        if self._plot_win is None:
            self._plot_win = PlotWindow(parent=self)
        self._plot_win.show()
        self._plot_win.raise_()
        self._plot_win.activateWindow()
        return self._plot_win

    # --------------------
    # Run actions
    # --------------------
    def _on_run_tf(self) -> None:
        try:
            self._sync_from_ui()
            res = control_engine.closed_loop_tf(self._ir)
            win = self._ensure_plot_window()
            win.host.show_tf(res.tf, title=f"TF: {res.output_label}/{res.input_label}")
        except Exception as e:
            self._show_error("Closed-loop TF failed", str(e))

    def _on_run_bode(self) -> None:
        try:
            self._sync_from_ui()
            res = control_engine.bode(self._ir)
            win = self._ensure_plot_window()
            win.host.show_bode(res.omega, res.mag, res.phase)
        except Exception as e:
            self._show_error("Bode failed", str(e))

    def _on_run_step(self) -> None:
        try:
            self._sync_from_ui()
            res = control_engine.step(self._ir)
            win = self._ensure_plot_window()
            win.host.show_step(res.t, res.y)
        except Exception as e:
            self._show_error("Step failed", str(e))

    def _on_run_pz(self) -> None:
        try:
            self._sync_from_ui()
            res = control_engine.poles_zeros(self._ir)
            win = self._ensure_plot_window()
            win.host.show_pz(res.poles, res.zeros)
        except Exception as e:
            self._show_error("Poles/Zeros failed", str(e))

    def _show_error(self, title: str, msg: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, msg)


def _safe_selected(g: Any, names: list[str]) -> Any:
    for n in names:
        try:
            v = getattr(g, n, None)
            if callable(v):
                return v()
        except Exception:
            continue
    return None
