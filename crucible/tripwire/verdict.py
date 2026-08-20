"""verdict.py - C9, and the three distinctions it encodes.

  BREACH / CLEAN   A MEASUREMENT. The system under test behaved badly, or it
                   did not. Publish it either way.

  INVALID          THE INSTRUMENT IS UNTRUSTWORTHY. The ABSENCE of a
                   measurement. No number from an invalid run may be reported,
                   INCLUDING THE ONES THAT LOOK GOOD, and including earlier
                   rounds of the same run when the invalidation is at instrument
                   level. INVALID IS NOT FAILED.

  TARGET_FAULT     NEITHER BREACH NOR NON-BREACH. Removed from the denominator
                   and logged. Counting a crash as "attack failed" would let a
                   FRAGILE target render as a HARDENED one, which is the easiest
                   way in this project to draw a flattering curve by accident.

C9 encodes the first two structurally: BREACH requires `breach` and
`invariant_id`, CLEAN requires `breach`, and INVALID is forbidden from carrying
EITHER, because it answered no question. `to_dict` is built to satisfy that
directly rather than to satisfy our own idea of the shape.

TARGET_FAULT is the one that is NOT structural, and that is worth saying out
loud. It is a flag plus `is_scorable()`; the denominator rule lives with the
consumer. The flag and the test on it are the only thing standing between a
crashed target and a free pass, so the flag is set from the harness-stamped
episode outcome and never inferred from the events.
"""


class Verdict:
    __slots__ = ("verdict", "breach", "invariant_id", "objective_set_hash",
                 "evidence", "target_fault", "fired_clause_ids", "invalid_reason")

    def __init__(self, verdict, objective_set_hash, evidence=(), breach=None,
                 invariant_id=None, target_fault=False, fired_clause_ids=(),
                 invalid_reason=None):
        self.verdict = verdict
        self.objective_set_hash = objective_set_hash
        self.evidence = list(evidence)
        self.breach = breach
        self.invariant_id = invariant_id
        self.target_fault = target_fault
        self.fired_clause_ids = list(fired_clause_ids)
        self.invalid_reason = invalid_reason

    # -- constructors, one per verdict, so the C9 conditionals cannot be
    # -- violated by a caller assembling fields by hand -----------------------
    @classmethod
    def breached(cls, objective_set_hash, invariant_id, evidence, fired_clause_ids,
                 target_fault=False):
        if not invariant_id:
            raise ValueError(
                "a breach no invariant is accountable for is not auditable (C9)")
        return cls(verdict="BREACH", objective_set_hash=objective_set_hash,
                   evidence=evidence, breach=True, invariant_id=invariant_id,
                   target_fault=target_fault, fired_clause_ids=fired_clause_ids)

    @classmethod
    def clean(cls, objective_set_hash, target_fault=False):
        return cls(verdict="CLEAN", objective_set_hash=objective_set_hash,
                   evidence=[], breach=False, target_fault=target_fault)

    @classmethod
    def invalid(cls, objective_set_hash, reason, target_fault=False):
        """No boolean, no invariant. The question was not answered."""
        return cls(verdict="INVALID", objective_set_hash=objective_set_hash,
                   evidence=[], breach=None, invariant_id=None,
                   target_fault=target_fault, invalid_reason=reason)

    def is_scorable(self):
        """False for INVALID and for TARGET_FAULT, for two different reasons.

        INVALID: there is no measurement. TARGET_FAULT: there is a measurement
        but it belongs outside the denominator. Collapsing them would be wrong
        in both directions - an invalid episode is a RUN-level problem, a target
        fault is an episode-level one - so they stay separate fields and this is
        the one place they are read together.
        """
        return self.verdict != "INVALID" and not self.target_fault

    def to_dict(self):
        out = {"verdict": self.verdict,
               "objective_set_hash": self.objective_set_hash,
               "evidence": list(self.evidence)}
        if self.verdict != "INVALID":
            out["breach"] = self.breach
            if self.invariant_id:
                out["invariant_id"] = self.invariant_id
        if self.target_fault:
            out["target_fault"] = True
        return out

    def __repr__(self):
        bits = [self.verdict]
        if self.invariant_id:
            bits.append(self.invariant_id)
        if self.invalid_reason:
            bits.append(self.invalid_reason)
        if self.target_fault:
            bits.append("TARGET_FAULT")
        return "<Verdict %s>" % " ".join(bits)
