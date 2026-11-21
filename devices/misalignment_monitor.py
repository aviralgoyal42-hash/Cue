"""
MisalignmentMonitor (Task 6): flags when the patch has probably moved, and measures by
how much its readings fell. Off by default; CustomTechDevice owns one only when asked.

RULE: like the device, it sees sensor readings only (a time and a volume, or "missing").
It never sees the real bladder volume. All its numbers are ASSUMED (docs/TASK6_PLAN.md).

Why the Experiment 6 detector failed, and what is different here
----------------------------------------------------------------
Experiment 6 compared ONE estimate with the HIGHEST estimate of the last 15 minutes and
used a fixed drop. A highest value is mostly noise, and a fixed drop cannot suit both a
quiet and a noisy sensor. This monitor instead
  * compares two AVERAGES of many readings, which are much steadier than single values;
  * measures how noisy the sensor is from its own readings, and asks for a drop that is
    large COMPARED WITH THAT NOISE;
  * also watches a second sign: readings going missing more often than they used to.

Rule 1, "level drop"
  The bladder cannot shrink by itself between emptyings. Take the last 2 x n valid
  readings: the older n ("before") and the newer n ("after").
      change = mean(after) / mean(before) - 1          (-0.30 = reads 30% lower)
      noise  = typical relative jump between neighbouring readings, turned into the
               scatter of one reading:  sqrt(mean(jump^2) / 2), over the last `noise_n` jumps
      chance = noise x sqrt(2 / n)                     (how far `change` wanders by luck)
  Flag when   change <= -k_noise x chance   AND   change <= -min_drop_fraction
              AND mean(before) >= min_ml.
  The measured ratio mean(after) / mean(before) is kept, so the device can correct for it.
  It is re-measured against the same "before" for the next n valid readings, because at the
  moment of the flag "after" still holds some readings from before the patch moved.

Rule 2, "dropout rise"
  Count missing readings in the last `dropout_slots` readings. Compare with the share that
  went missing before that (the device's own long-run rate, nudged upward to be cautious).
  Flag when a count this high would happen by luck less than `dropout_chance` of the time.

Task 7 option, `fill_adjust` (off by default; docs/TASK7_PLAN.md)
  The bladder keeps filling between "before" and "after", which hides part of the fall.
  With `fill_adjust` on, the ratio is measured against a straight line fitted to the
  readings from before the fall (how fast the bladder was filling), instead of against the
  flat "before" average. The flag rules themselves do not change.

The two rules help each other: once rule 2 has fired, the patch is already under suspicion,
so rule 1 asks for less proof (`k_noise_after_dropout` instead of `k_noise`).

Each rule fires at most once, until the user says the patch was put back (`reset`).
Readings during and just before/after a stimulation session are left out (`pause`,
`resume`): emptying is the one time the volume really does fall.
"""
import math
from collections import deque

LEVEL_DROP, DROPOUT_RISE = "level_drop", "dropout_rise"


def chance_of_at_least(count, slots, p):
    """Chance of `count` or more misses in `slots` readings when each is missed with chance p."""
    return sum(math.comb(slots, k) * p ** k * (1 - p) ** (slots - k) for k in range(count, slots + 1))


class MisalignmentMonitor:
    def __init__(self, window_n=15, k_noise=3.5, k_noise_after_dropout=2.0, min_drop_fraction=0.10,
                 min_ml=100.0, noise_n=120, noise_floor=0.02, dropout_slots=20, dropout_baseline_slots=120,
                 dropout_chance=1e-4, dropout_floor=0.02, compensate=True,
                 fill_adjust=False, fill_history_n=90, fill_min_n=30, ratio_floor=0.40):
        self._settings = dict(locals())              # kept so reset() can start again with the same settings
        del self._settings["self"]
        # Task 7 (off by default): allow for the bladder filling while the ratio is measured.
        self.fill_adjust = fill_adjust
        self.fill_min_n = fill_min_n
        self.ratio_floor = ratio_floor
        self._history = deque(maxlen=fill_history_n)  # (time, value) of the last valid readings
        self._line = None                            # (time0, value at time0, mL per second) once rule 1 fired
        self.line_kind = ""                          # "line", "flat_few_readings" or "flat_negative_slope"
        self.window_n = window_n
        self.k_noise = k_noise
        self.k_noise_after_dropout = k_noise_after_dropout
        self.min_drop_fraction = min_drop_fraction
        self.min_ml = min_ml
        self.noise_floor = noise_floor
        self.dropout_slots = dropout_slots
        self.dropout_baseline_slots = dropout_baseline_slots
        self.dropout_chance = dropout_chance
        self.dropout_floor = dropout_floor
        self.compensate = compensate                 # False = flag only, never correct
        self._values = deque(maxlen=2 * window_n)    # last valid readings (mL), oldest first
        self._jumps = deque(maxlen=noise_n)          # squared relative jumps between neighbours
        self._last_value = None
        self._slots = deque(maxlen=dropout_slots)    # 1 = missing, 0 = valid, newest last
        self._older_slots = 0                        # readings that have left the window ...
        self._older_missing = 0                      # ... and how many of them were missing
        self._paused = False
        self._before_mean = None                     # the "before" average when rule 1 fired
        self._settle_left = 0                        # readings still to come before the ratio is final
        self.fired = set()                          # rules that have fired since the last reset
        self.flags = []                              # one dict per flag, for the log
        self.ratio = 1.0                             # measured after/before ratio (1 = no shift seen)

    # ------------------------------------------------------------- session and patch events
    def pause(self):
        """A stimulation session started: stop looking until it is over."""
        self._paused = True

    def resume(self):
        """The session ended. Forget the readings from before it: the volume has changed."""
        self._paused = False
        self._values.clear()
        self._history.clear()
        self._last_value = None
        self._settle_left = 0                        # a ratio still being measured stays as it is

    def reset(self):
        """The user put the patch back: start again from nothing, with no correction."""
        self.__init__(**self._settings)

    # ------------------------------------------------------------- one reading
    def receive(self, reading):
        """Take one reading. Returns the list of rules that fired on it (usually empty)."""
        if self._paused:
            return []
        fired = []
        self._count_slot(reading.valid)
        if DROPOUT_RISE not in self.fired and self._dropout_rise():
            fired.append(self._flag(reading.t_s, DROPOUT_RISE, None))
        if reading.valid:
            self._add_value(reading.volume_ml)
            self._history.append((reading.t_s, reading.volume_ml))
            if LEVEL_DROP not in self.fired:
                ratio = self._level_drop()
                if ratio is not None:
                    fired.append(self._flag(reading.t_s, LEVEL_DROP, ratio))
                    if self.compensate:
                        self._settle_left = self.window_n
                        if self.fill_adjust:
                            self._fit_filling_line()
                            self.ratio = self._ratio_against_line()
                        else:
                            self.ratio = ratio
            elif self._settle_left > 0:
                # The rule fires as soon as the fall is clear, when "after" still holds some
                # readings from before the patch moved. So keep measuring against the same
                # "before" until "after" holds only readings taken since the flag.
                self._settle_left -= 1
                if self.fill_adjust:
                    self.ratio = self._ratio_against_line()
                else:
                    recent = list(self._values)[-self.window_n:]
                    self.ratio = min(1.0, sum(recent) / len(recent) / self._before_mean)
        return fired

    # ------------------------------------------------------------- Task 7: allow for filling
    def _fit_filling_line(self):
        """Fit a straight line (least squares, volume against time) through the remembered readings
        that are older than the newest n. It says what the patch would read now had it not moved.
        Too few readings, or a line that slopes down, gives a flat line at the "before" average,
        which is exactly the Task 6 correction."""
        older = list(self._history)[:-self.window_n]
        flat = (0.0, self._before_mean, 0.0)
        if len(older) < self.fill_min_n:
            self._line, self.line_kind = flat, "flat_few_readings"
            return
        t_mean = sum(t for t, _ in older) / len(older)
        v_mean = sum(v for _, v in older) / len(older)
        spread = sum((t - t_mean) ** 2 for t, _ in older)
        slope = sum((t - t_mean) * (v - v_mean) for t, v in older) / spread if spread > 0 else 0.0
        if slope < 0:                                # the bladder does not shrink by itself
            self._line, self.line_kind = flat, "flat_negative_slope"
        else:
            self._line, self.line_kind = (t_mean, v_mean, slope), "line"

    def _ratio_against_line(self):
        """Mean of the newest n readings, divided by what the line says at those same times."""
        t0, v0, slope = self._line
        recent = list(self._history)[-self.window_n:]
        read = sum(v for _, v in recent) / len(recent)
        expected = sum(v0 + slope * (t - t0) for t, _ in recent) / len(recent)
        return min(1.0, max(self.ratio_floor, read / expected))

    def _flag(self, t_s, rule, ratio):
        self.fired.add(rule)
        self.flags.append({"t_s": t_s, "rule": rule, "ratio": ratio})
        return rule

    # ------------------------------------------------------------- rule 1: level drop
    def _add_value(self, value):
        if self._last_value is not None:
            middle = (value + self._last_value) / 2.0
            if middle > 0:
                self._jumps.append(((value - self._last_value) / middle) ** 2)
        self._last_value = value
        self._values.append(value)

    def noise(self):
        """Scatter of one reading as a fraction of its size, measured from the readings themselves."""
        if not self._jumps:
            return self.noise_floor
        return max(self.noise_floor, math.sqrt(sum(self._jumps) / len(self._jumps) / 2.0))

    def _level_drop(self):
        n = self.window_n
        if len(self._values) < 2 * n:
            return None
        values = list(self._values)
        before, after = sum(values[:n]) / n, sum(values[n:]) / n
        if before < self.min_ml:
            return None
        change = after / before - 1.0
        chance = self.noise() * math.sqrt(2.0 / n)
        k = self.k_noise_after_dropout if DROPOUT_RISE in self.fired else self.k_noise
        if change <= -k * chance and change <= -self.min_drop_fraction:
            self._before_mean = before
            return after / before
        return None

    # ------------------------------------------------------------- rule 2: dropout rise
    def _count_slot(self, valid):
        if len(self._slots) == self._slots.maxlen:           # the oldest slot is about to leave
            self._older_slots += 1
            self._older_missing += self._slots[0]
        self._slots.append(0 if valid else 1)

    def _dropout_rise(self):
        if self._older_slots < self.dropout_baseline_slots or len(self._slots) < self.dropout_slots:
            return False
        usual = self._older_missing / self._older_slots
        cautious = usual + 2.0 * math.sqrt(usual * (1.0 - usual) / self._older_slots)   # lean high
        p = min(max(self.dropout_floor, cautious), 1.0)
        return chance_of_at_least(sum(self._slots), self.dropout_slots, p) < self.dropout_chance
