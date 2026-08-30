"""The rehearsal must teach the real thing and must not be able to reach the seal.

A rehearsal is only worth having if it exercises the path it is standing in
for, and it is only SAFE to have if it cannot touch the holdout or leave
something that could be mistaken for a real ruling. Both halves are asserted
here, and the second half is asserted structurally rather than by reading the
script's intentions.

Every instance id below belongs to a TRAINING family. Nothing in this file
reads, names, or resolves the sealed set.
"""

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rehearse-adjudication.py"
sys.path.insert(0, str(ROOT))


def _module():
    spec = importlib.util.spec_from_file_location("rehearse_adjudication", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT)] + list(args),
                          cwd=str(ROOT), capture_output=True, text=True,
                          timeout=300)


# ----------------------------------------------------- it cannot reach the seal


def test_pointing_the_rehearsal_at_the_sealed_family_is_refused():
    """The one mistake a practising operator is most likely to make.

    Someone rehearsing for an F4 run types `--family F4`, because that is the
    thing they are rehearsing for. It must refuse, it must refuse with a
    sentence rather than a traceback, and the refusal must come from the
    RUNNER'S loader - so it cannot drift out of step with the guard that
    protects the real run.
    """
    proc = _run("--family", "F4")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "E_SEALED_FAMILY_VIA_TRAINING" in proc.stdout
    assert "Traceback" not in (proc.stdout + proc.stderr), (
        "a practising operator got a stack trace where a sentence belonged")


def test_the_script_has_no_door_to_the_sealed_path_at_all():
    """READ FROM THE SOURCE, because the defect would be a future edit.

    No behavioural test can observe a `--sealed` flag nobody has added yet.
    This asserts the absence of every name that reaches the holdout: the flag,
    the object-name list the sealed read requires, and the loader on the other
    side of the door.

    Docstrings legitimately DISCUSS all of these - the module header explains at
    length why they are absent - so only executable code is searched.
    """
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    code = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            continue
        if isinstance(node, ast.Name):
            code.append(node.id)
        elif isinstance(node, ast.Attribute):
            code.append(node.attr)
    joined = " ".join(code)
    for banned in ("load_sealed_instances", "sealed_io", "SEALED_BUCKET",
                   "_declared_names"):
        assert banned not in joined, (
            "the rehearsal reaches for %r in executable code. It exists "
            "precisely because it cannot spend the single attempt." % banned)

    # And the two arguments that would make it possible.
    source = SCRIPT.read_text(encoding="utf-8")
    for flag in ('"--sealed"', '"--object-names"', '"--i-am-opening-the-seal"'):
        assert flag not in source, (
            "the rehearsal declares %s. There is one door to the holdout and "
            "it is not in this file." % flag)


def test_the_loader_is_called_with_the_sealed_flags_hard_false():
    """Not `args.something` - the literal `False`, twice.

    A rehearsal that passed a variable here would be one flag away from being
    talked into the real read by a future argument. Asserted over the AST so
    the constants cannot be spelled differently.
    """
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", None) == "load_instances"]
    assert len(calls) == 1, (
        "expected exactly one load_instances call, found %d" % len(calls))
    positional = calls[0].args
    assert len(positional) == 3, positional
    for arg in positional[1:]:
        assert isinstance(arg, ast.Constant) and arg.value is False, (
            "the sealed arguments are not literal False: %s"
            % ast.dump(positional[1]))


# --------------------------------------------- it cannot masquerade as the real


def test_a_rehearsal_record_cannot_satisfy_the_real_gate():
    """THE STRUCTURAL CLAIM THE MODULE DOCSTRING RESTS ON, ASSERTED.

    The docstring says a rehearsal record is harmless because the sealed gate
    derives its id set from the instances that came off the wire, so a record
    over stand-in ids cannot load against them. That is the protection that
    holds when the procedural one - "we did not write it anywhere obvious" -
    does not.

    An unasserted safety claim in a docstring is exactly the shape this
    repository keeps finding, so it is exercised here against the real loader
    rather than argued.
    """
    from crucible.transfer import inspect as insp
    from crucible.transfer.adjudication import AdjudicationError, PASS_CODE

    rehearsed_ids = ["atk_" + "a" * 12, "atk_" + "b" * 12]
    record = insp.attach_challenge(
        {
            "record_kind": "f4_adjudication",
            "instance_ids": rehearsed_ids,
            "instance_set_digest": insp.instance_set_digest(rehearsed_ids),
            "decisions": {i: {"codes": [PASS_CODE]} for i in rehearsed_ids},
        },
        insp.mint_challenge(rehearsed_ids))

    class _Elsewhere:
        """An instance from some other set - which is what the sealed read returns."""

        def __init__(self, iid):
            self.corpus_instance_id = iid

    other = [_Elsewhere("atk_" + "c" * 12), _Elsewhere("atk_" + "d" * 12)]
    with pytest.raises(AdjudicationError):
        insp.ledger_for(record, other)


def test_nothing_is_kept_unless_keep_is_passed(tmp_path):
    """A rehearsal that litters is a rehearsal whose litter gets picked up later."""
    proc = _run("--count", "1")
    # It will refuse on EOF at the first prompt, which is fine - the assertion
    # is about what it left behind, and the refusal path is the one most likely
    # to leave something.
    assert "Nothing was kept" in proc.stdout or proc.returncode != 0, proc.stdout
    strays = list(ROOT.glob("rehearsal*")) + list(ROOT.glob("*.challenge.json"))
    assert not strays, "the rehearsal wrote into the repository: %s" % strays


def test_the_envelope_is_not_a_valid_adjudication_record(tmp_path):
    """`--keep` leaves something that will not load as a ruling.

    The nesting is the belt; the id-set derivation above is the braces. This
    asserts the belt: the top level is an envelope, so a file handed to
    `--adjudication` by a tired person at 1am does not even parse as the thing
    it would need to be.
    """
    from crucible.transfer.adjudication import PASS_CODE

    answers = chr(10).join([PASS_CODE, "A Rehearsing Operator", "ACCEPT", ""])
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--count", "1", "--keep", str(tmp_path)],
        cwd=str(ROOT), input=answers, capture_output=True, text=True,
        timeout=300)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]

    envelope = tmp_path / "rehearsal-envelope.json"
    assert envelope.is_file(), sorted(p.name for p in tmp_path.iterdir())
    doc = json.loads(envelope.read_text(encoding="utf-8"))
    assert doc.get("record_kind") is None, (
        "the envelope carries record_kind at the top level, so it looks like "
        "the thing it is standing in for")
    assert "REHEARSAL" in doc["artifact"]
    assert doc["record"]["record_kind"] == "f4_adjudication", (
        "the nested record is not the real shape, so the rehearsal taught "
        "something other than the real thing")


# ------------------------------------------------------ it rehearses the REAL path


def test_the_rehearsal_runs_the_real_adjudicate_entry_point():
    """A rehearsal against a mock teaches the mock.

    The value of this script is that `insp.adjudicate` runs its own self-checks
    - `load_adjudication` and `verify_post_read` against the record it just
    built - so a ruling that would be refused on the day is refused here
    instead, with the operator still at the keyboard.
    """
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    called = {getattr(n.func, "attr", None) for n in ast.walk(tree)
              if isinstance(n, ast.Call)}
    assert "adjudicate" in called, (
        "the rehearsal no longer calls the real entry point, so it is "
        "rehearsing something other than the review it stands in for")


def test_the_runbook_tells_the_operator_to_rehearse():
    """A rehearsal nobody is told about is a script, not a control.

    The runbook is the operator's only written account of the procedure, and it
    is where "nobody has walked this path" was recorded. If it does not name
    the rehearsal, the rehearsal does not exist on the day.
    """
    text = (ROOT / "docs" / "F4-DRIVE-RUNBOOK.md").read_text(encoding="utf-8")
    assert "rehearse-adjudication.py" in text, (
        "the runbook does not mention the rehearsal")
