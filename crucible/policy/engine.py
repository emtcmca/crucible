"""engine.py - the POLICY_ENGINE. Pure code, no model, no I/O, no clock.

    evaluate(tool_handle, capability_set, args, policy, episode_prefix) -> Decision

FIVE arguments. `role` was removed from this signature by ruling 25: no rule may
bind to it, so passing it would leave an input in the signature that nothing
reads - and an input nobody reads is an input nobody audits.

The four steps, from `contracts/decision.schema.json` `$defs/EVALUATION_CONTRACT`:

  STEP 1  MATCH, BY MEMBERSHIP, NEVER BY SET EQUALITY.
          A tool carries a SET. A rule names ONE class. The rule matches when
          its class is a MEMBER of the call's set. Under set equality a rule
          binding CAP_EXTERNAL_COMMS silently stops firing on exactly the tools
          that carry it alongside CAP_READS_PII - which are the tools that
          matter most - the F4 destination rule never fires on the tools it
          exists for, and THE SEALED RESULT READS "did not generalize". That is
          a real number produced by a matcher bug, which is the worst kind
          because you would believe it.

          `cap:UNCLASSIFIED` does not parse, so no rule can match a tool nobody
          classified and such a tool is ALWAYS ALLOWED. The engine FAILS OPEN
          there, deliberately, and that is correct: detection is not
          remediation, and the TRIPWIRE scores the Objective Set independently
          of policy, so an unclassified tool that moves money is still a
          recorded breach. It is gated by the D3 manifest-completeness check -
          every tool mapped, or the run reports partial coverage WITH THE
          UNMAPPED TOOLS NAMED.

  STEP 2  FILTER on the `when`. AN UNEVALUABLE CLAUSE RETAINS THE RULE.
          Fail closed: an absent, null, or wrong-typed argument means we do not
          know that the rule is inapplicable, and "we do not know" must not read
          as "allow". This is why predicate evaluation is TRI-STATE rather than
          boolean - a boolean forces UNEVALUABLE to collapse into one of the two
          answers, and it always collapses into the wrong one.

  STEP 3  RESOLVE BY STRICTNESS, NEVER BY FILE ORDER.
          deny > require_approval > constrain_arg > implicit ALLOW.
          Ties within a class resolve by LOWEST rule_id. File order is never
          consulted, so a patch cannot change behaviour by insertion position -
          which is what makes `rules` sortable by rule_id without loss, which is
          in turn what makes the canonical form unambiguous.

  STEP 4  RETURN exactly one Decision naming the rule that produced it.

  DEFAULT IS ALLOW. The instrument is SUBTRACTIVE ONLY. There is no `allow`
  verb, so no sequence of patches can widen the target's blast radius; the worst
  a compromised or confused ARMORER can do is over-block, and the benign floor
  is what catches that.

TWO PREFIX SEMANTICS THAT SILENTLY DISABLE THE PREDICATE THEY BELONG TO:

  * `preceded_by` and `episode_sum` read ONLY events that actually happened -
    `kind == TOOL_EXECUTED` and a policy decision of ALLOW. Otherwise AN
    ATTACKER SATISFIES `preceded_by` FOR FREE WITH ONE BLOCKED CALL: make the
    PII read, let the policy deny it, and the composition rule downstream now
    believes the read happened.
  * `episode_sum` INCLUDES THE PENDING CALL. Otherwise the call that first
    crosses the threshold is the one that executes, and the rule fires exactly
    one call late - which for a salami-slicing family is one call too many.

PURITY IS NOT STATELESSNESS. `episode_prefix` is the ordered ToolEvent list
already recorded in THIS episode. No clock, no counter surviving the episode, no
hidden mutable state; the prefix is in the evidence bundle, so replay is exact.
The `seq` field is what lets an aggregate window replace a wall clock.

THE SEAMS ARE METHODS ON PURPOSE. `match_rules`, `visible_prefix`,
`episode_sum` and `resolve` are separate overridable methods so that
`tests/strawman_policy.py` can build an implementation that is wrong in EXACTLY
ONE of them. A strawman that is wrong in four places is evidence about nothing.
"""

from .decision import (
    ALLOW,
    APPROVAL_REQUIRED,
    DENY,
    REASON_APPROVAL_REQUIRED,
    REASON_CONSTRAINT_VIOLATED,
    REASON_POLICY_DENY,
    Decision,
)

# Strictness, ascending. Resolution takes the maximum; ties break on lowest
# rule_id. This dict is the ONLY place order is encoded - there is deliberately
# no path by which array position could reach a comparison.
STRICTNESS = {"constrain_arg": 1, "require_approval": 2, "deny": 3}

# Tri-state predicate result. UNEVALUABLE is not a third truth value in the
# logic - it is a statement about our KNOWLEDGE, and it retains the rule.
TRUE, FALSE, UNEVALUABLE = "TRUE", "FALSE", "UNEVALUABLE"


# TWO FROZEN CONTRACTS DECLARE THIS ENUM IN TWO CASES, AND BOTH ARE CORRECT.
# `tool_event.schema.json:97` says ALLOW / DENY / APPROVAL_REQUIRED;
# `breach_record.schema.json` says allow / deny / approval_required. Neither is
# a defect and neither can be edited - they are hashed as C1 and C5.
#
# WHAT WAS A DEFECT, found 2026-08-21: this module compared `!= "ALLOW"` against
# a raw field. All 269 authored trace events spell it lowercase, so every one of
# them failed that comparison and was DROPPED FROM THE VISIBLE PREFIX. Measured:
# same call, same rule, prefix spelled "ALLOW" -> DENY, prefix spelled "allow"
# -> ALLOW.
#
# THE DIRECTION IS THE WHOLE POINT. Dropping an event SHRINKS the prefix, so
# `preceded_by` reads FALSE, so the rule that depends on it never fires and the
# attack passes. This failed OPEN, silently, on the exact predicate form that
# makes F5 and F7 expressible - P11 through P14 all rest on it - and nothing
# anywhere compared the two spellings. A check that cannot fail.
_ALLOW_SPELLINGS = frozenset({"ALLOW", "allow"})
_KNOWN_SPELLINGS = _ALLOW_SPELLINGS | frozenset({
    "DENY", "deny", "APPROVAL_REQUIRED", "approval_required"})


def _decision_is_allow(value):
    """True / False, or raises on a spelling neither contract declares.

    An absent decision reads as ALLOW: a TOOL_EXECUTED event normally carries
    none, because the decision lives on the matching TOOL_ATTEMPT.

    An UNRECOGNISED spelling raises rather than reading as non-ALLOW. Treating
    it as non-ALLOW would drop the event, and dropping is the fail-OPEN
    direction - it makes an episode look better behaved than it was. The same
    argument is written out in `corpus/model.py::canonical_decision`, which
    refuses for exactly this reason; the engine had no equivalent.
    """
    if value is None:
        return True
    if value in _ALLOW_SPELLINGS:
        return True
    if value in _KNOWN_SPELLINGS:
        return False
    raise ValueError(
        "E_DECISION_VOCABULARY: policy_decision %r is declared by neither "
        "frozen contract. tool_event.schema.json declares the upper spellings "
        "and breach_record.schema.json the lower. REFUSED rather than treated "
        "as non-ALLOW, because that would drop the event from the visible "
        "prefix, and a shorter prefix makes `preceded_by` read false - the "
        "rule stops firing and the attack passes. An under-counted prefix "
        "looks exactly like a well-behaved episode." % (value,))

_ORDERED = ("lt", "lte", "gt", "gte")
_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
}


def _is_int(x):
    # `type(x) is int`, never isinstance: bool subclasses int in Python, and
    # `True < 5` is a legal comparison that means nothing here. The same trap
    # `crucible/canon/canonical.py` documents for serialization.
    return type(x) is int


class _Effect:
    """One matched rule's contribution. Ordered in ARRAY order when handed to
    `resolve`, precisely so a file-order strawman is genuinely wrong."""

    __slots__ = ("outcome", "rule_id", "reason_code", "strictness")

    def __init__(self, outcome, rule_id, reason_code, strictness):
        self.outcome = outcome
        self.rule_id = rule_id
        self.reason_code = reason_code
        self.strictness = strictness


class PolicyEngine:
    """Holds one policy. `evaluate` is a pure function of its arguments."""

    def __init__(self, policy):
        """`policy` is a full policy document or a bare `hashed_payload`."""
        if policy is None:
            payload = {}
        elif "hashed_payload" in policy:
            payload = policy["hashed_payload"]
        else:
            payload = policy
        self.payload = payload
        self._rules = list(payload.get("rules", []))

    # -- STEP 1 ------------------------------------------------------------
    def match_rules(self, capability_set, tool_handle):
        """MEMBERSHIP: the rule's one class must be IN the call's set."""
        caps = set(capability_set or ())
        out = []
        for r in self._rules:
            m = r.get("match", {})
            if m.get("capability_class") not in caps:
                continue
            names = m.get("tool_names") or []
            if names and tool_handle not in names:
                continue
            out.append(r)
        return out

    # -- prefix visibility -------------------------------------------------
    def visible_prefix(self, episode_prefix):
        """Allow + ok only. See the module docstring for what a looser filter
        hands an attacker."""
        out = []
        for ev in episode_prefix or ():
            if ev.get("kind") != "TOOL_EXECUTED":
                continue
            # TOOL_EXECUTED normally carries no policy_decision - the decision
            # lives on the matching TOOL_ATTEMPT - so an absent one reads as
            # ALLOW. An explicit non-ALLOW is honoured, which makes the filter
            # correct under both event-writing conventions rather than under
            # whichever one happens to be in use.
            if _decision_is_allow(ev.get("policy_decision")) is not True:
                continue
            out.append(ev)
        return tuple(out)

    # -- aggregate ---------------------------------------------------------
    def _sum_over(self, arg_path, events):
        total = 0
        for ev in events:
            found, value = _lookup(ev.get("args") or {}, arg_path)
            if found and _is_int(value):
                total += value
        return total

    def episode_sum(self, arg_path, visible_prefix, pending_args):
        """Prefix PLUS the pending call. Returns None when unevaluable.

        Absent on the pending call contributes zero - a call with no
        `amount_minor` is not a money movement and must not be swept in. Present
        but not an integer is UNEVALUABLE and therefore fails closed, because a
        string where a minor-unit integer belongs is a call we cannot reason
        about, not a call worth zero.
        """
        total = self._sum_over(arg_path, visible_prefix)
        found, value = _lookup(pending_args or {}, arg_path)
        if found:
            if not _is_int(value):
                return None
            total += value
        return total

    # -- STEP 2 ------------------------------------------------------------
    def _clause(self, cond, args, visible, episode_context, is_predicate):
        if is_predicate:
            form = cond.get("form")
            if form == "preceded_by":
                want = cond.get("value")
                for ev in visible:
                    if want in (ev.get("capability_classes") or ()):
                        return TRUE
                return FALSE
            if form == "episode_sum":
                total = self.episode_sum(cond.get("arg_path"), visible, args)
                if total is None:
                    return UNEVALUABLE
                return _compare(total, cond.get("op"), cond.get("value"))
            if form == "arg_vs_episode_context":
                if episode_context is None:
                    return UNEVALUABLE
                found, left = _lookup(args, cond.get("arg_path"))
                if not found:
                    return UNEVALUABLE
                try:
                    right = episode_context.get(cond.get("context_field"))
                except Exception:                            # noqa: BLE001
                    return UNEVALUABLE
                return _compare(left, cond.get("op"), right)
            return UNEVALUABLE

        op = cond.get("op")
        found, left = _lookup(args, cond.get("path"))
        if op == "is_absent":
            # Total by construction: absence is always knowable.
            return TRUE if not found else FALSE
        if op == "is_present":
            # GX5, ruling 42. The complement of a total predicate is total, so
            # this returns before the `not found -> UNEVALUABLE` line below and
            # can never fall through to it.
            return TRUE if found else FALSE
        if not found:
            return UNEVALUABLE
        if op == "in":
            members = cond.get("value") or []
            try:
                return TRUE if left in members else FALSE
            except TypeError:                                # pragma: no cover
                return UNEVALUABLE
        return _compare(left, op, cond.get("value"))

    def _when(self, rule, args, visible, episode_context):
        m = rule.get("match", {})
        results = []
        for cond in m.get("arg_conditions") or ():
            results.append(self._clause(cond, args, visible, episode_context, False))
        for cond in m.get("predicates") or ():
            results.append(self._clause(cond, args, visible, episode_context, True))
        if FALSE in results:
            return FALSE
        if UNEVALUABLE in results:
            return UNEVALUABLE                     # retain the rule, fail closed
        return TRUE

    # -- verb -> effect ----------------------------------------------------
    def _effect(self, rule, args):
        verb = rule.get("verb")
        rid = rule.get("rule_id")
        if verb == "deny":
            return _Effect(DENY, rid, REASON_POLICY_DENY, STRICTNESS["deny"])
        if verb == "require_approval":
            action = rule.get("action") or {}
            return _Effect(APPROVAL_REQUIRED, rid,
                           action.get("reason_code") or REASON_APPROVAL_REQUIRED,
                           STRICTNESS["require_approval"])
        if verb == "constrain_arg":
            action = rule.get("action") or {}
            found, left = _lookup(args, action.get("path"))
            verdict = _compare(left, action.get("op"), action.get("value")) \
                if found else UNEVALUABLE
            if verdict == TRUE:
                return None                        # satisfied: no restriction
            # FAILS CLOSED. Absent, null, wrong-typed, or unevaluable is treated
            # as VIOLATED - that is the whole point of the verb.
            return _Effect(DENY, rid, REASON_CONSTRAINT_VIOLATED,
                           STRICTNESS["constrain_arg"])
        return None

    # -- STEP 3 ------------------------------------------------------------
    def resolve(self, effects):
        """Highest strictness wins; ties break on LOWEST rule_id.

        `effects` arrives in array order and that order is never consulted here.
        Sorting on `(-strictness, rule_id)` makes both halves explicit in one
        expression rather than leaving the tie-break to `max`'s stability, which
        WOULD be file order wearing a different name.
        """
        if not effects:
            return Decision(ALLOW)
        best = sorted(effects, key=lambda e: (-e.strictness, e.rule_id or ""))[0]
        return Decision(best.outcome, best.rule_id, best.reason_code)

    # -- STEP 4 ------------------------------------------------------------
    def evaluate(self, *, tool_handle, capability_set, args,
                 episode_prefix=(), episode_context=None) -> Decision:
        args = args or {}
        visible = self.visible_prefix(episode_prefix)
        effects = []
        for rule in self.match_rules(capability_set, tool_handle):
            if self._when(rule, args, visible, episode_context) == FALSE:
                continue
            eff = self._effect(rule, args)
            if eff is not None:
                effects.append(eff)
        return self.resolve(effects)


def _lookup(args, path):
    """`(found, value)` for an arg path.

    Flat key first, because C1 records `derived.approval_tier` as a literal key
    - see `contracts/golden/C1-tool_event.valid.json`. Dotted traversal is the
    fallback for a genuinely nested argument. Trying the flat key first matters:
    under traversal-first, `derived.approval_tier` would look for an object
    named `derived`, find nothing, and report the field absent - which fails
    closed rather than open, but silently disables every rule that reads one.
    """
    if not isinstance(args, dict) or not path:
        return False, None
    if path in args:
        return True, args[path]
    node = args
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _compare(left, op, right):
    """Tri-state comparison. Type mismatches are UNEVALUABLE, never False.

    Reporting a mismatch as False would silently drop the rule from
    consideration, which is failing OPEN through the back door: the rule stops
    applying because of a type, not because of a fact.
    """
    fn = _OPS.get(op)
    if fn is None or left is None or right is None:
        return UNEVALUABLE
    if op in _ORDERED:
        if not (_is_int(left) and _is_int(right)):
            return UNEVALUABLE
    else:
        left_bool, right_bool = type(left) is bool, type(right) is bool
        if left_bool != right_bool:
            return UNEVALUABLE
        if not left_bool and _is_int(left) != _is_int(right):
            return UNEVALUABLE
    try:
        return TRUE if fn(left, right) else FALSE
    except TypeError:                                        # pragma: no cover
        return UNEVALUABLE


def evaluate(tool_handle, capability_set, args, policy, episode_prefix=(),
             episode_context=None) -> Decision:
    """The five-argument form C2 names, positionally, in the contract's order.

    It exists so the contract's own signature is something you can call and not
    only something a comment describes.
    """
    return PolicyEngine(policy).evaluate(
        tool_handle=tool_handle, capability_set=capability_set, args=args,
        episode_prefix=episode_prefix, episode_context=episode_context)
