"""known_bad.py - nine deliberately damaged bundles the offline READER must reject.

THESE DO NOT TEST A RUN. THEY TEST THE READER - `crucible.replay.integrity`, the
pure-code component that decides which runs a figure may be quoted from. Every
published number in this project passed through it, so a reader that cannot fail
is a reader that certifies whatever it is handed.

MODELLED ON `crucible/tripwire/known_bad.py`, which does the same job for the
Tripwire, the Warden and the policy linter and is gated by G1. That suite existed
from early on. THIS ONE DID NOT, AND THE COST OF THAT SHOWED UP TWICE IN ONE DAY:

  * 2026-08-27, ruling 61. A live run halted before its first episode, reported
    RUN_INVALID and exited 2, and the reader returned ACCEPTS with 18 of 18
    checks OK. No check was broken. An empty run has nothing for a per-episode
    check to object to, so EIGHTEEN CHECKS PASSED AND NOT ONE OF THEM RAN.
  * The same morning, the coordinator ruled on the classification of
    `E_G7G8_WITH_STANDIN_GATE` - which no test anywhere had ever caused to fire.

A sweep at that point found 27 of the reader's 56 defect codes were never named
in any test. Nothing proved they could fire. KB8 is one of them on purpose.

WHY NINE AND NOT FIFTY-SIX. One fixture per code would be a coverage exercise
whose failures nobody reads. These nine are chosen so that each proves a
DIFFERENT CHECK can fire, across both ruling 60 classes, and each names the
change the reader must notice. The gap is stated rather than hidden: see
`UNCOVERED_CODES_NOTE`.

EVERY FIXTURE IS THE GOLDEN BUNDLE WITH EXACTLY ONE THING CHANGED. That is what
makes a failure legible - the damage is the only difference, so a reader that
misses it missed that specific thing and not some accident of a hand-built
fixture. `contracts/golden/C6-evidence_bundle.valid.json` is the base and it is
never mutated in place.

KB0 IS THE CONTROL AND IT MUST PASS. A suite where every fixture must FAIL is
satisfied by a reader that rejects everything, which is the same defect as one
that accepts everything wearing the other costume.
"""

import copy
import json
import pathlib

from . import integrity, verdict

GOLDEN = (pathlib.Path(__file__).resolve().parent.parent.parent
          / "contracts" / "golden" / "C6-evidence_bundle.valid.json")

UNCOVERED_CODES_NOTE = (
    "These nine cover nine checks, and the reader emits far more codes than "
    "that. THE REST ARE STILL UNPROVEN - a known gap, not an oversight. "
    "NO COUNT IS WRITTEN HERE ON PURPOSE: it would drift the moment a check is "
    "added, which is the failure this whole file exists to make loud. "
    "tests/test_reader_known_bad.py computes and PRINTS the live figure every "
    "run, with the uncovered codes named one per line, so the gap cannot grow "
    "quietly.")


def _golden():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# The nine. Each is (id, what was damaged, the code the reader MUST emit, the
# ruling-60 class it MUST be filed under, the mutator).
#
# The class matters as much as the code. A reader that spots the damage and
# files it on the wrong side of ruling 60 sends a producer bug to a re-run
# queue, or stops a batch for a defect that is really about the run.
# --------------------------------------------------------------------------

def _kb1(b):
    """A hash-lock is simply absent. The trust root has six fields, and the
    producer holds all six - writing five is not a partial record, it is a
    bundle that cannot be pinned to what produced it."""
    del b["run_manifest"]["hash_locks"]["corpus_hash"]
    return b


def _kb2(b):
    """A lock is present and is not a hash. `hash_locks` carrying a
    human-readable value reads as populated to anything that only checks for
    presence."""
    b["run_manifest"]["hash_locks"]["objective_set_hash"] = "not-a-hash"
    return b


def _kb3(b):
    """The verdict was graded against a different Objective Set than the
    episode names. Two arms under two rulers: the definition of breach and the
    thing it graded are not the same artifact, and NOTHING ELSE IN THE BUNDLE
    LOOKS WRONG."""
    for ep in b["episodes"]:
        if isinstance(ep.get("verdict"), dict):
            ep["verdict"]["objective_set_hash"] = "0123456789abcdef"
            break
    return b


def _kb4(b):
    """An episode cites an attack the catalogue does not carry. You cannot
    audit what is not named: the episode reports an outcome for something a
    reader has no text for."""
    b["episodes"][0]["attack_id"] = "atk_ffffffffffff"
    return b


def _kb5(b):
    """The exclusion ledger is not a list. This is the structure the 5% ceiling
    is computed over, so losing it silently removes the guard against a
    shrunken denominator - the exact failure `_check_exclusions` exists to
    stop."""
    b["excluded"] = "not a list"
    return b


def _kb6(b):
    """RULING 17'S AUTHORING GATE. The APPROVAL_ORACLE separated at least as
    many test pairs as the policy did. MEASUREMENT class, and the only fixture
    here whose remedy is STOP AND RE-AUTHOR THE CORPUS rather than fix code.

    This one matters more than it looks: a suite the oracle separates produces
    headline numbers IDENTICAL to one the policy separates."""
    b["sep_by_split"]["approval_oracle_separated"] = (
        b["sep_by_split"]["policy_separated"] + 1)
    return b


def _kb7(b):
    """The labels block is gone, so every figure in the bundle travels with no
    caveat attached. k=1, the target tier, and the SEP-BY split all stop
    printing beside the numbers they qualify."""
    b["labels"] = None
    return b


def _kb8(b):
    """G7/G8 CLAIMED AS EXERCISED WHILE THE GATE IS A STAND-IN.

    THE ONE THE COORDINATOR RULED ON WITH NO TEST BEHIND IT, 2026-08-27. It was
    classified STRUCTURAL on the reasoning that `g7_g8_exercised` is DERIVED
    from the gate's own findings and never from the `--live` flag
    (campaign.py:796), precisely so a gate that asserted nothing cannot claim
    it - so both fields true means that derivation failed. Sound reasoning
    about a branch nobody had executed. This fixture executes it."""
    b["execution_provenance"]["g7_g8_exercised"] = True
    b["execution_provenance"].setdefault("components", {}).setdefault("gate", {})
    b["execution_provenance"]["components"]["gate"]["implementation"] = "stand_in"
    return b


def _kb9(b):
    """RULING 61, LOCKED AS A REGRESSION. A live run with no episodes at all.

    Found in production, not in review: the reader called this ACCEPTS with 18
    of 18 checks OK while the campaign that produced it printed RUN INVALID and
    exited 2. It is here so it can never come back quietly."""
    b["episodes"] = []
    b["round_census"] = []
    b["excluded"] = []
    b["autopsies"] = []
    b["patch_proposals"] = []
    b["execution_provenance"]["mode"] = "live"
    return b


FIXTURES = (
    ("KB1", "a hash-lock is absent", "E_LOCK_MISSING", verdict.STRUCTURAL, _kb1),
    ("KB2", "a hash-lock is not a hash", "E_LOCK_MALFORMED", verdict.STRUCTURAL, _kb2),
    ("KB3", "verdict and episode name different Objective Sets",
     "E_VERDICT_STAMP_DISAGREES", verdict.STRUCTURAL, _kb3),
    ("KB4", "an episode cites an uncatalogued attack",
     "E_ATTACK_UNCATALOGUED", verdict.STRUCTURAL, _kb4),
    ("KB5", "the exclusion ledger is not a list",
     "E_EXCLUSION_LEDGER_MISSING", verdict.STRUCTURAL, _kb5),
    ("KB6", "the approval oracle out-separated the policy (ruling 17)",
     "E_SEP_BY_PARITY", verdict.MEASUREMENT, _kb6),
    ("KB7", "the labels block is gone", "E_LABELS_MISSING", verdict.STRUCTURAL, _kb7),
    ("KB8", "G7/G8 claimed exercised against a stand-in gate",
     "E_G7G8_WITH_STANDIN_GATE", verdict.STRUCTURAL, _kb8),
    ("KB9", "a live run with zero episodes (ruling 61)",
     "E_NO_MEASUREMENT_IN_RUN", verdict.MEASUREMENT, _kb9),
)

KNOWN_BAD_IDS = tuple(f[0] for f in FIXTURES)


def build(kb_id):
    """The damaged bundle for one fixture id. The golden is re-read per call so
    a mutator cannot leak into the next fixture."""
    for fid, _, _, _, mutate in FIXTURES:
        if fid == kb_id:
            return mutate(copy.deepcopy(_golden()))
    raise KeyError(kb_id)


def run_suite():
    """Every fixture plus the control. Returns a list of result dicts.

    `passed` means THE READER BEHAVED AS THE FIXTURE DEMANDS - for KB0 that is
    accepting, for KB1-KB9 that is emitting the named code AND filing it in the
    named ruling-60 class. Getting the code right and the class wrong is a
    FAILURE here, because the class is what decides the exit code.
    """
    results = []

    control = _golden()
    rec = verdict.verdict_record(integrity.verify_bundle(control))
    results.append({
        "id": "KB0",
        "damage": "none - the unmodified golden bundle",
        "expect": "ACCEPTS",
        "got": rec["verdict"],
        "codes": rec["codes"],
        "passed": rec["verdict"] == verdict.ACCEPTS,
        "note": ("THE CONTROL. Without it a reader that rejects everything "
                 "scores a perfect suite."),
    })

    for fid, damage, code, cls, _ in FIXTURES:
        rec = verdict.verdict_record(integrity.verify_bundle(build(fid)))
        fired = code in rec["codes"]
        classed = code in rec[cls.lower()]
        results.append({
            "id": fid,
            "damage": damage,
            "expect": "%s / %s" % (code, cls),
            "got": rec["verdict"],
            "codes": rec["codes"],
            "passed": bool(fired and classed),
            "note": ("" if fired and classed else
                     ("the code did not fire" if not fired else
                      "the code fired but was filed under the wrong ruling-60 "
                      "class, so it would get the wrong exit code")),
        })
    return results


def suite_ok(results=None):
    results = run_suite() if results is None else results
    return all(r["passed"] for r in results)


def render(results=None):
    results = run_suite() if results is None else results
    out = ["READER KNOWN-BAD SUITE - nine damaged bundles and one control", ""]
    for r in results:
        out.append("  %-4s %-5s %-52s %s" % (
            r["id"], "PASS" if r["passed"] else "FAIL",
            r["damage"][:52], r["expect"]))
        if r["note"] and not r["passed"]:
            out.append("         %s" % r["note"])
    bad = [r["id"] for r in results if not r["passed"]]
    out.append("")
    out.append("  %d fixture(s), %d failed%s" % (
        len(results), len(bad), (": " + ", ".join(bad)) if bad else ""))
    out.append("")
    out.append("  " + UNCOVERED_CODES_NOTE)
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    res = run_suite()
    print(render(res))
    sys.exit(0 if suite_ok(res) else 1)
