"""test_dsl_grouping.py - GX2, the optional `group_by` key on `episode_sum`.

READ `test_a_grouped_fold_and_an_ungrouped_one_are_DIFFERENT_NUMBERS_on_one
_trace` FIRST. It is the control this whole file exists for.

A grammar that ACCEPTS the grouped form and then FOLDS UNGROUPED ANYWAY would
pass every parse test, every serialization test, every round-trip test and
every backward-compatibility test in this file. It would look like a shipped
feature and change nothing. The only assertion that can tell the two apart is
one where the grouped answer and the ungrouped answer over the SAME events are
different, and both are written out by hand rather than computed from the code
under test - a check that derives its expectation the same way as the claim
cannot catch the claim being wrong.

The second control is `test_the_engine_and_the_RULER_agree_about_who_is_in_the
_bucket`. The grouping rule is not a free choice: `crucible/tripwire/
objective_set.py::_fire_aggregate` already decides which events are in a bucket
when it scores an episode, and the policy engine has to mean the same thing by
the word. If it did not, a rule could close a breach by arithmetic the Objective
Set does not recognise, and the two would drift without any test failing.
"""

import json
import re

import pytest

from crucible.dsl import ParseError, parse_rule
from crucible.dsl.errors import ValidationError
from crucible.dsl.nodes import CLAUSE_EPISODE_SUM
from crucible.dsl.serialize import assign_rule_id, compile_rule, rule_body
from crucible.policy.engine import (FALSE, TRUE, UNEVALUABLE, PolicyEngine,
                                    _lookup)
from crucible.tripwire.model import ToolEvent
from crucible.tripwire.objective_set import _fire_aggregate
from crucible.warden import reference_engine

from . import l3_fixtures as fx

SUM_PATH = "derived.episode_count_same_subject"
GROUP_PATH = "case_id"
CAP = "CAP_MUTATES_DURABLE_STATE"

GROUPED = ("rule r_new1: cap:%s when "
           "episode_sum(%s group_by %s) >= 4 => deny" % (CAP, SUM_PATH, GROUP_PATH))
UNGROUPED = ("rule r_new1: cap:%s when "
             "episode_sum(%s) >= 4 => deny" % (CAP, SUM_PATH))


# --------------------------------------------------------------------------
# THE TRACE. Two buckets, and one call in neither.
#
# Every total below is stated as a literal and arrived at by adding up the
# numbers in this table by hand. Nothing here asks the engine what it thinks.
#
#   seq 1   case_A   count 1
#   seq 2   case_B   count 2
#   seq 3   case_B   count 2
#   seq 4   (no case_id)   count 9
#   pending case_A   count 2
#
#   ungrouped total, prefix + pending       1 + 2 + 2 + 9 + 2 = 16
#   case_A bucket, prefix + pending                     1 + 2 =  3
#   case_B bucket                                       2 + 2 =  4
#
# At a threshold of 4 those three numbers give three different answers, which
# is the entire reason the trace is shaped this way:
#   ungrouped                 16 >= 4   DENY
#   every bucket scanned      4 >= 4    DENY   (case_B, which the pending call
#                                               never touched)
#   the pending call's bucket  3 >= 4   ALLOW
# --------------------------------------------------------------------------

def _ev(seq, count, case=None):
    args = {SUM_PATH: count}
    if case is not None:
        args[GROUP_PATH] = case
    return {"kind": "TOOL_EXECUTED", "seq": seq, "tool_handle": "t_aaaaaaaa",
            "capability_classes": [CAP], "args": args}


PREFIX = [_ev(1, 1, "case_A"), _ev(2, 2, "case_B"), _ev(3, 2, "case_B"),
          _ev(4, 9, None)]
PENDING_IN_A = {SUM_PATH: 2, GROUP_PATH: "case_A"}
PENDING_NO_KEY = {SUM_PATH: 9}


def _decide(rule_text, args, prefix=PREFIX):
    engine = PolicyEngine({"rules": [compile_rule(parse_rule(rule_text))]})
    return engine.evaluate(tool_handle="t_aaaaaaaa", capability_set=[CAP],
                           args=args, episode_prefix=prefix,
                           episode_context={})


# --------------------------------------------------------------------------
# THE CONTROL. Everything else in this file passes whether or not the fold
# actually groups.
# --------------------------------------------------------------------------

def test_a_grouped_fold_and_an_ungrouped_one_are_DIFFERENT_NUMBERS_on_one_trace():
    """If this ever fails, the production was added and nothing was bought.

    The ungrouped rule sees 16 on this trace and denies. The grouped rule sees
    3 - the pending call's own bucket - and allows. Same events, same threshold,
    same verb, same capability class; the ONLY difference is the key. A parser
    that accepted `group_by` and dropped it on the floor would deny both, and
    every other assertion in this file would still pass.
    """
    assert _decide(UNGROUPED, PENDING_IN_A).outcome == "DENY"
    assert _decide(GROUPED, PENDING_IN_A).outcome == "ALLOW"


def test_the_control_above_can_actually_fail(monkeypatch):
    """THE BREAKER. A check that cannot fail is not measuring anything.

    This installs the exact defect the control exists to catch - an engine that
    ACCEPTS the grouping key and folds ungrouped anyway - and requires the
    control's own assertion to flip. Without it, "the grouped rule allows" is a
    sentence that would also be true of a rule the engine never matched, a
    threshold nothing reached, or a clause silently dropped.

    Note what does NOT break under this defect: parsing, serialization, the
    absent-key convention, the round-trips, the C4 schema, and the recorded
    rule's id. Thirteen of the assertions in this file are blind to it. That is
    why the control is the first test rather than the last.
    """
    def folds_ungrouped(self, arg_path, visible_prefix, pending_args,
                        group_path=None):
        total = self._sum_over(arg_path, visible_prefix)
        found, value = _lookup(pending_args or {}, arg_path)
        if found and isinstance(value, int) and not isinstance(value, bool):
            total += value
        return total

    monkeypatch.setattr(PolicyEngine, "episode_sum", folds_ungrouped)
    assert _decide(UNGROUPED, PENDING_IN_A).outcome == "DENY"
    assert _decide(GROUPED, PENDING_IN_A).outcome == "DENY", (
        "the grouping key was ignored and the control did NOT notice - the "
        "control is not measuring the grouping")


def test_the_fold_is_over_the_pending_calls_own_bucket_and_not_over_every_bucket():
    """`case_B` reaches 4 on this trace and the pending call never touched it.

    The TRIPWIRE scans every bucket because it judges a FINISHED EPISODE and
    asks whether ANY subject was mutated too often. The engine judges ONE CALL.
    Denying this call for a total accumulated on a subject it never touched is
    a different rule from the one the clause states, and it would deny an
    unrelated first call in an episode that had already tripped elsewhere.
    """
    assert _decide(GROUPED, PENDING_IN_A).outcome == "ALLOW"
    # ... and the same rule DOES deny once the pending call's own bucket
    # crosses the line, so the ALLOW above is the scope and not a dead rule.
    assert _decide(GROUPED, {SUM_PATH: 3, GROUP_PATH: "case_A"}).outcome == "DENY"
    assert _decide(GROUPED, {SUM_PATH: 2, GROUP_PATH: "case_B"}).outcome == "DENY"


def test_the_engine_and_the_RULER_agree_about_who_is_in_the_bucket():
    """THE SEMANTIC DECISION, CHECKED AGAINST ITS OWNER RATHER THAN ASSERTED.

    `_fire_aggregate` skips any event whose `group_by` path resolves ABSENT: a
    call carrying no key is in NO bucket. The engine had to choose the same
    thing or mean something different by the word `group_by` from the artifact
    that scores the episode.

    seq 4 carries a count of 9 and no `case_id`. If the ruler swept it into a
    bucket, the aggregate clause below would fire on this trace; it does not.
    If the ENGINE swept it in, the grouped rule would deny the pending call in
    `case_A` (1 + 9 + 2 = 12); it allows.
    """
    clause = {"id": "inv_test", "form": "aggregate", "window": "window_by_seq",
              "capability_class": CAP, "group_by": GROUP_PATH,
              "sum_path": SUM_PATH, "op": "gte", "value": 10}
    executed = [ToolEvent(e) for e in PREFIX]
    assert _fire_aggregate(clause, executed, {}) is None, (
        "the RULER put the keyless event in a bucket - the engine's grouping "
        "rule is copied from _fire_aggregate and would now be copied from "
        "something else")
    assert _decide(GROUPED, PENDING_IN_A).outcome == "ALLOW"


def test_the_reference_engine_agrees_with_the_real_one_on_the_same_trace():
    """`crucible/warden/reference_engine.py` is a SECOND implementation, kept on
    purpose so the known-bad suite boots without L3's code. It implements only
    what the fixtures exercise - which is exactly why an unread `group_by` was
    the hazard here. It would not have raised; it would have folded ungrouped,
    agreed with the real engine on every single-bucket episode, and disagreed
    on precisely the episodes the form exists for.
    """
    def _pol(text):
        # `reference_engine.evaluate` reads `policy["hashed_payload"]["rules"]`.
        # Handing it a bare `{"rules": [...]}` matches nothing and answers ALLOW
        # for every input, which is how the ALLOW assertion below passed on the
        # first run of this test while asserting nothing at all.
        return {"hashed_payload": {"rules": [compile_rule(parse_rule(text))]}}

    prefix = reference_engine.Prefix([ToolEvent(e) for e in PREFIX], {})
    pending = ToolEvent({"kind": "TOOL_ATTEMPT", "seq": 5,
                         "tool_handle": "t_aaaaaaaa",
                         "capability_classes": [CAP], "args": PENDING_IN_A})
    # The UNGROUPED rule must DENY here, or the ALLOW below is the reference
    # engine failing to see the rule rather than the grouping working.
    assert reference_engine.evaluate(pending, prefix,
                                     _pol(UNGROUPED)).decision == "DENY"
    assert reference_engine.evaluate(pending, prefix,
                                     _pol(GROUPED)).decision == "ALLOW"


# --------------------------------------------------------------------------
# The absent group key on the PENDING call. Semantic B, and the alternative
# was real enough to be built and measured before it was refused.
# --------------------------------------------------------------------------

def test_a_pending_call_with_no_group_key_is_in_no_bucket_and_is_ALLOWED():
    """FALSE, not UNEVALUABLE - and the difference is four benign fixtures.

    An unevaluable clause is RETAINED fail-closed, so under the other reading a
    grouped rule keyed on an argument only SOME tools in the class declare
    fires on every call in the class that does not carry it. That is `r_new6`
    one production down: a rule that validates cleanly and blocks the work.

    A capability class holds tools that do not share an argument, so this is
    the ordinary case rather than the corner.
    """
    d = _decide(GROUPED, PENDING_NO_KEY)
    assert d.outcome == "ALLOW"


def test_that_ALLOW_is_a_FALSE_clause_and_never_an_UNEVALUABLE_one():
    """Pinned at the clause rather than at the decision, because the two reach
    the same outcome here only as long as this is the only rule in the policy.
    An UNEVALUABLE clause in a longer `when` is RETAINED, and the difference
    would then reappear.
    """
    engine = PolicyEngine({"rules": []})
    cond = {"form": CLAUSE_EPISODE_SUM, "arg_path": SUM_PATH,
            "group_by": GROUP_PATH, "op": "gte", "value": 4}
    assert engine._clause(cond, PENDING_NO_KEY, PREFIX, {},
                          is_predicate=True) is FALSE
    assert engine._clause(cond, PENDING_IN_A, PREFIX, {},
                          is_predicate=True) is FALSE
    assert engine._clause(cond, {SUM_PATH: 3, GROUP_PATH: "case_A"}, PREFIX, {},
                          is_predicate=True) is TRUE


def test_a_non_integer_on_the_sum_path_is_still_UNEVALUABLE_when_grouped():
    """The ungrouped fold already rules this way: a string where a minor-unit
    integer belongs is a call we cannot reason about, not a call worth zero.
    Grouping does not change what an unreadable amount means."""
    engine = PolicyEngine({"rules": []})
    cond = {"form": CLAUSE_EPISODE_SUM, "arg_path": SUM_PATH,
            "group_by": GROUP_PATH, "op": "gte", "value": 4}
    assert engine._clause(cond, {SUM_PATH: "lots", GROUP_PATH: "case_A"},
                          PREFIX, {}, is_predicate=True) is UNEVALUABLE


# --------------------------------------------------------------------------
# Parsing and serialization.
# --------------------------------------------------------------------------

def test_the_grouping_key_parses_and_is_carried_on_the_clause():
    r = parse_rule(GROUPED)
    cl, = r.clauses
    assert cl.form == CLAUSE_EPISODE_SUM
    assert cl.path == SUM_PATH
    assert cl.group_path == GROUP_PATH


def test_an_ungrouped_episode_sum_still_parses_and_carries_no_key():
    """The negative check. The production is OPTIONAL, and if it ever stopped
    being optional every policy document in the tree would fail to parse."""
    cl, = parse_rule(UNGROUPED).clauses
    assert cl.form == CLAUSE_EPISODE_SUM
    assert cl.group_path is None


def test_the_stored_form_omits_the_key_ENTIRELY_when_it_is_unused():
    """ABSENT, NEVER NULL. Canonicalization restriction 5 forbids a null in a
    hashed payload, and here that rule is what makes the change backward
    compatible at all: `"group_by": null` on an ungrouped fold would re-id
    every rule ever written against `episode_sum`."""
    pred, = compile_rule(parse_rule(UNGROUPED))["match"]["predicates"]
    assert "group_by" not in pred
    assert None not in pred.values()

    pred, = compile_rule(parse_rule(GROUPED))["match"]["predicates"]
    assert pred["group_by"] == GROUP_PATH


def test_a_grouped_rule_and_an_ungrouped_one_are_DIFFERENT_RULES():
    """Same paths, same op, same value, same verb. If these collided, a patch
    retracting one would silently retract the other, and the loop's convergence
    detector - which is rule-id equality - would call a real change a fixpoint.
    """
    assert (assign_rule_id(rule_body(parse_rule(GROUPED)))
            != assign_rule_id(rule_body(parse_rule(UNGROUPED))))


def test_group_by_is_a_bare_keyword_and_not_a_keyword_argument():
    """`=` is deliberately not a token (`crucible/dsl/parser.py`, the comment on
    `_OPERATORS`: "`==` before `=`, which is not a token at all, and must not
    silently become one"). GX2 must not have reopened that."""
    with pytest.raises(ParseError):
        parse_rule("rule r_new1: cap:%s when "
                   "episode_sum(%s, group_by=%s) >= 4 => deny"
                   % (CAP, SUM_PATH, GROUP_PATH))


def test_only_episode_sum_takes_a_grouping_key():
    """The key was added inside ONE production, not to the clause grammar."""
    for bad in ("preceded_by(%s group_by %s)" % (CAP, GROUP_PATH),
                "%s group_by %s == 3" % (SUM_PATH, GROUP_PATH)):
        with pytest.raises(ParseError):
            parse_rule("rule r_new1: cap:%s when %s => deny" % (CAP, bad))


# --------------------------------------------------------------------------
# V10 reaches the second arg_path position.
# --------------------------------------------------------------------------

def _v():
    from crucible.dsl.validator import Validator
    return Validator(fx.MANIFEST_A, fx.DERIVED_B)


def test_V10_refuses_a_grouping_key_no_tool_declares():
    """A grouped clause keyed on an argument no tool carries buckets every call
    under ABSENT - which is to say into no bucket at all - so the clause is
    permanently FALSE and the rule can never fire. That is the
    check-that-cannot-fail shape from the inert side rather than the
    fail-closed one, and V10 says EVERY plain arg_path.
    """
    with pytest.raises(ValidationError) as ei:
        _v().validate_rule(parse_rule(
            "rule r_new1: cap:CAP_MOVES_MONEY when "
            "episode_sum(amount_minor group_by case_idd) >= 4 => deny"))
    assert ei.value.code == "E_UNDECLARED_ARG_PATH"


def test_V10_admits_a_grouping_key_the_manifest_does_declare():
    stored = _v().validate_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when "
        "episode_sum(amount_minor group_by beneficiary_id) >= 50000 => deny"))
    pred, = stored["match"]["predicates"]
    assert pred["group_by"] == "beneficiary_id"


def test_the_product_lexicon_check_does_not_read_group_by_as_a_product_noun():
    """`group_by` is the DSL's own keyword and is subtracted from the harvested
    lexicon the same way `episode_sum` and `preceded_by` are. Without that, V3
    would refuse every grouped rule as naming a product identifier."""
    _v().validate_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when "
        "episode_sum(amount_minor group_by beneficiary_id) >= 50000 => deny"))


# --------------------------------------------------------------------------
# BACKWARD COMPATIBILITY, against a rule this project actually recorded.
# --------------------------------------------------------------------------

# Quoted from `patch_proposals[]` of `evidence/smoke-2026-08-25/run-02.c6.json`
# (proposal `pp_run_20260825_213328_5100ff_r03_a01`), and present verbatim in
# two further bundles under `evidence/pilot-2026-08-25/run-09.c6.json` and
# `evidence/batch-night-2026-08-25/run-02.c6.json`. `evidence/` is gitignored,
# so the pair is carried here rather than read - which is the same treatment
# `tests/golden_traces/policy_v_final.json` gets, and for the same reason.
#
# THIS IS THE ONE RULE IN THE WHOLE RECORD THAT USES THE PRODUCTION GX2
# WIDENED. A hand-written example would prove the serializer is self-consistent
# and nothing more; this one proves an id already written into three bundles
# survives, and it is the ungrouped form by construction because the grouped
# form did not exist when it was written.
RECORDED_UNGROUPED_SUM_RULE = (
    "r_ef66f53e0333",
    "rule r_ef66f53e0333: cap:CAP_MUTATES_DURABLE_STATE when "
    "episode_sum(derived.episode_count_same_subject) >= 4 => deny "
    "origin armorer:3")


def test_a_recorded_ungrouped_rule_still_canonicalises_to_the_id_it_earned():
    """If this fails, every bundle carrying that rule becomes unreadable: the
    offline reader re-hashes each rule's DSL text and REFUSES the bundle when it
    no longer matches the recorded id, rather than measuring a different rule.
    """
    recorded_id, text = RECORDED_UNGROUPED_SUM_RULE
    assert assign_rule_id(rule_body(parse_rule(text))) == recorded_id


def test_that_recorded_rule_round_trips_through_the_armorer_renderer():
    """`render_rule` is what puts the CURRENT POLICY in front of the ARMORER
    every round. A rule that renders back to different text than it was written
    in would be shown to the model as a rule the policy does not hold."""
    from crucible.armorer.render import render_rule
    recorded_id, text = RECORDED_UNGROUPED_SUM_RULE
    stored = compile_rule(parse_rule(text))
    rendered = render_rule(stored)
    assert "group_by" not in rendered
    assert "episode_sum(derived.episode_count_same_subject) >= 4" in rendered
    # and back again, to the same id.
    body = re.sub(r"origin armorer$", "origin armorer:3", rendered.strip())
    assert assign_rule_id(rule_body(parse_rule(body))) == recorded_id


def test_a_grouped_rule_round_trips_through_the_renderer_too():
    stored = compile_rule(parse_rule(GROUPED))
    from crucible.armorer.render import render_rule
    rendered = render_rule(stored)
    assert "episode_sum(%s group_by %s) >= 4" % (SUM_PATH, GROUP_PATH) in rendered
    reparsed = parse_rule(re.sub(r"^rule r_[0-9a-f]{12}:", "rule r_new1:",
                                 rendered.strip()))
    assert assign_rule_id(rule_body(reparsed)) == stored["rule_id"]


def test_the_stored_form_validates_against_the_C4_schema():
    """`predicates` items are `additionalProperties: false`, so an undeclared
    `group_by` would be refused by the contract even though the parser accepted
    it - which is the failure this test exists to have caught once."""
    import jsonschema
    schema = json.loads(
        (fx.REPO / "contracts" / "policy_document.schema.json")
        .read_text(encoding="utf-8"))
    pred = compile_rule(parse_rule(GROUPED))["match"]["predicates"][0]
    item = (schema["$defs"]["rule"]["properties"]["match"]["properties"]
            ["predicates"]["items"])
    jsonschema.validate(pred, item)
