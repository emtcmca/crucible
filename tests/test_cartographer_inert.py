"""test_cartographer_inert.py - INERT, the positive assertion of the empty set.

Plain English first. The Cartographer prompt offered six capability classes and
`UNCLASSIFIED`. A human reading a read-only lookup reaches a third answer -
*"this tool has no capability worth policing"* - and the model had no vocabulary
for it, so it said `UNCLASSIFIED` on four of twelve tools in the live run of
2026-08-22 (`docs/proof/cartographer-live-run-2026-08-22.json`). That sheet named
the gap itself, in "Five things the run showed", §5.

Eric's ruling, 2026-08-23: `INERT` is added as a positive assertion of the
**empty capability set**.

THE THREE THINGS THIS SUITE EXISTS TO PIN, BECAUSE EACH IS EASY TO GET WRONG.

**1. `INERT` IS NOT A SEVENTH CAPABILITY CLASS.** It is a sentinel in the
proposal vocabulary, exactly as `UNCLASSIFIED` is, and it RESOLVES to `()` on the
way into a manifest. `crucible/manifest/load.py` still refuses `INERT` as a
declared class, and the DSL validator still refuses a seventh class in a
selector. Both are pinned below, because "add INERT" is one careless edit away
from meaning "add a class".

**2. `INERT` DOES NOT REDUCE RISK.** `capability_set()` returns `frozenset()` for
an inert tool and `cap_selector` matches by MEMBERSHIP, so no rule binds to it -
which is the same practical outcome as `UNCLASSIFIED`, whose selector does not
even parse (`E_UNCLASSIFIED_SELECTOR`). Both are equally unpoliceable by policy.
What `INERT` buys is epistemic: it separates *"a human looked and ratified this
as inert"* from *"nobody looked."* A test asserts the no-rule-binds property so
that nobody later reads `INERT` as a safety control.

**3. `INERT` REQUIRES A CITATION AND `UNCLASSIFIED` DOES NOT.** This is the
decision most worth arguing with, so the reasoning is written where the test can
be read next to it. `UNCLASSIFIED` means "I cannot determine", and the absence of
evidence IS that claim - there is nothing to cite. `INERT` means "I looked, and
it declares nothing in any of the six", which is a POSITIVE assertion about the
tool, and `prepass.py`'s doctrine binds positive assertions to citable evidence:
*"a classification with no citable evidence is a guess wearing a confidence
number."*

The second reason is the one that decides it. If `INERT` could be asserted with
nothing attached, it would be strictly CHEAPER to emit than `UNCLASSIFIED` and a
model taking the shortest path would drift onto it - collapsing the very
distinction this change exists to create, in the opposite direction. Requiring a
citation makes `INERT` the more expensive answer, which is correct, because it is
the stronger claim.

NO TEST HERE MAKES A MODEL CALL.
"""

import json

import pytest

from crucible.cartographer.extract import load_frozen_target
from crucible.cartographer.gemma import (
    INERT,
    ProposalRejected,
    build_prompt,
    validate_proposal_set,
)
from crucible.cartographer.prepass import CAPABILITY_CLASSES, UNCLASSIFIED
from crucible.cartographer.ratify import (
    RatificationError,
    build_ratification,
    to_manifest_entries,
)
from crucible.manifest.load import ManifestError, capability_set


@pytest.fixture(scope="module")
def specs():
    return load_frozen_target("adk_customer_service")["tools"]


def _proposal(name, classes, evidence, confidence=0.6):
    return {
        "tool_name": name,
        "proposed_classes": list(classes),
        "model_self_reported_confidence": confidence,
        "evidence": list(evidence),
    }


def _doc_cite(cls, span, why="because"):
    return {"capability_class": cls, "cites": {"kind": "docstring", "value": span},
            "citation": why}


def _first_docstring_span(spec):
    """A span guaranteed verbatim in that tool's own docstring."""
    return spec["docstring"].strip().splitlines()[0]


# --------------------------------------------------------------------------
# 1. INERT is a sentinel, not a seventh class.
# --------------------------------------------------------------------------

def test_inert_is_not_a_seventh_capability_class():
    """The six are frozen by CONVENTIONS 2.2. `INERT` is vocabulary for a
    PROPOSAL, and adding it to the class tuple would be a different and much
    larger change than the one Eric ruled on."""
    assert INERT == "INERT"
    assert INERT not in CAPABILITY_CLASSES
    assert len(CAPABILITY_CLASSES) == 6


def test_a_manifest_still_refuses_inert_as_a_declared_class(tmp_path):
    """`INERT` must never survive into `capability_classes` as a string. It is
    resolved to the empty set before a manifest entry exists; a manifest that
    literally declares it is the seventh-class defect and is refused."""
    from crucible.manifest.load import load_part_a
    doc = {"tools": [{"tool_handle": "t", "capability_classes": ["INERT"]}]}
    p = tmp_path / "m.json"
    p.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    with pytest.raises(ManifestError) as exc:
        load_part_a(p)
    assert exc.value.code == "E_UNKNOWN_CAPABILITY_CLASS"


# --------------------------------------------------------------------------
# 2. INERT resolves to the empty set, and the empty set binds no rule.
# --------------------------------------------------------------------------

def test_inert_resolves_to_the_empty_capability_set(specs):
    """End to end: a validated INERT proposal, accepted by a named human,
    produces a manifest entry whose `capability_classes` is EMPTY - not
    `("INERT",)`, and not absent."""
    spec = specs[0]
    span = _first_docstring_span(spec)
    proposals = [_proposal(spec["tool_name"], [INERT], [_doc_cite(INERT, span)])]
    clean = validate_proposal_set(proposals, [spec])
    assert clean[0]["proposed_classes"] == (INERT,)

    pset = {"proposals": clean, "model_id": "stub/none"}
    rat = build_ratification(
        ratified_by="Eric Tetzlaff", ratified_on="2026-08-23",
        proposals=clean,
        decisions={spec["tool_name"]: {"decision": "accept", "reason": "ok"}})
    entries = to_manifest_entries(pset, rat)
    assert len(entries) == 1
    assert entries[0]["capability_classes"] == ()


def test_an_inert_tool_binds_no_rule_so_inert_reduces_no_risk():
    """The property that stops `INERT` being narrated as a safety control.

    `cap_selector` matches by MEMBERSHIP in the capability set. An empty set has
    no members, so no `cap:` rule can bind to an inert tool - the SAME practical
    exposure as `UNCLASSIFIED`, whose selector does not even parse. `INERT` buys
    a record that a human looked. It buys no enforcement."""
    manifest = {"tools": [
        {"tool_handle": "inert_tool", "capability_classes": []},
        {"tool_handle": "money_tool", "capability_classes": ["CAP_MOVES_MONEY"]},
    ]}
    assert capability_set(manifest, "inert_tool") == frozenset()
    for cls in CAPABILITY_CLASSES:
        assert cls not in capability_set(manifest, "inert_tool")
    assert "CAP_MOVES_MONEY" in capability_set(manifest, "money_tool")


# --------------------------------------------------------------------------
# 3. The citation rule: INERT must cite, UNCLASSIFIED must not have to.
# --------------------------------------------------------------------------

def test_inert_without_evidence_is_refused(specs):
    """A positive assertion with no citation is the guess-wearing-a-confidence-
    number that the whole evidence contract exists to refuse."""
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], [INERT], [])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_CLASS_WITHOUT_EVIDENCE"
    assert exc.value.tool_name == spec["tool_name"]


def test_unclassified_without_evidence_is_still_accepted(specs):
    """The regression that keeps the two sentinels distinct. "I cannot
    determine" has nothing to cite, and requiring a citation for it would
    destroy the signal this change is meant to preserve."""
    spec = specs[0]
    ok = [_proposal(spec["tool_name"], [UNCLASSIFIED], [])]
    clean = validate_proposal_set(ok, [spec])
    assert clean[0]["proposed_classes"] == (UNCLASSIFIED,)
    assert clean[0]["evidence"] == ()


def test_an_inert_citation_must_still_be_grounded(specs):
    """`INERT` gets no relief from the grounding check either. A fabricated span
    is a parse failure here exactly as it is for the six."""
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], [INERT],
                     [_doc_cite(INERT, "this text is nowhere in the docstring")])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_CITATION_NOT_GROUNDED"


# --------------------------------------------------------------------------
# 4. INERT stands alone, and an empty list is still not how you say it.
# --------------------------------------------------------------------------

def test_inert_mixed_with_a_real_class_is_refused(specs):
    """"It has no capabilities, and also it moves money" is a contradiction, and
    it gets its own code so a test can prove WHICH rule fired."""
    spec = specs[0]
    span = _first_docstring_span(spec)
    bad = [_proposal(spec["tool_name"], [INERT, "CAP_MOVES_MONEY"],
                     [_doc_cite(INERT, span), _doc_cite("CAP_MOVES_MONEY", span)])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_INERT_MIXED"


def test_inert_mixed_with_unclassified_is_refused(specs):
    """The two sentinels are mutually exclusive: "I know it is nothing" and "I do
    not know" cannot both be the answer."""
    spec = specs[0]
    span = _first_docstring_span(spec)
    bad = [_proposal(spec["tool_name"], [INERT, UNCLASSIFIED], [_doc_cite(INERT, span)])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_INERT_MIXED"


def test_an_empty_class_list_is_still_refused(specs):
    """Unchanged, and deliberately so. The empty set is now SAYABLE, but only by
    asserting `INERT` and citing something. An empty list remains a silence that
    would be read as a claim."""
    spec = specs[0]
    bad = [_proposal(spec["tool_name"], [], [])]
    with pytest.raises(ProposalRejected) as exc:
        validate_proposal_set(bad, [spec])
    assert exc.value.code == "E_NO_CLASSES"


# --------------------------------------------------------------------------
# 5. The prompt must offer both, and say how they differ.
# --------------------------------------------------------------------------

def test_the_prompt_offers_inert_and_keeps_unclassified(specs):
    """If the model can only say `INERT`, the "I cannot determine" signal is
    destroyed and one collapsed distinction has been traded for another."""
    prompt = build_prompt(specs)
    assert "INERT" in prompt
    assert "UNCLASSIFIED" in prompt


def test_the_prompt_still_offers_exactly_six_capability_classes(specs):
    """The class guide is not where `INERT` goes. A model shown seven entries in
    a list headed "the six capability classes" will emit `INERT` as a class."""
    prompt = build_prompt(specs)
    for cls in CAPABILITY_CLASSES:
        assert cls in prompt
    marker = "Two further answers are available"
    assert marker in prompt, "the class guide and the sentinels must stay separated"
    guide_head = prompt.split(marker)[0]
    assert "INERT" not in guide_head
    assert "six capability classes" in guide_head


# --------------------------------------------------------------------------
# 6. A human may amend TO inert, which is the whole point of the vocabulary.
# --------------------------------------------------------------------------

def test_a_human_may_amend_a_tool_to_inert(specs):
    """The ratifier reading a read-only lookup needs to be able to record the
    empty set. Before this change `amend` could only reach the six or
    `UNCLASSIFIED`, so the reviewer had the same missing word the model did."""
    spec = specs[0]
    span = _first_docstring_span(spec)
    proposals = validate_proposal_set(
        [_proposal(spec["tool_name"], ["CAP_MOVES_MONEY"],
                   [_doc_cite("CAP_MOVES_MONEY", span)])], [spec])
    rat = build_ratification(
        ratified_by="Eric Tetzlaff", ratified_on="2026-08-23",
        proposals=proposals,
        decisions={spec["tool_name"]: {"decision": "amend", "classes": [INERT],
                                       "reason": "reads nothing, writes nothing"}})
    entries = to_manifest_entries({"proposals": proposals, "model_id": "s"}, rat)
    assert entries[0]["capability_classes"] == ()
    assert entries[0]["classified_by"] == "human"


def test_amending_to_a_class_outside_the_vocabulary_is_still_refused(specs):
    """The amend path did not become a hole. `INERT` was added to the vocabulary;
    nothing else was."""
    spec = specs[0]
    span = _first_docstring_span(spec)
    proposals = validate_proposal_set(
        [_proposal(spec["tool_name"], ["CAP_MOVES_MONEY"],
                   [_doc_cite("CAP_MOVES_MONEY", span)])], [spec])
    with pytest.raises(RatificationError) as exc:
        build_ratification(
            ratified_by="Eric Tetzlaff", ratified_on="2026-08-23",
            proposals=proposals,
            decisions={spec["tool_name"]: {"decision": "amend",
                                           "classes": ["CAP_INVENTED"],
                                           "reason": "no"}})
    assert exc.value.code == "E_UNKNOWN_CLASS"
