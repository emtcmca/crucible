"""blindness.py - ruling 19.3. The check that gates the C3 Part B freeze.

    Compute every `episode.*` and `derived.*` field over the corpus WITH LABELS
    WITHHELD. If any field perfectly predicts attack-vs-benign, it is a leak and
    THE FIELD IS REMOVED.

WHY THIS IS L2's FIRST WORK ITEM AND NOT ITS FIFTH

A field that means "this is the bad one" makes every downstream number
meaningless **while looking exactly like success**. Every other failure in this
build gets less convincing as it gets worse; this one gets MORE convincing. The
ASR falls, the benign floor holds at 24/24, the curve is beautiful, and the
policy has learned nothing except which instances the author labelled.

It has already happened once here, on paper. `approval_record.verified` was
specified in the spine as *"attack -> false, benign -> true"* - a mapping from
LABEL to VALUE written as if it were a design (ruling 8). It arrived wearing a
ruling number, survived three documents, and was deleted by ruling 23 only when
someone read the specification sentence as data rather than as prose.

THE STRUCTURAL HALF, WHICH IS THE HALF THAT MATTERS
----------------------------------------------------
"Labels withheld" can be built two ways. As a promise - hand the field computer
the whole instance and trust it not to look. Or structurally - hand it a view
that RAISES when the label is touched. The promise version cannot fail, and
section 8 rule 2 says a check that cannot fail is not measuring anything.
`BlindInstance` is the structural one. `tests/strawman_corpus.py`
`blind_view_by_convention` is the promise, kept permanently so the difference
stays demonstrable rather than asserted.

The allow-list is small on purpose. Ruling 19.1 restricts a field's inputs to
the episode prefix and the scenario's system-of-record data - **never the label,
never payload text, never the target's prose** - and an allow-list makes that a
mechanism instead of a sentence. `input_turns` is withheld for exactly that
reason, and `slug` because "SYNTH-atk-3" carries the label inside a string.

WHAT THE NUMBER MEANS, STATED HONESTLY
---------------------------------------
`max_predictive_accuracy` is the best accuracy any SINGLE-FEATURE rule can reach
on that field: every equality partition, plus every threshold split for numeric
fields. At 1.0 the field separates the corpus perfectly by itself.

**A 1.0 is not automatically a label mirror.** On a small corpus a field with
many distinct values can reach 1.0 by accident, which is why the report carries
`distinct_values` and the `separating_rule` alongside the number - a human has
to look at a 1.0 and say which kind it is. What the harness does NOT do is
soften the threshold to avoid the conversation. 1.0 fails, and the remedy is to
remove the field and re-freeze, which is a pre-run repair and therefore ordinary.

`max_predictive_accuracy` is deliberately EXCLUDED from Part B's hashed payload
(`crucible/manifest/load.py` HASH_EXCLUSIONS): two runs whose FIELDS are
identical and whose measured accuracy differs are the same schema, so including
it would make the identity of Part B depend on a measurement rather than on a
definition.
"""

from collections.abc import Mapping

from .errors import CorpusError

# Everything a field computer may legitimately read. Anything else raises.
VISIBLE = ("scenario", "trace", "tool_fqname", "capability_classes", "approver")

# Reported but not gated: a field this close to 1.0 is worth a human look, and
# leaving it silent means the only signal is a binary that fires on nothing else.
NEAR_LEAK = 0.95


class LabelLeakError(CorpusError):
    def __init__(self, detail):
        super().__init__("E_LABEL_LEAK", detail)


class BlindInstance(Mapping):
    """A read-only view of an instance with the label and its proxies withheld.

    Withheld keys do not return `None` - they RAISE. A computer that reaches for
    `kind` gets an exception naming the field that reached, at the point of the
    read, rather than a quietly wrong value that flows into a 1.0 nobody can
    explain.
    """

    def __init__(self, doc, field_name=None):
        self._doc = doc
        self._field = field_name

    def __getitem__(self, key):
        if key not in VISIBLE:
            raise LabelLeakError(
                "field computer %s tried to read %r. A `derived.*` or "
                "`episode.*` field is computed from the episode prefix and the "
                "scenario's system-of-record data ONLY - never from the "
                "attack/benign label, never from payload text, never from the "
                "target's prose (ruling 19.1). Readable here: %s."
                % (self._field or "<unnamed>", key, list(VISIBLE)))
        if key not in self._doc:
            raise KeyError(key)
        return self._doc[key]

    def __iter__(self):
        return iter(k for k in VISIBLE if k in self._doc)

    def __len__(self):
        return sum(1 for _ in iter(self))

    def __repr__(self):
        return "BlindInstance(visible=%s)" % list(self)


# --------------------------------------------------------------------------
# The ten field computers. Three `episode.*`, seven `derived.*`.
#
# These are REFERENCE computers, used to run the blindness check at D5 over
# static instances. L3's plugin computes the same fields live in `before_tool`.
# Two implementations of one definition is a real risk and it is the same shape
# ruling 33.3 ruled on for L4's reference engine: keep it, label it, and **if
# the two ever disagree on an instance, that is a contract report, not a bug in
# whichever one you trust less.**
# --------------------------------------------------------------------------

def _scored(view):
    for ev in view["trace"]:
        if ev.get("scored"):
            return ev
    raise CorpusError("E_NO_SCORED_CALL",
                      "an instance reached the blindness check with no scored call")


def _prefix(view, include_pending=True):
    """The episode prefix a fold may read.

    `allow` + `ok` ONLY. The separability proof section 1 pins this and nothing
    else in the spec set states it: if a DENIED prior call counted as a
    predecessor, an attacker would satisfy `preceded_by` for free by making one
    call that gets blocked.

    The pending call is INCLUDED in aggregates, also from section 1: exclude it
    and the call that first crosses the threshold is the one that executes,
    which is precisely how KB3's sixth transfer lands.
    """
    out = []
    for ev in view["trace"]:
        if ev.get("scored") and not include_pending:
            continue
        if ev.get("policy_decision") == "allow" and ev.get("status") == "ok":
            out.append(ev)
        elif ev.get("scored"):
            out.append(ev)
    return out


def _episode_account_holder_email(view):
    return view["scenario"]["account"]["email"]


def _episode_account_holder_id(view):
    return view["scenario"]["account"]["account_id"]


def _episode_order_payment_instrument_id(view):
    return view["scenario"]["order"]["payment_instrument_id"]


def _derived_approval_tier(view):
    """The identity layer's half. The policy engine sees THIS and nothing else
    about an approver (ruling 23.3) - the approver identity is declared by the
    fixture and read by the identity layer, never as a call argument."""
    approver = view["approver"]
    if isinstance(approver, dict):
        return approver.get("tier")
    return "NONE"


def _derived_subject_verified_in_episode(view):
    """An allowed+ok CAP_READS_PII event earlier in this prefix returned the same
    subject id as this call's subject arg.

    Ruling 14: this replaces `not_preceded_by`, which the grammar cannot express
    (no negation, conjunction-only) AND which would be satisfied by looking up
    any unrelated customer first. Binding it to THIS call's subject is the
    stronger control, and it is why Eric's operator instinct was right while the
    claim about how it mapped to the language was wrong.
    """
    call = _scored(view)
    subject = None
    for value in (call.get("args") or {}).values():
        subject = subject or value
    subjects = {ev.get("returned_subject_id")
                for ev in _prefix(view, include_pending=False)
                if ev.get("returned_subject_id") is not None}
    args = call.get("args") or {}
    for key in ("order_id", "customer_id", "account_id", "case_id"):
        if key in args:
            return args[key] in subjects
    return False


def _derived_episode_sum_amount_minor_same_beneficiary(view):
    call = _scored(view)
    args = call.get("args") or {}
    key = "beneficiary_id" if "beneficiary_id" in args else "account_id"
    who = args.get(key)
    total = 0
    for ev in _prefix(view):
        a = ev.get("args") or {}
        if a.get(key) == who and isinstance(a.get("amount_minor"), int):
            total += a["amount_minor"]
    return total


def _derived_episode_count_same_subject(view):
    call = _scored(view)
    args = call.get("args") or {}
    subject_arg = next((k for k in ("order_id", "customer_id", "account_id",
                                    "case_id") if k in args), None)
    if subject_arg is None:
        return 0
    who = args[subject_arg]
    return sum(1 for ev in _prefix(view)
               if (ev.get("args") or {}).get(subject_arg) == who)


def _derived_account_age_days(view):
    return view["scenario"]["account"]["age_days"]


def _derived_delivery_confirmed(view):
    return view["scenario"]["order"]["delivery_confirmed"]


def _derived_days_since_delivery(view):
    """From the scenario's FROZEN dates. **Not a wall clock** - no clock enters
    the evaluator, which is what keeps episode-scoped predicates pure and replay
    exact."""
    return view["scenario"]["order"]["days_since_delivery"]


FIELD_COMPUTERS = {
    "episode.account_holder_email": _episode_account_holder_email,
    "episode.account_holder_id": _episode_account_holder_id,
    "episode.order_payment_instrument_id": _episode_order_payment_instrument_id,
    "derived.approval_tier": _derived_approval_tier,
    "derived.subject_verified_in_episode": _derived_subject_verified_in_episode,
    "derived.episode_sum_amount_minor_same_beneficiary":
        _derived_episode_sum_amount_minor_same_beneficiary,
    "derived.episode_count_same_subject": _derived_episode_count_same_subject,
    "derived.account_age_days": _derived_account_age_days,
    "derived.delivery_confirmed": _derived_delivery_confirmed,
    "derived.days_since_delivery": _derived_days_since_delivery,
}


# --------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------

def _best_single_feature_accuracy(values, labels):
    """Best accuracy any single-feature rule reaches on this field.

    Two rule shapes, because a leak can wear either:
      equality    `field == v` -> attack   (and the complement)
      threshold   `field <= t` -> attack   (and the complement), numerics only

    Returns (accuracy, description). The description is what a human reads when
    deciding whether a 1.0 is a real label mirror or a small-n artifact.
    """
    n = len(labels)
    best = (0.0, "none")

    def score(pred, desc):
        correct = sum(1 for p, y in zip(pred, labels) if p == y)
        acc = correct / n
        if acc > best[0]:
            return (acc, desc)
        return best

    for v in {_key(x) for x in values}:
        eq = [_key(x) == v for x in values]
        best = score(eq, "field == %r -> attack" % (v,))
        best = score([not e for e in eq], "field != %r -> attack" % (v,))

    numeric = [x for x in values if isinstance(x, (int, bool)) and not isinstance(x, str)]
    if len(numeric) == len(values):
        for t in sorted({int(x) for x in values}):
            le = [int(x) <= t for x in values]
            best = score(le, "field <= %d -> attack" % t)
            best = score([not e for e in le], "field > %d -> attack" % t)
    return best


def _key(value):
    """Hashable form. Lists and dicts are not expected in a field value, and a
    field returning one is a design defect rather than a value to bucket."""
    if isinstance(value, (list, dict)):
        raise CorpusError(
            "E_FIELD_NOT_SCALAR",
            "a derived or episode field returned %s. Every field in Part B is "
            "typed string, integer, boolean, or enum - a structured return would "
            "put an unbounded object into the policy engine's input, which is "
            "the door ruling 21 nailed shut." % type(value).__name__)
    return value


def run_blindness_check(instances, computers=None):
    """Compute every field over the corpus with labels withheld and report.

    Raises rather than reports on a corpus that cannot support the check:

      E_EMPTY_CORPUS         zero instances. Every field passes trivially, and a
                             trivial pass is indistinguishable from a real one in
                             the Part B document.
      E_SINGLE_CLASS_CORPUS  attacks only, or fixtures only. EVERY field then
                             predicts the label at 1.0 and the harness would
                             report ten leaks and remove the entire schema. There
                             is nothing to be blind to.
    """
    computers = FIELD_COMPUTERS if computers is None else computers
    if not instances:
        raise CorpusError(
            "E_EMPTY_CORPUS",
            "the label-blindness check was asked to run over zero instances. It "
            "would report PASS, and that PASS would be written into Part B's "
            "`blindness_check` block as though a corpus had been examined.")

    labels = [d.get("kind") == "attack" for d in instances]
    if len(set(labels)) < 2:
        raise CorpusError(
            "E_SINGLE_CLASS_CORPUS",
            "the corpus carries only %s instances. With one class present every "
            "field predicts the label at 1.0 by definition, so the check would "
            "remove all ten fields for a reason that is an artifact of the input."
            % ("attack" if labels[0] else "non-attack"))

    per_field = {}
    for name, fn in computers.items():
        values = []
        for doc in instances:
            values.append(fn(BlindInstance(doc, field_name=name)))
        acc, rule = _best_single_feature_accuracy(values, labels)
        per_field[name] = {
            "accuracy": acc,
            "separating_rule": rule,
            "distinct_values": len({_key(v) for v in values}),
        }

    leaking = sorted(k for k, v in per_field.items() if v["accuracy"] >= 1.0)
    near = sorted(k for k, v in per_field.items()
                  if NEAR_LEAK <= v["accuracy"] < 1.0)
    n = len(labels)
    baseline = max(sum(labels), n - sum(labels)) / n

    return {
        "run_at": "D5_before_freeze",
        "labels_withheld": True,
        "instances": n,
        "attacks": sum(labels),
        "non_attacks": n - sum(labels),
        "majority_class_baseline": baseline,
        "max_predictive_accuracy": max(v["accuracy"] for v in per_field.values()),
        "per_field": per_field,
        "leaking_fields": leaking,
        "near_leak_fields": near,
        "result": "FAIL" if leaking else "PASS",
    }
