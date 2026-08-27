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

from crucible.conductor import closure
from crucible.conductor import g4
from crucible.conductor import real_gate as rg
from crucible.ledger import Ledger
from tests import closure_fixtures as CF
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

def test_the_contract_still_declares_the_shape_the_routing_depends_on():
    """THE THRESHOLD HALF OF THIS TEST BECAME A TAUTOLOGY ON 2026-08-26 AND IS
    RECORDED HERE RATHER THAN QUIETLY DROPPED.

    It used to end by asserting `asserted["newly_blocked_b"] == ">= %d" %
    g4.B_MIN`, and while `B_MIN` was a literal in `g4.py` that caught a
    hand-edited threshold. `B_MIN` is now READ from this same yaml, so the two
    sides of that comparison have one source: it is the file against itself and
    it cannot fail. Leaving it would be a check that cannot fail sitting inside
    the suite whose job is to refuse those.

    THE REPLACEMENT IS STRICTLY STRONGER and lives in
    `tests/test_g4_baseline.py::
    test_the_reader_actually_reads_and_a_hardcoded_literal_could_not_pass`: it
    points `contract_g4` at a DIFFERENT contract file and requires the bounds to
    move. A hardcoded literal fails that, and so does a reader that swallows an
    unreadable file and defaults.

    WHAT STAYS HERE IS NOT VACUOUS. `failure_mode: REJECT` and the ABSENCE of
    `absent_or_unevaluable` are the two facts `real_gate`'s routing is built on,
    and neither is derived from the module - the module has no opinion about
    either. If the contract grew an `absent_or_unevaluable` key, an unmeasurable
    G4 would have to stop rejecting and start voiding the run, and this is what
    notices.
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
    # Both assertions must still EXIST and still be parseable. This is a shape
    # check, not a value check - the values have exactly one owner now.
    assert set(asserted) == {"newly_blocked_b", "newly_breached_c"}
    assert g4._parse_threshold(asserted["newly_blocked_b"])[0] in ("gte", "gt")
    assert g4._parse_threshold(asserted["newly_breached_c"])[0] == "eq"


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
        # ORIGINATING-BREACH CLOSURE's inputs, added 2026-08-26. THIS FILE'S
        # SUBJECT IS G4. The default pair is one every candidate built here
        # closes, so a closure rejection can never be mistaken for a G4 one;
        # `tests/test_closure_gate.py` owns every assertion about closure, and
        # two files asserting one criterion is how one of them goes stale
        # without failing.
        self.originating_episode = CF.episode()
        self.originating_autopsy = CF.autopsy(self.originating_episode)
        self.closure_closed = None
        self.closure_code = None
        self.closure_clause_id = None
        self.closure_episode_still_breaches = None
        self.closure_mode = None
        self.closure_record_only_reason = ""


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


# THIS FILE'S SUBJECT IS G4, SO CLOSURE IS OBSERVED HERE AND NOT ENFORCED.
#
# Originating-breach closure (2026-08-26) is a SECOND candidate-dependent
# criterion on the same gate, and it rejects the same inert candidate G4 does -
# correctly, and for a different reason. Left enforcing, three tests below would
# go green or red on closure's verdict while claiming to be about attack
# reduction, and `test_the_gate_rejects_an_inert_candidate_that_every_other_
# gate_passes` could not say "the rejection must be G4's alone" at all.
#
# THE REASON IS STATED BECAUSE RECORD_ONLY REFUSES TO BE SELECTED WITHOUT ONE,
# and that refusal is the point: a criterion that is scored and not enforced is
# a promotion nothing gated. `tests/test_closure_gate.py` owns every assertion
# about closure, INCLUDING that closure's own record-only mode never suppresses
# G4. Two files asserting one criterion is how one of them goes stale without
# failing.
CLOSURE_OFF = ("this file's subject is G4; tests/test_closure_gate.py owns "
               "originating-breach closure")


def build(tmp_path, ledger, **over):
    """The same gate `tests/test_real_gate.py` builds, with its stubbed cloud
    assertions - those are that file's subject and are not re-tested here."""
    kwargs = dict(closure_mode=closure.RECORD_ONLY,
                  closure_record_only_reason=CLOSURE_OFF)
    kwargs.update(over)
    return trg.build(tmp_path, ledger, **kwargs)


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
    # CLOSURE IS EXCLUDED BY NAME, not by accident. It is RECORDED here (see
    # `CLOSURE_OFF`), and RECORDED is neither a pass nor a rejection - so
    # asserting `== PASS` over it would fail for a reason that has nothing to do
    # with attack reduction. Every other criterion must still be green.
    others = [f for f in report["findings"] if f["gate"] not in ("G4", "CLOSURE")]
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

# ---------------------------------------------------------------------------
# THE MODE. Record-only scores and does not enforce.
#
# EVERY TEST BELOW IS WRITTEN SO IT CANNOT PASS UNDER BOTH MODES. A test that
# holds either way is a test of the scorer, not of the switch, and the scorer
# already has eleven of those above. Each one names the candidate it feeds and
# asserts the OPPOSITE promotion outcome from its sibling.
# ---------------------------------------------------------------------------

RECORD_ONLY_REASON = "the v0 attack baseline does not exist yet"


def record_only_gate(tmp_path, ledger, reason=RECORD_ONLY_REASON):
    return build(tmp_path, ledger, g4_mode=g4.RECORD_ONLY,
                 g4_record_only_reason=reason)


def test_enforcing_is_the_default_and_record_only_must_be_asked_for():
    """POINT OF ORDER, ASSERTED RATHER THAN COMMENTED. A gate built with no
    mode argument enforces. This is the assertion that fails if someone
    switches the default to get past a deadline."""
    assert g4.DEFAULT_MODE == g4.ENFORCING
    assert g4.resolve_mode() == (g4.ENFORCING, "")
    assert g4.resolve_mode(None, "") == (g4.ENFORCING, "")


def test_record_only_refuses_to_be_selected_without_a_reason():
    """The reason is recorded in the bundle. A suppression nobody can name is
    the silent exclusion this repo keeps closing."""
    with pytest.raises(g4.G4ModeError) as ei:
        g4.resolve_mode(g4.RECORD_ONLY)
    assert "requires a reason" in str(ei.value)
    with pytest.raises(g4.G4ModeError):
        g4.resolve_mode(g4.RECORD_ONLY, "   ")


def test_a_misspelled_mode_falls_back_to_neither_mode():
    """NOT to ENFORCING, which would halt a run for a typo, and NOT to
    RECORD_ONLY, which would disable a REJECT criterion for one."""
    for bad in ("record_only", "RECORDONLY", "off", True, 1):
        with pytest.raises(g4.G4ModeError):
            g4.resolve_mode(bad, "a reason")


def test_a_reason_without_record_only_is_refused():
    """It would be recorded as though the criterion had been suppressed when it
    had not."""
    with pytest.raises(g4.G4ModeError):
        g4.resolve_mode(g4.ENFORCING, "a reason nobody asked for")


def test_the_gate_refuses_to_be_built_with_an_unexplained_record_only(
        led, tmp_path):
    """AT CONSTRUCTION, not at the first candidate. A gate built with a bad
    mode is not a gate that misbehaves in round three."""
    with pytest.raises(g4.G4ModeError):
        trg.build(tmp_path, led, g4_mode=g4.RECORD_ONLY)


def test_the_same_inert_candidate_is_rejected_enforcing_and_promoted_recording(
        led, tmp_path):
    """THE MODE TEST. One candidate, two modes, opposite outcomes.

    `deny_pii_reads` binds a class this slice never carries: b = 0 under both
    modes, because THE MEASUREMENT DOES NOT CHANGE. What changes is whether the
    measurement is allowed to stop the promotion. Neither half of this test can
    pass under the other mode.
    """
    enforcing = trg.build(tmp_path / "a", led)
    rec_a = Rec(F.EMPTY_POLICY, F.slice_of(n_breaching=3))
    assert enforcing(envelope(F.deny_pii_reads()), rec_a) is False
    assert rec_a.newly_blocked_b == 0

    recording = record_only_gate(tmp_path / "b", led)
    rec_b = Rec(F.EMPTY_POLICY, F.slice_of(n_breaching=3))
    assert recording(envelope(F.deny_pii_reads()), rec_b) is True
    # AND THE NUMBER IS THE SAME NUMBER. Record-only must not be a mode in
    # which G4 quietly scores something else.
    assert rec_b.newly_blocked_b == rec_a.newly_blocked_b == 0
    assert rec_b.newly_breached_c == rec_a.newly_breached_c == 0
    assert rec_b.g4_paired_n == rec_a.g4_paired_n


def test_record_only_does_not_enforce_even_a_regression(led, tmp_path):
    """`c > 0` is the strongest rejection G4 has, and RECORD_ONLY does not
    enforce that one either.

    THIS IS NOT A CONVENIENCE, IT IS THE POINT OF NAMING THE MODE IN THE
    ARTIFACT: a run in this mode promoted a candidate that re-opened three
    attacks, and the only thing that can tell a reader so is the recorded mode
    plus `would_have`.
    """
    gate = record_only_gate(tmp_path, led)
    rec = Rec(F.deny_over_ceiling(), F.slice_of(n_breaching=3))
    assert gate(envelope(F.EMPTY_POLICY), rec) is True
    assert rec.newly_breached_c == 3
    f = [x for x in gate.reports[0]["findings"] if x["gate"] == "G4"][0]
    assert f["status"] == rg.RECORDED and f["would_have"] == rg.FAIL


def test_record_only_records_a_passing_criterion_as_recorded_not_as_pass(
        led, tmp_path):
    """A PASS emitted in record-only mode would be indistinguishable from a run
    that really was gated. The status answers "was this enforced"; `would_have`
    answers "was it satisfied"."""
    gate = record_only_gate(tmp_path, led)
    assert gate(envelope(F.deny_over_ceiling()), Rec(F.EMPTY_POLICY,
                                                     F.slice_of())) is True
    f = [x for x in gate.reports[0]["findings"] if x["gate"] == "G4"][0]
    assert f["status"] == rg.RECORDED
    assert f["would_have"] == rg.PASS
    assert f["status"] != rg.PASS


def test_an_unmeasurable_g4_is_also_not_enforced_in_record_only(led, tmp_path):
    """The UNEVALUABLE route is a REJECT under ENFORCING and must not be a
    RUN_INVALID under either mode."""
    gate = record_only_gate(tmp_path, led)
    assert gate(envelope(F.deny_over_ceiling()), Rec(None, None)) is True
    f = [x for x in gate.reports[0]["findings"] if x["gate"] == "G4"][0]
    assert f["status"] == rg.RECORDED and f["would_have"] == rg.UNEVALUABLE


def test_record_only_never_suppresses_any_other_gate(led, tmp_path):
    """SCOPED TO G4, and this is the assertion that catches a mode that grew.

    `RECORDED` is excluded from the rejection set by status, not by gate id, so
    a future finding that wrongly carried it would silently stop rejecting.
    Here a G8 failure - RUN INVALID, the strongest outcome the gate has - must
    still raise while G4 is in record-only.
    """
    armorer_holds_a_role = trg.fake_fetch(
        policies_bindings=trg.CLEAN_POLICIES + [
            {"role": "roles/storage.objectAdmin",
             "members": [trg.sa(trg.ENV["SA_ARMORER"])]}],
        project_bindings=trg.CLEAN_PROJECT)
    gate = trg.build(tmp_path, led, g4_mode=g4.RECORD_ONLY,
                     g4_record_only_reason=RECORD_ONLY_REASON,
                     iam_fetch=armorer_holds_a_role)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(envelope(F.deny_over_ceiling()), Rec(F.EMPTY_POLICY, F.slice_of()))
    assert "the separation was never real" in str(ei.value)


def test_the_mode_is_stamped_on_the_record_for_the_bundle(led, tmp_path):
    """The bundle reads `record.g4_mode`. If the gate does not stamp it, the
    bundle says `None` and a reader cannot tell an ungated promotion from an
    unevaluated one."""
    enforcing = trg.build(tmp_path / "a", led)
    rec_a = Rec(F.EMPTY_POLICY, F.slice_of())
    enforcing(envelope(F.deny_over_ceiling()), rec_a)
    assert rec_a.g4_mode == g4.ENFORCING and rec_a.g4_record_only_reason == ""

    # A DISTINCT candidate. Both gates share one ledger and one run id, so a
    # byte-identical second policy raises E_CONVERGED - which is the fixpoint
    # signal and not a mode question.
    recording = record_only_gate(tmp_path / "b", led)
    rec_b = Rec(F.EMPTY_POLICY, F.slice_of())
    recording(envelope(F.deny_over_ceiling(threshold=60000)), rec_b)
    assert rec_b.g4_mode == g4.RECORD_ONLY
    assert rec_b.g4_record_only_reason == RECORD_ONLY_REASON


def test_the_banner_says_scored_and_not_enforced(led, tmp_path):
    """POINT 2. The banner's job is separating what is real from what is a
    stand-in, and a criterion that is scored and not enforced is a third thing
    that reads like the first."""
    from crucible.conductor.campaign import gate_banner_lines

    enforced = gate_banner_lines(False, {
        "policy_store": "x",
        "g4": {"mode": g4.ENFORCING, "enforced": True,
               "record_only_reason": None, "thresholds": "b >= 3, c == 0"}})
    assert any("G4" in l and "ENFORCING" in l for l in enforced)
    assert not any("NOT ENFORCED" in l for l in enforced)

    recorded = gate_banner_lines(False, {
        "policy_store": "x",
        "g4": {"mode": g4.RECORD_ONLY, "enforced": False,
               "record_only_reason": RECORD_ONLY_REASON,
               "thresholds": "b >= 3, c == 0"}})
    line = [l for l in recorded if "G4" in l][0]
    assert "SCORED, NOT ENFORCED" in line
    assert RECORD_ONLY_REASON in line
    assert "PROMOTED ANYWAY" in line


def test_the_banner_refuses_to_guess_a_mode_it_was_not_given():
    """A branch with no test is a branch that cannot fail.

    A caller that assembles `info` by hand gets NEITHER claim. Saying
    "ENFORCING" would be enforcement invented by the renderer; saying "NOT
    ENFORCED" would be a suppression invented by the renderer.
    """
    from crucible.conductor.campaign import gate_banner_lines

    line = [l for l in gate_banner_lines(False, {"policy_store": "x"})
            if "G4" in l][0]
    assert "MODE NOT SUPPLIED" in line
    assert "ENFORCING" not in line
    assert "NOT ENFORCED" not in line


def test_the_g4_banner_line_is_not_the_row_the_readme_test_pins():
    """POSITIONAL COUPLING, ASSERTED. `tests/test_readme_claims.py` pins the
    README's pasted transcript to `gate_banner_lines(False, ...)[0]`. Anyone
    who prepends a line here silently re-points that test at a different row,
    and it would keep passing while measuring the wrong thing."""
    from crucible.conductor.campaign import gate_banner_lines

    lines = gate_banner_lines(False, {
        "policy_store": "x",
        "g4": {"mode": g4.ENFORCING, "enforced": True,
               "record_only_reason": None, "thresholds": "b >= 3, c == 0"}})
    assert lines[0].startswith("  gate         :")
    assert any(l.startswith("  G4           :") for l in lines)


def test_render_distinguishes_a_recorded_pass_from_a_recorded_failure():
    """"Not enforced" and "not enforced AND it would have rejected this" are
    different facts, and a banner reader needs the second."""
    would_fail = rg.finding("G4", "c", rg.RECORDED, "d", would_have=rg.FAIL)
    would_pass = rg.finding("G4", "c", rg.RECORDED, "d", would_have=rg.PASS)
    assert "RECORDED(WOULD_FAIL)" in rg.render([would_fail])
    assert "RECORDED(WOULD_PASS)" in rg.render([would_pass])


def test_gate_summary_derives_enforcement_from_what_the_gate_did(led, tmp_path):
    """Same discipline as `g7_g8_exercised`: derived from the findings, never
    from the flag. A run that never reached a candidate enforced G4 exactly as
    little as a record-only run did."""
    from crucible.conductor.campaign import gate_summary

    gate = record_only_gate(tmp_path, led)
    gate(envelope(F.deny_pii_reads()), Rec(F.EMPTY_POLICY, F.slice_of()))
    out = gate_summary(gate, {"g4": {"mode": g4.RECORD_ONLY}})
    assert out["g4_mode"] == g4.RECORD_ONLY
    assert out["g4_scored_calls"] == 1
    assert out["g4_enforced_at_least_once"] is False
    assert out["g4_would_have_rejected"] == 1

    enforcing = trg.build(tmp_path / "b", led)
    enforcing(envelope(F.deny_over_ceiling()), Rec(F.EMPTY_POLICY, F.slice_of()))
    out2 = gate_summary(enforcing, {"g4": {"mode": g4.ENFORCING}})
    assert out2["g4_enforced_at_least_once"] is True
    assert out2["g4_would_have_rejected"] == 0


def test_the_scorer_takes_any_iterable_and_scores_both_arms_on_it():
    """THE INPUT CONTRACT the v0 baseline lane meets. A generator would be
    exhausted by the first episode's first arm, and every later comparison
    would silently be against nothing - so the slice is materialised once."""
    episodes = F.slice_of(n_breaching=3, n_clean=1)
    from_list = g4.paired_scores(episodes, F.EMPTY_POLICY,
                                 F.deny_over_ceiling(), F.OBJECTIVE_SET)
    from_gen = g4.paired_scores((e for e in episodes), F.EMPTY_POLICY,
                                F.deny_over_ceiling(), F.OBJECTIVE_SET)
    assert from_gen["newly_blocked_b"] == from_list["newly_blocked_b"] == 3
    assert from_gen["n"] == from_list["n"] == 4
    assert from_gen["slice_n"] == from_list["slice_n"] == 4


def test_the_scorer_does_not_care_which_policy_an_episode_was_recorded_under():
    """WHY A FIXED v0 BASELINE AND A RUN'S OWN EPISODES CAN FEED THE SAME
    FUNCTION. Both arms are re-scored from the recorded calls, so the episode's
    own `policy_version` is not an input to b or c."""
    base = F.slice_of(n_breaching=3, n_clean=0)
    aged = [dict(e, policy_version=7, policy_hash="q" * 16) for e in base]
    at_v0 = g4.paired_scores(base, F.EMPTY_POLICY, F.deny_over_ceiling(),
                             F.OBJECTIVE_SET)
    at_v7 = g4.paired_scores(aged, F.EMPTY_POLICY, F.deny_over_ceiling(),
                             F.OBJECTIVE_SET)
    assert at_v7["newly_blocked_b"] == at_v0["newly_blocked_b"] == 3
    assert at_v7["newly_breached_c"] == at_v0["newly_breached_c"] == 0
