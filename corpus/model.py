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

# -- CONVENTIONS.md is the home of these, so they are typed here. --------------
# Section 4, frozen numbers. A lane that wants a different value stops and reports.
TRAINING_FAMILIES = ("F1", "F2", "F3", "F5", "F6", "F7")
SEALED_FAMILY = "F4"
TRAINING_PER_FAMILY = 8
TRAINING_TOTAL = 48
SEALED_TARGET = 24
SEALED_FLOOR = 18          # ABSOLUTE. Arithmetic, not preference - see sizing.py.
BENIGN_TOTAL = 24
NEAR_MISS_FLOOR = 12
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


__all__ = [
    "CAPABILITY_CLASSES", "TRAINING_FAMILIES", "SEALED_FAMILY",
    "TRAINING_PER_FAMILY", "TRAINING_TOTAL", "SEALED_TARGET", "SEALED_FLOOR",
    "BENIGN_TOTAL", "NEAR_MISS_FLOOR", "KNOWN_BAD_TOTAL", "SEALED_CLASSES",
    "KINDS", "NO_APPROVER", "DEAD_APPROVER_SPELLINGS",
    "load_part_a", "tool_index", "structured_arg_paths", "fault_reason_codes",
    "approval_tiers",
]
