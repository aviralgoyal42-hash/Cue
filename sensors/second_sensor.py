"""
Sensor B (Task 8): an ABSTRACT second bladder-volume signal. It is not a model of any
technology or product, and nothing here says a real device could behave like it.

    reading B = gain_B x true volume x (1 + noise), or missing

Sensor B is built with the same synthetic sensor class as sensor A (the patch), with its
own random stream. This file only works out B's settings. All values are ASSUMED
(docs/TASK8_PLAN.md).

The "independence" setting, 0 to 1, says how much of a PATCH SHIFT also hits B:
    B's shift                  = 1 - independence x (1 - A's shift)
    B's extra missing readings = independence x A's extra missing readings
    0 = a patch shift does not touch B at all;  1 = the same fault hits B in full.
It applies to the patch shift only. A's other faults never touch B.
"""


def sensor_b_values(error, independence, a_values, gain_b=1.0, missing=0.10, drift_per_hour=0.0, own_shift=None):
    """Settings for sensor B, as a dict for SensorScenario.from_dict.

    error          B's mean relative error (the same meaning as sensor A's)
    independence   0 to 1, how much of A's patch shift B shares
    a_values       sensor A's scenario values (only its patch-shift entries are looked at)
    own_shift      (start_h, gain): B itself shifts, whatever A does (the "B moves" case)
    """
    if not 0.0 <= independence <= 1.0:
        raise ValueError(f"independence must be between 0 and 1, got {independence}")
    values = {"mean_relative_error": float(error), "gain_error": float(gain_b) - 1.0,
              "missing_probability": float(missing), "drift_per_hour": float(drift_per_hour)}
    start = a_values.get("misalignment_start_h")
    if start is not None and independence > 0:
        a_shift = a_values.get("misalignment_gain", 1.0)
        a_extra = a_values.get("misalignment_missing_probability", 0.0)
        values.update({"misalignment_start_h": start,
                       "misalignment_gain": round(1.0 - independence * (1.0 - a_shift), 12),
                       "misalignment_missing_probability": round(independence * a_extra, 12)})
    if own_shift is not None:
        values.update({"misalignment_start_h": float(own_shift[0]), "misalignment_gain": float(own_shift[1])})
    return values
