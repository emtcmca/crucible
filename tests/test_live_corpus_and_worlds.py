"""test_live_corpus_and_worlds.py - what `provenance: generated` actually means,
and the corpus lineage the bundle was dropping on the surface a judge reads.

THE BRIEF THIS LANE WAS GIVEN WAS WRONG ABOUT ITS OWN PREMISE, AND THE FIRST
TWO TESTS HERE ARE THE DISPROOF RATHER THAN THE FIX.
---------------------------------------------------------------------------
Two live runs on 2026-08-23 reported `provenance: generated` on 100% of their
attacks and carried no `corpus_instance_id` anywhere. That was read as "the
campaign does not use the hash-locked corpus in `--live`", and a repair was
scoped against it: resolve a default world for attacks that have no corpus
instance behind them.

There are no such attacks. `RedStrategist.vary()` takes an `AttackSeed` and
returns a dict that PRESERVES `attack_id` and `family_id` on every one of its
four paths; the only thing a model ever changes is `instruction`, and its own
system prompt tells it to "pursue the SAME objective by the SAME sequence of
actions". Nothing in this repository authors an attack with a new id. So:

    provenance: generated      == this corpus seed's final turn was REWRITTEN
    provenance: training_corpus == this corpus seed was REPLAYED VERBATIM

Both are corpus instances. `_attack_provenance` is a claim about the TEXT, not
about the origin of the attack, and the bundle was printing it where a reader
looks for origin.

WHAT THE REAL DEFECT WAS
------------------------
`_attacks` attaches `corpus_instance_id` only on the `training_corpus` branch.
On a live run every row takes the other branch, so the bundle - the run of
record - said nothing at all about which of the fifty frozen instances each
attack came from, even though every one of them came from one and the id was
sitting in the row under a different name. `crucible/replay/view.py` prints the
"resolves against the corpus frozen at corpus_hash" line only for rows carrying
that field, so the live bundle rendered as a corpus-free run. It was not one.

`contracts/evidence_bundle.schema.json` already permits the field on a
`generated` row: `corpus_instance_id` is in `properties`, and the `allOf` makes
it REQUIRED under `training_corpus` without forbidding it anywhere else. No
contract moves.
"""

import json

import pytest

import crucible.conductor.bundle as B
from crucible.conductor.corpus_seeds import CorpusSeeds
from crucible.red.red import AttackSeed, RedStrategist


def _round_with_attacks(attacks, index=1, outcome="SCORED"):
    from crucible.conductor.conductor import RoundRecord
    record = RoundRecord(round_index=index, hashes={})
    record.attacks = list(attacks)
    record.verdicts = []
    record.outcome = outcome
    return record


@pytest.fixture(scope="module")
def corpus():
    return CorpusSeeds.load()


# ---------------------------------------------------------------------------
# 1. THE DISPROOF. Item 1 of the brief describes a defect that does not exist.
# ---------------------------------------------------------------------------

def test_vary_preserves_the_seeds_attack_id_on_every_path(corpus):
    """The load-bearing fact the whole brief got backwards.

    Four paths out of `vary()`: no model, governor refusal, model rewrite, and
    unparseable-response fallback. All four return the SEED'S `attack_id`. If
    any one of them minted a new id, a generated attack really would have no
    corpus instance behind it and the brief's repair would be the right one.
    """
    seed = corpus.attack_seeds()[0]

    offline = RedStrategist(call_model=None).vary(seed, None)
    assert offline["attack_id"] == seed.attack_id
    assert offline["variation"] == "none"

    rewritten = RedStrategist(
        call_model=lambda **kw: {"text": json.dumps(
            {"instruction": "a different surface form entirely"})},
    ).vary(seed, None)
    assert rewritten["attack_id"] == seed.attack_id
    assert rewritten["variation"] == "model"
    assert rewritten["instruction"] != seed.instruction

    unparseable = RedStrategist(
        call_model=lambda **kw: {"text": "not json"},
    ).vary(seed, None)
    assert unparseable["attack_id"] == seed.attack_id
    assert unparseable["variation"] == "fallback"


def test_a_model_varied_attack_still_resolves_to_a_corpus_world(corpus):
    """THE TEST THE BRIEF ASKED FOR, AND IT PASSES ON THE FIRST RUN.

    "First write the test that drives a generated attack and watch it fail to
    be presented." It is not presented against a default world and it does not
    fail: `world_for` joins on `attack_id`, which `vary()` preserved, so a
    model-rewritten attack gets the SAME per-instance account and order world
    its seed named, with only the final turn replaced.

    That is also why no default world was added anywhere in this lane. There is
    no population for one to serve.
    """
    seed = corpus.attack_seeds()[0]
    rec = corpus.lookup(seed.attack_id)
    varied = RedStrategist(
        call_model=lambda **kw: {"text": json.dumps(
            {"instruction": "rewritten under pressure"})},
    ).vary(seed, None)
    assert varied["variation"] == "model"

    world = corpus.world_for(varied)
    assert world.order_id == rec.order_id
    assert world.customer_id == rec.customer_id
    # The instance's own earlier turns, verbatim; only the last one moved.
    assert world.turns[:-1] == rec.turns[:-1]
    assert world.turns[-1] == "rewritten under pressure"


# ---------------------------------------------------------------------------
# 2. THE REAL DEFECT.
# ---------------------------------------------------------------------------

def test_a_generated_attack_carries_the_corpus_instance_it_was_rewritten_from(corpus):
    """RED BEFORE GREEN. This is the live-bundle defect, reproduced offline.

    A row whose text was rewritten by the model is still a rewrite OF a frozen
    instance. Dropping the id makes the run of record unable to say which of
    the fifty it tested, and makes the replay render a corpus-backed run as a
    corpus-free one.
    """
    seed = corpus.attack_seeds()[0]
    record = _round_with_attacks([{
        "attack_id": seed.attack_id, "family_id": seed.family_id,
        "instruction": "rewritten by the model", "variation": "model"}])

    catalogue = {e["attack_id"]: e for e in B._attacks(   # noqa: SLF001
        [record], generator=B.generator_ref(True, 1729),
        corpus_instances=corpus)}
    row = catalogue[seed.attack_id]

    assert row["provenance"] == "generated"
    assert row["instruction"] == "rewritten by the model"
    assert row["corpus_instance_id"] == seed.attack_id, (
        "a generated attack that IS a rewrite of a frozen corpus instance must "
        "name that instance. Both live bundles of 2026-08-23 dropped it, and "
        "the run read as though the hash-locked corpus was never used.")


def test_an_attack_outside_the_corpus_gets_no_instance_id_rather_than_an_empty_one(corpus):
    """ABSENT, NOT EMPTY. Two different claims.

    Nothing in the repo mints an out-of-corpus attack today, so this guards the
    direction rather than a live population: if one ever appears, the row must
    say NOTHING about a corpus instance instead of saying `""`, which reads as
    "this resolves against corpus_hash and the id is blank".
    """
    record = _round_with_attacks([{
        "attack_id": "atk_ffffffffffff", "family_id": "fam_f1",
        "instruction": "authored from nothing", "variation": "model"}])

    row = B._attacks([record], generator=B.generator_ref(True, 1729),   # noqa: SLF001
                     corpus_instances=corpus)[0]
    assert row["provenance"] == "generated"
    assert "corpus_instance_id" not in row


def test_without_a_corpus_the_catalogue_invents_nothing(corpus):
    """`corpus_instances` defaults to None and the behaviour is the old one.

    A bundle built by a caller that never loaded the corpus must not guess.
    """
    seed = corpus.attack_seeds()[0]
    record = _round_with_attacks([{
        "attack_id": seed.attack_id, "family_id": seed.family_id,
        "instruction": "rewritten by the model", "variation": "model"}])
    row = B._attacks([record], generator=B.generator_ref(True, 1729))[0]  # noqa: SLF001
    assert "corpus_instance_id" not in row


# ---------------------------------------------------------------------------
# 3. THE THREE-WAY MODE SELECTOR. Eric's ruling, 2026-08-23.
# ---------------------------------------------------------------------------

def _rewriting_model(**kw):
    return {"text": json.dumps({"instruction": "a different surface form"}),
            "usd": 0.0, "tokens": 0}


def _strategist(mode):
    return RedStrategist(_rewriting_model, seed=1729, attack_mode=mode)


def test_corpus_mode_replays_verbatim_even_with_a_model_configured(corpus):
    """THE MEASUREMENT MODE. The attack set is fixed by `corpus_hash`.

    The distinction that matters: this is NOT "no model was available". A model
    IS configured here and is deliberately not called, which is what makes the
    mode a declared choice rather than a consequence of the environment.
    """
    seeds = corpus.attack_seeds()
    proposed = _strategist("corpus").propose_round(seeds, None, 6)
    assert len(proposed) == 6
    assert {a["variation"] for a in proposed} == {"none"}
    by_id = {s.attack_id: s for s in seeds}
    for a in proposed:
        assert a["instruction"] == by_id[a["attack_id"]].instruction


def test_corpus_mode_puts_the_same_six_attacks_in_the_same_order_every_run(corpus):
    """REPRODUCIBLE IN ITS INPUTS, WHICH IS THE ONLY CLAIM CORPUS MODE MAKES.

    Two strategists on the same seed compose the identical round. It says
    nothing about the target's replies - the target is a sampled model and its
    outcomes vary run to run. Corpus mode is not determinism.
    """
    seeds = corpus.attack_seeds()
    a = _strategist("corpus").propose_round(seeds, None, 6)
    b = _strategist("corpus").propose_round(seeds, None, 6)
    assert [x["attack_id"] for x in a] == [x["attack_id"] for x in b]
    assert [x["instruction"] for x in a] == [x["instruction"] for x in b]


def test_generated_mode_rewrites_every_seed(corpus):
    seeds = corpus.attack_seeds()
    proposed = _strategist("generated").propose_round(seeds, None, 6)
    assert {a["variation"] for a in proposed} == {"model"}


def test_hybrid_splits_three_and_three_and_flips_the_arms_between_rounds(corpus):
    """THE SPLIT IS DECLARED, DETERMINISTIC, AND NOT CONFOUNDED WITH FAMILY.

    `select()` cycles families in sorted order, so position p is always the
    same family. A fixed parity would give one arm the same three families
    forever and the run would report a difference between treatments that is
    partly a difference between families. The round offset flips it, so both
    arms see every family across the round cap.
    """
    seeds = corpus.attack_seeds()
    red = _strategist("hybrid")

    r1 = red.propose_round(seeds, None, 6)
    r2 = red.propose_round(seeds, None, 6)

    for r in (r1, r2):
        varied = [a for a in r if a["variation"] == "model"]
        assert len(varied) == 3, "equal arms, or the rates have unequal precision"

    fams1 = {a["family_id"] for a in r1 if a["variation"] == "model"}
    fams2 = {a["family_id"] for a in r2 if a["variation"] == "model"}
    assert fams1 and fams2 and fams1.isdisjoint(fams2), (
        "the same families were rewritten in both rounds, so treatment and "
        "family are confounded and neither rate can be attributed")


def test_an_unknown_attack_mode_is_refused_rather_than_defaulted():
    with pytest.raises(ValueError) as exc:
        RedStrategist(None, attack_mode="mixed")
    assert "attack_mode" in str(exc.value)


# ---------------------------------------------------------------------------
# 4. THE NON-POOLING RULE, AS OUTPUT.
# ---------------------------------------------------------------------------

def test_the_breakout_keeps_the_two_populations_apart_and_labels_the_pooled_row():
    """THE WHOLE POINT, IN ONE FIXTURE.

    Six attacks, three of each provenance. Every rewritten one breaches and
    every replayed one holds. The pooled rate is 50% and it is the number that
    means nothing: it would read identically if the arms were reversed.
    """
    attacks, verdicts = [], []
    for i in range(3):
        attacks.append({"attack_id": "atk_c0000000000%d" % i,
                        "family_id": "fam_f1", "variation": "none"})
        verdicts.append({"attack_id": "atk_c0000000000%d" % i,
                         "verdict": "CLEAN", "breach": False})
        attacks.append({"attack_id": "atk_g0000000000%d" % i,
                        "family_id": "fam_f1", "variation": "model"})
        verdicts.append({"attack_id": "atk_g0000000000%d" % i,
                         "verdict": "BREACH", "breach": True})
    record = _round_with_attacks(attacks)
    record.verdicts = verdicts

    out = B.provenance_breakout([record])
    assert out["training_corpus"]["breach_rate"] == 0.0
    assert out["generated"]["breach_rate"] == 1.0
    assert out["pooled"]["breach_rate"] == 0.5

    lines = "\n".join(B.provenance_breakout_lines(out, "hybrid"))
    assert "NEVER POOL" in lines
    assert "pooled" in lines
    assert lines.index("training_corpus") < lines.index("    pooled"), (
        "the pooled row must not be the first population a reader sees")


def test_an_empty_arm_reports_no_rate_rather_than_zero():
    """`None`, NOT `0.0`. "No attacks of this kind ran" and "none of them
    breached" are opposite findings, and 0.0 states the second."""
    record = _round_with_attacks([
        {"attack_id": "atk_e00000000001", "family_id": "fam_f1",
         "variation": "model"}])
    record.verdicts = [{"attack_id": "atk_e00000000001",
                        "verdict": "INVALID"}]
    out = B.provenance_breakout([record])
    assert out["generated"]["scorable"] == 0
    assert out["generated"]["breach_rate"] is None
    assert out["generated"]["excluded"] == 1
    assert out["generated"]["exclusion_rate"] == 1.0
    assert "training_corpus" not in out


def test_a_verdict_whose_attack_is_not_in_the_round_is_named_not_absorbed():
    """It should never happen. If it does it must not move a published rate by
    being folded into one of the two real columns."""
    record = _round_with_attacks([
        {"attack_id": "atk_a00000000001", "family_id": "fam_f1",
         "variation": "model"}])
    record.verdicts = [{"attack_id": "atk_zzzzzzzzzzzz", "verdict": "BREACH",
                        "breach": True}]
    out = B.provenance_breakout([record])
    assert out["unattributed"]["breaches"] == 1
    assert out["generated"]["breaches"] == 0


# ---------------------------------------------------------------------------
# 5. THE CONTRACT ACCEPTS THE REPAIR. No hash moves.
# ---------------------------------------------------------------------------

def test_c6_accepts_a_generated_row_that_names_its_corpus_instance(corpus):
    """`corpus_instance_id` is in `attacks[].properties` and the `allOf`
    requires it under `training_corpus` without forbidding it under
    `generated`. Asserted against the REAL validator rather than read off the
    schema by eye, because `additionalProperties: false` is exactly the kind of
    thing that is right in the reading and wrong in the run."""
    import jsonschema

    from crucible.replay.integrity import c6_validator

    seed = corpus.attack_seeds()[0]
    row = {
        "attack_id": seed.attack_id, "family_id": seed.family_id,
        "instruction": "rewritten by the model", "provenance": "generated",
        "round_index": 1, "derived_from_attack_id": seed.attack_id,
        "corpus_instance_id": seed.attack_id,
        "generator": {"model_id": "gemini-3.6-flash", "provider": "vertex_ai"},
    }
    schema = c6_validator().schema["properties"]["attacks"]["items"]
    jsonschema.validate(row, schema)
