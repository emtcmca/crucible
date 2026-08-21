"""reference_engine.py - a CALIBRATION-ONLY shadow policy engine.

READ THIS BEFORE USING IT ANYWHERE. `crucible/policy/` belongs to L3, and L3
owns the real evaluator. This module exists for exactly one reason: the
REGRESSION_WARDEN and the nine known-bad fixtures must be buildable and provable
WITHOUT another lane's code, because six blind lanes cannot wait on each other
and the known-bad suite has to boot on D3 whatever else has slipped.

  - `run_warden(..., evaluate_call=<L3's engine>)` is the production call. The
    warden takes the evaluator as a PARAMETER; it is not wired to this file.
  - `tests/test_warden_replay.py::test_an_injected_engine_is_used_instead_of_
    the_reference_one` asserts that injection actually takes effect, so this
    cannot silently shadow a real engine and grade the run itself.
  - IF THIS ENGINE AND L3'S EVER DISAGREE ON A FIXTURE, THAT IS A CONTRACT
    REPORT, NOT A LOCAL FIX. Two implementations of the same semantics are two
    sources of truth, which is the defect class this project keeps paying for.
    The duplication is deliberate, bounded, and reported.

It implements only what the fixtures exercise: membership matching, the three
verbs with their precedence, plain argument conditions, and the three
episode-scoped predicate forms.

MEMBERSHIP, NEVER SET EQUALITY (ruling 22). A tool carries a SET of classes and
the tools that matter most carry several. Under equality a single-class rule
stops firing on exactly those tools, the sealed result reads "did not
generalize", and it is a real number produced by a matcher bug.

PRECEDENCE IS BY VERB, AND FILE ORDER IS NEVER CONSULTED.
`deny > require_approval > constrain_arg > implicit allow`, ties by lowest
`rule_id`. Rules are stored pre-sorted by `rule_id`, so array position carries
no semantics and sorting is lossless - which removes an entire class of "same
policy, different hash" bugs.
"""

_ABSENT = object()


class Prefix:
    """The ordered `ToolEvent` list already recorded IN THIS EPISODE, plus the
    frozen `episode.*` block.

    It is what makes the episode-scoped predicate forms possible without giving
    up purity: no clock, no counter surviving the episode, no hidden mutable
    state. The prefix is RECORDED in the evidence bundle, so replay is exact -
    and purity was never about statelessness, it was about determinism.
    """

    __slots__ = ("events", "episode_context")

    def __init__(self, events, episode_context):
        self.events = list(events)
        self.episode_context = episode_context or {}


class Decision:
    __slots__ = ("decision", "rule_id", "reason")

    def __init__(self, decision, rule_id=None, reason=None):
        self.decision = decision
        self.rule_id = rule_id
        self.reason = reason

    def __repr__(self):
        return "<%s %s>" % (self.decision, self.rule_id or "-")


ALLOW = "ALLOW"
DENY = "DENY"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

_VERB_RANK = {"deny": 0, "require_approval": 1, "constrain_arg": 2}


def _resolve(args, path):
    if path in args:
        return args[path]
    node = args
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _ABSENT
        node = node[part]
    return node


def _cmp(op, left, right):
    """Total. A wrong type is FALSE, never an exception - except under
    `constrain_arg`, where the caller reads an unevaluable path as VIOLATED."""
    if op in ("eq", "ne"):
        equal = left == right and (type(left) is bool) == (type(right) is bool)
        return equal if op == "eq" else not equal
    if op == "in":
        return isinstance(right, (list, tuple)) and left in right
    if op == "is_absent":
        return left is _ABSENT
    if type(left) is bool or type(right) is bool:
        return False
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return False
    return {"lt": left < right, "lte": left <= right,
            "gt": left > right, "gte": left >= right}[op]


def _arg_condition_holds(cond, event):
    value = _resolve(event.args, cond["path"])
    if cond["op"] == "is_absent":
        return value is _ABSENT
    if value is _ABSENT:
        return False
    return _cmp(cond["op"], value, cond.get("value"))


def _predicate_holds(pred, event, prefix):
    form = pred["form"]

    if form == "preceded_by":
        # A BLOCKED CAP_READS_PII DOES NOT SATISFY THIS. `preceded_by` is about
        # what HAPPENED, and a denied attempt did not happen. It also sees only
        # THAT a read occurred, never that this byte came from it - cross-call
        # dataflow is a language limit, out of scope, and stated rather than
        # hidden.
        want = pred["value"]
        return any(e.is_executed and want in e.capability_classes for e in prefix.events)

    if form == "episode_sum":
        # A bounded fold over a finite recorded prefix, not user arithmetic -
        # which is why it does not break the "total and terminating" rule. The
        # PENDING call is included: a prefix summing to 99,999 against a 100,000
        # ceiling must deny the pending 500, or the ceiling is off by one call.
        total = 0
        for e in list(prefix.events) + [event]:
            if e is event or e.is_executed:
                v = _resolve(e.args, pred["arg_path"])
                if type(v) is int:
                    total += v
        return _cmp(pred["op"], total, pred["value"])

    if form == "arg_vs_episode_context":
        # THE ONE THE SEPARABILITY PROOF DEMANDS. Three of the four mandated
        # near-miss fixtures differ from their paired attack ONLY by destination
        # or recipient identity; without this form, any rule that blocks the
        # attack breaks the fixture and any rule that preserves the fixture
        # cannot see the difference. G3 rejects every round and the loop never
        # promotes.
        field = pred["context_field"]
        if field not in prefix.episode_context:
            return False
        left = _resolve(event.args, pred["arg_path"])
        if left is _ABSENT:
            return False
        return _cmp(pred["op"], left, prefix.episode_context[field])

    raise ValueError("unknown predicate form %r" % form)


def _rule_matches(rule, event, prefix):
    match = rule.get("match", {})
    cap = match.get("capability_class")
    if cap and cap not in event.capability_classes:
        return False
    tools = match.get("tool_names") or []
    if tools and event.raw.get("tool_handle") not in tools:
        return False
    for cond in match.get("arg_conditions") or []:
        if not _arg_condition_holds(cond, event):
            return False
    for pred in match.get("predicates") or []:
        if not _predicate_holds(pred, event, prefix):
            return False
    return True


def _constraint_violated(rule, event):
    """`constrain_arg` FAILS CLOSED: an absent, null, wrong-typed, or
    unevaluable path is treated as VIOLATED and the call is denied. That is the
    whole point of the verb, and it is also why the verb is structurally
    disfavoured wherever a legitimate exception path exists - it is terminal when
    violated and cannot route to approval."""
    action = rule.get("action") or {}
    path, op = action.get("path"), action.get("op")
    if not path or not op:
        return True
    value = _resolve(event.args, path)
    if value is _ABSENT or value is None:
        return True
    return not _cmp(op, value, action.get("value"))


def evaluate(event, prefix, policy, approver=None):
    """One call against one policy. Returns a `Decision`.

    `approver` is accepted and IGNORED. The approver identity is declared by the
    FIXTURE and read by the identity layer; what the policy engine sees is
    `derived.approval_tier` and nothing else about the approver. Without that
    separation the forgeable channel returns through a different door in two
    weeks. The APPROVAL_ORACLE resolves APPROVAL_REQUIRED in the harness, not
    here.
    """
    rules = (policy.get("hashed_payload") or {}).get("rules") or []
    matched = [r for r in rules if _rule_matches(r, event, prefix)]
    if not matched:
        return Decision(ALLOW)

    matched.sort(key=lambda r: (_VERB_RANK.get(r.get("verb"), 9), r.get("rule_id", "")))
    for rule in matched:
        verb = rule.get("verb")
        if verb == "deny":
            return Decision(DENY, rule.get("rule_id"), "deny")
        if verb == "require_approval":
            return Decision(APPROVAL_REQUIRED, rule.get("rule_id"),
                            (rule.get("action") or {}).get("reason_code"))
        if verb == "constrain_arg" and _constraint_violated(rule, event):
            return Decision(DENY, rule.get("rule_id"), "constrain_arg violated")
    return Decision(ALLOW)
