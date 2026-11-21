"""
STAGE 2 diagnostics: check two behaviours of the unmodified upstream kidney model
that Stage 1 predicted by reading the code.

1. Noise redraw: upstream draws new inflow noise only when `t % 60 == 0` holds
   exactly in floating point. We count the draws in one simulated hour for several
   time steps (60 draws expected).
2. Noise bias: inflow below zero is set to zero, so noise should RAISE the mean
   inflow above the noise-free value (about 0.017 mL/s). We measure the mean over
   one simulated day for several noise levels.

Usage:  python experiments/stage2_upstream_diagnostics.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lut_upstream import load_upstream, M3_PER_ML  # noqa: E402

LUT_Model = load_upstream()


def count_noise_draws(dT, max_time_s=3600, seed=1):
    """Run the model and count calls to np.random.uniform (one per noise redraw)."""
    lut = LUT_Model.LUT()
    draws = []
    original = np.random.uniform

    def counting_uniform(*args, **kwargs):
        draws.append(lut.t)
        return original(*args, **kwargs)

    np.random.uniform = counting_uniform  # upstream calls np.random.uniform at run time
    try:
        lut.process_neural_input(max_time_s, dT, seed=seed)
    finally:
        np.random.uniform = original
    return draws


def main():
    print("1. Inflow-noise redraws in 1 simulated hour (60 expected)")
    for dT in [0.05, 0.1, 0.2, 0.25, 0.3, 0.7, 1.0]:
        draws = count_noise_draws(dT)
        print(f"   dT = {dT:<4} s: {len(draws):3d} draws; first at t = {[round(t, 1) for t in draws[:3]]}")

    print("2. Mean inflow over 1 simulated day (noise-free mean of the sine term: 0.017 mL/s)")
    for noise in [0.0, 0.5, 1.0]:
        data = LUT_Model.LUT().process_neural_input(24 * 3600, 0.1, noise=noise, seed=42)
        q_ml = data["Q_in"] / M3_PER_ML
        print(f"   noise = {noise}: mean {q_ml.mean():.5f} mL/s ({q_ml.mean() * 60:.3f} mL/min); "
              f"share of time with zero inflow {np.mean(q_ml == 0):.1%}")

    print("3. Time-step stability (10 simulated minutes from empty)")
    # Forward Euler on tau_S * df/dt = w - f multiplies the error by (1 - dT/tau_S) each
    # step. With tau_S = 0.2 s this shrinks only if dT < 2 * tau_S = 0.4 s, and it stops
    # alternating in sign only if dT <= tau_S = 0.2 s.
    for dT in [0.1, 0.2, 0.3, 0.39, 0.41, 0.5, 0.7, 1.0]:
        with np.errstate(all="ignore"):
            data = LUT_Model.LUT().process_neural_input(600, dT, seed=1)
        f_aS = data["f_aS_s"].to_numpy()
        finite = np.isfinite(f_aS).all() and np.isfinite(data["V_B"]).all()
        overshoot = np.nanmax(f_aS) > 0.5 + 1e-9  # storage target is omega_s* = 0.5
        print(f"   dT = {dT:<4} s: finite = {finite}, f_aS range "
              f"[{np.nanmin(f_aS):.3g}, {np.nanmax(f_aS):.3g}], overshoots 0.5: {overshoot}")


if __name__ == "__main__":
    main()
