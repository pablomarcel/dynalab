# DynaLab

**DynaLab** is a Python desktop app for building and analyzing block-diagram control systems with a graphical canvas, editable block parameters, and classical control analysis tools.

It is aimed at the workflow many engineers actually want:

- drop blocks onto a diagram
- wire up a feedback loop
- edit gains and transfer functions directly in the UI
- compute the closed-loop transfer function
- inspect Bode and step response plots without leaving the app

In spirit, it is a lightweight **Simulink-style desktop workbench** built with **PySide6**, **NodeGraphQt**, and **python-control**.

---

## Why this project exists

A lot of Python control tooling is powerful, but heavily script-driven. That is great for notebooks and batch workflows, but not always ideal when you want to:

- sketch a loop visually
- tune blocks interactively
- inspect responses immediately
- use a diagram-first workflow instead of a code-first workflow

DynaLab was built to close that gap with a Python-native desktop UI for classical control work.

---

## Current capabilities

### Block-diagram canvas

The app provides a desktop graph editor where you can:

- drag and drop blocks from a block library
- connect blocks visually
- create standard feedback control diagrams
- delete blocks and reconnect the model quickly

### Editable block parameters

Selecting a block opens its parameters in the inspector panel, where you can edit values directly.

Examples:

- **Gain** block: change `k`
- **Transfer Function** block: edit numerator and denominator coefficients
- **Sum** block: define sign pattern such as `[+1, -1]`
- **Delay** block: configure discrete-domain timing values
- **Source blocks**: set step magnitude, impulse parameters, or constant values

### Built-in analysis tools

From the UI, the current app can compute and display:

- **Closed-loop transfer function**
- **Bode plot**
- **Step response**
- **Poles and zeros**

### Project persistence

DynaLab supports project save/load using a `.simproj` file format so diagrams and analysis setups can be reopened later.

---

## Supported block library

### Sources

- Step
- Impulse
- Constant

### LTI blocks

- Transfer Function (TF)
- Gain
- Sum
- Delay (`z^-1`)

### Sinks

- Scope
- Terminator

---

## Screens the app includes

The current application layout centers around three main work areas:

- **Canvas** for block-diagram construction
- **Library dock** for block insertion
- **Inspector dock** for parameter editing

Analysis results are shown in a separate plot window.

---

## Example workflow

A typical workflow looks like this:

1. Launch the app.
2. Drag a **Step** source, **Sum** block, **Transfer Function** block, **Gain** block, and **Scope** onto the canvas.
3. Connect the blocks into a standard negative-feedback loop.
4. Click each block and set parameters in the inspector.
5. Run:
   - **Closed-loop TF**
   - **Bode**
   - **Step**
6. Inspect the resulting plots and transfer function display.

That gives you a visual control-diagram workflow without having to assemble the entire model manually in Python code.

---

## Technology stack

DynaLab is currently built around:

- **Python**
- **PySide6** for the desktop shell
- **NodeGraphQt** for the node-based block-diagram canvas
- **python-control** for classical control analysis
- **NumPy** and **Matplotlib** for numeric work and plotting

---

## Installation

Create and activate a virtual environment, then install the required packages.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install PySide6 NodeGraphQt control numpy matplotlib
```

Depending on your platform and environment, you may also want `scipy` installed because some control-related workflows commonly depend on it:

```bash
pip install scipy
```

---

## Running the app

From the project root:

```bash
python -m simulator
```

To clear saved UI settings and start fresh:

```bash
python -m simulator --reset-settings
```

---

## Project structure

A simplified view of the architecture:

```text
simulator/
  app.py
  settings.py
  log.py

  core/
    ir/
    project/
    signals/

  blocks/
    lti/
    sources/
    sinks/

  compilers/
    control_compiler.py
    pathsim_compiler.py
    bdsim_compiler.py

  engines/
    control_engine.py
    sim_engine.py

  ui/
    main_window.py
    graph/
    inspector/
    plots/
    nodes/
```

### Architectural idea

The app is intentionally separated into layers:

- **UI layer**: canvas, inspector, menus, plots
- **IR layer**: semantic project representation for blocks, ports, and wires
- **Compiler layer**: turns the diagram into analysis-ready models
- **Engine layer**: runs control analysis and returns structured results

This architecture is meant to keep the graphical editor from becoming tightly coupled to any one solver backend.

---

## Design philosophy

DynaLab is being built with a few practical goals in mind:

- **diagram-first workflow** instead of script-first workflow
- **Python-native control tooling** rather than a black-box desktop stack
- **editable semantic model** underneath the UI
- **extensible backend architecture** so new analysis engines can be integrated later
- **incremental evolution** from classical control analysis toward broader simulation workflows

---

## What is working well already

At this stage, the project already demonstrates a lot of real functionality:

- the UI launches cleanly
- blocks can be placed on the graph canvas
- feedback diagrams can be constructed visually
- the inspector can edit block parameters
- transfer function, Bode, step, and pole/zero analysis are working
- projects can be persisted and reopened

This is not just a mock UI. It is already a usable early desktop control-analysis tool.

---

## Current limitations

This project is still in an early release stage, so some limitations remain.

Examples of current scope boundaries:

- the block library is intentionally small
- the current analysis focus is classical LTI/control workflows
- advanced simulation backends are still evolving
- diagram ergonomics and visual polish are still being improved
- some backend/library compatibility can depend on the local Python environment

---

## Roadmap direction

Planned or natural next-step upgrades include:

- richer block library
- better visual routing and diagram polish
- stronger project/session behavior
- explicit input/output selection from the canvas
- improved simulation backend integration
- broader discrete-time and hybrid workflows
- more robust scope and signal-inspection tools
- packaging into a friendlier distributable desktop release

---

## Why this is interesting

DynaLab sits at an interesting intersection:

- **control engineering**
- **scientific Python**
- **desktop UI development**
- **diagram-driven modeling**

It is useful both as:

- a practical control-systems desktop tool
- and an engineering software architecture project

---

## Development notes

The project has been iterated heavily around a few non-negotiable behaviors:

- blocks must be visually editable
- feedback loops must be supported
- graph connections must export correctly into the semantic IR
- the UI must remain responsive while analysis remains grounded in real control tooling

A lot of effort has gone into making the graph canvas, inspector, and control-analysis path work together cleanly.

---

## Who this is for

DynaLab should be interesting to:

- control engineers
- students studying feedback systems
- Python developers building engineering tools
- anyone curious about a Python-native alternative to diagram-based control analysis workflows

---

## Status

**Current release stage:** early alpha / first usable desktop release.

The app is already capable of meaningful control-diagram construction and analysis, but it is still actively evolving.

---

## License

See [`LICENSE`](LICENSE).
