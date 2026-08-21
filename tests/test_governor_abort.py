"""The BUDGET_GOVERNOR's negative check. L5's first work item, part two.

`docs/lanes/L5-loop.md` section 4: "the governor aborts on a low ceiling and logs
the abort as a first-class result, NOT AN EXCEPTION."

WHY THAT DISTINCTION IS NOT STYLE
---------------------------------
The abort is a RESULT OF THE RUN. It goes in the round outcome, it goes in the
ledger, and it goes in the evidence bundle, because "the campaign stopped after
three rounds because it hit the spend cap" and "the campaign converged after
three rounds" are different findings that produce identical artifacts if the
first one leaves as a traceback.

CONVENTIONS 2.4 draws the same line between INVALID and FAILED: the absence of a
measurement is itself something that must be recorded, and no number from a run
that ended in an unhandled exception is trustworthy either.

Two checks, two strawmen:
  G1  the abort is RETURNED, never raised          -> `raising_governor`
  G2  the abort is RECORDED in the event log       -> `silent_governor`
"""

import dataclasses
import importlib
import json

import pytest

from crucible.governor import strawman as straw

# The ARMORER at medium thinking measured $0.0146/call in the day-1 spike
# (DECISION.md, 20 calls, $0.2913). A ceiling below one call is the cheapest
# possible way to reach the boundary without spending anything to get there.
ONE_ARMORER_CALL_USD = 0.0146


def _mod():
    return importlib.import_module("crucible.governor.governor")


def _low_ceiling_governor(governor_cls=None, budget_cls=None):
    mod = _mod()
    Budget = budget_cls or mod.Budget
    Governor = governor_cls or mod.BudgetGovernor
    budget = Budget(usd_cap=0.001, token_cap=40_000_000, round_cap=6,
                    call_cap=200)
    return Governor(budget)


# --------------------------------------------------------------------------
# G1 - the abort is a value
# --------------------------------------------------------------------------

def check_G1(governor):
    """Calling authorize past the ceiling RETURNS a refusal verdict."""
    verdict = governor.authorize("ARMORER", ONE_ARMORER_CALL_USD)
    assert verdict.allowed is False, (
        "G1: a governor with a $0.001 cap authorized a $0.0146 call.")
    assert verdict.code == _mod().HALT_BUDGET_EXHAUSTED
    # It has to survive the trip into a round outcome, so it has to be data.
    payload = dataclasses.asdict(verdict)
    assert json.loads(json.dumps(payload)) == payload, (
        "G1: the verdict is not serializable, so it cannot reach the ledger.")


def check_G2(governor):
    """The refusal is recorded as an event, not merely returned."""
    governor.authorize("ARMORER", ONE_ARMORER_CALL_USD)
    aborts = [e for e in governor.events if e.kind == "ABORT"]
    assert aborts, (
        "G2: the governor refused and recorded nothing. A run that stopped for "
        "a reason nobody recorded is indistinguishable from one that converged.")
    assert aborts[-1].code == _mod().HALT_BUDGET_EXHAUSTED
    assert aborts[-1].role == "ARMORER"


CHECKS = {"G1": check_G1, "G2": check_G2}


@pytest.mark.parametrize("check_id", sorted(CHECKS))
def test_real_governor_passes(check_id):
    CHECKS[check_id](_low_ceiling_governor())


def test_authorize_does_not_raise_even_at_zero_budget():
    """The property stated directly, with no ceremony around it. A governor that
    raises here fails by ERRORING this test rather than by asserting, which is a
    weaker signal - so G1 above checks the returned value as well."""
    mod = _mod()
    gov = mod.BudgetGovernor(mod.Budget(usd_cap=0.0, token_cap=0, round_cap=0,
                                        call_cap=0))
    verdict = gov.authorize("CORONER", 0.0001)
    assert verdict.allowed is False


def test_a_governor_under_the_ceiling_allows_and_records_the_charge():
    """The positive half. Without it, a governor hard-wired to `allowed=False`
    would pass every check above."""
    mod = _mod()
    gov = mod.BudgetGovernor(mod.Budget(usd_cap=1.00, token_cap=1_000_000,
                                        round_cap=6, call_cap=10))
    assert gov.authorize("ARMORER", ONE_ARMORER_CALL_USD).allowed is True
    gov.record("ARMORER", usd=ONE_ARMORER_CALL_USD, tokens=51_000)
    assert gov.spent_usd == pytest.approx(ONE_ARMORER_CALL_USD)
    assert gov.tokens_used == 51_000
    assert gov.calls_made == 1


def test_each_ceiling_has_its_own_code():
    """Four ceilings, four codes. One generic HALT would make the evidence
    bundle unable to say WHICH limit ended the run, which is the same defect as
    not recording it at all."""
    mod = _mod()
    cases = [
        (mod.Budget(usd_cap=0.0, token_cap=10**9, round_cap=6, call_cap=10),
         mod.HALT_BUDGET_EXHAUSTED),
        (mod.Budget(usd_cap=100.0, token_cap=0, round_cap=6, call_cap=10),
         mod.HALT_TOKEN_CEILING),
        (mod.Budget(usd_cap=100.0, token_cap=10**9, round_cap=6, call_cap=0),
         mod.HALT_CALL_CAP),
    ]
    for budget, expected in cases:
        gov = mod.BudgetGovernor(budget)
        verdict = gov.authorize("ARMORER", 0.01, estimated_tokens=1000)
        assert verdict.allowed is False
        assert verdict.code == expected, (
            "expected %s, got %s" % (expected, verdict.code))


def test_round_cap_is_six_and_is_its_own_refusal():
    """CONVENTIONS ruling 10: the round cap is SIX, raised from four because at
    a cap of four with three-consecutive-dry convergence only round one could be
    productive - a formality rather than a criterion."""
    mod = _mod()
    gov = mod.BudgetGovernor(mod.Budget(usd_cap=100.0, token_cap=10**9,
                                        round_cap=6, call_cap=1000))
    for _ in range(6):
        assert gov.open_round().allowed is True
    verdict = gov.open_round()
    assert verdict.allowed is False
    assert verdict.code == mod.HALT_ROUND_CAP


# --------------------------------------------------------------------------
# The meta-check
# --------------------------------------------------------------------------

_STRAW_CASES = [
    (name, check_id)
    for name in sorted(straw.STRAWMEN)
    for check_id in sorted(CHECKS)
]


@pytest.mark.parametrize("name,check_id", _STRAW_CASES)
def test_strawman_fails_exactly_what_it_declared(name, check_id):
    mod = _mod()
    factory, must_fail = straw.STRAWMEN[name]
    cls = factory(mod.Budget, mod.BudgetGovernor)
    declared = check_id in must_fail
    try:
        CHECKS[check_id](_low_ceiling_governor(governor_cls=cls))
    except AssertionError:
        failed = True
    except Exception:
        failed = True          # raising_governor gets here, which IS the defect
    else:
        failed = False

    if declared and not failed:
        pytest.fail(
            "THE SUITE IS BROKEN, not the strawman. %s declared it must fail "
            "%s (%s) and it passed." % (name, check_id, must_fail[check_id]))
    if failed and not declared:
        pytest.fail(
            "%s failed %s, which it did not declare. Name it or fix it; do not "
            "absorb it." % (name, check_id))


# --------------------------------------------------------------------------
# The accounting hole this lane put in and then found in its own campaign
# --------------------------------------------------------------------------

def test_every_model_role_charges_the_governor():
    """FOUND BY READING A REAL SPEND FIGURE, NOT BY A TEST.

    The first live campaign fired ~26 model calls across three roles and reported
    $0.0141 - almost exactly one ARMORER call. The RED_STRATEGIST and the CORONER
    both TOOK a governor and neither called `record`, so two of the three roles
    were free as far as the cap was concerned.

    That is the defect CONVENTIONS section 12 finding 8 already names in the
    original cost model - "cost is understated ~10x", and "the ledger has no line
    for benign or known-bad fixture episodes". A governor that under-counts is
    worse than no governor: it produces a spend figure that looks like a
    measurement and licenses a run somebody thinks is affordable.

    Asserted per role, so a fourth role added later without wiring fails here.
    """
    from crucible.coroner import Coroner
    from crucible.governor import governor as gmod
    from crucible.red import AttackSeed, RedStrategist

    def stub(*, system, user, model, thinking_level):
        return {"text": '{"instruction": "x", "narrative": "y"}',
                "usd": 0.005, "tokens": 1000}

    gov = gmod.BudgetGovernor(gmod.Budget(usd_cap=10.0, token_cap=10 ** 9,
                                          round_cap=6, call_cap=100))

    RedStrategist(stub, seed=0, governor=gov).vary(
        AttackSeed("atk_a", "fam_a", "x"), None)
    assert gov.calls_made == 1, "the RED_STRATEGIST did not charge the governor"

    Coroner(stub, governor=gov).narrate(
        {"invariant_id": "inv_x", "capability_classes_involved": [],
         "offending_tool_calls": []})
    assert gov.calls_made == 2, "the CORONER did not charge the governor"

    assert gov.spent_usd == pytest.approx(0.010)
    assert {e.role for e in gov.events if e.kind == "CHARGE"} == {
        "RED_STRATEGIST", "CORONER"}


def test_a_refused_role_degrades_rather_than_raising():
    """Both roles must survive a ceiling as a DEGRADATION, not an exception. The
    CORONER loses its prose and keeps its record; the RED_STRATEGIST replays its
    seed and labels the round."""
    from crucible.coroner import Coroner
    from crucible.governor import governor as gmod
    from crucible.red import AttackSeed, RedStrategist

    def stub(*, system, user, model, thinking_level):   # pragma: no cover
        raise AssertionError("nothing should be called past the ceiling")

    gov = gmod.BudgetGovernor(gmod.Budget(usd_cap=0.0, token_cap=10 ** 9,
                                          round_cap=6, call_cap=100))
    out = RedStrategist(stub, seed=0, governor=gov).vary(
        AttackSeed("atk_a", "fam_a", "seed text"), None)
    assert out["variation"] == "governor_refused"
    assert out["instruction"] == "seed text"

    human_only, dropped, usd, tokens = Coroner(stub, governor=gov).narrate(
        {"invariant_id": "inv_x", "capability_classes_involved": [],
         "offending_tool_calls": []})
    assert human_only == {} and usd == 0.0
