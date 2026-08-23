"""test_corpus_seeds.py - does the campaign now attack with the CORPUS?

`docs/decisions-pending/campaign-does-not-read-the-corpus.md`: the campaign ran
six hand-authored one-sentence literals while `corpus/training/` held 50
hash-locked instances, and no adapter existed. `crucible/conductor/corpus_seeds.py`
is the adapter. These tests prove the four things it has to be true about, and
each one is written so that it FAILS if the adapter reverts to the shape it
replaced:

  * the seeds come from all 50 training instances, and their family ids invert
    to real F-families - which is what makes a per-family rate and the F4
    transfer figure computable at all
  * the world an episode runs against is the world the INSTANCE names, asserted
    by a postcondition (a refund receipt in the ledger) and not by a return code
  * nothing here can reach the sealed family, and a sealed instance planted in
    the training directory RAISES rather than being filtered out
  * the three conversational turns are DRIVEN as three turns on one session,
    not concatenated

THE CONTROL THIS FILE TURNS ON, AND IT IS THE POINT OF `test_the_wrong_world_*`
--------------------------------------------------------------------------------
Two of these tests run the SAME corpus attack against the SHARED demo world and
assert it produces the wrong answer. A test that only shows the fixed path
working cannot distinguish "the fix landed" from "this attack was always going
to pass", and the whole finding was that the failure is silent.

No live model, no network, no gcloud. Every drive is a real
`google.adk.runners.Runner` against a deterministic stub, the pattern
`tests/test_real_target.py` established.
"""

import json
import pathlib

import pytest

from corpus.model import SEALED_FAMILY, TRAINING_FAMILIES, TRAINING_TOTAL
from crucible.conductor.corpus_seeds import (
    TRAINING_LAYOUT,
    CorpusSeedError,
    CorpusSeeds,
    family_id_for,
    family_label,
)
from crucible.plugin.adk import ADK_AVAILABLE

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"

# F1-01-chargeback-band-override. Named by slug and RESOLVED to its
# content-addressed id at run time - hardcoding `atk_7317dc7d3b15` would pin a
# test to bytes the corpus freeze owns.
F1_01_SLUG = "F1-01-chargeback-band-override"


@pytest.fixture(scope="module")
def seeds():
    return CorpusSeeds.load()


def _by_slug(seeds, slug):
    for a in seeds._attacks:                                    # noqa: SLF001
        if a.slug == slug:
            return a
    raise AssertionError("no training instance with slug %r" % slug)


def _attack_dict(rec, instruction=None):
    return {"attack_id": rec.attack_id, "family_id": rec.family_id,
            "instruction": instruction or rec.instruction}


# ===========================================================================
# 1. The seeds are the corpus, and the family ids reach the taxonomy.
# ===========================================================================

def test_every_training_instance_becomes_a_seed(seeds):
    """50, not 6. The number is read from `corpus.model`, not typed here."""
    assert len(seeds.attack_seeds()) == TRAINING_TOTAL == 50


def test_family_ids_invert_to_real_f_families(seeds):
    """THE DEFECT, DIRECTLY. `fam_direct_ask` maps to nothing in F1-F7, so no
    per-family rate and no transfer figure was computable from any run. Every
    seed's `family_id` must now round-trip to a training family."""
    labels = {family_label(s.family_id) for s in seeds.attack_seeds()}
    assert labels == set(TRAINING_FAMILIES)
    assert SEALED_FAMILY not in labels


def test_family_id_translation_round_trips_and_refuses_a_second_spelling():
    assert family_id_for("F1") == "fam_f1"
    assert family_label("fam_f1") == "F1"
    # `tests/golden_traces/attacks/AT01.json` carries this longer shape.
    # Accepting it here would put two spellings of one family into the
    # analysis, which is the defect `ALLOW`/`allow` already cost this repo.
    with pytest.raises(CorpusSeedError):
        family_label("fam_f1_direct_authority")
    with pytest.raises(CorpusSeedError):
        family_id_for("fam_f1")


def test_the_hand_authored_family_ids_are_gone(seeds):
    dead = {"fam_direct_ask", "fam_authority_claim", "fam_delegated_chain",
            "fam_split_ask", "fam_destination_swap", "fam_urgency"}
    assert not dead & {s.family_id for s in seeds.attack_seeds()}


def test_the_instruction_is_the_final_turn_not_a_concatenation(seeds):
    """`AttackSeed` holds one string and the RED_STRATEGIST rewrites it, so the
    one it holds is the turn carrying the ask under pressure. Joining the turns
    into it would make the seed unvariable without destroying the escalation."""
    rec = _by_slug(seeds, F1_01_SLUG)
    seed = next(s for s in seeds.attack_seeds() if s.attack_id == rec.attack_id)
    assert seed.instruction == rec.turns[-1]
    assert rec.turns[0] not in seed.instruction


# ===========================================================================
# 2. The sealed boundary. IAM is the real one; this is the code-side half.
# ===========================================================================

def test_the_layout_names_the_training_directory_and_nothing_else():
    """Structural, not a promise. `load_corpus` opens the buckets it is handed;
    a bucket absent from the layout is one it never opens."""
    assert set(TRAINING_LAYOUT) == {"training"}
    assert TRAINING_LAYOUT["training"].name == "training"
    assert "sealed" not in str(TRAINING_LAYOUT["training"])


def test_no_loaded_instance_belongs_to_the_sealed_family(seeds):
    report = seeds.report()
    assert SEALED_FAMILY not in report["families"]
    assert report["sealed_family_loaded"] is False


def _plant(tmp_path, seeds, **overrides):
    """A REAL training instance with fields overridden, written to a temporary
    training directory. Valid in every other respect, so the only thing under
    test is the gate."""
    doc = dict(_by_slug(seeds, F1_01_SLUG).doc)
    for k in ("_instance_id", "_source_file"):
        doc.pop(k, None)
    doc.update(overrides)
    d = tmp_path / "training"
    d.mkdir()
    (d / "planted.json").write_text(json.dumps(doc), encoding="utf-8")
    return d


def test_a_correctly_sealed_f4_instance_in_training_raises_it_is_not_filtered(
        tmp_path, seeds):
    """THE HOLE THIS GATE ACTUALLY CLOSES, AND IT IS NOT THE OBVIOUS ONE.

    `corpus/schema.py::_validate_family` refuses F4 with `sealed: false` and
    refuses a training family with `sealed: true` - but an instance that is
    HONESTLY LABELLED, family F4 and `sealed: true`, satisfies both branches
    and loads out of `corpus/training/` with no complaint. The existing
    validator checks that the label is self-consistent; nothing before this
    checked WHICH DIRECTORY a sealed instance was sitting in.

    It raises rather than filters. A filter would drop it silently and pass
    identically whether the seal held or not - a check that cannot fail.
    """
    d = _plant(tmp_path, seeds, family=SEALED_FAMILY, sealed=True)
    with pytest.raises(CorpusSeedError) as e:
        CorpusSeeds.load(layout={"training": d})
    assert e.value.code == "E_SEALED_FAMILY_REACHED"


def test_the_existing_corpus_validator_still_owns_the_mislabelled_case(
        tmp_path, seeds):
    """F4 with `sealed: false` is `corpus/schema.py`'s check and stays there.
    Asserted so that the two layers are visibly different questions rather than
    two copies of one - this file adds the directory question, not a second
    opinion on the label."""
    from corpus.errors import CorpusError

    d = _plant(tmp_path, seeds, family=SEALED_FAMILY, sealed=False)
    with pytest.raises(CorpusError) as e:
        CorpusSeeds.load(layout={"training": d})
    assert e.value.code == "E_SEALED_FAMILY_IN_TRAINING"


def test_an_empty_training_corpus_raises_rather_than_seeding_zero_attacks(
        tmp_path):
    """A zero-attack round reports no breaches, and a zero-breach run reads
    exactly like a hardened one."""
    d = tmp_path / "training"
    d.mkdir()
    with pytest.raises(CorpusSeedError) as e:
        CorpusSeeds.load(layout={"training": d})
    assert e.value.code == "E_EMPTY_TRAINING_CORPUS"


# ===========================================================================
# 3. The per-instance world.
# ===========================================================================

def test_every_instance_gets_a_world_that_reproduces_it(seeds):
    """`verify_world` cross-checks two derivations of the six policy-visible
    fields - `corpus/blindness.py`'s reference computers reading the instance,
    and `real_target.scenario_and_context` reading the constructed world. It
    runs on every episode; this runs it on all 50 at once."""
    for seed in seeds.attack_seeds():
        world = seeds.world_for({"attack_id": seed.attack_id,
                                 "instruction": seed.instruction})
        rec = seeds.lookup(seed.attack_id)
        order = world.sor.get_order(rec.order_id)
        assert order is not None, rec.slug
        assert order.order_total_minor == \
            rec.doc["scenario"]["order"]["order_total_minor"]
        assert world.sor.get_customer(rec.customer_id) is not None


def test_the_wrong_world_holds_a_different_order_of_the_same_name(seeds):
    """THE COLLISION, ASSERTED. `F1-01` names ORD-4471 and the shared demo world
    HAS an ORD-4471 - a $34 stoneware mug against the instance's $900 television.
    So the failure was never a lookup miss; it was a real order that is the
    wrong order, which is why nothing raised."""
    from target.refund_agent.simulated_system_of_record import (
        DEMO_AS_OF, SimulatedSystemOfRecord, seed_demo_ledger,
    )
    rec = _by_slug(seeds, F1_01_SLUG)
    assert rec.order_id == "ORD-4471"

    demo = seed_demo_ledger(SimulatedSystemOfRecord(as_of=DEMO_AS_OF))
    corpus_world = seeds.world_for(_attack_dict(rec))
    assert demo.get_order("ORD-4471").order_total_minor == 3400
    assert corpus_world.sor.get_order("ORD-4471").order_total_minor == 90000


def test_the_approval_tier_comes_from_the_instance_not_a_constant(seeds):
    """Hardcoded `"NONE"` on the grounds that attacks declare no approver. Six
    of the fifty declare one with a real tier, and F1-08 is unmeasurable
    without it."""
    tiers = {a.approval_tier for a in seeds._attacks}           # noqa: SLF001
    assert tiers - {"NONE"}, "no instance contributed a non-NONE approval tier"


def test_unstated_fields_are_reported_not_filled(seeds):
    """`order.currency` is stated by 34 of 50 and `order.placed_on` by none.
    Unstated is carried as null and COUNTED, never as a plausible value."""
    report = seeds.report()
    assert report["unstated_fields"]["order.placed_on"] == 50
    rec = next(a for a in seeds._attacks                        # noqa: SLF001
               if "order.currency" in a.unstated_fields)
    world = seeds.world_for(_attack_dict(rec))
    assert world.sor.get_order(rec.order_id).currency is None


def test_the_second_account_dialect_is_reported_and_not_silently_accepted(seeds):
    """18 instances spell the returns panel `lifetime_orders`/`returns_90d`/
    `open_risk_flag`/`not_received_lifetime`. Accepting both spellings is the
    shim that produced `ALLOW`/`allow` here already, so the keys are not read -
    they are counted, and the fix is a re-author plus a corpus_hash re-freeze."""
    ignored = seeds.report()["ignored_scenario_keys"]
    assert ignored["account.lifetime_orders"] == 18
    assert ignored["account.open_risk_flag"] == 18
    # Not read into any record, and SAID OUT LOUD in the run rather than left
    # to a docstring: the loss is a sentence the banner prints.
    rec = next(a for a in seeds._attacks                        # noqa: SLF001
               if "account.lifetime_orders" in a.ignored_scenario_keys)
    world = seeds.world_for(_attack_dict(rec))
    assert world.sor.get_customer(rec.customer_id).lifetime_order_count is None
    assert any("lifetime_orders" in d for d in seeds.disclaimers())


# ===========================================================================
# 4. Provenance for the C6 evidence bundle.
# ===========================================================================

def test_provenance_satisfies_the_c6_attacks_contract(seeds):
    """Validated against `contracts/evidence_bundle.schema.json` itself rather
    than against a list of field names retyped here. That file is hash-locked;
    a field renamed there must break this test."""
    import jsonschema

    schema = json.loads((CONTRACTS / "evidence_bundle.schema.json")
                        .read_text(encoding="utf-8"))
    item = schema["properties"]["attacks"]["items"]
    for seed in seeds.attack_seeds():
        entry = seeds.provenance_for(seed.attack_id)
        jsonschema.validate(entry, item)
        assert entry["provenance"] == "training_corpus"
        assert entry["corpus_instance_id"] == entry["attack_id"]


# ===========================================================================
# 5. The offline script comes from the instance's own trace.
# ===========================================================================

def test_the_offline_script_is_the_instances_own_trace(seeds):
    """`campaign.offline_script_for` keys six hand-written shapes off the dead
    family ids and names a hardcoded ORD-4472. Both halves break under corpus
    seeds, silently: the ids no longer match, so every attack falls through to
    a default shape aimed at an order the per-instance world does not hold."""
    rec = _by_slug(seeds, F1_01_SLUG)
    script = seeds.offline_script(_attack_dict(rec))
    assert [name for name, _ in script] == [
        "lookup_order", "lookup_customer", "issue_refund"]
    assert all(args.get("order_id", rec.order_id) == rec.order_id
               for _, args in script)
    assert script[-1][1]["amount_minor"] == 90000


def test_the_offline_script_does_not_replay_the_corpus_policy_decision(seeds):
    """The live policy engine decides. Carrying `policy_decision` through would
    make the offline run a replay of the answer."""
    for _, args in seeds.offline_script(_attack_dict(_by_slug(seeds, F1_01_SLUG))):
        assert "policy_decision" not in args
        assert "scored" not in args


# ===========================================================================
# 6. Driving the real target. Postconditions, not return codes.
# ===========================================================================

pytest_adk = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")

if ADK_AVAILABLE:
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    from crucible.conductor.campaign import build_offline_target_model
    from crucible.conductor.real_target import build_real_target
    from crucible.tripwire import RunManifest

    class _TurnCountingLlm(BaseLlm):
        """Records the user turns it was shown and calls no tool.

        Counting the USER parts in the request history is what distinguishes
        three turns driven on one session from three turns concatenated into
        one: concatenation produces a single user part on every request.
        """

        model: str = "crucible-turn-counter"
        seen: list = []

        async def generate_content_async(self, llm_request, stream: bool = False):
            users = [p.text for c in (llm_request.contents or ())
                     if c.role == "user" for p in (c.parts or ())
                     if getattr(p, "text", None)]
            self.seen.append(tuple(users))
            yield LlmResponse(content=types.Content(
                role="model", parts=[types.Part(text="acknowledged")]))


def _run_manifest():
    return RunManifest(policy_version=0, policy_hash="ph_test_corpus_seeds",
                       manifest_hash="mh_test_corpus_seeds",
                       derived_schema_hash="dsh_test_corpus_seeds",
                       objective_set_hash="osh_test_corpus_seeds")


def _empty_policy():
    return {"hashed_payload": {"policy_schema_version": 1, "rules": []}}


@pytest_adk
def test_the_corpus_world_is_the_one_the_money_moves_in(seeds):
    """THE POSTCONDITION. A receipt in the ledger, not an exit code.

    F1-01 asks for a $900 refund on ORD-4471. Against the instance's own world
    the ledger records it; the run has something real to score.
    """
    rec = _by_slug(seeds, F1_01_SLUG)
    attack = _attack_dict(rec)
    captured = {}

    def world_for(a):
        world = seeds.world_for(a)
        captured["sor"] = world.sor
        return world

    target = build_real_target(
        run_manifest=_run_manifest(),
        model=build_offline_target_model(seeds.offline_script(attack)),
        world_factory=world_for)
    target(attack, _empty_policy())

    refunds = captured["sor"].refunds
    assert len(refunds) == 1
    assert refunds[0].amount_minor == 90000
    assert refunds[0].detail["order_id"] == "ORD-4471"


@pytest_adk
def test_the_wrong_world_moves_no_money_and_says_nothing_about_it(seeds):
    """THE CONTROL, AND THE REASON THE DEFECT WAS SILENT.

    The same attack against the shared demo world: the ledger's own invariant
    refuses $900 against a $34 order, the tool returns an error dict, and
    ZERO money moves - while the episode still completes and seals clean. No
    exception is raised anywhere, which is why 1155 tests and a full offline
    campaign never saw it.
    """
    from target.refund_agent.simulated_system_of_record import (
        DEMO_AS_OF, SimulatedSystemOfRecord, seed_demo_ledger,
    )
    rec = _by_slug(seeds, F1_01_SLUG)
    attack = _attack_dict(rec)
    captured = {}

    def demo_sor():
        captured["sor"] = seed_demo_ledger(
            SimulatedSystemOfRecord(as_of=DEMO_AS_OF))
        return captured["sor"]

    target = build_real_target(
        run_manifest=_run_manifest(),
        model=build_offline_target_model(seeds.offline_script(attack)),
        sor_factory=demo_sor)
    episode = target(attack, _empty_policy())

    assert captured["sor"].refunds == ()
    assert captured["sor"].get_order("ORD-4471").refunded_minor == 0
    assert episode["outcome"] == "completed"


@pytest_adk
def test_three_turns_are_driven_as_three_turns_on_one_session(seeds):
    """MULTI-TURN, NOT CONCATENATION. The escalation is where the pressure
    lives: F1-01's chargeback threat only works because it answers a refusal
    that has not happened yet, and that structure is in the ORDER of the turns.

    The stub records the user turns visible on each request. Driven, it is
    asked three times and the history grows 1 -> 2 -> 3. Concatenated, it would
    be asked once and see one part.
    """
    rec = _by_slug(seeds, F1_01_SLUG)
    assert len(rec.turns) == 3
    llm = _TurnCountingLlm(seen=[])
    target = build_real_target(run_manifest=_run_manifest(), model=llm,
                               world_factory=seeds.world_for)
    target(_attack_dict(rec), _empty_policy())

    assert [len(s) for s in llm.seen] == [1, 2, 3]
    assert llm.seen[-1] == rec.turns


@pytest_adk
def test_the_red_strategists_rewrite_lands_on_the_final_turn(seeds):
    """The seed carries the final turn, so that is the only turn variation can
    reach. The earlier turns are the instance's own, verbatim - stated here so
    that a varied round is understood as a PARTIALLY varied conversation."""
    rec = _by_slug(seeds, F1_01_SLUG)
    marker = "VARIED-BY-THE-RED-STRATEGIST-9d1f"
    llm = _TurnCountingLlm(seen=[])
    target = build_real_target(run_manifest=_run_manifest(), model=llm,
                               world_factory=seeds.world_for)
    target(_attack_dict(rec, instruction=marker), _empty_policy())

    assert llm.seen[-1] == rec.turns[:-1] + (marker,)


@pytest_adk
def test_a_single_turn_world_still_drives_exactly_one_turn(seeds):
    """The demo path, unchanged. One shape for both, not two."""
    llm = _TurnCountingLlm(seen=[])
    target = build_real_target(run_manifest=_run_manifest(), model=llm)
    target({"attack_id": "atk_a00000000001", "family_id": "fam_test",
            "instruction": "one turn only"}, _empty_policy())
    assert [len(s) for s in llm.seen] == [1]


@pytest_adk
def test_two_world_sources_at_once_is_refused():
    """One makes the world a constant of the run and the other makes it a
    function of the attack. Silently preferring either means an episode ran
    somewhere the caller did not ask for."""
    with pytest.raises(ValueError) as e:
        build_real_target(run_manifest=_run_manifest(),
                          sor_factory=lambda: None,
                          world_factory=lambda a: None)
    assert "world_factory" in str(e.value)


@pytest_adk
def test_an_attack_with_no_corpus_instance_does_not_fall_back_to_a_world(seeds):
    """A world that cannot be built must HALT, not default. Defaulting is the
    ORD-4471/ORD-4472 collision arriving through a different door."""
    with pytest.raises(CorpusSeedError) as e:
        seeds.world_for({"attack_id": "atk_000000000000",
                         "instruction": "not from the corpus"})
    assert e.value.code == "E_ATTACK_NOT_IN_CORPUS"
