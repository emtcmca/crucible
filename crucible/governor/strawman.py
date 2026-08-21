"""strawman.py - DELIBERATELY WRONG governors, kept in the tree forever.

Proof that `tests/test_governor_abort.py` can fail. CONVENTIONS.md section 8
rule 2.

  raising_governor   raises when the ceiling is reached instead of returning a
                     verdict. This is the natural Python instinct and it is
                     wrong here for a reason that is not about style: the abort
                     IS A RESULT OF THE RUN. It has to be written to the ledger,
                     carried in the round outcome, and reported. An exception
                     propagates past all three and the run ends looking like a
                     crash. CONVENTIONS 2.4 draws the identical line between
                     INVALID and FAILED - the absence of a measurement is itself
                     a thing that must be recorded, and no number from a run
                     that ended in a traceback is trustworthy either.

  silent_governor    returns allowed=False and logs NOTHING. Structurally the
                     opposite failure and materially the worse one: the loop
                     stops early, every downstream artifact looks complete, and
                     the reason the campaign ran three rounds instead of six is
                     nowhere in the evidence bundle. A run that stopped for a
                     reason nobody recorded is indistinguishable from a run that
                     converged.
"""


class BudgetExhausted(RuntimeError):
    """The exception the wrong design raises."""


def raising_governor(budget_cls, governor_cls):
    """Return a governor subclass that raises rather than returning."""

    class Raising(governor_cls):
        def authorize(self, role, estimated_usd, estimated_tokens=0):
            verdict = super().authorize(role, estimated_usd, estimated_tokens)
            if not verdict.allowed:
                raise BudgetExhausted(verdict.code)
            return verdict

    return Raising


def silent_governor(budget_cls, governor_cls):
    """Return a governor subclass that refuses without recording the refusal."""

    class Silent(governor_cls):
        def authorize(self, role, estimated_usd, estimated_tokens=0):
            before = len(self.events)
            verdict = super().authorize(role, estimated_usd, estimated_tokens)
            del self.events[before:]
            return verdict

    return Silent


RAISING_MUST_FAIL = {
    "G1": "the call raises, so there is no verdict object to return, to log, or "
          "to put in a round outcome.",
    "G2": "AND IT FAILS THE SECOND CHECK TOO, WHICH IS WORTH NAMING RATHER THAN "
          "ABSORBING - the meta-check caught this on the first green run. The "
          "event IS appended: `super().authorize` runs to completion before the "
          "raise. But no caller ever reaches the line that reads it, because the "
          "exception unwinds past it. A record nobody can get to is not a record, "
          "and that is the same defect as not writing one - which is exactly why "
          "the round outcome carries the verdict rather than the log.",
}

SILENT_MUST_FAIL = {
    "G2": "the refusal never reaches `events`, so the evidence bundle cannot "
          "say why the campaign stopped.",
}

STRAWMEN = {
    "raising_governor": (raising_governor, RAISING_MUST_FAIL),
    "silent_governor": (silent_governor, SILENT_MUST_FAIL),
}
