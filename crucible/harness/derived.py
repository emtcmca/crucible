"""derived.py - the arithmetic behind the seven Part B `derived.*` fields.

W2 FOUND THAT THIS HAD NO OWNER, AND THAT IS A REAL GAP RATHER THAN AN OVERSIGHT
IN ANY ONE LANE.

L3 built the DISCIPLINE: which prefix is reserved, that a model-authored value
under `derived.` is discarded and the attempt recorded, that the stamp happens in
`before_tool` before evaluation. It deliberately left the computation injectable,
and its own docstring says why -- "the per-field computation belongs to the
corpus/harness layer", keeping them apart is what makes ruling 19's two refusals
checkable in one place.

L2 DECLARED the fields in Part B: names, types, and what each is computed from.

Nobody wrote the arithmetic, because it sits exactly between two lanes and the
path ownership map has no entry for it. It surfaced the first time an episode was
driven end to end, which is what the wave between the lanes and the loop is for.

THE ONE RULE THIS MODULE EXISTS TO KEEP
---------------------------------------
**Every field here is computed by CODE from the recorded episode prefix, the
frozen `episode.*` context, or a scenario record. No model is consulted, ever.**
Ruling 19: a model-computed input argument launders a model into the pure-code
path without touching a component, and every downstream number silently becomes
a statement about that model instead of about the policy.

`derived.subject_verified_in_episode` is the one that carries the most weight.
It is the field that makes the target's composition rule enforceable at all, and
it is STRONGER than the `preceded_by` predicate ruling 14 struck: `preceded_by`
is satisfied by a lookup of ANY order, so an attacker gets it for free by looking
up their own. This binds the lookup to THIS call's subject.
"""

from ..plugin import TOOL_ATTEMPT, TOOL_EXECUTED


def _executed(prefix):
    """Only calls that were ALLOWED and SUCCEEDED count toward any predicate.

    Otherwise an attacker satisfies a precedence requirement for free with one
    BLOCKED call: the attempt is in the prefix, and a naive reader counts it.
    """
    out, executed_ids = [], set()
    for e in prefix:
        if e.get("kind") == TOOL_EXECUTED:
            executed_ids.add((e.get("invocation_id"), e.get("tool_handle")))
    for e in prefix:
        if e.get("kind") == TOOL_ATTEMPT and \
                (e.get("invocation_id"), e.get("tool_handle")) in executed_ids:
            out.append(e)
    return out


def _subject_key(manifest, tool_handle):
    for t in manifest.get("tools", []):
        if t["tool_handle"] == tool_handle:
            return t.get("subject_key")
    return None


def _beneficiary_key(manifest, tool_handle):
    for t in manifest.get("tools", []):
        if t["tool_handle"] == tool_handle:
            return t.get("beneficiary_key")
    return None


class DerivedCompute:
    """Callable matching `DerivedStamper(compute=...)`.

    `scenario` carries the frozen non-episode facts a couple of fields need --
    account age, delivery confirmation, the frozen as-of date. They come from the
    corpus instance, never from a wall clock: a target that read the system clock
    would make its own behaviour non-replayable, and the whole build rests on
    replay.
    """

    def __init__(self, manifest, scenario=None):
        self.manifest = manifest
        self.scenario = scenario or {}

    def __call__(self, name, tool_args, context):
        prefix = list(context.get("prefix") or ())
        handle = context.get("tool_handle")
        fn = getattr(self, "_" + name.split(".", 1)[1], None)
        if fn is None:
            raise ValueError(
                "%r is declared in Part B and has no computation here. A "
                "declared field with no arithmetic is worse than an undeclared "
                "one: the schema promises the evaluator a value that never "
                "arrives." % name)
        return fn(tool_args, prefix, handle)

    # -- the load-bearing one ---------------------------------------------
    def _subject_verified_in_episode(self, args, prefix, handle):
        """Was THIS call's subject looked up earlier in THIS episode?

        Binding to the subject is the whole point. `preceded_by(CAP_READS_PII)`
        is satisfied by a lookup of ANY order, which an attacker gets for free.
        """
        key = _subject_key(self.manifest, handle)
        if not key:
            return False
        subject = args.get(key)
        if subject is None:
            return False
        for e in _executed(prefix):
            k = _subject_key(self.manifest, e.get("tool_handle"))
            if k and (e.get("args") or {}).get(k) == subject:
                return True
        return False

    def _episode_sum_amount_minor_same_beneficiary(self, args, prefix, handle):
        """INCLUDES THE PENDING CALL. Excluding it means the call that first
        crosses a threshold is the one that executes."""
        key = _beneficiary_key(self.manifest, handle)
        who = args.get(key) if key else None
        total = int(args.get("amount_minor") or 0)
        if who is None:
            return total
        for e in _executed(prefix):
            k = _beneficiary_key(self.manifest, e.get("tool_handle"))
            a = e.get("args") or {}
            if k and a.get(k) == who:
                total += int(a.get("amount_minor") or 0)
        return total

    def _episode_count_same_subject(self, args, prefix, handle):
        key = _subject_key(self.manifest, handle)
        subject = args.get(key) if key else None
        if subject is None:
            return 0
        n = 0
        for e in _executed(prefix):
            k = _subject_key(self.manifest, e.get("tool_handle"))
            if k and (e.get("args") or {}).get(k) == subject:
                n += 1
        return n + 1          # the pending call, same reason as the sum

    # -- scenario-sourced. Frozen facts, never a clock. --------------------
    def _approval_tier(self, args, prefix, handle):
        return self.scenario.get("approval_tier", "T0")

    def _account_age_days(self, args, prefix, handle):
        return int(self.scenario.get("account_age_days", 0))

    def _delivery_confirmed(self, args, prefix, handle):
        return bool(self.scenario.get("delivery_confirmed", False))

    def _days_since_delivery(self, args, prefix, handle):
        return int(self.scenario.get("days_since_delivery", 0))
