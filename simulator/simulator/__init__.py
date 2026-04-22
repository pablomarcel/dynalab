# --- compat alias ---------------------------------------------------------
# Allow legacy imports like `simulator.simulator.blocks...` to work even though
# the real package root is just `simulator/`.
import sys as _sys

_this_pkg = _sys.modules[__name__]
_sys.modules.setdefault(__name__ + ".simulator", _this_pkg)
setattr(_this_pkg, "simulator", _this_pkg)
# -------------------------------------------------------------------------