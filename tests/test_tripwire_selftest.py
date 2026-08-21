"""test_tripwire_selftest.py - --selftest, and what it has to prove.

The boot self-test runs BEFORE EVERY ROUND and is G1a's mechanism. It is not a
smoke test. Two things it must establish, and the second is the one that is
usually missing:

  1  THE HARNESS CAN RETURN EVERY VERDICT, including the rare ones. A harness
     that has only ever emitted BREACH and CLEAN has never demonstrated it can
     reach INVALID, and INVALID is the verdict that stops a whole run.

  2  THE HARNESS CAN STILL FAIL. Each shipped strawman is run against the suite
     and MUST be rejected by it. Nine straight all-PASS runs are
     indistinguishable from a broken judge, which is the entire reason the
     known-bad suite exists - so `--selftest` re-earns that claim on every boot
     rather than inheriting it from the day the fixtures were written.

Failure of the boot self-test is `HALT_HUMAN`, listed alongside a known-bad leak
and a read-back failure. It is not advisory.
"""

import subprocess
import sys
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

from crucible.tripwire import selftest  # noqa: E402


def test_selftest_passes():
    report = selftest()
    assert report.ok, report.failures


def test_selftest_produced_every_verdict_in_the_union_domain():
    """BREACH and CLEAN are easy. INVALID, REJECT, and the linter's
    REJECT-then-ACCEPT are the ones a suite quietly stops covering."""
    report = selftest()
    assert report.verdicts_observed == {
        "BREACH", "CLEAN", "INVALID", "REJECT", "LINTER_REJECT_THEN_ACCEPT"}


def test_selftest_proves_each_strawman_is_still_caught():
    report = selftest()
    assert report.strawmen_caught, "no strawman was exercised"
    for name, caught in report.strawmen_caught.items():
        assert caught, (
            "STRAWMAN %r PASSED THE KNOWN-BAD SUITE. The suite has stopped "
            "measuring; a deliberately wrong oracle is now indistinguishable "
            "from the real one." % name)


def test_selftest_runs_the_import_lint():
    report = selftest()
    assert report.import_lint_findings == []
    assert report.import_lint_ran is True, (
        "a self-test that skips the lint reports a model-free component on the "
        "strength of a docstring")


def test_selftest_exits_zero_from_the_command_line():
    proc = subprocess.run(
        [sys.executable, "-m", "crucible.tripwire", "--selftest"],
        cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ALL EXPECTED" in proc.stdout


def test_selftest_exits_nonzero_when_a_fixture_is_mislabelled(tmp_path):
    """The command-line half of the mis-labelled-fixture check. A boot self-test
    that reports a problem on stdout and still exits 0 is a check that cannot
    fail, because CI reads the exit code."""
    import json
    import shutil
    shutil.copytree(REPO / "tests" / "golden_traces", tmp_path / "golden_traces")
    p = tmp_path / "golden_traces" / "known_bad" / "KB8.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["expected_verdict"] = "BREACH"
    p.write_text(json.dumps(doc), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "crucible.tripwire", "--selftest",
         "--traces", str(tmp_path / "golden_traces")],
        cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "KB8" in (proc.stdout + proc.stderr)
