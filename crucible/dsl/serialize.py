"""serialize.py - ParsedRule to the stored C4 form, and the rule_id assignment.

The stored form is `policy_document.schema.json` `$defs/rule`. Two properties of
it are load-bearing rather than cosmetic:

  * **Arrays are sorted AT CONSTRUCTION** (canonicalization.md restriction 6),
    not at hash time. Sorting at hash time would look lossless and be
    destructive; sorting here is what makes the canonical form unambiguous and
    removes an entire class of "same policy, different hash" bugs.
  * **`rule_id` is assigned by CODE**, from the canonical bytes of the rule body.
    The ARMORER emits `r_new1` and never sees a hash (CONVENTIONS 2.6). A model
    cannot compute a SHA-256; asked to, it fails every attempt, and the day-1
    spike would have read 0/20 and triggered an architecture change for a reason
    that has nothing to do with the DSL.

--------------------------------------------------------------------------
THREE CONVENTIONS THIS FILE HAD TO CHOOSE, BECAUSE THE CONTRACT IS SILENT AND
EACH CHOICE MOVES `rule_id`. All three are REPORTED to the coordinator; none is
a lane editing a contract. They are collected here rather than scattered so
there is one place to change if a ruling lands.
--------------------------------------------------------------------------

1. `origin` IS EXCLUDED FROM THE RULE ID. `canonicalization.md` section 1 says
   `rule_id = hash(canonical(rule_without_rule_id))`, which read literally
   includes `origin` - and `origin` carries the round number (`armorer:3`).
   Including it means the SAME SEMANTIC RULE re-proposed in a later round gets a
   DIFFERENT id, so `add_rule` of an existing rule stops being detectably a
   no-op - and that detection is named in the same paragraph as "the per-rule
   half of the convergence detector". The two sentences cannot both hold.
   Resolved toward convergence: the id is over what the rule DOES (verb, match,
   action), not over who proposed it in which round. `origin` still lives inside
   the hashed PAYLOAD, so `policy_hash` still covers it - which is what the
   schema's own comment about origin is protecting.

2. EMPTY-ARRAY PRESENCE follows the golden fixture exactly: `tool_names` and
   `arg_conditions` are always emitted (empty when unused) and `predicates` is
   emitted only when non-empty. `contracts/golden/C4-policy_document.valid.json`
   is written that way and nothing states the rule. A present empty array and an
   absent key are different canonical bytes and therefore different ids, so this
   is not a style question.

3. `predicates` AND `tool_names` SORT ORDER. Restriction 6 names `rules`,
   `capability_classes` and `arg_conditions` and stops. Both of the unnamed
   arrays sit inside the hashed body, so an unsorted one means the same rule
   hashes two ways depending on the order the ARMORER happened to write its
   clauses. Sorted here on a stated key.
"""

from ..canon.hashing import rule_id as _content_id
from .nodes import (
    CLAUSE_ARG_CMP_LITERAL,
    CLAUSE_ARG_IN_ENUM_LIST,
    CLAUSE_ARG_IS_ABSENT,
    CLAUSE_ARG_IS_PRESENT,
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
    CLAUSE_EPISODE_SUM,
    CLAUSE_PRECEDED_BY,
    CMP_OPS,
    ParsedRule,
)

# Convention 1 above. Named so that a coordinator ruling is a one-line change
# and so that a grep for the question finds the answer.
FIELDS_OUTSIDE_THE_RULE_ID = ("rule_id", "origin")


def _arg_condition(clause):
    if clause.form == CLAUSE_ARG_CMP_LITERAL:
        return {"path": clause.path, "op": CMP_OPS[clause.op],
                "value": clause.value, "value_type": clause.value_type}
    if clause.form == CLAUSE_ARG_IN_ENUM_LIST:
        # Membership is order-insensitive, so sorting is lossless - and without
        # it `x in [A,B]` and `x in [B,A]` are two ids for one rule.
        return {"path": clause.path, "op": "in",
                "value": sorted(clause.values), "value_type": "enum_list"}
    if clause.form == CLAUSE_ARG_IS_ABSENT:
        # No `value`: an absent fact is an absent key (canonicalization rule 5),
        # and `null` is forbidden anywhere in a hashed payload.
        return {"path": clause.path, "op": "is_absent"}
    if clause.form == CLAUSE_ARG_IS_PRESENT:
        # Same reasoning, same shape: no `value` key at all. GX5, ruling 42.
        return {"path": clause.path, "op": "is_present"}
    return None


def _predicate(clause):
    if clause.form == CLAUSE_PRECEDED_BY:
        return {"form": CLAUSE_PRECEDED_BY, "value": clause.cap_class}
    if clause.form == CLAUSE_EPISODE_SUM:
        out = {"form": CLAUSE_EPISODE_SUM, "arg_path": clause.path,
               "op": CMP_OPS[clause.op], "value": clause.value}
        # GX2. THE KEY IS ABSENT WHEN UNUSED, NEVER NULL. Canonicalization
        # restriction 5 forbids a null in a hashed payload, and here that rule
        # is doing more than tidiness: `if clause.group_path` is the entire
        # reason a rule written before this production existed still hashes to
        # the rule_id already recorded beside it in every bundle. Emitting
        # `"group_by": null` on an ungrouped fold would re-id every such rule
        # and make the offline reader refuse the bundles that carry them.
        if clause.group_path:
            out["group_by"] = clause.group_path
        return out
    if clause.form == CLAUSE_ARG_VS_EPISODE_CONTEXT:
        return {"form": CLAUSE_ARG_VS_EPISODE_CONTEXT, "arg_path": clause.path,
                "op": CMP_OPS[clause.op], "context_field": clause.context_field}
    return None


def _predicate_sort_key(p):
    """Stated, so it is auditable rather than incidental. Convention 3."""
    # `group_by` is appended LAST rather than inserted beside `arg_path`.
    # Appending leaves the key of every predicate that carries no grouping key
    # exactly as it was, so the sort of an existing rule's `predicates` array
    # cannot move - and predicate order is inside the hashed body, so a moved
    # sort is a moved rule_id. GX2.
    return (p.get("form", ""), p.get("arg_path", ""), p.get("op", ""),
            p.get("context_field", ""), str(p.get("value", "")),
            p.get("group_by", ""))


def rule_body(parsed: ParsedRule) -> dict:
    """The stored rule WITHOUT `rule_id` and WITHOUT `origin`. This is what gets
    hashed - see convention 1 in the module docstring."""
    match = {
        "capability_class": parsed.cap_class,
        "tool_names": sorted(parsed.tool_handles),
        "arg_conditions": sorted(
            (c for c in (_arg_condition(cl) for cl in parsed.clauses) if c),
            key=lambda a: (a["path"], a["op"])),
    }
    preds = [p for p in (_predicate(cl) for cl in parsed.clauses) if p]
    if preds:
        match["predicates"] = sorted(preds, key=_predicate_sort_key)

    body = {"verb": parsed.action.verb, "match": match}

    if parsed.action.verb == "constrain_arg":
        body["action"] = {"path": parsed.action.path,
                          "op": CMP_OPS[parsed.action.op],
                          "value": parsed.action.value,
                          "value_type": parsed.action.value_type}
    elif parsed.action.verb == "require_approval":
        body["action"] = {"reason_code": parsed.action.reason_code}
    # `deny` carries no action block, matching the golden fixture. It also
    # carries no reason_code in the grammar, which C2 requires on every DENY;
    # the engine mints one. See `crucible/policy/decision.py`.

    return body


def assign_rule_id(body: dict) -> str:
    """Content-addressed id over a rule body. Never called by the ARMORER."""
    return _content_id(body)


def compile_rule(parsed: ParsedRule) -> dict:
    """Stored rule with the real content-addressed `rule_id` written in."""
    body = rule_body(parsed)
    out = {"rule_id": assign_rule_id(body)}
    out.update(body)
    if parsed.origin is not None:
        # RULING 38: the CLASS is stored, the ROUND is not. `armorer:4` and
        # `armorer:2` are the same rule from different rounds; the round has no
        # semantic force, and inside the hash it makes the same rule hash
        # differently every time it is re-proposed, which breaks
        # convergence-by-hash-equality. The class DOES have force -- it decides
        # retractability -- so it stays. The round goes to `provenance`, keyed
        # by rule_id, outside the hashed payload.
        out["origin"] = origin_class(parsed.origin)
    return out


def origin_class(origin: str) -> str:
    """`armorer:4` -> `armorer`. `seed` -> `seed`."""
    return origin.split(":", 1)[0] if origin else origin


def origin_round(origin: str):
    """The round number, or None for a seed rule. Belongs in `provenance`."""
    if not origin or ":" not in origin:
        return None
    return int(origin.split(":", 1)[1])


def provenance_for(parsed: ParsedRule, stored_rule_id: str) -> dict:
    """The out-of-hash record for one rule. Keyed by rule_id at the call site."""
    entry = {"origin_round": origin_round(parsed.origin)}
    return {stored_rule_id: {k: v for k, v in entry.items() if v is not None}}


def id_of_stored_rule(stored: dict) -> str:
    """Recompute the id of an already-stored rule. Strips exactly the fields
    convention 1 puts outside the id, so that a round-trip is stable."""
    body = {k: v for k, v in stored.items() if k not in FIELDS_OUTSIDE_THE_RULE_ID}
    return assign_rule_id(body)


def sort_rules(rules: list) -> list:
    """`rules` ascending by `rule_id` - restriction 6.

    Lossless, because precedence is by VERB and file order is never consulted,
    so array position carries no semantics for anything to lose.
    """
    return sorted(rules, key=lambda r: r["rule_id"])
