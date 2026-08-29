"""The transfer evidence contract and its reader, and the proofs that the suite
of proofs can itself FAIL.

`crucible/transfer/reader.py` passed all twenty-two of its fixtures the first
time it ran. THAT IS NOT EVIDENCE. Twenty-two straight passes are
indistinguishable from a broken judge, which is why most of what is below is
not about the reader at all - it is about the SUITE:

  * it must catch a reader that accepts everything     (the damaged fixtures)
  * it must catch a reader that rejects everything     (the two controls)
  * it must catch a reader that finds the right defect
    and files it under the wrong ruling 60 class       (the class assertion)
  * its coverage of the reader's own codes must be FLOORED and PRINTED, so a
    refactor that quietly stops exercising the reader cannot report clean

AND ONE THING THAT IS NOT ABOUT EITHER. The floor. A run whose denominator
falls below the pre-registered floor is VALID and its rate is UNDEFINED, and
those two facts pull in opposite directions. A reader that rejected it would
destroy the most instructive artifact the phase can produce; a reader that
divided anyway would publish a number the design says means nothing. Both
failures look like rigor from one side. The tests for it are grouped together
at the bottom under their own banner.
"""

import copy
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

from crucible.replay import verdict as V              # noqa: E402
from crucible.transfer import reader as TR            # noqa: E402

SCHEMA_PATH = REPO / "contracts" / "transfer_evidence.schema.json"
C6_PATH = REPO / "contracts" / "evidence_bundle.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator():
    return TR.transfer_validator()


def _accepts(bundle, **kwargs):
    return TR.verdict_record(TR.verify_transfer_bundle(bundle, **kwargs))


# ==========================================================================
# The contract itself.
# ==========================================================================

def test_the_contract_is_a_valid_draft_2020_12_schema():
    """A checker that never inspects its own instrument reports on the
    instrument's behalf. Six of this repository's ten contracts once carried
    array-valued `$comment`s, which are illegal, while every fixture check
    against them stayed green."""
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_bundle_kind_is_a_const_so_the_two_kinds_can_never_be_confused():
    assert _schema()["properties"]["bundle_kind"]["const"] == "transfer_evidence"
    bad = TR.control_clean()
    bad["bundle_kind"] = "evidence_bundle"
    assert list(_validator().iter_errors(bad)), (
        "a document claiming to be a C6 bundle validated against the transfer "
        "contract")
    record = _accepts(bad)
    assert "E_WRONG_BUNDLE_KIND" in record["codes"]


def test_a_c6_bundle_does_not_validate_as_a_transfer_bundle():
    """The two kinds answer different questions, and a tool that confused them
    would report a comparison that was never made."""
    c6 = json.loads((REPO / "contracts" / "golden"
                     / "C6-evidence_bundle.valid.json").read_text(encoding="utf-8"))
    assert list(_validator().iter_errors(c6))


def test_the_decisive_reason_this_kind_exists_is_still_true_of_c6():
    """C6's `attacks[].provenance` admits exactly two values and NEITHER is
    true of a sealed holdout instance. `training_corpus` means reproducible
    from the committed corpus, which the sealed family is not; `generated`
    obligates the bundle to carry the attack's own bytes, which would publish
    the sealed instructions.

    If C6 ever gains a third value this test fails, and the justification for a
    separate kind has to be re-argued rather than assumed."""
    c6 = json.loads(C6_PATH.read_text(encoding="utf-8"))
    enum = c6["properties"]["attacks"]["items"]["properties"]["provenance"]["enum"]
    assert sorted(enum) == ["generated", "training_corpus"]


def test_the_contract_admits_no_rate_for_a_producer_to_assert():
    """DERIVED BY THE READER, NEVER WRITTEN BY THE PRODUCER. A producer that
    asserts its own applicability is a producer that can lie about it, and the
    assertion would be believed on exactly the same authority as the number it
    exempts. The same discipline the exclusion-rate applicability test follows."""
    block = _schema()["properties"]["transfer_arithmetic"]
    assert block["additionalProperties"] is False
    assert "transfer_rate" not in block["properties"]
    bad = TR.control_clean()
    bad["transfer_arithmetic"]["transfer_rate"] = 0.64
    assert list(_validator().iter_errors(bad))


@pytest.mark.parametrize("forbidden", ["instruction", "prompt", "text", "turns",
                                       "transcript", "attack_text"])
def test_no_instruction_carrying_property_may_exist_on_an_episode(forbidden):
    """A SEAL-SAFETY PROPERTY, NOT A STYLE CHOICE. The sealed instructions open
    exactly once and this document is published."""
    bad = TR.control_clean()
    bad["episodes"][0][forbidden] = "anything at all"
    assert list(_validator().iter_errors(bad)), (
        "the contract admitted a %r property on an object describing a sealed "
        "instance" % forbidden)


@pytest.mark.parametrize("where", ["episodes", "exclusions", "censuses"])
def test_every_instance_describing_object_is_closed(where):
    """`additionalProperties: false` is what makes the absence structural
    rather than conventional."""
    schema = _schema()
    assert schema["properties"][where]["items"]["additionalProperties"] is False


def test_an_exclusion_cannot_carry_a_round_index():
    """A transfer arm HAS NO ROUNDS. C6's `excluded[]` requires one, which is
    one of the six mismatches: any value written there would be invented."""
    schema = _schema()
    assert "round_index" not in schema["properties"]["exclusions"]["items"]["properties"]
    bad = TR.control_clean()
    bad["exclusions"][0]["round_index"] = 1
    assert list(_validator().iter_errors(bad))


def test_the_component_enum_admits_not_applicable_and_c6_does_not():
    """The CORONER, the ARMORER and the WARDEN are deliberately not invoked.
    Under C6 they would have to be described as something they were not."""
    ours = _schema()["$defs"]["component"]["properties"]["implementation"]["enum"]
    assert "not_applicable" in ours
    c6 = json.loads(C6_PATH.read_text(encoding="utf-8"))
    theirs = (c6["properties"]["execution_provenance"]["properties"]["components"]
              ["properties"]["coroner"]["properties"]["implementation"])
    assert "not_applicable" not in theirs.get("enum", []), (
        "C6 gained not_applicable; one of the six A3.8.3 mismatches has "
        "changed and the argument for a separate kind is now narrower")


def test_a_tool_call_argument_cannot_hold_an_instruction():
    """C1's `args` is an unconstrained object, which in a document about sealed
    instances is where a whole attack sits while every validator stays green.
    This contract bounds every argument value."""
    bad = TR.control_clean()
    bad["episodes"][0]["tool_calls"][0]["args"]["memo"] = "x" * 400
    assert list(_validator().iter_errors(bad))
    nested = TR.control_clean()
    nested["episodes"][0]["tool_calls"][0]["args"]["memo"] = {"deep": "text"}
    assert list(_validator().iter_errors(nested)), (
        "a nested object inside args would carry the string bound past the "
        "depth at which it applies")


def test_no_campaign_only_field_is_admitted():
    for field in ("rounds", "round_census", "patch_proposals", "gate_decisions",
                  "v0_benign_traces", "autopsies"):
        bad = TR.control_clean()
        bad[field] = []
        assert list(_validator().iter_errors(bad)), (
            "the contract admitted the campaign-only field %r" % field)


# ==========================================================================
# The reader's checks, one by one. Each is the fixture's assertion restated at
# the level of a single behaviour, so a failure names the check rather than the
# fixture id.
# ==========================================================================

def test_a_clean_bundle_reads_accepts_with_every_row_ok():
    report = TR.verify_transfer_bundle(TR.control_clean())
    assert report.ok, TR.render(report)
    record = TR.verdict_record(report)
    assert record["verdict"] == V.ACCEPTS
    assert record["exit_class"] == V.CLEAN
    assert TR.exit_code(record) == 0


def test_exactly_two_arms():
    one = TR.control_clean()
    one["arms"] = one["arms"][:1]
    assert "E_ARM_COUNT" in _accepts(one)["codes"]
    three = TR.build("TKB2")
    assert "E_ARM_COUNT" in _accepts(three)["codes"]


def test_two_arms_that_are_the_same_arm_twice_are_refused():
    """minItems and maxItems cannot tell two identical arms from two different
    ones, and a policy compared with itself produces a difference of zero that
    looks exactly like a policy with no purchase on the family."""
    bad = TR.control_clean()
    bad["arms"][1] = copy.deepcopy(bad["arms"][0])
    assert "E_ARM_DUPLICATED" in _accepts(bad)["codes"]


def test_the_expected_instance_count_is_a_parameter_and_not_a_constant():
    """A checker welded to one experiment's number is a checker that gets
    edited the first time a second experiment happens."""
    smaller = TR.synthetic_bundle(instances=18, breaches_v0=13, breaches_vfinal=4)
    assert _accepts(smaller, expected_instances=18)["verdict"] == V.ACCEPTS
    at_default = _accepts(smaller)
    assert "E_INSTANCE_COUNT" in at_default["codes"]
    assert "E_INSTANCE_COUNT" in at_default["measurement"], (
        "a short run is a RUN fact whose remedy is a re-run, not an edit to "
        "the writer")


def test_the_two_arms_must_cover_the_identical_instance_set():
    record = _accepts(TR.build("TKB4"))
    assert "E_ARM_INSTANCE_SETS_DIFFER" in record["codes"]
    assert TR.exit_code(record) == 0, (
        "an unpaired comparison is a faithful record of a bad run, so it must "
        "not look like a crash to a batch runner")


def test_episode_ids_must_be_unique_which_is_the_collision_c6_accepts():
    """`_episode_id_for()` derives an id from the attack id alone, so two arms
    over one instance set collide BY CONSTRUCTION. This is the single gap that
    a transfer run walks straight into."""
    record = _accepts(TR.build("TKB3"))
    assert "E_EPISODE_ID_DUPLICATED" in record["codes"]
    assert "E_EPISODE_ID_DUPLICATED" in record["structural"]
    assert TR.exit_code(record) == 1


def test_an_instance_driven_twice_in_one_arm_is_refused():
    bad = TR.control_clean()
    twin = copy.deepcopy(bad["episodes"][0])
    twin["episode_id"] = "ep_ffffffffffff"
    for call in twin["tool_calls"]:
        call["episode_id"] = twin["episode_id"]
    bad["episodes"].append(twin)
    assert "E_INSTANCE_DUPLICATED_IN_ARM" in _accepts(bad)["codes"]


def test_every_episode_names_a_declared_arm():
    assert "E_EPISODE_ARM_UNKNOWN" in _accepts(TR.build("TKB5"))["codes"]


def test_the_census_must_agree_with_the_episodes_and_not_only_with_itself():
    """Internal arithmetic catches a census that does not add up. Agreement
    with the episodes catches one that adds up perfectly and describes a
    different run."""
    internally_wrong = TR.build("TKB6")
    assert "E_ARM_CENSUS_ARITHMETIC" in _accepts(internally_wrong)["codes"]

    consistent_but_false = TR.control_clean()
    for row in consistent_but_false["censuses"]:
        if row["arm"] == TR.ARM_V0:
            row["attempted"] = 100
            row["scorable"] = 99
    record = _accepts(consistent_but_false)
    assert "E_ARM_CENSUS_DISAGREES" in record["codes"]


def test_an_unscored_episode_must_be_named_in_the_ledger():
    """Silent exclusion turns flakiness into apparent hardening."""
    assert "E_EXCLUSION_UNNAMED" in _accepts(TR.build("TKB20"))["codes"]


def test_an_exclusion_naming_a_drive_that_never_happened_is_refused():
    bad = TR.control_clean()
    bad["exclusions"][0]["instance_id"] = "atk_ffffffffffff"
    assert "E_EXCLUSION_ORPHAN" in _accepts(bad)["codes"]


def test_both_preflight_lists_are_required_and_the_flag_is_derived():
    """`preflight()` only RETURNS findings: it does not raise and does not
    append to the gate's reports, so a runner that dropped the result leaves an
    empty list behind, and a flag derived from an empty list is derived from
    nothing."""
    record = _accepts(TR.build("TKB7"))
    assert "E_PREFLIGHT_MISSING" in record["codes"]
    assert "E_G7G8_OVERCLAIM" in record["codes"]

    half = TR.control_clean()
    half["preflight"]["before_read"] = [half["preflight"]["before_read"][0]]
    assert "E_PREFLIGHT_MISSING" in _accepts(half)["codes"], (
        "a list carrying only G7 is a preflight that asserted half of what it "
        "claims")


def test_an_unevaluable_gate_invalidates_the_run_and_exits_zero():
    """An unevaluable gate is a check that cannot fail. The run is invalid and
    the document is faithful, which is MEASUREMENT."""
    record = _accepts(TR.build("TKB14"))
    assert "E_PREFLIGHT_INVALIDATES" in record["measurement"]
    assert TR.exit_code(record) == 0


def test_the_policy_hash_is_recomputed_from_the_payload_shipped_beside_it():
    """The only check here that can disagree with the record. Comparing a
    stored hash to itself passes on a truncated write, a partial write and a
    corrupted read alike."""
    assert "E_POLICY_HASH_RECOMPUTE" in _accepts(TR.build("TKB8"))["codes"]

    short_only = TR.control_clean()
    short_only["arms"][0]["policy_hash"] = "0" * 16
    assert "E_POLICY_HASH_RECOMPUTE" in _accepts(short_only)["codes"]

    swapped = TR.control_clean()
    swapped["arms"][1]["hashed_payload"] = {"policy_version": 99, "rules": []}
    assert "E_POLICY_HASH_RECOMPUTE" in _accepts(swapped)["codes"], (
        "a payload swapped under an unchanged hash is the case a stored-hash "
        "comparison cannot see")


def test_the_binding_attestation_may_admit_a_defect_but_not_contradict_itself():
    """A3.8.6. The zero is attested, NOT repaired: it sits inside the canonical
    policy hash, so correcting it would produce a policy that is not the one
    the pre-registration pins."""
    assert _accepts(TR.control_clean())["verdict"] == V.ACCEPTS, (
        "POLICY_BINDING_DEFECT is an admissible status and the expected one")
    assert "E_BINDING_STATUS_DISAGREES" in _accepts(TR.build("TKB15"))["codes"]

    foreign = TR.control_clean()
    foreign["policy_binding"]["runtime_manifest_hash"] = "1234567890abcdef"
    record = _accepts(foreign)
    assert "E_BINDING_MANIFEST_DISAGREES" in record["measurement"], (
        "a run against an unfrozen target surface is a RUN fact; the remedy is "
        "to re-run against the frozen target")


def test_the_uninvoked_components_must_say_so():
    assert "E_COMPONENT_INVOKED" in _accepts(TR.build("TKB16"))["codes"]
    stand_in = TR.control_clean()
    stand_in["execution_provenance"]["components"]["coroner"]["implementation"] = "stand_in"
    assert "E_COMPONENT_INVOKED" in _accepts(stand_in)["codes"], (
        "stand_in says something ran in its place, which is a different and "
        "weaker claim than not_applicable")


def test_the_arithmetic_is_recomputed_from_the_episodes():
    assert "E_TRANSFER_ARITHMETIC" in _accepts(TR.build("TKB11"))["codes"]
    inflated = TR.control_clean()
    inflated["transfer_arithmetic"]["breached_at_v0"] = 24
    assert "E_TRANSFER_ARITHMETIC" in _accepts(inflated)["codes"]


def test_a_live_run_with_no_episodes_is_not_a_run_a_figure_may_be_quoted_from():
    """RULING 61, LOCKED AS A REGRESSION. Every per-episode check above passes
    VACUOUSLY on an empty bundle, which is how a halted run once read ACCEPTS
    with eighteen of eighteen checks OK beside an exit code of 2."""
    record = _accepts(TR.build("TKB13"), expected_instances=0)
    assert "E_NO_MEASUREMENT_IN_TRANSFER" in record["measurement"]
    assert TR.exit_code(record) == 0


def test_the_reader_reports_rather_than_raises_on_a_document_it_cannot_read():
    for garbage in ({}, {"bundle_kind": "transfer_evidence"},
                    {"episodes": "not a list", "arms": "not a list"}):
        report = TR.verify_transfer_bundle(garbage)
        assert report.defects
        assert TR.verdict_record(report)["verdict"] == V.REJECTS


def test_the_crash_guard_actually_executes():
    """A BRANCH THAT NEVER EXECUTES IS INDISTINGUISHABLE FROM ONE THAT WORKS.
    The reader's own defect code is worth nothing until something has taken
    that path, so this test takes it."""
    bad = TR.control_clean()

    class _Exploding(dict):
        def get(self, *args, **kwargs):
            raise RuntimeError("a structure the reader cannot walk")

    bad["preflight"] = _Exploding()
    report = TR.verify_transfer_bundle(bad)
    codes = [d.code for d in report.defects]
    assert TR.E_READER_CRASHED in codes
    assert TR.classify(TR.E_READER_CRASHED) == V.STRUCTURAL


# ==========================================================================
# SEAL SAFETY. Not a measurement property. The sealed family opens once and
# this document is published.
# ==========================================================================

def test_a_forbidden_property_name_is_caught_at_any_depth():
    """The key scan runs over the WHOLE document, not over episodes. A producer
    that wants to carry the attack along attaches it to whatever object is
    nearest, and the payload is unconstrained by design."""
    bad = TR.control_clean()
    payload = dict(bad["arms"][1]["hashed_payload"])
    payload["prompt"] = "short"
    bad["arms"][1]["hashed_payload"] = payload
    from crucible.canon import hash_full
    bad["arms"][1]["policy_hash"] = hash_full(payload)[:16]
    bad["arms"][1]["policy_hash_full"] = hash_full(payload)
    record = _accepts(bad)
    assert "E_SEALED_TEXT_FIELD" in record["codes"]
    assert "E_POLICY_HASH_RECOMPUTE" not in record["codes"], (
        "the fixture must isolate the seal finding, or it passes for the "
        "wrong reason")


def test_a_string_long_enough_to_be_an_instruction_is_refused_unread():
    """BETTER A FALSE REFUSAL THAN A PUBLISHED SEAL. Exercised through the
    check directly, because the contract's own length bounds would refuse this
    first and the reader's scan has to survive the contract being loosened."""
    bad = TR.control_clean()
    bad["episodes"][0]["tool_calls"][0]["args"]["memo"] = "z" * (TR.SEAL_MAX_STRING + 1)
    defects = []
    row = TR._check_seal_safety(bad, defects)
    assert row.status == "FAIL"
    assert [d.code for d in defects] == ["E_SEALED_TEXT_PRESENT"]


def test_the_length_bound_does_not_fire_on_a_caveat_or_a_policy_payload():
    """The bound is scoped to objects DESCRIBING A SEALED INSTANCE. A label is
    a caveat about the run, and a policy payload's bytes are pinned by the hash
    recomputation in the same report, so neither is a place a sealed
    instruction can hide unnoticed."""
    bundle = TR.control_clean()
    bundle["labels"]["timing_deviation"] = "a legitimately long caveat. " * 12
    defects = []
    TR._check_seal_safety(bundle, defects)
    assert not defects


def test_the_seal_scan_reaches_every_episode_and_not_only_the_first():
    """A scan that stopped at the first episode would report clean over
    forty-seven unexamined ones."""
    bad = TR.control_clean()
    bad["episodes"][-1]["tool_calls"] = []
    bad["episodes"][-1]["outcome"] = "error"
    last = bad["episodes"][-1]
    last["verdict"]["invalid_reason"] = "E_NO_EVENTS_NO_REPLY"
    bad["episodes"][-1]["instructions"] = "x"
    assert "E_SEALED_TEXT_FIELD" in _accepts(bad)["codes"]


# ==========================================================================
# THE KNOWN-BAD SUITE, AND THE PROOFS THAT IT CAN FAIL.
# ==========================================================================

def test_the_suite_passes():
    results = TR.run_suite()
    bad = [r["id"] for r in results if not r["passed"]]
    assert not bad, TR.render_suite(results)


def test_both_controls_are_present_and_must_accept():
    """A suite of nothing but must-fail fixtures is satisfied perfectly by a
    reader that refuses every bundle it is handed."""
    results = TR.run_suite()
    controls = [r for r in results if r["id"] in TR.CONTROL_IDS]
    assert len(controls) == 2
    assert all(r["expect"] == "ACCEPTS" for r in controls)


def test_every_fixture_changes_one_thing_and_says_when_it_changes_more():
    """The damage must be the only difference from the control. A fixture that
    drifts in some second way can pass for the wrong reason."""
    golden = TR.control_clean()
    # The three fixtures that legitimately touch more than one top-level key,
    # and why. Each keeps the bundle otherwise CONSISTENT, which is the point:
    # a fixture that also broke the census would be caught by the census check
    # and would prove nothing about the check it names.
    multi = {"TKB4": 3, "TKB13": 4, "TKB20": 2}
    for fid, _, _, _, _ in TR.FIXTURES:
        damaged = TR.build(fid)
        changed = {k for k in set(golden) | set(damaged)
                   if golden.get(k) != damaged.get(k)}
        limit = multi.get(fid, 1)
        assert len(changed) <= limit, (
            "%s differs from the control in %d top-level keys: %s"
            % (fid, len(changed), sorted(changed)))


def test_building_a_fixture_does_not_leak_into_the_next_one():
    first = TR.build("TKB1")
    assert "corpus_hash" not in first["run_manifest"]["hash_locks"]
    second = TR.build("TKB2")
    assert "corpus_hash" in second["run_manifest"]["hash_locks"], (
        "TKB1 leaked into TKB2 - the fixtures share state")
    assert TR.control_clean()["run_manifest"]["hash_locks"].get("corpus_hash")


class _Strawman:
    """A reader stand-in. `defects` is whatever we tell it to find."""

    def __init__(self, defects):
        self.rows = []
        self.defects = list(defects)
        self.digest = None

    @property
    def ok(self):
        return not self.defects


def test_the_suite_catches_a_reader_that_accepts_everything(monkeypatch):
    """THE SINGLE MOST IMPORTANT TEST IN THIS FILE. A reader that returns no
    defects for any input is the exact failure mode the suite exists to
    detect."""
    monkeypatch.setattr(TR, "verify_transfer_bundle",
                        lambda b, **kw: _Strawman([]))
    results = TR.run_suite()
    controls = [r for r in results if r["id"] in TR.CONTROL_IDS]
    assert all(r["passed"] for r in controls), (
        "the controls should still pass against an accept-everything reader - "
        "that is what makes the damaged fixtures the ones that catch it")
    failed = [r["id"] for r in results if not r["passed"]]
    assert failed == list(TR.KNOWN_BAD_IDS), (
        "an accept-everything reader must fail EVERY damaged fixture; it "
        "failed only %s" % failed)
    assert not TR.suite_ok(results)


def test_the_suite_catches_a_reader_that_rejects_everything(monkeypatch):
    """The mirror, caught by the controls alone, which is the whole reason
    there are controls."""
    bogus = TR.Defect("E_TRANSFER_SCHEMA", "nowhere",
                      "a reader that refuses everything")
    monkeypatch.setattr(TR, "verify_transfer_bundle",
                        lambda b, **kw: _Strawman([bogus]))
    results = TR.run_suite()
    controls = [r for r in results if r["id"] in TR.CONTROL_IDS]
    assert not any(r["passed"] for r in controls), (
        "the controls MUST fail against a reject-everything reader. If they do "
        "not, the suite is satisfied by a reader that certifies nothing.")
    assert not TR.suite_ok(results)


def test_the_suite_catches_a_reader_that_refuses_the_below_floor_run(monkeypatch):
    """The failure this reader is most likely to be written into: refusing a
    VALID run because its denominator is small. It looks like rigor, and the
    only thing that catches it is a control that is below the floor and clean."""
    real = TR.verify_transfer_bundle

    def _refuses_small_denominators(bundle, **kwargs):
        report = real(bundle, **kwargs)
        figure = TR.transfer_figure(bundle)
        if figure is not None and not figure.defined:
            report.defects.append(TR.Defect(
                "E_TRANSFER_ARITHMETIC", "transfer_arithmetic",
                "denominator below the floor"))
        return report

    monkeypatch.setattr(TR, "verify_transfer_bundle", _refuses_small_denominators)
    results = TR.run_suite()
    below = next(r for r in results if r["id"] == "TKB0F")
    assert not below["passed"], (
        "TKB0F is the only fixture that catches a reader which rejects a valid "
        "run for having a small denominator")


def test_the_suite_catches_the_right_defect_filed_under_the_wrong_class():
    """Ruling 60 makes the CLASS decide the exit code, so a reader that finds
    the defect and files it on the wrong side is still broken - it would send a
    producer bug to a re-run queue, or halt a batch over a bad run."""
    fid, _, code, cls, _ = next(f for f in TR.FIXTURES if f[0] == "TKB4")
    assert cls == V.MEASUREMENT
    record = _accepts(TR.build(fid))
    assert code in record["codes"]
    assert code in record[V.MEASUREMENT.lower()]
    assert code not in record[V.STRUCTURAL.lower()], (
        "an unpaired instance set filed STRUCTURAL would exit non-zero on a "
        "bundle whose remedy is a re-run")


def test_every_structural_fixture_exits_non_zero_and_every_measurement_one_does_not():
    for fid, _, code, cls, _ in TR.FIXTURES:
        record = _accepts(TR.build(fid), expected_instances=(
            0 if fid == "TKB13" else TR.DEFAULT_EXPECTED_INSTANCES))
        if cls == V.STRUCTURAL:
            assert TR.exit_code(record) == 1, "%s should exit non-zero" % fid
        else:
            assert record["exit_class"] != V.STRUCTURAL, (
                "%s fired a structural code as well, so its exit code no "
                "longer proves anything about %s" % (fid, code))
            assert TR.exit_code(record) == 0, "%s should exit 0" % fid


# ==========================================================================
# The checks the shipped fixture suite does not reach, exercised here.
#
# A DATA TABLE RATHER THAN TWENTY FUNCTIONS, and it is read by the coverage
# section below, so the gap it closes is COMPUTED rather than claimed. A
# coverage figure derived by grepping this file for code names would count a
# code that appears in a comment, which is the quiet direction of the same
# defect the whole file is about.
# ==========================================================================

def _m_lock_malformed(b):
    b["run_manifest"]["hash_locks"]["corpus_hash"] = ""
    return b


def _m_arm_unnamed(b):
    b["arms"][1]["arm"] = "v9"
    return b


def _m_payload_unhashable(b):
    b["arms"][0]["hashed_payload"] = {"weight": 1.5}
    return b


def _m_stamp_missing(b):
    del b["episodes"][0]["manifest_hash"]
    return b


def _m_stamp_malformed(b):
    b["episodes"][0]["derived_schema_hash"] = "nope"
    return b


def _m_verdict_stamp_disagrees(b):
    b["episodes"][0]["verdict"]["objective_set_hash"] = "9999999999999999"
    return b


def _m_prefix_unordered(b):
    calls = b["episodes"][0]["tool_calls"]
    calls[0]["seq"], calls[1]["seq"] = calls[1]["seq"], calls[0]["seq"]
    return b


def _m_tool_call_foreign(b):
    b["episodes"][0]["tool_calls"][0]["episode_id"] = "ep_ffffffffffff"
    return b


def _m_census_missing(b):
    b["censuses"] = [b["censuses"][0]]
    return b


def _m_census_duplicated(b):
    b["censuses"].append(copy.deepcopy(b["censuses"][0]))
    return b


def _m_binding_missing(b):
    del b["policy_binding"]
    return b


def _m_binding_unknown_policy(b):
    b["policy_binding"]["policy_hash"] = "abcdefabcdefabcd"
    return b


def _m_provenance_missing(b):
    del b["execution_provenance"]
    return b


def _m_live_without_model_calls(b):
    b["execution_provenance"]["model_calls"] = 0
    return b


def _m_labels_missing(b):
    del b["labels"]
    return b


def _m_label_missing(b):
    b["labels"]["timing_deviation"] = "   "
    return b


def _m_not_canonicalizable(b):
    b["arms"][0]["rule_count"] = 1.5
    return b


def _m_wrong_kind(b):
    b["bundle_kind"] = "evidence_bundle"
    return b


def _m_arm_duplicated(b):
    b["arms"][1] = copy.deepcopy(b["arms"][0])
    return b


def _m_instance_twice_in_one_arm(b):
    twin = copy.deepcopy(b["episodes"][0])
    twin["episode_id"] = "ep_ffffffffffff"
    for call in twin["tool_calls"]:
        call["episode_id"] = twin["episode_id"]
    b["episodes"].append(twin)
    return b


def _m_exclusion_orphan(b):
    b["exclusions"][0]["instance_id"] = "atk_ffffffffffff"
    return b


def _m_binding_manifest_disagrees(b):
    b["policy_binding"]["runtime_manifest_hash"] = "1234567890abcdef"
    return b


class _Exploding(dict):
    """A structure the reader cannot walk. Not a hypothetical: a bundle
    malformed enough to crash the reader is the most structural defect there
    is, and the artifact is needed most in exactly that case."""

    def get(self, *args, **kwargs):
        raise RuntimeError("a structure the reader cannot walk")


def _m_reader_crashes(b):
    b["preflight"] = _Exploding()
    return b


_EXTRA_MUTATIONS = (
    ("a lock that is not a lock", _m_lock_malformed, "E_LOCK_MALFORMED"),
    ("an arm with a name nobody declared", _m_arm_unnamed, "E_ARM_UNNAMED"),
    ("a policy payload with no canonical form", _m_payload_unhashable,
     "E_POLICY_PAYLOAD_UNHASHABLE"),
    ("an episode missing a ruler stamp", _m_stamp_missing,
     "E_EPISODE_STAMP_MISSING"),
    ("an episode with a malformed stamp", _m_stamp_malformed,
     "E_EPISODE_STAMP_MALFORMED"),
    ("a verdict graded under a different ruler", _m_verdict_stamp_disagrees,
     "E_VERDICT_STAMP_DISAGREES"),
    ("a trace out of order", _m_prefix_unordered, "E_PREFIX_UNORDERED"),
    ("a call stamped with a foreign episode", _m_tool_call_foreign,
     "E_TOOL_CALL_EPISODE_DISAGREES"),
    ("an arm with no census row", _m_census_missing, "E_ARM_CENSUS_MISSING"),
    ("one arm with two census rows", _m_census_duplicated,
     "E_ARM_CENSUS_DUPLICATED"),
    ("no binding attestation", _m_binding_missing, "E_BINDING_MISSING"),
    ("an attestation about a policy no arm carries", _m_binding_unknown_policy,
     "E_BINDING_POLICY_HASH_UNKNOWN"),
    ("no execution provenance", _m_provenance_missing, "E_PROVENANCE_MISSING"),
    ("a live run with no model calls", _m_live_without_model_calls,
     "E_LIVE_WITHOUT_MODEL_CALLS"),
    ("no labels at all", _m_labels_missing, "E_LABELS_MISSING"),
    ("a blank caveat", _m_label_missing, "E_LABEL_MISSING"),
    ("a float, so the document has no canonical form", _m_not_canonicalizable,
     "E_NOT_CANONICALIZABLE"),
    # The last six are ALSO covered by a dedicated test above, which asserts
    # more than that the code fires. They are repeated here as data so the
    # coverage figure below is computed from codes that actually fired rather
    # than from a regex over this file.
    ("a document that says it is a campaign bundle", _m_wrong_kind,
     "E_WRONG_BUNDLE_KIND"),
    ("one arm written twice", _m_arm_duplicated, "E_ARM_DUPLICATED"),
    ("one instance driven twice in one arm", _m_instance_twice_in_one_arm,
     "E_INSTANCE_DUPLICATED_IN_ARM"),
    ("an exclusion for a drive that never happened", _m_exclusion_orphan,
     "E_EXCLUSION_ORPHAN"),
    ("a runtime manifest that is not the frozen one",
     _m_binding_manifest_disagrees, "E_BINDING_MANIFEST_DISAGREES"),
    ("a structure that crashes the reader", _m_reader_crashes,
     "E_READER_CRASHED"),
)


@pytest.mark.parametrize("damage,mutate,code",
                         _EXTRA_MUTATIONS,
                         ids=[m[2] for m in _EXTRA_MUTATIONS])
def test_the_checks_the_fixture_suite_does_not_reach_can_still_fire(damage,
                                                                    mutate,
                                                                    code):
    record = _accepts(mutate(TR.control_clean()))
    assert code in record["codes"], (
        "%s did not fire on a bundle carrying %s. Nothing proves that check "
        "can fail." % (code, damage))


# ==========================================================================
# Coverage, floored and printed. The gap is declared, never silent.
# ==========================================================================

_MIN_CODES_EXERCISED = 46

# String literals in reader.py that look like defect codes and are not: the
# synthetic fixtures stamp a TRIPWIRE invalidity reason on an episode. Listed
# rather than filtered by position, so a new one has to be admitted here on
# purpose.
_NOT_DEFECT_CODES = {"E_NO_EVENTS_NO_REPLY"}


def _codes_the_reader_can_emit():
    src = (REPO / "crucible" / "transfer" / "reader.py").read_text(encoding="utf-8")
    return set(re.findall(r'"(E_[A-Z0-9_]+)"', src)) - _NOT_DEFECT_CODES


def _codes_this_suite_exercises():
    """Codes that ACTUALLY FIRED, from the shipped fixtures and from the table
    above. Both halves are run, not read: a code is counted only when a reader
    emitted it on a real document."""
    seen = set()
    for fid, _, _, _, _ in TR.FIXTURES:
        seen |= set(_accepts(TR.build(fid))["codes"])
    for _damage, mutate, _code in _EXTRA_MUTATIONS:
        seen |= set(_accepts(mutate(TR.control_clean()))["codes"])
    return seen


def test_every_code_the_reader_can_emit_is_classified():
    """A code nobody classified is a code nobody thought about, and the
    STRUCTURAL default is a backstop rather than the mechanism."""
    unclassified = sorted(_codes_the_reader_can_emit() - set(TR.CLASSIFICATION))
    assert not unclassified, (
        "these codes have no row in the partition table: %s" % unclassified)


def test_every_classified_code_carries_a_reason():
    for code in TR.CLASSIFICATION:
        assert TR.REASONS.get(code), "%s is classified with no reason" % code


def test_an_unknown_code_defaults_to_structural():
    """The noisy direction is the safe one. Defaulting to MEASUREMENT exits 0
    and hides it, which is the precise shape ruling 60 exists to close."""
    assert TR.classify("E_SOMETHING_NOBODY_CLASSIFIED") == V.STRUCTURAL
    structural, measurement, unclassified = TR.partition(["E_NEW_CODE"])
    assert unclassified == ["E_NEW_CODE"]
    assert structural == ["E_NEW_CODE"]
    assert measurement == []


def test_every_fixtures_named_code_is_one_the_reader_can_actually_emit():
    """Guards a typo in a fixture's expectation, which would otherwise make the
    fixture unfalsifiable in the quiet direction."""
    emittable = _codes_the_reader_can_emit()
    for fid, _, code, _, _ in TR.FIXTURES:
        assert code in emittable, (
            "%s expects %s, which appears nowhere in reader.py" % (fid, code))


def test_the_suite_actually_exercises_the_reader_and_the_floor_proves_it():
    """THE VACUITY FLOOR. Without it, a suite whose fixtures stopped damaging
    anything would report twenty-two clean passes and exercise nothing."""
    exercised = _codes_this_suite_exercises()
    assert len(exercised) >= _MIN_CODES_EXERCISED, (
        "the suite caused only %d distinct reader codes to fire, below the "
        "floor of %d. The fixtures have stopped damaging what they claim to."
        % (len(exercised), _MIN_CODES_EXERCISED))


def test_the_uncovered_codes_are_reported_so_the_gap_cannot_grow_quietly(capsys):
    """NOT AN ASSERTION THAT COVERAGE IS COMPLETE - it is not, and pretending
    otherwise is the defect. This prints what is still unproven so the number
    is visible every run, and fails only if coverage goes BACKWARDS."""
    emittable = _codes_the_reader_can_emit()
    exercised = _codes_this_suite_exercises()
    uncovered = sorted(emittable - exercised)
    with capsys.disabled():
        print("\n  TRANSFER READER CODE COVERAGE: %d of %d exercised by the "
              "known-bad suite, %d STILL UNPROVEN"
              % (len(exercised & emittable), len(emittable), len(uncovered)))
        for code in uncovered:
            print("    unproven  %s" % code)
    assert len(exercised & emittable) >= _MIN_CODES_EXERCISED


# ==========================================================================
# THE FLOOR. The one place where being wrong in either direction costs most.
#
# Below the floor the run is VALID and the rate is UNDEFINED. Rejecting a valid
# run and quoting an undefined rate are both wrong, and both look like rigor
# from one side.
# ==========================================================================

def test_a_run_below_the_floor_is_valid_and_the_reader_does_not_reject_it():
    bundle = TR.control_below_floor()
    report = TR.verify_transfer_bundle(bundle)
    assert report.ok, TR.render(report)
    record = TR.verdict_record(report)
    assert record["verdict"] == V.ACCEPTS
    assert TR.exit_code(record) == 0


def test_a_run_below_the_floor_refuses_to_produce_a_rate():
    figure = TR.transfer_figure(TR.control_below_floor())
    assert figure.defined is False
    with pytest.raises(TR.UndefinedTransferRate):
        figure.rate


def test_the_undefined_figure_prints_the_two_raw_counts_and_no_quotient():
    """What gets reported in place of a rate is the two counts. A figure that
    fell silent would leave a reader to divide the numbers themselves."""
    figure = TR.transfer_figure(TR.control_below_floor())
    text = figure.text()
    assert "8" in text and "3" in text
    assert "not defined" in text.lower()
    assert "percent" not in text.lower(), (
        "a percentage in the undefined case is the number the design says "
        "means nothing")
    assert "invalid" not in text.lower().replace("not invalid", "")


def test_the_floor_row_is_reported_as_not_applicable_rather_than_omitted():
    """A check that quietly stops running is how a boundary rots. The row
    prints the counts beside the word it cannot compute."""
    report = TR.verify_transfer_bundle(TR.control_below_floor())
    row = next(r for r in report.rows if r.check == "TRANSFER RATE")
    assert row.status == "N/A"
    assert "NO RATE" in row.note


def test_above_the_floor_the_rate_is_defined_and_carries_its_caveat():
    figure = TR.transfer_figure(TR.control_clean())
    assert figure.defined is True
    assert figure.breached_at_v0 == 14
    assert figure.breached_at_vfinal == 5
    assert figure.closed == 9
    assert abs(figure.rate - 9 / 14.0) < 1e-9
    text = figure.text()
    assert "single-sample" in text and "no stability estimate" in text


def test_exactly_at_the_floor_the_rate_is_defined():
    """The boundary itself, because an off-by-one here silently changes which
    runs report a rate."""
    at = TR.synthetic_bundle(breaches_v0=TR.DEFAULT_FLOOR, breaches_vfinal=2)
    assert TR.transfer_figure(at).defined is True
    below = TR.synthetic_bundle(breaches_v0=TR.DEFAULT_FLOOR - 1, breaches_vfinal=2)
    assert TR.transfer_figure(below).defined is False


def test_a_zero_denominator_is_undefined_rather_than_a_division_by_zero():
    figure = TR.TransferFigure(0, 0, 0)
    assert figure.defined is False
    with pytest.raises(TR.UndefinedTransferRate):
        figure.rate


def test_the_floor_is_a_parameter_and_the_bundles_declared_floor_is_checked():
    """Two different things and both are needed. The reader's expected floor is
    an argument so a second experiment does not require editing the checker;
    the bundle's own floor is asserted against it so a lowered floor is caught
    rather than obeyed."""
    bundle = TR.control_below_floor()
    assert TR.transfer_figure(bundle, floor=6).defined is True

    lowered = TR.build("TKB17")
    record = _accepts(lowered)
    assert "E_FLOOR_MOVED" in record["structural"]
    assert TR.exit_code(record) == 1


def test_the_undefined_rate_cannot_be_formatted_by_accident():
    """Raising rather than returning None is the point: a None flows into a
    format string and prints, and "transfer rate None" is a sentence somebody
    edits into something tidier."""
    figure = TR.transfer_figure(TR.control_below_floor())
    with pytest.raises(TR.UndefinedTransferRate):
        "%.1f" % (100 * figure.rate)
