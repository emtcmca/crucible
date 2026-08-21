"""l3_fixtures.py - shared inputs for L3's checks. Not a test module.

Everything here comes from `contracts/golden/` where a golden fixture exists.
Where one does not - a policy with two rules of different verbs, an episode
prefix containing a blocked call - the object is hand-built HERE and never
imported from another lane's code. L3-enforcement.md section 3: develop against
the goldens, never against another lane's implementation.

The hand-built rule dicts are in the STORED C4 form, not DSL text, and that is
deliberate. An engine check that went through the parser would fail red for a
parser bug and green for an engine bug, and the whole point of a negative check
is that when it fires you know what it is telling you.
"""

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden"


def _load(name):
    """Load a golden fixture and drop its top-level authoring notes.

    `_note` and `_must_fail_because` are commentary the fixture author left for
    a human; the document root is `additionalProperties: false`, so they are not
    part of the instance. `scripts/contract-check.py:211-212` pops exactly these
    two before validating, and this does the same rather than teaching the
    validator to tolerate underscore keys - a validator that ignores unknown
    keys is a validator that would also ignore `match_mode`.
    """
    doc = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        doc.pop("_note", None)
        doc.pop("_must_fail_because", None)
    return doc


MANIFEST_A = _load("C3a-capability_manifest.valid.json")
DERIVED_B = _load("C3b-derived_schema.valid.json")
POLICY_DOC_VALID = _load("C4-policy_document.valid.json")
POLICY_DOC_KNOWN_BAD = _load("C4-policy_document.KNOWN_BAD.json")
TOOL_EVENT_VALID = _load("C1-tool_event.valid.json")

# Handles, named so a check reads as English rather than as hex.
T_REFUND = "tool:t_9f2c1b77"      # {CAP_MOVES_MONEY}
T_EMAIL = "tool:t_1275c768"       # {CAP_EXTERNAL_COMMS, CAP_READS_PII} - the
                                  # membership fixture: a rule binding ONE of
                                  # those two must fire on it.
T_UNKNOWN = "tool:t_deadbeef"     # fail_closed, all six

# The seven declared derived paths and the three episode fields, read out of
# Part B rather than restated - a restatement is a drift site (section 8 rule 11).
DECLARED_DERIVED = tuple(f["name"] for f in DERIVED_B["derived_fields"])
DECLARED_EPISODE = tuple(f["name"] for f in DERIVED_B["episode_fields"])

# Deliberately NOT declared. Ruling 24 uses this exact field to make the point
# that a rule can compile as GRAMMAR and reject as POLICY: derived.* arg-paths
# resolve against the manifest's declared set, and this one is undeclared on
# purpose because no corpus instance exercises it and AN UNCHECKABLE FIELD HAS
# NO BUSINESS IN A HASHED ARTIFACT.
UNDECLARED_DERIVED = "derived.prior_decision_on_this_order"

EPISODE_FACTS = {
    "episode.account_holder_email": "holder@example.invalid",
    "episode.account_holder_id": "acct_8812",
    "episode.order_payment_instrument_id": "pi_44120",
}


# --------------------------------------------------------------------------
# Stored-form rule builders. Ids are hand-chosen so tie-break order is
# controllable: content-addressed ids are unpredictable by construction, and a
# check that asserts "lowest rule_id wins" cannot be written against ids nobody
# can predict. These are fixtures, not artifacts of the real assigner.
# --------------------------------------------------------------------------

def rule(rule_id, verb, cap_class, *, tool_names=None, arg_conditions=None,
         predicates=None, action=None, origin="armorer:1"):
    match = {"capability_class": cap_class, "tool_names": list(tool_names or [])}
    if arg_conditions is not None:
        match["arg_conditions"] = list(arg_conditions)
    if predicates is not None:
        match["predicates"] = list(predicates)
    out = {"rule_id": rule_id, "verb": verb, "match": match, "origin": origin}
    if action is not None:
        out["action"] = action
    return out


def policy(*rules, target_manifest_hash="9f2c1b77e0a4d3e6"):
    """A bare `hashed_payload`. Rules are passed IN THE ORDER GIVEN and are NOT
    sorted here, precisely so a check can hand the same rule set to the engine
    twice in two different orders and assert the answer does not move."""
    return {
        "policy_schema_version": 1,
        "target_manifest_hash": target_manifest_hash,
        "rules": list(rules),
    }


# --------------------------------------------------------------------------
# Episode-prefix builders. A ToolEvent, C1 shape, minus the fields no engine
# check reads. `policy_decision` and `kind` are the two that decide visibility,
# so they are always explicit here - a default would hide the thing under test.
# --------------------------------------------------------------------------

def event(kind, cap_classes, *, args=None, policy_decision=None,
          tool_handle=T_REFUND, seq=0, denied_by_rule_id=None):
    ev = {
        "episode_id": "ep_4bf92f3577b3",
        "invocation_id": "inv-%04d" % seq,
        "kind": kind,
        "tool_name": "fixture_tool",
        "tool_handle": tool_handle,
        "capability_classes": sorted(cap_classes),
        "args": dict(args or {}),
        "role": "root_agent",
        "derived_overwrites": [],
        "seq": seq,
        "ts_monotonic": 1724512869221000000 + seq,
    }
    if policy_decision is not None:
        ev["policy_decision"] = policy_decision
    if denied_by_rule_id is not None:
        ev["denied_by_rule_id"] = denied_by_rule_id
    return ev


def executed(cap_classes, **kw):
    """A call that actually ran. The only kind the TRIPWIRE scores on, and the
    only kind `preceded_by` and `episode_sum` may see."""
    return event("TOOL_EXECUTED", cap_classes, **kw)


def blocked_attempt(cap_classes, **kw):
    """A call the policy stopped. It leaves a TOOL_ATTEMPT and NO matching
    TOOL_EXECUTED - which is how enforcement is proven from the record alone,
    and which is exactly why this event must be INVISIBLE to `preceded_by`.
    If a blocked call satisfied a composition predicate, an attacker would get
    the precondition for free by making a call he already knows will fail."""
    kw.setdefault("denied_by_rule_id", "r_000000000001")
    return event("TOOL_ATTEMPT", cap_classes, policy_decision="DENY", **kw)


def errored(cap_classes, **kw):
    ev = event("TOOL_ERROR", cap_classes, **kw)
    ev["error_class"] = "RuntimeError"
    return ev
