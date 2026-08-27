"""The ENFORCING branch of a gate decision, canonicalized.

WHY THIS FILE EXISTS. On 2026-08-27 a twenty-run live batch exited 0 twenty
times and produced twenty bundles that NO READER CAN OPEN. `_gate_decisions`
wrote

    "record_only_reason": record.g4_record_only_reason or None

and in ENFORCING mode there is no reason, so the key came out `null`.
Canonicalization restriction 5 - *an absent fact is an absent key* - refuses
`null` outright (`crucible/canon/canonical.py`:156-159), and
`crucible/replay/integrity.py::_check_canonical` canonicalizes the WHOLE
bundle. One empty string in one optional field made every figure in that batch
unquotable.

**Every prior batch ran in RECORD_ONLY, where that field always carries a
string.** The enforcing path had never been exercised end to end, and a branch
that never executes is indistinguishable from a branch that works. That is the
third time this shape has cost this repo something: the `CONVERGED` enum was
the first (`tests/test_c6_producer.py`:161) and G4 itself was the second.

WHAT IS ASSERTED, AND WHY BOTH HALVES ARE NEEDED
------------------------------------------------
The negative alone - "ENFORCING canonicalizes" - is satisfied by deleting the
key in both modes, which would throw away the one thing it exists to record.
So RECORD_ONLY is asserted in the same file, one test apart: the key must be
PRESENT and must carry the reason. Absent means enforcing; present means
scored-but-not-binding, and the difference is the whole point of the field.
"""

import json
import pathlib

import pytest

from crucible.canon import CanonicalizationError, canonicalize
from crucible.conductor import bundle as B
from crucible.conductor import closure as closuremod
from crucible.conductor import g4 as g4mod
from crucible.conductor.conductor import RoundRecord
from crucible.replay.integrity import verify_bundle

GOLDEN = (pathlib.Path(__file__).resolve().parents[1] / "contracts" /
          "golden" / "C6-evidence_bundle.valid.json")


def _enforcing_record(round_index=1, slice_name=g4mod.SLICE_BASELINE):
    """A round exactly as the 08-27 batch recorded one.

    Every G4 and closure field carries a real measurement - the gate ran, b and
    c were computed, the clause was found and closure was decided - and the two
    `record_only_reason` fields are `""` BECAUSE THE MODE IS ENFORCING. There
    is no reason to give when nothing was suppressed. `closure_code` is `None`
    for the same reason one level over: the code names which of the four
    UNEVALUABLE causes applied, and closure here was evaluated.

    That combination is not a corner case invented for a test. It is what 46 of
    the batch's gate decisions look like, counted off the bundles themselves.

    The slice defaults to `baseline` because that is what the batch ran, and
    the batch is what this file reproduces. `g4_slice` is NOT a `RoundRecord`
    field - `real_gate.py`:931 sets it on the instance - so it is assigned the
    same way here rather than being invented as a constructor argument the
    producer would never see.
    """
    record = RoundRecord(
        round_index=round_index,
        gate_decision="PROMOTE",
        benign_passed=26,
        benign_total=26,
        newly_blocked_b=5,
        newly_breached_c=0,
        g4_paired_n=50,
        g4_unpairable=0,
        g4_mode=g4mod.ENFORCING,
        g4_record_only_reason="",
        closure_closed=True,
        closure_code=None,
        closure_clause_id="c_destination_smuggling",
        closure_episode_still_breaches=False,
        closure_mode=closuremod.ENFORCING,
        closure_record_only_reason="",
    )
    record.g4_slice = slice_name
    return record


def _canonical_defects(bundle):
    report = verify_bundle(bundle)
    return [d for d in report.defects if d.code == "E_NOT_CANONICALIZABLE"]


# ---------------------------------------------------------------------------
# 1. THE DEFECT ITSELF, at the producer.
# ---------------------------------------------------------------------------

def test_an_ENFORCING_gate_decision_canonicalizes():
    """RED before the fix, with `E_NULL` at
    `$[0].criteria.attack_reduction.record_only_reason`.

    Straight at `_gate_decisions` rather than through a campaign, because the
    campaign that produced the broken batch needed live models and twenty
    minutes to reach this branch. The producer is where the `null` is written
    and it is the smallest thing that can prove it.
    """
    decisions = B._gate_decisions([_enforcing_record()], gate=None,
                                  run_id="run_test_enforcing")
    assert decisions, "the fixture round must reach a gate decision"
    try:
        canonicalize(decisions)
    except CanonicalizationError as exc:
        pytest.fail(
            "an ENFORCING gate decision is not canonicalizable: %s at %s. "
            "Restriction 5 - an absent fact is an ABSENT KEY, not a null one."
            % (exc, getattr(exc, "path", "$")))


def test_an_ENFORCING_gate_decision_omits_the_keys_it_has_no_value_for():
    """The shape of the fix, pinned so a later edit cannot reintroduce `null`.

    Asserting only "it canonicalizes" would also be satisfied by writing `""`
    or `"n/a"`, and an empty string is the value ruling-style guidance calls
    the most dangerous one: it satisfies "the key exists" and carries no
    information. The key must be GONE.
    """
    decisions = B._gate_decisions([_enforcing_record()], gate=None,
                                  run_id="run_test_enforcing")
    g4 = decisions[0]["criteria"]["attack_reduction"]
    closure = decisions[0]["criteria"]["breach_closure"]

    assert "record_only_reason" not in g4
    assert "record_only_reason" not in closure
    # THE THIRD SITE, and it was in none of the three greps that found this
    # bug. `closure_code` is None on a closure that was EVALUATED, so it went
    # null on 28 of the batch's decisions - a second broken key hiding behind
    # the first, because the reader stops at the first defect it hits.
    assert "code" not in closure

    assert g4["mode"] == g4mod.ENFORCING and g4["enforced"] is True
    assert closure["mode"] == closuremod.ENFORCING
    assert closure["enforced"] is True
    assert closure["closed"] is True


# ---------------------------------------------------------------------------
# 1b. THE SAME DEFECT ON THE DEFAULT PATH, WHICH THE BATCH NEVER TOOK.
#     The batch ran `--g4-slice baseline`, so `slice_is_blind_to` came out a
#     string. On `run` - `g4.DEFAULT_SLICE`, what every campaign gets when
#     nobody passes the flag - the same expression yields `None`. A second
#     unreadable bundle was one omitted command-line flag away, and the reader
#     would never have reported it because it stops at the first defect and
#     `record_only_reason` sorts ahead of `slice_is_blind_to`.
# ---------------------------------------------------------------------------

def test_the_DEFAULT_slice_also_canonicalizes():
    decisions = B._gate_decisions(
        [_enforcing_record(slice_name=g4mod.DEFAULT_SLICE)],
        gate=None, run_id="run_test_default_slice")
    g4 = decisions[0]["criteria"]["attack_reduction"]
    assert g4["slice"] == g4mod.DEFAULT_SLICE
    assert "slice_is_blind_to" not in g4, (
        "the run slice is blind to nothing that needs naming; an absent fact "
        "is an absent key, not a null one")
    canonicalize(decisions)


def test_a_round_the_gate_never_stamped_a_slice_onto_canonicalizes():
    """`g4_slice` is set by `real_gate.py`:931, not by the dataclass, so a
    gate-deciding round that predates it - or one from any gate that does not
    set it - has no attribute at all. `getattr(..., None)` then wrote `null`."""
    record = _enforcing_record()
    del record.g4_slice
    decisions = B._gate_decisions([record], gate=None, run_id="run_test_noslice")
    g4 = decisions[0]["criteria"]["attack_reduction"]
    assert "slice" not in g4 and "slice_is_blind_to" not in g4
    canonicalize(decisions)


# ---------------------------------------------------------------------------
# 1c. A ROUND THAT REACHED A DECISION WITHOUT G4 OR CLOSURE BEING SCORED.
#     `RoundRecord`:280-338 declares nine of these fields `Optional` and
#     documents `None` as "NOT EVALUATED, which is not b = 0". Every one of
#     them was written into the bundle unguarded.
# ---------------------------------------------------------------------------

def test_an_UNSCORED_round_canonicalizes_and_still_says_it_was_unscored():
    record = RoundRecord(round_index=1, gate_decision="HALT",
                         benign_passed=26, benign_total=26)
    decisions = B._gate_decisions([record], gate=None, run_id="run_test_unscored")
    g4 = decisions[0]["criteria"]["attack_reduction"]
    closure = decisions[0]["criteria"]["breach_closure"]
    # THE ABSENCE STILL HAS TO BE READABLE AS AN ABSENCE. `evaluated: false` is
    # the field that says so, and it is why dropping the null keys loses
    # nothing: the statement "G4 did not run" survives in a key that is a bool
    # and can never be null.
    assert g4["evaluated"] is False and closure["evaluated"] is False
    for gone in ("newly_blocked_b", "newly_breached_c", "paired_n",
                 "unpairable", "mode"):
        assert gone not in g4, gone
    for gone in ("closed", "code", "originating_clause_id",
                 "episode_still_breaches", "mode"):
        assert gone not in closure, gone
    canonicalize(decisions)


def test_a_round_with_no_benign_numbers_canonicalizes():
    """`benign_passed` / `benign_total` are `Optional[int]`
    (`conductor.py`:290-291) and `criteria["benign_floor"]` read them raw."""
    record = RoundRecord(round_index=1, gate_decision="HALT")
    decisions = B._gate_decisions([record], gate=None, run_id="run_test_nofloor")
    floor = decisions[0]["criteria"]["benign_floor"]
    assert "passed" not in floor and "total" not in floor
    canonicalize(decisions)


# ---------------------------------------------------------------------------
# 2. THE POSITIVE. Omitting the reason in RECORD_ONLY would lose the thing the
#    field exists to record, so the fix has to be conditional and not a delete.
# ---------------------------------------------------------------------------

def test_RECORD_ONLY_still_carries_the_reason_it_was_not_enforced():
    reason = "baseline slice not yet frozen for this corpus"
    record = _enforcing_record()
    record.g4_mode = g4mod.RECORD_ONLY
    record.g4_record_only_reason = reason
    record.closure_mode = closuremod.RECORD_ONLY
    record.closure_record_only_reason = reason

    decisions = B._gate_decisions([record], gate=None, run_id="run_test_ro")
    g4 = decisions[0]["criteria"]["attack_reduction"]
    closure = decisions[0]["criteria"]["breach_closure"]

    assert g4["record_only_reason"] == reason
    assert closure["record_only_reason"] == reason
    assert g4["enforced"] is False and closure["enforced"] is False
    canonicalize(decisions)


def test_an_UNEVALUABLE_closure_still_names_which_cause():
    """The mirror of the `code` omission above. Absent means EVALUATED; when
    closure could not be evaluated the code is the only thing that says which
    of the four causes applied, and dropping it would read as success."""
    record = _enforcing_record()
    record.closure_closed = None
    record.closure_code = "E_NO_ORIGINATING_CLAUSE"
    record.closure_clause_id = None
    record.closure_episode_still_breaches = None

    decisions = B._gate_decisions([record], gate=None, run_id="run_test_unev")
    closure = decisions[0]["criteria"]["breach_closure"]
    assert closure["code"] == "E_NO_ORIGINATING_CLAUSE"
    assert closure["evaluated"] is False
    canonicalize(decisions)


# ---------------------------------------------------------------------------
# 3. THROUGH THE OFFLINE READER, on a whole bundle. The producer test above is
#    the tight one; this is the one that reproduces what the batch actually
#    failed, because `_check_canonical` canonicalizes the ENTIRE document.
# ---------------------------------------------------------------------------

def test_the_run_summarys_gate_block_carries_no_null_in_either_mode(tmp_path):
    """`campaign.build_gate` wrote `record_only_reason: null` too.

    That dict lands in the run SUMMARY, not in the canonicalized bundle, so it
    was not what broke the batch. It is the same shape, and the shape is what
    has to stop - the summary is one copy-paste away from being folded into a
    hashed artifact, and this is the seam where that would be found late.
    """
    from crucible.conductor.campaign import build_gate
    from crucible.conductor.hashlocks import load_hash_locks
    from crucible.conductor.real_tripwire import resolve_objective_set

    run_id = "run_20260827_000000_5100ff"
    _gate, info = build_gate(run_id, load_hash_locks(resolve_objective_set()),
                             live=False, store_root=str(tmp_path / "g"))
    assert info["g4"]["enforced"] is True
    assert "record_only_reason" not in info["g4"]
    assert "record_only_reason" not in info["closure"]
    canonicalize(info["g4"])
    canonicalize(info["closure"])

    _gate2, info2 = build_gate(run_id + "x", load_hash_locks(
        resolve_objective_set()), live=False, store_root=str(tmp_path / "h"),
        g4_mode=g4mod.RECORD_ONLY, g4_record_only_reason="observing only",
        closure_mode=closuremod.RECORD_ONLY,
        closure_record_only_reason="observing only")
    assert info2["g4"]["record_only_reason"] == "observing only"
    assert info2["closure"]["record_only_reason"] == "observing only"


def test_a_bundle_carrying_an_ENFORCING_gate_decision_passes_the_offline_reader():
    """On the committed golden fixture, not on a live run.

    `contracts/golden/C6-evidence_bundle.valid.json` is the artifact
    `contract-check` already validates, so the mutation lands on something that
    is checked in - and a golden bundle plus one enforcing gate decision is
    exactly the document twenty live runs wrote and no reader could open.

    Only `E_NOT_CANONICALIZABLE` is asserted on. The golden fixture is not this
    test's subject and its other rows are somebody else's contract.
    """
    bundle = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert not _canonical_defects(bundle), (
        "the golden fixture must start canonicalizable or this test proves "
        "nothing about the mutation")

    bundle["gate_decisions"] = B._gate_decisions(
        [_enforcing_record(round_index=bundle["gate_decisions"][0]
                           ["round_index"])],
        gate=None, run_id="run_test_enforcing")

    assert B.validate_bundle(bundle) == [], (
        "an enforcing gate decision must still satisfy C6")
    defects = _canonical_defects(bundle)
    assert defects == [], "\n".join(
        "%s %s: %s" % (d.code, d.where, d.detail) for d in defects)
