"""hashing.py - the content-addressed identifiers derived from canonical bytes.

`contracts/canonicalization.md` section 1:

    policy_hash_full = hex(SHA256(jcs_canonical_utf8(hashed_payload)))   # run_id NOT inside
    policy_hash      = policy_hash_full[0:16]
    rule_id          = "r_" + hex(SHA256(jcs_canonical_utf8(rule_without_rule_id)))[0:12]

`CONVENTIONS.md` section 2.5 gives the wider ID table; every ID except `run_*` and
`fam_*` is deterministic, which is what makes retries idempotent and replay free.

THE ARMORER NEVER CALLS `rule_id` (CONVENTIONS section 2.6). A model cannot compute a
SHA-256. It emits the placeholder `r_new1`; the validator canonicalizes the body,
calls this, and rewrites the placeholder. `is_placeholder_rule_id` is here so that
check lives next to the thing it guards rather than in a comment somewhere else.
"""

import hashlib
import re

from .canonical import CanonicalizationError, canonicalize

# `r_` plus exactly 12 lowercase hex. Anything else is not one of ours.
RULE_ID_RE = re.compile(r"^r_[0-9a-f]{12}$")
PLACEHOLDER_RE = re.compile(r"^r_new[0-9]+$")


def hash_full(obj) -> str:
    """Full 64-char lowercase hex SHA-256 of the canonical form of `obj`."""
    return hashlib.sha256(canonicalize(obj)).hexdigest()


def short_hash(obj, n: int) -> str:
    """First `n` hex chars of `hash_full`. Truncation length is never guessed at
    a call site - CONVENTIONS section 2.5 fixes one length per ID kind."""
    if n < 8 or n > 64:
        raise ValueError("truncation outside the range section 2.5 uses")
    return hash_full(obj)[:n]


def policy_hash(hashed_payload) -> str:
    """16 hex chars over the policy's hashed payload.

    `run_id` is deliberately OUTSIDE that payload. It was inside once, and it made
    the same policy hash differently in two runs, which breaks convergence-by-hash-
    equality and the resume key at the same time (canonicalization.md section 4).
    """
    if isinstance(hashed_payload, dict) and "run_id" in hashed_payload:
        raise CanonicalizationError(
            "E_RUN_ID_IN_PAYLOAD",
            "run_id is outside the hashed payload. Inside, the same policy hashes "
            "differently in two runs and convergence-by-hash-equality stops working.")
    return short_hash(hashed_payload, 16)


def rule_id(rule_body: dict) -> str:
    """Content-addressed rule ID. `rule_id` is stripped before hashing, so the same
    semantic rule always gets the same ID and `add_rule` of an existing rule is
    DETECTABLY a no-op - the per-rule half of the convergence detector."""
    if not isinstance(rule_body, dict):
        raise TypeError("rule body must be an object")
    body = {k: v for k, v in rule_body.items() if k != "rule_id"}
    if not body:
        raise CanonicalizationError("E_EMPTY_RULE", "a rule with no body has no identity")
    return "r_" + short_hash(body, 12)


def is_placeholder_rule_id(value: str) -> bool:
    """True for `r_new1`, `r_new2`, ... - what the ARMORER is required to emit."""
    return bool(PLACEHOLDER_RE.match(value or ""))


def is_real_rule_id(value: str) -> bool:
    return bool(RULE_ID_RE.match(value or ""))


def assert_model_did_not_forge_a_rule_id(value: str) -> None:
    """CONVENTIONS section 2.6: a patch in which the model emitted a hash-shaped ID
    on `add_rule` is REJECTED.

    Not because the ID would be wrong - it would almost certainly be wrong - but
    because a model that emitted a plausible one has demonstrated it is guessing at
    a deterministic computation, and the next guess lands somewhere we cannot see.
    """
    if is_placeholder_rule_id(value):
        return
    if is_real_rule_id(value):
        raise CanonicalizationError(
            "E_MODEL_EMITTED_RULE_ID",
            "%r is hash-shaped. On add_rule the ARMORER emits a placeholder "
            "(r_new1, r_new2, ...) and the validator assigns the real ID." % value)
    raise CanonicalizationError(
        "E_BAD_RULE_ID", "%r is neither a placeholder nor a valid rule ID" % value)
