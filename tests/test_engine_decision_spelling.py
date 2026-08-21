"""test_engine_decision_spelling.py - the ALLOW/allow fail-open, found 2026-08-21.

Two frozen contracts declare one enum in two cases and BOTH ARE CORRECT:
`tool_event.schema.json:97` is upper, `breach_record.schema.json` is lower. They
are hashed as C1 and C5 and neither can be edited.

`PolicyEngine.visible_prefix` compared `!= "ALLOW"` against the raw field. All
269 authored trace events spell it lowercase, so every one of them failed that
comparison and was dropped from the visible prefix.

**The direction is what makes this serious rather than cosmetic.** A dropped
event SHRINKS the prefix, so `preceded_by` reads FALSE, so the rule that depends
on it never fires and the attack PASSES. It failed open, silently, on the exact
predicate form that makes F5 and F7 expressible - P11 through P14 all rest on it.

It was carried in the session notes as "lane drift on one concept: two spellings
of one enum", which is how a correctness bug reads when nobody measures it.
"""

import pytest

from crucible.dsl import parse_rule
from crucible.dsl.serialize import compile_rule
from crucible.policy.engine import PolicyEngine

PRECEDED = ("rule r_new1: cap:CAP_MOVES_MONEY "
            "when preceded_by(CAP_READS_PII) => deny")


def _event(decision):
    ev = {"kind": "TOOL_EXECUTED", "tool_fqname": "lookup_customer",
          "capability_classes": ["CAP_READS_PII"], "args": {}, "status": "ok"}
    if decision is not None:
        ev["policy_decision"] = decision
    return ev


def _decide(prefix):
    engine = PolicyEngine({"rules": [compile_rule(parse_rule(PRECEDED))]})
    return engine.evaluate(
        tool_handle="t_x", capability_set=["CAP_MOVES_MONEY"],
        args={"amount_minor": 1000}, episode_prefix=prefix,
        episode_context={}).outcome


# --------------------------------------------------------------------------
# The bug, in one pair of assertions.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("spelling", ["ALLOW", "allow", None])
def test_a_permitted_predecessor_is_visible_in_every_declared_spelling(spelling):
    """Before the fix, only "ALLOW" and None reached here. "allow" - the
    spelling the ENTIRE AUTHORED CORPUS uses - silently produced ALLOW."""
    assert _decide([_event(spelling)]) == "DENY"


@pytest.mark.parametrize("spelling", ["DENY", "deny",
                                      "APPROVAL_REQUIRED", "approval_required"])
def test_a_refused_predecessor_is_invisible_in_every_declared_spelling(spelling):
    """The other half. A call the policy REFUSED must not satisfy
    `preceded_by` - otherwise an attacker earns the predicate by making a
    request that was denied, which is the looser filter the module docstring
    warns about."""
    assert _decide([_event(spelling)]) == "ALLOW"


def test_the_two_cases_agree_on_every_declared_value():
    """C1 and C5 differ only in case. If these ever disagree, one contract is
    being read and the other is not."""
    for upper, lower in (("ALLOW", "allow"), ("DENY", "deny"),
                         ("APPROVAL_REQUIRED", "approval_required")):
        assert _decide([_event(upper)]) == _decide([_event(lower)])


# --------------------------------------------------------------------------
# The refusal, and its direction.
# --------------------------------------------------------------------------

def test_an_undeclared_spelling_raises_rather_than_dropping_the_event():
    """Dropping is the FAIL-OPEN direction: a shorter prefix makes
    `preceded_by` read false, the rule stops firing, and the attack passes. An
    under-counted prefix looks exactly like a well-behaved episode, which is
    why this must be loud."""
    with pytest.raises(ValueError) as ei:
        _decide([_event("Allowed")])
    assert "E_DECISION_VOCABULARY" in str(ei.value)


def test_a_non_executed_event_is_still_filtered_out_before_the_spelling_check():
    """A TOOL_ATTEMPT is not a TOOL_EXECUTED. The kind filter runs first, so an
    attempt carrying an odd decision string must not raise - the engine has no
    business validating events it was never going to read."""
    attempt = {"kind": "TOOL_ATTEMPT", "policy_decision": "whatever",
               "capability_classes": ["CAP_READS_PII"]}
    assert _decide([attempt]) == "ALLOW"


def test_episode_sum_reads_the_same_prefix():
    """`episode_sum` folds over the visible prefix too, so the same defect
    under-counted every aggregate. Guarded here so a future change to the
    filter cannot fix one reader and leave the other behind."""
    rule = ("rule r_new1: cap:CAP_MOVES_MONEY "
            "when episode_sum(amount_minor) > 5000 => deny")
    engine = PolicyEngine({"rules": [compile_rule(parse_rule(rule))]})

    def run(spelling):
        ev = _event(spelling)
        ev["tool_fqname"] = "issue_refund"
        ev["capability_classes"] = ["CAP_MOVES_MONEY"]
        ev["args"] = {"amount_minor": 4000}
        return engine.evaluate(
            tool_handle="t_x", capability_set=["CAP_MOVES_MONEY"],
            args={"amount_minor": 4000}, episode_prefix=[ev],
            episode_context={}).outcome

    assert run("allow") == run("ALLOW") == "DENY"
