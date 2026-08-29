"""The ratification record must bind the human's DECISIONS, not only the proposals.

WHY THIS FILE EXISTS.

`proposal_set_digest()` hashes what the reviewer SAW - tool names, proposed
classes, evidence. Nothing hashed what the reviewer DECIDED. So an amendment
class could be edited after signing, `to_manifest_entries()` would emit a
different manifest, and the digest check stayed green. The record was
tamper-evident on its inputs and tamper-blind on its output.

That is the eighth instance of this project's signature defect: a check that
passes while measuring nothing. The digest check could not see the field that
changes the manifest.

Found by a third-party adversarial review on 2026-08-28 and reproduced here
before the fix existed. Every test below except the controls FAILED against the
pre-fix module.

WHAT THE DIGEST COVERS, AND WHAT IT DELIBERATELY DOES NOT.

Covered: the verdict and the amendment classes - the two fields that decide what
`to_manifest_entries` emits. NOT covered: the free-text `reason`, for the same
stated reason the proposal digest excludes the prompt and the raw response - a
ratification that expires because a typo was fixed is a ratification people
route around. Excluding it is safe precisely because `reason` has no effect on
the emitted manifest: a tamperer who rewrites a reason without touching the
class has changed nothing that ships.

THE DIGEST IS NOT A SIGNATURE. Anyone who can edit the record can recompute both
digests. The protection is that the signed sheet records them in a COMMITTED
document, so later divergence is detectable against git. Same reasoning as the
sealed-family commitment.
"""

import copy

import pytest

from crucible.cartographer.ratify import (
    RatificationError,
    build_ratification,
    decisions_digest,
    to_manifest_entries,
)


def _proposals():
    """Two proposals, enough to exercise accept and amend together."""
    return [
        {
            "tool_name": "access_cart_information",
            "proposed_classes": ["UNCLASSIFIED"],
            "evidence": [],
        },
        {
            "tool_name": "approve_discount",
            "proposed_classes": ["CAP_MOVES_MONEY"],
            "evidence": [
                {
                    "capability_class": "CAP_MOVES_MONEY",
                    "cites": {"kind": "docstring", "value": "Approve the discount."},
                    "citation": "Approve the discount.",
                }
            ],
        },
    ]


def _decisions():
    return {
        "access_cart_information": {
            "decision": "amend",
            "classes": ["CAP_READS_PII"],
            "reason": "returns a named customer's cart record",
        },
        "approve_discount": {"decision": "accept", "reason": "stands"},
    }


def _signed():
    proposals = _proposals()
    rat = build_ratification(
        ratified_by="Eric Tetzlaff",
        ratified_on="2026-08-28",
        proposals=proposals,
        decisions=_decisions(),
    )
    return {"proposals": proposals, "model_id": "test"}, rat


# --------------------------------------------------------------- the defect --
def test_a_post_signature_change_to_an_amendment_class_is_refused():
    """THE REPRODUCTION. This is the defect, stated as a test.

    Changing a signed amendment from CAP_READS_PII to CAP_MOVES_MONEY changed
    the emitted manifest while the proposal digest stayed valid.
    """
    pset, rat = _signed()
    tampered = copy.deepcopy(rat)
    tampered["decisions"]["access_cart_information"]["classes"] = ["CAP_MOVES_MONEY"]

    # The proposals did not move, so the OLD check cannot see this.
    assert tampered["proposal_set_digest"] == rat["proposal_set_digest"]

    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(pset, tampered)
    assert exc.value.code == "E_DECISIONS_DIGEST_MISMATCH"


def test_a_post_signature_change_to_a_verdict_is_refused():
    """A class is not the only field that changes the manifest.

    Flipping accept to reject DROPS a tool from the manifest entirely, which is
    at least as consequential as changing its classes.
    """
    pset, rat = _signed()
    tampered = copy.deepcopy(rat)
    tampered["decisions"]["approve_discount"]["decision"] = "reject"

    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(pset, tampered)
    assert exc.value.code == "E_DECISIONS_DIGEST_MISMATCH"


def test_adding_a_decision_after_signature_is_refused():
    """A tool the reviewer never ruled on cannot be added afterwards."""
    pset, rat = _signed()
    tampered = copy.deepcopy(rat)
    tampered["decisions"]["generate_qr_code"] = {
        "decision": "amend",
        "classes": ["CAP_MOVES_MONEY"],
        "reason": "smuggled in",
    }
    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(pset, tampered)
    assert exc.value.code == "E_DECISIONS_DIGEST_MISMATCH"


def test_a_record_with_no_decisions_digest_is_refused():
    """A record predating the fix must not pass unchallenged.

    Nothing has ever been ratified, so there is no legacy record to honour. A
    missing digest is an unbound record and it fails closed, loudly - the
    alternative is a field an attacker deletes to disable the check.
    """
    pset, rat = _signed()
    stripped = copy.deepcopy(rat)
    del stripped["decisions_digest"]
    with pytest.raises(RatificationError) as exc:
        to_manifest_entries(pset, stripped)
    assert exc.value.code == "E_DECISIONS_DIGEST_MISSING"


# ------------------------------------------------------------- the controls --
# A check that cannot pass is as useless as one that cannot fail.
def test_an_untampered_ratification_still_produces_its_manifest():
    pset, rat = _signed()
    entries = {e["tool_name"]: e for e in to_manifest_entries(pset, rat)}
    assert entries["access_cart_information"]["capability_classes"] == ("CAP_READS_PII",)
    assert entries["access_cart_information"]["classified_by"] == "human"
    assert entries["approve_discount"]["capability_classes"] == ("CAP_MOVES_MONEY",)
    assert entries["approve_discount"]["classified_by"] == "cartographer"


def test_editing_only_the_free_text_reason_does_not_invalidate():
    """Deliberate scope limit, not an oversight - see the module docstring.

    `reason` does not reach the manifest, so binding it would only make the
    record expire on a typo fix.
    """
    pset, rat = _signed()
    edited = copy.deepcopy(rat)
    edited["decisions"]["access_cart_information"]["reason"] = "typo fixed"
    entries = {e["tool_name"]: e for e in to_manifest_entries(pset, edited)}
    assert entries["access_cart_information"]["capability_classes"] == ("CAP_READS_PII",)


def test_the_decisions_digest_is_order_independent_over_tools():
    """Two reviewers recording the same rulings in a different order agree."""
    a = decisions_digest(_decisions())
    reordered = dict(reversed(list(_decisions().items())))
    assert decisions_digest(reordered) == a


def test_the_decisions_digest_moves_when_a_class_moves():
    """The mutation check on the control itself."""
    d = _decisions()
    a = decisions_digest(d)
    d["access_cart_information"]["classes"] = ["CAP_MOVES_MONEY"]
    assert decisions_digest(d) != a
