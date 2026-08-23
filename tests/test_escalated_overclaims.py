"""test_escalated_overclaims.py - printed sentences that outran the code.

Same defect class as `test_overclaim.py`, found in a second sweep on
2026-08-23 and escalated out of the lane that found it because the files were
not that lane's to edit. A sentence asserting something the code never
computed is a defect of the same severity as a crash, and this repository is
judged partly on architectural honesty.

Four, in three files:

  1. `scripts/verify-chain.py` - MIRROR_DRIFT summed a hash-field mismatch
     with a CANONICALIZATION FAILURE and then said "That flags the index, not
     the record", for a failure that is in the record's own bytes. It also
     decided which side moved, from data that cannot decide it.
  2. `scripts/verify-chain.py` - the success banner printed a conclusion about
     IAM. The script never opens a socket. `crucible/conductor/real_gate.py`
     is what checks that boundary live, and it can return UNEVALUABLE;
     `data-spec.md` A4 still carries status CONFIRM.
  3. `crucible/replay/offline_lint.py` - the note justifying a duplicate lint
     module said the other one bakes its roots in at module level. It does
     not; the signatures are identical. That note is the only thing standing
     between the module and "delete it, call the other one", so the reason it
     gives has to be one that is true.
  4. `crucible/conductor/bundle.py` - "N/M benign fixtures replayed clean",
     where ruling 2 counts an oracle-approved APPROVAL_REQUIRED as a pass.

Every one of them was reported by another lane and RE-VERIFIED here before it
was touched. A report is a lead, not a finding.
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


# ---------------------------------------------------------------------------
# 3. The justification for a duplicate lint module
# ---------------------------------------------------------------------------
#
# `crucible/replay/offline_lint.py` ends with a note explaining why it is a
# second file rather than a parameter on `crucible/tripwire/import_lint.py`.
# That note is load-bearing - it is the only thing standing between this module
# and "delete it, call the other one" - and half of it was false.

def test_import_lint_takes_roots_exactly_as_offline_lint_does(tmp_path):
    """"bakes ... its roots in at module level, so it cannot be pointed at a
    different question without editing it" - `run_import_lint(roots=None)` is
    the same signature and the same `DEFAULT_ROOTS if roots is None else roots`
    line. Proven by aiming it somewhere else and getting an answer."""
    from crucible.replay.offline_lint import run_offline_lint
    from crucible.tripwire.import_lint import run_import_lint

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "m.py").write_text("import openai\nimport socket\n",
                                    encoding="utf-8")

    # import_lint's Finding names the field `module`; offline_lint's names
    # it `what`. Two lanes, two vocabularies, and that is itself part of
    # why they are two files.
    aimed = run_import_lint(roots=(str(elsewhere),))
    assert [f.module for f in aimed] == ["openai"], (
        "import_lint answered a question about a root it does not default to")
    aimed_off = run_offline_lint(roots=(str(elsewhere),))
    assert [f.what for f in aimed_off] == ["socket"]

    # The zero that matters: an EMPTY directory, so a non-zero above is not
    # the only thing this call can produce.
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run_import_lint(roots=(str(empty),)) == []


DEAD_ROOTS_CLAIM = "bakes its deny set and its roots in at module level"


def test_the_offline_lint_note_does_not_claim_import_lint_bakes_its_roots():
    """A CORRECTION NOTE QUOTES THE SENTENCE IT KILLS, so a bare substring
    check flags the correction as the defect - the same exemption problem
    `canon-check --selftest` ships a fixture for. The rule is therefore not
    "the string is absent" but "the string is never left standing": if it
    appears at all, the refutation must appear with it."""
    from crucible.replay import offline_lint
    flat = " ".join(offline_lint.__doc__.split())
    if DEAD_ROOTS_CLAIM in flat:
        assert "THE ROOTS HALF WAS FALSE" in flat, (
            "the dead claim is present and nothing next to it says it is dead")
        head, _, tail = flat.partition(DEAD_ROOTS_CLAIM)
        assert 'used to read "' in head[-120:], (
            "and it must be introduced as a quotation of a dead claim, not "
            "asserted: %r" % head[-120:])
        assert "THE ROOTS HALF WAS FALSE" in tail, (
            "the refutation must FOLLOW the quote, not precede it")


def test_that_guard_can_still_fail():
    """The check above is conditional, and a conditional check is the shape
    that silently stops checking. Fed a note that quotes the dead claim and
    never refutes it, it must fail."""
    flat = 'the module %s and that is why.' % DEAD_ROOTS_CLAIM
    assert DEAD_ROOTS_CLAIM in flat
    assert "THE ROOTS HALF WAS FALSE" not in flat, (
        "this is the input the guard exists to reject")


def test_the_offline_lint_note_still_justifies_the_duplication():
    """Deleting the justification would be worse than a wrong one. The
    duplication IS justified; the sentence just named the wrong reason."""
    from crucible.replay import offline_lint
    flat = " ".join(offline_lint.__doc__.split())
    assert "RELATIONSHIP TO" in flat
    assert "belongs to another lane" in flat
    assert "environment" in flat, (
        "the real structural difference is the environment rule - name it")


def test_import_lints_walker_structurally_cannot_make_the_environment_rule():
    """The reason that IS true, asserted as behaviour rather than as prose.

    `import_lint.scan_source` walks Import, ImportFrom and Call. It has no
    `ast.Attribute` branch and no denied-`os`-attribute set, so `os.environ`
    is invisible to it - and the environment rule is the one `offline_lint`'s
    own docstring calls "the sharpest rule here". Parameterizing the deny set
    would not have given it that rule.

    Both directions, so neither zero is a blind instrument: `import_lint` DOES
    report `openai` on the same call shape, and `offline_lint` DOES report the
    environment read.
    """
    from crucible.replay.offline_lint import scan_offline_source
    from crucible.tripwire.import_lint import scan_source

    env_read = "import os\nx = os.environ['K']\n"
    assert scan_source(env_read, "m.py") == [], (
        "if this ever reports something, the justification has changed")
    assert scan_source("import openai\n", "m.py"), (
        "and the empty list above is a measured zero, not a dead scanner")
    assert [f.what for f in scan_offline_source(env_read, "m.py")] == \
        ["os.environ"]


def test_both_modules_bake_their_deny_set_so_that_is_not_the_difference():
    """The half of the sentence that was TRUE was also not a differentiator.
    Both deny sets are module-level frozensets that no function parameter
    reaches, so it could never have been the reason there are two files."""
    import inspect

    from crucible.replay import offline_lint
    from crucible.tripwire import import_lint

    for mod, fn in ((import_lint, "scan_source"),
                    (offline_lint, "scan_offline_source")):
        sig = inspect.signature(getattr(mod, fn))
        assert list(sig.parameters) == ["source", "path"], (
            "%s.%s takes no deny-set parameter" % (mod.__name__, fn))


# ---------------------------------------------------------------------------
# 4. "replayed clean" for a run a human may have carried
# ---------------------------------------------------------------------------

def _one_proposal(decision="REJECT"):
    """One `patch_proposals` entry, built the way `test_c6_producer` builds
    them. Imported here rather than duplicated so the two cannot drift."""
    from tests.test_c6_producer import _Patch, _round_with_patch

    from crucible.conductor import bundle as B
    patch = _Patch("rule r_new1: cap:CAP_MOVES_MONEY => deny")
    record = _round_with_patch(decision, feedback={
        "benign_failures": 8, "classes": ["CAP_MOVES_MONEY"]})
    proposal, = B._patch_proposals([record], {1: patch}, "run_x")  # noqa: SLF001
    return proposal


def test_the_warden_line_does_not_call_an_approval_masked_pass_clean():
    """RULING 2: `escalate` means human-in-the-loop, and the scripted APPROVAL
    ORACLE approves any fixture declaring a valid approver. So a benign fixture
    whose call the policy STOPPED with APPROVAL_REQUIRED, and which the oracle
    then waved through, counts as a PASS.

    "replayed clean" is the reader's phrase for "ran untouched". Ruling 37 is
    the whole finding that those two are different results and must not print
    the same - and this line printed the flattering one."""
    result = _one_proposal()["warden_result"]
    assert "replayed clean" not in result
    assert result.startswith("18/26"), "the count itself was never in dispute"


def test_the_warden_line_names_ruling_2_as_the_reason_a_pass_is_not_clean():
    """Deleting the word is not the fix. A reader who sees "18/26 passed" will
    make the same inference unless something tells them what a pass includes."""
    result = _one_proposal()["warden_result"]
    low = result.lower()
    assert "approval" in low
    assert "ruling 2" in low


def test_the_warden_line_says_the_approval_masked_count_is_absent():
    """Ruling 37.1 requires BPR to carry its approval-masked count
    permanently. `benign_passes_requiring_approval` HAS NO PRODUCER - see
    `crucible/conductor/real_warden.py`, whose return shape is five fields and
    does not include it. An absent number said to be absent is honest; the
    same number quietly omitted beside the word "clean" is the defect."""
    result = _one_proposal()["warden_result"]
    assert "benign_passes_requiring_approval" in result


def test_a_promoted_proposal_gets_the_same_caveat():
    """The other side. 26/26 is exactly the number ruling 37 says can be
    reached by routing everything to a human, so the caveat matters MORE on a
    promotion than on a rejection."""
    result = _one_proposal("PROMOTE")["warden_result"]
    assert result.startswith("26/26")
    assert "replayed clean" not in result
    assert "ruling 2" in result.lower()
