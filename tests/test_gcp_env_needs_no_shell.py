"""Reading the names must not require a shell, and constructing a gate must not either.

THE FINDING. An independent reviewer could not reproduce this suite's green on
a Windows host: `test_holdout_touch.py` lost all of its tests to one collection
error because it read the environment through `infra.verify_iam.load_env`,
which shells out to bash. That was repaired inside the test file first. This
closes it at the source, and the source turned out to reach further than the
tests.

`crucible/conductor/real_gate.py:313` calls the same `load_env`. That is
PRODUCTION code: on a host without a working bash, a `RealGate` could not be
CONSTRUCTED, so G7 and G8 - the two assertions that make a sealed run
believable - could not run at all. The repository ships an "Open in Cloud Shell"
button and step-by-step spin-up instructions aimed at contest judges, and
"reproducible setup instructions" is a scored criterion. A gate that needs the
reviewer to install Git Bash first is not reproducible; it is portable to the
author's machine.

WHY NOT JUST REQUIRE BASH. Adding the dependency is the cheaper edit and the
worse answer. It moves a problem we can solve once, here, onto every person who
ever opens the repository - and it makes the failure appear as a stack trace
about the file system rather than as anything to do with IAM, which is the one
thing `verify_iam.py`'s own header says this gate must never do.

WHAT WAS ACTUALLY WRONG. The docstring said bash was used "so there is exactly
one parser of it as well as one copy of it". One copy of the FILE is the real
property and it is preserved: `scripts/gcp-env.sh` is still the only place any
of these names exists, and nothing retypes them. One parser was the part that
was not worth its price, and the price was the whole suite's collectability.
A differential test buys both - see `test_holdout_touch.py`, which runs the
pure-Python reader and bash side by side and compares full key sets wherever
bash can actually run.
"""

import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _ShellUsed(AssertionError):
    """Raised in place of any subprocess launch. Reaching it IS the failure."""


@pytest.fixture
def no_subprocess(monkeypatch):
    """Every route out to a process, closed.

    Patching `subprocess.run` alone would leave `Popen`, `check_output` and
    `os.system` open, and a reader that quietly fell back to one of them would
    pass this test while still needing a shell. The point is not that one API
    is unused; it is that NO process is launched.
    """
    def boom(*a, **k):
        raise _ShellUsed("a subprocess was launched: %r" % (a[:1],))

    for name in ("run", "Popen", "check_output", "call", "check_call"):
        monkeypatch.setattr(subprocess, name, boom, raising=False)
    monkeypatch.setattr(os, "system", boom, raising=False)
    return boom


def test_reading_the_names_launches_no_process(no_subprocess):
    """`load_env` is the single reader every caller goes through."""
    from infra import verify_iam

    env = verify_iam.load_env(str(ROOT))
    assert env.get("CRUCIBLE_PROJECT"), "the anchor name did not survive"
    assert env.get("SUFFIX"), "SUFFIX did not survive"


def test_the_names_still_come_from_the_one_file(no_subprocess):
    """One COPY is the property that matters, and it is intact.

    Every value the reader returns has to be findable in `scripts/gcp-env.sh`.
    A reader that had grown its own defaults would pass the test above while
    quietly becoming a second source of truth for a bucket name - which G7 and
    G8 grep for as literal strings, so a divergence there does not fail loudly.
    It produces an unevaluable gate, and an unevaluable gate is a check that
    cannot fail.
    """
    from infra import verify_iam

    text = (ROOT / "scripts" / "gcp-env.sh").read_text(encoding="utf-8")
    for key, value in verify_iam.load_env(str(ROOT)).items():
        assert key in text, "%s is not declared in scripts/gcp-env.sh" % key
        # Values are COMPOSED - `gs://${CRUCIBLE_SEALED}` expands to a string
        # that is nowhere in the file verbatim - so the whole value cannot be
        # the unit. The unit is each unbroken run of four or more LETTERS:
        # small enough to survive both composition and the suffix - `x7`
        # splits `crucible-sealed-x7` and must not drag a partial word out
        # with it - and large enough that an invented bucket or account name
        # cannot hide inside one. The differential test below is the strong
        # check on values; this one holds where bash is unavailable to run it.
        for word in re.findall(r"[A-Za-z]{4,}", value):
            assert word in text, (
                "%s=%r contains the word %r, which appears nowhere in "
                "gcp-env.sh. The reader has invented a name."
                % (key, value, word))


def test_a_gate_can_be_constructed_without_a_shell(no_subprocess):
    """THE ONE THAT MATTERS, and the reason this is not only a test problem.

    G7 and G8 are the assertions that make a sealed run believable. If the
    object carrying them cannot be built on a reviewer's machine, they are
    unavailable to the only people the proof is for.

    `skip_cloud=True` because the network is a separate dependency and this
    test is about the shell. Construction is what was broken.
    """
    from crucible.conductor.real_gate import RealGate

    gate = RealGate(ledger=None, run_id="no-shell", blob_writer=None,
                    blob_reader=None, repo_root=ROOT,
                    holdout_expected=0, skip_cloud=True)
    findings = gate.preflight()
    assert findings, "a preflight that returns nothing is not a preflight"


def test_the_gate_reports_the_same_names_with_and_without_the_shell():
    """The control on all three tests above.

    Every one of them would pass against a reader that returned plausible
    rubbish, because none of them checks the VALUES against an independent
    source. This runs the real bash reader when bash exists and requires the
    two to agree name for name.

    Skipped rather than passed where bash is missing, with the reason naming
    what went unmeasured - a silent skip here would be a check that passes
    while measuring nothing, in the file written to close exactly that.
    """
    import shutil

    from infra import verify_iam

    if not shutil.which("bash"):
        pytest.skip(
            "no bash on PATH, so the pure-Python reader cannot be compared "
            "against the shell that used to do this job. UNMEASURED HERE: "
            "that the two agree name for name on scripts/gcp-env.sh. The "
            "reader is still exercised by the other tests in this file; only "
            "the cross-check against sh semantics is lost.")

    proc = subprocess.run(
        ["bash", "-c", '. "%s/scripts/gcp-env.sh" && env | grep -E '
                       '"^(CRUCIBLE_|SA_|SUFFIX)"' % ROOT.as_posix()],
        capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip("bash is on PATH but could not run gcp-env.sh: %s"
                    % (proc.stderr or "").strip()[:200])

    from_shell = dict(line.split("=", 1)
                      for line in proc.stdout.splitlines() if "=" in line)
    from_python = verify_iam.load_env(str(ROOT))

    assert set(from_python) == set(from_shell), (
        "the readers disagree on WHICH names exist: only in python %s, only in "
        "shell %s" % (sorted(set(from_python) - set(from_shell)),
                      sorted(set(from_shell) - set(from_python))))
    for key in sorted(from_shell):
        assert from_python[key] == from_shell[key], (
            "%s differs: python %r, shell %r"
            % (key, from_python[key], from_shell[key]))
