"""
The physiology used by Project Cue: the upstream LUT model, extended by SUBCLASSING.

The upstream code is never edited. `CueLUT` inherits everything from upstream `LUT`
and replaces only three small methods. The upstream simulation loop
(`process_neural_input`) runs exactly as written.

What the simplified SCI condition changes (all ASSUMED, see config.SCI)
-----------------------------------------------------------------------
DISABLED  Sensation reaching the brain and the decision to void.
          Upstream: `is_voiding()` starts a void when detrusor pressure reaches
          54.7 cmH2O or volume reaches 500 mL. Under SCI it always returns False.
DISABLED  The descending, coordinated voiding program (detrusor drive 0.6,
          no sympathetic inhibition, sphincter drive 0.1). Upstream only uses these
          values while voiding, so with no void they are never applied.
REMAINS   The storage-phase neural drives, which depend on volume (Gaussians of
          fullness) and urethral opening. We treat them as the spinal reflexes below a
          suprasacral injury. This is our reinterpretation: the paper calls them
          signals "from the brain", and the model has no separate reflex arc.
REMAINS   All mechanics (detrusor wall, sphincter, urethral flow) and the kidney.
          Filling continues. If bladder pressure exceeds sphincter closure pressure,
          the mechanics open the urethra and urine leaks. That leak is a MODEL
          PREDICTION, not a validated SCI behaviour.

Volume ceiling
--------------
Upstream clips volume at `bladder_args['max_V_B']` (500 mL) and ALSO uses that
number to compute fullness inside the neural drives. We separate the two roles:
  * `max_V_B` is set to the (ASSUMED) volume ceiling, so the clip moves up;
  * while a neural drive is computed, `max_V_B` is temporarily put back to the
    fullness reference (500 mL), so the drive is exactly the upstream one.
Above 500 mL the drives are extrapolated beyond the range they were designed for.

Units: everything inside the model is SI (m^3, m^3/s, Pa, s). `simulate()` adds
columns converted with explicit factors; the converted columns carry the unit in
their names (V_B_ml, p_D_cmH2O ...).
"""
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lut_upstream import load_upstream, M3_PER_ML, PA_PER_CMH2O  # noqa: E402

LUT_Model = load_upstream()


class CueLUT(LUT_Model.LUT):
    """Upstream LUT plus the simplified SCI condition and a separate volume ceiling."""

    def __init__(self, sci_enabled=True, fullness_reference_ml=500.0, volume_ceiling_ml=500.0,
                 initial_volume_ml=0.0, overrides=None, drive_above_reference="extrapolate"):
        super().__init__()
        for key, val in (overrides or {}).items():
            group, name = key.split(".")
            table = getattr(self, group)          # bladder_args, kidney_args or neural_args
            if name not in table:
                raise KeyError(f"{key} is not an upstream parameter")
            table[name] = val
        if drive_above_reference not in ("extrapolate", "hold"):
            raise ValueError("drive_above_reference must be 'extrapolate' or 'hold'")
        self.sci_enabled = sci_enabled
        self.drive_above_reference = drive_above_reference
        self.fullness_reference_m3 = fullness_reference_ml * M3_PER_ML
        self.bladder_args["max_V_B"] = volume_ceiling_ml * M3_PER_ML   # the upstream clip value
        self.V_B = initial_volume_ml * M3_PER_ML

    @contextmanager
    def _upstream_fullness_scale(self):
        """Temporarily restore max_V_B so upstream computes fullness = V_B / 500 mL.

        'extrapolate': fullness can exceed 1, so the upstream Gaussians are evaluated
                       beyond the range they were designed for (their peaks sit at or
                       below full, so the drive FALLS as the bladder over-fills).
        'hold':        fullness is capped at 1 (= min(V_B / 500 mL, 1)), so above 500 mL
                       the drive stays at its value at 500 mL. Equally unsourced.
        """
        ceiling = self.bladder_args["max_V_B"]
        reference = self.fullness_reference_m3
        if self.drive_above_reference == "hold":
            reference = max(reference, self.V_B)
        self.bladder_args["max_V_B"] = reference
        try:
            yield
        finally:
            self.bladder_args["max_V_B"] = ceiling

    def update_parasympathetic_input(self):
        with self._upstream_fullness_scale():
            return super().update_parasympathetic_input()

    def update_sympathetic_input(self):
        with self._upstream_fullness_scale():
            return super().update_sympathetic_input()

    def is_voiding(self):
        if self.sci_enabled:
            return False   # no sensation-driven, voluntary void and no coordinated program
        return super().is_voiding()


def simulate(model, duration_s, dt_s, seed, noise):
    """Run the unmodified upstream loop on `model`; return SI columns plus converted ones."""
    data = model.process_neural_input(duration_s, dt_s, noise=noise, seed=seed)  # SI output
    data["V_B_ml"] = data["V_B"] / M3_PER_ML
    data["Q_ml_s"] = data["Q"] / M3_PER_ML
    data["Q_in_ml_s"] = data["Q_in"] / M3_PER_ML
    data["p_D_cmH2O"] = data["p_D"] / PA_PER_CMH2O
    data["p_S_cmH2O"] = data["p_S"] / PA_PER_CMH2O
    data["r_U_mm"] = data["r_U"] * 1000.0
    return data


def model_from_config(cfg, sci_enabled=None, volume_ceiling_ml=None):
    """Build a CueLUT from config.py (arguments override the config, for sweeps)."""
    sci = cfg.SCI
    return CueLUT(
        sci_enabled=cfg.value(sci, "enabled") if sci_enabled is None else sci_enabled,
        fullness_reference_ml=cfg.value(sci, "fullness_reference_ml"),
        volume_ceiling_ml=cfg.value(sci, "volume_ceiling_ml") if volume_ceiling_ml is None else volume_ceiling_ml,
        initial_volume_ml=cfg.value(cfg.SIMULATION, "initial_volume_ml"),
        overrides=cfg.PHYSIOLOGY_OVERRIDES,
        drive_above_reference=cfg.value(sci, "drive_above_reference"),
    )
