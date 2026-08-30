"""`seal-leak-check.py` must REFUSE when it has nothing to compare against.

Found 2026-08-22 by the overclaim-sweep lane, in a file it was not allowed to
edit, and it is the most serious instance of the day's defect class.

`SEALED` was a hardcoded absolute path into a DIFFERENT WORKTREE. On the build
machine that path resolves, so the check ran, found the held-out instances,
built its signals, and worked. On a clone, a CI box, or a judge's machine it
does not resolve - and `pathlib.glob` over a missing directory RETURNS EMPTY
RATHER THAN RAISING.

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

------------------------------------------------------------------------------
2026-08-30: AND NOT ONE OF THEM MAY POINT AT THE REAL HELD-OUT SET.

An outside reviewer read this module rather than running it and found the half
of the finding that the sister repair had missed. `test_pre_read_seal_proof.py`
had been moved onto an invented fixture the day before; this file had not. It
searched two candidate locations for the real local held-out set and, where one
was present, ran the real scanner with no override at all - so on the build
machine an ordinary `pytest` opened and parsed every held-out instance. The
reviewer declined to run the suite for exactly that reason, twice.

Nothing was published and no bucket object was fetched. But a suite that opens
the holdout is a suite a reviewer is right to refuse, and "no F4 content has
been exposed to a human or a model" is a claim this repository makes in public.
A test module that quietly performs a local read while the claim is made about
it is the same defect as a check that passes while measuring nothing - it just
points outward instead of inward.

WHAT REPLACED IT. Every test below runs the real script against an INVENTED
sealed set written into `tmp_path`, handed over by an explicit
`CRUCIBLE_SEALED_DIR` on every single `subprocess.run`. No candidate path is
searched, no real location is named anywhere in this file, and
`test_no_path_here_can_reach_the_real_held_out_set` reads this module's own
source to keep all three true.

THE ASSERTIONS HAVE TO DISCRIMINATE. Pointing at a fixture is worth nothing if
the test would pass just the same when the override is ignored - that mistake
was already made once in this exact area, with an `assert not said_pass` that
was true either way. So the two positive tests assert something that is TRUE OF
THE INVENTED SET AND FALSE OF THE REAL ONE:

  * the run prints the fixture's own directory and its instance count, and the
    fixture holds three instances at a `tmp_path` the real set can never be at;
  * the selftest plants a leak drawn from the signals it built and reports
    catching it, and the string it reports carries the invented family prefix.

If the override were ignored, both would report the real set's path, count and
vocabulary instead, and both fail.

AND A FAILURE MESSAGE IS PUBLISHED OUTPUT. If the override ever does break, the
scanner's output may name held-out material, and a pytest failure message ends
up in a terminal, a CI log, or a reviewer's context - which is the exposure this
file exists to prevent, arriving through the door marked "diagnostics". So
`_showable()` withholds any output that has not first proved it came from the
invented set. Harder to debug, and correct.
"""

import ast
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "seal-leak-check.py"

#: The invented family prefix. It appears in the fixture directory name, in
#: every fixture file stem, and therefore in anything the scanner says about
#: them - which is what lets `_showable` tell fixture output from real output.
#: Checked 2026-08-30 against every tracked file in the repo: zero occurrences.
FIXTURE_MARK = "wqz-"

#: A sealed set that is not the sealed set. EVERY TOKEN IS INVENTED and none of
#: them occurs anywhere in the repository - verified 2026-08-30 by scanning the
#: text of every tracked file. That property is load-bearing twice over: a stem
#: sharing words with ordinary repo prose manufactures spurious leak hits (an
#: earlier draft used stems containing "ordering" and "refund" and produced six
#: of them), and a stem colliding with the sister module's fixture produces real
#: ones - which is how these tokens were chosen, after a first attempt reused
#: `test_pre_read_seal_proof.py`'s and the scanner correctly flagged that file.
#:
#: Only the SHAPE is borrowed from the real set. `signals()` splits the stem on
#: "-", treats everything from the fourth segment on as the pretext tail, pairs
#: adjacent tail tokens, and reads `scored_features.payout_instrument_id`.
_FIXTURE_TOKENS = (
    ("vorthak", "blimnoq"), ("drazzek", "vunthil"), ("pyrgloss", "chundak"),
    ("zomvril", "kwaptor"), ("grelbin", "shoxnar"), ("tulvane", "meskirr"),
    ("ozzendal", "farquine"), ("hydrolp", "jexmuth"), ("narquil", "plovrek"),
    ("quimbash", "raxendo"), ("sferbil", "thundrax"), ("ulvexo", "vraskin"),
    ("wexlorn", "xanthrup"), ("yobrilt", "zafquen"), ("brontik", "clymvax"),
    ("dorvish", "emblorq"),
)


def _stand_in_sealed_dir(tmp_path, count):
    """Write `count` invented instances and hand back their directory."""
    d = tmp_path / (FIXTURE_MARK + "not-the-sealed-set")
    d.mkdir(exist_ok=True)
    for i in range(count):
        a, b = _FIXTURE_TOKENS[i]
        doc = {
            "instance_id": "atk_wqz%011d" % (i + 1),
            "capability_classes": ["CAP_MOVES_MONEY"],
            "scored_features": {"payout_instrument_id": "pm_wqz_%04d" % (i + 1)},
            "turns": ["an invented turn", "an invented instruction"],
        }
        (d / ("%s%02d-hx-%s-%s.json" % (FIXTURE_MARK, i + 1, a, b))).write_text(
            json.dumps(doc, indent=2), encoding="utf-8")
    return d


#: Output that has PROVEN it did not come from the real set. Either it carries
#: the invented family prefix, or it is the refusal - which the script prints
#: before it has read anything at all.
_PROVES_NOT_SEALED = (FIXTURE_MARK, "REFUSING TO RUN")


def _showable(out):
    """A failure message is published output. Withhold anything unproven."""
    if any(m in out for m in _PROVES_NOT_SEALED):
        return out[-1500:]
    return ("<%d chars withheld. Nothing in this output identifies the invented "
            "fixture, so it may name held-out material, and a pytest failure "
            "message is read by a terminal, a CI log and a reviewer.>" % len(out))


def _run(sealed_dir, *extra_args):
    """Run the real script against `sealed_dir`, which is never optional.

    THE PARAMETER HAS NO DEFAULT ON PURPOSE, and a test below reads the AST to
    keep it that way. A default of `None` is what let the old `_run` inherit
    `CRUCIBLE_SEALED_DIR` from whatever shell started pytest and fall back to
    the real set when it was unset - the defect, expressed as a keyword
    argument.
    """
    env = dict(os.environ)
    env["CRUCIBLE_SEALED_DIR"] = str(sealed_dir)
    proc = subprocess.run([sys.executable, str(SCRIPT)] + list(extra_args),
                          cwd=str(REPO), env=env, capture_output=True,
                          text=True, timeout=900)
    return proc.returncode, proc.stdout + proc.stderr


def test_it_refuses_when_no_sealed_set_resolves(tmp_path):
    """THE RED CASE. This is the clone, the CI box, the judge's machine."""
    code, out = _run(tmp_path / "does-not-exist")
    assert code == 2, (
        "with no sealed set the script exited %r. Anything but a refusal is a "
        "green light nobody earned: there are no signals, so every file "
        "compares clean against nothing.\n%s" % (code, _showable(out)))
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
        "an empty sealed directory exited %r, not a refusal\n%s"
        % (code, _showable(out)))
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


def test_a_resolvable_sealed_set_runs_and_reports_what_it_compared(tmp_path):
    """THE OTHER DIRECTION, and it is the one that matters.

    A "fix" that made the script refuse unconditionally would pass every test
    above and destroy the check entirely. Where a sealed set IS present it must
    resolve it, build real signals, scan every tracked file, and SAY HOW MANY OF
    EACH - the counts are what distinguish a real pass from the empty one, which
    otherwise print the same words.

    This used to run against whatever the script resolved on its own, skipping
    where nothing was found. On the build machine that meant an ordinary pytest
    run opened the real held-out set; on every other machine it meant the whole
    test skipped, so the direction that matters was proven nowhere. An invented
    set fixes both at once.

    THE DISCRIMINATING ASSERTIONS ARE THE PATH AND THE COUNT. The script prints
    the directory it resolved and how many instances it found there. The fixture
    lives under `tmp_path` and holds three. If the override were ignored, both
    values would be the real set's instead - a different directory and a
    different number - and neither substring would be present. There is no way
    for this test to pass while reading the holdout.
    """
    sealed = _stand_in_sealed_dir(tmp_path, 3)
    code, out = _run(sealed)

    used_the_fixture = ("sealed set: %s" % sealed.as_posix()) in out
    assert used_the_fixture, (
        "the run did not report the invented directory as the set it "
        "resolved, so CRUCIBLE_SEALED_DIR was ignored and the real held-out "
        "set was opened. Output withheld: it may name held-out material.")

    assert code == 0, "the fixture run exited %r\n%s" % (code, _showable(out))
    assert "3 instance(s)" in out and "signal(s)" in out, (
        "the run did not say how many instances and signals it compared "
        "against. Without those counts a real pass and the empty pass this "
        "file exists to stop are indistinguishable.\n%s" % _showable(out))
    assert "ACTUALLY SCANNED" in out, (
        "the clean line does not distinguish files it scanned from files it "
        "merely listed. Exempt and unreadable files were in the denominator."
        "\n%s" % _showable(out))


def test_the_matcher_still_catches_a_planted_leak(tmp_path):
    """`--selftest` plants one of each leak kind and requires every one caught.

    Without this the file only ever asserts that a clean repo scans clean, which
    is the shape of a check that cannot fail. The selftest indexes the sixteenth
    slug, so the fixture holds sixteen instances.

    IT DISCRIMINATES ON VOCABULARY. The planted strings are drawn from the
    signals the scanner just built, so what it reports catching is the invented
    family prefix. Against the real set it would report a real pretext instead -
    which would also mean this test had just printed one.
    """
    sealed = _stand_in_sealed_dir(tmp_path, 16)
    code, out = _run(sealed, "--selftest")

    caught_the_invented_vocabulary = FIXTURE_MARK in out
    assert caught_the_invented_vocabulary, (
        "the selftest did not report catching anything from the invented set, "
        "so CRUCIBLE_SEALED_DIR was ignored. Output withheld.")
    assert code == 0, (
        "the selftest failed: one of the planted leak kinds was not caught, or "
        "one of the ordinary-prose cases was flagged.\n%s" % _showable(out))
    assert "0 case(s) failed" in out, _showable(out)


def test_the_path_is_resolved_rather_than_typed():
    """The regression guard. A hardcoded absolute path into another worktree is
    what made this invisible for as long as it existed."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "CRUCIBLE_SEALED_DIR" in source
    assert 'REPO / "corpus" / "sealed"' in source, (
        "no repo-relative candidate. The standard location must be tried "
        "before any machine-specific one.")


# --------------------------------------------------------------------------
# The guard on the guard: read this module's own source, because the failure it
# protects against is a future edit, and no runtime assertion can observe a call
# nobody has written yet.

#: Assembled from fragments so the ban does not match the line that states it.
#: Spelling either one out here would make this test fail on itself, and the
#: obvious repair - exempting the line - is how a guard stops guarding.
_BANNED_LOCATIONS = ("wt-" + "SEAL", "corpus" + "/sealed")


def test_no_path_here_can_reach_the_real_held_out_set():
    """Four properties, all read off this file's AST, all of them the same one.

    1. No location of a real sealed set is typed anywhere in this module - not
       in code, not in a docstring. A path in prose is one copy-paste from being
       a path in code, and this module's whole defect began as a literal.
    2. This module never globs. Resolving a sealed directory IN-PROCESS was the
       other half of the old defect: `_sealed_present()` searched two candidate
       locations and listed their contents, and held-out FILENAMES are
       themselves the material the seal protects - each one describes its
       attack's pretext.
    3. Every `subprocess.run` that launches the script passes `env=`. Dropping
       that kwarg restores the defect silently.
    4. `_run` has no default for `sealed_dir`, and sets `CRUCIBLE_SEALED_DIR`
       unconditionally at the top level of its body rather than inside a branch.
       A default, or an `if`, is a path through this module to the real set.

    Each check carries a census. A loop over an empty list asserting nothing is
    the purest form of a check that passes while measuring nothing, and this
    repository has seventeen recorded instances of it.
    """
    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    for banned in _BANNED_LOCATIONS:
        assert banned not in src, (
            "this module names a real sealed location (%r). It must reach one "
            "only through an invented fixture." % banned)

    tree = ast.parse(src)

    globs = [n for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and n.attr in ("glob", "rglob")]
    assert not globs, (
        "this module globs a directory. Resolving the sealed set in-process is "
        "the half of the 2026-08-22 defect that survived the first repair, and "
        "held-out filenames are held-out material.")

    runs = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name != "run" or "SCRIPT" not in ast.dump(node):
            continue
        runs += 1
        assert any(kw.arg == "env" for kw in node.keywords), (
            "a subprocess.run launching the scanner does not pass env=, so it "
            "inherits CRUCIBLE_SEALED_DIR from whatever shell ran pytest and "
            "falls back to the real held-out set when that is unset")
    assert runs >= 1, "this test found no scanner invocations to check"

    runners = [n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "_run"]
    assert len(runners) == 1, "expected exactly one _run, found %d" % len(runners)
    fn = runners[0]
    assert [a.arg for a in fn.args.args] == ["sealed_dir"], (
        "_run's signature changed. The sealed directory must be its first and "
        "only positional parameter.")
    assert not fn.args.defaults, (
        "_run gives sealed_dir a default, so a caller can omit it and inherit "
        "the ambient environment. That default IS the defect.")

    assignments = 0
    for stmt in fn.body:                      # DIRECT body only, not ast.walk:
        if not isinstance(stmt, ast.Assign):  # an assignment inside an `if` is
            continue                          # exactly what must not be here.
        for target in stmt.targets:
            if isinstance(target, ast.Subscript) \
                    and isinstance(target.slice, ast.Constant) \
                    and target.slice.value == "CRUCIBLE_SEALED_DIR":
                assignments += 1
    assert assignments == 1, (
        "_run does not set CRUCIBLE_SEALED_DIR exactly once, unconditionally, "
        "at the top level of its body (found %d). Setting it inside a branch "
        "means some path through _run does not set it at all." % assignments)
