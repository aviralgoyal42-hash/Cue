"""
SensorFusion (Task 8): what the device could do with TWO volume signals, sensor A (the
patch) and an abstract sensor B. Off by default: the rig builds one only when asked.

RULE: like the device, it sees readings only (a time and a volume, or "missing"), from
each sensor. It never sees the real bladder volume. All numbers are ASSUMED
(docs/TASK8_PLAN.md).

The disagreement test
---------------------
It watches the RATIO A / B, not either sensor alone. Both look at the same bladder, so
filling and emptying cancel in the ratio, and so does a constant gain error in either one.
    now     = the last `now_s` seconds;   before = the `before_s` seconds before that
    ratio   = mean of A's valid readings / mean of B's valid readings, in each window
    change  = ratio now / ratio before - 1          (-0.30 = A fell 30% compared with B)
    noise   = sqrt(sA^2 / nA + sB^2 / nB), added for both windows, where sA and sB are each
              sensor's own scatter, measured from the jumps between its neighbouring readings
    Flag when  |change| >= k_noise x noise  AND  |change| >= min_change
               AND B's mean now >= min_ml.          Once only, until `reset`.
The test cannot tell WHICH sensor is wrong, and a fault that hits both equally is invisible.

The three rules (what reading is passed on to the device)
    "flag"      sensor A, always. The flag only asks the user to check the patch.
    "trust_b"   sensor A until the test fires, then sensor B.
    "average"   the mean of A and B (the valid one if only one is valid), always.
The flag is raised in the same way under all three rules.
"""
import math
from collections import deque

RULES = ("flag", "trust_b", "average")


def fused_value(rule, a, b, flagged):
    """The volume passed on to the device (None = missing). `a` and `b` are volumes or None."""
    if rule == "average":
        if a is not None and b is not None:
            return (a + b) / 2.0
        return a if a is not None else b
    if rule == "trust_b" and flagged:
        return b
    return a


class SensorFusion:
    def __init__(self, rule="flag", now_s=1200.0, before_s=5400.0, min_now=10, min_before=30, k_noise=4.0,
                 min_change=0.10, min_ml=100.0, noise_n=120, noise_floor=0.02):
        if rule not in RULES:
            raise ValueError(f"rule must be one of {RULES}, got {rule!r}")
        self._settings = dict(locals())
        del self._settings["self"]
        self.rule = rule
        self.now_s, self.before_s = now_s, before_s
        self.min_now, self.min_before = min_now, min_before
        self.k_noise, self.min_change, self.min_ml = k_noise, min_change, min_ml
        self.noise_floor = noise_floor
        self._pairs = deque()                        # (time, A or None, B or None), oldest first
        self._jumps = (deque(maxlen=noise_n), deque(maxlen=noise_n))   # squared relative jumps, A and B
        self._last = [None, None]
        self._paused = False
        self.flagged = False
        self.flag = None                             # {"t_s", "change"} once the test has fired

    # ------------------------------------------------------------- session and patch events
    def pause(self):
        """A stimulation session started: stop testing until it is over."""
        self._paused = True

    def resume(self):
        """The session ended: start again from fresh readings."""
        self._paused = False
        self._pairs.clear()
        self._last = [None, None]

    def reset(self):
        """The user put the patch back: start again from nothing, trusting sensor A again."""
        self.__init__(**self._settings)

    # ------------------------------------------------------------- one pair of readings
    def receive(self, reading_a, reading_b):
        """Take one reading from each sensor (same time). Returns (reading for the device, fired)."""
        fired = False
        if not self._paused and not self.flagged:
            self._remember(reading_a.t_s, reading_a.volume_ml, reading_b.volume_ml)
            change = self._disagreement(reading_a.t_s)
            if change is not None:
                self.flagged, fired = True, True
                self.flag = {"t_s": reading_a.t_s, "change": change}
        value = fused_value(self.rule, reading_a.volume_ml, reading_b.volume_ml, self.flagged)
        return type(reading_a)(reading_a.t_s, value), fired

    def _remember(self, t_s, a, b):
        for which, value in ((0, a), (1, b)):
            if value is None:
                continue
            last = self._last[which]
            if last is not None and (value + last) > 0:
                self._jumps[which].append(((value - last) / ((value + last) / 2.0)) ** 2)
            self._last[which] = value
        self._pairs.append((t_s, a, b))
        oldest = t_s - self.now_s - self.before_s
        while self._pairs and self._pairs[0][0] <= oldest:
            self._pairs.popleft()

    def noise(self, which):
        """Scatter of one reading of sensor A (0) or B (1), as a fraction of its size."""
        jumps = self._jumps[which]
        if not jumps:
            return self.noise_floor
        return max(self.noise_floor, math.sqrt(sum(jumps) / len(jumps) / 2.0))

    def _disagreement(self, t_s):
        """The change in the A / B ratio if it is large enough to flag, else None."""
        split = t_s - self.now_s
        sums = [[0.0, 0], [0.0, 0], [0.0, 0], [0.0, 0]]     # A now, B now, A before, B before
        for t, a, b in self._pairs:
            base = 0 if t > split else 2
            if a is not None:
                sums[base][0] += a
                sums[base][1] += 1
            if b is not None:
                sums[base + 1][0] += b
                sums[base + 1][1] += 1
        (a_now, na), (b_now, nb), (a_bef, ma), (b_bef, mb) = sums
        if na < self.min_now or nb < self.min_now or ma < self.min_before or mb < self.min_before:
            return None
        if b_now / nb < self.min_ml or b_now <= 0 or a_bef <= 0 or b_bef <= 0:
            return None
        change = (a_now / na) / (b_now / nb) / ((a_bef / ma) / (b_bef / mb)) - 1.0
        sa, sb = self.noise(0), self.noise(1)
        noise = math.sqrt(sa * sa / na + sb * sb / nb + sa * sa / ma + sb * sb / mb)
        if abs(change) >= self.k_noise * noise and abs(change) >= self.min_change:
            return change
        return None
