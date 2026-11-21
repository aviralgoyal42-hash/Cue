# Experiment 2 (SCI + Cue monitoring): success criteria

**Written 2026-11-04, before any Experiment 2 code was run.** These criteria are frozen. If one has to change, the change is logged at the bottom of this file with the date and the reason. The original text stays as it is.

## What Experiment 2 tests

The synthetic ultrasound sensor reads the simulated bladder. `CustomTechDevice` sees **only those readings** and decides when to alert the user. There is no button press and no stimulation; those come in Stage 5. The physiology is the Stage 3 SCI baseline, run at two sphincter strengths: the default (`somatic_a` × 1.0) and 10% weaker (× 0.9).

All criteria are about the model. Passing them shows that the alert logic works **in this simulation under these assumptions**. It does **not** show clinical safety or a clinically correct alert volume.

## Reference volume ("capacity" in this experiment)

**V_ref = 500 mL.** This is the upstream fullness reference (`max_V_B`, SOURCED). The healthy model voids at about 490 mL. This is a modelling reference, not a clinical capacity for people with SCI, and it is not a sourced clinical threshold.

## The adverse event the alert must beat

Each physiology run has one **adverse-event time, T_adverse**, taken from ground truth by the evaluation code only:
- **Default sphincter:** the first time true volume reaches V_ref (500 mL). Beyond this point the model is extrapolating and pressure behaves non-physiologically (Stage 3).
- **10% weaker sphincter:** the first time involuntary leakage starts (outflow > 0 with no void). In Stage 3 this was at about 485 mL, at about 7.0 h. If leakage started after the bladder reached 500 mL, the earlier of the two times would be used.

## How each alert is classified (evaluation side, using ground truth)

| Class | Definition |
|---|---|
| **False alert** | An alert event raised while true volume is **below 0.6 × V_ref (300 mL)**. |
| **Useful alert** | The first alert event at or above 300 mL that occurs **before T_adverse**. |
| **Late** | The first alert event at or above 300 mL occurs **after T_adverse**. |
| **Missed** | No alert event at or above 300 mL occurs during the run. |
| **Lead time** | T_adverse minus the time of the useful alert. |

The 300 mL "clearly not full" bound (0.6 × V_ref) is ASSUMED. It is a modelling convention and has no clinical source.

## Pass criteria (for one combination of sensor scenario, alert threshold and sphincter strength)

Each combination is evaluated over several physiology seeds × several sensor seeds. The counts are in `config.EXPERIMENT2`.

| ID | Criterion | Required |
|---|---|---|
| **C1** | Runs with a useful alert | **≥ 95%** |
| **C2** | Runs with at least one false alert | **≤ 5%** |
| **C3** | Median lead time, over runs with a useful alert | **≥ 30 min** (ASSUMED: time for the user to decide and act) |
| **C4** | Episodes where readings stop for longer than the device's stale timeout and the device flags "sensor stale" | **100%** (the device must report when it is blind) |

"Cue works" for a combination means **C1, C2 and C3 all pass**. C4 is judged across all combinations that include missing readings or misalignment.

## What is reported regardless of pass or fail

For every combination:
- sensor MAE, RMSE and mean relative error (relative error only where true volume ≥ 50 mL, to avoid dividing by near-zero);
- the fraction of readings that were missing;
- the device estimate's error;
- the distribution of alert times and volumes;
- the rates of false, late and missed alerts.

In addition, the **trade-off curve** across alert thresholds (false alerts against late or missed alerts) is reported for every sensor scenario. The threshold is never picked to make one scenario look good.

**Pressure.** The device does not use pressure. Bladder pressure falls as the bladder over-fills in this model (Stage 3), so pressure is **not** used as a fullness indicator anywhere. True pressure at the alert is reported only as a descriptive number.

## Change log
- 2026-11-04, after Experiment 2: **no criteria changed.** Two weaknesses of these criteria showed up in the results. Early alerts above 300 mL count as useful, and repeated alerts ("churn") are not penalised. Both are reported in `docs/STAGE4_EXPERIMENT2.md` and in VALIDATION_AND_LIMITATIONS.md §5 (E26, E27) instead of being fixed here.
