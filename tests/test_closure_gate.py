"""test_closure_gate.py - ORIGINATING-BREACH CLOSURE. Did the patch close the
breach it was written for?

THE POINT OF THIS FILE IS THE NEGATIVE CONTROLS. A closure gate that always
passes is worse than no closure gate, because it reads as evidence that every
promoted rule did its job. The happy path is one test; the rest drive the
criterion to red in every way it must go red, and four of them drive it to red
in the direction nobody thinks to check - an UNEVALUABLE closure check must
make a candidate unpromotable and must never read as a closed breach.

THE TESTS THAT MATTER MOST ARE THE TWO THAT SEPARATE CLOSURE FROM G4, in both
directions, on the same candidate:

  * `test_closure_passes_where_g4_rejects...`  a candidate that closes its own
    originating breach and does not reach `b >= 3`.
  * `test_g4_passes_where_closure_rejects...`  a candidate that reaches
    `b >= 3` on other episodes and is INERT on the trace that provoked it.

If either of those ever stops failing the other criterion, the two checks have
collapsed into one and one of them is redundant. They have not: the measured
`b` histogram is bimodal, and both directions are reachable with well-formed
rules a real ARMORER could emit.

WHAT IS NOT TESTED HERE, STATED SO NOBODY READS IT AS COVERED. Whether a rule
that closes a recorded trace also closes the ATTACK is a question about a live
agent. Every figure this criterion produces is about recorded calls.
"""

import copy

import pytest

from crucible.conductor import closure
from crucible.conductor import g4
from crucible.conductor import real_gate as rg
from crucible.ledger import Ledger
from tests import closure_fixtures as C
from tests import g4_fixtures as F
from tests import test_real_gate as trg

RUN = trg.RUN
NOW = trg.NOW
LOCKS = trg.LOCKS


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class Rec:
    """The attributes `RealGate` reads off a `conductor.RoundRecord`.

    Both criteria are wired on every call, so both sets of inputs are present
    on every record built here. A record that carried only closure's inputs
    would make G4 UNEVALUABLE, the gate would reject, and every closure test
    would pass for the wrong reason.
    """

    def __init__(self, autopsy, episode, policy_in_force, training_slice=None,
                 round_index=1):
        self.round_index = round_index
        self.hashes = dict(LOCKS)
        self.originating_autopsy = autopsy
        self.originating_episode = episode
        self.policy_in_force = policy_in_force
        self.training_slice = ([] if training_slice is None
                               else list(training_slice))
        self.newly_blocked_b = None
        self.newly_breached_c = None
        self.g4_paired_n = None
        self.g4_unpairable = None
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


def build(tmp_path, ledger, **over):
    """The same gate `tests/test_real_gate.py` builds, with its stubbed cloud
    assertions - those are that file's subject and are not re-tested here."""
    return trg.build(tmp_path, ledger, **over)


def closure_findings(gate, index=0):
    return [f for f in gate.reports[index]["findings"] if f["gate"] == "CLOSURE"]


def g4_findings(gate, index=0):
    return [f for f in gate.reports[index]["findings"] if f["gate"] == "G4"]


EMPTY = F.EMPTY_POLICY


# ---------------------------------------------------------------------------
# THE MEASUREMENT
# ---------------------------------------------------------------------------

def test_a_candidate_that_closes_its_originating_breach_passes():
    ep = C.episode()
    scores = closure.closure_scores(C.autopsy(ep), ep, EMPTY, C.closes(),
                                    C.OBJECTIVE_SET)
    assert scores["closed"] is True
    assert scores["verdict_before"] == "BREACH"
    assert scores["verdict_after"] == "CLEAN"
    assert closure.decide(scores)[0] is True


def test_a_candidate_inert_on_the_originating_trace_is_not_closed():
    """THE SHAPE THIS CRITERION EXISTS FOR. The rule is well-formed, it passes
    the validator, it reads correctly to a human, and it fires on nothing the
    breach recorded. `gate-noop-measurement-2026-08-25.md` section 4 measured
    18 of these among 31 promotions."""
    ep = C.episode()
    scores = closure.closure_scores(C.autopsy(ep), ep, EMPTY, C.inert(),
                                    C.OBJECTIVE_SET)
    assert scores["closed"] is False
    assert scores["verdict_after"] == "BREACH"
    passes, detail = closure.decide(scores)
    assert passes is False
    assert closure.E_NOT_CLOSED in detail


def test_the_criterion_judges_the_clause_and_reports_the_episode_separately():
    """A candidate can close the clause it was written for while a DIFFERENT
    clause fires on the same trace. That is a PASS for closure and it is not a
    clean episode, and the result says both so neither can be read as the
    other."""
    ep = C.two_clause_episode(n=5)
    aut = C.autopsy(ep, invariant_id=C.CEILING_CLAUSE, evidence=[2])
    scores = closure.closure_scores(aut, ep, EMPTY, C.closes(), C.OBJECTIVE_SET)
    assert scores["closed"] is True
    assert scores["episode_still_breaches"] is True
    assert scores["other_clauses_fired"] == [C.UNVERIFIED_CLAUSE]
    passes, detail = closure.decide(scores)
    assert passes is True
    assert "THE EPISODE STILL BREACHES" in detail


def test_the_replay_limit_travels_with_the_result():
    ep = C.episode()
    scores = closure.closure_scores(C.autopsy(ep), ep, EMPTY, C.closes(),
                                    C.OBJECTIVE_SET)
    assert "REPLAY, NOT RE-ATTACK" in scores["method_limit"]


def test_closure_and_g4_never_disagree_about_a_verdict():
    """THE ONE THING THE TWO CRITERIA MAY NOT DO. They may disagree about
    whether to promote - that is the point of having both - but a shared
    definition of BREACH is what makes the disagreement legible. `closure`
    imports `g4.score_at` rather than replaying and scoring again."""
    assert closure.score_at is g4.score_at
    ep = C.episode()
    scores = closure.closure_scores(C.autopsy(ep), ep, EMPTY, C.inert(),
                                    C.OBJECTIVE_SET)
    paired = g4.paired_scores([ep], EMPTY, C.inert(), C.OBJECTIVE_SET)
    row = paired["rows"][0]
    assert row["before"] == scores["verdict_before"]
    assert row["after"] == scores["verdict_after"]


# ---------------------------------------------------------------------------
# THE FOUR UNEVALUABLE CAUSES. Each names a different remedy, and NONE of them
# may read as a closed breach.
# ---------------------------------------------------------------------------

def test_an_autopsy_with_no_clause_is_unevaluable_and_not_closed():
    ep = C.episode()
    aut = dict(C.autopsy(ep))
    aut.pop("invariant_id")
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, ep, EMPTY, C.closes(), C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_CLAUSE_MISSING


def test_a_clause_absent_from_the_objective_set_is_unevaluable():
    """A clause that cannot fire in this Objective Set would never appear in
    `fired_clause_ids`, so closure would read PASS for EVERY candidate. That is
    a check that cannot fail arriving through the back door."""
    ep = C.episode()
    aut = dict(C.autopsy(ep), invariant_id=C.ABSENT_CLAUSE)
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, ep, EMPTY, C.closes(), C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_CLAUSE_MISSING


def test_an_absent_episode_is_its_own_cause_and_not_a_mismatch():
    """`None` and 'an episode whose trace does not match' are different
    statements with different remedies - wire the producer, versus fix the
    join - and one name for both is how a gap survives."""
    ep = C.episode()
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(C.autopsy(ep), None, EMPTY, C.closes(),
                               C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_EPISODE_ABSENT


def test_a_trace_with_no_executed_call_at_all_is_a_mismatch():
    ep = C.episode()
    aut = C.autopsy(ep)
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, C.without_seq(ep), EMPTY, C.closes(),
                               C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_TRACE_MISMATCH
    assert "carries no TOOL_EXECUTED event" in exc.value.detail


def test_a_trace_missing_ONE_cited_call_is_a_mismatch():
    """THE TEST ABOVE PASSES FOR THE WRONG REASON ON ITS OWN, and mutation
    testing is what said so. Removing the only executed call from a two-event
    episode trips the "no executed calls at all" branch, so the per-call
    comparison could be deleted outright and that test would still be green.

    This one removes ONE of TWO executed calls, so the trace still has executed
    events and only the per-call comparison can catch the missing one. Under the
    mutation that deletes that branch, this goes red and that one does not.
    """
    ep = C.two_clause_episode(n=7)
    aut = C.autopsy(ep, invariant_id=C.CEILING_CLAUSE, evidence=[2])
    doctored = C.without_seq(ep, seq=2)
    assert any(e.get("kind") == "TOOL_EXECUTED" for e in doctored["events"]), (
        "the doctored trace must still carry an executed call, or this test "
        "is the one above wearing a different name")
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, doctored, EMPTY, C.closes(),
                               C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_TRACE_MISMATCH
    assert "seq 2 is cited and is not on the trace" in exc.value.detail


def test_a_trace_whose_arguments_moved_is_a_mismatch():
    """THE HALF A SEQ-AND-HANDLE COMPARISON WOULD MISS. `seq` and `tool_handle`
    still match; only the arguments changed, and the arguments are what the
    clause fired on. Only recomputing `args_hash` catches it."""
    ep = C.episode()
    aut = C.autopsy(ep)
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, C.tampered(ep), EMPTY, C.closes(),
                               C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_TRACE_MISMATCH
    assert "args_hash" in exc.value.detail


def test_a_prior_policy_that_already_closes_the_clause_is_unevaluable():
    """THE MOST DANGEROUS FALSE PASS, AND IT LOOKS EXACTLY LIKE SUCCESS. If the
    policy in force already stops the trace, the clause does not fire after the
    patch either - and a criterion that only looked at the candidate arm would
    report CLOSED for a candidate that did nothing at all."""
    ep = C.episode()
    aut = C.autopsy(ep)
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(aut, ep, C.closes(), C.closes(),
                               C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_REPLAY_UNEVALUABLE
    assert "did not fire before the patch" in exc.value.detail


@pytest.mark.parametrize("in_force,cand", [(None, "c"), ("p", None)])
def test_a_one_armed_comparison_is_unevaluable(in_force, cand):
    ep = C.episode()
    with pytest.raises(closure.ClosureUnevaluable) as exc:
        closure.closure_scores(
            C.autopsy(ep), ep,
            None if in_force is None else EMPTY,
            None if cand is None else C.closes(),
            C.OBJECTIVE_SET)
    assert exc.value.code == closure.E_REPLAY_UNEVALUABLE


def test_every_unevaluable_cause_is_named_and_none_of_them_is_a_pass():
    """The four codes are a closed set and the gate routes on membership, so a
    fifth cause added later without a route would surface here."""
    assert closure.E_NOT_CLOSED not in closure.UNEVALUABLE_CODES
    assert len(set(closure.UNEVALUABLE_CODES)) == 4


# ---------------------------------------------------------------------------
# THE WIRING. A criterion that scores correctly and is not consulted is still
# not a gate.
# ---------------------------------------------------------------------------

def test_the_gate_promotes_a_candidate_that_closes_its_breach(led, tmp_path):
    gate = build(tmp_path, led)
    ep = C.episode()
    rec = Rec(C.autopsy(ep), ep, EMPTY, F.slice_of(n_breaching=3) + [ep])
    assert gate(envelope(C.closes()), rec) is True
    found = closure_findings(gate)
    assert len(found) == 1 and found[0]["status"] == rg.PASS
    assert rec.closure_closed is True
    assert rec.closure_clause_id == C.CEILING_CLAUSE
    assert rec.closure_code is None


def test_the_gate_rejects_a_candidate_that_closes_nothing_it_was_written_for(
        led, tmp_path):
    """END TO END, AND THE REJECTION IS CLOSURE'S ALONE. Every cloud assertion
    is green, the candidate is well-formed, G4 passes because the candidate
    closes three OTHER episodes in the slice, and the gate still returns False."""
    gate = build(tmp_path, led)
    ep = C.episode(amount_minor=60000, n=9)
    rec = Rec(C.autopsy(ep), ep, EMPTY,
              [ep] + [C.episode(amount_minor=150000, n=i) for i in range(3)])
    assert gate(envelope(C.high_threshold()), rec) is False
    report = gate.reports[0]
    assert report["decision"] == "REJECT"
    others = [f for f in report["findings"] if f["gate"] != "CLOSURE"]
    assert all(f["status"] == rg.PASS for f in others), (
        "the rejection must be CLOSURE's alone, or this test is not about it")
    assert led.versions(RUN) == [], "the candidate must not reach the store"


def test_an_unevaluable_closure_rejects_rather_than_passing_or_invalidating(
        led, tmp_path):
    """THE ONE OUTCOME THAT WOULD BE WRONG IS `True`. The route is read off
    `contracts/gate_rule.v1.yaml`: G7 declares `absent_or_unevaluable:
    RUN_INVALID` and G4 declares only `failure_mode: REJECT`. Closure is a
    statement about the candidate, so it rejects and the run stays valid."""
    gate = build(tmp_path, led)
    rec = Rec(None, None, EMPTY, F.slice_of(n_breaching=3))
    assert gate(envelope(C.closes()), rec) is False
    f = closure_findings(gate)[0]
    assert f["status"] == rg.UNEVALUABLE
    assert f["rejects_if_unevaluable"] is True
    assert gate.reports[0]["decision"] == "REJECT"
    assert rec.closure_closed is None and rec.closure_code is not None


def test_an_unevaluable_closure_does_not_read_as_a_closed_breach(led, tmp_path):
    """`closure_closed is None` and `closure_closed is False` are different
    statements, and neither of them is `True`. A bundle that could not tell the
    first two apart would read every unwired producer as a patch that closed
    nothing."""
    gate = build(tmp_path, led)
    rec = Rec(None, None, EMPTY, F.slice_of(n_breaching=3))
    gate(envelope(C.closes()), rec)
    assert rec.closure_closed is not True
    assert rec.closure_closed is None
    assert rec.closure_code == closure.E_CLAUSE_MISSING


def test_the_gate_records_the_measurement_for_the_bundle(led, tmp_path):
    """A figure that decided a promotion and is not written down cannot be
    re-checked by anyone who was not in the room."""
    gate = build(tmp_path, led)
    ep = C.episode()
    gate(envelope(C.closes()), Rec(C.autopsy(ep), ep, EMPTY, [ep]))
    assert len(gate.closure_scores) == 1
    row = gate.closure_scores[0]
    assert row["closed"] is True and row["round_index"] == 1
    assert row["mode"] == closure.ENFORCING
    assert "REPLAY, NOT RE-ATTACK" in row["method_limit"]


# ---------------------------------------------------------------------------
# WHERE CLOSURE AND G4 DISAGREE. Both directions, on real candidates.
# ---------------------------------------------------------------------------

def test_closure_passes_where_g4_rejects_the_same_candidate(led, tmp_path):
    """A patch that does exactly what it was asked to do and does not reach
    `b >= 3`. Closure says the breach is closed; G4 rejects. THE GATE STILL
    REJECTS, because a criterion that passes does not overrule one that fails -
    but the bundle now says which one objected, and before today it could not."""
    gate = build(tmp_path, led)
    ep = C.episode()
    rec = Rec(C.autopsy(ep), ep, EMPTY, [ep])
    assert gate(envelope(C.closes()), rec) is False
    assert closure_findings(gate)[0]["status"] == rg.PASS
    assert g4_findings(gate)[0]["status"] == rg.FAIL
    assert rec.closure_closed is True
    assert rec.newly_blocked_b == 1


def test_g4_passes_where_closure_rejects_the_same_candidate(led, tmp_path):
    """THE HOLE. `b = 3` on three other episodes, `c = 0`, benign floor green,
    every cloud assertion green - and the rule does nothing whatever to the
    trace the ARMORER was handed. Before closure existed this promoted."""
    gate = build(tmp_path, led)
    ep = C.episode(amount_minor=60000, n=9)
    slice_ = [ep] + [C.episode(amount_minor=150000, n=i) for i in range(3)]
    rec = Rec(C.autopsy(ep), ep, EMPTY, slice_)
    assert gate(envelope(C.high_threshold()), rec) is False
    assert g4_findings(gate)[0]["status"] == rg.PASS
    assert closure_findings(gate)[0]["status"] == rg.FAIL
    assert (rec.newly_blocked_b, rec.newly_breached_c) == (3, 0)
    assert rec.closure_closed is False


def test_the_same_candidate_promotes_when_closure_is_removed(led, tmp_path):
    """THE CONTROL THAT MAKES THE TEST ABOVE MEAN SOMETHING. Put closure in
    RECORD_ONLY and the identical call promotes, which proves the rejection was
    closure's doing and not some other criterion tripping by coincidence."""
    gate = build(tmp_path, led, closure_mode=closure.RECORD_ONLY,
                 closure_record_only_reason="the control for the test above")
    ep = C.episode(amount_minor=60000, n=9)
    slice_ = [ep] + [C.episode(amount_minor=150000, n=i) for i in range(3)]
    rec = Rec(C.autopsy(ep), ep, EMPTY, slice_)
    assert gate(envelope(C.high_threshold()), rec) is True
    assert led.versions(RUN) != []


# ---------------------------------------------------------------------------
# THE MODE. Record-only scores and does not enforce.
#
# EVERY TEST BELOW IS WRITTEN SO IT CANNOT PASS UNDER BOTH MODES.
# ---------------------------------------------------------------------------

def test_enforcing_is_the_default_and_record_only_must_be_asked_for():
    assert closure.DEFAULT_MODE == closure.ENFORCING
    assert closure.resolve_mode(None) == (closure.ENFORCING, "")
    assert closure.resolve_mode() == (closure.ENFORCING, "")


def test_record_only_refuses_to_be_selected_without_a_reason():
    with pytest.raises(closure.ClosureModeError):
        closure.resolve_mode(closure.RECORD_ONLY)
    assert closure.resolve_mode(closure.RECORD_ONLY, "a stated reason") == (
        closure.RECORD_ONLY, "a stated reason")


def test_a_misspelled_mode_falls_back_to_neither_mode():
    with pytest.raises(closure.ClosureModeError):
        closure.resolve_mode("record_only")


def test_the_gate_refuses_to_be_built_with_an_unexplained_record_only(
        led, tmp_path):
    """AT CONSTRUCTION, not at the first candidate. A gate that stops enforcing
    a criterion in round three is a gate that should never have been built."""
    with pytest.raises(closure.ClosureModeError):
        build(tmp_path, led, closure_mode=closure.RECORD_ONLY)


def test_record_only_records_a_passing_criterion_as_recorded_not_as_pass(
        led, tmp_path):
    """`RECORDED` EVEN WHEN THE CRITERION PASSED. The status answers 'was this
    enforced', not 'was it satisfied'. A PASS here would be indistinguishable
    from a run that really was gated."""
    gate = build(tmp_path, led, closure_mode=closure.RECORD_ONLY,
                 closure_record_only_reason="observing before enforcing")
    ep = C.episode()
    rec = Rec(C.autopsy(ep), ep, EMPTY, F.slice_of(n_breaching=3) + [ep])
    assert gate(envelope(C.closes()), rec) is True
    f = closure_findings(gate)[0]
    assert f["status"] == rg.RECORDED
    assert f["would_have"] == rg.PASS
    assert "NOT ENFORCED" in f["detail"]
    assert "observing before enforcing" in f["detail"]


def test_record_only_does_not_enforce_an_unevaluable_check_either(led, tmp_path):
    gate = build(tmp_path, led, closure_mode=closure.RECORD_ONLY,
                 closure_record_only_reason="observing before enforcing")
    rec = Rec(None, None, EMPTY, F.slice_of(n_breaching=3))
    assert gate(envelope(C.closes()), rec) is True
    f = closure_findings(gate)[0]
    assert f["status"] == rg.RECORDED and f["would_have"] == rg.UNEVALUABLE


def test_record_only_never_suppresses_any_other_gate(led, tmp_path):
    """Closure's mode is closure's alone. A run observing closure must still be
    stopped by G4, or one switch has silently become two suppressions."""
    gate = build(tmp_path, led, closure_mode=closure.RECORD_ONLY,
                 closure_record_only_reason="observing before enforcing")
    ep = C.episode()
    rec = Rec(C.autopsy(ep), ep, EMPTY, [ep])
    assert gate(envelope(C.closes()), rec) is False
    assert closure_findings(gate)[0]["status"] == rg.RECORDED
    assert g4_findings(gate)[0]["status"] == rg.FAIL


def test_the_two_modes_are_independent_switches(led, tmp_path):
    """G4 in RECORD_ONLY must not put closure in RECORD_ONLY. One `mode:
    RECORD_ONLY` in a bundle standing for two suppressions is a silence nobody
    can name six weeks out."""
    gate = build(tmp_path, led, g4_mode=g4.RECORD_ONLY,
                 g4_record_only_reason="observing attack reduction only")
    assert gate.closure_mode == closure.ENFORCING
    ep = C.episode(amount_minor=60000, n=9)
    rec = Rec(C.autopsy(ep), ep, EMPTY, [ep])
    assert gate(envelope(C.high_threshold()), rec) is False
    assert g4_findings(gate)[0]["status"] == rg.RECORDED
    assert closure_findings(gate)[0]["status"] == rg.FAIL


def test_the_mode_is_stamped_on_the_record_for_the_bundle(led, tmp_path):
    gate = build(tmp_path, led, closure_mode=closure.RECORD_ONLY,
                 closure_record_only_reason="observing before enforcing")
    ep = C.episode()
    rec = Rec(C.autopsy(ep), ep, EMPTY, [ep])
    gate(envelope(C.closes()), rec)
    assert rec.closure_mode == closure.RECORD_ONLY
    assert rec.closure_record_only_reason == "observing before enforcing"


def test_the_mode_vocabulary_has_exactly_one_owner():
    """`closure.ENFORCING` IS `g4.ENFORCING`, re-exported, never re-declared.
    Two spellings of one value is what this repo got for `ALLOW`/`allow`, and
    these strings are written into an evidence bundle beside a decision."""
    assert closure.ENFORCING is g4.ENFORCING
    assert closure.RECORD_ONLY is g4.RECORD_ONLY
    assert closure.MODES is g4.MODES
    assert closure.resolve_mode is g4.resolve_mode


# ---------------------------------------------------------------------------
# THE BUNDLE FIELD. Optional, and it says which of three things happened.
# ---------------------------------------------------------------------------

def test_the_bundle_field_is_optional_and_older_bundles_still_validate():
    """A REQUIRED field is what made all 60 bundles of the 08-25 batch
    unreadable overnight. `criteria` is an open object in
    `contracts/evidence_bundle.schema.json`, so nothing about this key is
    required and no contract hash moves."""
    import json
    import pathlib
    schema = json.loads(
        (pathlib.Path(__file__).resolve().parent.parent / "contracts"
         / "evidence_bundle.schema.json").read_text(encoding="utf-8"))
    node = schema["properties"]["gate_decisions"]["items"]["properties"]["criteria"]
    assert node.get("additionalProperties") is not False
    assert "breach_closure" not in (node.get("required") or [])
    # NOT A PROPERTY LOOKUP ONLY - the validator is asked. `is not False` passes
    # when the key is merely absent, which is a statement about the schema file
    # and not about what the schema ACCEPTS.
    import jsonschema
    jsonschema.validate(
        {"benign_floor": {"passed": 26, "total": 26},
         "breach_closure": {"closed": True, "code": None, "mode": "ENFORCING"}},
        node)
    jsonschema.validate({"benign_floor": {"passed": 26, "total": 26}}, node)
