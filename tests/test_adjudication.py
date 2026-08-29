"""The F4 validity adjudication is a human ledger, not a classifier.

WHY THIS FILE EXISTS.

`docs/proof/f4-unseal-preregistration-2026-08-25.md` section 2 fixes two validity
criteria before the sealed family is read. Both are written in semantic language
- "refers to", "resolvable against", "plausibly cause" - and code cannot honestly
infer any of it. So `crucible/transfer/adjudication.py` records a named human's
per-instance ruling and refuses to produce a count without one.

Every test below is a control over a way that refusal could be hollow: a ledger
that counts an undecided instance, a code edited after signature, a count taken
from the producer instead of derived, an adjudication assembled from a structure
that already carries the verdicts. Each was run against a deliberately broken
copy of the module and observed to FAIL before being kept - a control nobody
tried to break is not a control, and this project has eleven recorded instances
of a check that passes while measuring nothing.

EVERY FIXTURE HERE IS INVENTED. The ids are made-up twelve-hex strings. Nothing
in this file was read from `corpus/sealed/`, from the seal worktree, or from the
holdout bucket, and nothing in the module under test can accept instance content
even if a caller offers it.
"""

import dataclasses

import pytest

from crucible.cartographer.ratify import _NOT_A_HUMAN as _RATIFY_NOT_A_HUMAN
from crucible.transfer.adjudication import (
    CONTRACT_VERSION,
    NOTE_MAX_CHARS,
    PASS_CODE,
    RECORD_KIND,
    REASON_CODES,
    V1_CODES,
    V2_CODES,
    AdjudicationError,
    AdjudicationLedger,
    assert_no_outcome_fields,
    build_adjudication,
    decisions_digest,
    instance_set_digest,
    load_adjudication,
)

HUMAN = "Eric Tetzlaff"
WHEN = "2026-08-29"

# Invented ids. Twelve hex characters each, which is the whole shape the module
# accepts - it cannot carry a description of an attack, which is the point.
A = "atk_0123456789ab"
B = "atk_1122334455aa"
C = "atk_aabbccddeeff"
D = "atk_deadbeef0001"


def _decisions():
    """One pass, one V1 failure, one V2 failure, one that fails both."""
    return {
        A: {"codes": [PASS_CODE]},
        B: {"codes": ["V1_ORPHANED_TURN"], "note": "no order, no amount"},
        C: {"codes": ["V2_NO_CLAUSE_REACHABLE"]},
        D: {"codes": ["V1_NO_RESOLVABLE_ENTITY", "V2_NO_TOOL_REACHABLE"]},
    }


def _build(**overrides):
    kwargs = {
        "adjudicated_by": HUMAN,
        "adjudicated_on": WHEN,
        "instance_ids": [A, B, C, D],
        "decisions": _decisions(),
    }
    kwargs.update(overrides)
    return build_adjudication(**kwargs)


# ---------------------------------------------------------------------------
# A named human, refused if it is a component
# ---------------------------------------------------------------------------

def test_an_adjudication_needs_a_named_human():
    with pytest.raises(AdjudicationError) as e:
        _build(adjudicated_by="   ")
    assert e.value.code == "E_NO_ADJUDICATOR"


@pytest.mark.parametrize("name", [
    "cartographer", "armorer", "coroner", "gate", "tripwire",
    "crucible-sealed-eval", "Runner", "CLAUDE", "sealed eval", "target_agent",
])
def test_a_component_cannot_adjudicate_the_fixtures_it_is_measured_over(name):
    with pytest.raises(AdjudicationError) as e:
        _build(adjudicated_by=name)
    assert e.value.code == "E_SELF_APPROVAL"


def test_the_component_list_is_reused_from_ratify_and_never_diverges():
    """Anti-drift control, not a tautology.

    The module imports ratify's list and extends it. If someone replaces the
    import with a hand-copied literal, the two lists can drift the moment ratify
    learns a new component name - and the copy that goes stale is the one nobody
    is editing. This asserts the containment the import guarantees.
    """
    from crucible.transfer import adjudication

    assert _RATIFY_NOT_A_HUMAN <= adjudication._NOT_A_HUMAN
    # And the extension is real: transfer introduces identities ratify never saw.
    assert "crucible_sealed_eval" in adjudication._NOT_A_HUMAN
    assert "crucible_sealed_eval" not in _RATIFY_NOT_A_HUMAN


def test_a_record_must_say_when_it_was_made():
    with pytest.raises(AdjudicationError) as e:
        _build(adjudicated_on="")
    assert e.value.code == "E_NO_ADJUDICATION_DATE"


# ---------------------------------------------------------------------------
# Every instance decided, or the ledger is incomplete
# ---------------------------------------------------------------------------

def test_an_undecided_instance_refuses_the_whole_ledger_and_is_named():
    decisions = _decisions()
    del decisions[C]
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_UNADJUDICATED_INSTANCE"
    assert C in str(e.value)
    # And only the undecided one is named - a message listing everything is a
    # message nobody reads.
    assert A not in str(e.value)


def test_every_undecided_instance_is_named_not_just_the_first():
    decisions = _decisions()
    del decisions[B]
    del decisions[C]
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert B in str(e.value) and C in str(e.value)


def test_a_decision_for_an_instance_outside_the_set_is_refused():
    decisions = _decisions()
    decisions["atk_ffffffffffff"] = {"codes": [PASS_CODE]}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_DECISION_FOR_UNKNOWN_INSTANCE"


def test_an_empty_instance_set_is_refused():
    with pytest.raises(AdjudicationError) as e:
        _build(instance_ids=[], decisions={})
    assert e.value.code == "E_NO_INSTANCE_SET"


# ---------------------------------------------------------------------------
# The closed reason vocabulary
# ---------------------------------------------------------------------------

def test_the_vocabulary_is_closed_and_has_one_pass_code():
    assert REASON_CODES == (PASS_CODE,) + V1_CODES + V2_CODES
    assert len(set(REASON_CODES)) == len(REASON_CODES)
    assert not set(V1_CODES) & set(V2_CODES)


def test_a_code_outside_the_vocabulary_is_refused():
    decisions = _decisions()
    decisions[C] = {"codes": ["V3_LOOKED_WRONG"]}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_UNKNOWN_CODE"


def test_free_text_cannot_be_smuggled_in_as_a_code():
    decisions = _decisions()
    decisions[C] = {"codes": ["the instruction asks for a refund to a new card"]}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_UNKNOWN_CODE"


def test_a_decision_with_no_code_is_an_undecided_instance():
    decisions = _decisions()
    decisions[C] = {"codes": []}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_NO_CODE"


def test_a_bare_string_is_not_a_code_list():
    """`{"codes": "V_SCOREABLE"}` iterates into characters if nobody checks."""
    decisions = _decisions()
    decisions[C] = {"codes": PASS_CODE}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_CODES_NOT_A_SEQUENCE"


def test_a_pass_beside_a_failure_is_two_rulings_recorded_as_one():
    decisions = _decisions()
    decisions[C] = {"codes": [PASS_CODE, "V1_ORPHANED_TURN"]}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_PASS_MIXED_WITH_FAILURE"


def test_a_repeated_code_is_refused():
    decisions = _decisions()
    decisions[C] = {"codes": ["V1_ORPHANED_TURN", "V1_ORPHANED_TURN"]}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_DUPLICATE_CODE"


def test_a_decision_holds_codes_and_a_note_and_nothing_else():
    decisions = _decisions()
    decisions[C] = {"codes": [PASS_CODE], "instruction": "close it out"}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_UNKNOWN_DECISION_FIELD"
    assert "instruction" in str(e.value)


# ---------------------------------------------------------------------------
# The note is never load-bearing and never reaches a published record
# ---------------------------------------------------------------------------

def test_a_note_never_reaches_the_record():
    record = _build()
    assert record["decisions"][B] == {"codes": ["V1_ORPHANED_TURN"]}
    assert "note" not in record["decisions"][B]


def test_the_note_is_outside_the_digest_so_a_typo_fix_does_not_break_the_record():
    decisions = _decisions()
    first = _build(decisions=decisions)
    decisions[B]["note"] = "rewritten entirely, same ruling"
    second = _build(decisions=decisions)
    assert first["decisions_digest"] == second["decisions_digest"]
    assert first == second


def test_a_note_is_bounded_because_the_bound_is_the_seal():
    decisions = _decisions()
    decisions[B]["note"] = "x" * (NOTE_MAX_CHARS + 1)
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_NOTE_TOO_LONG"


def test_the_record_carries_no_free_text_field_at_all():
    """A published record describing sealed instances has nowhere to write prose.

    `ratify.py` has a record-level `notes`. This deliberately does not, and the
    control is a closed key set rather than a paragraph saying so.
    """
    record = _build()
    assert set(record) == {
        "record_kind", "contract_version", "criterion_source",
        "adjudicated_by", "adjudicated_on", "instance_count", "instance_ids",
        "instance_set_digest", "decisions_digest", "decisions", "counts",
        "scoreable_ids",
    }
    for decision in record["decisions"].values():
        assert set(decision) == {"codes"}


# ---------------------------------------------------------------------------
# Ids are opaque. Instance CONTENT never enters this module.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "F4-05-destination-smuggling",
    "atk_0123456789ab-refund-to-new-card",
    "atk_0123456789AB",
    "atk_0123456789a",
    "gs://crucible-sealed-x7/atk_0123456789ab.json",
    123,
    None,
])
def test_only_opaque_instance_ids_are_accepted(bad):
    with pytest.raises(AdjudicationError) as e:
        _build(instance_ids=[A, bad], decisions={A: {"codes": [PASS_CODE]}})
    assert e.value.code in ("E_NOT_AN_INSTANCE_ID",)


def test_a_repeated_instance_id_would_inflate_every_denominator():
    with pytest.raises(AdjudicationError) as e:
        _build(instance_ids=[A, B, A], decisions={
            A: {"codes": [PASS_CODE]}, B: {"codes": [PASS_CODE]}})
    assert e.value.code == "E_DUPLICATE_INSTANCE_ID"


def test_the_module_names_no_sealed_location():
    """Structural control on the source itself.

    The module must be able to run from opaque ids alone. If it ever grows a
    path to the sealed corpus, the worktree or the holdout bucket, it has stopped
    being blind and this fails.
    """
    import inspect

    from crucible.transfer import adjudication

    source = inspect.getsource(adjudication)
    for forbidden in ("corpus/sealed", "crucible-wt-SEAL", "gs://",
                      "crucible-sealed-x7", "gcloud", "storage.Client"):
        assert forbidden not in source, forbidden


# ---------------------------------------------------------------------------
# Counts are derived, never supplied
# ---------------------------------------------------------------------------

def test_counts_are_derived_from_the_decisions():
    record = _build()
    assert record["counts"] == {
        "adjudicated": 4,
        "structurally_scoreable": 1,
        "failing_v1": 2,
        "failing_v2": 2,
        "failing_v1_or_v2": 3,
    }


def test_an_instance_failing_both_is_counted_in_both_parts_and_once_in_the_union():
    """The union is the number the outcome table asks for, and it is not the sum."""
    record = _build()
    counts = record["counts"]
    assert counts["failing_v1"] + counts["failing_v2"] == 4
    assert counts["failing_v1_or_v2"] == 3
    assert counts["structurally_scoreable"] + counts["failing_v1_or_v2"] == 4


def test_the_scoreable_set_is_derived_and_is_what_a_run_may_score_over():
    ledger = load_adjudication(_build(), [A, B, C, D])
    assert ledger.scoreable_ids == (A,)
    assert ledger.v1_failure_ids == (B, D)
    assert ledger.v2_failure_ids == (C, D)
    assert ledger.v1_failures == 2
    assert ledger.v2_failures == 2
    assert ledger.failing_v1_or_v2 == 3


def test_a_supplied_count_is_a_cross_check_that_raises_on_disagreement():
    with pytest.raises(AdjudicationError) as e:
        _build(expected_counts={"structurally_scoreable": 4})
    assert e.value.code == "E_COUNT_DISAGREEMENT"
    assert "structurally_scoreable" in str(e.value)


def test_a_supplied_count_that_agrees_passes():
    record = _build(expected_counts={"structurally_scoreable": 1,
                                     "failing_v1_or_v2": 3})
    assert record["counts"]["failing_v1_or_v2"] == 3


def test_a_count_this_ledger_does_not_derive_is_refused():
    with pytest.raises(AdjudicationError) as e:
        _build(expected_counts={"breached_at_v0": 3})
    # The outcome guard fires first on this one, which is the stronger refusal.
    assert e.value.code in ("E_UNKNOWN_COUNT", "E_OUTCOME_LEAKED")


def test_an_unrecognised_count_name_is_refused():
    with pytest.raises(AdjudicationError) as e:
        _build(expected_counts={"structurally_scorable": 1})
    assert e.value.code == "E_UNKNOWN_COUNT"


# ---------------------------------------------------------------------------
# Two digests, both bound
# ---------------------------------------------------------------------------

def test_the_instance_set_digest_moves_when_the_set_moves():
    assert instance_set_digest([A, B]) != instance_set_digest([A, B, C])


def test_the_instance_set_digest_is_order_independent():
    assert instance_set_digest([A, B, C]) == instance_set_digest([C, A, B])


def test_the_decisions_digest_is_order_independent_within_and_across_decisions():
    one = {A: (PASS_CODE,), D: ("V1_ORPHANED_TURN", "V2_NO_TOOL_REACHABLE")}
    two = {D: ("V2_NO_TOOL_REACHABLE", "V1_ORPHANED_TURN"), A: (PASS_CODE,)}
    assert decisions_digest(one) == decisions_digest(two)


def test_the_decisions_digest_moves_when_a_code_moves():
    one = {A: (PASS_CODE,)}
    two = {A: ("V1_ORPHANED_TURN",)}
    assert decisions_digest(one) != decisions_digest(two)


def test_a_record_signed_over_a_different_instance_set_is_refused():
    record = _build()
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C])
    assert e.value.code in ("E_UNADJUDICATED_INSTANCE",
                            "E_INSTANCE_SET_DIGEST_MISMATCH")


def test_an_instance_added_to_the_set_after_signing_is_caught():
    record = _build()
    record["instance_ids"].append("atk_000000000001")
    record["decisions"]["atk_000000000001"] = {"codes": [PASS_CODE]}
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D, "atk_000000000001"])
    assert e.value.code == "E_INSTANCE_SET_DIGEST_MISMATCH"


def test_a_record_with_no_decisions_digest_fails_closed():
    """Absence is not consent. An optional check is one you disable by deletion."""
    record = _build()
    del record["decisions_digest"]
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_DECISIONS_DIGEST_MISSING"


def test_a_code_edited_after_signature_is_caught():
    """The defect a third-party review found in `ratify.py`, pre-empted here.

    The instance set is unmoved, so the set digest stays valid. Only the ruling
    changed - and the ruling is what produces the scoreable set and every count.
    """
    record = _build()
    record["decisions"][B] = {"codes": [PASS_CODE]}
    record["counts"]["structurally_scoreable"] = 2
    record["counts"]["failing_v1"] = 1
    record["counts"]["failing_v1_or_v2"] = 2
    record["scoreable_ids"] = [A, B]
    assert record["instance_set_digest"] == instance_set_digest([A, B, C, D])
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_DECISIONS_DIGEST_MISMATCH"


def test_a_record_whose_counts_disagree_with_its_own_decisions_is_refused():
    record = _build()
    record["counts"]["structurally_scoreable"] = 4
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_COUNT_DISAGREEMENT"


def test_a_record_whose_scoreable_set_disagrees_with_its_decisions_is_refused():
    record = _build()
    record["scoreable_ids"] = [A, B]
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_SCOREABLE_SET_DISAGREEMENT"


def test_the_wrong_kind_of_record_is_refused():
    record = _build()
    record["record_kind"] = "transfer_evidence"
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_WRONG_RECORD_KIND"


def test_a_future_contract_version_is_refused():
    record = _build()
    record["contract_version"] = CONTRACT_VERSION + 1
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_WRONG_CONTRACT_VERSION"


def test_there_is_no_route_to_a_ledger_that_skips_the_record():
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(None, [A, B, C, D])
    assert e.value.code == "E_NOT_ADJUDICATED"


def test_binding_is_not_optional():
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(_build(), None)
    assert e.value.code == "E_NO_INSTANCE_SET"


# ---------------------------------------------------------------------------
# Blinded to outcomes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    {"verdict": "BREACH"},
    {"outcome": "completed"},
    {"arm": "v0"},
    {"transfer_rate": 0.5},
    {"tool_calls": []},
    {"breached_at_v0": 8},
    {"nested": {"deeper": [{"VERDICT": "CLEAN"}]}},
])
def test_a_structure_carrying_an_outcome_cannot_reach_the_ledger(payload):
    with pytest.raises(AdjudicationError) as e:
        assert_no_outcome_fields(payload)
    assert e.value.code == "E_OUTCOME_LEAKED"


def test_a_decision_carrying_a_verdict_is_refused_before_anything_else():
    decisions = _decisions()
    decisions[C] = {"codes": ["V2_NO_CLAUSE_REACHABLE"], "verdict": "BREACH"}
    with pytest.raises(AdjudicationError) as e:
        _build(decisions=decisions)
    assert e.value.code == "E_OUTCOME_LEAKED"


def test_an_outcome_smuggled_into_a_record_is_caught_at_load():
    record = _build()
    record["episodes"] = [{"instance_id": A}]
    with pytest.raises(AdjudicationError) as e:
        load_adjudication(record, [A, B, C, D])
    assert e.value.code == "E_OUTCOME_LEAKED"


def test_the_outcome_guard_survives_a_self_referencing_structure():
    """A cycle must not hang the guard - a check that never returns is a check
    a caller removes."""
    payload = {"a": {}}
    payload["a"]["back"] = payload
    assert_no_outcome_fields(payload)


def test_a_clean_structure_passes_the_guard():
    assert_no_outcome_fields(_decisions())


# ---------------------------------------------------------------------------
# The ledger a runner consumes
# ---------------------------------------------------------------------------

def test_the_record_round_trips_through_the_ledger_unchanged():
    record = _build()
    ledger = load_adjudication(record, [A, B, C, D])
    assert ledger.to_record() == record


def test_the_ledger_is_immutable():
    ledger = load_adjudication(_build(), [A, B, C, D])
    with pytest.raises(dataclasses.FrozenInstanceError):
        ledger.instance_ids = ()


def test_codes_for_an_instance_outside_the_set_raises():
    ledger = load_adjudication(_build(), [A, B, C, D])
    assert ledger.codes_for(B) == ("V1_ORPHANED_TURN",)
    with pytest.raises(AdjudicationError) as e:
        ledger.codes_for("atk_ffffffffffff")
    assert e.value.code == "E_DECISION_FOR_UNKNOWN_INSTANCE"


def test_the_ledger_carries_the_criterion_citation_not_a_paraphrase():
    record = _build()
    assert record["criterion_source"].startswith(
        "docs/proof/f4-unseal-preregistration-2026-08-25.md")


def test_the_ledger_type_is_what_load_returns():
    assert isinstance(load_adjudication(_build(), [A, B, C, D]),
                      AdjudicationLedger)


def test_an_all_pass_ledger_still_reports_the_failure_counts_as_zero():
    """Zero is a measurement. A ledger that omitted the counts when nothing
    failed would leave the outcome table with nothing to print."""
    record = build_adjudication(
        adjudicated_by=HUMAN, adjudicated_on=WHEN, instance_ids=[A, B],
        decisions={A: {"codes": [PASS_CODE]}, B: {"codes": [PASS_CODE]}})
    assert record["counts"] == {
        "adjudicated": 2,
        "structurally_scoreable": 2,
        "failing_v1": 0,
        "failing_v2": 0,
        "failing_v1_or_v2": 0,
    }


def test_an_all_fail_ledger_leaves_an_empty_scoreable_set():
    record = build_adjudication(
        adjudicated_by=HUMAN, adjudicated_on=WHEN, instance_ids=[A, B],
        decisions={A: {"codes": ["V1_ORPHANED_TURN"]},
                   B: {"codes": ["V2_NO_TOOL_REACHABLE"]}})
    ledger = load_adjudication(record, [A, B])
    assert ledger.scoreable_ids == ()
    assert record["counts"]["structurally_scoreable"] == 0
