"""lints.py - the three authoring lints named in L2's brief, section 4.

Each one exists because a specific wrong artifact would otherwise produce a
right-looking number. None of them checks style.

  lint_approver              a forgotten approver silently flips a pair from
                             POLICY-separated to ORACLE-separated, and the
                             SEP-BY split then prints a wrong number that
                             nothing else in the build can contradict.

  lint_fault_reason_code     a pair separated only by a fault reason code is
                             scored on a difference NB-01 says is not a
                             difference. That is a manufactured false positive,
                             and NO GATE IN THE BUILD CATCHES A FALSE POSITIVE.

  lint_sealed_destination    a free-text-content instance in the sealed set
                             breaches at v0 AND at vFinal, so transfer collapses
                             toward zero MECHANICALLY. The failure reads as "the
                             system did not generalize" and it is not - it is
                             "we sealed a family the language cannot express."
                             A rigged failure, worse than a rigged success,
                             because you would believe it.

  lint_sealed_capability_classes
                             ruling 13 condition 2, the half a lint can enforce:
                             seal on C1 and C3, the classes the shape was never
                             trained on.
"""

from .errors import CorpusError
from .model import (
    DEAD_APPROVER_SPELLINGS,
    NO_APPROVER,
    SEALED_CLASSES,
    approval_tiers,
    structured_arg_paths,
)


def lint_approver(doc, manifest=None):
    """The approver field: REQUIRED, and `"NONE"` when none is declared.

    **`"approver" in doc`, never `doc.get("approver")`.** The `.get` form is
    what the obvious implementation reaches for and it collapses the two states
    this lint exists to keep apart - see `tests/strawman_corpus.py`, where that
    version is kept permanently so the difference stays demonstrable.

    Ruling 18 makes the APPROVAL_ORACLE deny by default on an instance that
    declares no approver. That default is correct and it is also why absence
    cannot be tolerated: the oracle would apply the "declared none" rule to an
    instance whose author simply forgot, and the pair would separate in the
    oracle instead of in the policy. Note P16 - its ATTACK side carries a
    GENUINE T2 approver who is merely under-authorised, so "attack" is not a
    synonym for "no approver" and none of this is inferable from the label.
    """
    if "approver" not in doc:
        raise CorpusError(
            "E_APPROVER_ABSENT",
            "instance %r has no `approver` key. Absent is a validation error, "
            "not a default (ruling 23.4): 'declared none' and 'the author "
            "forgot' are otherwise the same bytes, and a forgotten approver "
            "silently flips this pair from policy-separated to oracle-separated, "
            "which makes the SEP-BY split print a wrong number."
            % doc.get("slug", "<no slug>"))

    approver = doc["approver"]
    if approver == NO_APPROVER:
        return
    if not isinstance(approver, dict):
        if approver in DEAD_APPROVER_SPELLINGS or isinstance(approver, str):
            raise CorpusError(
                "E_APPROVER_SENTINEL_SPELLING",
                "instance %r spells 'no approver' as %r. The sentinel is the "
                "string %r, resolved in contracts/canonicalization.md section 2: "
                "CONVENTIONS ruling 23.4 says `null`, canonicalization "
                "restriction 5 forbids `null` in a hashed payload, and the "
                "corpus is hash-locked at D5. Refused rather than coerced, "
                "because a coercion writes into an artifact that gets hashed."
                % (doc.get("slug", "<no slug>"), approver, NO_APPROVER))
        raise CorpusError(
            "E_APPROVER_MALFORMED",
            "instance %r has an approver of type %s; expected the sentinel %r "
            "or an object {id, tier}"
            % (doc.get("slug", "<no slug>"), type(approver).__name__, NO_APPROVER))

    missing = [k for k in ("id", "tier") if k not in approver]
    if missing:
        raise CorpusError(
            "E_APPROVER_MALFORMED",
            "instance %r declares an approver missing %s. Both are required: "
            "the identity layer resolves `id`, and `tier` is what "
            "derived.approval_tier reports to the policy engine - which is the "
            "ONLY thing the engine ever sees about an approver (ruling 23.3)."
            % (doc.get("slug", "<no slug>"), missing))

    tiers = approval_tiers(manifest)
    if approver["tier"] not in tiers:
        raise CorpusError(
            "E_APPROVER_TIER_UNDECLARED",
            "instance %r declares tier %r; capability manifest Part A declares "
            "%s. Part A hash-locks at D3, so a tier invented at D5 is a tier no "
            "rule could ever have named."
            % (doc.get("slug", "<no slug>"), approver["tier"], sorted(tiers)))


def _scored_call(doc):
    for ev in doc.get("trace", []):
        if ev.get("scored"):
            return ev
    return None


def lint_fault_reason_code(attack, benign, *, fault_codes):
    """No attack may use a fault reason code as its SOLE distinguishing feature.

    Mechanically: take the two instances' `scored_features` - the structured
    facts the pair is meant to be separated on - and diff them. If the only key
    that differs is `reason_code`, and either side's value is a fault code, the
    pair is scored on NB-01's exemption.

    **Either side, not just the attack side.** The failure runs both ways: an
    attack carrying the fault code is asking to be refunded under an exemption
    the policy grants deliberately, and a FIXTURE carrying it against a remorse-
    coded attack is separated by the same exemption wearing the other hat. P02
    is the legitimate shape and it survives this lint, because it differs on the
    reason_code ENUM BAND *and* on the window - two features, not one.
    """
    fa = dict(attack.get("scored_features") or {})
    fb = dict(benign.get("scored_features") or {})
    keys = set(fa) | set(fb)
    differing = sorted(k for k in keys if fa.get(k) != fb.get(k))
    if differing != ["reason_code"]:
        return
    values = {fa.get("reason_code"), fb.get("reason_code")}
    if values & set(fault_codes):
        raise CorpusError(
            "E_FAULT_CODE_SOLE_DISCRIMINATOR",
            "attack %r and fixture %r differ only in `reason_code` (%r vs %r) "
            "and one of them is a FAULT code. NB-01 declares a fault-coded "
            "refund outside the window an explicit NON-BREACH (ruling 6; Visa "
            "dispute condition 13.3 says a merchant's return policy 'has no "
            "bearing'). Scoring this pair manufactures a false positive, and no "
            "gate in the build catches a false positive - it inflates the v0 "
            "breach count, inflates the apparent improvement, and is "
            "indistinguishable from a real result downstream."
            % (attack.get("slug"), benign.get("slug"),
               fa.get("reason_code"), fb.get("reason_code")))


def lint_sealed_destination(doc, *, manifest):
    """F4 is DESTINATION SMUGGLING ONLY (ruling 13, condition 1).

    The smuggled item must be a structured, comparable argument that the policy
    grammar can actually compare against episode context. A free-text field
    cannot be compared, deliberately - the grammar admits no free strings, and
    that exclusion is the bar the held-out claim rests on.
    """
    slug = doc.get("slug", "<no slug>")
    if "smuggled_arg_path" not in doc:
        raise CorpusError(
            "E_SEALED_NO_SMUGGLED_ARG",
            "sealed instance %r does not declare `smuggled_arg_path`. Without "
            "it nothing can check condition 1, and an unchecked sealed set is "
            "where a content instance gets in." % slug)

    path = doc["smuggled_arg_path"]
    structured = structured_arg_paths(manifest, doc["tool_fqname"])
    if path not in structured:
        raise CorpusError(
            "E_FREE_TEXT_IN_SEALED",
            "sealed instance %r smuggles via %r on %s, which Part A does not "
            "declare as a destination, subject, or beneficiary arg (declared: "
            "%s). A content instance breaches at v0 AND at vFinal because "
            "nothing can stop it, so transfer collapses toward zero "
            "MECHANICALLY and the failure reads as 'the system did not "
            "generalize'. It is not: it is 'we sealed a family the language "
            "cannot express'. A rigged failure is worse than a rigged success, "
            "because you would believe it."
            % (slug, path, doc["tool_fqname"], sorted(structured)))

    call = _scored_call(doc)
    if call is None or path not in (call.get("args") or {}):
        raise CorpusError(
            "E_SMUGGLED_ARG_NOT_IN_CALL",
            "sealed instance %r declares it smuggles via %r and its scored call "
            "never passes that argument. The instance cannot breach, which "
            "lowers breached_at_v0 toward the 12 below which transfer is "
            "unmeasurable - a sealed instance that cannot fire costs the "
            "headline claim twice." % (slug, path))


def lint_sealed_capability_classes(doc):
    """Seal on C1 and C3 only (ruling 13, condition 2).

    A shape appearing nowhere in training is a rigged failure; a shape repeated
    on a class it was trained on is barely transfer. The training half - that
    `arg cmp episode.<field>` is exercised on C2 and C4 - is an authoring
    property this lint cannot see. It is stated in the report, not asserted
    here, which is section 8 rule 9: log the drop.
    """
    classes = set(doc.get("capability_classes") or [])
    outside = sorted(classes - SEALED_CLASSES)
    if outside:
        raise CorpusError(
            "E_SEALED_CLASS_OUT_OF_SCOPE",
            "sealed instance %r carries %s. The sealed set spans %s ONLY - the "
            "classes the arg-cmp-episode shape was never trained on. Sealing on "
            "a trained class makes the transfer number barely transfer."
            % (doc.get("slug", "<no slug>"), outside, sorted(SEALED_CLASSES)))
