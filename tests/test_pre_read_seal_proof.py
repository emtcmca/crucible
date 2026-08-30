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

Nothing here reads the sealed corpus.
"""

import ast
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


@pytest.mark.skipif(not SCRIPT.is_file(), reason="script missing")
def test_the_script_runs_end_to_end_and_returns_a_real_exit_code():
    """Assert the postcondition, not the log line.

    Exit 0 with a healthy-looking print is a known failure shape here. This
    runs the real script and requires the exit code to AGREE with the verdict
    it printed - a proof that says FAIL and exits 0 would be read by any
    scheduler as a pass.
    """
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout or ""
    assert "VERDICT" in out, out[-400:]
    said_pass = "VERDICT  PASS" in out
    assert (proc.returncode == 0) == said_pass, (
        "the exit code and the printed verdict disagree: rc=%d, printed %s"
        % (proc.returncode, "PASS" if said_pass else "FAIL"))
