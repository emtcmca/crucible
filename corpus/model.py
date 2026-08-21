"""model.py - the frozen constants, and the values that are SOURCED rather than retyped.

`CLAUDE.md`, on the infrastructure names: *a second copy of a bucket name is a
second source of truth*. The same argument applies to every value here that
exists somewhere else in the repository, and the rule this module follows is:

    a constant may be typed here ONLY if CONVENTIONS.md is its home.
    anything else is READ from the artifact that owns it, at import time,
    and cross-checked.

So the six capability classes come from `crucible.manifest` (which got them from
section 2.2), the twelve `reason_code` values and the six approval tiers come
from capability manifest Part A, and the four FAULT reason codes come from
`taxonomy/non-breach-declarations.json` NB-01 - because the lint and the
Objective Set have to agree about what a fault code is, and the Objective Set
reads NB-01.

That last one is not theoretical. NB-01's whole purpose is that a fault-code
refund outside the window is CORRECT POLICY (ruling 6, Visa dispute condition
13.3). If this module's idea of "fault code" drifted from NB-01's, the lint
would clear a pair the scorer then calls a breach, and the harness would
manufacture a false positive that no gate in the build catches.
"""

import json
import pathlib

from crucible.manifest.load import CAPABILITY_CLASSES, load_part_a as _load_a

from .errors import CorpusError

REPO = pathlib.Path(__file__).resolve().parent.parent
PART_A_PATH = REPO / "target" / "refund_agent" / "capability_manifest.json"
NON_BREACH_PATH = REPO / "taxonomy" / "non-breach-declarations.json"
TOOL_EVENT_PATH = REPO / "contracts" / "tool_event.schema.json"
BREACH_RECORD_PATH = REPO / "contracts" / "breach_record.schema.json"

# -- CONVENTIONS.md is the home of these, so they are typed here. --------------
# Section 4, frozen numbers. A lane that wants a different value stops and reports.
TRAINING_FAMILIES = ("F1", "F2", "F3", "F5", "F6", "F7")
SEALED_FAMILY = "F4"
TRAINING_PER_FAMILY = 8

# AMENDED BY RULING 2026-08-21. F5 alone carries ten; every other family is
# still eight, and the shape is still "eight per family with one named
# exception" rather than a table of arbitrary numbers.
#
# WHY THIS IS AN OVERRIDE DICT AND NOT A FLAT PER-FAMILY TABLE. A table makes 10
# look exactly as ordinary as 8, and the whole point is that it is not: it is a
# ruling, with a reason, that a reader six days from now must be able to see
# without going to the ledger. An override is a deviation that has to announce
# itself.
#
# THE REASON. `CAP_INVOKES_AGENT` is one of six capability classes and was
# exercised by ZERO episodes - `delegate_to_specialist` had been added to the
# target specifically to make the class instantiable, and then nothing ever
# called it. So `r_new11` could never fire, be learned, or be falsified, and one
# sixth of the taxonomy was untested.
#
# WHY AMEND RATHER THAN RETIRE, which was the first ruling and was withdrawn:
# retirement cannot make room. All twelve original near-misses are load-bearing
# for a separability pair, so retiring any of them orphans a pair. The only
# non-load-bearing near-misses were the two the branch itself adds - and those
# are the ONLY benign delegation coverage in the corpus, so retiring them would
# have left two delegation ATTACKS with no benign partner and nothing to prove a
# learned deny rule does not over-block ordinary delegated work.
TRAINING_FAMILY_OVERRIDES = {"F5": 10}

TRAINING_TOTAL = 50        # 48 + the two F5 instances above.
SEALED_TARGET = 24
SEALED_FLOOR = 18          # ABSOLUTE. Arithmetic, not preference - see sizing.py.
BENIGN_TOTAL = 26          # 24 + F5-NM-03, F5-NM-04. Same ruling.
NEAR_MISS_FLOOR = 14       # 12 + the same two, both near-misses.
KNOWN_BAD_TOTAL = 9

# Ruling 13 condition 2: TRAIN the arg-cmp-episode shape on C2 and C4, SEAL on
# C1 and C3 - classes where the shape was never exercised, against tools the
# loop never saw.
SEALED_CLASSES = frozenset({"CAP_MOVES_MONEY", "CAP_MUTATES_DURABLE_STATE"})

KINDS = ("attack", "benign", "known_bad")

# `contracts/canonicalization.md` section 2. The string, not `null`: the corpus
# is hash-locked at D5 and canonicalization restriction 5 refuses null in a
# hashed payload. Presence stays mandatory either way, which is the half ruling
# 23.4 was protecting.
NO_APPROVER = "NONE"

# Spellings that mean "the author meant NONE and wrote something else". Refused
# by name rather than coerced: a coercion here writes a value into an artifact
# that gets hashed, and the failure would surface on freeze day as a corpus that
# will not canonicalize.
DEAD_APPROVER_SPELLINGS = (None, "", "none", "None", "null", "NULL", "Null")


def load_part_a(path=None):
    """Capability manifest Part A, through the real loader.

    Not `json.load`. `crucible.manifest.load_part_a` enforces the things that
    make Part A trustworthy - no duplicate handles, no absent capability_classes
    defaulting to the empty set, no tool declaring UNCLASSIFIED as a class - and
    a corpus validated against an unvalidated manifest is validated against
    nothing.
    """
    manifest, _digest = _load_a(str(path or PART_A_PATH))
    return manifest


def tool_index(manifest):
    return {t["tool_fqname"]: t for t in manifest["tools"]}


def structured_arg_paths(manifest, tool_fqname):
    """The arg paths Part A declares as STRUCTURED and COMPARABLE for a tool.

    Ruling 13 condition 1: the smuggled item must be a structured, comparable
    argument - payout instrument, recipient, delegate queue, write target. Part
    A already declares exactly those, three ways:

        destination_args   where the call is aimed
        subject_key        whose record it acts on
        beneficiary_key    who gets the money

    **Everything else on the signature is free text as far as this lint is
    concerned, and that is the safe direction.** An allow-list grows when the
    manifest grows; a denylist of free-text names ({"memo", "note"}) silently
    stops covering every argument added after it was written.
    """
    t = tool_index(manifest).get(tool_fqname)
    if t is None:
        raise CorpusError("E_TOOL_NOT_IN_MANIFEST",
                          "%s is not declared in capability manifest Part A" % tool_fqname)
    paths = set(t.get("destination_args", []))
    for key in ("subject_key", "beneficiary_key"):
        if t.get(key):
            paths.add(t[key])
    return frozenset(paths)


def _non_breach_declarations():
    return json.loads(NON_BREACH_PATH.read_text(encoding="utf-8"))


def fault_reason_codes(manifest=None):
    """The FAULT reason codes, read out of NB-01 and cross-checked against Part A.

    Two artifacts have to agree here or the harness manufactures a false
    positive: NB-01 (which the Objective Set installs) and Part A (which the DSL
    parser validates enum members against). Reading one and asserting against
    the other is the cheapest possible check that they have not drifted.
    """
    decls = _non_breach_declarations()["declarations"]
    nb01 = [d for d in decls if d["id"] == "NB-01"]
    if not nb01:
        raise CorpusError(
            "E_NB01_MISSING",
            "taxonomy/non-breach-declarations.json declares no NB-01. The "
            "fault-reason_code lint would then pass everything, and a lint that "
            "passes everything is a check that cannot fail.")
    codes = frozenset(nb01[0]["recognition_signature"]["reason_code_in"])
    if not codes:
        raise CorpusError("E_NB01_EMPTY", "NB-01 declares no fault reason codes")
    declared = set((manifest or load_part_a())["arg_enums"]["reason_code"])
    drift = sorted(codes - declared)
    if drift:
        raise CorpusError(
            "E_FAULT_CODE_NOT_DECLARED",
            "NB-01 names %s as fault reason codes and capability manifest Part A "
            "does not declare them. The lint and the Objective Set would then "
            "disagree about what a fault code is, and the disagreement is "
            "invisible in every artifact downstream." % drift)
    return codes


def approval_tiers(manifest=None):
    """The six tiers, from Part A's `derived.approval_tier` enum.

    Ruling 20 splits this field across the freeze line on purpose: the VALUES
    are Part A (the DSL parser must validate a rule naming T2 from D3 onward,
    including rules written before the corpus exists), the COMPUTATION is Part B.
    """
    return frozenset((manifest or load_part_a())["arg_enums"]["derived.approval_tier"])


# ---------------------------------------------------------------------------
# The trace vocabulary. TWO FROZEN CONTRACTS SPELL THIS ENUM TWO WAYS.
# ---------------------------------------------------------------------------
#   contracts/tool_event.schema.json   policy_decision: ALLOW | DENY | APPROVAL_REQUIRED
#   contracts/breach_record.schema.json  policy_decision: allow | deny | approval_required
#                                        status:          ok | error
#
# The corpus trace was authored in the breach-record spelling and the C2 ToolEvent
# is upper. Section 8 rule 11 says one concept, one name; these are frozen
# artifacts and this module may not edit either, so the reconciliation lives here
# and is REPORTED rather than hidden.
#
# **The defect this closes is silence, not casing.** `blindness._prefix` matched
# one spelling and simply stopped counting an event carrying the other. Nothing
# raised. Every episode aggregate read low, `episode_sum_amount_minor_...`
# under-counted, and an `episode_sum` rule quietly stopped firing on exactly the
# calls it exists to catch - the KB3 shape, arriving through a typo. So the two
# CONTRACT-DECLARED spellings both resolve, and anything else is REFUSED by name.
# `"Allow"`, `"allowed"`, `"AllowED"` and an absent field all raise.

def _enum_at(path, prop):
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == prop and isinstance(value, dict) and "enum" in value:
                    found.append(tuple(value["enum"]))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    if not found:
        raise CorpusError(
            "E_CONTRACT_ENUM_MISSING",
            "%s declares no enum for %r. This module reads the vocabulary out of "
            "the contract rather than retyping it, so an absent enum would leave "
            "the reader with nothing to validate against and every value would "
            "pass." % (pathlib.Path(path).name, prop))
    return max(found, key=len)


def trace_vocabulary():
    """Canonical decision/status maps, READ from the two contracts, cross-checked.

    Returns `(decisions, statuses)`, each a dict mapping every accepted spelling
    to the C2 canonical form. **C2 wins on the canonical spelling** - it is the
    contract the live plugin writes - and the breach-record spelling is admitted
    as a declared alias, not as a second vocabulary.

    Raises if the two contracts ever stop being case-variants of one another.
    That would be a real divergence rather than a casing difference, and silently
    admitting both would then mean admitting two different enums under one name.
    """
    c2 = _enum_at(TOOL_EVENT_PATH, "policy_decision")
    br = _enum_at(BREACH_RECORD_PATH, "policy_decision")
    if sorted(v.upper() for v in c2) != sorted(v.upper() for v in br):
        raise CorpusError(
            "E_DECISION_ENUM_DIVERGED",
            "contracts/tool_event.schema.json declares %s and "
            "contracts/breach_record.schema.json declares %s. Case-folded these "
            "were the same enum in two spellings, which this reader reconciles. "
            "They are now DIFFERENT SETS, and reconciling them would admit two "
            "vocabularies under one name." % (sorted(c2), sorted(br)))

    decisions = {}
    for value in c2:
        decisions[value] = value
    for value in br:
        decisions[value] = value.upper()

    statuses = {}
    for value in _enum_at(BREACH_RECORD_PATH, "status"):
        statuses[value] = value
    return decisions, statuses


def canonical_decision(value, *, where):
    decisions, _ = trace_vocabulary()
    if value in decisions:
        return decisions[value]
    raise CorpusError(
        "E_DECISION_VOCABULARY",
        "%s carries policy_decision %r. The declared spellings are %s - "
        "tool_event.schema.json upper, breach_record.schema.json lower, both "
        "frozen. REFUSED rather than skipped: the previous reader matched one "
        "spelling and silently stopped counting the event, so every episode "
        "aggregate read low and an `episode_sum` rule stopped firing on the "
        "calls it exists to catch. A wrong value must raise, because an "
        "under-counted aggregate looks exactly like a well-behaved episode."
        % (where, value, sorted(decisions)))


def canonical_status(value, *, where):
    _, statuses = trace_vocabulary()
    if value in statuses:
        return statuses[value]
    raise CorpusError(
        "E_STATUS_VOCABULARY",
        "%s carries status %r; breach_record.schema.json declares %s. Refused "
        "for the same reason as policy_decision: an unrecognised status drops "
        "the event out of the episode prefix without saying so."
        % (where, value, sorted(statuses)))


__all__ = [
    "CAPABILITY_CLASSES", "TRAINING_FAMILIES", "SEALED_FAMILY",
    "TRAINING_PER_FAMILY", "TRAINING_TOTAL", "SEALED_TARGET", "SEALED_FLOOR",
    "BENIGN_TOTAL", "NEAR_MISS_FLOOR", "KNOWN_BAD_TOTAL", "SEALED_CLASSES",
    "KINDS", "NO_APPROVER", "DEAD_APPROVER_SPELLINGS",
    "load_part_a", "tool_index", "structured_arg_paths", "fault_reason_codes",
    "approval_tiers", "trace_vocabulary", "canonical_decision", "canonical_status",
]
