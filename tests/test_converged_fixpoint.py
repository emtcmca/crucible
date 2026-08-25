"""The policy fixpoint is a terminal SUCCESS, not an unhandled exception.

Run 08 of the 2026-08-24 live batch promoted a policy to GCS and then died
raising PromotionError("E_CONVERGED") - whose own message reads "This is the
convergence signal, not a failure". The run produced no evidence bundle, so the
single most complete outcome in the batch is the one outcome with no record of
itself. These tests pin the repair.
"""
import pytest

from crucible.conductor.conductor import (
    CONVERGED_DRY_ROUNDS, CONVERGED_POLICY_FIXPOINT, RoundRecord)


class _FixpointError(RuntimeError):
    """Shaped like crucible.gate.PromotionError, deliberately NOT imported.

    The conductor catches this by duck type across its injected-callable seam.
    Constructing a look-alike here is the test of that contract: if the
    conductor ever starts catching by class, this stops being caught and the
    test fails, which is the notification we want."""
    def __init__(self, code, detail):
        super().__init__("%s: %s" % (code, detail))
        self.code = code
        self.detail = detail


def _conductor_with(promoter):
    """A Conductor whose promoter is the only live part."""
    from crucible.conductor.conductor import Conductor
    c = Conductor.__new__(Conductor)
    c.promote = promoter
    return c


def test_the_fixpoint_is_caught_and_marked_converged():
    c = _conductor_with(
        lambda cand, rec: (_ for _ in ()).throw(
            _FixpointError("E_CONVERGED", "hashes identically to v1")))
    rec = RoundRecord(round_index=1)

    assert c._promote_or_converge({}, rec) is False
    assert rec.gate_decision == "CONVERGED"
    assert "identically" in rec.gate_detail


def test_a_converged_round_is_not_a_gate_rejection():
    """The distinction that matters. Two REJECTs halt the campaign, so a
    fixpoint miscounted as a rejection turns the success signal into
    HALT_GATE_REJECTED_TWICE."""
    c = _conductor_with(
        lambda cand, rec: (_ for _ in ()).throw(
            _FixpointError("E_CONVERGED", "nothing left to add")))
    rec = RoundRecord(round_index=1)
    c._promote_or_converge({}, rec)

    assert rec.gate_decision != "REJECT"


def test_any_other_promotion_failure_still_raises():
    """An automatic resume past a failed assertion is the fabrication the
    assertion exists to prevent. Only E_CONVERGED is absorbed."""
    c = _conductor_with(
        lambda cand, rec: (_ for _ in ()).throw(
            _FixpointError("E_WRONG_PROMOTER", "G8 tripping in code")))
    rec = RoundRecord(round_index=1)

    with pytest.raises(RuntimeError):
        c._promote_or_converge({}, rec)
    assert rec.gate_decision is None


def test_a_promoter_returning_true_is_untouched():
    c = _conductor_with(lambda cand, rec: True)
    rec = RoundRecord(round_index=1)
    assert c._promote_or_converge({}, rec) is True
    assert rec.gate_decision is None


def test_the_two_convergence_signals_are_distinct_values():
    """Same terminal status, different finding. DRY_ROUNDS means no breach was
    found; POLICY_FIXPOINT means one was found and the policy already covered
    it. Folding them into one word is E_NO_EVENTS in a new place."""
    assert CONVERGED_DRY_ROUNDS != CONVERGED_POLICY_FIXPOINT
    assert CONVERGED_DRY_ROUNDS and CONVERGED_POLICY_FIXPOINT
