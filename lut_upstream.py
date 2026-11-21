"""
Locate and import the UNMODIFIED upstream Lower Urinary Tract model.

Upstream: MoveR-Digital-Health-and-Care-Hub/lower-urinary-tract-sim, tag v1.3.0
(commit bd8f2a0), MIT licence. Lister et al. 2025, R Soc Open Sci 12:242062,
doi:10.1098/rsos.242062. The clone lives in third_party/lut-sim and is never edited.

Why this module exists: the upstream package is called `model`, so our own code
must not create a package with that name. Everything in Project Cue imports the
upstream model through `load_upstream()` instead.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
UPSTREAM_DIR = PROJECT_ROOT / "third_party" / "lut-sim"
UPSTREAM_COMMIT = "bd8f2a072ef017b99dc051b24972333141f7d257"

# Unit conversions, written out explicitly (the upstream code uses the same factors).
M3_PER_ML = 1e-6            # 1 mL = 1e-6 m^3
PA_PER_CMH2O = 98.0665      # 1 cmH2O = 98.0665 Pa (standard gravity, water at 4 C)


def load_upstream():
    """Return the upstream `LUT_Model` module, importing it from third_party/lut-sim."""
    if not (UPSTREAM_DIR / "model" / "LUT_Model.py").exists():
        raise FileNotFoundError(f"Upstream model not found in {UPSTREAM_DIR}")
    if str(UPSTREAM_DIR) not in sys.path:
        sys.path.insert(0, str(UPSTREAM_DIR))
    from model import LUT_Model  # the README's own import line
    return LUT_Model
