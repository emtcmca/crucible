"""render.py - the stored C4 policy document back into DSL text.

The ARMORER is handed "the current policy, in full" and must be able to copy a
real `rule_id` verbatim off it when it retracts one (CONVENTIONS 2.6 - copying an
identifier is a different task from computing one, and it is one a model does
reliably). So it has to see TEXT, not JSON: the language it writes in and the
language it reads the policy in should be the same language, or every prompt is
also a translation exercise.

THIS IS A MIRROR OF THE PARSER AND THAT IS A LIABILITY WORTH NAMING
-------------------------------------------------------------------
Two independent implementations of one mapping drift. The guard is a ROUND-TRIP
TEST: render each stored rule, parse the text back with L3's real parser,
re-compile it, and require the SAME `rule_id`. A renderer that emits something
the parser reads differently is caught by the content hash rather than by
inspection, which is the only way to catch it reliably. Same instrument, opposite
direction.

`origin` IS RENDERED, AND IT IS RENDERED FROM A FIELD RULING 32 SAYS SHOULD NOT
BE THERE. `contracts/policy_document.schema.json` stores `origin` inside
`hashed_payload.rules[]` with a `$comment` saying it lives there deliberately;
CONVENTIONS ruling 32 rules that it is provenance and belongs in the unhashed
`provenance` map keyed by rule_id. CONVENTIONS outranks contracts, so the
contract is the defect - and a lane does not edit `contracts/`. This renderer
reads whichever place the document carries it, so it keeps working either way,
and the conflict is REPORTED rather than routed around.
"""

from ..dsl.nodes import CMP_OPS

# stored op enum -> the text form. The inverse of nodes.CMP_OPS, built from it so
# the two cannot drift.
_OP_TEXT = {v: k for k, v in CMP_OPS.items()}


def _literal(value, value_type=None):
    if value_type == "enum_list" or isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _clause_texts(match):
    """`when` conjuncts, in the order the stored form holds them.

    Arrays are stored PRE-SORTED at construction (canonicalization restriction
    6), so this order is canonical rather than incidental, and rendering it
    unchanged is what makes the round trip land on the same id.
    """
    out = []
    for cond in match.get("arg_conditions", []):
        path, op = cond["path"], cond["op"]
        if op == "is_absent":
            out.append("%s is absent" % path)
        elif op == "is_present":
            out.append("%s is present" % path)          # GX5, ruling 42
        elif op == "in":
            out.append("%s in %s" % (path, _literal(cond["value"], "enum_list")))
        else:
            out.append("%s %s %s" % (path, _OP_TEXT[op],
                                     _literal(cond.get("value"),
                                              cond.get("value_type"))))
    for pred in match.get("predicates", []):
        form = pred["form"]
        if form == "preceded_by":
            out.append("preceded_by(%s)" % pred["value"])
        elif form == "episode_sum":
            out.append("episode_sum(%s) %s %s"
                       % (pred["arg_path"], _OP_TEXT[pred["op"]], pred["value"]))
        elif form == "arg_vs_episode_context":
            out.append("%s %s episode.%s"
                       % (pred["arg_path"], _OP_TEXT[pred["op"]],
                          pred["context_field"]))
        else:                                            # pragma: no cover
            raise ValueError("unknown predicate form %r" % form)
    return out


def _action_text(rule):
    verb = rule["verb"]
    if verb == "deny":
        return "deny"
    action = rule.get("action", {})
    if verb == "constrain_arg":
        return "constrain_arg(%s %s %s)" % (
            action["path"], _OP_TEXT[action["op"]],
            _literal(action.get("value"), action.get("value_type")))
    if verb == "require_approval":
        return "require_approval(%s)" % action["reason_code"]
    raise ValueError("unknown verb %r - there are three and there is no fourth"
                     % verb)


def render_rule(rule: dict, origin=None) -> str:
    match = rule.get("match", {})
    parts = ["cap:%s" % match["capability_class"]]
    # The STORED handle carries the `tool:` prefix; the GRAMMAR's qualifier
    # supplies it (`qualifier = "tool" ":" tool_handle`, `tool_handle = "t_"
    # HEX8`). Emitting the stored form directly produces `tool:tool:t_9f2c1b77`,
    # which the parser rejects with E_BAD_TOOL_HANDLE. Found by the round-trip
    # test, not by reading either file - which is the argument for having it.
    parts += ["tool:%s" % h.split("tool:", 1)[-1]
              for h in match.get("tool_names", [])]
    text = "rule %s: %s" % (rule["rule_id"], ", ".join(parts))

    clauses = _clause_texts(match)
    if clauses:
        text += " when " + " and ".join(clauses)
    text += " => " + _action_text(rule)

    origin = origin if origin is not None else rule.get("origin")
    if origin:
        text += " origin " + origin
    return text


def render_policy(document: dict) -> str:
    """The whole policy as DSL text, one rule per line."""
    payload = document.get("hashed_payload", document)
    provenance = document.get("provenance", {}) or {}
    version = document.get("lineage", {}).get("version")

    lines = []
    if version is not None:
        lines.append("# policy@v%d" % version)
    lines.append("# %d rule(s). Seed rules are irretractable."
                 % len(payload.get("rules", [])))
    for rule in payload.get("rules", []):
        # Read origin from wherever the document carries it - see the module
        # docstring on ruling 32 versus the frozen C4 schema.
        origin = rule.get("origin")
        if origin is None:
            origin = (provenance.get(rule["rule_id"], {}) or {}).get("origin")
        lines.append(render_rule(rule, origin))
    return "\n".join(lines)
