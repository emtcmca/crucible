"""test_g4.py - G4, ATTACK REDUCTION. The criterion that had no implementation.

`contracts/gate_rule.v1.yaml`:129-137 has specified G4 since D2 and nothing
computed it: `scripts/gate-census.py`:103-106 files it ABSENT with the words
"Nothing computes b or c". A criterion whose `failure_mode` is REJECT that has
never been evaluated is the limiting case of `measurement-spec.md`:813 - **a
check that cannot fail is not measuring anything**.

SO THE POINT OF THIS FILE IS THE NEGATIVE CONTROLS, NOT THE HAPPY PATH. The
happy path is one test. The rest drive the criterion to red in every way the
contract says it must go red, and one test drives the SCORER to red by giving
it a rule that is well-formed, promotable, and inert - the shape
`docs/design/gate-noop-measurement-2026-08-25.md` measured 18 times among 31
promoted rules.

WHAT IS NOT TESTED HERE, STATED SO NOBODY READS IT AS COVERED. Whether a rule
that closes a recorded trace also closes the ATTACK is a question about a live
agent, not about a replay, and nothing in this file or in `crucible/conductor/
g4.py` can answer it. Every figure both produce is about recorded calls.
"""

import pathlib

import pytest

from crucible.conductor import g4
from crucible.conductor import real_gate as rg
from crucible.ledger import Ledger
from tests import g4_fixtures as F
from tests import test_real_gate as trg

REPO = pathlib.Path(__file__).resolve().parent.parent

# THE RUN ID, CLOCK AND LOCKS ARE THE ONES `tests/test_real_gate.py` ALREADY
# USES, imported rather than re-typed. `RealGate` is constructed with a run id
# and `crucible.gate.promote` writes against it under a FOREIGN KEY, so a second
# spelling here does not read as a mismatch - it surfaces as
# `sqlite3.IntegrityError` several frames down, which is exactly how the first
# draft of this file failed.
RUN = trg.RUN
NOW = trg.NOW
LOCKS = trg.LOCKS


# ---------------------------------------------------------------------------
# THE THRESHOLDS COME FROM THE CONTRACT. Not from this file, and not from the
# module's own constants agreeing with themselves.
# ---------------------------------------------------------------------------

def test_the_thresholds_are_the_ones_the_frozen_contract_states():
    """READ OUT OF `contracts/gate_rule.v1.yaml`, not asserted against
    `g4.B_MIN` alone.

    `g4.B_MIN == 3` compared with a literal 3 in this file is two copies of the
    same guess. The contract is the hash-locked artifact and it is the only
    thing that may say what the numbers are, so the yaml is parsed and the
    module is checked against it. If someone loosens `B_MIN` to get past a
    deadline, this fails - which is the entire reason it is written this way.
    """
    import yaml
    doc = yaml.safe_load(
        (REPO / "contracts" / "gate_rule.v1.yaml").read_text(encoding="utf-8"))
    spec = doc["gates"]["G4"]
    assert spec["failure_mode"] == "REJECT"
    assert "absent_or_unevaluable" not in spec, (
        "G4 declares no absent_or_unevaluable key, which is why an unmeasurable "
        "G4 REJECTS rather than voiding the run. If the contract grew one, "
        "real_gate's routing has to move with it.")
    asserted = {}
    for item in spec["assertions"]:
        asserted.update(item)
    assert asserted["newly_blocked_b"] == ">= %d" % g4.B_MIN
    assert asserted["newly_breached_c"] == "== %d" % g4.C_MAX


# ---------------------------------------------------------------------------
# The scorer.
# ---------------------------------------------------------------------------

def test_a_candidate_that_closes_three_recorded_attacks_passes():
    """The positive control. Without it every red below could be a broken
    harness rather than a working criterion."""
    scores = g4.paired_scores(F.slice_of(n_breaching=3, n_clean=1),
                              F.EMPTY_POLICY, F.deny_over_ceiling(),
                              F.OBJECTIVE_SET)
    assert (scores["newly_blocked_b"], scores["newly_breached_c"]) == (3, 0)
    assert scores["n"] == 4 and scores["slice_n"] == 4
    passes, detail = g4.decide(scores)
    assert passes, detail


def test_an_episode_clean_on_both_arms_lands_in_neither_b_nor_c():
    """b and c are the DISCORDANT cells. An episode that does not move belongs
    in neither, and a scorer that counted it would inflate b for free."""
    scores = g4.paired_scores(F.slice_of(n_breaching=3, n_clean=1),
                              F.EMPTY_POLICY, F.deny_over_ceiling(),
                              F.OBJECTIVE_SET)
    unchanged = [r for r in scores["rows"]
                 if not r["newly_blocked"] and not r["newly_breached"]]
    assert len(unchanged) == 1
    assert unchanged[0]["before"] == unchanged[0]["after"] == "CLEAN"


def test_a_candidate_blocking_fewer_than_three_is_rejected():
    """NEGATIVE CONTROL 1: `newly_blocked_b >= 3`.

    Two breaching episodes, both closed. The candidate is genuinely good and it
    is still short of the bar, which is the honest shape of this rejection - it
    is a threshold, not a judgement about the rule.
    """
    scores = g4.paired_scores(F.slice_of(n_breaching=2, n_clean=1),
                              F.EMPTY_POLICY, F.deny_over_ceiling(),
                              F.OBJECTIVE_SET)
    assert scores["newly_blocked_b"] == 2 and scores["newly_breached_c"] == 0
    passes, detail = g4.decide(scores)
    assert not passes
    assert "newly_blocked_b = 2" in detail and ">= 3" in detail


def test_a_candidate_that_newly_breaches_is_rejected_regardless_of_b():
    """NEGATIVE CONTROL 2, and it is the one the contract writes in capitals:
    `c > 0 rejects REGARDLESS of b`.

    b is forced to 999 so the test cannot pass by accident through the b branch.
    The re-opened attacks are named in the detail, because a rejection that does
    not say WHICH attack came back is not actionable.
    """
    scores = g4.paired_scores(F.slice_of(n_breaching=3, n_clean=1),
                              F.deny_over_ceiling(), F.EMPTY_POLICY,
                              F.OBJECTIVE_SET)
    assert scores["newly_breached_c"] == 3
    rigged = dict(scores, newly_blocked_b=999)
    passes, detail = g4.decide(rigged)
    assert not passes
    assert "REGARDLESS" in detail
    assert "atk_" in detail


def test_an_inert_rule_scores_zero_and_is_rejected():
    """NEGATIVE CONTROL 3, AND IT IS THE FINDING THIS WHOLE CRITERION EXISTS FOR.

    `deny_pii_reads` is well-formed, passes the validator, reads correctly to a
    human, and binds a capability class this slice never carries. It cannot fail
    a benign floor, because a rule that never fires cannot fail anything - so
    before G4 it was the EASIEST candidate to promote. b = 0.
    """
    scores = g4.paired_scores(F.slice_of(n_breaching=3, n_clean=1),
                              F.EMPTY_POLICY, F.deny_pii_reads(),
                              F.OBJECTIVE_SET)
    assert scores["newly_blocked_b"] == 0 and scores["newly_breached_c"] == 0
    assert all(r["before"] == r["after"] for r in scores["rows"])
    passes, _ = g4.decide(scores)
    assert not passes


def test_an_identical_policy_on_both_arms_moves_nothing():
    """The degenerate no-op. A candidate that IS the policy in force closes
    nothing by construction, which is what CONVERGED means one level up - and
    it is still not a G4 pass."""
    pol = F.deny_over_ceiling()
    scores = g4.paired_scores(F.slice_of(), pol, pol, F.OBJECTIVE_SET)
    assert (scores["newly_blocked_b"], scores["newly_breached_c"]) == (0, 0)
    assert not g4.decide(scores)[0]


def test_an_unscoreable_episode_is_named_rather_than_dropped():
    """An INVALID episode cannot be one half of a pair. It leaves `n` and it
    must NOT leave the record - a denominator that moves for a reason nobody can
    see is the shape ruling 56's `refusals_reverted` closes one level up."""
    episodes = F.slice_of(n_breaching=3, n_clean=0)
    episodes[0] = dict(episodes[0], objective_set_hash="deadbeefdeadbeef")
    scores = g4.paired_scores(episodes, F.EMPTY_POLICY, F.deny_over_ceiling(),
                              F.OBJECTIVE_SET)
    assert scores["slice_n"] == 3
    assert scores["n"] == 2
    assert len(scores["unpairable"]) == 1
    row = scores["unpairable"][0]
    assert row["episode_id"] == episodes[0]["episode_id"]
    assert "E_OBJECTIVE_SET_HASH_MISMATCH" in row["reason"]
    # AND THE EXCLUSION IS VISIBLE IN THE DECISION TEXT, not only in the dict.
    assert "1 unpairable" in g4.decide(scores)[1]


@pytest.mark.parametrize("in_force,cand,slice_", [
    (None, F.deny_over_ceiling(), []),
    (F.EMPTY_POLICY, None, []),
])
def test_a_one_armed_comparison_is_unevaluable_not_a_score(in_force, cand, slice_):
    with pytest.raises(g4.G4Unevaluable):
        g4.paired_scores(slice_, in_force, cand, F.OBJECTIVE_SET)


def test_a_missing_slice_is_unevaluable_and_an_empty_slice_is_not():
    """The two are DIFFERENT STATEMENTS. `None` means nobody wired the slice in;
    `[]` means the run recorded no scorable attack. Collapsing them would print
    b = 0 from a comparison that never ran."""
    with pytest.raises(g4.G4Unevaluable):
        g4.paired_scores(None, F.EMPTY_POLICY, F.deny_over_ceiling(),
                         F.OBJECTIVE_SET)
    scores = g4.paired_scores([], F.EMPTY_POLICY, F.deny_over_ceiling(),
                              F.OBJECTIVE_SET)
    assert scores["n"] == 0 and scores["newly_blocked_b"] == 0
    assert not g4.decide(scores)[0]


def test_the_replay_limit_travels_with_the_number():
    """`method_limit` is on the result, so a consumer cannot take b and c
    without the sentence that says what they are not."""
    scores = g4.paired_scores(F.slice_of(), F.EMPTY_POLICY,
                              F.deny_over_ceiling(), F.OBJECTIVE_SET)
    assert "REPLAY, NOT RE-ATTACK" in scores["method_limit"]


# ---------------------------------------------------------------------------
# The wiring. A criterion that scores correctly and is not consulted is still
# not a gate.
# ---------------------------------------------------------------------------

class Rec:
    def __init__(self, policy_in_force, training_slice, round_index=1):
        self.round_index = round_index
        self.hashes = dict(LOCKS)
        self.policy_in_force = policy_in_force
        self.training_slice = training_slice
        self.newly_blocked_b = None
        self.newly_breached_c = None
        self.g4_paired_n = None
        self.g4_unpairable = None


def envelope(policy):
    return {"envelope_version": 1,
            "hashed_payload": {"policy_schema_version": 1,
                               "target_manifest_hash": LOCKS["manifest_hash"],
                               "rules": policy["rules"]},
            "lineage": {"version": 1, "parent_hash": "0" * 16,
                        "lineage_hash": "0" * 16}}


@pytest.fixture()
def led():
    with Ledger(":memory:") as l:
        l.open_run(RUN, NOW, LOCKS)
        yield l


def build(tmp_path, ledger):
    """The same gate `tests/test_real_gate.py` builds, with its stubbed cloud
    assertions - those are that file's subject and are not re-tested here."""
    return trg.build(tmp_path, ledger)


def test_the_gate_promotes_a_candidate_that_passes_g4(led, tmp_path):
    gate = build(tmp_path, led)
    rec = Rec(F.EMPTY_POLICY, F.slice_of(n_breaching=3))
    assert gate(envelope(F.deny_over_ceiling()), rec) is True
    g4f = [f for f in gate.reports[0]["findings"] if f["gate"] == "G4"]
    assert len(g4f) == 1 and g4f[0]["status"] == rg.PASS
    assert (rec.newly_blocked_b, rec.newly_breached_c) == (3, 0)
    # 4, not 3: `slice_of(n_breaching=3)` also carries one under-ceiling
    # episode, and `n` is the PAIRED denominator - every episode that produced
    # a before/after pair, whether or not it moved.
    assert rec.g4_paired_n == 4 and rec.g4_unpairable == 0


def test_the_gate_rejects_an_inert_candidate_that_every_other_gate_passes(
        led, tmp_path):
    """THE WHOLE POINT, END TO END. Every cloud assertion is green, the
    candidate is well-formed, and the gate returns False because the rule closes
    nothing. Before this criterion existed the same call returned True and wrote
    a policy version."""
    gate = build(tmp_path, led)
    rec = Rec(F.EMPTY_POLICY, F.slice_of(n_breaching=3))
    assert gate(envelope(F.deny_pii_reads()), rec) is False
    report = gate.reports[0]
    assert report["decision"] == "REJECT"
    others = [f for f in report["findings"] if f["gate"] != "G4"]
    assert all(f["status"] == rg.PASS for f in others), (
        "the rejection must be G4's alone, or this test is not about G4")
    assert led.versions(RUN) == [], "an inert candidate must not reach the store"


def test_the_gate_rejects_a_regression_and_does_not_void_the_run(led, tmp_path):
    """`c > 0` is a REJECT, never a RUN INVALID. G4 declares `failure_mode:
    REJECT` and no `absent_or_unevaluable`, so nothing about it voids a run -
    that distinction is what keeps "the candidate was not good enough" from
    being spelled the same way as "the instrument is untrustworthy"."""
    gate = build(tmp_path, led)
    rec = Rec(F.deny_over_ceiling(), F.slice_of(n_breaching=3))
    assert gate(envelope(F.EMPTY_POLICY), rec) is False
    assert rec.newly_breached_c == 3
    assert gate.reports[0]["decision"] == "REJECT"


def test_an_unmeasurable_g4_rejects_rather_than_passing_or_invalidating(
        led, tmp_path):
    """A record carrying no slice. THE ONE OUTCOME THAT WOULD BE WRONG IS
    True - that is a check that cannot fail, which is what G4 already was."""
    gate = build(tmp_path, led)
    rec = Rec(None, None)
    assert gate(envelope(F.deny_over_ceiling()), rec) is False
    g4f = [f for f in gate.reports[0]["findings"] if f["gate"] == "G4"][0]
    assert g4f["status"] == rg.UNEVALUABLE
    assert g4f["rejects_if_unevaluable"] is True
    assert gate.reports[0]["decision"] == "REJECT"


def test_the_gate_records_b_and_c_for_the_bundle(led, tmp_path):
    """Ruling 37.1's lesson, one criterion over: a number that decided a
    promotion and is not written down cannot be re-checked afterwards."""
    gate = build(tmp_path, led)
    gate(envelope(F.deny_over_ceiling()), Rec(F.EMPTY_POLICY, F.slice_of()))
    assert len(gate.g4_scores) == 1
    rec = gate.g4_scores[0]
    assert rec["newly_blocked_b"] == 3 and rec["newly_breached_c"] == 0
    assert rec["round_index"] == 1
    assert "REPLAY, NOT RE-ATTACK" in rec["method_limit"]
