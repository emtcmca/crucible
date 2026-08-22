"""test_c6_producer.py - does the campaign write a C6 evidence bundle, or does
`contracts/evidence_bundle.schema.json` merely exist?

THE PRECISE GAP THIS FILE EXISTS FOR
=====================================
`campaign.py` wrote `{summary, hashes, final_policy, rounds}`. C6 requires
seventeen root keys. **THE TWO SHAPES HAD ZERO KEYS IN COMMON**, so
`crucible/replay/view.py`, `crucible/replay/integrity.py`, the judge's
reproduction path and the demo could not read one run this project had ever
produced. The loop worked and left no record anything could open.

That is the same failure shape `tests/test_campaign_gate_wiring.py` was written
for one component earlier: a correct module (`crucible/replay/` reads C6
beautifully), a green suite of its own (`tests/test_bundle_reader.py` passes
against a HAND-WRITTEN golden), and nothing connecting the two. A per-module
suite structurally cannot see it, because each side tests itself in isolation
against a fixture the other side never wrote.

**So every test here asserts on a bundle a REAL CAMPAIGN RUN PRODUCED**, or on
`crucible/conductor/bundle.py` handed real run objects. A test that validated a
hand-built dict against the schema would prove that the schema parses.

WHAT IS OFFLINE-ONLY HERE. READ THIS BEFORE TRUSTING A GREEN RUN.
=================================================================
1. **No model call is made anywhere in this file and no gcloud process starts.**
   Every campaign run below is offline: the target is driven by a scripted
   model, the RED_STRATEGIST replays its seeds verbatim, and the ARMORER is
   handed a refusal stub. So the ATTACK CATALOGUE is exercised only on its
   `training_corpus` branch by the end-to-end runs, and the `generated` branch -
   the one that carries bytes that exist nowhere else - is exercised by
   `_attacks` directly, against a synthetic model-varied attack.
2. **`patch_proposals` is empty in every end-to-end run here**, because an
   offline ARMORER produces no patch. Its assembly is exercised by unit tests
   against a synthetic `PatchResult`.
3. **`g7_g8_exercised` is false in every bundle here** and nothing in this file
   evaluates G7 or G8 against anything.
"""

import json
import pathlib

import pytest

from crucible.conductor import bundle as B
from crucible.conductor import campaign as C
from crucible.conductor import real_gate as rg
from crucible.conductor.conductor import RoundRecord
from crucible.plugin.adk import ADK_AVAILABLE
from crucible.replay.integrity import verify_bundle

adk_only = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")


def _read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def offline_run(tmp_path_factory):
    """ONE full offline campaign, reused by every end-to-end test below.

    Module-scoped because it drives six real ADK episodes and replays the
    26-fixture benign suite; running that once per assertion would turn this
    file into the slowest in the suite for no extra evidence.
    """
    out = tmp_path_factory.mktemp("c6") / "bundle.json"
    code = C.run(["--out", str(out)])
    return {"code": code, "out": out, "c6": pathlib.Path(C.c6_path(str(out))),
            "bundle": _read(C.c6_path(str(out)))}


# ---------------------------------------------------------------------------
# 1. THE GAP ITSELF. These two fail red on the tree before this lane, where the
#    campaign wrote no C6 document at all.
# ---------------------------------------------------------------------------

@adk_only
def test_a_completed_run_writes_a_bundle_that_validates_against_the_real_C6(
        offline_run):
    """Against `contracts/evidence_bundle.schema.json` itself, through the SAME
    validator the offline reader builds - not a copy of it, and not a subset of
    the checks. `additionalProperties: false` sits at the root and on every
    array's items, so this also proves no extra key was smuggled in."""
    assert offline_run["c6"].exists()
    errors = B.validate_bundle(offline_run["bundle"])
    assert errors == [], "\n".join(errors)


@adk_only
def test_a_HALTED_run_still_writes_a_C6_bundle(monkeypatch, tmp_path):
    """A bundle that only exists on the happy path is missing exactly when a
    reader most needs it.

    `GateRunInvalid` means THERE IS NO MEASUREMENT, and the bundle that says so
    has to be readable or the void itself is unreadable. It carries no episodes,
    because there were none - and it still carries the hash-locks, the frozen
    parameters, the SEP-BY split, the clause table, the benign floor and all
    five labels.
    """
    exc = rg.GateRunInvalid(
        [rg.finding("G7c", "holdout_touch_count == 2", rg.FAIL,
                    "holdout_touch_count is 9, expected 2", invalidates=True)])

    class _Raiser:
        def __init__(self, **kwargs):
            pass

        def run(self, policy):
            raise exc

    monkeypatch.setattr(C, "Conductor", _Raiser)
    out = tmp_path / "halt.json"
    assert C.run(["--out", str(out)]) == C.EXIT_RUN_INVALID

    bundle = _read(C.c6_path(str(out)))
    errors = B.validate_bundle(bundle)
    assert errors == [], "\n".join(errors)
    assert bundle["episodes"] == []
    assert bundle["round_census"] == []
    # The frame survives the void. This is the half a reader most needs.
    assert len(bundle["run_manifest"]["hash_locks"]) == 6
    assert len(bundle["v0_benign_traces"]) == 26
    assert len(bundle["clause_coverage"]["clauses"]) == 9
    assert sorted(bundle["labels"]) == ["benign_regression", "k",
                                        "sep_by_split", "target_tier",
                                        "trust_root"]


# ---------------------------------------------------------------------------
# 2. THE CHECK THAT PROVES THE CHECK CAN FAIL.
#    Nine straight all-PASS runs are indistinguishable from a broken judge.
# ---------------------------------------------------------------------------

@adk_only
@pytest.mark.parametrize("mutate,why", [
    (lambda b: b.pop("labels"),
     "the five caveats that travel with every figure"),
    (lambda b: b.pop("attacks"),
     "the catalogue that says what was tested"),
    (lambda b: b["episodes"][0].pop("episode_frozen_context"),
     "ruling 16's frozen block - the F4 seal collapses without it"),
    (lambda b: b.__setitem__("smuggled", 1),
     "an extra root key; additionalProperties is false"),
    (lambda b: b["cost"].pop("wall_clock_ms"),
     "the number a customer decides on"),
])
def test_the_validator_REJECTS_a_bundle_with_a_hole_in_it(offline_run, mutate,
                                                          why):
    """`validate_bundle` returning [] on a real bundle means nothing unless it
    can return something. Each mutation below is a hole C6 was extended on
    2026-08-22 specifically to catch, and each is applied to a bundle that
    validated clean one test ago - so the only difference is the hole."""
    damaged = json.loads(json.dumps(offline_run["bundle"]))
    mutate(damaged)
    assert B.validate_bundle(damaged), why


# ---------------------------------------------------------------------------
# 3. WHAT WAS TESTED. The attack text, which the campaign used to strip.
# ---------------------------------------------------------------------------

@adk_only
def test_the_bundle_carries_the_ATTACK_TEXT(offline_run):
    """`campaign.py::_round_json` read

        [{k: v for k, v in a.items() if k != "instruction"} for a in ...]

    so the one field a reader most wants went nowhere at all. For a model-varied
    attack that made the string unrecoverable the moment the process exited.
    """
    bundle = offline_run["bundle"]
    assert bundle["attacks"], "no catalogue at all"
    for entry in bundle["attacks"]:
        assert entry["instruction"].strip(), entry["attack_id"]
    # The bytes are the SEEDS', verbatim - not a summary and not a hash.
    texts = {e["instruction"] for e in bundle["attacks"]}
    assert {s.instruction for s in C.SEEDS} <= texts


@adk_only
def test_every_attack_an_episode_names_is_in_the_catalogue(offline_run):
    """An episode naming an uncatalogued attack cannot be traced to what was
    tested, which makes the run a scoreboard rather than a record."""
    bundle = offline_run["bundle"]
    catalogued = {e["attack_id"] for e in bundle["attacks"]}
    named = {e["attack_id"] for e in bundle["episodes"]}
    assert named and named <= catalogued


def test_a_MODEL_VARIED_attack_is_provenance_generated_and_carries_its_bytes():
    """The branch no offline run reaches, and the one that matters most.

    `RedStrategist.vary` returns `variation: "model"` only when the model
    actually rewrote the seed. Those bytes exist in NO corpus and on NO disk, so
    `provenance` must be `generated` - which is what makes `instruction`
    REQUIRED rather than optional - and the lineage back to the seed must
    survive.

    A `fallback` or `governor_refused` variation is the SAME BYTES as the seed
    reached by a different road, and calling that "generated" would claim a
    novel attack where a replay happened.
    """
    varied = _round_with_attacks([
        {"attack_id": "atk_a00000000001", "family_id": "fam_direct_ask",
         "instruction": "rewritten by the model", "variation": "model"},
        {"attack_id": "atk_a00000000002", "family_id": "fam_urgency",
         "instruction": "the seed, verbatim", "variation": "fallback"},
    ])
    catalogue = {e["attack_id"]: e for e in B._attacks(   # noqa: SLF001
        [varied], generator=B.generator_ref(True, C.RED_SEED))}

    generated = catalogue["atk_a00000000001"]
    assert generated["provenance"] == "generated"
    assert generated["instruction"] == "rewritten by the model"
    assert generated["derived_from_attack_id"] == "atk_a00000000001"
    assert generated["generator"]["model_id"] and generated["generator"]["provider"]
    assert generated["round_index"] == 1

    replayed = catalogue["atk_a00000000002"]
    assert replayed["provenance"] == "training_corpus"
    assert "generator" not in replayed


# ---------------------------------------------------------------------------
# 4. THE DENOMINATORS. A live run on 2026-08-22 recorded 36 target faults and
#    named not one of them.
# ---------------------------------------------------------------------------

def _round_with_attacks(attacks, verdicts=(), index=1, outcome="SCORED"):
    record = RoundRecord(round_index=index, hashes={})
    record.attacks = list(attacks)
    record.verdicts = list(verdicts)
    record.outcome = outcome
    return record


def _verdict(attack_id, verdict, *, target_fault=False, episode_id=None):
    out = {"verdict": verdict, "objective_set_hash": "0" * 16, "evidence": [],
           "attack_id": attack_id,
           "_episode": {"episode_id": episode_id or ("ep_" + attack_id[4:])}}
    if verdict != "INVALID":
        out["breach"] = verdict == "BREACH"
    if target_fault:
        out["target_fault"] = True
    return out


def test_every_excluded_episode_is_NAMED_with_its_instance_id_and_its_reason():
    """Section 5.1 requires the LIST WITH INSTANCE IDS, not the count. A
    denominator that shrinks for a reason the ledger does not name is the silent
    exclusion that turns flakiness into apparent hardening.

    The two reasons stay apart because they mean different things: TARGET_FAULT
    is a measurement that belongs outside the denominator, INVALID is the
    ABSENCE of a measurement.
    """
    record = _round_with_attacks([], [
        _verdict("atk_a00000000001", "CLEAN"),
        _verdict("atk_a00000000002", "BREACH", target_fault=True),
        _verdict("atk_a00000000003", "INVALID"),
    ])
    rows = B._excluded_rows(record)                       # noqa: SLF001
    by_id = {r["instance_id"]: r for r in rows}
    assert set(by_id) == {"atk_a00000000002", "atk_a00000000003"}
    assert by_id["atk_a00000000002"]["reason"] == "target_fault"
    assert by_id["atk_a00000000003"]["reason"] == "invalid_verdict"
    for row in rows:
        assert row["round_index"] == 1
        assert row["episode_id"].startswith("ep_")
        assert row["detail"].strip()


def test_the_census_arithmetic_holds_and_the_ledger_matches_it():
    """`attempted == scorable + excluded`, and the number of named exclusions
    for a round equals that round's `excluded` count. The replay reader
    cross-checks BOTH, so the two halves cannot drift apart in silence."""
    record = _round_with_attacks([], [
        _verdict("atk_a00000000001", "CLEAN"),
        _verdict("atk_a00000000002", "BREACH"),
        _verdict("atk_a00000000003", "BREACH", target_fault=True),
        _verdict("atk_a00000000004", "INVALID"),
    ])
    row = B._round_census([record], {})[0]               # noqa: SLF001
    assert row["attempted"] == row["scorable"] + row["excluded"] == 4
    assert row["scorable"] == 2 and row["excluded"] == 2
    assert row["target_faults"] == 1 and row["invalid"] == 1
    assert row["breaches"] == 1          # the faulted one is NOT counted
    assert len(B._excluded_rows(record)) == row["excluded"]   # noqa: SLF001


@adk_only
def test_the_census_arithmetic_holds_on_a_real_run(offline_run):
    bundle = offline_run["bundle"]
    listed = {}
    for entry in bundle["excluded"]:
        listed[entry["round_index"]] = listed.get(entry["round_index"], 0) + 1
    assert bundle["round_census"]
    for row in bundle["round_census"]:
        assert row["attempted"] == row["scorable"] + row["excluded"]
        assert listed.get(row["round_index"], 0) == row["excluded"]


# ---------------------------------------------------------------------------
# 5. WHAT WAS FOUND AND WHAT WAS PATCHED.
# ---------------------------------------------------------------------------

@adk_only
def test_the_autopsy_in_the_C6_BUNDLE_is_the_FULL_RECORD_not_the_projection(
        offline_run):
    """The opposite of what the campaign RECORD carries, on purpose.

    `project()` is the ARMORER's blinding - it strips `run_id`, `attack_id`,
    `objective_set_hash` and both manifest hashes so the ARMORER cannot see what
    it must be blind to. That is exactly the wrong document for the run of
    record, where a reader needs the parts the ARMORER may not have. C6 `$ref`s
    the full C5 breach record.
    """
    autopsies = offline_run["bundle"]["autopsies"]
    assert autopsies, "the run breached and no autopsy reached the bundle"
    for record in autopsies:
        for field in ("run_id", "attack_id", "objective_set_hash",
                      "manifest_hash", "derived_schema_hash", "breach_id"):
            assert record.get(field), field


@adk_only
def test_the_policy_chain_carries_the_RULE_TEXT_a_human_can_read(offline_run):
    """"Here is the rule that now stops it" has to be legible from the bundle
    alone. Four hashes and a `gcs_uri` into a bucket the reader cannot open is a
    forwarding address, not an answer."""
    chain = offline_run["bundle"]["policy_chain"]
    assert chain
    for entry in chain:
        assert entry["rules"]
        assert len(entry["policy_hash_full"]) == 64
        for rule in entry["rules"]:
            assert rule["dsl_text"].startswith("rule %s:" % rule["rule_id"])
            assert rule["verb"] in ("deny", "require_approval", "constrain_arg")


def test_the_placeholder_rule_id_is_RECOMPUTED_from_the_armorers_own_text():
    """CONVENTIONS 2.6: the ARMORER never writes a rule id, because a model
    cannot compute SHA-256. It emits `r_new1` and the validator rewrites it, and
    C6 wants BOTH halves - which is what makes the mechanism visible to a reader
    instead of a claim in a doc.

    `Validator.validate_patch` returns only the rewritten half, so the mapping
    is derived again with L3's own parser and `compile_rule`. This test proves
    the recomputation lands on the id the validator assigns - the same function,
    not a lookalike - rather than on a guess by ordinal position.
    """
    from crucible.dsl import compile_rule, parse_policy

    text = ("rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50000 "
            "=> deny")
    expected = compile_rule(parse_policy(text).rules[0])["rule_id"]

    class _Patch:
        patch_text = text

    mapping = B._proposed_id_map(_Patch())               # noqa: SLF001
    assert mapping == {expected: "r_new1"}
    assert expected.startswith("r_") and len(expected) == 14


def test_a_patch_with_no_placeholder_yields_no_mapping_rather_than_a_guess():
    """The OPTIONAL field is omitted rather than filled by pairing on position.
    Guessing a pairing by ordinal is wrong SILENTLY, which is the failure mode
    an omission cannot have."""

    class _Patch:
        patch_text = "retract_rule r_5f2a91cc0b74"

    assert B._proposed_id_map(_Patch()) == {}            # noqa: SLF001


# ---------------------------------------------------------------------------
# 6. THE LABELS AND THE PROVENANCE - the caveats that must travel in the file.
# ---------------------------------------------------------------------------

@adk_only
def test_an_offline_bundle_is_structurally_impossible_to_read_as_a_live_one(
        offline_run):
    """Every other field in a stand-in bundle is byte-identical IN SHAPE to a
    live one. Without this block the two are told apart only by knowing which
    command was typed, and the banner that said so has scrolled away."""
    prov = offline_run["bundle"]["execution_provenance"]
    assert prov["mode"] == "offline_stand_in"
    assert prov["model_calls"] == 0
    assert prov["g7_g8_exercised"] is False
    assert prov["g7_g8_detail"].strip()
    assert set(prov["components"]) == {
        "target", "red_strategist", "tripwire", "coroner", "armorer", "warden",
        "gate"}
    # The target's MODEL was scripted. A reader scanning this column must not
    # see `real` beside an agent that could not have been talked into anything.
    assert prov["components"]["target"]["implementation"] == "stand_in"
    assert prov["components"]["tripwire"]["implementation"] == "real"
    assert prov["components"]["warden"]["implementation"] == "real"
    # And every episode says the same thing, per episode.
    for episode in offline_run["bundle"]["episodes"]:
        assert episode["model_provenance"]["downgraded"] is True
        assert episode["model_provenance"]["requested_model_id"]


@adk_only
def test_the_labels_agree_with_the_data_they_describe(offline_run):
    """A label free to disagree with its own bundle is WORSE than a missing one,
    because it is a caveat a reader will believe. The reader cross-checks the k
    against `reps_k`, the split against `sep_by_split` and the tier against
    `target_ref.model_id`; this asserts the producer wrote them that way."""
    bundle = offline_run["bundle"]
    labels = bundle["labels"]
    manifest = bundle["run_manifest"]
    assert "k = %d" % manifest["frozen_parameters"]["reps_k"] in labels["k"]
    for value in bundle["sep_by_split"].values():
        assert str(value) in labels["sep_by_split"]
    assert manifest["target_ref"]["model_id"] in labels["target_tier"]
    # An offline run's tier label must say the tier was not the thing measured.
    assert "THIS RUN DID NOT USE IT" in labels["target_tier"]
    assert "NOT EXERCISED" in labels["trust_root"]
    # The regression bound is COMPUTED from this bundle's own fixture results,
    # never quoted, so it cannot be cited against a corpus it was not measured
    # on. Ruling 43 moved the denominator 24 -> 26 and the bound 12.5% -> ~11.5%.
    assert "%d benign fixtures" % len(bundle["fixture_results"]) in \
        labels["benign_regression"]
    assert "no legitimate behavior was lost" in labels["benign_regression"]


@adk_only
def test_the_frozen_parameters_are_sourced_from_their_owners(offline_run):
    """`benign_floor` carried "24/24" in three places for a day after ruling 43
    moved the suite to 26, and every suite stayed green, because nothing
    compared a literal to its owner."""
    from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR, SEALED_FLOOR
    from crucible.tripwire.known_bad import KNOWN_BAD_IDS

    frozen = offline_run["bundle"]["run_manifest"]["frozen_parameters"]
    assert frozen["benign_floor"] == "%d/%d" % (BENIGN_TOTAL, BENIGN_TOTAL)
    assert frozen["near_miss_floor"] == "%d/%d" % (NEAR_MISS_FLOOR,
                                                   NEAR_MISS_FLOOR)
    assert frozen["known_bad_count"] == len(KNOWN_BAD_IDS)
    assert frozen["sealed_family_min"] == SEALED_FLOOR


@adk_only
def test_the_spine_version_is_read_from_CONVENTIONS_and_never_defaulted(
        offline_run, tmp_path):
    """CONVENTIONS owns the number - "the coordinator changes the value, bumps
    SPINE_VERSION" - so it is parsed rather than typed here, and a file that
    does not carry it REFUSES. A manifest stamped with a spine version nobody
    set cannot say which rulings it was built under."""
    conventions = pathlib.Path("docs/CONVENTIONS.md").read_text(encoding="utf-8")
    assert offline_run["bundle"]["run_manifest"]["spine_version"] == \
        B.spine_version()
    assert "SPINE_VERSION: %d" % B.spine_version() in conventions

    empty = tmp_path / "no-spine.md"
    empty.write_text("nothing here\n", encoding="utf-8")
    with pytest.raises(B.BundleError):
        B.spine_version(empty)
    with pytest.raises(B.BundleError):
        B.spine_version(tmp_path / "does-not-exist.md")


# ---------------------------------------------------------------------------
# 7. THE OFFLINE READER'S OWN VERDICT, END TO END - and the ONE named gap.
# ---------------------------------------------------------------------------

# `Conductor._round` fires ONE autopsy per round, on `breaches[0]`, and says so
# at length: the ARMORER is the highest-judgment lowest-volume role and six
# autopsies of one round produce six patches against one policy. C6's reader
# requires an autopsy for EVERY breach episode. The two are in genuine conflict
# and it is the LOOP's to resolve, not this producer's - the CORONER was never
# called for the second breach, so writing an autopsy for it would be inventing
# a finding.
#
# Pinned here rather than left as a silence so the gap cannot GROW without a
# test going red, and so nobody mistakes the red row for a producer defect.
KNOWN_GAP = "E_AUTOPSY_MISSING_FOR_BREACH"


@adk_only
def test_the_bundle_passes_every_check_the_offline_READER_makes_but_one(
        offline_run):
    """`verify_bundle` is a much stricter instrument than the schema: it
    recomputes the canonical form, cross-checks every episode stamp against the
    manifest, checks the parent links in the chain, checks coverage names the
    Objective Set the run locked, checks the exclusion ledger against its
    denominators, and checks each label against the value it describes.

    Producing a bundle that only VALIDATES would have been the easy half.
    """
    report = verify_bundle(offline_run["bundle"])
    unexpected = [d for d in report.defects if d.code != KNOWN_GAP]
    assert unexpected == [], "\n".join(
        "%s %s: %s" % (d.code, d.where, d.detail) for d in unexpected)
    failing = {row.check for row in report.rows if row.status != "OK"}
    assert failing <= {"AUTOPSIES"}, failing


@adk_only
def test_the_KNOWN_GAP_is_still_exactly_one_round_short_and_not_something_else(
        offline_run):
    """A pinned exemption that stops describing the thing it exempts is how a
    real defect hides behind an old note. This asserts the gap is what the note
    says it is: MORE BREACH EPISODES THAN AUTOPSIES, one autopsy per round, and
    nothing else."""
    bundle = offline_run["bundle"]
    breaches = [e for e in bundle["episodes"]
                if e["verdict"]["verdict"] == "BREACH"]
    rounds_with_a_breach = {e["round_index"] for e in breaches}
    assert len(bundle["autopsies"]) == len(rounds_with_a_breach)
    assert len(breaches) > len(bundle["autopsies"])
    # Every autopsy that IS present names an attack an episode ran.
    named = {e["attack_id"] for e in bundle["episodes"]}
    for record in bundle["autopsies"]:
        assert record["attack_id"] in named


# ---------------------------------------------------------------------------
# 8. COVERAGE - which part of the definition of breach was actually reached.
# ---------------------------------------------------------------------------

@adk_only
def test_clause_coverage_counts_EVERY_clause_including_the_ones_that_never_fired(
        offline_run):
    """`episodes_fired == 0` IS THE FINDING. A rate over an unknown fraction of
    the definition of breach reads as a rate over all of it.

    Coverage is RECOMPUTED with the real `Objective_Set.matches` rather than
    counted from the verdicts, because a verdict cites only the FIRST clause to
    fire and counting from those would undercount every clause that fired behind
    another one.
    """
    bundle = offline_run["bundle"]
    coverage = bundle["clause_coverage"]
    assert coverage["objective_set_hash"] == \
        bundle["run_manifest"]["hash_locks"]["objective_set_hash"]
    assert len(coverage["clauses"]) == 9
    fired = {c["invariant_id"]: c["episodes_fired"] for c in coverage["clauses"]}
    assert any(n == 0 for n in fired.values()), (
        "every clause fired, which would make this field say nothing")
    # Superset of what the verdicts cite - the property the reader cross-checks.
    for episode in bundle["episodes"]:
        verdict = episode["verdict"]
        if verdict["verdict"] == "BREACH":
            assert fired[verdict["invariant_id"]] >= 1


# ---------------------------------------------------------------------------
# 9. THE TWO FILES, AND WHICH ONE IS THE EVIDENCE.
# ---------------------------------------------------------------------------

@adk_only
def test_both_files_are_written_and_neither_states_a_measurement_twice(
        offline_run):
    """`<out>` is the campaign record - `capability_retained`, the hash-lock
    provenance map, the disclaimer, the things C6 has no field for. `<out>.c6.json`
    is the run of record. Attack text, verdicts, rules and every rate live in
    the bundle ONLY: a second copy of a measurement is a second thing to go
    wrong, and this repository has been bitten by exactly that more than once.
    """
    record = _read(offline_run["out"])
    assert set(record) == {"summary", "hashes", "final_policy", "rounds"}
    assert "capability_retained_at_end" in record["summary"]
    assert record["summary"]["no_result_may_be_quoted_from_this_run"]
    # The campaign record carries NO attack text and no C6 key.
    for entry in (r for rnd in record["rounds"] for r in rnd["attacks"]):
        assert "instruction" not in entry
    assert not set(record) & set(offline_run["bundle"])


@adk_only
def test_the_run_says_on_stdout_whether_what_it_wrote_is_evidence(
        monkeypatch, tmp_path, capsys):
    """A producer that wrote an invalid bundle quietly would hand a reader
    something that is not evidence and cannot say so. The banner is printed at
    write time, from the validator's own result."""
    out = tmp_path / "spoken.json"
    assert C.run(["--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "C6 VALIDATION: PASS" in printed
    assert "THE RUN OF RECORD" in printed
    assert C.c6_path(str(out)) in printed
    # BOTH verdicts, and the second is the one that decides whether the demo
    # can render. The offline reader FAILS CLOSED, so a producer that printed
    # only the schema verdict would report PASS on a bundle the viewer refuses -
    # a check that looks green while the thing it checks is broken.
    assert "OFFLINE READER:" in printed
    assert ("ACCEPTS" in printed) or (KNOWN_GAP in printed)


def test_a_failed_validation_is_reported_and_the_file_is_still_written(
        tmp_path, capsys):
    """The rejected document is the only useful artifact there is when the thing
    being debugged is the producer - so it is WRITTEN. What must never happen is
    that it is written SILENTLY, and the exit code must not read as success."""
    path = tmp_path / "broken.c6.json"
    errors, written = B.write_bundle({"bundle_version": 2}, str(path))
    assert errors
    assert pathlib.Path(written).exists()
    printed = capsys.readouterr().out
    assert "C6 VALIDATION: FAILED" in printed
    assert "THIS FILE IS NOT EVIDENCE" in printed
    assert C.EXIT_BUNDLE_INVALID not in (0, C.EXIT_RUN_INVALID, C.EXIT_GATE_HALT)
