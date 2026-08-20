"""test_hashing.py - the content-addressed IDs built on the canonical form.

Contract: `contracts/canonicalization.md` section 1, `CONVENTIONS.md` sections 2.5
and 2.6.

Same discipline as test_canonicalization.py: no hex literal appears anywhere in
this file. Every assertion is about a RELATIONSHIP - two spellings agree, two
meanings disagree, a shape is accepted or refused - because an expected-digest
assertion could only ever be produced by running the code it is testing.
"""

import pytest

from crucible.canon import (
    CanonicalizationError,
    canonicalize,
    hash_full,
    policy_hash,
    rule_id,
    short_hash,
)
from crucible.canon.hashing import (
    assert_model_did_not_forge_a_rule_id,
    is_placeholder_rule_id,
    is_real_rule_id,
)


# --------------------------------------------------------------------------
# rule_id - the per-rule half of the convergence detector.
# --------------------------------------------------------------------------

RULE = {
    "verb": "deny",
    "cap_selector": "CAP_MOVES_MONEY",
    "when": [{"path": "amount_minor", "op": "gt", "value": 50000}],
}


def test_rule_id_shape():
    rid = rule_id(RULE)
    assert is_real_rule_id(rid), rid
    assert len(rid) == len("r_") + 12


def test_rule_id_ignores_key_order():
    """The whole reason the ID is computed over the CANONICAL form."""
    shuffled = {"when": RULE["when"], "cap_selector": RULE["cap_selector"],
                "verb": RULE["verb"]}
    assert rule_id(RULE) == rule_id(shuffled)


def test_rule_id_ignores_an_existing_rule_id():
    """add_rule of a rule already in the policy must be DETECTABLY a no-op.

    If `rule_id` were part of its own input, re-adding a rule would produce a new
    ID every time and the convergence detector would report progress forever.
    """
    with_id = dict(RULE, rule_id="r_000000000000")
    assert rule_id(with_id) == rule_id(RULE)


def test_rule_id_changes_when_the_rule_changes():
    weaker = dict(RULE, when=[{"path": "amount_minor", "op": "gt", "value": 50001}])
    assert rule_id(weaker) != rule_id(RULE), (
        "a one-unit change to a threshold produced the same ID; the ID is not "
        "addressing the content it claims to")


def test_rule_id_refuses_an_empty_body():
    with pytest.raises(CanonicalizationError) as ei:
        rule_id({"rule_id": "r_000000000000"})
    assert ei.value.code == "E_EMPTY_RULE"


# --------------------------------------------------------------------------
# CONVENTIONS 2.6 - the ARMORER never writes a rule ID.
# --------------------------------------------------------------------------

def test_placeholder_ids_are_what_the_armorer_may_emit():
    assert is_placeholder_rule_id("r_new1")
    assert is_placeholder_rule_id("r_new12")
    assert not is_placeholder_rule_id("r_new")
    assert not is_real_rule_id("r_new1")
    assert_model_did_not_forge_a_rule_id("r_new1")     # does not raise


def test_a_hash_shaped_id_from_the_model_is_rejected():
    """Rejected even though it is WELL-FORMED, and that is the point.

    The objection is not that the ID would be wrong. It is that a model which
    produced a plausible SHA-256 has demonstrated it is guessing at a
    deterministic computation, and the next guess lands somewhere invisible.
    """
    forged = rule_id(RULE)                 # a genuinely correct ID...
    assert is_real_rule_id(forged)
    with pytest.raises(CanonicalizationError) as ei:
        assert_model_did_not_forge_a_rule_id(forged)   # ...still refused
    assert ei.value.code == "E_MODEL_EMITTED_RULE_ID"


def test_garbage_id_is_rejected_distinctly():
    with pytest.raises(CanonicalizationError) as ei:
        assert_model_did_not_forge_a_rule_id("rule-42")
    assert ei.value.code == "E_BAD_RULE_ID"


# --------------------------------------------------------------------------
# policy_hash - and the run_id trap.
# --------------------------------------------------------------------------

PAYLOAD = {"version": 3, "rules": [RULE]}


def test_policy_hash_shape_and_stability():
    h = policy_hash(PAYLOAD)
    assert len(h) == 16 and all(c in "0123456789abcdef" for c in h)
    assert h == policy_hash({"rules": [RULE], "version": 3})


def test_run_id_inside_the_hashed_payload_is_refused():
    """It was inside once. The same policy then hashed differently in two runs,
    which breaks convergence-by-hash-equality and the resume key together.

    A comment saying 'run_id goes outside' cannot fail. This can.
    """
    with pytest.raises(CanonicalizationError) as ei:
        policy_hash(dict(PAYLOAD, run_id="run_20260820_120000_abc123"))
    assert ei.value.code == "E_RUN_ID_IN_PAYLOAD"


def test_policy_hash_is_a_prefix_of_the_full_hash():
    assert hash_full(PAYLOAD).startswith(policy_hash(PAYLOAD))


def test_short_hash_refuses_a_length_no_id_kind_uses():
    for n in (0, 4, 7, 65):
        with pytest.raises(ValueError):
            short_hash(PAYLOAD, n)


# --------------------------------------------------------------------------
# The restrictions reach the hashing layer too.
# --------------------------------------------------------------------------

def test_a_float_in_a_rule_body_cannot_be_hashed():
    """Reached through canonicalize(), not canonicalize_bytes() - the in-memory
    path has no parser hook to catch it, so the emitter must."""
    with pytest.raises(CanonicalizationError) as ei:
        rule_id(dict(RULE, threshold=0.5))
    assert ei.value.code == "E_FLOAT"


def test_a_null_in_a_rule_body_cannot_be_hashed():
    with pytest.raises(CanonicalizationError) as ei:
        rule_id(dict(RULE, approver=None))
    assert ei.value.code == "E_NULL"
    assert "NONE" in ei.value.detail, (
        "the error should point at the sentinel that replaces null, or the next "
        "person fixes it by deleting the field and silently changes the meaning")


def test_bool_does_not_serialize_as_an_integer():
    """bool is a subclass of int in Python. isinstance(True, int) is True, so an
    integer check written the obvious way emits `1` for `true` and the policy
    hash quietly stops matching the policy text."""
    assert canonicalize({"a": True}) == b'{"a":true}'
    assert canonicalize({"a": 1}) == b'{"a":1}'
    assert hash_full({"a": True}) != hash_full({"a": 1})
