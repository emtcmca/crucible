"""test_escalated_overclaims.py - printed sentences that outran the code.

Same defect class as `test_overclaim.py`, found in a second sweep on
2026-08-23 and escalated out of the lane that found it because the files were
not that lane's to edit. A sentence asserting something the code never
computed is a defect of the same severity as a crash, and this repository is
judged partly on architectural honesty.

Two here, both in `scripts/verify-chain.py`:

  1. MIRROR_DRIFT summed a hash-field mismatch with a CANONICALIZATION
     FAILURE and then said "That flags the index, not the record" - for a
     failure that is in the record's own bytes. It also decided which side
     moved, from data that cannot decide it.
  2. The success banner printed a conclusion about IAM. The script never
     opens a socket. `crucible/conductor/real_gate.py` is what checks that
     boundary live, and it can return UNEVALUABLE; `data-spec.md` A4 still
     carries status CONFIRM.

And one in `crucible/replay/offline_lint.py` - see the last section.
"""

import importlib.util
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


_VC_CACHE = []


def _verify_chain():
    """`scripts/verify-chain.py` as a module. Loaded by path because of the
    hyphen, and NOT imported at module scope: it rebinds `sys.stdout` at
    import, which does not belong in a pytest process. Every test that needs
    the printed OUTPUT shells out instead; this is for the pure functions.

    `io.StringIO` has no `.buffer`, so the script's `hasattr` guard declines to
    rebind and pytest's capture survives."""
    if _VC_CACHE:
        return _VC_CACHE[0]
    import io
    spec = importlib.util.spec_from_file_location(
        "verify_chain_under_test", REPO / "scripts" / "verify-chain.py")
    mod = importlib.util.module_from_spec(spec)
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.stdout = saved
    _VC_CACHE.append(mod)
    return mod


class _FakeLedger:
    """`rows_from_ledger` uses exactly one method. A real sqlite ledger cannot
    be made to hold a payload that does not canonicalize - `promote` refuses
    one - so the two fault kinds are injected here."""

    def __init__(self, rows):
        self._rows = rows

    def versions(self, run_id):
        return self._rows


UNCANONICAL = {"version": 1, "payload_bytes": b'{"amount": 1.5}',
               "policy_hash_full": "a" * 64, "parent_hash": None,
               "lineage_hash": "l" * 64}
# Canonicalizes cleanly; the stored hash FIELD is the thing that disagrees.
FIELD_MISMATCH = {"version": 2, "payload_bytes": b'{"amount": 1}',
                  "policy_hash_full": "b" * 64, "parent_hash": "a" * 64,
                  "lineage_hash": "m" * 64}


# ---------------------------------------------------------------------------
# 1. Two faults, two counts
# ---------------------------------------------------------------------------

def test_a_payload_that_does_not_canonicalize_is_not_counted_as_hash_field_drift():
    """The bytes themselves are broken. Calling that "a stored hash field
    disagrees with the stored bytes" names the wrong artifact, and the summary
    then said "That flags the index, not the record" about it."""
    vc = _verify_chain()
    rows, byte_drift, field_drift = vc.rows_from_ledger(
        _FakeLedger([UNCANONICAL]), "run_x")
    assert len(rows) == 1
    assert len(byte_drift) == 1, "the canonicalization failure is its own fault"
    assert field_drift == [], (
        "and it is NOT a hash-field mismatch - no hash was computed to compare")


def test_a_hash_field_mismatch_is_not_counted_as_a_canonicalization_failure():
    """The other direction, so neither count can quietly absorb the other."""
    vc = _verify_chain()
    _rows, byte_drift, field_drift = vc.rows_from_ledger(
        _FakeLedger([FIELD_MISMATCH]), "run_x")
    assert byte_drift == []
    assert len(field_drift) == 1


def test_both_faults_at_once_are_reported_as_two_and_never_summed():
    vc = _verify_chain()
    _rows, byte_drift, field_drift = vc.rows_from_ledger(
        _FakeLedger([UNCANONICAL, FIELD_MISMATCH]), "run_x")
    assert (len(byte_drift), len(field_drift)) == (1, 1)
    lines = "\n".join(vc.drift_lines(byte_drift, field_drift))
    assert "2 stored hash field" not in lines, (
        "the old summary summed them into one count of hash fields")


def test_a_clean_ledger_produces_no_drift_lines():
    """The other side. A reporter that always reports is not reporting.

    Both fault kinds above came out non-empty from the same function on the
    same call shape, so this zero is a measured zero rather than a blind spot.
    """
    vc = _verify_chain()
    clean = {"version": 1, "payload_bytes": b'{"amount": 1}',
             "policy_hash_full": __import__("hashlib").sha256(
                 b'{"amount":1}').hexdigest(),
             "parent_hash": None, "lineage_hash": "l" * 64}
    _rows, byte_drift, field_drift = vc.rows_from_ledger(
        _FakeLedger([clean]), "run_x")
    assert (byte_drift, field_drift) == ([], [])
    assert vc.drift_lines([], []) == []


def test_the_drift_summary_does_not_decide_which_side_moved():
    """"That flags the index, not the record" is a CONCLUSION, and the data
    cannot support it: a stored hash and stored bytes that disagree tell you
    they disagree and nothing about which one was rewritten. The row-level
    text two functions away said the opposite - "Something rewrote the
    payload" - so the script contradicted itself in one run."""
    vc = _verify_chain()
    _rows, byte_drift, field_drift = vc.rows_from_ledger(
        _FakeLedger([FIELD_MISMATCH]), "run_x")
    lines = " ".join(vc.drift_lines(byte_drift, field_drift))
    assert "flags the index, not the record" not in lines
    assert "which side" in lines.lower() or "cannot say" in lines.lower(), (
        "it must say the direction is undecidable rather than pick one")


# ---------------------------------------------------------------------------
# 2. The IAM sentence the script never earned
# ---------------------------------------------------------------------------

def _run_verify_chain_on_a_real_ledger(tmp_path):
    """Build a three-version chain the same way `--selftest` does, then run the
    script as a subprocess and return its stdout. The banner under test only
    prints on the success path, so it has to be a real intact chain."""
    import json

    from crucible.gate import promote
    from crucible.ledger import Ledger

    run = "run_20260820_000000_iamtest"
    locks = {"manifest_hash": "m" * 16, "objective_set_hash": "o" * 16,
             "gate_rule_hash": "g" * 16, "target_hash": "t" * 16}
    blobs = {}
    db = tmp_path / "chain.db"
    with Ledger(str(db)) as led:
        led.open_run(run, "2026-08-20T00:00:00Z", locks)
        for i in (1, 2, 3):
            payload = {"policy_schema_version": 1,
                       "target_manifest_hash": locks["manifest_hash"],
                       "rules": [{"rule_id": "r_%012d" % k, "verb": "deny",
                                  "cap_selector": "CAP_MOVES_MONEY"}
                                 for k in range(i)]}
            promote(led, run, json.dumps(payload).encode(), "crucible-gate",
                    "2026-08-20T00:00:00Z", locks["manifest_hash"],
                    lambda n, d: blobs.__setitem__(n, d), lambda n: blobs[n])

    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "verify-chain.py"),
         "--ledger", str(db), "--run", run],
        capture_output=True, text=True, cwd=str(REPO))
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout


@pytest.fixture(scope="module")
def chain_output(tmp_path_factory):
    return _run_verify_chain_on_a_real_ledger(tmp_path_factory.mktemp("vc"))


def test_the_banner_does_not_assert_an_iam_boundary_it_never_inspected(chain_output):
    """The script opens a sqlite file. It runs no `gcloud`, reads no IAM
    policy, and cannot tell whether the boundary it was describing exists.

    `crucible/conductor/real_gate.py` is what checks it, live, and that gate
    can return UNEVALUABLE with the text "This gate did not inspect the
    boundary and must not be read as a pass." Two scripts must not disagree
    about whether a boundary was checked.

    Whitespace is collapsed first. The original sentence was split across two
    `print` calls, so a literal substring check on the raw output passed while
    the sentence was still there - a check that could not fail."""
    flat = " ".join(chain_output.split())
    assert "IAM immutability is the real control; this is the detector." \
        not in flat


def test_the_banner_says_the_iam_boundary_was_not_read(chain_output):
    """Saying nothing would be quieter and worse: the distinction between
    detector and control is the honest half, and data-spec 2.4 says to state
    it out loud. So it stays - attributed, and marked as not read here."""
    low = chain_output.lower()
    assert "not read" in low or "did not" in low
    assert "real_gate" in chain_output or "G8" in chain_output, (
        "name the gate that DOES check it, so the reader can go look")


def test_the_banner_still_makes_the_claim_it_did_earn(chain_output):
    """The other side, so the fix cannot be "delete the paragraph". Every hash
    WAS recomputed from bytes, and the chain IS unsigned; both are earned."""
    assert "RECOMPUTED FROM BYTES" in chain_output
    assert "Unsigned" in chain_output
    assert "CHAIN INTACT" in chain_output


def test_the_selftest_exercises_both_drift_kinds():
    """A branch nothing has ever entered is a branch nobody has seen work. The
    selftest's own standard is "a verifier that has only ever been shown
    intact chains has not been shown to verify anything", and until 2026-08-23
    neither drift path was in it."""
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "verify-chain.py"), "--selftest"],
        capture_output=True, text=True, cwd=str(REPO))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "does not canonicalize" in out.stdout
    assert "hash field" in out.stdout
    assert "FAIL" not in out.stdout
