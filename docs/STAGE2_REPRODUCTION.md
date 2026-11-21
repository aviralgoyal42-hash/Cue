# Project Cue: Stage 2, reproducing the upstream simulator (unmodified)

Date: 2026-11-03. Upstream: lower-urinary-tract-sim v1.3.0, commit `bd8f2a0`. The upstream code was not edited. A test checks this with `git status`.

Environment: Python 3.12.10, numpy 2.3.1, scipy 1.15.2, pandas 2.2.3, matplotlib 3.10.0 (the upstream pins). The environment lives in `%USERPROFILE%\.venvs\project-cue`.

## What was reproduced

| Check | Upstream reference (saved notebook output) | Our run | Result |
|---|---|---|---|
| Figure 2 run: 1 day, dT 0.1 s, seed 42. First 5 and last 5 rows, all 13 columns. | `figures.ipynb` cell 4, printed to 6 decimals | Largest difference 4.9 × 10⁻⁷. The pass tolerance is 5 × 10⁻⁷, which is half of the last printed digit. | **Match** |
| Sensitivity-analysis baseline: 5 days, dT 0.1 s, seed 42 | `figures.ipynb` cell 18: 6.04 h, 489.56 mL, 489.56 mL | 6.04 h, 489.56 mL, 489.56 mL | **Match** |
| Paper text (R Soc Open Sci 2025) | Max flow 21.1 mL/s. Capacity 489.58 mL. Void duration 27.1 s (§3.1) or 27.3 ± 0.05 s (§3.3). | Peak flow 21.11 mL/s. Capacity 489.54–489.59 mL. Void duration **26.6–26.7 s**. | Flow and capacity match. Void duration is about 0.5 s shorter than the paper states. The paper does not give the dT or seed used for that number, so this is noted but not treated as an error. |

Runtime: about 45 s per simulated day at dT 0.1 s, so the 5-day run took 238 s.

How to rerun:
```
python experiments/stage2_reproduce_upstream.py --baseline5d
python experiments/stage2_upstream_diagnostics.py
python -m pytest                     # quick tests
set CUE_RUN_SLOW=1 && python -m pytest   # also the full-day reproduction (~35 s)
```

Outputs in `results/stage2/`:
- `figure2_reproduction.png`: volume, pressure and neural drive against time.
- `figure2_run_1day_1Hz.csv`: the run, saved once per second.
- `figure2_row_check.csv`: differences from the printed notebook rows.
- `stage2_report.json`: summary numbers.
- `stage2_run_log.txt`: console output.

## What the baseline (healthy) model does

These are model outputs, not physiological facts.

- **Voiding.** Every void starts when detrusor pressure reaches the 54.7 cmH₂O trigger, at **489.5–489.6 mL every time**. Inflow noise changes *when* the void happens but not the volume. Voids are spaced 5.3–7.2 h apart, with a 5-day mean of 6.04 h.
- **Emptying.** Every void empties the bladder to 0.0 mL in about 26.7 s. So **post-void residual is always zero**, by construction (see Stage 1 §3).
- **Storage.** During storage the sphincter closure pressure stays at **59.08 cmH₂O** (ω\*s = 0.5). This confirms the Stage 1 estimate of about 59 cmH₂O. The closure pressure is only about 4 cmH₂O above the void trigger. That matters for Stage 3: if the void trigger is removed, the detrusor pressure may rise past this closure pressure.

## Stage 1 predictions checked

| Stage 1 prediction | Result |
|---|---|
| Inflow noise raises the mean because negative values are set to zero | **Confirmed.** Mean inflow is 0.0170 mL/s at noise 0, 0.0178 mL/s at noise 0.5 and **0.0227 mL/s at noise 1** (1.36 mL/min). At noise 1, inflow is zero 34.7% of the time. |
| Noise is redrawn only when `t % 60 == 0` holds exactly | **Confirmed.** Noise is redrawn every 60 s for dT of 0.05, 0.1, 0.2, 0.25, 0.3 and 1.0 s. For dT = 0.7 s it is redrawn only every 420 s. |
| Misspelt unit strings are silently ignored | **Confirmed by test.** `V_unit='mL'` and `p_unit='cmh2o'` give SI output. |

## New finding: time-step limit (numerical stability)

The sphincter activation equation, τ_S·df/dt = ω − f with τ_S = 0.2 s, is integrated with forward Euler. Each step multiplies the error by (1 − dT/τ_S). In plain words: a time step that is too large makes each correction overshoot by more than it fixes, so the error grows step by step instead of shrinking.

| dT | Behaviour over 10 simulated minutes |
|---|---|
| 0.1 s | Smooth, no overshoot |
| 0.2 s | Reaches its target in exactly one step |
| 0.3 s, 0.39 s | Stable but oscillates. f\*aS reaches 0.75 and 0.975, above its 0.5 target. |
| ≥ 0.41 s | **Diverges.** Values reach about 10³⁰ and beyond, then become infinite or NaN. |

**Rule for the Cue framework:** the configuration will reject dT ≥ 0.4 s and warn for dT > 0.2 s. We will use dT = 0.1 s, the upstream default, unless there is a reason to change it. The paper makes no statement about step size.

## Tests added (`tests/test_stage2_upstream.py`)

8 quick tests pass and the 1 slow test passes when enabled:
- The upstream clone is pinned and unmodified.
- The first rows match the notebook.
- Results are reproducible with a fixed seed, and different seeds give different results.
- Explicit unit factors (1 mL = 10⁻⁶ m³, 1 cmH₂O = 98.0665 Pa) match the upstream conversion.
- The misspelt-unit pitfall is documented.
- dT = 0.1 s is stable and dT = 0.5 s diverges.
- The full-day reproduction matches (slow test).

## Problems and notes

- `matplotlib 3.10.0` triggers deprecation warnings from the newer `pyparsing`. They are harmless and are filtered in `pytest.ini`.
- Windows' 260-character path limit applies. Python could not run a script from the app's temporary folder, so all scripts live inside `project-cue/`.
- Naming rule: the upstream package is called `model`. **Our code must not create a `model/` package**, or the two would clash. We import upstream through `lut_upstream.load_upstream()`. The physiology wrapper will be named `cue_model/` or similar rather than the suggested `model/`.

## Ready for Stage 3?

Yes, technically. The remaining blockers are the scientific decisions from Stage 1 §10:
1. what to do with the storage reflex drives under SCI;
2. what to use instead of the 500 mL clamp;
3. where the pressure-ceiling signal comes from.
