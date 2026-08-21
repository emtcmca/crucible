"""test_dsl_parser.py - grammar coverage for `contracts/policy.ebnf`.

The two parse-level negative checks (N2 `cap:A|B`, N5 `cap:UNCLASSIFIED`) live
in `tests/l3_checks.py` because they also have to run against a permissive
strawman. This file covers the rest of the grammar: the three verbs, the three
episode-scoped predicate forms, retractions, and the no-free-strings bar.

The bar is the one to read twice. A language that cannot express a string match
CANNOT LEARN A STRING FILTER, so the held-out-family result is true BY
CONSTRUCTION rather than by discipline. Every test below that asserts a refusal
of a quoted string is defending that sentence.
"""

import pytest

from crucible.dsl import ParseError, parse_policy, parse_rule
from crucible.dsl.nodes import (
    CLAUSE_ARG_IN_ENUM_LIST,
    CLAUSE_ARG_IS_ABSENT,
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
    CLAUSE_EPISODE_SUM,
    CLAUSE_PRECEDED_BY,
)


def _code(text):
    with pytest.raises(ParseError) as ei:
        parse_rule(text)
    return ei.value.code


# --------------------------------------------------------------------------
# The three verbs, and there is no fourth.
# --------------------------------------------------------------------------

def test_the_three_verbs_parse():
    assert parse_rule("rule r_new1: cap:CAP_MOVES_MONEY => deny").action.verb == "deny"

    ca = parse_rule("rule r_new2: cap:CAP_MOVES_MONEY "
                    "=> constrain_arg(amount_minor <= 5000)").action
    assert (ca.verb, ca.path, ca.op, ca.value) == ("constrain_arg", "amount_minor",
                                                   "<=", 5000)

    ra = parse_rule("rule r_new3: cap:CAP_MOVES_MONEY "
                    "=> require_approval(SUPERVISOR_REVIEW)").action
    assert (ra.verb, ra.reason_code) == ("require_approval", "SUPERVISOR_REVIEW")


def test_a_fourth_verb_is_refused_by_name():
    """A fourth verb - log_only, rate_limit, sanitize - either introduces state,
    introduces content inspection, or introduces a non-blocking outcome the
    TRIPWIRE cannot score as a boolean. There is also no `allow` verb: the
    policy is SUBTRACTIVE ONLY, so no sequence of patches can widen the
    target's blast radius."""
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY => log_only") == "E_UNKNOWN_VERB"
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY => allow") == "E_UNKNOWN_VERB"


# --------------------------------------------------------------------------
# The selector.
# --------------------------------------------------------------------------

def test_cap_selector_is_required_and_first():
    """There is no way to write a rule that binds ONLY to a tool, which is the
    mechanism behind headline result #1: every learned rule generalizes to
    exactly one capability class."""
    assert _code("rule r_new1: tool:t_9f2c1b77 => deny") == "E_UNEXPECTED_TOKEN"


def test_role_is_gone_from_the_grammar():
    """Ruling 25. `role_name` was the ONLY plain-text product identifier this
    grammar admitted, and it was not covered by the product-lexicon denylist -
    which is harvested from tool names and descriptions. The ARMORER could
    therefore bind a learned rule to one product string and pass validation,
    an escape hatch out of headline result #1's own stated mechanism.

    `role` is still RECORDED on every ToolEvent and still resolved by the
    adapter. What changed is only whether a rule may BIND to it.
    """
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY, role:root_agent => deny") \
        == "E_UNEXPECTED_TOKEN"


def test_tool_handles_must_be_opaque():
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY, tool:issue_refund => deny") \
        == "E_BAD_TOOL_HANDLE"
    r = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY, tool:t_9f2c1b77 => deny")
    assert r.tool_handles == ["tool:t_9f2c1b77"]


# --------------------------------------------------------------------------
# The three episode-scoped forms. Section 5 added all three at once and each
# one makes a specific family expressible.
# --------------------------------------------------------------------------

def test_preceded_by_makes_F5_expressible():
    c = parse_rule("rule r_new1: cap:CAP_EXTERNAL_COMMS "
                   "when preceded_by(CAP_READS_PII) => deny").clauses[0]
    assert (c.form, c.cap_class) == (CLAUSE_PRECEDED_BY, "CAP_READS_PII")


def test_episode_sum_makes_F7_expressible():
    c = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY "
                   "when episode_sum(amount_minor) > 50000 => deny").clauses[0]
    assert (c.form, c.path, c.op, c.value) == (CLAUSE_EPISODE_SUM,
                                               "amount_minor", ">", 50000)


def test_episode_sum_compares_to_an_integer_only():
    """`episode_sum(p) <op> INTEGER` - not `literal`. A sum is a number; letting
    it compare to an enum symbol would be a type error the grammar can prevent
    for free."""
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY "
                 "when episode_sum(amount_minor) > BIG => deny") \
        == "E_UNEXPECTED_TOKEN"


def test_arg_vs_episode_context_is_the_one_the_proof_demands():
    """Three of the four mandated near-miss fixtures differ from their paired
    attack ONLY by destination or recipient identity. Without this form, any
    rule that blocks the attack breaks the fixture and any rule that preserves
    the fixture cannot see the difference - G3 rejects every round, two
    rejections halt the loop, and THE LOOP NEVER PROMOTES."""
    c = parse_rule("rule r_new1: cap:CAP_EXTERNAL_COMMS "
                   "when to != episode.account_holder_email => deny").clauses[0]
    assert (c.form, c.path, c.op, c.context_field) == (
        CLAUSE_ARG_VS_EPISODE_CONTEXT, "to", "!=", "account_holder_email")


def test_the_asymmetry_is_enforced_an_episode_fact_cannot_be_the_left_side():
    """The production is `arg_path cmp_op episode.field`. There is NO clause
    form `episode.field cmp_op literal`. An episode context fact can only ever
    be compared to AN ARGUMENT OF THE PENDING CALL, never tested against a
    literal - which is why the `derived.*` namespace is load-bearing rather
    than a convenience.

    It parses as an ordinary arg_path here (the grammar has no opinion about
    names) and the VALIDATOR refuses it, same shape as ruling 24's exhibit.
    """
    r = parse_rule("rule r_new1: cap:CAP_EXTERNAL_COMMS "
                   "when episode.account_holder_email == NOBODY => deny")
    assert r.clauses[0].path == "episode.account_holder_email"


def test_an_unknown_context_field_is_named():
    assert _code("rule r_new1: cap:CAP_EXTERNAL_COMMS "
                 "when to == episode.shipping_city => deny") \
        == "E_UNKNOWN_CONTEXT_FIELD"


# --------------------------------------------------------------------------
# NO FREE STRINGS. The bar.
# --------------------------------------------------------------------------

def test_a_quoted_string_is_not_a_literal():
    assert _code('rule r_new1: cap:CAP_EXTERNAL_COMMS '
                 'when to == "attacker@evil.invalid" => deny') \
        == "E_UNEXPECTED_CHAR"


def test_a_lowercase_word_is_not_a_literal_either():
    """The cheapest way around a quote check is to drop the quotes. An
    enum_symbol is UPPER_SNAKE, so a bare lowercase word is not a literal - and
    it is not silently read as an arg_path on the right-hand side."""
    assert _code("rule r_new1: cap:CAP_EXTERNAL_COMMS "
                 "when to == attacker => deny") == "E_BAD_LITERAL"


def test_no_floats():
    """Money is INT64 MINOR UNITS plus an ISO-4217 currency string. A float
    anywhere in a hashed payload is what canonicalization restriction 4 exists
    to prevent, and the grammar keeps it from ever getting that far."""
    assert _code("rule r_new1: cap:CAP_MOVES_MONEY "
                 "when amount >= 500.50 => deny") in ("E_UNEXPECTED_TOKEN",
                                                      "E_BAD_ARG_PATH")


def test_booleans_negatives_and_enum_lists():
    r = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY "
                   "when derived.delivery_confirmed == false "
                   "and derived.days_since_delivery >= -1 "
                   "and reason_code in [DEFECTIVE, CHANGED_MIND] "
                   "and tracking is absent => deny")
    forms = [c.form for c in r.clauses]
    assert CLAUSE_ARG_IN_ENUM_LIST in forms and CLAUSE_ARG_IS_ABSENT in forms
    assert r.clauses[0].value is False and r.clauses[0].value_type == "bool"
    assert r.clauses[1].value == -1


# --------------------------------------------------------------------------
# Rule ids and origins.
# --------------------------------------------------------------------------

def test_both_id_forms_parse_and_nothing_else_does():
    """The parser accepts a placeholder AND a real id, because it also reads
    stored documents. Refusing a hash-shaped id on `add_rule` is V9 and belongs
    to the validator, which is the layer that knows whether this is an add."""
    assert parse_rule("rule r_new1: cap:CAP_MOVES_MONEY => deny").rule_id == "r_new1"
    assert parse_rule("rule r_5f2a91cc0b74: cap:CAP_MOVES_MONEY => deny").rule_id \
        == "r_5f2a91cc0b74"
    assert _code("rule R_NEW1: cap:CAP_MOVES_MONEY => deny") == "E_BAD_RULE_ID"
    assert _code("rule r_ZZZZZZZZZZZZ: cap:CAP_MOVES_MONEY => deny") == "E_BAD_RULE_ID"


def test_a_patch_is_rules_and_retractions():
    patch = parse_policy(
        "rule r_new1: cap:CAP_MOVES_MONEY => deny origin armorer:3\n"
        "retract r_c71204ff8a3d\n"
        "\n"
        "rule r_new2: cap:CAP_READS_PII => require_approval(PII_REVIEW) origin seed\n")
    assert [r.rule_id for r in patch.rules] == ["r_new1", "r_new2"]
    assert patch.retractions == ["r_c71204ff8a3d"]
    assert patch.rules[0].origin == "armorer:3"
    assert patch.rules[1].origin == "seed"


def test_the_action_arrow_is_lexed_before_the_comparison_operators():
    """`=>` must win over `>=` and `>`. If it did not, `... => deny` would lex
    as `>` then `=` and the error would name the wrong cause - which is the one
    thing R8's single repair attempt cannot recover from, since the parser error
    is its only feedback."""
    r = parse_rule("rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 1 => deny")
    assert r.clauses[0].op == ">=" and r.action.verb == "deny"
