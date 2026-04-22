"""simulator.engines.control_engine

High-level LTI analysis functions using python-control.

This engine:
- compiles ProjectIR -> interconnected model (control_compiler)
- computes transfer functions, poles/zeros, bode, step, margins
- returns structured results for UI

Notes:
- For MVP, TF and margins assume SISO (1 selected input and 1 selected output).
- Bode computation uses control.frequency_response() to avoid the bode() / bode_plot()
  return-value deprecation warnings in newer python-control versions.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import control

from simulator.simulator.compilers.control_compiler import CompiledControlModel, compile_to_control
from simulator.simulator.core.ir.types import ProjectIR
from .results import BodeResult, MarginsResult, PolesZerosResult, StepResult, TFResult


class ControlEngineError(RuntimeError):
    pass


def compile(ir: ProjectIR) -> CompiledControlModel:
    return compile_to_control(ir)


def closed_loop_tf(ir: ProjectIR) -> TFResult:
    """Return closed-loop transfer function between the selected I/O.

    For MVP, assumes 1 input and 1 output.
    """
    cm = compile(ir)
    if len(cm.inputs) != 1 or len(cm.outputs) != 1:
        raise ControlEngineError("TF output requires exactly 1 selected input and 1 selected output (SISO).")

    sys = cm.system
    try:
        tf = control.tf(sys)
    except Exception as e:
        raise ControlEngineError(f"Failed to convert interconnected system to TF: {e}")

    return TFResult(tf=tf, input_label=cm.inputs[0], output_label=cm.outputs[0])


def poles_zeros(ir: ProjectIR) -> PolesZerosResult:
    cm = compile(ir)
    sys = cm.system
    try:
        p = control.poles(sys)
        z = control.zeros(sys)
    except Exception as e:
        raise ControlEngineError(f"Failed to compute poles/zeros: {e}")
    return PolesZerosResult(poles=np.asarray(p), zeros=np.asarray(z))


def bode(ir: ProjectIR, *, omega: Optional[np.ndarray] = None) -> BodeResult:
    """Compute bode magnitude/phase arrays.

    Uses python-control frequency_response() to avoid deprecation warnings around bode().
    Returns:
      omega: rad/s
      mag:   linear magnitude |G(jw)|
      phase: radians
    """
    cm = compile(ir)
    sys = cm.system

    # Default omega grid if not provided
    if omega is None:
        omega = np.logspace(-1, 2, 200)  # 0.1 .. 100 rad/s

    try:
        resp = control.frequency_response(sys, omega)
        mag, phase, omega_out = resp  # mag: |G|, phase: rad, omega: rad/s
    except Exception as e:
        raise ControlEngineError(f"Failed to compute frequency response: {e}")

    # Squeeze to 1D for UI (MVP SISO)
    omega_arr = np.squeeze(np.asarray(omega_out, dtype=float))
    mag_arr = np.squeeze(np.asarray(mag, dtype=float))
    phase_arr = np.squeeze(np.asarray(phase, dtype=float))

    return BodeResult(omega=omega_arr, mag=mag_arr, phase=phase_arr)


def step(ir: ProjectIR, *, T: Optional[np.ndarray] = None) -> StepResult:
    cm = compile(ir)
    sys = cm.system
    try:
        t, y = control.step_response(sys, T=T)
    except Exception as e:
        raise ControlEngineError(f"Failed to compute step response: {e}")
    return StepResult(t=np.asarray(t), y=np.asarray(y))


def margins(ir: ProjectIR) -> MarginsResult:
    """Gain/phase margins.

    Note: margins typically expects SISO.
    """
    cm = compile(ir)
    if len(cm.inputs) != 1 or len(cm.outputs) != 1:
        raise ControlEngineError("Margins require exactly 1 input and 1 output selected (SISO).")

    tfres = closed_loop_tf(ir)
    try:
        gm, pm, sm, wg, wp, ws = control.stability_margins(tfres.tf, returnall=False)
    except Exception as e:
        raise ControlEngineError(f"Failed to compute stability margins: {e}")

    return MarginsResult(gm=float(gm), pm=float(pm), sm=float(sm), wg=float(wg), wp=float(wp), ws=float(ws))
