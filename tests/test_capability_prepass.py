"""test_capability_prepass.py - the deterministic pre-pass CAPABILITY_CARTOGRAPHER
needs and did not have.

`docs/decisions-pending/gemma-scope.md` section 6 checked, on 2026-08-21, that no
`classify_tool` existed anywhere in `crucible/` or `target/` - the eight tools in
`target/refund_agent/capability_manifest.json` were classified by a human. This
suite proves `crucible/cartographer/prepass.classify_tool`:

  - resolves a class when the tool's own signature genuinely implies it, with an
    evidence string a human can check against that signature directly;
  - declines (UNCLASSIFIED, resolved=False) rather than guess, when nothing in
    the signature implies a class;
  - was NOT tuned against the eight human-classified tools to inflate agreement.
    The agreement test pins the ACTUAL confusion (right / missed / over-claimed),
    not a number chosen because it looked good.

The negative control matters as much as the positive ones: a classifier that
always resolves something, or always resolves the SAME thing, would pass a
looser suite. `test_not_a_constant_function` is the check that would catch that
strawman.
"""

import json
import pathlib

import pytest

from crucible.cartographer.prepass import (
    CAPABILITY_CLASSES,
    UNCLASSIFIED,
    classify_tool,
    tool_spec_from_function,
)

MANIFEST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "target" / "refund_agent" / "capability_manifest.json"
)


def _manifest_ground_truth():
    """Read-only: {tool_short_name: frozenset(capability_classes)} from the
    human-classified manifest. Never modified - it is being frozen the same
    day this suite was written."""
    doc = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    out = {}
    for entry in doc["tools"]:
        short_name = entry["tool_fqname"].rsplit(".", 1)[-1]
        out[short_name] = frozenset(entry["capability_classes"])
    return out


def _target_tool_functions():
    """The same eight bare functions the manifest classifies, imported only
    for their signatures/docstrings - never edited, never re-classified by
    hand here."""
    from target.refund_agent import tools as target_tools
    return {fn.__name__: fn for fn in target_tools.TOOL_FUNCTIONS}


# --------------------------------------------------------------------------
# A signature that clearly implies a class, with the right evidence.
# --------------------------------------------------------------------------

def test_agent_destination_argument_resolves_invokes_agent():
    """A tool that takes another agent's name as a destination argument
    resolves CAP_INVOKES_AGENT, and the evidence names the exact argument
    that produced it - `delegate_to_specialist`'s real signature."""
    spec = {
        "tool_name": "delegate_to_specialist",
        "args": [
            {"name": "case_id", "type": "string", "description": "The case."},
            {"name": "specialist_agent", "type": "string",
             "description": "FRAUD_ANALYST, RETURNS_SPECIALIST, or BILLING_ANALYST."},
            {"name": "order_id", "type": "string", "description": "The order."},
        ],
    }
    result = classify_tool(spec)

    assert result["resolved"] is True
    assert "CAP_INVOKES_AGENT" in result["classes"]
    assert UNCLASSIFIED not in result["classes"]
    assert result["confidence"] > 0.0

    invoke_evidence = [e for e in result["evidence"]
                       if e["capability_class"] == "CAP_INVOKES_AGENT"]
    assert len(invoke_evidence) == 1
    assert "specialist_agent" in invoke_evidence[0]["citation"]


def test_money_shaped_arguments_resolve_moves_money_with_evidence():
    """An amount-shaped argument next to a currency argument resolves
    CAP_MOVES_MONEY, citing both argument names."""
    spec = {
        "tool_name": "issue_refund",
        "args": [
            {"name": "order_id", "type": "string", "description": "The order."},
            {"name": "amount_minor", "type": "integer",
             "description": "Amount in minor units."},
            {"name": "currency", "type": "string", "description": "ISO-4217 code."},
        ],
    }
    result = classify_tool(spec)

    assert result["resolved"] is True
    assert "CAP_MOVES_MONEY" in result["classes"]
    money_evidence = [e for e in result["evidence"]
                      if e["capability_class"] == "CAP_MOVES_MONEY"]
    assert len(money_evidence) == 1
    assert "amount_minor" in money_evidence[0]["citation"]
    assert "currency" in money_evidence[0]["citation"]


# --------------------------------------------------------------------------
# A signature that implies nothing resolves to UNCLASSIFIED, resolved=False.
# --------------------------------------------------------------------------

def test_unresolvable_signature_declines_rather_than_guesses():
    """`lookup_order`'s real signature takes one plain string argument whose
    name gives away nothing about money, comms, state, agents, or escalation
    - its PII exposure lives in its RETURN payload, which a request-shape
    pre-pass cannot see. The correct answer is UNCLASSIFIED, not a guess."""
    spec = {
        "tool_name": "lookup_order",
        "args": [
            {"name": "order_id", "type": "string",
             "description": 'The order number, e.g. "ORD-4471".'},
        ],
    }
    result = classify_tool(spec)

    assert result["resolved"] is False
    assert result["classes"] == (UNCLASSIFIED,)
    assert result["evidence"] == ()
    assert result["confidence"] == 0.0


def test_no_arguments_declines():
    """A tool with no arguments at all cannot trip any rule - this is the
    degenerate case every rule must handle without raising."""
    result = classify_tool({"tool_name": "ping", "args": []})
    assert result["resolved"] is False
    assert result["classes"] == (UNCLASSIFIED,)


# --------------------------------------------------------------------------
# Agreement against the eight human-classified tools. PINNED, not chosen.
#
# This is not "does the pre-pass reproduce the manifest" - the memo (gemma-
# scope.md section 6) explicitly says not to tune toward that. It is "does
# the pre-pass do what it honestly does", recorded so a change to the rules
# shows up here as a diff a reviewer has to explain.
# --------------------------------------------------------------------------

def test_agreement_against_human_classified_manifest():
    """Run classify_tool over the real signatures of all eight manifest
    tools and compare against `classified_by: human, human_confirmed: true`.

    Pinned result (recorded 2026-08-22, from the actual run - see this
    file's docstring and the deliverable report for the full table):

      resolved (found something):     6 of 8  - all but lookup_order, lookup_customer
      exact match (predicted == truth): 2 of 8  - email_customer, update_case_notes
      class-level recall:              7 of 13 true (tool, class) pairs found
      class-level over-claims:         1        - escalate_to_human predicted
                                                   CAP_MOVES_MONEY, which the
                                                   manifest does not assign it
                                                   (it recommends an amount, an
                                                   escalation never moves money
                                                   itself)

    A regression in any of these numbers means the rules changed - which is
    fine, but it must not be silent.
    """
    truth = _manifest_ground_truth()
    fns = _target_tool_functions()
    assert set(truth) == set(fns), "the manifest and target/tools.py disagree on which eight tools exist"

    resolved_count = 0
    exact_match_count = 0
    correct_pairs = 0
    missed_pairs = []
    overclaimed_pairs = []

    for name, fn in fns.items():
        spec = tool_spec_from_function(fn, declaring_agent="refund_agent")
        result = classify_tool(spec)
        predicted = set(result["classes"]) if result["resolved"] else set()
        true_classes = set(truth[name])

        if result["resolved"]:
            resolved_count += 1
        if predicted == true_classes:
            exact_match_count += 1

        correct_pairs += len(predicted & true_classes)
        missed_pairs.extend((name, c) for c in sorted(true_classes - predicted))
        overclaimed_pairs.extend((name, c) for c in sorted(predicted - true_classes))

    assert resolved_count == 6
    assert exact_match_count == 2
    assert correct_pairs == 7
    assert sorted(overclaimed_pairs) == [("escalate_to_human", "CAP_MOVES_MONEY")]
    assert sorted(missed_pairs) == [
        ("delegate_to_specialist", "CAP_MUTATES_DURABLE_STATE"),
        ("escalate_to_human", "CAP_MUTATES_DURABLE_STATE"),
        ("issue_refund", "CAP_MUTATES_DURABLE_STATE"),
        ("issue_store_credit", "CAP_MUTATES_DURABLE_STATE"),
        ("lookup_customer", "CAP_READS_PII"),
        ("lookup_order", "CAP_READS_PII"),
    ]


def test_unresolved_tools_are_named_not_silently_zero():
    """The two tools the pre-pass cannot resolve (lookup_order,
    lookup_customer) must come back UNCLASSIFIED and resolved=False - never
    silently inert (empty classes), which `capabilities.py` treats as a
    different, false claim ("we know it has no capabilities")."""
    fns = _target_tool_functions()
    for name in ("lookup_order", "lookup_customer"):
        spec = tool_spec_from_function(fns[name])
        result = classify_tool(spec)
        assert result["resolved"] is False
        assert result["classes"] == (UNCLASSIFIED,)


# --------------------------------------------------------------------------
# Negative control - a suite that always passes is not measuring anything.
# --------------------------------------------------------------------------

def test_not_a_constant_function():
    """A classifier that returns the same thing for every tool (always
    UNCLASSIFIED, or always some fixed class set) would pass every test
    above that only checks one tool at a time. This test would catch it: it
    demands both an UNCLASSIFIED result and at least two DIFFERENT resolved
    class sets across the real eight tools."""
    fns = _target_tool_functions()
    seen_class_sets = set()
    any_unresolved = False

    for fn in fns.values():
        spec = tool_spec_from_function(fn)
        result = classify_tool(spec)
        if result["resolved"]:
            seen_class_sets.add(result["classes"])
        else:
            any_unresolved = True

    assert any_unresolved, "expected at least one genuinely unresolvable tool (lookup_order/lookup_customer)"
    assert len(seen_class_sets) >= 2, (
        "a classifier returning one fixed resolved answer for every tool would "
        "still satisfy 'resolves something' checks - it must not pass here")


def test_evidence_always_present_on_a_resolved_result():
    """Ruling out the strawman that resolves a class but forgets to cite why.
    Every resolved class must have exactly one evidence entry naming it."""
    fns = _target_tool_functions()
    for fn in fns.values():
        spec = tool_spec_from_function(fn)
        result = classify_tool(spec)
        if not result["resolved"]:
            continue
        cited_classes = {e["capability_class"] for e in result["evidence"]}
        assert cited_classes == set(result["classes"]), (
            "%s: every resolved class must carry evidence, and evidence must "
            "not cite a class that was not resolved" % spec["tool_name"])
        for e in result["evidence"]:
            assert e["citation"], "empty citation is not evidence"


def test_unclassified_never_mixes_with_a_real_class():
    """capabilities.py's own rule (C4 V2): UNCLASSIFIED travels alone. A
    result must never propose UNCLASSIFIED alongside a real capability class
    - that would read as covered when it is not."""
    fns = _target_tool_functions()
    for fn in fns.values():
        spec = tool_spec_from_function(fn)
        result = classify_tool(spec)
        if UNCLASSIFIED in result["classes"]:
            assert result["classes"] == (UNCLASSIFIED,)


def test_classify_tool_is_pure_and_deterministic():
    """Same input, called twice, must produce an identical result - no
    hidden state, no randomness, no I/O side effect that could change the
    second answer."""
    spec = {
        "tool_name": "email_customer",
        "args": [
            {"name": "customer_id", "type": "string", "description": "The account."},
            {"name": "to", "type": "string", "description": "A SINGLE email address. Not a list."},
            {"name": "subject_line", "type": "string", "description": "Subject."},
            {"name": "body", "type": "string", "description": "Body."},
        ],
    }
    first = classify_tool(spec)
    second = classify_tool(spec)
    assert first == second


def test_all_six_capability_classes_are_reachable():
    """Every one of the six classes must be producible by at least one rule
    - a pre-pass that could never resolve one of the six would be silently
    incomplete against the taxonomy it claims to speak."""
    reachable = set()
    fixtures = [
        {"tool_name": "t1", "args": [
            {"name": "amount_minor", "description": ""},
            {"name": "currency", "description": ""}]},
        {"tool_name": "t2", "args": [
            {"name": "to", "description": "the email address to send to"}]},
        {"tool_name": "t3", "args": [{"name": "status_to", "description": ""}]},
        {"tool_name": "t4", "args": [{"name": "specialist_agent", "description": ""}]},
        {"tool_name": "t5", "args": [{"name": "queue", "description": "RISK_REVIEW"}]},
    ]
    for spec in fixtures:
        result = classify_tool(spec)
        assert result["resolved"] is True, spec
        reachable.update(result["classes"])

    assert reachable == set(CAPABILITY_CLASSES), (
        "unreachable classes: %s" % (set(CAPABILITY_CLASSES) - reachable))
