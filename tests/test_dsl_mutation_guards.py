"""test_dsl_mutation_guards.py - the L3 half of the mutation audit.

WHY THIS FILE EXISTS
---------------------
`docs/decisions-pending/mutation-audit-2026-08-22.md` mutated seven load-bearing
surfaces and closed its own report with a named next target:

    Not mutated: `crucible/dsl/` and `policy/engine.py` - the largest untouched
    surface and the obvious next audit.

This is that audit. 61 mutations across the parser, the validator's numbered
rules V1-V10, the serializer's content-addressed rule ids, and the POLICY_ENGINE.
48 were killed. THIRTEEN SURVIVED, and every one of them is closed below.

The surface matters more than its line count. THE DSL IS WHAT THE ARMORER WRITES
INTO: every patch the loop will ever produce is text in this grammar, parsed by
this parser, judged by this validator, hashed by this serializer and executed by
this engine. Nothing downstream re-checks the grammar - the Warden scores what
the policy DOES, not whether the policy says what its author meant.

THE METHOD, unchanged from the first audit: break the invariant at the source in
the smallest way that makes the claim false, run the WHOLE suite, record whether
anything went red, restore, assert byte-identity, and confirm `git status
--short` is clean before the next one. A mutation that SURVIVES is a finding -
that invariant is unguarded no matter how many tests appear to cover it.

Every test below is NAMED with the mutation it closes and was proven RED under
that mutation and GREEN without it. EACH ONE CARRIES A POSITIVE CONTROL IN THE
SAME FUNCTION - the arrangement that DOES fire - because a guard that rejects
everything passes for the wrong reason, and that is the exact defect being
closed.

The full table, including the 48 that were correctly killed, is
`docs/decisions-pending/dsl-mutation-audit-2026-08-22.md`.
"""

import copy
import dataclasses

import pytest

from crucible.dsl import parse_policy, parse_rule
from crucible.dsl.errors import ParseError, ValidationError
from crucible.dsl.nodes import (
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
    UNCLASSIFIED,
    Clause,
)
from crucible.dsl.serialize import compile_rule
from crucible.dsl.validator import Validator, validate_policy_document
from crucible.policy.decision import ALLOW, DENY
from crucible.policy.engine import PolicyEngine

from . import l3_fixtures as fx


def _validator():
    return Validator(fx.MANIFEST_A, fx.DERIVED_B)


def _code(fn):
    """The refusal code, or an assertion failure naming what was accepted."""
    try:
        out = fn()
    except (ValidationError, ParseError) as e:
        return e.code
    pytest.fail("expected a refusal, got %r" % (out,))


def _decide(rule, args, prefix=(), caps=("CAP_MOVES_MONEY",)):
    return PolicyEngine(fx.policy(rule)).evaluate(
        tool_handle=fx.T_REFUND, capability_set=set(caps), args=args,
        episode_prefix=prefix).outcome


# ==========================================================================
# TIER 1 - the decision on a live call. A survivor here changes what the
# target is allowed to do, on the enforcement path, at run time.
# ==========================================================================

def test_E3_constrain_arg_FAILS_CLOSED_on_absent_null_and_wrong_typed_arguments():
    """`constrain_arg` treats absent, null and wrong-typed as VIOLATED.

    KILLS TWO MUTATIONS. E3 relaxed `if verdict == TRUE: return None` to
    `if verdict != FALSE`, which lets UNEVALUABLE mean "no restriction". E3b
    returned early on an absent argument. Both survived the whole suite.

    THIS IS THE SINGLE MOST DANGEROUS INVERSION IN THE GRAMMAR and it is the
    one the engine's own docstring is loudest about: "an absent, null, or
    wrong-typed argument means we do not know that the rule is inapplicable,
    and 'we do not know' must not read as 'allow'." Failing open here is not a
    rule that stops working - it is a rule that stops working ON EXACTLY THE
    CALLS AN ATTACKER CONTROLS THE SHAPE OF. A `constrain_arg(amount_minor <=
    50000)` learned from a breach is defeated by sending `amount_minor` as a
    string, or by omitting it and letting a default apply downstream, and the
    Warden sees a policy that passed every benign fixture.

    Nothing in the suite covered it because every fixture and every golden
    trace carries a well-typed `amount_minor`. The three shapes below are the
    ones `check_totality`'s own synthetic sweep enumerates, which is the tell:
    V8 asserts the engine does not CRASH on them and nothing asserted what it
    DECIDES.
    """
    r = fx.rule("r_000000000001", "constrain_arg", "CAP_MOVES_MONEY",
                arg_conditions=[],
                action={"path": "amount_minor", "op": "lte", "value": 50000,
                        "value_type": "int"})

    # POSITIVE CONTROL. The verb is live in both directions: a satisfied
    # constraint imposes nothing, a violated one denies. Without this pair the
    # three assertions below would pass against an engine that denies
    # everything.
    assert _decide(r, {"amount_minor": 1000}) == ALLOW
    assert _decide(r, {"amount_minor": 90000}) == DENY

    assert _decide(r, {}) == DENY, "an ABSENT argument is VIOLATED"
    assert _decide(r, {"amount_minor": None}) == DENY, "a NULL argument is VIOLATED"
    assert _decide(r, {"amount_minor": "90000"}) == DENY, \
        "a STRING where a minor-unit integer belongs is VIOLATED"


def test_E14_preceded_by_reads_the_CLASS_IT_NAMES_and_not_merely_ANY_predecessor():
    """`preceded_by(X)` is TRUE only when a visible predecessor carried X.

    E14 made the loop return TRUE on the first visible event regardless of its
    capability classes, and the whole suite stayed green.

    BLAST RADIUS: `preceded_by` IS THE SEPARATING PREDICATE OF THE F5 FAMILY.
    EIGHT of the ten `corpus/training/F5-*.json` instances name it in
    `separable_by` (counted at source 2026-08-22; F5-04 and F5-08 do not), and
    `corpus/pairs.json` names it as the discriminating feature of the
    composition pairs. An engine that ignores WHICH class
    preceded turns every one of those rules into "deny anything that follows
    anything", which passes the attack half of each pair and destroys the
    near-miss half - and over-blocking is the trivial defeat of any attack
    suite, which is why the benign floor is 100% and on the never-cut list.
    The suite's existing `preceded_by` coverage all runs the TRUE arrangement
    or an empty prefix; nobody ran a prefix carrying the WRONG class.
    """
    r = fx.rule("r_000000000002", "deny", "CAP_MOVES_MONEY",
                predicates=[{"form": "preceded_by", "value": "CAP_INVOKES_AGENT"}])

    right = (fx.executed({"CAP_INVOKES_AGENT"}, seq=0),)
    wrong = (fx.executed({"CAP_READS_PII"}, seq=0),)

    # POSITIVE CONTROL. The predicate fires when the named class really is in
    # the prefix, and does not fire on an empty one. A guard asserting only
    # "wrong class -> ALLOW" would pass against a rule that never matches.
    assert _decide(r, {}, prefix=right) == DENY
    assert _decide(r, {}, prefix=()) == ALLOW

    assert _decide(r, {}, prefix=wrong) == ALLOW, \
        "a predecessor carrying a DIFFERENT class does not satisfy preceded_by"


def test_E10_a_TYPE_MISMATCH_retains_the_rule_rather_than_dropping_it():
    """`_compare` returns UNEVALUABLE, never FALSE, on a type mismatch.

    E10 turned the ordered-comparison type gate into FALSE. Nothing went red.

    The direction is the whole finding. FALSE removes the rule from
    consideration, and the engine's docstring names that exactly: "reporting a
    mismatch as False would silently drop the rule, which is failing OPEN
    through the back door - the rule stops applying because of a type, not
    because of a fact." UNEVALUABLE retains it (fail closed). The suite covers
    the absent-argument road into UNEVALUABLE and never the wrong-typed one,
    so the guard is written on the road nobody drove.
    """
    r = fx.rule("r_000000000003", "deny", "CAP_MOVES_MONEY",
                arg_conditions=[{"path": "amount_minor", "op": "gte",
                                 "value": 50000, "value_type": "int"}])

    # POSITIVE CONTROL. The clause is live in both directions - over the
    # threshold denies, under it allows - so the assertion below cannot pass
    # against a rule that matches everything or nothing.
    assert _decide(r, {"amount_minor": 90000}) == DENY
    assert _decide(r, {"amount_minor": 1000}) == ALLOW

    assert _decide(r, {"amount_minor": "90000"}) == DENY, \
        "a string where an integer belongs is UNEVALUABLE, and UNEVALUABLE RETAINS"


def test_E11_a_BOOLEAN_is_not_an_INTEGER_when_money_is_being_summed():
    """`_is_int` is `type(x) is int`, never `isinstance`.

    E11 relaxed it to `isinstance`, and the whole suite stayed green.

    `bool` subclasses `int` in Python, so under `isinstance` a boolean argument
    is swept into an `episode_sum` as one minor unit. That is a money total
    assembled partly out of flags. `crucible/canon/canonical.py` documents the
    same trap for serialization and the engine repeats it in a comment - `True
    < 5` is a legal comparison that means nothing here - and nothing tested it
    on either side.

    Written on the AGGREGATE road rather than the `_compare` road on purpose:
    the `_compare` road is a special case of the type gate mutation E10 already
    disables, so a guard written there would go red under two different
    mutations and prove neither.
    """
    r = fx.rule("r_000000000004", "deny", "CAP_MOVES_MONEY",
                predicates=[{"form": "episode_sum", "arg_path": "amount_minor",
                             "op": "gte", "value": 2}])
    booleans = (fx.executed({"CAP_MOVES_MONEY"}, args={"amount_minor": True}, seq=0),
                fx.executed({"CAP_MOVES_MONEY"}, args={"amount_minor": True}, seq=1))
    integers = (fx.executed({"CAP_MOVES_MONEY"}, args={"amount_minor": 1}, seq=0),
                fx.executed({"CAP_MOVES_MONEY"}, args={"amount_minor": 1}, seq=1))

    # POSITIVE CONTROL. The same two events carrying REAL integers do reach the
    # threshold and do deny, so the assertion below is about the type and not
    # about a predicate that never fires.
    assert _decide(r, {}, prefix=integers) == DENY
    assert _decide(r, {}, prefix=()) == ALLOW

    assert _decide(r, {}, prefix=booleans) == ALLOW, \
        "two booleans are not two minor units and must not sum to the cap"


# ==========================================================================
# TIER 2 - the abstraction claim. Every terminal in this grammar is abstract
# or manifest-declared, and that sentence is what headline result #1 rests on.
# ==========================================================================

# V1 - `cap_selector` required and FIRST - HAS NO GUARD HERE, DELIBERATELY.
# It is the mechanism behind headline result #1 and it is already covered:
# `tests/test_dsl_parser.py::test_cap_selector_is_required_and_first` kills a
# parser that lets a tool-only rule through. The audit's FIRST cut at that
# mutation survived and would have been filed as a finding - it made
# `selector()` return a default class, after which the very next `expect("=>")`
# tripped on the `tool` token and the text still failed to parse with the same
# error code. A mutation that survives because it did not change the observable
# is not evidence of a gap. Written down in the audit rather than closed with a
# duplicate test.


def test_P7_preceded_by_UNCLASSIFIED_is_refused_BY_ITS_OWN_NAME():
    """The refusal carries `E_UNCLASSIFIED_SELECTOR`, not a generic one.

    P7 deleted the explicit branch. The suite stayed green because the token
    then falls through to the six-class check and is still refused - with
    `E_UNKNOWN_CAP_CLASS`.

    That is precisely the failure the parser's docstring predicts for the
    selector form and which `l3_checks.py` guards there and only there: "a
    generic 'unknown capability class' error would fire today AND STOP FIRING
    THE MOMENT SOMEBODY ADDED UNCLASSIFIED TO A LIST for an unrelated
    reason." `UNCLASSIFIED` is the fail-open sentinel - it means we do not know
    what this tool does - and it is one list membership away from being
    admissible in the composition predicate while remaining refused in the
    selector. The ARMORER also gets ONE repair attempt with this code as its
    sole feedback, and the two codes point at different repairs.
    """
    # POSITIVE CONTROL. A real class parses here, and an invented one gets the
    # OTHER code - so this test distinguishes two live refusals rather than
    # asserting that everything is rejected.
    assert parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when preceded_by(CAP_READS_PII) "
        "=> deny").clauses
    assert _code(lambda: parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when preceded_by(CAP_NOPE) => deny")) \
        == "E_UNKNOWN_CAP_CLASS"

    assert _code(lambda: parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when preceded_by(UNCLASSIFIED) "
        "=> deny")) == "E_UNCLASSIFIED_SELECTOR"


def test_D2_the_VALIDATOR_refuses_UNCLASSIFIED_on_a_rule_the_parser_never_saw():
    """V2, re-asserted off the parse tree rather than only at the lexer.

    D2 disabled `check_selector`'s UNCLASSIFIED branch and the suite stayed
    green, because every committed test reaches the validator THROUGH the
    parser and the parser refuses the text first.

    The validator's own docstring states the claim this closes: V2 is
    "re-asserted here SO THE REFUSAL SURVIVES SOMEONE BUILDING A RULE WITHOUT
    IT." Today the parser is the only producer of a `ParsedRule`, so this is
    defence in depth rather than an open door - and an assertion nobody has
    ever seen fail is an assertion nobody knows still works. The rule is built
    here the way that second producer would build it.

    What it defends is not small: `cap:UNCLASSIFIED => deny` on an unseen
    target blocks everything, because an unmapped tool is UNCLASSIFIED until
    the manifest maps it. That is the headline transfer result, manufactured.
    """
    base = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY => deny")

    # POSITIVE CONTROL. The same rule with a real class validates, so the
    # refusal below is about the sentinel and not about the hand-built node.
    assert _validator().validate_rule(base)["rule_id"].startswith("r_")

    forged = dataclasses.replace(base, cap_class=UNCLASSIFIED)
    assert _code(lambda: _validator().validate_rule(forged)) \
        == "E_UNCLASSIFIED_SELECTOR"


def test_D3_the_VALIDATOR_refuses_a_SEVENTH_capability_class():
    """`CAP_CLASSES` is six and there is no seventh - checked at the validator.

    D3 disabled the membership branch in `check_selector`; the suite stayed
    green for the same reason D2 did. Kept separate from D2 because the two
    branches defend different things: D2 is the fail-open sentinel, this is a
    class the manifest can never map, so a rule naming it matches nothing, ever
    - the silent-no-op shape that `match_mode` was DELETED rather than pinned
    to avoid.
    """
    base = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY => deny")

    # POSITIVE CONTROL. Six classes in, six classes out.
    assert _validator().validate_rule(base)["match"]["capability_class"] \
        == "CAP_MOVES_MONEY"

    forged = dataclasses.replace(base, cap_class="CAP_INVENTED")
    assert _code(lambda: _validator().validate_rule(forged)) == "E_UNKNOWN_CAP_CLASS"


def test_D22_an_UNDECLARED_episode_context_field_is_refused_by_the_validator():
    """The three `episode.*` bindings resolve against Part B.

    D22 disabled `check_context_fields` and the suite stayed green - again
    because the parser's `CONTEXT_FIELDS` list refuses the text first.

    The two lists are not the same artifact and that is the point. The parser
    holds a frozen tuple in `nodes.py`; the validator resolves against PART B,
    which freezes at D5 with the corpus and is gated on the label-blindness
    check. Ruling 20 makes them two artifacts with two hashes and two freeze
    dates on purpose. A context field admitted by the grammar but undeclared by
    Part B is a comparison against a fact the episode seal does not carry, and
    `episode.*` is frozen before the first user turn precisely so that F4 rests
    on it.

    NOTE FOR THE COORDINATOR, not closed here: this check carries an emptiness
    escape - `if self.declared_episode and ...` - so a Part B declaring no
    episode fields switches it off in silence. V10 refused that shape one
    check over and said why. Reported, not changed.
    """
    base = parse_rule("rule r_new1: cap:CAP_EXTERNAL_COMMS => deny")
    declared = Clause(form=CLAUSE_ARG_VS_EPISODE_CONTEXT, path="to", op="==",
                      context_field="account_holder_email")
    invented = Clause(form=CLAUSE_ARG_VS_EPISODE_CONTEXT, path="to", op="==",
                      context_field="account_holder_secret")

    # POSITIVE CONTROL. A DECLARED field on the same clause form validates, so
    # the refusal below is about the name and not about the form.
    assert _validator().validate_rule(dataclasses.replace(base, clauses=[declared]))

    assert _code(lambda: _validator().validate_rule(
        dataclasses.replace(base, clauses=[invented]))) \
        == "E_UNDECLARED_EPISODE_FIELD"


# ==========================================================================
# TIER 3 - the canonical form. A survivor here gives one policy two hashes,
# which breaks convergence-by-hash-equality and the resume key together.
# ==========================================================================

def test_D17_a_policy_document_whose_rules_are_OUT_OF_ORDER_is_refused():
    """Canonicalization restriction 6: `rules` are stored PRE-SORTED by
    `rule_id` ascending.

    D17 disabled `E_RULES_NOT_SORTED` and the whole suite stayed green. The
    string appears in no test in the repo.

    Sorting AT CONSTRUCTION rather than at hash time is what makes the
    canonical form unambiguous - `serialize.py` argues that sorting at hash
    time "would look lossless and be destructive". The check in
    `validate_policy_document` is the only thing that notices a document which
    skipped that step, and a stored document that is not in canonical order is
    a policy that hashes one way here and another way after a round trip.
    """
    doc = copy.deepcopy(fx.POLICY_DOC_VALID)
    ids = [r["rule_id"] for r in doc["hashed_payload"]["rules"]]
    assert ids == sorted(ids) and len(ids) > 1, \
        "the golden fixture must be sorted and must have something to reorder"

    # POSITIVE CONTROL. The document as shipped validates, so the refusal below
    # is about the ORDER and not about some other defect in the fixture.
    validate_policy_document(doc)

    out_of_order = copy.deepcopy(doc)
    out_of_order["hashed_payload"]["rules"].reverse()
    assert _code(lambda: validate_policy_document(out_of_order)) \
        == "E_RULES_NOT_SORTED"


def test_S8_a_validated_patch_emits_its_rules_SORTED_whatever_order_they_arrived():
    """`sort_rules` is what puts `validate_patch`'s output in canonical order.

    S8 turned it into `list(rules)` and the suite stayed green: the patch
    output then carries the rules in dict-insertion order - the pre-existing
    policy first, the newly added rule after it - and nothing checked.

    Paired with D17 this is the whole hole. S8 produces the unsorted document
    and D17 is the only thing that would refuse it; both survived, so a policy
    could be written out of canonical order and read back without complaint.
    The fixture below is chosen so insertion order and sorted order DISAGREE -
    the existing rule's id is `r_ffff...`, which sorts last, and it is handed
    in first.
    """
    v = _validator()
    existing = fx.rule("r_ffffffffffff", "deny", "CAP_READS_PII", origin="seed")
    current = {"policy_schema_version": 1, "target_manifest_hash": "0" * 16,
               "rules": [existing]}

    payload = v.validate_patch(
        parse_policy("rule r_new1: cap:CAP_MOVES_MONEY => deny origin armorer:1"),
        current)
    ids = [r["rule_id"] for r in payload["rules"]]

    # POSITIVE CONTROL. Both rules really are in the output and the arrangement
    # really does disagree with insertion order - otherwise "sorted" would be
    # true of a one-element list and would prove nothing.
    assert len(ids) == 2 and "r_ffffffffffff" in ids
    assert ids[-1] == "r_ffffffffffff", "the pre-existing rule must sort LAST"

    assert ids == sorted(ids), "validate_patch emits rules in canonical order"


def test_S6_TWO_CLAUSE_ORDERS_are_one_rule_and_therefore_one_rule_id():
    """`arg_conditions` are sorted AT CONSTRUCTION - restriction 6 names them.

    S6 removed the sort and the whole suite stayed green.
    `test_convention_3_clause_order_does_not_move_the_id` looks like the guard
    for this and is not: it writes exactly ONE `arg_condition`, and a
    one-element list is sorted in every order. It covers `predicates` and
    `tool_names`, the two arrays restriction 6 does NOT name, and leaves
    uncovered the one it does.

    `rule_id` is content-addressed, so an unsorted array means THE SAME
    SEMANTIC RULE GETS TWO IDS depending on the order the ARMORER happened to
    write its clauses - and the ARMORER is a model, so that order is not
    stable. `add_rule` of an existing rule then stops being detectably a no-op,
    which is the per-rule half of the convergence detector.
    """
    v = _validator()
    a = v.validate_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50000 "
        "and reason_code == DEFECTIVE => deny"))
    b = v.validate_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when reason_code == DEFECTIVE "
        "and amount_minor >= 50000 => deny"))

    # POSITIVE CONTROL. A rule that is genuinely different gets a different id,
    # so equality below is not the trivial equality of a hash over nothing.
    c = v.validate_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50001 "
        "and reason_code == DEFECTIVE => deny"))
    assert a["rule_id"] != c["rule_id"]
    assert len(a["match"]["arg_conditions"]) == 2, "two clauses, or nothing to sort"

    assert a["rule_id"] == b["rule_id"], \
        "clause order is not part of what the rule MEANS and must not move its id"


def test_the_compiled_form_and_the_validated_form_agree_on_the_id():
    """A cheap invariant this file leans on, asserted rather than assumed.

    Every guard above that compares ids reads them off `validate_rule`;
    `compile_rule` is the function that actually assigns them. If those two
    ever diverged, S6's guard would be measuring the wrong function.
    """
    parsed = parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50000 => deny")
    assert compile_rule(parsed)["rule_id"] == \
        _validator().validate_rule(parsed)["rule_id"]
