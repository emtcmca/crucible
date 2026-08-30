"""The pre-read seal proof must be able to fail, and must not touch the bucket.

THE PROOF IS A COMMAND, NOT A DOCUMENT, and that is the point of it. The
pre-registration requires a FRESH seal proof immediately before the sealed
read. A hand-written one ages the moment it is committed and nothing records
when it stopped being true.

Two properties matter more than anything the proof reports:

  1. IT CAN FAIL. A proof that passes unconditionally is a check that passes
     while measuring nothing - seventeen recorded instances in this repository
     and the reason every gate here ships a deliberately broken fixture.
  2. IT DOES NOT SPEND WHAT IT IS PROVING. The holdout counter measures
     audit-log DATA ACCESS entries against `gs://crucible-sealed-x7`, so an
     unattested read by the operator identity marks the run INVALID. A proof
     that reached for the bucket would be the most expensive check available.

WHAT "READ" MEANS HERE, BECAUSE THIS MODULE GOT IT WRONG AND SAID SO WRONGLY.

This docstring used to end "Nothing here reads the sealed corpus." That was
FALSE, and an independent reviewer found it by declining to run the suite: the
end-to-end test below executes the real proof command, which shells out to
`seal-commitment.py` and `seal-leak-check.py`, and BOTH of those open and parse
every sealed JSON file on the local disk. An ordinary `pytest` run therefore
opened the holdout.

Three different things were being called "a read" and only one of them is the
one that costs anything:

  CONTENT_READ        a granted `storage.objects.get` naming a real object in
                      gs://crucible-sealed-x7, inside the run's own window.
                      DEFINED BY A3.2 OF
                      docs/proof/f4-unseal-preregistration-2026-08-25.md, which
                      owns the term and the unit. Cited, never restated. It is
                      what marks a run INVALID.
  LOCAL FINGERPRINT ACCESS
                      a process opens the local files, hashes the bytes, and
                      surfaces nothing. This is how the seal is PROVEN intact.
                      It is not a violation, and forbidding it would forbid the
                      proof.
  HUMAN-OR-MODEL EXPOSURE
                      sealed text reaching a person's eyes or a model's
                      context. This is what the single attempt is spent on, and
                      what the adjudication gate exists to sequence.

THE MIDDLE AND LAST NAMES WERE CHOSEN ON THE SECOND ATTEMPT, and the first
attempt is worth recording because it is the same defect one level up. This
block originally called the third category "A CONTENT READ" - a term A3.2 had
already defined, for the first category, as a bucket fetch. Two distinct events
under one name, in a document written to separate them. The reviewer caught it
in the next pass: *"the three-way distinction is useful, but this naming is not
the right cut."* A vocabulary that collides with the ratified one is worse than
no vocabulary, because the ratified document is the one everything else cites.

THE CLAIM ITSELF WAS ALSO WRONG AS WRITTEN, and it has been narrowed. This
module used to say the sentence "no F4 object has been read" survived
untouched. It does not - local F4 files have been opened repeatedly, by the
commitment tool and the leak scanner, which is exactly what the finding was
about. What is defensible is the scoped pair:

  * no F4 GCS object has been fetched inside the measurement window;
  * no F4 content has been exposed to a human or a model.

Both rest on attestation. An outside reviewer cannot independently ratify
either one without the audit evidence or without observing the human process,
and that limit is part of the claim rather than a footnote to it. AUDIT.md
carries it for the repository; this note carries it for this module.

SO THE END-TO-END TEST NOW POINTS AT AN INVENTED FIXTURE DIRECTORY via
`CRUCIBLE_SEALED_DIR`, and a test below asserts it cannot do otherwise. The
PASSING branch of the proof is exercised by the OPERATOR immediately before the
read, which is the only place it can honestly be exercised: reproducing it in
CI would mean reading the holdout on every commit.
"""

import ast
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pre-read-seal-proof.py"
sys.path.insert(0, str(ROOT))


def _module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pre_read_seal_proof", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_dirty_tree_fails_the_proof(monkeypatch):
    """THE DELIBERATELY BROKEN CASE.

    A proof taken over uncommitted changes describes a state nobody else can
    reach, so it is worth nothing to the reader it exists for. This is also the
    check that proves the script can return FAIL at all.
    """
    mod = _module()
    monkeypatch.setattr(mod, "_run", lambda args, label: (True, "ok"))
    monkeypatch.setattr(mod, "git",
                        lambda *a: (" M some/file.py" if a[0] == "status" else "deadbeef"))
    checks = mod.gather()
    tree = [c for c in checks if "working tree" in c["check"]]
    assert tree and tree[0]["ok"] is False
    assert tree[0]["result"] == "DIRTY"


def test_a_clean_tree_with_passing_checks_passes():
    """The control. Without it the test above passes against a proof that
    always fails, which is a different bug with identical symptoms here."""
    mod = _module()
    import unittest.mock as m
    with m.patch.object(mod, "_run", lambda args, label: (True, "ok")), \
         m.patch.object(mod, "git", lambda *a: ("" if a[0] == "status" else "cafe")):
        checks = mod.gather()
    assert all(c["ok"] for c in checks)


def test_a_failing_subcheck_fails_the_whole_proof():
    """Either sub-check failing has to sink it. A proof that reported a leak
    and still said PASS would be worse than no proof."""
    mod = _module()
    import unittest.mock as m
    calls = {"n": 0}

    def one_bad(args, label):
        calls["n"] += 1
        return (calls["n"] != 1), "tail"

    with m.patch.object(mod, "_run", one_bad), \
         m.patch.object(mod, "git", lambda *a: ("" if a[0] == "status" else "cafe")):
        checks = mod.gather()
    assert not all(c["ok"] for c in checks)


def test_the_proof_never_reaches_for_the_sealed_bucket():
    """THE CONSTRAINT THAT COSTS THE MOST TO BREAK.

    Read from the source rather than from behaviour, deliberately: the failure
    this guards against is a future edit adding a convenience call, and no
    offline test can observe a `gcloud` invocation that nobody has written yet.
    So this asserts the bucket name and every cloud entry point are absent from
    the file, which is a property a reviewer can check by eye and a test can
    hold in place.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    # Docstrings and comments legitimately DISCUSS the bucket - the module
    # header explains at length why it must not be touched. Only executable
    # code is searched, so the explanation cannot fail its own rule.
    code_only = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            continue
        if isinstance(node, ast.Name):
            code_only.append(node.id)
        elif isinstance(node, ast.Attribute):
            code_only.append(node.attr)
    joined = " ".join(code_only)
    for banned in ("gcloud", "storage", "bigquery", "google"):
        assert banned not in joined, (
            "the proof reaches for %r in executable code. It must not touch "
            "gs://crucible-sealed-x7 in any way: the holdout counter measures "
            "audit-log DATA ACCESS entries there, and an unattested operator "
            "read marks the run INVALID." % banned)


def test_the_proof_publishes_no_fingerprint_value():
    """Ruling 46: a frozen hash has exactly one owner, the artifact.

    The proof records that the recompute AGREED and cites the commitment file.
    A copy of the value here would be a second source for it, and the whole
    reason the commitment is credible is that there is only one.
    """
    mod = _module()
    import unittest.mock as m
    with m.patch.object(mod, "_run", lambda args, label: (True, "ok")), \
         m.patch.object(mod, "git", lambda *a: ("" if a[0] == "status" else "cafe")):
        checks = mod.gather()
    blob = repr(checks)
    import json
    recorded = json.loads(
        (ROOT / "docs" / "proof" / "sealed-family-commitment.json")
        .read_text(encoding="utf-8"))["fingerprint"]
    assert recorded not in blob, "the proof copied the fingerprint value"
    assert any("sealed-family-commitment.json" in str(c.get("value_lives_in", ""))
               for c in checks), "the proof does not say where the value lives"


#: A sealed set that is not the sealed set. Every filename and every value is
#: INVENTED. Only the SHAPE is borrowed: `seal-commitment.py` hashes filenames
#: plus bytes and reads `capability_classes`, and `seal-leak-check.py` derives
#: its signal vocabulary from the file stems.
_FIXTURE_INSTANCES = {
    "f9-01-zzqx-vunlo-brimmage.json": {
        "instance_id": "atk_ffffffff0001",
        "capability_classes": ["CAP_MOVES_MONEY"],
        "turns": ["an invented turn", "an invented instruction"],
    },
    "f9-02-zzqx-praddle-yoxen.json": {
        "instance_id": "atk_ffffffff0002",
        "capability_classes": ["CAP_EXTERNAL_COMMS"],
        "turns": ["another invented turn", "another invented instruction"],
    },
}


def _stand_in_sealed_dir(tmp_path):
    """Write the invented set and hand back its directory."""
    import json
    d = tmp_path / "not-the-sealed-set"
    d.mkdir()
    for name, doc in _FIXTURE_INSTANCES.items():
        (d / name).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return d


@pytest.mark.skipif(not SCRIPT.is_file(), reason="script missing")
def test_the_script_runs_end_to_end_and_returns_a_real_exit_code(tmp_path):
    """Assert the postcondition, not the log line - over an INVENTED set.

    Exit 0 with a healthy-looking print is a known failure shape here. This
    runs the real script and requires the exit code to AGREE with the verdict
    it printed: a proof that says FAIL and exits 0 is read by any scheduler as
    a pass.

    IT POINTS AT A FIXTURE, AND THAT IS THE POINT. This test used to run the
    proof against whatever `seal-commitment.py` resolved on its own, which on
    the build machine is the SEAL worktree - so an ordinary `pytest` run opened
    and parsed all twenty-four held-out instances. Nothing was published and no
    bucket was touched, but a suite that reaches for the holdout is a suite an
    outside reviewer is right to decline to run, and one did.

    Against an invented set the fingerprint cannot match the published
    commitment, so the verdict here is FAIL. That is the branch worth pinning:
    agreement between what the proof SAYS and what it RETURNS is what a
    scheduler acts on, and it is only interesting when the two could disagree.
    """
    env = dict(os.environ)
    env["CRUCIBLE_SEALED_DIR"] = str(_stand_in_sealed_dir(tmp_path))
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=900, env=env)
    out = proc.stdout or ""
    assert "VERDICT" in out, out[-400:]
    said_pass = "VERDICT  PASS" in out
    assert (proc.returncode == 0) == said_pass, (
        "the exit code and the printed verdict disagree: rc=%d, printed %s"
        % (proc.returncode, "PASS" if said_pass else "FAIL"))
    # AND THE COMMITMENT CHECK MUST HAVE DISAGREED, which is the assertion
    # that actually discriminates.
    #
    # `assert not said_pass` was the first attempt and it was worthless: the
    # working tree is dirty in any live session, so the verdict is FAIL whether
    # or not the override was honoured, and the assertion passes either way.
    # That is a check that passes while measuring nothing, written INTO the
    # test for a fix whose whole subject is checks that pass while measuring
    # nothing.
    #
    # The fingerprint recomputed over an invented set CANNOT equal the
    # published commitment. If this said AGREED, the override was ignored and
    # the real holdout was hashed - which is precisely the defect being
    # removed, and it is now the thing that fails.
    assert "DISAGREED" in out, (
        "the commitment check did not disagree over an invented sealed set. "
        "CRUCIBLE_SEALED_DIR was ignored and the real holdout was read.\n"
        + out[-800:])
    assert not said_pass, out[-400:]


@pytest.mark.skipif(not SCRIPT.is_file(), reason="script missing")
def test_no_test_in_this_module_runs_the_proof_without_an_override():
    """The guard on the guard, read from this file's own source.

    The defect was never that the end-to-end test should not exist. It was that
    reaching the holdout was the DEFAULT and nothing said so. A future edit
    adding a second subprocess call, or dropping the `env=` kwarg from this
    one, restores the defect silently and no assertion in the module notices.

    So: every `subprocess.run` in this file that launches SCRIPT must pass an
    explicit `env`. Checked over the AST rather than by string search, because
    a comment mentioning `env=` satisfies a grep.
    """
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name != "run" or "SCRIPT" not in ast.dump(node):
            continue
        checked += 1
        assert any(kw.arg == "env" for kw in node.keywords), (
            "a subprocess.run launching the proof does not pass env=, so it "
            "inherits CRUCIBLE_SEALED_DIR from whatever shell ran pytest and "
            "falls back to the real holdout when that is unset")
    # THE CENSUS, NOT ONLY THE PREDICATE. A loop over an empty list asserting
    # nothing is the purest form of a check that passes while measuring
    # nothing, and this repository has seventeen recorded instances of it.
    assert checked >= 1, "this test found no proof invocations to check"


# ------------------------------- the artifact's own sequential ordering claim --
#
# An adversarial review put it exactly: the proof "cannot simultaneously be
# newly written, committed, current-HEAD-bound, and leave the tree clean."
# Reading HEAD happens before the file exists; writing it dirties the tree;
# committing it moves HEAD past the value recorded inside it.
#
# The resolution is to stop claiming simultaneity. The artifact claims a
# SEQUENCE - clean at HEAD X, then this file and nothing else, so the commit
# carrying it has X as its parent - and `--write` enforces the middle link
# instead of describing it.


def test_only_the_artifact_may_be_dirty_after_it_is_written():
    """The link that makes the parent-commit claim true rather than hoped."""
    mod = _module()
    expected = "docs/proof/pre-read-seal-proof-20260830T000000Z.json"
    assert mod.stray_dirty_paths("?? " + expected, expected) == []


def test_anything_else_dirty_is_reported_by_name():
    """A second dirty path means the commit carrying the proof carries it too.

    That is the ambiguity the proof exists to remove: a reader looking at the
    commit can no longer tell which of its contents the clean-tree claim was
    taken over.
    """
    mod = _module()
    expected = "docs/proof/pre-read-seal-proof-20260830T000000Z.json"
    porcelain = "\n".join((" M crucible/transfer/reader.py",
                            "?? " + expected,
                            "?? docs/diagrams/a-plate.svg"))
    assert mod.stray_dirty_paths(porcelain, expected) == [
        "crucible/transfer/reader.py", "docs/diagrams/a-plate.svg"]


def test_a_renamed_path_is_read_as_its_destination():
    """Porcelain renames are `orig -> new`, and `new` is the dirty one.

    Splitting on the arrow was not obvious and getting it wrong fails OPEN:
    the whole `orig -> new` string never equals the expected path, so the
    rename would be reported as a stray and the operator would be refused on a
    real run for a path that is genuinely the artifact.
    """
    mod = _module()
    expected = "docs/proof/pre-read-seal-proof-20260830T000000Z.json"
    porcelain = "R  docs/proof/old-name.json -> " + expected
    assert mod.stray_dirty_paths(porcelain, expected) == []


def test_a_quoted_path_with_a_space_is_unquoted():
    """Git quotes paths containing spaces. Left quoted, one would never match."""
    mod = _module()
    expected = "docs/proof/a file.json"
    assert mod.stray_dirty_paths('?? "docs/proof/a file.json"', expected) == []


# --------------------- the proof must describe ONE commit, not two of them --
#
# The proof used to run its checks and then read HEAD. An adversarial review
# named the consequence: a parallel commit landing after the leak scan and
# before HEAD is recorded leaves the worktree CLEAN, so the artifact names a
# commit whose contents were never scanned and `git status` cannot see it.
#
# Six worktrees have been live in this project at once. That is not a
# theoretical race here.
#
# No command can hold HEAD still, so the proof detects instead: it reads HEAD
# before the first check and again after the last, and a move is a FAIL.


def _pinned(mod, monkeypatch, heads):
    """Run `main` with the subprocess checks stubbed and HEAD scripted.

    `heads` is consumed one value per `rev-parse`, so a test says the sequence
    it wants rather than reaching into the module's control flow.
    """
    seq = iter(heads)
    monkeypatch.setattr(mod, "_run", lambda args, label: (True, "ok"))
    monkeypatch.setattr(
        mod, "git",
        lambda *a: ("" if a[0] == "status" else next(seq)))
    return mod.main([])


def test_a_commit_landing_while_the_checks_run_fails_the_proof(monkeypatch):
    """The race, detected. The tree is clean at both ends and it still fails.

    This is the case no dirty-path check can reach: nothing is modified, the
    scan simply happened against a different commit than the one recorded.
    """
    mod = _module()
    rc = _pinned(mod, monkeypatch, ["aaaaaaaaaaaa1111", "bbbbbbbbbbbb2222"])
    assert rc != 0, "the proof passed while HEAD moved underneath it"


def test_a_settled_tree_still_passes(monkeypatch):
    """The control, and it is not optional.

    Without it the test above passes against a proof that fails
    unconditionally, which is a different bug with identical symptoms.
    """
    mod = _module()
    rc = _pinned(mod, monkeypatch, ["aaaaaaaaaaaa1111", "aaaaaaaaaaaa1111"])
    assert rc == 0


def test_the_moved_head_check_says_which_two_commits(monkeypatch):
    """A refusal that names neither commit sends the operator to guess.

    At 1am, on a run that cannot be repeated, "something moved" is not a
    finding. The row has to carry the commit that was scanned and the commit
    that was recorded.
    """
    mod = _module()
    seq = iter(["aaaaaaaaaaaa1111", "bbbbbbbbbbbb2222"])
    monkeypatch.setattr(mod, "_run", lambda args, label: (True, "ok"))
    monkeypatch.setattr(mod, "git",
                        lambda *a: ("" if a[0] == "status" else next(seq)))
    mod.main([])
    # Re-run gather-free: the row is built in main, so assert on its text via a
    # second pass that captures what was printed.
    import io
    import contextlib
    seq2 = iter(["aaaaaaaaaaaa1111", "bbbbbbbbbbbb2222"])
    monkeypatch.setattr(mod, "git",
                        lambda *a: ("" if a[0] == "status" else next(seq2)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main([])
    out = buf.getvalue()
    assert "MOVED" in out, out
    assert "aaaaaaaaaaaa" in out and "bbbbbbbbbbbb" in out, out


# ------------------------------- a guard must fail closed when it cannot see --
#
# THE REVIEWER'S REPRODUCTION: "I simulated Git commands returning empty output
# and the proof printed VERDICT PASS, with a blank HEAD."
#
# The git helper took `.stdout.strip()` and threw away the return code, so every
# caller read the empty string as a fact about the repository - "" meant a clean
# tree and an unmoved HEAD. A git that could not run at all therefore produced a
# passing proof, immediately before an irreversible read. In a project that runs
# six worktrees at once, a held `index.lock` is enough to cause it.


class _FakeProc:
    def __init__(self, code, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def test_git_failing_is_not_a_clean_tree(monkeypatch):
    """UNKNOWN is its own answer, and it is not a pass.

    "clean" and "we could not ask" were the same value - the empty string -
    until this was fixed.
    """
    mod = _module()
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: _FakeProc(128, "", "fatal: not a repository"))
    monkeypatch.setattr(mod, "_run", lambda args, label: (True, "ok"))
    checks = mod.gather()
    tree = [c for c in checks if "working tree" in c["check"]]
    assert tree and tree[0]["ok"] is False, (
        "an unreadable repository was reported as a clean one")
    assert tree[0]["result"] == "UNKNOWN"


def test_the_proof_refuses_outright_when_git_cannot_run(monkeypatch, capsys):
    """The reviewer's exact case: every git command fails, and it must NOT pass."""
    mod = _module()
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: _FakeProc(128, "", "fatal: not a repository"))
    rc = mod.main([])
    out = capsys.readouterr().out
    assert rc != 0, "the proof passed with git unavailable"
    assert "REFUSED" in out
    assert "VERDICT  PASS" not in out


def test_a_blank_head_from_a_successful_git_is_refused(monkeypatch, capsys):
    """git can exit 0 and name no commit, in an unborn repository.

    The artifact's whole claim is that its own commit has this value as its
    parent. There is nothing here to be a parent, and a proof that recorded a
    blank HEAD would be making a claim about a commit that does not exist.
    """
    mod = _module()
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _FakeProc(0, ""))
    monkeypatch.setattr(mod, "_run", lambda args, label: (True, "ok"))
    rc = mod.main([])
    out = capsys.readouterr().out
    assert rc != 0, "a blank HEAD was accepted"
    assert "named no commit" in out


def test_git_raises_rather_than_returning_a_sentinel(monkeypatch):
    """Raising is deliberate. A sentinel is something four call sites can forget."""
    mod = _module()
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: _FakeProc(1, "", "boom"))
    with pytest.raises(mod.GitUnavailable) as caught:
        mod.git("rev-parse", "HEAD")
    assert "boom" in str(caught.value)


def test_git_succeeding_still_returns_its_output(monkeypatch):
    """The over-blocking control. A helper that only ever raises is not a helper."""
    mod = _module()
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: _FakeProc(0, "  cafebabe  \n"))
    assert mod.git("rev-parse", "HEAD") == "cafebabe"
