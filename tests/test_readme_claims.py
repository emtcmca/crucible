"""README.md is the first file a judge opens. These tests are its ruler.

WHY THIS FILE EXISTS
--------------------------------------------------------------------------
Three separate overclaims were found in `README.md` on 2026-08-22, and all
three had the same shape: **a sentence that was true when it was typed and
had no way of learning that it had stopped being true.**

  1. "the benign pass rate NOW PERMANENTLY CARRIES a second figure" - describing
     `benign_passes_requiring_approval`, a field with NO PRODUCER anywhere in
     the codebase. Ruling 37 requires it; nothing computes it. The README
     announced the fix as shipped.
  2. A transcript captioned "Pasted from a real run" whose gate line read
     `gate : STAND-IN. No GCS, no IAM.` The gate was wired to `RealGate` on
     2026-08-22 and `campaign.gate_banner_lines` has emitted `REAL ...` ever
     since. The README's stated consequence - "`promote=` is a constant
     function returning true" - was not stale, it was INVERTED.
  3. The same transcript showed FIVE hash-lock rows while the banner prints
     SIX (`corpus_hash` landed 2026-08-22), and two of its five hash VALUES
     were the pre-reseal pair.

`crucible/replay/view.py::regression_upper_bound` is the house answer and it
has now been earned four times: it COMPUTES its figure from a constant and
stayed correct through a denominator change while four prose documents drifted.
A README cannot compute - it is prose by definition. So the next best thing is
what this file does: **pin every quotable claim in it to the code that would
have to change first**, so the failing test arrives before the judge does.

WHAT THIS FILE DELIBERATELY DOES NOT DO
--------------------------------------------------------------------------
It does not run the campaign. A test that shells out to
`python -m crucible.conductor.campaign` would take tens of seconds, would need
the ADK import, and would be skipped the first time it got slow. Instead it
calls the SAME FUNCTIONS the banner calls - `gate_banner_lines`, `LOCK_FIELDS`,
`load_hash_locks` - and asserts the README quotes what they return. If the
banner text moves, these fail. If a hash is re-frozen, these fail. That is the
whole design.

BOTH DIRECTIONS, EVERY TIME
--------------------------------------------------------------------------
A test that only checked "the false claim is gone" would pass on a README that
asserted NOTHING, which would destroy the strongest thing the project has to
say. So each claim here is pinned twice: the dead phrasing must be ABSENT, and
the honest claim that replaced it must be PRESENT. Deleting both fails.
"""

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
README = REPO / "README.md"
TEXT = README.read_text(encoding="utf-8")


def _transcript():
    """The offline-campaign banner block pasted into README section 5.

    Located by its own first line rather than by line number, because a line
    number in a test is the same fragile thing this file exists to remove.
    """
    start = TEXT.index("L5 CAMPAIGN  run_")
    end = TEXT.index("```", start)
    return TEXT[start:end]


# ---------------------------------------------------------------------------
# FINDING A - a feature that does not exist. Deleted, not softened.
# ---------------------------------------------------------------------------

def test_readme_does_not_claim_the_approval_masked_count_is_built():
    """`benign_passes_requiring_approval` HAS NO PRODUCER. It appears in
    `real_warden.py` in a docstring saying the return shape does NOT carry it,
    and in `test_real_warden.py` in a test asserting its ABSENCE. Ruling 37.1
    requires it permanently; the ruler was not in fact fixed. The README's
    "how we fixed our own ruler" paragraph announced a build that never
    happened, which is the exact failure mode the project is about."""
    for dead in ("now permanently carries a second figure",
                 "can never again be counted"):
        assert dead not in TEXT, (
            "README still announces the approval-masked count as shipped (%r). "
            "It has no producer - see test_the_ruler_is_still_unfixed below. A "
            "claim about a feature that does not exist gets DELETED." % dead)


def test_the_ruler_is_fixed_and_the_readme_must_not_walk_it_back():
    """INVERTED 2026-08-24, WHEN THE GAP CLOSED, and deliberately not deleted.

    This test used to assert the README kept SAYING the gap was open, and it
    carried an instruction for whoever closed it: promote the gap statement
    into a claim and delete the branch. The producer landed, the test fired
    exactly as designed, and the README was updated.

    Deleting it here would have been the wrong half of that instruction. The
    check still has to be able to fail, just in the other direction: if someone
    removes the producer while the README claims the fix shipped, the repo
    starts advertising an instrument it does not have - which is the precise
    failure the original test existed to prevent, only with the sign flipped.

    The producer test is structural: `real_warden.real_warden` is the ONLY
    thing that returns a benign report to the campaign, so if the key is not
    in its return value, nothing downstream can print it."""
    from crucible.conductor.real_warden import real_warden

    empty = {"envelope_version": 1, "hashed_payload": {"rules": []}}
    report = real_warden(empty)

    assert "benign_passes_requiring_approval" in report, (
        "THE PRODUCER IS GONE. `real_warden` no longer returns "
        "benign_passes_requiring_approval, and the README says the fix shipped "
        "on 2026-08-24. Restore the producer, or walk the README back to a "
        "stated gap. Do not leave the claim standing without the instrument.")

    assert "benign_passes_requiring_approval" in TEXT, (
        "name the field. A claim without its identifier cannot be checked by "
        "the next reader, and this one is now a claim rather than a gap.")
    assert "closed on 2026-08-24" in TEXT or "was closed" in TEXT, (
        "the producer exists but the README no longer says the fix landed. "
        "State it, with its date, so the claim carries a verification point.")
    for dead in ("Nothing computes that number today",
                 "it has not been closed"):
        assert dead not in TEXT, (
            "README still carries the pre-fix gap statement %r alongside the "
            "shipped producer. The two cannot both be true." % dead)


# ---------------------------------------------------------------------------
# FINDING B - the transcript. Pinned to the functions that print it.
# ---------------------------------------------------------------------------

def test_readme_gate_line_is_the_one_the_campaign_actually_prints():
    """DERIVED, not restated. `gate_banner_lines(live=False, ...)` is the sole
    producer of that banner row; this asserts the README quotes its stable
    head. When someone edits that function, this fails."""
    from crucible.conductor.campaign import gate_banner_lines

    line = gate_banner_lines(False, {"policy_store": "<anything>"})[0]
    head = line.split(". Policy store")[0]
    assert head in _transcript(), (
        "README's pasted banner does not carry the gate line the campaign "
        "emits offline.\n  campaign prints: %r\n  README does not contain it."
        % head)


def test_readme_does_not_carry_the_retired_stand_in_gate_line():
    """The dead literal, refused by name. It was published for long enough
    that a copy-paste from an old handoff could reintroduce it."""
    assert "gate         : STAND-IN" not in TEXT
    assert "`promote=` is a constant function returning true" not in TEXT, (
        "this was not stale, it was INVERTED: `campaign.py:27` records that "
        "`promote=lambda c, r: True` was REPLACED by RealGate on 2026-08-22.")


def test_the_gate_the_campaign_builds_is_the_real_one(tmp_path):
    """The claim above only stays honest while the wiring holds. This is the
    postcondition, asserted rather than assumed: `build_gate` returns a
    `RealGate`, so the README is entitled to say the gate is real code.

    `run_id` is uniquified from `tmp_path` because `build_gate` opens a real
    ledger row and the run table's primary key is the run id - a fixed literal
    here passes once and raises IntegrityError forever after, which is a test
    that fails for a reason having nothing to do with what it measures."""
    from crucible.conductor.campaign import build_gate
    from crucible.conductor.real_gate import RealGate

    gate, info = build_gate("run_readme_%s" % abs(hash(str(tmp_path))),
                            _locks(), live=False, store_root=str(tmp_path))
    assert isinstance(gate, RealGate)
    assert info["replaces"] == "promote=lambda c, r: True", (
        "build_gate no longer records what it replaced; README's paragraph 1 "
        "cites that string as the reason the stand-in claim is retired")


def _locks():
    from crucible.conductor.hashlocks import load_hash_locks
    from crucible.conductor.campaign import resolve_objective_set
    return load_hash_locks(resolve_objective_set())


def test_readme_transcript_shows_every_hash_lock_field_the_banner_prints():
    """SIX rows, and the six names come from `LOCK_FIELDS`, not from this
    file. The published transcript showed five - `corpus_hash`, the field that
    says WHICH SUITE every rate was measured against, was the missing one."""
    from crucible.conductor.hashlocks import LOCK_FIELDS

    block = _transcript()
    for name in LOCK_FIELDS:
        assert re.search(r"^\s+%s\s+[0-9a-f]{16}\s" % re.escape(name),
                         block, re.M), (
            "README's banner transcript has no row for %s. The banner prints "
            "one row per LOCK_FIELDS entry." % name)


def test_readme_transcript_hash_values_are_the_ones_in_force():
    """The stale-hash catcher.

    Two of the published transcript's five values were the pre-reseal
    `target_agent_hash` / `manifest_hash` pair. Nothing in the repository could
    notice, because a hash in prose is a string. This reads the README's rows
    and compares each against `load_hash_locks`, which reads the artifacts."""
    locks = _locks()
    block = _transcript()
    rows = dict(re.findall(r"^\s+([a-z_]+_hash)\s+([0-9a-f]{16})\s", block, re.M))
    assert rows, "no hash-lock rows parsed out of the README transcript"
    wrong = {n: (v, locks.values[n]) for n, v in rows.items()
             if n in locks.values and v != locks.values[n]}
    assert not wrong, (
        "README quotes hash values that are no longer in force "
        "(name: readme -> actual): %s" % wrong)


def test_readme_transcript_provenance_matches_what_the_locks_report():
    """FROZEN / IN_FORCE is the load-bearing half of a hash-lock row: a value
    with no dated freeze record does not evidence that the artifact was pinned
    BEFORE the first measurement. The published transcript showed
    `derived_schema_hash IN_FORCE` plus a `>>> 1 of 5 ... NO DATED FREEZE
    RECORD` warning; all six now load FROZEN and the warning is not printed."""
    locks = _locks()
    block = _transcript()
    rows = dict(re.findall(r"^\s+([a-z_]+_hash)\s+[0-9a-f]{16}\s+(\S+)", block, re.M))
    for name, kind in rows.items():
        assert kind == locks.provenance[name]["kind"], (
            "README shows %s as %s; it loads as %s"
            % (name, kind, locks.provenance[name]["kind"]))
    warned = "NO DATED FREEZE RECORD" in block
    assert warned == bool(locks.unfrozen), (
        "the transcript's unfrozen warning and the real lock state disagree: "
        "README %s the warning, locks report unfrozen=%s"
        % ("shows" if warned else "omits", locks.unfrozen or "NONE"))


def test_readme_does_not_still_report_the_float_bug_the_reader_rejects():
    """A DEFECT NOTE IS A CLAIM TOO, and it goes stale in the flattering
    direction's opposite: this one told a judge to expect a broken bundle that
    the campaign now writes correctly. `bundle` validates and the offline
    reader accepts, verified by the run of 2026-08-22."""
    assert "E_FLOAT at $:" not in TEXT, (
        "README still tells the reader the campaign's bundle is rejected by "
        "the replay viewer. The 2026-08-22 offline run prints 'OFFLINE "
        "READER: ACCEPTS. 17/17 integrity checks OK'.")


# ---------------------------------------------------------------------------
# The counts the README quotes, pinned to the modules that own them.
# ---------------------------------------------------------------------------

def test_readme_benign_denominators_match_the_corpus_constants():
    """26 / 14 appear in the README's prose. They moved once already (ruling
    43, 24->26 and 12->14) and four documents did not follow."""
    from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR

    assert "%d-fixture benign suite" % BENIGN_TOTAL in TEXT or \
           "%d benign" % BENIGN_TOTAL in TEXT
    assert str(NEAR_MISS_FLOOR) in TEXT


def test_readme_tool_count_matches_the_running_target():
    """8 tools, counted from the manifest the target actually builds."""
    from target.refund_agent.manifest import build_manifest

    n = len(build_manifest()["tools"])
    assert "**%d tools**" % n in TEXT, (
        "README's tool count disagrees with build_manifest(), which declares "
        "%d" % n)
