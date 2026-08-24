"""The ARMORER gets more than one attempt at the benign floor, and it is bounded.

WHAT THE LIVE RUNS SHOWED, which is not "the ARMORER ignores feedback".

Run 1, 2026-08-23:

    r01  cap:CAP_MUTATES_DURABLE_STATE when derived.episode_count_same_subject > 1
         => deny                                     -> benign  5/26
    r02  same `when`, BYTE FOR BYTE, verb swapped
         => require_approval(...)                    -> benign 16/26
    then HALT_HUMAN_GATE_REJECTED_TWICE

The rejection feedback says "reconsider the verb before you touch the `when`",
and the ARMORER did exactly that, recovering eleven fixtures. The run then
halted on a process that was still converging.

Run 3, 2026-08-24, showed the other half: rounds 2-6 were DRY, a dry round skips
CORONER -> ARMORER entirely, so the ARMORER was called ONCE in a six-round run.
The feedback was computed, carried forward, and consumed by nothing. The run
"converged" with the hole still open and nothing promoted.

So the retry had to be bound to THE BREACH, not to the next round, and the
budget had to be bigger than two. Eric's ruling: "definitely extend the working
loop well beyond 2 attempts."

WHAT THESE TESTS PIN, and why each one can fail:

  1  the loop RETRIES within one round, and each retry carries the previous
     attempt's counts forward
  2  it STOPS at the declared budget - an unbounded loop is a search over the
     benign suite, and the budget is the leak control
  3  it STOPS EARLY when it stops improving, so a stuck loop does not spend the
     remaining budget re-learning the same thing
  4  it does NOT stop on a single sideways step, which is the case a naive
     monotonic check gets wrong and which run 1 would have tripped
  5  the TRAJECTORY is recorded, because "cannot narrow" and "was still
     converging when we stopped it" are different findings and run 1 was the
     second with nothing to show it
  6  a DSL-invalid patch keeps its own halt code, distinct from a floor failure
"""

import pytest

from crucible.conductor import conductor as C
from tests.test_conductor_loop import FAIL, PASS, StubArmorer, make


# ONE BREACHING ROUND, THEN DRY. `armorer.n` is cumulative across rounds, so a
# plan that breaches every round measures the ROUND loop and says nothing about
# narrowing. Three dry rounds also converge the run, so nothing depends on the
# round cap.
ONE_BREACH_THEN_DRY = [True, False, False, False]


def _scripted(*floors):
    """A benign gate that returns `floors` in order, then PASSes forever.

    The tail matters: the dry rounds after the breach never call the gate, but a
    plan that changes must not turn into a StopIteration that reads as a loop
    defect.
    """
    seq = list(floors)
    state = {"i": 0}

    def gate(_n):
        i = state["i"]
        state["i"] += 1
        return seq[i] if i < len(seq) else PASS
    return gate


def _floor(passed, total=24, near=12):
    return {"passed": passed, "total": total, "near_miss_passed": near,
            "near_miss_total": near,
            "failed_classes": ["CAP_MOVES_MONEY"] if passed < total else []}


class CountingArmorer(StubArmorer):
    """Records the `rejection_feedback` it was handed on every call."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.feedback_seen = []

    def propose(self, breach_record, current_policy, round_index,
                rejection_feedback=None):
        self.feedback_seen.append(rejection_feedback)
        return super().propose(breach_record, current_policy, round_index,
                               rejection_feedback=rejection_feedback)


# ---------------------------------------------------------------------------
# 1  IT RETRIES, AND THE FEEDBACK TRAVELS
# ---------------------------------------------------------------------------

def test_the_floor_failing_buys_another_attempt_in_the_same_round():
    """RED before this change: one ARMORER call per round, full stop."""
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(16), _floor(24))
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=6).run({})
    assert result.rounds[0].narrowing_attempts >= 3, (
        "the round made %d ARMORER attempt(s) with a floor that failed twice. "
        "The retry is still bound to the next round."
        % result.rounds[0].narrowing_attempts)


def test_each_retry_carries_the_previous_attempt_s_counts():
    """The first call has no feedback; every later one does, and it is COUNTS
    AND CLASSES - the shape `RejectionFeedback.__post_init__` enforces."""
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(16), _floor(24))
    make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
         armorer=armorer, narrowing_attempts=6).run({})
    assert armorer.feedback_seen[0] is None
    second = armorer.feedback_seen[1]
    assert second is not None and second.benign_failures == 24 - 5
    third = armorer.feedback_seen[2]
    assert third is not None and third.benign_failures == 24 - 16, (
        "the second retry was handed the FIRST attempt's numbers. Each attempt "
        "must report its own, or the ARMORER is narrowing against a stale count.")


# ---------------------------------------------------------------------------
# 2  IT IS BOUNDED - the leak control
# ---------------------------------------------------------------------------

def test_the_loop_stops_at_the_declared_budget():
    """An unbounded narrowing loop is a search over the benign suite. What the
    ARMORER can learn is (attempts x bits per signal), so the ATTEMPT COUNT is
    the control and it is declared rather than emergent."""
    armorer = CountingArmorer()
    # Strictly improving forever, so ONLY the budget can stop it.
    gate = lambda _n: _floor(1)   # never improves, never passes
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=4).run({})
    assert result.rounds[0].narrowing_attempts <= 4, result.rounds[0].narrowing_attempts


def test_the_shipped_budget_is_well_beyond_two():
    """Eric's ruling, 2026-08-24, pinned so a later 'tidy-up' cannot quietly
    restore the value that halted run 1 mid-convergence."""
    assert C.NARROWING_ATTEMPTS >= 6, C.NARROWING_ATTEMPTS


# ---------------------------------------------------------------------------
# 3 & 4  THE STALL STOP, AND THE CASE IT MUST NOT TRIP ON
# ---------------------------------------------------------------------------

def test_a_loop_that_stops_improving_stops_early():
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(5), _floor(5), _floor(5), _floor(5),
                   _floor(5), _floor(5), _floor(5))
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=6).run({})
    assert result.rounds[0].narrowing_attempts < 6, (
        "the loop spent its whole budget on a floor that never moved. A stuck "
        "loop is burning ARMORER calls and leak budget to re-learn one thing.")


def test_one_sideways_step_does_not_end_the_loop():
    """THE CASE A NAIVE MONOTONIC CHECK GETS WRONG.

    Requiring strict improvement every attempt would stop at the first plateau
    and throw away the runs that recover after it. Two consecutive
    non-improving attempts, not one.
    """
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(5), _floor(16), _floor(24))
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=6).run({})
    assert result.rounds[0].narrowing_attempts >= 4, (
        "the loop gave up on a plateau it then climbed out of. n=%d"
        % result.rounds[0].narrowing_attempts)


# ---------------------------------------------------------------------------
# 5  THE TRAJECTORY IS THE EVIDENCE
# ---------------------------------------------------------------------------

def test_the_round_records_every_floor_it_saw():
    """Run 1 went 5/26 -> 16/26 and was cut off, and NOTHING RECORDED THAT. A
    reader of that bundle cannot tell a loop that cannot narrow from one that
    was still converging when the budget ran out."""
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(16), _floor(24))
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=6).run({})
    record = result.rounds[0]
    assert record.benign_trajectory == [5, 16, 24], record.benign_trajectory
    assert record.narrowing_attempts == 3


def test_a_round_that_never_reaches_the_floor_says_how_far_it_got():
    armorer = CountingArmorer()
    gate = _scripted(_floor(5), _floor(9), _floor(9), _floor(9))
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
                  armorer=armorer, narrowing_attempts=6).run({})
    record = result.rounds[0]
    assert record.gate_decision == "REJECT"
    assert "trajectory" in record.halt_detail, record.halt_detail
    assert record.benign_trajectory[0] == 5


# ---------------------------------------------------------------------------
# 6  TWO FAILURES, TWO NAMES
# ---------------------------------------------------------------------------

def test_a_dsl_invalid_patch_keeps_its_own_halt_code():
    """`ARMORER_EXHAUSTED` means it could not spell the language.
    `ARMORER_CANNOT_NARROW` means it spelled it fine and kept over-blocking.
    Ruling 29: two failures sharing one name is how a gap survives."""
    armorer = StubArmorer(ok=False, halt="ARMORER_EXHAUSTED")
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=lambda n: PASS,
                  armorer=armorer, narrowing_attempts=6).run({})
    assert result.halt == "ARMORER_EXHAUSTED"
    assert armorer.n == 1, (
        "a patch that will not parse must not consume the narrowing budget - "
        "narrowing is about breadth and this one has no rule to narrow")
    assert C.HALT_ARMORER_CANNOT_NARROW != "ARMORER_EXHAUSTED"


def test_a_floor_that_holds_on_the_first_try_costs_one_call():
    """The loop must not add attempts to the happy path."""
    armorer = CountingArmorer()
    result = make(breach_plan=ONE_BREACH_THEN_DRY, benign=lambda n: PASS,
                  armorer=armorer, narrowing_attempts=6).run({})
    assert result.rounds[0].narrowing_attempts == 1, "the happy path grew attempts"
    assert result.rounds[0].gate_decision == "PROMOTE"


def test_every_attempt_survives_in_the_proposal_log():
    """`ProposalLog.by_round` was a dict assignment, so with a loop it kept only
    the LAST patch and the narrowing trajectory never reached the bundle. Same
    defect class as the deduped attack catalogue: keyed by something that
    stopped being unique the moment a loop was added."""
    from crucible.conductor.bundle import ProposalLog

    armorer = CountingArmorer()
    log = ProposalLog(armorer)
    gate = _scripted(_floor(5), _floor(16), _floor(24))
    make(breach_plan=ONE_BREACH_THEN_DRY, benign=gate,
         armorer=log, narrowing_attempts=6).run({})
    assert len(log.attempts_by_round[1]) == 3, log.attempts_by_round
    assert log.by_round[1] is log.attempts_by_round[1][-1]
