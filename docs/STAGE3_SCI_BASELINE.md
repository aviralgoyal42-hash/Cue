# Project Cue: Stage 3, SCI condition and baseline (Experiment 1: no Cue)

Date: 2026-11-04. All numbers are model predictions under the assumptions in `config.py`. The assumption table is in `VALIDATION_AND_LIMITATIONS.md` §2–3.

## How the SCI condition is implemented

`cue_model/sci_lut.py` defines `CueLUT`, a subclass of the upstream `LUT`. The upstream loop runs unchanged. A test shows that with SCI switched off, `CueLUT` is **bit-for-bit identical** to upstream through a full void.

| Pathway | In the model | SCI setting |
|---|---|---|
| Sensation reaching the brain, and the decision to void | `is_voiding()` (54.7 cmH₂O or 500 mL trigger) | **Disabled.** It always returns False. |
| Descending coordinated void (detrusor on, sphincter relaxed) | Constant drives used only while voiding | **Disabled.** It is never reached. |
| Spinal storage reflexes below the injury | Upstream storage-phase drives (Gaussians of fullness and urethral opening) | **Kept** as the stand-in for intact reflexes. ASSUMED reinterpretation. |
| Mechanics, kidney, filling | Upstream | Unchanged |
| Volume limit | Upstream clips at 500 mL and also uses 500 mL to scale fullness | The two jobs are separated. Fullness is still scaled to 500 mL (SOURCED). The clip is moved to an ASSUMED ceiling (default 1000 mL, swept). |
| Drives above 500 mL | Never reached upstream | `extrapolate` (default) or `hold`. Both ASSUMED, both run. |

The injury level is configurable but only `"suprasacral"` is implemented. Anything else stops with an error. No injury detection or severity classification exists, as specified.

## Results (Experiment 1, 24 h, seed 42, default 1000 mL ceiling)

Figures: `results/stage3/exp1_control_vs_sci.png`, `exp1_control_vs_sci_hold.png`, `exp1_ceiling_sweep.png`, `exp1_hold_ceiling_sweep.png`. Data: `summary_all_cases.csv`, `leak_episodes_all_cases.csv`, and one 1 Hz trace per case.

| | Healthy control | SCI, no Cue |
|---|---|---|
| Urine produced | 1,957 mL | 1,957 mL |
| Voids | 3, each at about 490 mL and emptying to 0 | 0 |
| Leaks | 0 | **0** |
| Maximum volume | 490 mL | 1,000 mL (the ceiling), first reached at 13 h |
| Peak detrusor pressure | 54.7 cmH₂O | 56.6 cmH₂O, at about 500 mL (7.2 h) |
| Pressure at the end | 53.1 cmH₂O | **12.2 cmH₂O** (falls as the bladder over-fills) |
| Urine discarded by the ceiling clip | 0 | **957 mL** (mass not conserved) |

### What behaves oddly (reported, not fixed)

1. **No leak at default strength.** The detrusor peaks at 56.6 cmH₂O. The sphincter closes at 59.1 cmH₂O. The urethra never opens.
2. **Pressure falls when the bladder over-fills.** This happens under both drive rules, so it comes from the mechanics: the over-stretched detrusor loses active force and the wall geometry changes. The drive rule changes only how far it falls. This contradicts the clinical concern about high storage pressure after SCI. It is a limitation of extrapolating the model, not a finding about SCI.
3. **Urine disappears at the ceiling.** The upstream clip discards inflow. The sweep shows 457–1,457 mL discarded per day, depending on the ceiling.
4. **The no-leak result is fragile.** Reducing sphincter drive strength by 10% gives continuous overflow dribbling from about 7 h onwards, with about 1,470 mL leaked per day at ≤ 0.07 mL/s.
5. **No neurogenic detrusor overactivity or dyssynergia appears in any run.** As predicted in Stage 1, the model has no mechanism for either.

## Tests

`tests/test_stage3_sci.py` has 12 tests, all passing. They check:
- initial-volume unit conversion;
- exact equality with upstream when SCI is off;
- that SCI never voids;
- that drives keep the 500 mL reference;
- the `hold` and `extrapolate` behaviour;
- the ceiling, and that discarded volume is measured exactly;
- that there is no clipping below the ceiling;
- parameter override checks;
- leak detection on a synthetic trace;
- that a healthy void is not counted as a leak;
- that the configuration rejects unstable or unimplemented settings;
- that every parameter is labelled.

## Implications for Stage 4 and later (not acted on yet)

- Cue's alert and the experiments should be evaluated **before** the ceiling is reached. After that point the volume trace is an artefact of the clip.
- The healthy-model pressure trigger (54.7 cmH₂O at about 490 mL) is an upstream modelling choice. It is not a clinical fullness threshold, and Cue's alert must not be described as clinically safe because it fires near that volume.
- Because leak versus no leak depends on `somatic_a`, Experiments 2–4 should be run at least at the default and at ×0.9 so that both baseline behaviours are covered.
