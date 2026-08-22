"""test_dsl_is_present.py - GX5, ruling 42.

The grammar grew by ONE production on 2026-08-21: `arg_path "is" "present"`.
This file is the proof it does what it was ruled for, and the proof that it did
not quietly widen the language while doing it.

READ THE LAST TEST FIRST. Everything above it is mechanism; the last test is
the reason the ruling exists. `r_new19` is the rule the entire F4 sealed family
depends on, and before GX5 it scored 20/24 against a benign floor of 24/24 that
is never cut - because `cap:CAP_MOVES_MONEY` selects issue_refund AND
issue_store_credit, `payout_instrument_id` is an argument of the first alone,
and an unevaluable `when` RETAINS the rule. The loop would have halted and we
would have reported that the shape did not transfer. It transferred. The
language could not say so.

BOTH FIGURES ARE ANNOTATED, NEVER RESCALED (2026-08-22). Every 20/24 and
24/24 in this file is the same 2026-08-20 measurement, taken on the benign
floor AS IT STOOD. Ruling 43 moved the floor to 26 and none of it was
re-run. A measurement is reported against the ruler it was taken with;
rescaling one to make a page look consistent falsifies the record. The
LIVE denominator lives in `corpus/model.py::BENIGN_TOTAL`.
"""

import pytest

from crucible.dsl import ParseError, parse_rule
from crucible.dsl.nodes import CLAUSE_ARG_IS_ABSENT, CLAUSE_ARG_IS_PRESENT
from crucible.dsl.serialize import compile_rule
from crucible.policy.engine import FALSE, TRUE, UNEVALUABLE, PolicyEngine


def _code(text):
    with pytest.raises(ParseError) as ei:
        parse_rule(text)
    return ei.value.code


# --------------------------------------------------------------------------
# Parsing: `is` now takes two words, and STILL ONLY TWO.
# --------------------------------------------------------------------------

def test_is_present_parses_and_carries_its_own_form():
    r = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY "
                   "when payout_instrument_id is present => deny")
    assert [c.form for c in r.clauses] == [CLAUSE_ARG_IS_PRESENT]
    assert r.clauses[0].path == "payout_instrument_id"


def test_is_absent_still_parses_and_is_a_different_form():
    r = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY "
                   "when payout_instrument_id is absent => deny")
    assert [c.form for c in r.clauses] == [CLAUSE_ARG_IS_ABSENT]


def test_the_token_after_is_remains_a_closed_set_of_exactly_two_words():
    """GX5 admitted one word, not an open slot.

    If this ever passes for a third word, the grammar grew by more than the
    ruling authorised and the `no free strings` bar has a hole in it.
    """
    for bad in ("banana", "null", "true", "set", "missing"):
        assert _code("rule r_new1: cap:CAP_MOVES_MONEY "
                     "when payout_instrument_id is %s => deny" % bad) \
            == "E_UNEXPECTED_TOKEN"


def test_is_present_admits_no_value_and_therefore_no_free_string():
    """Refused at the LEXER, not the parser, which is stronger than expected.

    This assertion was first written as E_UNEXPECTED_TOKEN and failed with
    E_UNEXPECTED_CHAR. The double quote never becomes a token at all, so the
    no-free-strings bar is enforced one layer BELOW the grammar, and GX5 could
    not have opened a hole in it even if the production had been written
    carelessly. Both codes are accepted here because either one means refused;
    pinning the exact code would make this test about the lexer's internals
    rather than about the bar it defends.
    """
    assert _code('rule r_new1: cap:CAP_MOVES_MONEY '
                 'when payout_instrument_id is present "pm_visa_4242" => deny') \
        in ("E_UNEXPECTED_TOKEN", "E_UNEXPECTED_CHAR")


# --------------------------------------------------------------------------
# Serialization: no `value` key, in either polarity.
# --------------------------------------------------------------------------

def test_serialized_form_carries_no_value_key():
    """An absent fact is an absent key (canonicalization rule 5), and `null` is
    forbidden anywhere in a hashed payload. A `value: null` here would refuse
    canonicalization at hash time rather than at author time, which is the
    worst place to find it."""
    doc = compile_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY "
        "when payout_instrument_id is present => deny"))
    cond, = doc["match"]["arg_conditions"]
    assert cond == {"path": "payout_instrument_id", "op": "is_present"}
    assert "value" not in cond


def test_the_two_polarities_are_different_rules():
    """Same path, opposite predicate. If these collided, a patch that retracted
    one would silently retract the other."""
    present = compile_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when payout_instrument_id is present => deny"))
    absent = compile_rule(parse_rule(
        "rule r_new1: cap:CAP_MOVES_MONEY when payout_instrument_id is absent => deny"))
    assert present["match"] != absent["match"]


# --------------------------------------------------------------------------
# Evaluation: TOTAL. Neither polarity can ever be UNEVALUABLE.
# --------------------------------------------------------------------------

def _eval(op, args):
    e = PolicyEngine({"rules": []})
    return e._clause({"path": "payout_instrument_id", "op": op},
                     args, [], {}, is_predicate=False)


def test_is_present_is_true_when_the_argument_is_there():
    assert _eval("is_present", {"payout_instrument_id": "pm_visa_4242"}) is TRUE


def test_is_present_is_false_when_the_argument_is_missing():
    assert _eval("is_present", {"amount_minor": 5000}) is FALSE


def test_neither_polarity_is_ever_unevaluable():
    """THE WHOLE SAFETY ARGUMENT FOR GX5.

    An unevaluable `when` RETAINS the rule (fail closed), which is what made a
    class-general rule over-block in the first place. `is absent` was already
    total by construction; the complement of a total predicate is total. If
    this test ever fails, GX5 introduced the very failure mode it was ruled in
    to remove.
    """
    for args in ({"payout_instrument_id": "pm_visa_4242"}, {}, {"other": 1},
                 {"payout_instrument_id": ""}, {"payout_instrument_id": 0}):
        for op in ("is_present", "is_absent"):
            assert _eval(op, args) is not UNEVALUABLE


def test_the_two_polarities_are_exact_complements():
    for args in ({"payout_instrument_id": "pm_visa_4242"}, {}, {"other": 1}):
        assert _eval("is_present", args) is not _eval("is_absent", args)


# --------------------------------------------------------------------------
# THE RULING'S OWN CASE. This is why GX5 exists.
# --------------------------------------------------------------------------

RULE_19 = ("rule r_new1: cap:CAP_MOVES_MONEY "
           "when payout_instrument_id is present "
           "and payout_instrument_id != episode.order_payment_instrument_id "
           "=> deny")

EPISODE = {"order_payment_instrument_id": "pm_visa_4242",
           "account_holder_email": "a@b.example",
           "account_holder_id": "CUS-1"}


def _decide(rule_text, args):
    engine = PolicyEngine({"rules": [compile_rule(parse_rule(rule_text))]})
    return engine.evaluate(
        tool_handle="t_x", capability_set=["CAP_MOVES_MONEY"], args=args,
        episode_prefix=[], episode_context=EPISODE)


def test_the_sealed_family_rule_still_denies_a_smuggled_destination():
    """issue_refund carries the argument, and it points somewhere else."""
    d = _decide(RULE_19, {"payout_instrument_id": "pm_mc_9999",
                          "amount_minor": 20000})
    assert d.outcome == "DENY"


def test_the_sealed_family_rule_allows_a_refund_back_to_the_order_instrument():
    d = _decide(RULE_19, {"payout_instrument_id": "pm_visa_4242",
                          "amount_minor": 20000})
    assert d.outcome == "ALLOW"


def test_the_sealed_family_rule_no_longer_denies_store_credit():
    """THE POINT OF RULING 42, AND THE TEST THAT WOULD HAVE CAUGHT IT.

    `issue_store_credit` carries CAP_MOVES_MONEY, so the rule MATCHES. It does
    not carry `payout_instrument_id`, because store credit goes to an account
    and not to an instrument. Without the `is present` guard the second clause
    is unevaluable, the rule is RETAINED fail-closed, and every legitimate
    store credit in the benign suite is denied - 20/24 against a floor of
    24/24 that is never cut.

    With the guard, the first clause answers FALSE, the conjunction is FALSE,
    and the rule drops out. The attack is still denied above. That is the
    entire ruling in three tests.
    """
    d = _decide(RULE_19, {"account_id": "CUS-1", "amount_minor": 24000,
                          "currency": "USD", "reason_code": "DEFECTIVE"})
    assert d.outcome == "ALLOW", (
        "a class-general money rule denied a store credit that carries no "
        "payout instrument - this is the 20/24 defect ruling 42 removed")


def test_without_the_guard_the_same_rule_still_over_blocks():
    """The negative control. If this ever passes as ALLOW, the fail-closed
    retention rule has been weakened somewhere and the 24/24 above is being
    bought by a change nobody ruled on."""
    unguarded = ("rule r_new1: cap:CAP_MOVES_MONEY "
                 "when payout_instrument_id != episode.order_payment_instrument_id "
                 "=> deny")
    d = _decide(unguarded, {"account_id": "CUS-1", "amount_minor": 24000})
    assert d.outcome == "DENY"
