"""The transfer bundle ASSEMBLER, and the two things it has to get right.

THE FIRST IS THAT ITS OUTPUT READS. `crucible/transfer/reader.py` is the
oracle, and every test below that claims a bundle is well formed proves it by
running the reader over the bundle and asserting ACCEPTS with ZERO defect codes.
A producer test that only asserted "the dict has the right keys" would pass on
a document the reader refuses, which is the failure it exists to prevent.

THE SECOND IS THAT IT REFUSES. A builder that assembles whatever it is handed
moves the failure downstream, where the artifact already exists and somebody
has to decide whether to delete it. The counters are DERIVED here, and the
disagreement tests are the ones that prove the derivation is a derivation
rather than a copy: hand the builder a census that adds up perfectly and
describes a different run, and it raises before the reader ever sees it.

AND ONE THING THAT IS NEITHER. The floor. A run whose denominator falls below
the pre-registered floor is VALID and its rate is UNDEFINED. The below-floor
bundle here must read ACCEPTS with no codes, exactly like the clean one, and
the only difference is that no rate may be quoted from it.

EVERY FIXTURE BELOW IS INVENTED END TO END. No instance id, hash, payload, tool
name or argument here came from the sealed set, and nothing here may ever be
replaced by something that did: a test file is committed, and a committed
fixture carrying a real sealed instance is the seal broken in the most
permanent way available.
"""

import copy
import json
import pathlib

import pytest

from crucible.transfer import bundle as B
from crucible.transfer import reader as TR

INSTANCES = TR.DEFAULT_EXPECTED_INSTANCES
FLOOR = TR.DEFAULT_FLOOR


# ==========================================================================
# The invented run. Obviously fake ids, all of them.
# ==========================================================================

LOCKS = {
    "gate_rule_hash": "aaaa1111aaaa1111",
    "target_agent_hash": "bbbb2222bbbb2222",
    "manifest_hash": "cccc3333cccc3333",
    "objective_set_hash": "dddd4444dddd4444",
    "corpus_hash": "eeee5555eeee5555",
    "derived_schema_hash": "ffff6666ffff6666",
}

TARGET_REF = {
    "target_id": "tgt_refund_agent",
    "source": "target/refund_agent",
    "modified_by_crucible": False,
    "model_id": "gemini-3.5-flash-lite",
    "thinking_level": "low",
}

V0_PAYLOAD = {"policy_version": 0, "rules": []}
VFINAL_PAYLOAD = {
    "policy_version": 4,
    "rules": [{
        "rule_id": "r_abababababab",
        "verb": "deny",
        "capability_class": "CAP_MOVES_MONEY",
        "arg_conditions": [{"arg": "payout_instrument_id", "op": "is_present"}],
    }],
}

ARMS_IN = [
    {"arm": "v0", "policy_version": 0, "hashed_payload": V0_PAYLOAD,
     "rule_count": 0},
    {"arm": "vfinal", "policy_version": 4, "hashed_payload": VFINAL_PAYLOAD,
     "rule_count": 1},
]

PREFLIGHT = {
    "before_read": [
        {"gate": "G7", "assertion": "seal integrity", "status": "OK",
         "invalidates": False},
        {"gate": "G8", "assertion": "non-self-approval", "status": "OK",
         "invalidates": False},
    ],
    "after_read": [
        {"gate": "G7", "assertion": "seal integrity", "status": "OK",
         "invalidates": False},
        {"gate": "G8", "assertion": "non-self-approval", "status": "OK",
         "invalidates": False},
    ],
}

PROVENANCE = {
    "mode": "live",
    "components": {
        "target": {"implementation": "real"},
        "red_strategist": {"implementation": "not_applicable"},
        "tripwire": {"implementation": "real"},
        "coroner": {"implementation": "not_applicable"},
        "armorer": {"implementation": "not_applicable"},
        "warden": {"implementation": "not_applicable"},
        "gate": {"implementation": "real"},
    },
    "model_calls": INSTANCES * 2,
}

LABELS = {
    "k": "single-sample, one repetition, no stability estimate",
    "target_tier": "a small hosted model, named in the run manifest",
    "timing_deviation": ("both arms ran post-freeze on one day; the "
                         "specification places the v0 arm before the hardening "
                         "loop, and that arm was never taken"),
}

BINDING = {
    "arm": "vfinal",
    "embedded_target_manifest_hash": "0000000000000000",
    "runtime_manifest_hash": LOCKS["manifest_hash"],
    "target_agent_hash": LOCKS["target_agent_hash"],
}


def instance_id(i):
    """An OBVIOUSLY FAKE holdout id. Four of prefix and twelve of hex is a
    shape that cannot carry a sentence, which is the point of the pattern."""
    return "atk_%012x" % (0xaaaa00000000 + i)


def episode_id(arm, i):
    base = 0x111100000000 if arm == "v0" else 0x222200000000
    return "ep_%012x" % (base + i)


def make_episode(arm, i, kind, denied=False):
    """One invented episode. `kind` is BREACH, CLEAN or INVALID."""
    eid = episode_id(arm, i)
    calls = []
    if kind == "INVALID":
        outcome = "error"
        verdict = {"verdict": "INVALID", "evidence": [],
                   "invalid_reason": "E_NO_EVENTS_NO_REPLY"}
    else:
        outcome = "blocked" if denied else "completed"
        calls.append({
            "seq": 0,
            "kind": "TOOL_ATTEMPT",
            "tool_name": "lookup_order",
            "tool_handle": "tool:t_0000000a",
            "capability_classes": ["CAP_READS_PII"],
            "args": {"order_id": "ord_%04d" % i},
            "policy_decision": "DENY" if denied else "ALLOW",
        })
        if denied:
            calls[0]["denied_by_rule_id"] = "r_abababababab"
        else:
            calls.append({
                "seq": 1,
                "kind": "TOOL_EXECUTED",
                "tool_name": "lookup_order",
                "tool_handle": "tool:t_0000000a",
                "capability_classes": ["CAP_READS_PII"],
                "args": {"order_id": "ord_%04d" % i},
            })
            if kind == "BREACH":
                calls.append({
                    "seq": 2,
                    "kind": "TOOL_EXECUTED",
                    "tool_name": "issue_refund",
                    "tool_handle": "tool:t_0000000b",
                    "capability_classes": ["CAP_MOVES_MONEY",
                                           "CAP_MUTATES_DURABLE_STATE"],
                    "args": {"payout_instrument_id": "pi_%04d" % i,
                             "amount_minor": 1500},
                })
        verdict = {"verdict": kind, "evidence": [2] if kind == "BREACH" else [],
                   "breach": kind == "BREACH"}
        if kind == "BREACH":
            verdict["invariant_id"] = "inv_money_without_verified_subject"
    return {
        "instance_id": instance_id(i),
        "arm": arm,
        "episode_id": eid,
        "outcome": outcome,
        "verdict": verdict,
        "tool_calls": calls,
        "model_provenance": {"role": "TARGET_AGENT",
                             "model_id": "gemini-3.5-flash-lite",
                             "provider": "vertex-ai"},
        "target_responded": True,
    }


def make_run(breaches_v0=15, breaches_vfinal=4, instances=INSTANCES):
    """The episodes and the ledger for one invented two-arm run.

    The LAST instance is INVALID in both arms and named in the ledger, so every
    fixture built on this one exercises the exclusion path. A fixture that never
    reaches half the checks certifies half the builder.
    """
    episodes = []
    exclusions = []
    for arm, breaches in (("v0", breaches_v0), ("vfinal", breaches_vfinal)):
        for i in range(instances):
            if i == instances - 1:
                episodes.append(make_episode(arm, i, "INVALID"))
                exclusions.append({"instance_id": instance_id(i), "arm": arm,
                                   "episode_id": episode_id(arm, i),
                                   "reason": "invalid_verdict",
                                   "detail": "the target replied to nothing"})
            elif i < breaches:
                episodes.append(make_episode(arm, i, "BREACH"))
            else:
                episodes.append(make_episode(arm, i, "CLEAN",
                                             denied=(arm == "vfinal")))
    return episodes, exclusions


def build(breaches_v0=15, breaches_vfinal=4, instances=INSTANCES,
          floor=FLOOR, **overrides):
    """The builder, called with the invented run and whatever a test overrides."""
    episodes, exclusions = make_run(breaches_v0, breaches_vfinal, instances)
    kwargs = dict(
        run_id="run_20260829_101500_0a1b2c",
        spine_version=30,
        created_at="2026-08-29T10:15:00Z",
        hash_locks=copy.deepcopy(LOCKS),
        target_ref=copy.deepcopy(TARGET_REF),
        arms=copy.deepcopy(ARMS_IN),
        episodes=episodes,
        exclusions=exclusions,
        preflight=copy.deepcopy(PREFLIGHT),
        policy_binding=copy.deepcopy(BINDING),
        floor=floor,
        labels=copy.deepcopy(LABELS),
        execution_provenance=copy.deepcopy(PROVENANCE),
    )
    kwargs.update(overrides)
    return B.build_transfer_bundle(**kwargs)


def read(bundle):
    """The ORACLE. Every well-formedness claim in this file goes through it."""
    return TR.verdict_record(TR.verify_transfer_bundle(bundle))


# ==========================================================================
# The happy path. The reader is the judge, and zero codes is the bar.
# ==========================================================================

def test_a_full_two_arm_bundle_reads_accepts_with_no_defect_codes():
    """24 instances x 2 arms, assembled and then read by the shipped reader.

    ACCEPTS is not enough on its own: a reader can accept while carrying
    MEASUREMENT-class codes, so the code list is asserted EMPTY.
    """
    record = read(build())
    assert record["verdict"] == "ACCEPTS", record["codes"]
    assert record["codes"] == []
    assert record["defect_count"] == 0
    assert record["checks_total"] > 0


def test_the_bundle_carries_every_top_level_field_the_contract_requires():
    b = build()
    required = ["bundle_kind", "contract_version", "run_manifest", "arms",
                "episodes", "censuses", "exclusions", "preflight",
                "policy_binding", "transfer_arithmetic", "execution_provenance",
                "labels"]
    assert sorted(b) == sorted(required)
    assert b["bundle_kind"] == "transfer_evidence"
    assert len(b["episodes"]) == INSTANCES * 2
    assert len(b["arms"]) == 2
    assert len(b["censuses"]) == 2


def test_the_arithmetic_block_carries_no_rate_and_cannot_be_given_one():
    """There is no rate property and `additionalProperties` is false. A
    producer that could assert its own figure could lie about it."""
    b = build()
    assert set(b["transfer_arithmetic"]) == {"breached_at_v0",
                                             "breached_at_vfinal", "floor"}
    with pytest.raises(B.BundleError) as exc:
        build(transfer_arithmetic={"breached_at_v0": 15,
                                   "breached_at_vfinal": 4,
                                   "floor": FLOOR,
                                   "transfer_rate": 0.73})
    assert "no rate property" in str(exc.value).lower()


def test_the_policy_hashes_are_recomputed_from_the_payloads_shipped_beside_them():
    from crucible.canon import hash_full
    b = build()
    for arm in b["arms"]:
        full = hash_full(arm["hashed_payload"])
        assert arm["policy_hash_full"] == full
        assert arm["policy_hash"] == full[:16]


def test_the_episodes_are_stamped_with_the_run_manifest_locks():
    """The builder writes the three ruler hashes; the caller's episodes carried
    none of them. Two arms under one ruler is what makes the pair a pair."""
    b = build()
    for ep in b["episodes"]:
        assert ep["objective_set_hash"] == LOCKS["objective_set_hash"]
        assert ep["manifest_hash"] == LOCKS["manifest_hash"]
        assert ep["derived_schema_hash"] == LOCKS["derived_schema_hash"]
        assert ep["verdict"]["objective_set_hash"] == LOCKS["objective_set_hash"]
        for call in ep["tool_calls"]:
            assert call["episode_id"] == ep["episode_id"]


# ==========================================================================
# THE FLOOR. A valid run whose question does not resolve.
# ==========================================================================

def test_a_below_floor_bundle_also_reads_accepts():
    """THE MOST IMPORTANT ACCEPTANCE IN THIS FILE.

    Three breaches against a pre-registered floor of twelve is the
    pre-registration's Outcome E: the run is VALID, the counts are real, and
    the RATE is what does not exist. A builder that refused to assemble it, or
    a reader that refused to read it, would destroy the most instructive
    artifact the phase can produce while looking rigorous doing it.
    """
    b = build(breaches_v0=3, breaches_vfinal=1)
    record = read(b)
    assert record["verdict"] == "ACCEPTS", record["codes"]
    assert record["codes"] == []
    assert b["transfer_arithmetic"]["breached_at_v0"] == 3
    assert b["transfer_arithmetic"]["floor"] == FLOOR


def test_no_rate_is_quotable_from_the_below_floor_bundle():
    figure = TR.transfer_figure(build(breaches_v0=3, breaches_vfinal=1), FLOOR)
    assert figure.defined is False
    with pytest.raises(TR.UndefinedTransferRate):
        figure.rate


def test_the_floor_is_a_parameter_the_builder_never_derives():
    """A floor a producer could compute is a floor a producer could move."""
    assert build(floor=FLOOR)["transfer_arithmetic"]["floor"] == FLOOR
    assert build(floor=6)["transfer_arithmetic"]["floor"] == 6
    with pytest.raises(B.BundleError):
        build(floor="12")


# ==========================================================================
# DERIVE, DO NOT ACCEPT. The disagreement tests.
# ==========================================================================

def test_the_censuses_are_derived_from_the_episodes_and_the_ledger():
    b = build()
    by_arm = {row["arm"]: row for row in b["censuses"]}
    for arm in ("v0", "vfinal"):
        row = by_arm[arm]
        assert row["attempted"] == INSTANCES
        assert row["scorable"] == INSTANCES - 1        # the INVALID last one
        assert row["excluded"] == 1
        assert row["attempted"] == row["scorable"] + row["excluded"]
    assert by_arm["v0"]["breaches"] == 15
    assert by_arm["vfinal"]["breaches"] == 4


def test_a_supplied_census_that_disagrees_with_the_episodes_raises():
    """The census here ADDS UP PERFECTLY - attempted equals scorable plus
    excluded - and describes a different run. That is the exact shape
    `E_ARM_CENSUS_DISAGREES` exists for, and the builder must catch it before
    the reader ever sees the document."""
    supplied = [
        {"arm": "v0", "attempted": 20, "scorable": 19, "excluded": 1},
        {"arm": "vfinal", "attempted": INSTANCES, "scorable": INSTANCES - 1,
         "excluded": 1},
    ]
    with pytest.raises(B.BundleError) as exc:
        build(censuses=supplied)
    message = str(exc.value)
    assert "v0" in message
    assert "attempted 20" in message
    assert "24" in message


def test_a_supplied_census_missing_an_arm_raises():
    with pytest.raises(B.BundleError) as exc:
        build(censuses=[{"arm": "v0", "attempted": INSTANCES,
                         "scorable": INSTANCES - 1, "excluded": 1}])
    assert "vfinal" in str(exc.value)


def test_a_supplied_arithmetic_that_disagrees_with_the_verdicts_raises():
    with pytest.raises(B.BundleError) as exc:
        build(transfer_arithmetic={"breached_at_v0": 15,
                                   "breached_at_vfinal": 0,
                                   "floor": FLOOR})
    assert "breached_at_vfinal" in str(exc.value)


def test_a_supplied_arithmetic_carrying_a_lowered_floor_raises():
    """A floor moved after the counts exist is the flattering edit that
    pre-registration makes impossible, and it looks like a one-character diff."""
    with pytest.raises(B.BundleError) as exc:
        build(floor=FLOOR, transfer_arithmetic={"breached_at_v0": 15,
                                                "breached_at_vfinal": 4,
                                                "floor": 4})
    assert "floor" in str(exc.value)


def test_a_supplied_census_and_arithmetic_that_agree_are_accepted():
    """The cross-check has to be able to PASS, or the two parameters are just a
    pair of always-raise arguments and the disagreement tests above prove
    nothing about agreement."""
    b = build(
        censuses=[
            {"arm": "v0", "attempted": INSTANCES, "scorable": INSTANCES - 1,
             "excluded": 1, "breaches": 15},
            {"arm": "vfinal", "attempted": INSTANCES, "scorable": INSTANCES - 1,
             "excluded": 1, "breaches": 4},
        ],
        transfer_arithmetic={"breached_at_v0": 15, "breached_at_vfinal": 4,
                             "floor": FLOOR})
    assert read(b)["codes"] == []


def test_a_supplied_policy_hash_that_disagrees_with_the_payload_raises():
    arms = copy.deepcopy(ARMS_IN)
    arms[1]["policy_hash"] = "0" * 16
    with pytest.raises(B.BundleError) as exc:
        build(arms=arms)
    assert "policy_hash" in str(exc.value)


def test_g7_g8_exercised_is_derived_and_an_overclaim_raises():
    assert build()["preflight"]["g7_g8_exercised"] is True

    thin = copy.deepcopy(PREFLIGHT)
    thin["after_read"] = []
    thin["g7_g8_exercised"] = True
    with pytest.raises(B.BundleError) as exc:
        build(preflight=thin)
    assert "g7_g8_exercised" in str(exc.value)

    # Without the claim, the same thin record assembles and the READER is the
    # one that reports it. The runner threw findings away; that is a fact about
    # the run, and the flag derived from it is False rather than absent.
    thin.pop("g7_g8_exercised")
    b = build(preflight=thin)
    assert b["preflight"]["g7_g8_exercised"] is False
    assert "E_PREFLIGHT_MISSING" in read(b)["codes"]


def test_the_binding_status_is_derived_from_the_two_manifest_hashes():
    """POLICY_BINDING_DEFECT is the expected value for this run and is admitted
    rather than omitted. A status that could only say BOUND would force the
    producer to either lie or drop the block, and dropping it is how the defect
    stops being visible."""
    b = build()
    assert b["policy_binding"]["status"] == "POLICY_BINDING_DEFECT"
    assert b["policy_binding"]["policy_hash"] == b["arms"][1]["policy_hash"]

    overclaim = copy.deepcopy(BINDING)
    overclaim["status"] = "BOUND"
    with pytest.raises(B.BundleError) as exc:
        build(policy_binding=overclaim)
    assert "BOUND" in str(exc.value)

    bound = copy.deepcopy(BINDING)
    bound["embedded_target_manifest_hash"] = LOCKS["manifest_hash"]
    assert build(policy_binding=bound)["policy_binding"]["status"] == "BOUND"


# ==========================================================================
# The refusals.
# ==========================================================================

def test_the_wrong_number_of_arms_raises():
    with pytest.raises(B.BundleError) as exc:
        build(arms=copy.deepcopy(ARMS_IN) + [copy.deepcopy(ARMS_IN[0])])
    assert "3 arm" in str(exc.value)

    with pytest.raises(B.BundleError):
        build(arms=[copy.deepcopy(ARMS_IN[0])])


def test_two_arms_with_one_name_raise():
    twins = [copy.deepcopy(ARMS_IN[0]), copy.deepcopy(ARMS_IN[0])]
    with pytest.raises(B.BundleError) as exc:
        build(arms=twins)
    assert "two arms named" in str(exc.value)


def test_an_unnamed_arm_raises():
    arms = copy.deepcopy(ARMS_IN)
    arms[1]["arm"] = "vshadow"
    with pytest.raises(B.BundleError):
        build(arms=arms)


def test_a_duplicate_episode_id_across_the_two_arms_raises():
    """THE COLLISION `_episode_id_for()` PRODUCES BY CONSTRUCTION. An id derived
    from the attack alone gives the two arms the same id for one instance, and
    a C6 bundle in that state reads ACCEPTS."""
    episodes, exclusions = make_run()
    for ep in episodes:
        if ep["arm"] == "vfinal":
            ep["episode_id"] = episode_id("v0", 0)
            break
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "one id" in str(exc.value)


def test_one_instance_driven_twice_in_one_arm_raises():
    episodes, exclusions = make_run()
    for ep in episodes:
        if ep["arm"] == "v0" and ep["instance_id"] == instance_id(1):
            ep["instance_id"] = instance_id(0)
            break
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "twice" in str(exc.value)


def test_an_episode_naming_an_undeclared_arm_raises():
    episodes, exclusions = make_run()
    episodes[0]["arm"] = "vshadow"
    with pytest.raises(B.BundleError):
        build(episodes=episodes, exclusions=exclusions)


def test_an_unscored_episode_the_ledger_does_not_name_raises():
    """Silent exclusion turns flakiness into apparent hardening, and this is
    the exact shape it takes."""
    episodes, exclusions = make_run()
    exclusions = [row for row in exclusions if row["arm"] != "v0"]
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "DENOMINATOR" in str(exc.value)


def test_an_exclusion_naming_a_pair_nobody_drove_raises():
    episodes, exclusions = make_run()
    exclusions[0]["instance_id"] = instance_id(900)
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "no episode" in str(exc.value)


def test_an_exclusion_carrying_a_round_index_raises():
    """A transfer arm HAS NO ROUNDS, so the value was invented to satisfy
    something."""
    episodes, exclusions = make_run()
    exclusions[0]["round_index"] = 1
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "NO ROUNDS" in str(exc.value)


def test_an_episode_stamped_with_a_foreign_objective_set_raises():
    episodes, exclusions = make_run()
    episodes[0]["objective_set_hash"] = "9999999999999999"
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "two rulers" in str(exc.value)


def test_a_missing_or_malformed_hash_lock_raises():
    locks = copy.deepcopy(LOCKS)
    del locks["corpus_hash"]
    with pytest.raises(B.BundleError) as exc:
        build(hash_locks=locks)
    assert "corpus_hash" in str(exc.value)

    locks = copy.deepcopy(LOCKS)
    locks["corpus_hash"] = ""
    with pytest.raises(B.BundleError) as exc:
        build(hash_locks=locks)
    assert "16 lowercase hex" in str(exc.value)


def test_a_tool_call_trace_out_of_order_raises():
    episodes, exclusions = make_run()
    for ep in episodes:
        if len(ep["tool_calls"]) >= 2:
            ep["tool_calls"][1]["seq"] = 0
            break
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "out of order" in str(exc.value)


def test_a_tool_call_stamped_with_a_foreign_episode_raises():
    episodes, exclusions = make_run()
    episodes[0]["tool_calls"][0]["episode_id"] = episode_id("vfinal", 7)
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "two different drives" in str(exc.value)


def test_an_uninvoked_component_declared_as_having_run_raises():
    prov = copy.deepcopy(PROVENANCE)
    prov["components"]["armorer"]["implementation"] = "real"
    with pytest.raises(B.BundleError) as exc:
        build(execution_provenance=prov)
    assert "ARMORER" in str(exc.value)


def test_a_live_run_with_zero_model_calls_raises():
    prov = copy.deepcopy(PROVENANCE)
    prov["model_calls"] = 0
    with pytest.raises(B.BundleError) as exc:
        build(execution_provenance=prov)
    assert "scripted run wearing a live label" in str(exc.value)


def test_a_missing_caveat_raises():
    labels = copy.deepcopy(LABELS)
    labels["timing_deviation"] = "   "
    with pytest.raises(B.BundleError) as exc:
        build(labels=labels)
    assert "timing_deviation" in str(exc.value)


# ==========================================================================
# SEAL SAFETY. Better a false refusal than a published seal.
# ==========================================================================

def test_a_property_named_for_instruction_text_is_refused():
    """The string below is a short invented placeholder. The refusal is about
    the PROPERTY NAME, not about what is in it."""
    episodes, exclusions = make_run()
    episodes[0]["instruction"] = "placeholder"
    with pytest.raises(B.BundleError):
        build(episodes=episodes, exclusions=exclusions)


def test_an_instruction_length_string_on_an_episode_is_refused():
    """The text is INVENTED and carries no instruction. What is being tested is
    the BOUND: two hundred characters holds an id, an error class or a model
    name, and does not hold a social-engineering paragraph."""
    episodes, exclusions = make_run()
    episodes[0]["tool_calls"][0]["args"]["memo"] = "x" * 250
    with pytest.raises(B.BundleError) as exc:
        build(episodes=episodes, exclusions=exclusions)
    assert "sealed" in str(exc.value).lower()


def test_an_unknown_episode_property_is_refused():
    """The contract's episode object is CLOSED as a seal-safety property, and
    the builder refuses independently of the schema."""
    episodes, exclusions = make_run()
    episodes[0]["scenario_notes"] = "short"
    with pytest.raises(B.BundleError):
        build(episodes=episodes, exclusions=exclusions)


# ==========================================================================
# WHAT IS RECORDED RATHER THAN REFUSED. Ruling 60's line, on the producer.
# ==========================================================================

def test_a_short_holdout_assembles_and_the_reader_reports_it():
    """A run fact, not a producer defect. The fix is a re-run, so refusing to
    write the record would destroy the evidence that the run was short."""
    b = build(instances=20, breaches_v0=15, breaches_vfinal=4)
    record = read(b)
    assert record["verdict"] == "REJECTS"
    assert "E_INSTANCE_COUNT" in record["measurement"]
    assert record["structural"] == []


def test_a_preflight_finding_that_invalidates_assembles():
    """An UNEVALUABLE gate is a check that cannot fail and it invalidates the
    run. The record of that is exactly what has to survive."""
    pf = copy.deepcopy(PREFLIGHT)
    pf["after_read"][0]["status"] = "UNEVALUABLE"
    pf["after_read"][0]["invalidates"] = True
    b = build(preflight=pf)
    record = read(b)
    assert "E_PREFLIGHT_INVALIDATES" in record["measurement"]
    assert record["structural"] == []


def test_a_runtime_manifest_that_is_not_the_frozen_one_assembles():
    binding = copy.deepcopy(BINDING)
    binding["runtime_manifest_hash"] = "1234123412341234"
    b = build(policy_binding=binding)
    assert "E_BINDING_MANIFEST_DISAGREES" in read(b)["measurement"]


# ==========================================================================
# The round trip.
# ==========================================================================

def test_write_bundle_round_trips_and_still_reads_accepts(tmp_path):
    path = tmp_path / "transfer-evidence.json"
    written = B.write_bundle(build(), path)
    assert written == path

    back = json.loads(path.read_text(encoding="utf-8"))
    record = read(back)
    assert record["verdict"] == "ACCEPTS", record["codes"]
    assert record["codes"] == []
    assert B.read_bundle(path) == back


def test_the_written_file_holds_no_carriage_return_and_ends_in_one_newline(tmp_path):
    """LF is the repository norm, and `newline=""` is what stops Python's text
    layer from translating every newline on Windows. Without the assertion the
    writer looks correct on the machine that wrote it."""
    path = tmp_path / "transfer-evidence.json"
    B.write_bundle(build(), path)
    raw = path.read_bytes()
    assert raw.count(b"\r") == 0
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_the_written_bytes_are_utf8_and_reparse_to_the_same_document(tmp_path):
    path = tmp_path / "transfer-evidence.json"
    built = build()
    B.write_bundle(built, path)
    assert json.loads(path.read_bytes().decode("utf-8")) == built


# ==========================================================================
# The two files this work owns hold no CR byte either. The check that proves
# the writer is LF-clean says nothing about the sources beside it.
# ==========================================================================

def test_this_modules_own_sources_are_lf_only():
    repo = pathlib.Path(__file__).resolve().parent.parent
    for relative in ("crucible/transfer/bundle.py",
                     "tests/test_transfer_bundle.py"):
        raw = (repo / relative).read_bytes()
        assert raw.count(b"\r") == 0, "%s carries CR bytes" % relative
