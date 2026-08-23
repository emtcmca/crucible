"""`seal-leak-check.py` must REFUSE when it has nothing to compare against.

Found 2026-08-22 by the overclaim-sweep lane, in a file it was not allowed to
edit, and it is the most serious instance of the day's defect class.

`SEALED` was `pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed")` - a
hardcoded absolute path into a DIFFERENT WORKTREE. On this machine that path
exists, so the check ran, found the 24 sealed instances, built 104 signals, and
worked. On a clone, a CI box, or a judge's machine it does not exist - and
`pathlib.glob` over a missing directory RETURNS EMPTY RATHER THAN RAISING.

So every signal set came back empty, each of ~485 files was compared against
nothing, and the script printed

    no leaks across 488 tracked files

and exited 0. **A check that cannot fail, standing behind a security claim about
a public repository**, and the only thing keeping it honest was which machine it
happened to be run on.

Three further halves of the same defect, all fixed with it:

* A bare `except Exception: continue` on the read swallowed unreadable files
  while still counting them in "across N tracked files" - an unscanned file
  reported as a clean one.
* The denominator was `len(tracked_files())`, which includes the exempt files
  the loop deliberately skipped.
* `CRUCIBLE_SEALED_DIR` originally fell through to the other candidates when it
  did not resolve. An explicit override that silently picks a different
  directory is the same defect one level up, so it is now authoritative.

The script is invoked by a human, not by CI, which makes the silent pass worse
rather than better: somebody runs it, sees green, and believes it.

WHY THESE RUN AS SUBPROCESSES. An in-process import was tried first and the
script defeats it: at module scope it permanently reassigns `sys.stdout` to a
`TextIOWrapper` over `sys.stdout.buffer`. Under pytest that wrapper outlives the
capture object it wrapped, and every later write in the session raises
`ValueError: I/O operation on closed file` from `tempfile` - the harness
failing, not the code under test. A subprocess also tests the thing a human
actually runs, including its exit code, rather than a function reachable only
after monkeypatching module state.
"""

import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "seal-leak-check.py"

CANDIDATES = (REPO / "corpus" / "sealed",
              pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed"))


def _sealed_present():
    return any(p.is_dir() and any(p.glob("*.json")) for p in CANDIDATES)


def _run(sealed_dir=None):
    """Run the real script. `sealed_dir=None` leaves the environment alone."""
    env = dict(os.environ)
    if sealed_dir is not None:
        env["CRUCIBLE_SEALED_DIR"] = str(sealed_dir)
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(REPO),
                          env=env, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def test_it_refuses_when_no_sealed_set_resolves(tmp_path):
    """THE RED CASE. This is the clone, the CI box, the judge's machine."""
    code, out = _run(tmp_path / "does-not-exist")
    assert code == 2, (
        "with no sealed set the script exited %r. Anything but a refusal is a "
        "green light nobody earned: there are no signals, so every file "
        "compares clean against nothing.\n%s" % (code, out))
    assert "REFUSING TO RUN" in out
    # THE VERDICT LINE, not the phrase. The refusal message QUOTES the words it
    # is warning about ("would print 'no leaks' having proved exactly nothing"),
    # so a bare substring test fails on the fix's own explanation. Assert the
    # line the script prints when it actually passes.
    assert "no leaks across" not in out, (
        "it printed a clean verdict while refusing. The refusal has to REPLACE "
        "the verdict, not accompany it.")


def test_it_refuses_when_the_sealed_set_exists_but_yields_no_signals(tmp_path):
    """A directory that exists and contributes nothing fails exactly like one
    that is absent, and looks exactly like a clean run. Resolving a path is not
    the same as having something to compare against."""
    empty = tmp_path / "sealed"
    empty.mkdir()
    code, out = _run(empty)
    assert code == 2, (
        "an empty sealed directory exited %r, not a refusal\n%s" % (code, out))
    assert "REFUSING TO RUN" in out
    assert "no leaks across" not in out


def test_an_explicit_override_is_authoritative(tmp_path):
    """It must NOT fall through to the real sealed set when the override fails
    to resolve. Falling through is what would make the two tests above
    unwritable on the one machine that holds the corpus - and an override
    silently overruled is its own version of this file's defect."""
    code, out = _run(tmp_path / "nope")
    assert code == 2
    assert "instance(s)" not in out, (
        "the override did not resolve and the script used the real sealed set "
        "anyway. An explicit instruction was silently overruled.")


def test_the_real_sealed_set_still_runs_and_reports_what_it_compared():
    """THE OTHER DIRECTION, and it is the one that matters.

    A "fix" that made the script refuse unconditionally would pass every test
    above and destroy the check entirely. Where the sealed set IS present it
    must resolve it, build real signals, and SAY HOW MANY OF EACH - the counts
    are what distinguish a real pass from the empty one, which otherwise print
    the same words.

    Skipped rather than failed where the set is genuinely absent: that is the
    IAM boundary working, not a defect.
    """
    if not _sealed_present():
        pytest.skip("no sealed set on this machine; the refusal tests cover it")
    code, out = _run()
    assert code == 0, "the real run exited %r\n%s" % (code, out)
    assert "instance(s)" in out and "signal(s)" in out, (
        "the run did not say how many instances and signals it compared "
        "against. Without those counts a real pass and the empty pass this "
        "file exists to stop are indistinguishable.")
    assert "ACTUALLY SCANNED" in out, (
        "the clean line does not distinguish files it scanned from files it "
        "merely listed. Exempt and unreadable files were in the denominator.")


def test_the_path_is_resolved_rather_than_typed():
    """The regression guard. A hardcoded absolute path into another worktree is
    what made this invisible for as long as it existed."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "CRUCIBLE_SEALED_DIR" in source
    assert 'REPO / "corpus" / "sealed"' in source, (
        "no repo-relative candidate. The standard location must be tried "
        "before any machine-specific one.")
