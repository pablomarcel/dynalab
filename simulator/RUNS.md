# RUNS.md — simulator

## -1) One-time session bootstrap (simulator-aware)

```bash
# --- run-from-root helpers (simulator-aware) ------------------------------
_simulator_root() {
  local d="$PWD"
  while [ "$d" != "/" ]; do
    # project root is the folder that contains:
    #   - pyproject.toml
    #   - simulator/__init__.py
    if [ -f "$d/pyproject.toml" ] && [ -f "$d/simulator/__init__.py" ]; then
      echo "$d"; return
    fi
    d="$(dirname "$d")"
  done
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return
  fi
  echo "$PWD"
}
runroot() { ( cd "$(_simulator_root)" && "$@" ); }

# ensure standard folders exist
runroot mkdir -p simulator/out simulator/in simulator/in/demos
```

---

## 0) Launch the desktop app

### A) Primary entrypoint (recommended)

```bash
runroot python -m simulator
```

```bash
runroot python -m simulator --reset-settings
```

### B) Explicit UI launcher module

```bash
runroot python -m simulator.app
```

### C) Dev convenience launcher (same UI, extra flags)

```bash
runroot python scripts/dev_run.py
```

---

## 1) Launch with included demos

### Unity feedback demo

```bash
runroot python scripts/dev_run.py --demo unity
# or:
runroot python scripts/dev_run.py --file simulator/in/demos/unity_feedback.simproj
```

### Nested loops demo

```bash
runroot python scripts/dev_run.py --demo nested
# or:
runroot python scripts/dev_run.py --file simulator/in/demos/nested_loops.simproj
```

---

## 2) Sandbox entrypoints

### UI quickstart (loads an in-memory demo IR)

```bash
runroot python -m simulator.sandbox.quickstart
```

### Compiler/engine smoke test (no UI)

```bash
runroot python -m simulator.sandbox.demo_build_ir
```

---

## 3) Build an executable (optional)

```bash
runroot python scripts/build_exe.py --name Simulator
# onefile build (harder to get right):
runroot python scripts/build_exe.py --name Simulator --onefile
```
