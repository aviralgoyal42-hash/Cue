# Experiment 2b (rerun with 15 physiology seeds): criteria

**Written 2026-11-04, before the rerun was started.**

- **Frozen criteria:** C1–C4 are exactly those in `docs/EXPERIMENT2_SUCCESS_CRITERIA.md`, unchanged.
- **What changes:** 15 inflow (physiology) seeds per sphincter strength instead of 3: seeds 42 and 1–14. With 20 sensor seeds, each cell then has 300 runs instead of 60. Everything else is identical, including scenarios, thresholds and device settings.

## POST-HOC metric (added after seeing Experiment 2; not a success criterion)

**Band rate** = the fraction of runs in which a useful alert exists **and** the true volume at that first useful alert lies in **350–450 mL**.

The 350–450 mL band is ASSUMED. It was chosen after Experiment 2 showed that noisy sensors can "pass" by alerting early (E26). This metric is labelled post-hoc everywhere and does not decide pass or fail.

## Caveat on lead time (applies to Experiment 2 and 2b)

Lead time is mostly (adverse-event volume − alert volume) ÷ inflow rate. With inflow around 0.02 mL/s, a 100 mL gap is roughly 80 min. **C3 therefore largely restates the threshold and the filling rate.** It is not independent evidence that Cue works.
