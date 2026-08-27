"""The reader known-bad suite, and the proofs that it can FAIL.

`crucible/replay/known_bad.py` passed all ten fixtures the first time it ran.
THAT IS NOT EVIDENCE. It is the promptsmith lesson restated: nine straight
all-PASS runs are indistinguishable from a broken judge, which is why that
project ships fixtures its suite must always fail.

So the tests below are not mostly about the reader. They are about the SUITE:

  * it must catch a reader that accepts everything      (the damaged fixtures)
  * it must catch a reader that rejects everything      (the control, KB0)
  * it must catch a reader that finds the right defect
    and files it under the wrong ruling-60 class        (the class assertion)
  * its coverage of the reader's codes must be FLOORED, so a refactor that
    quietly stops exercising the reader cannot report a clean suite

The last one is the `_MIN_AGGREGATES` lesson from the ruling 60 lane, which
caught a regex matching nothing on its first run: `offenders == []` is satisfied
just as well by looking nowhere.
"""

import re
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

from crucible.replay import integrity as I        # noqa: E402
from crucible.replay import known_bad as KB       # noqa: E402
from crucible.replay import verdict as V          # noqa: E402


def test_the_suite_passes():
    results = KB.run_suite()
    bad = [r["id"] for r in results if not r["passed"]]
    assert not bad, KB.render(results)


def test_the_control_is_present_and_is_the_unmodified_golden():
    """KB0 is load-bearing. A suite of nothing but must-fail fixtures is
    satisfied perfectly by a reader that refuses every bundle it is handed."""
    results = KB.run_suite()
    assert results[0]["id"] == "KB0"
    assert results[0]["expect"] == "ACCEPTS"


def test_every_fixture_changes_exactly_one_thing():
    """The damage must be the ONLY difference from the golden. A fixture that
    drifts from the golden in some second way can pass for the wrong reason."""
    golden = KB._golden()
    for fid, _, _, _, _ in KB.FIXTURES:
        damaged = KB.build(fid)
        top = {k for k in set(golden) | set(damaged)
               if golden.get(k) != damaged.get(k)}
        # KB9 empties five arrays at once and says so - it is the ruling 61
        # regression and the emptiness IS the single change.
        limit = 6 if fid == "KB9" else 1
        assert len(top) <= limit, (
            "%s differs from the golden in %d top-level keys: %s"
            % (fid, len(top), sorted(top)))


def test_building_a_fixture_does_not_mutate_the_golden_on_disk_or_the_next_one():
    """Mutators take a deepcopy. Without that, KB1 deleting a lock would leave
    every later fixture missing it, and the suite would pass in a way that has
    nothing to do with what each fixture claims to test."""
    first = KB.build("KB1")
    assert "corpus_hash" not in first["run_manifest"]["hash_locks"]
    second = KB.build("KB2")
    assert "corpus_hash" in second["run_manifest"]["hash_locks"], (
        "KB1 leaked into KB2 - the fixtures share state")
    assert KB._golden()["run_manifest"]["hash_locks"].get("corpus_hash")


# ==========================================================================
# THE PART THAT MATTERS: proving the suite can fail.
# ==========================================================================

class _Strawman:
    """A reader stand-in. `defects` is whatever we tell it to find."""

    def __init__(self, defects):
        self.rows = []
        self.defects = list(defects)
        self.digest = None

    @property
    def ok(self):
        return not self.defects


def test_the_suite_catches_a_reader_that_accepts_everything(monkeypatch):
    """The single most important test in this file.

    A reader that returns no defects for any input is the exact failure mode
    this suite exists to detect, and it is what the reader effectively WAS for
    an empty bundle until ruling 61."""
    monkeypatch.setattr(I, "verify_bundle", lambda b: _Strawman([]))
    results = KB.run_suite()

    assert results[0]["passed"], (
        "the control should still pass against an accept-everything reader - "
        "that is what makes the damaged fixtures the ones that catch it")
    failed = [r["id"] for r in results if not r["passed"]]
    assert failed == list(KB.KNOWN_BAD_IDS), (
        "an accept-everything reader must fail EVERY damaged fixture; it "
        "failed only %s" % failed)
    assert not KB.suite_ok(results)


def test_the_suite_catches_a_reader_that_rejects_everything(monkeypatch):
    """The mirror. Caught by KB0 alone, which is the whole reason KB0 exists."""
    bogus = I.Defect("E_SCHEMA", "nowhere", "a reader that refuses everything")
    monkeypatch.setattr(I, "verify_bundle", lambda b: _Strawman([bogus]))
    results = KB.run_suite()

    assert not results[0]["passed"], (
        "KB0 MUST fail against a reject-everything reader. If it does not, the "
        "suite is satisfied by a reader that certifies nothing.")
    assert not KB.suite_ok(results)


def test_the_suite_catches_the_right_defect_filed_under_the_wrong_class():
    """Ruling 60 makes the CLASS decide the exit code, so a reader that finds
    the defect and files it on the wrong side is still broken - it would send a
    producer bug to a re-run queue, or halt a batch over a bad run.

    Proved by flipping the expectation rather than the reader: KB6 is the one
    MEASUREMENT fixture, so demanding it be STRUCTURAL must fail."""
    fid, damage, code, cls, mutate = next(
        f for f in KB.FIXTURES if f[0] == "KB6")
    assert cls == V.MEASUREMENT
    rec = V.verdict_record(I.verify_bundle(KB.build(fid)))
    assert code in rec["codes"], "KB6 must still fire its code"
    assert code in rec[V.MEASUREMENT.lower()]
    assert code not in rec[V.STRUCTURAL.lower()], (
        "E_SEP_BY_PARITY filed STRUCTURAL would exit non-zero on a bundle "
        "whose remedy is STOP AND RE-AUTHOR the corpus")


# ==========================================================================
# Coverage, floored and printed. The gap is declared, never silent.
# ==========================================================================

_MIN_CODES_EXERCISED = 10


def _codes_the_reader_can_emit():
    src = (REPO / "crucible" / "replay" / "integrity.py").read_text(
        encoding="utf-8")
    return set(re.findall(r'"(E_[A-Z0-9_]+)"', src))


def _codes_this_suite_exercises():
    seen = set()
    for fid, _, _, _, _ in KB.FIXTURES:
        seen |= set(V.verdict_record(I.verify_bundle(KB.build(fid)))["codes"])
    return seen


def test_the_suite_actually_exercises_the_reader_and_the_floor_proves_it():
    """THE VACUITY FLOOR. Without it, a suite whose fixtures stopped damaging
    anything would report ten clean passes and exercise nothing."""
    exercised = _codes_this_suite_exercises()
    assert len(exercised) >= _MIN_CODES_EXERCISED, (
        "the suite caused only %d distinct reader codes to fire, below the "
        "floor of %d. The fixtures have stopped damaging what they claim to."
        % (len(exercised), _MIN_CODES_EXERCISED))


def test_every_fixtures_named_code_is_a_code_the_reader_can_actually_emit():
    """Guards a typo in a fixture's expectation, which would otherwise make the
    fixture unfalsifiable in the quiet direction."""
    emittable = _codes_the_reader_can_emit()
    for fid, _, code, _, _ in KB.FIXTURES:
        assert code in emittable, (
            "%s expects %s, which appears nowhere in integrity.py" % (fid, code))


def test_the_uncovered_codes_are_reported_so_the_gap_cannot_grow_quietly(capsys):
    """NOT AN ASSERTION THAT COVERAGE IS COMPLETE - it is not, and pretending
    otherwise is the defect. This prints what is still unproven so the number
    is visible every run, and fails only if coverage goes BACKWARDS."""
    emittable = _codes_the_reader_can_emit()
    exercised = _codes_this_suite_exercises()
    uncovered = sorted(emittable - exercised)

    with capsys.disabled():
        print("\n  READER CODE COVERAGE: %d of %d exercised by KB1-KB9, "
              "%d STILL UNPROVEN"
              % (len(exercised & emittable), len(emittable), len(uncovered)))
        for code in uncovered:
            print("    unproven  %s" % code)

    assert len(exercised & emittable) >= _MIN_CODES_EXERCISED
