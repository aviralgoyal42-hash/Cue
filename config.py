"""
Project Cue: the ONE configuration file.

Every value carries a label:
  SOURCED  - taken from the upstream implementation (lower-urinary-tract-sim v1.3.0)
             or a cited reference, named in `source`.
  ASSUMED  - our own choice. There is no published value behind it, so every result
             that depends on it is a model prediction under that assumption.

Note on "SOURCED (upstream)": the upstream defaults are the values the original
authors used. The paper does not give a primary reference or species for each
mechanical constant in its main text (see docs/STAGE1_REPOSITORY_REVIEW.md, section 6);
Table S1 cites Bastiaanssen 1996 for them, species unconfirmed (docs/MECHANICAL_CONSTANT_PROVENANCE.md). Being SOURCED does not mean validated.

Units are part of every name (_s, _ml, _cmH2O ...). The physiology runs in SI
internally; conversion happens only in cue_model/sci_lut.py with explicit factors.
"""
from dataclasses import dataclass
from typing import Any
import warnings

SOURCED = "SOURCED"
ASSUMED = "ASSUMED"
UPSTREAM = "lower-urinary-tract-sim v1.3.0 (Lister et al. 2025, R Soc Open Sci 12:242062)"


@dataclass(frozen=True)
class Param:
    value: Any
    unit: str
    status: str        # SOURCED or ASSUMED
    source: str        # citation, or the reason for the assumption

    def __post_init__(self):
        if self.status not in (SOURCED, ASSUMED):
            raise ValueError(f"status must be SOURCED or ASSUMED, got {self.status!r}")


# ---------------------------------------------------------------- simulation
SIMULATION = {
    "dt_s": Param(0.1, "s", SOURCED,
                  f"{UPSTREAM}, paper_figures notebooks. Must stay < 0.4 s: forward Euler on the "
                  "sphincter equation (tau_S = 0.2 s) diverges above that (Stage 2 finding)."),
    "duration_s": Param(24 * 3600, "s", ASSUMED, "One simulated day: long enough for several filling cycles."),
    "seed": Param(42, "-", SOURCED, f"Seed used in {UPSTREAM} notebooks (an arbitrary but fixed choice)."),
    "inflow_noise": Param(1.0, "-", SOURCED,
                          f"{UPSTREAM} default. Note: raises mean inflow from 0.017 to ~0.023 mL/s (Stage 2)."),
    "initial_volume_ml": Param(0.0, "mL", SOURCED, f"{UPSTREAM} starts from an empty bladder."),
}

# ---------------------------------------------------------------- physiology
# Optional overrides of upstream constants, e.g. {"kidney_args.kidney_c": 0.02}.
# Keys must exist in the upstream LUT object. Every override is ASSUMED by definition
# and must be justified here in a comment. Empty = use the upstream values unchanged.
#   urine production rate  -> kidney_args.kidney_c (mean, mL/s), kidney_a (daily swing, mL/s)
#   bladder compliance     -> bladder_args.C_l, bladder_args.alpha (passive wall stress)
#   detrusor strength      -> bladder_args.sigma_isoD (Pa);  sphincter strength -> sigma_isoS (Pa)
#   neural input strength  -> neural_args.parasympathetic_a, sympathetic_a, somatic_a (0-1)
PHYSIOLOGY_OVERRIDES: dict = {}

# ---------------------------------------------------------------- SCI condition
SCI = {
    "enabled": Param(True, "-", ASSUMED, "Experiments 1-4 all use the simplified SCI condition."),
    "injury_level": Param("suprasacral", "-", ASSUMED,
                          "ONE simplified condition: injury above the sacral cord, sacral reflex arc intact. "
                          "The true injury level is unconfirmed. Other levels are not implemented."),
    "voluntary_voiding": Param(False, "-", ASSUMED,
                               "Sensation to the brain and the decision to void are lost "
                               "(upstream is_voiding() trigger switched off)."),
    "coordinated_voiding_program": Param(False, "-", ASSUMED,
                                         "The descending coordinated void (detrusor on, sphincter relaxed) is lost."),
    "storage_drive_profile": Param("upstream", "-", ASSUMED,
                                   "The upstream storage-phase drives (volume-dependent Gaussians) stand in for the "
                                   "intact spinal reflexes below the injury. The paper calls them signals 'from the "
                                   "brain', so this reinterpretation is ours."),
    "fullness_reference_ml": Param(500.0, "mL", SOURCED,
                                   f"{UPSTREAM} max_V_B (Table S1 lists it as New: no primary source). Used ONLY to scale fullness inside the neural drives, "
                                   "so they behave exactly as upstream up to 500 mL. Above 500 mL they are extrapolated."),
    "drive_above_reference": Param("extrapolate", "-", ASSUMED,
                                   "How the neural drives behave above 500 mL, where upstream never goes. "
                                   "'extrapolate' (default) = upstream formulas unchanged, i.e. least modification; "
                                   "'hold' = drive frozen at its 500 mL value. Neither is sourced; both are reported."),
    "volume_ceiling_ml": Param(1000.0, "mL", ASSUMED,
                               "Placeholder. Upstream hard-clips volume at 500 mL; no sourced SCI value was found. "
                               "Inflow arriving at the ceiling is discarded by the model, so results are reported as a "
                               "sweep over several ceilings and the discarded volume is measured."),
}

CEILING_SWEEP_ML = Param([500.0, 750.0, 1000.0, 1500.0], "mL", ASSUMED,
                         "Values chosen to show how results depend on the unsourced ceiling.")


# ---------------------------------------------------------------- ultrasound sensor (Stage 4)
# The sensor is a SYNTHETIC EXPERIMENTAL PROXY. Nothing here is a validated ultrasound model.
TOYMUS_2024 = ("Toymus et al. 2024, Nat Commun 15:7216 (doi:10.1038/s41467-024-50397-8): wearable A-mode "
               "patch, 5 healthy volunteers, supine only, reference = B-mode ultrasound (not catheter), "
               "in-vivo mean relative error 11.17% (definition not stated)")
SENSOR = {
    "sample_interval_s": Param(60.0, "s", ASSUMED,
                               "One reading per minute. Toymus 2024 pulses every 2.5 s but recorded in-vivo volumes "
                               "every 30 min, so no sourced alert-system rate exists."),
    "best_case_mean_relative_error": Param(0.1117, "-", SOURCED,
                                           f"{TOYMUS_2024}. Used ONLY as a labelled best-case anchor: healthy, "
                                           "supine, BMI 18-23.7; not an SCI accuracy."),
    "noise_model": Param("gaussian_multiplicative", "-", ASSUMED,
                         "reading = truth x (1 + e), e ~ Normal(0, s), with s chosen so that mean |e| equals the "
                         "target mean relative error (s = MRE x sqrt(pi/2)). The real error distribution is unknown."),
}

# Each scenario lists only what differs from a perfect sensor. All magnitudes are ASSUMED
# except the 11.17% anchor; they span "best case" to "clearly bad" so the trade-off is visible.
_A = 0.1117
SENSOR_SCENARIOS = Param({
    "ideal":           {},                                    # reference only: no real sensor is perfect
    "anchor_11pct":    {"mean_relative_error": _A},
    "mre_20pct":       {"mean_relative_error": 0.20},
    "mre_30pct":       {"mean_relative_error": 0.30},
    "mre_40pct":       {"mean_relative_error": 0.40},
    "gain_minus20":    {"mean_relative_error": _A, "gain_error": -0.20},
    "gain_plus20":     {"mean_relative_error": _A, "gain_error": +0.20},
    "drift_minus2ph":  {"mean_relative_error": _A, "drift_per_hour": -0.02},
    "drift_plus2ph":   {"mean_relative_error": _A, "drift_per_hour": +0.02},
    "delay_5min":      {"mean_relative_error": _A, "delay_s": 300.0},
    "delay_15min":     {"mean_relative_error": _A, "delay_s": 900.0},
    "missing_20pct":   {"mean_relative_error": _A, "missing_probability": 0.20},
    "missing_50pct":   {"mean_relative_error": _A, "missing_probability": 0.50},
    "misaligned_at_4h": {"mean_relative_error": _A, "misalignment_start_h": 4.0, "misalignment_gain": 0.7,
                         "misalignment_missing_probability": 0.30},
    "combined_bad":    {"mean_relative_error": 0.30, "drift_per_hour": -0.02, "missing_probability": 0.30,
                        "delay_s": 300.0},
}, "-", ASSUMED, "Sweep of error types and sizes; posture changes are represented by the misalignment scenario "
                 "(Toymus 2024 tested supine only).")

# ---------------------------------------------------------------- Cue device (Stage 4)
DEVICE = {
    "median_window": Param(5, "readings", ASSUMED, "Estimate = median of the last 5 valid readings (robust to spikes)."),
    "confirm_n": Param(3, "readings", ASSUMED, "Alert only after 3 consecutive valid estimates at/above threshold."),
    "rearm_hysteresis_ml": Param(50.0, "mL", ASSUMED, "Alert re-arms when the estimate falls 50 mL below threshold."),
    "stale_timeout_s": Param(600.0, "s", ASSUMED, "No valid reading for 10 min -> device raises 'sensor stale'."),
}

# ---------------------------------------------------------------- Experiment 2 (Stage 4)
EXPERIMENT2 = {
    "alert_thresholds_ml": Param([250.0, 300.0, 350.0, 400.0, 450.0, 500.0], "mL", ASSUMED,
                                 "Swept, never tuned: the trade-off is the result."),
    "duration_s": Param(12 * 3600, "s", ASSUMED, "12 h covers the first fill past 500 mL and the leak onset (~7 h)."),
    "sphincter_scalings": Param([1.0, 0.9], "x somatic_a", ASSUMED,
                                "Default and 10% weaker: the two Stage 3 baseline behaviours (no leak / leak)."),
    "physiology_seeds": Param([42, 1, 2], "-", ASSUMED, "Inflow-noise seeds (filling-time spread)."),
    "sensor_seeds_per_case": Param(20, "-", ASSUMED, "Repeats of each sensor scenario with new sensor noise."),
    "reference_volume_ml": Param(500.0, "mL", SOURCED, f"{UPSTREAM} max_V_B (Table S1 lists it as New: no primary source); see EXPERIMENT2_SUCCESS_CRITERIA.md."),
    "false_alert_fraction": Param(0.6, "x V_ref", ASSUMED, "Alert below 300 mL true volume counts as false."),
    "relative_error_floor_ml": Param(50.0, "mL", ASSUMED, "Relative error only computed where true volume >= 50 mL."),
}


# ---------------------------------------------------------------- Stage 5: user, stimulation, safety
USER_SCENARIOS = Param({
    "prompt":              {"delay_min_s": 30.0, "delay_max_s": 300.0},
    "delayed":             {"delay_min_s": 1800.0, "delay_max_s": 5400.0},
    "no_press":            {"responds_to_alert": False},
    "accidental_no_alert": {"responds_to_alert": False, "accidental_press_times_s": [3600.0, 7200.0]},
    "press_in_lockout":    {"delay_min_s": 30.0, "delay_max_s": 300.0, "second_press_after_s": 300.0},
    "held_button":         {"delay_min_s": 30.0, "delay_max_s": 300.0, "hold_s": 900.0},
}, "-", ASSUMED, "No data exist on how people with SCI respond to a fullness alert. Delays are uniform "
                 "distributions chosen to span 'prompt' (0.5-5 min) and 'delayed' (30-90 min).")

STIM_PATTERNS = Param({   # model-exploration values (normalised drive, seconds); NOT clinical parameters
    "e0.6_s0.0_continuous": {"detrusor_drive": 0.6, "sphincter_drive": 0.0, "on_s": 1.0, "off_s": 0.0},
    "e0.6_s0.5_continuous": {"detrusor_drive": 0.6, "sphincter_drive": 0.5, "on_s": 1.0, "off_s": 0.0},
    "e0.6_s0.0_5on5off":    {"detrusor_drive": 0.6, "sphincter_drive": 0.0, "on_s": 5.0, "off_s": 5.0},
    "e0.6_s0.5_5on5off":    {"detrusor_drive": 0.6, "sphincter_drive": 0.5, "on_s": 5.0, "off_s": 5.0},
    "e1.0_s0.0_continuous": {"detrusor_drive": 1.0, "sphincter_drive": 0.0, "on_s": 1.0, "off_s": 0.0},
    "e1.0_s0.5_continuous": {"detrusor_drive": 1.0, "sphincter_drive": 0.5, "on_s": 1.0, "off_s": 0.0},
    "e1.0_s0.0_5on5off":    {"detrusor_drive": 1.0, "sphincter_drive": 0.0, "on_s": 5.0, "off_s": 5.0},
    "e1.0_s0.5_5on5off":    {"detrusor_drive": 1.0, "sphincter_drive": 0.5, "on_s": 5.0, "off_s": 5.0},
}, "-", ASSUMED, "Grid declared before any stimulation run. 0.6 = upstream healthy voiding detrusor drive "
                 "(SOURCED model value); 1.0 = maximum. Sphincter 0.5 = co-activation at the storage level "
                 "(ASSUMED, unvalidated conflict); 0.0 = no co-activation.")
REFERENCE_STIM = Param("e1.0_s0.5_5on5off", "-", ASSUMED,
                       "Declared before running: co-activation (the conservative assumption) with intermittent bursts.")
STIM_MAP_GRID = Param({"detrusor_drive": [0.4, 0.6, 0.8, 1.0], "sphincter_drive": [0.0, 0.25, 0.5, 1.0],
                       "timing_on_off_s": [[1.0, 0.0], [2.0, 2.0], [5.0, 5.0], [10.0, 5.0], [5.0, 10.0]],
                       "session_s": [60.0, 120.0], "start_volume_ml": 450.0},
                      "-", ASSUMED, "Stage 5 characterisation grid (open-loop stimulation from a full bladder).")

CONTROLLER = {
    "max_duration_s": Param(60.0, "s", ASSUMED, "Primary cutoff, needs no sensor. The model's healthy void "
                            "lasts ~27 s. Swept 30/60/120 s in Experiment 3."),
    "volume_stop_ml": Param(100.0, "mL", ASSUMED, "Stop when the DEVICE ESTIMATE falls to 100 mL."),
    "pressure_ceilings_cmH2O": Param([40.0, 55.0, 70.0], "cmH2O", ASSUMED,
                                     "Swept. 55 is near this model's healthy-void peak (54.7). 40 echoes the "
                                     "detrusor leak point pressure linked to upper-tract risk in myelodysplasia "
                                     "(McGuire et al. 1981, J Urol 126:205-209; checked via secondary sources only); "
                                     "it is NOT a validated stimulation limit."),
    "reference_pressure_ceiling_cmH2O": Param(55.0, "cmH2O", ASSUMED, "Middle of the sweep."),
    "lockout_s": Param(1800.0, "s", ASSUMED, "30 min between uses."),
    "pressure_sample_interval_s": Param(0.5, "s", ASSUMED, "Synthetic implant channel sampling."),
    "pressure_max_age_s": Param(2.0, "s", ASSUMED, "Older pressure readings are ignored."),
    "ultrasound_interval_during_stim_s": Param([60.0, 5.0], "s", ASSUMED,
                                               "60 s = unchanged; 5 s = faster sampling while stimulating. Swept."),
    "post_stimulus_window_s": Param(120.0, "s", ASSUMED, "Flow up to 120 s after a session counts as that "
                                    "session's emptying, not as leakage."),
}

SESSION_GUARD = {   # Task 3, docs/EXPERIMENT7_CRITERIA.md. Off unless a case asks for it.
    "session_caps": Param([2, 3, 4], "sessions per 12 h run", ASSUMED,
                          "Given by the user. Per 12 h run, not per day. Swept in Experiment 7."),
    "min_drop_fractions": Param([0.20, 0.40], "-", ASSUMED, "Given by the user. Swept in Experiment 7."),
    "readings_before_check": Param(5, "readings", ASSUMED, "Equal to DEVICE.median_window, so the estimate judged "
                                   "holds no reading from before or during the session."),
    "check_deadline_s": Param(600.0, "s", ASSUMED, "Reuses DEVICE.stale_timeout_s. Must not exceed the lockout."),
    "alert_repeat_s": Param(1800.0, "s", ASSUMED, "Reuses CONTROLLER.lockout_s."),
}

PRESSURE_SCENARIOS = Param({
    "ok":            {"noise_sd_cmH2O": 2.0},
    "noisy":         {"noise_sd_cmH2O": 10.0},
    "reads_low_30pct": {"noise_sd_cmH2O": 2.0, "gain_error": -0.30},
    "stuck_low":     {"stuck_at_cmH2O": 5.0},
    "dead":          {"dead_from_s": 0.0},
}, "-", ASSUMED, "Hypothetical implant channel; no published accuracy exists. 'ok' still has 2 cmH2O noise.")

EXTRA_SENSOR_FAULTS = Param({
    "stuck_high_450ml_from_5h": {"mean_relative_error": 0.1117, "stuck_from_h": 5.0, "stuck_at_ml": 450.0},
    "stuck_low_50ml_from_3h":   {"mean_relative_error": 0.1117, "stuck_from_h": 3.0, "stuck_at_ml": 50.0},
}, "-", ASSUMED, "Frozen-output faults that give a stuck device estimate (Experiment 4).")

EMPTYING_CLASSES = Param({"complete_min_fraction": 0.95, "partial_min_fraction": 0.10}, "-", ASSUMED,
                         "Voided fraction of the pre-session volume: >= 0.95 complete, >= 0.10 partial, else none.")

EXPERIMENT3 = {
    "duration_s": Param(12 * 3600, "s", ASSUMED, "Covers the first fill, alert, emptying and refill."),
    "alert_threshold_ml": Param(400.0, "mL", ASSUMED, "Centre of the 350-450 mL band where the anchor sensor "
                                "passed in Experiment 2 (a choice made after Experiment 2; 350 and 450 also run)."),
    "physiology_seeds": Param([42, 1, 2], "-", ASSUMED, "Inflow seeds."),
    "sensor_scenario": Param("anchor_11pct", "-", ASSUMED, "Best-case anchor sensor."),
}


def value(section, key):
    """Shortcut: the bare value of one parameter."""
    return section[key].value


def validate():
    """Refuse settings that are known to break the model; warn about doubtful ones."""
    dt = value(SIMULATION, "dt_s")
    if dt >= 0.4:
        raise ValueError(f"dt_s = {dt} s is unstable (must be < 0.4 s, see docs/STAGE2_REPRODUCTION.md)")
    if dt > 0.2:
        warnings.warn(f"dt_s = {dt} s is stable but makes sphincter activation overshoot; use <= 0.2 s")
    if 60 % dt > 1e-9 and abs(60 % dt - dt) > 1e-9:
        warnings.warn(f"dt_s = {dt} s does not divide 60 s; upstream inflow noise will be redrawn irregularly")
    if value(SCI, "enabled") and (value(SCI, "voluntary_voiding") or value(SCI, "coordinated_voiding_program")):
        # In the upstream model one switch (is_voiding) both decides to void and runs the
        # coordinated program, so the two cannot be separated without new physiology.
        raise NotImplementedError("With SCI enabled, both voiding pathways must be False")
    if value(SCI, "storage_drive_profile") != "upstream":
        raise NotImplementedError("Only the 'upstream' storage drive profile is implemented")
    if value(SCI, "injury_level") != "suprasacral":
        raise NotImplementedError("Only the 'suprasacral' simplified condition is implemented")
    if value(SCI, "volume_ceiling_ml") < value(SCI, "fullness_reference_ml"):
        raise ValueError("volume_ceiling_ml must be >= fullness_reference_ml")
    if value(SESSION_GUARD, "readings_before_check") < value(DEVICE, "median_window"):
        raise ValueError("readings_before_check must cover the median window, or old readings reach the check")
    if value(SESSION_GUARD, "check_deadline_s") > value(CONTROLLER, "lockout_s"):
        raise ValueError("check_deadline_s must not exceed lockout_s")


def as_table():
    """All labelled parameters as rows (for printing or saving next to results)."""
    rows = []
    single = {"CEILING_SWEEP_ML": CEILING_SWEEP_ML, "SENSOR_SCENARIOS": SENSOR_SCENARIOS,
              "USER_SCENARIOS": USER_SCENARIOS, "STIM_PATTERNS": STIM_PATTERNS, "REFERENCE_STIM": REFERENCE_STIM,
              "STIM_MAP_GRID": STIM_MAP_GRID, "PRESSURE_SCENARIOS": PRESSURE_SCENARIOS,
              "EXTRA_SENSOR_FAULTS": EXTRA_SENSOR_FAULTS, "EMPTYING_CLASSES": EMPTYING_CLASSES}
    for name, p in single.items():
        rows.append({"section": "GROUPS", "name": name, "value": p.value, "unit": p.unit,
                     "status": p.status, "source": p.source})
    for section_name, section in [("SIMULATION", SIMULATION), ("SCI", SCI), ("SENSOR", SENSOR),
                                  ("DEVICE", DEVICE), ("EXPERIMENT2", EXPERIMENT2),
                                  ("CONTROLLER", CONTROLLER), ("SESSION_GUARD", SESSION_GUARD),
                                  ("EXPERIMENT3", EXPERIMENT3)]:
        for key, p in section.items():
            rows.append({"section": section_name, "name": key, "value": p.value, "unit": p.unit,
                         "status": p.status, "source": p.source})
    for key, val in PHYSIOLOGY_OVERRIDES.items():
        rows.append({"section": "PHYSIOLOGY_OVERRIDES", "name": key, "value": val, "unit": "upstream units",
                     "status": ASSUMED, "source": "override of an upstream constant"})
    return rows
