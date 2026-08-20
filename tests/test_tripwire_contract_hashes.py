"""test_tripwire_contract_hashes.py - the contracts L4 consumes, asserted by hash.

L4 produces **C9** and consumes **C1**, **C4**, and **C8**. Every one of them is
frozen at the W0 contract hash and recorded in `contracts/MANIFEST.json`.

WHY THE LANE ASSERTS THIS ITSELF rather than leaning on
`scripts/contract-check.py`. That script is the coordinator's gate over the whole
set and it runs when somebody runs it. This file runs on every `pytest`, which
is what a lane actually executes twenty times an hour - and the failure it is
guarding against is not malice, it is a lane editing a frozen artifact to make
its own suite go green. A CONTRACT THAT NO LONGER HASHES TO ITS RECORDED VALUE
MEANS SOMEONE EDITED A FROZEN ARTIFACT, AND THAT IS A STOP-AND-REPORT, NOT A
LOCAL FIX.

C8 is the one that matters most here and it is worth saying why. It carries G1a,
the nine expected verdicts, and it is HASH-LOCKED AT D2 AND NOT EDITABLE AFTER.
The known-bad harness reads its answer key out of that file. If C8 could drift,
the answer key could drift with it, and a re-labelled fixture would boot happily
against a moved key - which is the single edit that makes a blanket
`breach == true` oracle look correct.

The normalization is the one `MANIFEST.json` declares: LF, trailing whitespace
stripped per line, exactly one trailing newline, UTF-8 no BOM. It is NOT JCS -
these are text files, not JSON payloads, and hashing them as parsed JSON would
be a second, disagreeing definition of the same digest.
"""

import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"
MANIFEST = json.loads((CONTRACTS / "MANIFEST.json").read_text(encoding="utf-8"))

# C9 is produced here; C1, C4, and C8 are consumed. All four are asserted,
# because producing a contract is not a licence to edit it either.
L4_CONTRACTS = ("C1", "C4", "C8", "C9")


def normalize(raw):
    """The MANIFEST.json normalization, applied to bytes read from disk."""
    if raw[:3] == b"\xef\xbb\xbf":
        raise AssertionError("a contract file grew a BOM")
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return (text.rstrip("\n") + "\n").encode("utf-8")


_CASES = sorted(
    (cid, fname, meta["sha256"])
    for cid in L4_CONTRACTS
    for fname, meta in MANIFEST["contracts"][cid]["files"].items()
)


@pytest.mark.parametrize("cid,fname,expected", _CASES,
                         ids=["%s:%s" % (c, f) for c, f, _ in _CASES])
def test_consumed_contract_still_hashes_to_its_recorded_value(cid, fname, expected):
    got = hashlib.sha256(normalize((CONTRACTS / fname).read_bytes())).hexdigest()
    assert got == expected, (
        "%s (%s) NO LONGER HASHES TO ITS RECORDED VALUE. A frozen artifact was edited. "
        "STOP AND REPORT - lanes never edit contracts/, and the fix is not local.\n"
        "  recorded %s\n  on disk  %s" % (cid, fname, expected, got))


def test_the_manifest_agrees_with_the_lane_brief_about_who_consumes_what():
    """If the ownership map moves, this lane's assumptions about its inputs have
    moved with it, and the lane should find that out from a red test rather than
    from a merge conflict."""
    assert "L4" in MANIFEST["contracts"]["C1"]["consumed_by"]
    assert "L4" in MANIFEST["contracts"]["C4"]["consumed_by"]
    assert "L4" in MANIFEST["contracts"]["C8"]["consumed_by"]
    assert MANIFEST["contracts"]["C9"]["produced_by"] == "L4"


def test_c8_is_the_source_of_the_known_bad_answer_key():
    """Ties the hash assertion above to the thing it protects. C8 is hash-locked
    at D2; the harness reads G1a out of it; therefore the answer key is
    hash-locked too, and that is the whole chain."""
    from crucible.tripwire import expected_verdicts_from_gate_rule
    expected = expected_verdicts_from_gate_rule(CONTRACTS / "gate_rule.v1.yaml")
    assert len(expected) == 9
    assert expected["KB8"] == "CLEAN"
    assert MANIFEST["contracts"]["C8"]["files"]["gate_rule.v1.yaml"]["freezes"] == (
        "D2_not_editable_after")


def test_the_hash_check_can_fail(tmp_path):
    """The negative check ON the hash check, and it is not ceremony here.

    On 2026-08-20 the contract gate's own first negative test COULD NOT FAIL: it
    appended a trailing newline, which is exactly the mutation the normalization
    exists to absorb. It looked green for the same reason a broken smoke detector
    looks quiet. So this proves two things separately - that a real content
    change is caught, and that the mutations the normalization is SUPPOSED to
    absorb are still absorbed rather than being caught by accident.
    """
    original = (CONTRACTS / "verdict.schema.json").read_bytes()
    baseline = hashlib.sha256(normalize(original)).hexdigest()

    # A real content change. Must move the digest.
    changed = original.replace(b'"BREACH"', b'"BREACHED"', 1)
    assert changed != original, "the fixture text moved; this mutation no longer applies"
    assert hashlib.sha256(normalize(changed)).hexdigest() != baseline

    # Mutations the declared normalization absorbs. Must NOT move the digest -
    # if one of these did, the check would be measuring line endings rather than
    # content, and every checkout on Windows would look like tampering.
    for absorbed in (original + b"\n\n\n",
                     original.replace(b"\n", b"\r\n"),
                     original.rstrip(b"\n") + b"   \n"):
        assert hashlib.sha256(normalize(absorbed)).hexdigest() == baseline
