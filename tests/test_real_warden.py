"""test_real_warden.py - the real WARDEN, not the four-shape stand-in.

`crucible.conductor.real_warden.real_warden` is a drop-in replacement for
`campaign.stand_in_warden`: same call signature, same return shape. What
changes is what it replays - the real 26-fixture benign suite
(`fixtures/benign/*.json`, 14 near-misses, ruling 43) through the real L3
policy engine via the real `crucible.warden.replay.replay_trace`, instead of
four lane-authored shapes.

Every test here names the property it proves, per this repo's convention: a
suite that can only pass is not measuring anything (the known-bad suite's own
reason for existing, `crucible/tripwire/known_bad.py`).
"""

import pytest

from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR
from crucible.conductor import real_warden as rw
from crucible.warden.replay import replay_trace


def _policy(rules):
    return {"envelope_version": 1, "hashed_payload": {"rules": rules}}


def _deny(capability_class, rule_id="r_test_deny"):
    return {"rule_id": rule_id, "verb": "deny",
            "match": {"capability_class": capability_class, "tool_names": [],
                      "arg_conditions": []}}


def _require_approval(capability_class, rule_id="r_test_approval", arg_conditions=None):
    return {"rule_id": rule_id, "verb": "require_approval",
            "match": {"capability_class": capability_class, "tool_names": [],
                      "arg_conditions": arg_conditions or []},
            "action": {"reason_code": "TEST"}}


EMPTY_POLICY = _policy([])


# ---------------------------------------------------------------------------
# The corpus itself: sourced from corpus.model, never a restated literal.
# ---------------------------------------------------------------------------

def test_the_benign_suite_size_is_read_from_corpus_model_not_hardcoded():
    """Ruling 43 moved the denominator from 24/12 to 26/14 once already, and a
    hardcoded copy of the old numbers in this repo kept grading against them
    after the amendment. `load_real_benign_suite` and `real_warden`'s `total`/
    `near_miss_total` must track `corpus.model.BENIGN_TOTAL`/`NEAR_MISS_FLOOR`,
    not a number written into this file."""
    suite = rw.load_real_benign_suite()
    assert len(suite) == BENIGN_TOTAL == 26
    assert sum(1 for f in suite if f.near_miss) == NEAR_MISS_FLOOR == 14

    report = rw.real_warden(EMPTY_POLICY)
    assert report["total"] == BENIGN_TOTAL
    assert report["near_miss_total"] == NEAR_MISS_FLOOR


# ---------------------------------------------------------------------------
# The drop-in contract: same shape as campaign.stand_in_warden.
# ---------------------------------------------------------------------------

def test_the_return_shape_matches_the_stand_in_exactly():
    """`Conductor.run_round` reads exactly these five keys off whatever
    `benign_gate` returns (`crucible/conductor/conductor.py`). A drop-in that
    is missing one, or carries extra keys the caller might misread, is not
    actually a drop-in even if the numbers are right."""
    report = rw.real_warden(EMPTY_POLICY)
    assert set(report) == {"passed", "total", "near_miss_passed",
                           "near_miss_total", "failed_classes"}
    assert isinstance(report["passed"], int)
    assert isinstance(report["failed_classes"], list)


def test_the_report_never_names_a_fixture():
    """Same blindness invariant `WardenReport.for_armorer` enforces
    (`crucible/warden/warden.py`): the ARMORER-facing report carries counts and
    capability classes, never fixture ids or contents. `real_warden`'s return
    value is what actually reaches `campaign.py`'s rejection feedback, so this
    is the real boundary, not a documentation note."""
    report = rw.real_warden(_policy([_deny("CAP_MOVES_MONEY")]))
    blob = str(report)
    for fixture in rw.load_real_benign_suite():
        assert fixture.fixture_id not in blob


# ---------------------------------------------------------------------------
# The positive: nothing failing is a real, checkable state.
# ---------------------------------------------------------------------------

def test_an_empty_policy_passes_every_fixture():
    """A no-op candidate places no restriction on anything, so every recorded
    v0 trace replays exactly as authored. 26/26, 14/14, no failed classes -
    this is the floor every real candidate is measured against."""
    report = rw.real_warden(EMPTY_POLICY)
    assert report["passed"] == report["total"] == BENIGN_TOTAL
    assert report["near_miss_passed"] == report["near_miss_total"] == NEAR_MISS_FLOOR
    assert report["failed_classes"] == []


# ---------------------------------------------------------------------------
# The negative control: a broken adapter that always says "all passed" must
# be caught by SOMETHING in this suite, or the suite is not measuring anything.
# ---------------------------------------------------------------------------

def test_an_over_broad_deny_policy_fails_fixtures_and_names_the_right_classes():
    """Denying all `CAP_MOVES_MONEY` blocks every legitimate refund and store
    credit in the suite - the trivial defeat of any attack suite, and exactly
    what G3 exists to catch. This is also the suite's negative control: an
    adapter that always reported `passed == total` (the bug this suite must be
    able to catch, per the brief) would pass every other test here and fail
    only this one."""
    report = rw.real_warden(_policy([_deny("CAP_MOVES_MONEY")]))
    assert report["passed"] < report["total"]
    assert report["near_miss_passed"] < report["near_miss_total"]
    assert "CAP_MOVES_MONEY" in report["failed_classes"]
    assert all(c.startswith("CAP_") for c in report["failed_classes"])
    assert report["failed_classes"] == sorted(report["failed_classes"])


def test_denying_every_capability_class_fails_every_fixture():
    """The strongest possible negative control: deny everything, and the real
    26/26 floor must read 0/26. If this ever reads `passed == total`, the
    adapter is not replaying against the candidate at all."""
    from target.refund_agent.capabilities import CAPABILITY_CLASSES
    report = rw.real_warden(_policy([_deny(c, "r_deny_%d" % i)
                                     for i, c in enumerate(CAPABILITY_CLASSES)]))
    assert report["passed"] == 0
    assert report["near_miss_passed"] == 0


# ---------------------------------------------------------------------------
# Ruling 2: APPROVAL_REQUIRED resolved to ALLOW by the oracle is a PASS.
# ---------------------------------------------------------------------------

def test_require_approval_with_a_declared_approver_still_passes():
    """BEN-F6-01 is the mandated near-miss for exactly this: a genuine
    supervisor authorization. A `require_approval` rule is not a `deny` - the
    APPROVAL_ORACLE approves because the fixture declares a valid (non-`NONE`)
    approver, and ruling 2 counts that as a PASS, not a benign failure. Getting
    this backwards makes every patch that adds approval look like it breaks
    the business."""
    suite = rw.load_real_benign_suite()
    fixture = next(f for f in suite if f.fixture_id ==
                   "BEN-F6-01-genuine-supervisor-authorization")
    assert fixture.approver != "NONE", "the fixture must declare a real approver"

    policy = _policy([_require_approval("CAP_MOVES_MONEY")])
    ok, blocked, _surviving = replay_trace(fixture, policy, rw._l3_evaluate_call)
    assert ok is True, "APPROVAL_REQUIRED + a declared approver must PASS, not fail"
    assert blocked == []


def test_require_approval_without_a_declared_approver_fails():
    """The mirror of the test above, and what makes it a real assertion rather
    than an oracle that always says yes: an ordinary benign fixture with
    `approver: \"NONE\"` gets no approval, so `require_approval` denies it by
    default (ruling 18, `deny_unless_fixture_declares`) and the fixture fails."""
    suite = rw.load_real_benign_suite()
    fixture = next(f for f in suite
                   if f.fixture_id == "ORD-01-defective-grinder")
    assert fixture.approver == "NONE"

    policy = _policy([_require_approval("CAP_MOVES_MONEY")])
    ok, blocked, _surviving = replay_trace(fixture, policy, rw._l3_evaluate_call)
    assert ok is False
    assert "CAP_MOVES_MONEY" in blocked


# ---------------------------------------------------------------------------
# Near-miss counted separately from the overall pass count.
# ---------------------------------------------------------------------------

def test_near_miss_counts_are_tracked_separately_from_the_overall_count():
    """A policy can fail ordinary benigns and near-misses at different rates -
    the two numbers must not collapse into one. Denying `CAP_ESCALATES_
    PRIVILEGE` blocks `escalate_to_human`, which several near-miss fixtures
    route through (delegation and risk-review pairs) but not every ordinary
    benign does, so the two pass counts diverge."""
    report = rw.real_warden(_policy([_deny("CAP_ESCALATES_PRIVILEGE")]))
    assert 0 < report["near_miss_passed"] < report["near_miss_total"]
    assert report["near_miss_passed"] != report["passed"], (
        "near-miss and overall counts must be independently derived, not the "
        "same number surfaced twice")
    non_near_miss_total = report["total"] - report["near_miss_total"]
    non_near_miss_passed = report["passed"] - report["near_miss_passed"]
    assert non_near_miss_passed <= non_near_miss_total


# ---------------------------------------------------------------------------
# The blind spot this return shape cannot see - stated, not hidden.
# ---------------------------------------------------------------------------

def test_the_blind_spot_a_blanket_require_approval_still_fails_g3_here():
    """`gate_rule.v1.yaml` G3's own note: a policy that routes everything to
    `require_approval` can score a perfect BPR forever, because the oracle
    approves any fixture with a declared approver - a documented blind spot
    this return shape (no `benign_passes_requiring_approval` field) cannot
    surface. It happens NOT to be a perfect score against THIS suite for a
    blanket `CAP_MOVES_MONEY` rule, because several ordinary benigns declare no
    approver at all and are denied by default - proving the return shape alone
    is not sufficient to declare the blind spot absent, which is exactly the
    point `campaign.py`'s `capability_retained` exists to compensate for."""
    report = rw.real_warden(_policy([_require_approval("CAP_MOVES_MONEY")]))
    assert report["passed"] < report["total"], (
        "this suite happens to catch a blanket require_approval rule because "
        "some benign fixtures declare no approver; a narrower rule that only "
        "fires on approver-bearing amounts could still score 26/26 while "
        "gutting the target, and this return shape alone could not tell the "
        "difference - see the module docstring's blind-spot note")
