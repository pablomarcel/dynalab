# Running the `machines/simulator` desktop app

This project is a **PySide6 desktop app** with a node-graph editor + a python-control backend.

## 0) Prereqs

You need:

- Python 3.10+ (3.11/3.12 recommended)
- A virtual environment (venv/conda)
- Qt bindings: **PySide6**
- Plotting: **matplotlib**
- Control math: **python-control** + **numpy**
- Node editor: **OdenGraphQt** (preferred) or **NodeGraphQt**

> If you only install one node-graph package, install **OdenGraphQt** (PySide6-friendly fork).

---

## 1) Create + activate a venv

From the **`machines/simulator/`** folder:

```bash
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate    # Windows PowerShell
```

Upgrade tooling:

```bash
python -m pip install -U pip wheel setuptools
```

---

## 2) Install the package (editable)

From **`machines/simulator/`**:

```bash
python -m pip install -e .
```

If your `pyproject.toml` does not already declare these, also install:

```bash
python -m pip install PySide6 matplotlib numpy control
python -m pip install OdenGraphQt || python -m pip install NodeGraphQt
```

---

## 3) Run the app (3 equivalent ways)

### A) Recommended: module entrypoint

From **`machines/simulator/`**:

```bash
python -m simulator
```

### B) Direct app launcher

```bash
python -m simulator.app
```

(or)

```bash
python simulator/app.py
```

### C) Dev convenience launcher (with demos)

```bash
python scripts/dev_run.py --demo unity
python scripts/dev_run.py --demo nested
```

Open a specific project:

```bash
python scripts/dev_run.py --file simulator/in/demos/unity_feedback.simproj
```

---

## 4) Quick smoke tests (no UI)

### Build + compile a demo IR and print the closed-loop TF

```bash
python -m simulator.sandbox.demo_build_ir
```

### Launch UI with a demo loaded (no file IO)

```bash
python -m simulator.sandbox.quickstart
```

---

## Common issues

### “Cannot import a node-graph framework…”
Install one of these:

```bash
python -m pip install OdenGraphQt
# or
python -m pip install NodeGraphQt
```

### Matplotlib backend issues
Ensure you have the Qt backend installed (PySide6) and try:

```bash
python -c "import matplotlib; print(matplotlib.get_backend())"
```

The app uses `matplotlib.backends.backend_qtagg`, which is correct for Qt6.

### macOS: Qt permission / Gatekeeper weirdness
If the app launches but shows empty windows, try running from Terminal (so you can see stdout/stderr), and ensure your venv is active.

---

## Where to find demos

- `simulator/in/demos/unity_feedback.simproj`
- `simulator/in/demos/nested_loops.simproj`

---

## What “Run → Closed-loop TF / Bode / Step” expects

For MVP LTI analysis via python-control, you must have:

- A valid diagram (all required inputs connected)
- `ProjectIR.io_inputs` and `ProjectIR.io_outputs` set

The demo `.simproj` files already set these.
In the UI, IO-selection persistence is not fully implemented yet — so if you draw a diagram from scratch, you may need to open/edit a demo first or set IO selection in a future UI step.
