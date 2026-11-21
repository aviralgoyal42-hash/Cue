"""
HYPOTHETICAL sacral nerve-root stimulator (Stage 5). Not a real device, not validated,
and NOT a source of clinical stimulation parameters.

What "stimulation" means in this model: while a burst is ON, the model's normalised
neural inputs are REPLACED inside the original upstream loop:
    omega_e* (pelvic, detrusor excitation)  <- detrusor_drive   (0-1, dimensionless)
    omega_s* (pudendal, sphincter)          <- sphincter_drive  (0-1, dimensionless)
    omega_i* (hypogastric, inhibition)      unchanged (sacral roots do not carry it)
While a burst is OFF, the inputs go back to the model's own storage-phase values.
Sacral roots carry both kinds of fibre, so a sphincter_drive > 0 is the ASSUMED, unvalidated
way of representing "stimulation also contracts the sphincter". The model has no sacral
anatomy, no fibre recruitment and no dyssynergia, and nothing links these numbers to
current, frequency or pulse width. Burst timings are model-exploration values in seconds,
not recommendations.

HYPOTHETICAL sphincter block (Task 6, off by default)
-----------------------------------------------------
A second, equally hypothetical channel that stops part of the sphincter's drive from
reaching the muscle, so the sphincter relaxes while the detrusor is driven. In the model
it is one number, `sphincter_block` (0-1, dimensionless, ASSUMED):
    sphincter input = (what it would have been) x (1 - sphincter_block)
    0 = no block (the old behaviour, exactly);  1 = complete block.
`block_scope` says when the block acts:
    "burst"    only while a burst is ON. It removes the co-activation and nothing else.
               An 80% block of a 0.5 co-activation gives 0.1, the Task 5 level.
    "session"  from the start to the end of the session, including the gaps between bursts,
               where it also cuts the sphincter's own reflex drive.
`block_fails_at_s` is a FAULT for testing: the block stops working this many seconds
after the session starts (0 = it never works). None = no fault.
The block is a model drive, not a nerve-block setting. Nothing here says a real device
could reach any block level (docs/TASK6_PLAN.md).
"""
from dataclasses import dataclass
from typing import Optional

BLOCK_SCOPES = ("burst", "session")


@dataclass(frozen=True)
class BurstPattern:
    name: str = "continuous_e1.0_s0.0"
    detrusor_drive: float = 1.0
    sphincter_drive: float = 0.0
    on_s: float = 1.0
    off_s: float = 0.0        # 0 = continuous while the session lasts
    sphincter_block: float = 0.0              # 0 = no block (default), 1 = complete block
    block_scope: str = "burst"                # "burst" or "session"
    block_fails_at_s: Optional[float] = None  # fault: seconds after session start; None = no fault

    def __post_init__(self):
        if not 0.0 <= self.sphincter_block <= 1.0:
            raise ValueError(f"sphincter_block must be between 0 and 1, got {self.sphincter_block}")
        if self.block_scope not in BLOCK_SCOPES:
            raise ValueError(f"block_scope must be one of {BLOCK_SCOPES}, got {self.block_scope!r}")
        if self.block_fails_at_s is not None and self.block_fails_at_s < 0:
            raise ValueError("block_fails_at_s must be >= 0 or None")

    @classmethod
    def from_dict(cls, name, values):
        return cls(name=name, **values)


class HypotheticalStimulator:
    def __init__(self, pattern: BurstPattern):
        self.pattern = pattern
        self.active = False
        self.start_t = None
        self.sessions = []           # (start_s, stop_s)

    def start(self, t_s):
        if not self.active:
            self.active, self.start_t = True, t_s

    def stop(self, t_s):
        if self.active:
            self.sessions.append((self.start_t, t_s))
            self.active, self.start_t = False, None

    def burst_on(self, t_s):
        """True while inside the ON part of a burst."""
        if not self.active:
            return False
        p = self.pattern
        if p.off_s <= 0:
            return True
        return (t_s - self.start_t) % (p.on_s + p.off_s) < p.on_s

    def block_on(self, t_s):
        """True while the sphincter block is acting (never outside a session)."""
        p = self.pattern
        if not self.active or p.sphincter_block <= 0:
            return False
        if p.block_fails_at_s is not None and t_s - self.start_t >= p.block_fails_at_s:
            return False                                   # the fault: the block has stopped working
        return p.block_scope == "session" or self.burst_on(t_s)

    def _blocked(self, drive):
        # Rounded so that an 80% block of 0.5 is exactly 0.1 (not 0.09999999999999998).
        return round(drive * (1.0 - self.pattern.sphincter_block), 12)

    def sphincter_input(self, t_s, own_drive):
        """The sphincter's input now. `own_drive` is the model's own (reflex) value.
        Burst ON: the co-activation replaces it. Block acting: whatever it is gets cut."""
        drive = self.pattern.sphincter_drive if self.burst_on(t_s) else own_drive
        return self._blocked(drive) if self.block_on(t_s) else drive

    def drive(self, t_s):
        """(detrusor drive, sphincter drive) to impose now, or (None, None) = leave the model alone.
        The sphincter value includes the block. Between bursts use sphincter_input()."""
        if self.burst_on(t_s):
            sphincter = self.pattern.sphincter_drive
            return self.pattern.detrusor_drive, (self._blocked(sphincter) if self.block_on(t_s) else sphincter)
        return None, None
