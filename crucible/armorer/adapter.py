"""adapter.py - the ARMORER's input projection. THE STRUCTURAL FIX.

C5's `$defs.ARMORER_PROJECTION` specifies what the ARMORER receives: an
enumerated projection of one BreachRecord and nothing else.

    { capability_classes_involved, offending_tool_calls, invariant_id,
      round_index, autopsy_id }

No free text. No attack payload. No natural-language rationale. No fixture id
and no fixture contents. No `human_only` subtree - THE ADAPTER HAS NO FIELD THAT
COULD HOLD IT.

WHY A LINT IS NOT A SUBSTITUTE, IN ONE SENTENCE
----------------------------------------------
The measurement spec's own example handed the ARMORER rule `r019` in English -
"Any composition of CAP_INVOKES_AGENT followed by CAP_MOVES_MONEY is reachable" -
and that sentence passed a modal-verb lint because it is in the indicative. A
lint tests the GRAMMATICAL MOOD of a sentence and a rule can be stated as a fact.

WHY THIS IS BUILT FROM A LIST RATHER THAN FILTERED AGAINST ONE
--------------------------------------------------------------
A denylist is a list of the names you already regret. The next leak arrives under
a name nobody denied - which is precisely how `generalization_hypothesis` got
through, and it is what `strawman.denylist_projection` reproduces. Building a new
dict from an allowlist makes the emitted key set CLOSED: a field added to C5
tomorrow is invisible here until someone adds it here on purpose.

THE SECOND CHANNEL, WHICH THE FIELD LIST DOES NOT CLOSE
-------------------------------------------------------
C5 types `offending_tool_calls[].args_redacted` as a bare `object`: no
`additionalProperties: false`, no value-type restriction. An adapter can name
exactly the right five fields and still forward a paragraph of English sitting in
an argument value. So argument VALUES are abstracted to shapes here, and the
`raw_args` strawman - correct at the top level, wrong one layer down - is what
proves the check discriminates.

The abstraction keeps exactly what the ARMORER needs to choose a rule and nothing
else:

    int   kept verbatim          `constrain_arg(amount_minor <= 50000)` needs the
                                 number, and an integer cannot carry a sentence
    bool  kept verbatim          the derived.* fields are booleans
    UPPER_SNAKE string  kept     a declared enum member is a manifest symbol, not
                                 free text - the grammar admits it as a literal
    any other string  -> OPAQUE_STRING
    null              -> ABSENT      (which the grammar can test: `is absent`)
    list or object    -> OPAQUE_STRUCTURE

That mapping is not a redaction of the values so much as a statement of what the
policy language can see. The DSL has NO FREE STRINGS. An argument value the
grammar could never mention is, to the ARMORER, information it cannot act on and
can only be misled by.

HONESTY BOUND, and it is stated in C5 too: fixture blindness is APPLICATION
CONVENTION PLUS A CODE CHECK, NOT IAM. The ARMORER holds `datastore.user` and
Firestore IAM has no per-collection granularity, so nothing at the platform layer
stops it reading a fixture collection. NEVER CALL THIS ONE ENFORCED ON CAMERA.
The one blindness that IS real IAM is the sealed family, and the 403 proves it.
"""

import copy
import re

# --------------------------------------------------------------------------
# The allowlists. C5 $defs.ARMORER_PROJECTION is the source; the ordering here
# is the order the fields are rendered in, chosen so the model reads the
# question (what broke, in what class) before the evidence.
# --------------------------------------------------------------------------

ARMORER_INPUT_FIELDS = (
    "autopsy_id",                   # for the provenance citation G6 requires
    "round_index",
    "invariant_id",                 # enum-shaped id, not a description
    "capability_classes_involved",  # enum members only
    "offending_tool_calls",
)

# THE CLAUSE PROJECTION - ALLOW-LIST, AND THE ALLOW-LIST IS THE POINT.
#
# `invariant_id` has always been validated here as "A POINTER INTO THE OBJECTIVE
# SET", and until 2026-08-24 the ARMORER was handed the pointer with no way to
# follow it. Two consecutive live rounds then bound
# `derived.episode_count_same_subject > 1` against an invariant whose real
# threshold is `gte 4`, because its projection carried the observed values
# 1, 2, 3 and nothing else. `> 1` is the ONLY inference that input supports:
# block above the lowest thing I saw. Not over-broad reasoning - correct
# reasoning on an input with the answer removed.
#
# WHY THIS IS NOT A BLINDNESS BREACH. architecture-spec 1.1 lists what the
# ARMORER is blind to: the attacker's NL rationale and payload, the benign and
# known-bad suites, the Warden's report contents, product vocabulary, the
# held-out family. THE OBJECTIVE SET IS NOT ON THAT LIST - it is on the
# RED_STRATEGIST's, where the failure it prevents is Red gaming the oracle
# instead of the target. Nothing about the benign suite passes through here.
#
# ALLOW-LIST RATHER THAN "DROP KEYS STARTING WITH _". `_why` is a paragraph of
# prose and the ARMORER's input has NO FREE-TEXT FIELD OF ANY KIND ON ANY PATH
# (locked 2026-08-20, after `generalization_hypothesis` was caught handing over
# the rule in English). A denylist keyed on the underscore would pass the next
# prose field somebody adds without one. This enumerates what may travel; every
# entry below is a shape, an enum member, or a number.
INVARIANT_FIELDS = (
    "id",                 # the pointer, echoed so the two cannot disagree
    "form",               # per_event | sequence | aggregate
    "capability_class",   # enum member
    "channel",
    "window",
    "group_by",
    "sum_path",           # the derived field the threshold is on
    "op",                 # gt | gte
    "value",              # THE BOUNDARY. The field whose absence caused the defect.
    "conditions",         # per_event predicates
    "steps",              # sequence predicates
)

# Inside `conditions[]` and `steps[].conditions[]`. Same doctrine one level down:
# a condition is a shape, never a sentence.
INVARIANT_CONDITION_FIELDS = ("path", "op", "value", "context_field")
INVARIANT_STEP_FIELDS = ("capability_class", "conditions")


ARMORER_CALL_FIELDS = (
    "seq",
    "tool_handle",
    "capability_classes",
    "policy_decision",
    "status",
    "args_redacted",
)

# Deliberately ABSENT from both lists, and each for its own reason:
#   human_only          the whole point
#   attack_family_id    naming the family is naming the attack's intent, and the
#                       ARMORER is blind to intent by construction
#   breach_id, run_id   run bookkeeping; nothing a rule may bind to
#   amount_minor_moved  a summary statistic that duplicates an argument the
#                       ARMORER already sees in context, and a rule bound to the
#                       summary would be bound to a number with no arg_path
#   args_hash           a hash is a deterministic computation; CONVENTIONS 2.6
#   latency_ms          timing, which the grammar cannot express and must not
#   role                RECORDED, NOT EVALUATED (ruling 25). role_name was the
#                       only plain-text product identifier the grammar admitted
#                       and it was cut for exactly that reason. Handing it to the
#                       ARMORER would re-open the escape hatch on the input side
#   objective_set_hash, manifest_hash, derived_schema_hash
#                       stamps for the evidence bundle; not policy inputs

OPAQUE_STRING = "OPAQUE_STRING"
OPAQUE_STRUCTURE = "OPAQUE_STRUCTURE"
ABSENT = "ABSENT"

# policy.ebnf: arg_path = ident { "." ident } ; ident = LOWER { LOWER|DIGIT|"_" }
_ARG_PATH_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
# policy.ebnf: enum_symbol = UPPER_SNAKE
_ENUM_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

CAP_CLASSES_AND_SENTINEL = frozenset((
    "CAP_MOVES_MONEY", "CAP_EXTERNAL_COMMS", "CAP_MUTATES_DURABLE_STATE",
    "CAP_READS_PII", "CAP_ESCALATES_PRIVILEGE", "CAP_INVOKES_AGENT",
    "UNCLASSIFIED",
))

_POLICY_DECISIONS = frozenset(("allow", "deny", "approval_required"))
_STATUSES = frozenset(("ok", "error"))
_INVARIANT_RE = re.compile(r"^inv_[a-z0-9_]+$")
_AUTOPSY_RE = re.compile(r"^aut_[a-z0-9_]+$")
_TOOL_HANDLE_RE = re.compile(r"^tool:t_[0-9a-f]{8}$")


class ProjectionError(ValueError):
    """The record cannot be projected at all.

    Raised rather than repaired. A record whose `invariant_id` is a sentence is
    not a record with a cosmetic problem - it is a CORONER that has started
    writing prose into an enumerated field, and repairing it quietly would hide
    exactly the drift this adapter exists to stop.
    """


def _abstract_value(value):
    """One argument value -> the shape the policy language can see."""
    if value is None:
        return ABSENT
    if isinstance(value, bool):          # before int: bool IS an int in Python
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value if _ENUM_SYMBOL_RE.match(value) else OPAQUE_STRING
    if isinstance(value, float):
        # CONVENTIONS 6: money is INT64 minor units and there are NO FLOATS in a
        # hashed payload. A float here means somebody wrote one upstream; the
        # ARMORER is not the place to find that out, so it is opaque rather than
        # silently truncated to an int the model would then bound a rule against.
        return OPAQUE_STRUCTURE
    return OPAQUE_STRUCTURE


def _abstract_args(args, drops):
    if not isinstance(args, dict):
        return {}
    out = {}
    for key in sorted(args):
        if not _ARG_PATH_RE.match(str(key)):
            # The KEY is not a legal arg_path, so no rule could ever name it. A
            # projection that hides prose in a value and forwards it in a key has
            # not hidden it.
            drops.append(("arg_key_not_an_arg_path", str(key)[:40]))
            continue
        abstracted = _abstract_value(args[key])
        if abstracted in (OPAQUE_STRING, OPAQUE_STRUCTURE):
            drops.append(("arg_value_abstracted", str(key)))
        out[key] = abstracted
    return out


def _project_call(call, drops):
    if not isinstance(call, dict):
        raise ProjectionError("an offending_tool_call must be an object")
    out = {}
    for field in ARMORER_CALL_FIELDS:
        if field not in call:
            continue
        value = call[field]
        if field == "args_redacted":
            out[field] = _abstract_args(value, drops)
        elif field == "capability_classes":
            unknown = [c for c in value if c not in CAP_CLASSES_AND_SENTINEL]
            if unknown:
                raise ProjectionError(
                    "capability_classes carries %r, which is not one of the six "
                    "classes or the UNCLASSIFIED sentinel" % unknown[0])
            out[field] = sorted(set(value))
        elif field == "policy_decision":
            if value not in _POLICY_DECISIONS:
                raise ProjectionError("policy_decision %r is not an enum member"
                                      % (value,))
            out[field] = value
        elif field == "status":
            if value not in _STATUSES:
                raise ProjectionError("status %r is not an enum member" % (value,))
            out[field] = value
        elif field == "tool_handle":
            if not _TOOL_HANDLE_RE.match(str(value)):
                raise ProjectionError(
                    "tool_handle %r is not opaque. Handles are `tool:t_` plus "
                    "eight hex BECAUSE what a tool is called is not information "
                    "the ARMORER is entitled to." % (value,))
            out[field] = value
        elif field == "seq":
            out[field] = int(value)
        else:                                            # pragma: no cover
            out[field] = copy.deepcopy(value)
    return out


def _project_conditions(conditions):
    out = []
    for cond in conditions or ():
        if not isinstance(cond, dict):
            raise ProjectionError("a clause condition must be an object")
        out.append({k: cond[k] for k in INVARIANT_CONDITION_FIELDS if k in cond})
    return out


def project_invariant(clause):
    """One Objective Set clause, reduced to its predicate. No prose, ever."""
    if not isinstance(clause, dict):
        raise ProjectionError("an Objective Set clause must be an object")
    out = {}
    for field in INVARIANT_FIELDS:
        if field not in clause:
            continue
        if field == "conditions":
            out[field] = _project_conditions(clause[field])
        elif field == "steps":
            steps = []
            for step in clause[field] or ():
                reduced = {k: step[k] for k in INVARIANT_STEP_FIELDS
                           if k in step and k != "conditions"}
                if "conditions" in step:
                    reduced["conditions"] = _project_conditions(step["conditions"])
                steps.append(reduced)
            out[field] = steps
        else:
            out[field] = copy.deepcopy(clause[field])
    if "id" not in out:
        raise ProjectionError("a projected clause with no id cannot be checked "
                              "against the invariant_id it is supposed to be")
    return out


def _clause_for(objective_set, invariant_id):
    """The clause an `invariant_id` points at. REFUSES rather than returning None.

    A pointer that resolves to nothing means the record describes a breach
    against an Objective Set other than the one in force. Emitting the projection
    anyway would silently hand the ARMORER the input that produced `> 1`, and
    nothing downstream could see that it had.
    """
    clauses = (getattr(objective_set, "clauses", None)
               or (objective_set or {}).get("clauses") or ())
    for clause in clauses:
        raw = clause if isinstance(clause, dict) else getattr(clause, "raw", None)
        if raw is None:
            raw = {k: v for k, v in vars(clause).items() if not k.startswith("__")}
        if raw.get("id") == invariant_id:
            return raw
    raise ProjectionError(
        "invariant_id %r resolves to no clause in the Objective Set in force. "
        "The pointer is dangling, which means this record was written against a "
        "different definition of breach than the one this run is locked to."
        % (invariant_id,))


def project(record, drops=None, objective_set=None, _clause_override=None):
    """Project one C5 BreachRecord into the ARMORER's input.

    `drops` is an optional list; every value this adapter abstracts away is
    appended to it. CONVENTIONS section 8 rule 9 - log the drop. Silent
    truncation reads as "covered everything" when it did not, and here the drop
    log is also the only place a leak ATTEMPT is visible: a CORONER that started
    writing sentences into arguments shows up as a rising count of
    `arg_value_abstracted`, not as an error.
    """
    if drops is None:
        drops = []
    if not isinstance(record, dict):
        raise ProjectionError("a BreachRecord is an object")

    out = {}
    for field in ARMORER_INPUT_FIELDS:
        if field not in record:
            continue
        value = record[field]
        if field == "offending_tool_calls":
            out[field] = [_project_call(c, drops) for c in value]
        elif field == "capability_classes_involved":
            unknown = [c for c in value if c not in CAP_CLASSES_AND_SENTINEL]
            if unknown:
                raise ProjectionError(
                    "capability_classes_involved carries %r" % unknown[0])
            out[field] = sorted(set(value))
        elif field == "invariant_id":
            if not _INVARIANT_RE.match(str(value)):
                raise ProjectionError(
                    "invariant_id %r is not `inv_` plus lowercase. An invariant "
                    "id is a POINTER INTO THE OBJECTIVE SET, and a free-form one "
                    "is a description of the breach - which is the channel this "
                    "adapter exists to close." % (value,))
            out[field] = value
        elif field == "autopsy_id":
            if not _AUTOPSY_RE.match(str(value)):
                raise ProjectionError("autopsy_id %r is malformed" % (value,))
            out[field] = value
        elif field == "round_index":
            out[field] = int(value)
        else:                                            # pragma: no cover
            out[field] = copy.deepcopy(value)

    # THE DEREFERENCE. Optional so every existing caller and fixture keeps
    # working - a required argument here would have been a wider change than the
    # defect warranted - but the CONDUCTOR always passes it, and
    # `test_the_conductor_hands_the_armorer_the_objective_set_in_force` is what
    # stops "optional" from quietly becoming "never supplied".
    if objective_set is not None or _clause_override is not None:
        clause = _clause_override
        if clause is None:
            clause = _clause_for(objective_set, out["invariant_id"])
        projected = project_invariant(clause)
        if projected["id"] != out["invariant_id"]:
            raise ProjectionError(
                "the projected clause is %r and the record names %r"
                % (projected["id"], out["invariant_id"]))
        out["invariant"] = projected

    for field in ARMORER_INPUT_FIELDS:
        if field not in out:
            raise ProjectionError(
                "the record is missing %r, which the ARMORER's input requires. "
                "A projection with a hole in it is not a smaller input, it is an "
                "input the model will fill in from somewhere." % field)
    return out
