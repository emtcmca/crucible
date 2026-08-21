"""load.py - loading the capability manifest and deriving its hash.

Ruling 20 SPLIT the manifest into two artifacts with two freeze dates:

    PART A  capability_manifest.json   freezes D3, WITH THE TARGET
    PART B  derived_schema.json        freezes D5, WITH THE CORPUS,
                                       gated on the label-blindness check

The test that decides which part a field belongs to: **does the TARGET need it
to run, or only the EVALUATOR?** A tool's capability classes are Part A - the
plugin cannot make a decision without them. A `derived.*` field's declaration is
Part B - the target never sees it.

They hash SEPARATELY (`manifest_hash` and `derived_schema_hash`) because they
freeze on different days. One hash over both would mean the D5 corpus freeze
retroactively changed the identity of the thing the D3 target was frozen
against, and every D3-D5 result would refer to a manifest hash that no longer
exists.

TWO THINGS THAT ARE NOT THE SAME, AND MUST NOT SHARE AN ENCODING
-----------------------------------------------------------------
A tool ABSENT from the manifest and a tool present with an EMPTY capability set
mean different things. Absent is "nobody classified this", which is an error.
Empty is "we know it has no capabilities", which is a claim. `UNCLASSIFIED` is a
third thing again: "we do not know what this does", and it is why
`fail_closed_default` tools carry every class rather than none.

Defaulting an absent tool to the empty set is the failure this module exists to
prevent: a tool the plugin cannot classify becomes a tool the policy cannot
constrain, and the run reports a clean sheet on a surface it never inspected.
"""

import hashlib
import json
import pathlib

from ..canon import CanonicalizationError, canonicalize_bytes

CAPABILITY_CLASSES = (
    "CAP_MOVES_MONEY",
    "CAP_MUTATES_DURABLE_STATE",
    "CAP_READS_PII",
    "CAP_EXTERNAL_COMMS",
    "CAP_ESCALATES_PRIVILEGE",
    "CAP_INVOKES_AGENT",
)
UNCLASSIFIED = "UNCLASSIFIED"


class ManifestError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


def load_part_a(path):
    """Load capability manifest Part A and return (manifest, manifest_hash)."""
    raw = pathlib.Path(path).read_bytes()
    return _load(raw, part="A")


def load_part_b(path):
    """Load derived_schema Part B and return (schema, derived_schema_hash)."""
    raw = pathlib.Path(path).read_bytes()
    return _load(raw, part="B")


# Fields carried in the document but EXCLUDED from its hashed payload.
#
# THIS IS NOT A CARVE-OUT INVENTED HERE. `canonicalization.md` restriction 4,
# which is frozen: "Money is integer minor units plus an ISO-4217 currency
# string. Confidences and rates live OUTSIDE the hashed payload." And
# `derived_schema.schema.json` says it again on the field itself:
# "Reported outside the hashed payload (floats are forbidden inside one)."
#
# Both statements are true and nothing implemented either of them, so Part B
# could not be hashed at all -- and `derived_schema_hash` is one of the five
# hash-locks. The rule existed; the mechanism did not.
#
# The list is ENUMERATED and each entry names why. It must never become "strip
# whatever fails to canonicalize" -- that is weakening a gate, which
# CONVENTIONS section 8 rule 3 makes a stop condition rather than a repair. Any
# float NOT on this list is still refused, and there is a test for exactly that.
HASH_EXCLUSIONS = {
    "B": [
        (("blindness_check", "max_predictive_accuracy"),
         "a rate. canonicalization.md restriction 4 puts confidences and rates "
         "outside the hashed payload, and the schema's own $comment agrees. Two "
         "runs whose fields are identical and whose measured accuracy differs "
         "are the SAME SCHEMA, so including it would make the identity of Part B "
         "depend on a measurement rather than on a definition."),
    ],
}


def _strip_excluded(doc, part):
    """Remove the enumerated exclusions and report which ones were present."""
    removed = []
    for path, _why in HASH_EXCLUSIONS.get(part, []):
        cur = doc
        for key in path[:-1]:
            cur = cur.get(key) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, dict) and path[-1] in cur:
            cur.pop(path[-1])
            removed.append(".".join(path))
    return removed


def _load(raw, part):
    # Parse first, so an excluded field can be removed before canonicalization
    # sees it. json.loads here is deliberately NOT the canonicalizer: this pass
    # is only to locate the exclusions, and everything that survives it still
    # goes through the real canonicalizer with every restriction enforced.
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ManifestError("E_MALFORMED", "part %s is not JSON: %s" % (part, e))

    excluded = _strip_excluded(doc, part)
    payload = json.dumps(doc, ensure_ascii=False).encode("utf-8")

    try:
        canonical = canonicalize_bytes(payload)
    except CanonicalizationError as e:
        raise ManifestError(
            "E_NOT_CANONICALIZABLE",
            "part %s does not canonicalize (%s). It is hash-locked, so a payload "
            "that cannot be canonicalized cannot be frozen.%s"
            % (part, e,
               " Excluded before hashing: %s -- so this is a SECOND offending "
               "value, not the known one." % ", ".join(excluded)
               if excluded else "")) from None

    digest = hashlib.sha256(canonical).hexdigest()
    if part == "A":
        _validate_part_a(doc)
    return doc, digest[:16]


def _validate_part_a(doc):
    tools = doc.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ManifestError("E_NO_TOOLS", "Part A declares no tools")

    handles = set()
    for t in tools:
        h = t.get("tool_handle")
        if not h:
            raise ManifestError("E_NO_HANDLE", "a tool entry has no tool_handle")
        if h in handles:
            raise ManifestError("E_DUPLICATE_HANDLE",
                                "%s appears twice; the second silently wins" % h)
        handles.add(h)

        classes = t.get("capability_classes")
        if classes is None:
            raise ManifestError(
                "E_NO_CAPABILITY_CLASSES",
                "%s has no capability_classes. Absent is not the empty set: "
                "absent means nobody classified it, empty means we know it has "
                "none. Defaulting one to the other makes a tool the policy "
                "cannot constrain look like a tool that needs no constraint." % h)
        bad = [c for c in classes if c not in CAPABILITY_CLASSES]
        if bad:
            raise ManifestError(
                "E_UNKNOWN_CAPABILITY_CLASS",
                "%s declares %s. There are exactly six classes and "
                "%s is not one of them%s"
                % (h, bad, bad[0],
                   " -- UNCLASSIFIED is a sentinel for an unclassified CALL, "
                   "never a class a tool may declare" if UNCLASSIFIED in bad else ""))

        if t.get("fail_closed"):
            missing = set(CAPABILITY_CLASSES) - set(classes)
            if missing:
                raise ManifestError(
                    "E_FAIL_CLOSED_NOT_MAXIMAL",
                    "%s is fail_closed but omits %s. Fail-closed means 'we do "
                    "not know what this does', and the only safe encoding of "
                    "that is EVERY class -- omitting one asserts knowledge the "
                    "classifier explicitly does not have"
                    % (h, sorted(missing)))


def assert_manifest_covers(manifest, tool_handles):
    """Every tool the agent can actually call must appear in Part A.

    L2's exit criteria require the manifest be COMPLETE. This is the check that
    makes that testable rather than asserted: a tool present in the agent and
    absent from the manifest is an error, never an empty capability set.
    """
    declared = {t["tool_handle"] for t in manifest.get("tools", [])}
    missing = sorted(set(tool_handles) - declared)
    if missing:
        raise ManifestError(
            "E_MANIFEST_INCOMPLETE",
            "the agent can call %s, and Part A does not declare %s. An "
            "undeclared tool is unconstrainable by any rule, and the run would "
            "report a clean sheet on a surface it never inspected."
            % (len(tool_handles), missing))
    extra = sorted(declared - set(tool_handles))
    return {"declared": len(declared), "callable": len(tool_handles),
            "declared_but_not_callable": extra}


def capability_set(manifest, tool_handle):
    """The call's capability set, or the UNCLASSIFIED sentinel.

    Ruling 22: `cap_selector` matches by MEMBERSHIP in this set. Returning the
    empty set for an unknown tool would make every rule miss it silently, so an
    unknown tool returns the sentinel and the caller must decide -- which is the
    whole reason the sentinel is distinct from the empty set.
    """
    for t in manifest.get("tools", []):
        if t["tool_handle"] == tool_handle:
            return frozenset(t["capability_classes"])
    return UNCLASSIFIED
