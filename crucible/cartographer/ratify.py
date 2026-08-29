"""ratify.py - the human gate between a Cartographer proposal and a manifest.

Plain English first. `architecture-spec.md:138` says the Cartographer's output is
"never final" and that "it cannot approve its own classification".
`docs/decisions-pending/gemma-scope.md` section 6 says the same thing from the
other direction: *"The Cartographer proposing straight into the manifest would
break the one property that makes it defensible."* This module is that property,
written as code instead of as a paragraph.

There is exactly one route from a proposal to a manifest entry, it is
`to_manifest_entries()`, and it will not produce an entry unless a named human
has recorded a decision for that specific tool inside a record whose digest
matches the proposal set being ratified.

WHY THE DIGEST IS THE INTERESTING PART.

A ratification that names a person and a date, but not *what they saw*, is
signable in advance and re-usable afterwards. `proposal_set_digest()` hashes the
proposals themselves - tool names, proposed classes, evidence, in canonical form.
Change one proposed class after signing and the digest moves, the ratification
stops matching, and `to_manifest_entries` raises. The person is bound to the
bytes they read, which is the same reason `sealed-family-commitment.json` exists
next to `sealed-family-ratification.md`.

The prompt and the raw response are deliberately NOT in the digest. Re-running
the model would change them without changing a single classification, and a
ratification that expires because a whitespace shifted is a ratification people
route around.

THREE DECISIONS, NOT TWO.

`accept`, `amend`, `reject`. `amend` carries the human's own class set and is the
outcome that matters most: it records that a person changed the answer, and the
manifest entry it produces is stamped `classified_by: human`, not
`cartographer`. A gate that can only rubber-stamp or refuse hides the case where
the reviewer did the real work.
"""

from ..canon.hashing import hash_full
from .gemma import INERT
from .prepass import CAPABILITY_CLASSES, UNCLASSIFIED

VALID_CLASSES = frozenset(CAPABILITY_CLASSES)
DECISIONS = ("accept", "amend", "reject")

# Names that are components of this system, not people. A ratification signed by
# one of these is the self-approval the architecture forbids.
_NOT_A_HUMAN = frozenset({
    "cartographer", "capability_cartographer", "gemma", "armorer", "coroner",
    "warden", "gate", "red_team", "tripwire", "crucible", "model", "ai",
})


class RatificationError(RuntimeError):
    """Raised when the human gate has not actually been passed."""

    def __init__(self, code, message):
        super().__init__("%s: %s" % (code, message))
        self.code = code


def proposal_set_digest(proposals) -> str:
    """SHA-256 over the classifications alone, in canonical form.

    Covers tool name, proposed classes and evidence. Excludes the prompt, the raw
    response, the model id and the self-reported confidence - see the module
    docstring on why a digest that moves for cosmetic reasons is a digest that
    gets bypassed.
    """
    body = [
        {
            "tool_name": p["tool_name"],
            "proposed_classes": list(p["proposed_classes"]),
            "evidence": [
                {
                    "capability_class": e["capability_class"],
                    "cites": dict(e["cites"]),
                    "citation": e["citation"],
                }
                for e in p["evidence"]
            ],
        }
        for p in proposals
    ]
    return hash_full(body)


def decisions_digest(decisions) -> str:
    """SHA-256 over what the human DECIDED, in canonical form.

    THE COMPANION TO `proposal_set_digest`, AND THE HALF THAT WAS MISSING.

    The proposal digest binds what the reviewer SAW. Until 2026-08-28 nothing
    bound what the reviewer DECIDED, so an amendment class edited after signing
    changed the manifest `to_manifest_entries` emits while the proposal digest
    stayed valid. The record was tamper-evident on its inputs and tamper-blind
    on its output - a check that passes while measuring nothing, which is this
    project's signature defect and this was its eighth instance. Found by a
    third-party adversarial review.

    Covers the VERDICT and the AMENDMENT CLASSES: the only two fields that
    decide what ships. Excludes the free-text `reason`, for the same stated
    reason the proposal digest excludes the prompt - a record that expires
    because a typo was fixed is a record people route around. That exclusion is
    safe because `reason` never reaches the manifest, so rewriting one without
    touching a class changes nothing that ships.

    Sorted by tool name so two reviewers who record identical rulings in a
    different order agree. Classes are hashed IN THE GIVEN ORDER, because the
    emitted `capability_classes` tuple carries that order.

    NOT A SIGNATURE. Anyone who can edit the record can recompute both digests.
    The protection is that the signed sheet records them in a COMMITTED
    document, so divergence is detectable against git - the same arrangement
    `sealed-family-commitment.json` has.
    """
    body = [
        {
            "tool_name": name,
            "decision": (d or {}).get("decision"),
            "classes": list((d or {}).get("classes") or []),
        }
        for name, d in sorted((decisions or {}).items())
    ]
    return hash_full(body)


def build_ratification(*, ratified_by, ratified_on, proposals, decisions, notes=None):
    """Assemble a ratification record for one proposal set.

    Args:
        ratified_by: the human's name. A component name is refused.
        ratified_on: ISO date the review happened.
        proposals: the proposal tuple from `Cartographer.propose()`.
        decisions: {tool_name: {"decision": "accept"|"amend"|"reject",
                                "classes": [...],   # required for amend
                                "reason": str}}
        notes: free text for the accompanying proof document.

    Raises `RatificationError` if a decision is missing, unknown, or amends to a
    class outside the six.
    """
    who = (ratified_by or "").strip()
    if not who:
        raise RatificationError("E_NO_RATIFIER", "a ratification needs a named human")
    if who.lower().replace(" ", "_") in _NOT_A_HUMAN:
        raise RatificationError(
            "E_SELF_APPROVAL",
            "%r is a component of this system, not a person. "
            "architecture-spec.md:138 - it cannot approve its own classification" % who)

    proposed_names = [p["tool_name"] for p in proposals]
    missing = [n for n in proposed_names if n not in (decisions or {})]
    if missing:
        raise RatificationError(
            "E_UNREVIEWED_TOOL",
            "no decision recorded for: %s. Every proposed tool is reviewed or "
            "the ratification does not cover the set" % ", ".join(sorted(missing)))
    extra = [n for n in (decisions or {}) if n not in proposed_names]
    if extra:
        raise RatificationError(
            "E_DECISION_FOR_UNPROPOSED_TOOL",
            "decisions recorded for tools that were never proposed: %s"
            % ", ".join(sorted(extra)))

    clean = {}
    for name, d in decisions.items():
        verdict = (d or {}).get("decision")
        if verdict not in DECISIONS:
            raise RatificationError(
                "E_UNKNOWN_DECISION",
                "%r for %r; expected one of %s" % (verdict, name, ", ".join(DECISIONS)))
        classes = list((d or {}).get("classes") or [])
        if verdict == "amend":
            if not classes:
                raise RatificationError(
                    "E_AMEND_WITHOUT_CLASSES",
                    "%r is amended but no replacement class set was given" % name)
            for c in classes:
                # INERT is accepted here for the same reason it was added to the
                # prompt: before it existed, a reviewer looking at a read-only
                # lookup had the same missing word the model did, and had to
                # write UNCLASSIFIED over an answer he was certain of.
                if c not in (UNCLASSIFIED, INERT) and c not in VALID_CLASSES:
                    raise RatificationError(
                        "E_UNKNOWN_CLASS", "%r amended to %r, not one of the six" % (name, c))
                if c == INERT and len(classes) > 1:
                    raise RatificationError(
                        "E_INERT_MIXED",
                        "%r amended to INERT alongside %s. INERT is the EMPTY "
                        "capability set and cannot be one member of a larger one"
                        % (name, ", ".join(repr(x) for x in classes if x != INERT)))
        clean[name] = {
            "decision": verdict,
            "classes": classes,
            "reason": str((d or {}).get("reason") or "").strip(),
        }

    return {
        "ratified_by": who,
        "ratified_on": ratified_on,
        "proposal_set_digest": proposal_set_digest(proposals),
        # Taken over the NORMALIZED decisions, so the value a reviewer can
        # recompute by hand from the signed sheet is the value checked here.
        "decisions_digest": decisions_digest(clean),
        "decisions": clean,
        "notes": notes or "",
    }


def _resolve_classes(classes):
    """Turn a ratified proposal vocabulary into a manifest capability set.

    THE ONLY PLACE THE TWO VOCABULARIES MEET, and it does exactly one thing:
    `("INERT",)` becomes `()`.

    That mapping is the whole of Eric's 2026-08-23 ruling. `INERT` is not a
    seventh capability class - `manifest/load.py` still refuses the literal
    string, and the DSL validator still refuses a seventh class in a selector.
    It is a proposal-vocabulary token that RESOLVES to the empty capability set,
    which `manifest/load.py`'s own docstring already sanctions: *"Empty is 'we
    know it has no capabilities', which is a claim."*

    WHAT THIS DOES NOT BUY, stated here because the resolution is where somebody
    would go looking for a safety property and not find one. `cap_selector`
    matches by MEMBERSHIP, so an empty set binds no rule - the same practical
    exposure as `UNCLASSIFIED`, whose selector does not even parse
    (`E_UNCLASSIFIED_SELECTOR`). `INERT` does not make a tool safer. It records
    that a human looked and ruled, where `UNCLASSIFIED` records that nobody
    could. For a fleet-cataloging problem that distinction is the product; as an
    enforcement claim it would be false.

    `UNCLASSIFIED` is deliberately NOT resolved here. It passes through and
    `manifest/load.py` refuses it by name, which is fail-closed and loud. Mapping
    it to anything would be inventing a decision the reviewer did not make.
    """
    classes = tuple(classes)
    if classes == (INERT,):
        return ()
    return classes


def to_manifest_entries(proposal_set, ratification):
    """The one route from proposals to manifest entries.

    Returns a list of `{tool_name, capability_classes, classified_by,
    human_confirmed, evidence, source_model}` - rejected tools omitted.

    Raises `RatificationError` if the record does not bind to this exact
    proposal set, or if any proposed tool is unreviewed.
    """
    proposals = list(proposal_set.get("proposals") or ())
    if not proposals:
        raise RatificationError(
            "E_NOTHING_TO_RATIFY", "the proposal set is empty")
    if not isinstance(ratification, dict):
        raise RatificationError(
            "E_NOT_RATIFIED",
            "no ratification record. A Cartographer proposal does not enter a "
            "manifest on its own authority (architecture-spec.md:138)")

    expected = proposal_set_digest(proposals)
    got = ratification.get("proposal_set_digest")
    if got != expected:
        raise RatificationError(
            "E_DIGEST_MISMATCH",
            "the ratification was signed over a different proposal set "
            "(signed %s, have %s). The classifications changed after review."
            % (got, expected))

    decisions = ratification.get("decisions") or {}

    # The proposal digest above proves the reviewer saw these proposals. It says
    # NOTHING about what they ruled, and the ruling is what this function emits.
    # Fail closed on a missing digest rather than treating absence as consent:
    # an optional check is one an attacker disables by deleting a field, and
    # nothing has ever been ratified, so there is no legacy record to honour.
    signed_decisions = ratification.get("decisions_digest")
    if not signed_decisions:
        raise RatificationError(
            "E_DECISIONS_DIGEST_MISSING",
            "the ratification carries no decisions_digest, so nothing binds the "
            "verdicts to the person who recorded them. Re-sign with "
            "build_ratification()")
    if signed_decisions != decisions_digest(decisions):
        raise RatificationError(
            "E_DECISIONS_DIGEST_MISMATCH",
            "the decisions changed after they were signed. The proposal set is "
            "unmoved, so this is an edit to a verdict or an amendment class - "
            "the fields that decide what enters the manifest")

    entries = []
    for p in proposals:
        name = p["tool_name"]
        d = decisions.get(name)
        if not d:
            raise RatificationError(
                "E_UNREVIEWED_TOOL", "%r has no recorded decision" % name)
        verdict = d.get("decision")
        if verdict == "reject":
            continue
        if verdict == "amend":
            classes = _resolve_classes(d.get("classes") or ())
            classified_by = "human"
        elif verdict == "accept":
            classes = _resolve_classes(p["proposed_classes"])
            classified_by = "cartographer"
        else:
            raise RatificationError(
                "E_UNKNOWN_DECISION", "%r for %r" % (verdict, name))
        entries.append({
            "tool_name": name,
            "capability_classes": classes,
            # `cartographer` on an accepted proposal, `human` on an amended
            # one. Both carry human_confirmed=True; the difference records who
            # actually produced the answer that shipped.
            "classified_by": classified_by,
            "human_confirmed": True,
            "ratified_by": ratification.get("ratified_by"),
            "ratified_on": ratification.get("ratified_on"),
            "evidence": tuple(p["evidence"]),
            "source_model": proposal_set.get("model_id"),
        })
    return entries
