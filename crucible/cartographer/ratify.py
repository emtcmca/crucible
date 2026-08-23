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
                if c != UNCLASSIFIED and c not in VALID_CLASSES:
                    raise RatificationError(
                        "E_UNKNOWN_CLASS", "%r amended to %r, not one of the six" % (name, c))
        clean[name] = {
            "decision": verdict,
            "classes": classes,
            "reason": str((d or {}).get("reason") or "").strip(),
        }

    return {
        "ratified_by": who,
        "ratified_on": ratified_on,
        "proposal_set_digest": proposal_set_digest(proposals),
        "decisions": clean,
        "notes": notes or "",
    }


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
            classes = tuple(d.get("classes") or ())
            classified_by = "human"
        elif verdict == "accept":
            classes = tuple(p["proposed_classes"])
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
