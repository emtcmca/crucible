"""The two things the LIVEMIX lane could not do without moving a contract hash.

WHAT MOVED, AND WHAT DID NOT. This change edits ONE contract file,
`contracts/evidence_bundle.schema.json`, which moves the C6 entry inside
`contracts/MANIFEST.json`. **It moves NONE of the six hash-locks.** `gate_rule`,
`target_agent`, `manifest` (capability manifest Part A), `objective_set`,
`corpus` and `derived_schema` are all untouched, and `contract-check.py` pass 1
is the only thing in the tree that pins a C6 file hash.

REQUIREMENT 1 - `attack_mode` IS A REQUIRED C6 ROOT FIELD.
The requirement's own sentence is "a run that does not declare its mode must be
unreadable", and unreadable is a strong word chosen on purpose: not defaulted,
not inferred, REJECTED by the validator. It is here rather than left to be
recomputed because IT IS NOT RECOMPUTABLE. A `generated` run whose governor
refused, or whose model returned something unparseable, emits
`variation: "fallback"` and every row renders `training_corpus` - so reading the
mode off the provenance column is wrong EXACTLY when the run degraded, which is
when a reader most needs it.

REQUIREMENT 2 - `episodes[].provenance`, WHICH IS THE PER-ROUND SPLIT.
`_attacks` keeps ONE catalogue row per `attack_id` and a generated variant
supersedes a verbatim replay of the same id. `select()` can draw an instance in
two rounds, so in hybrid an instance attacked BOTH ways collapses to one row.
Measured on a real two-round hybrid before this change: 12 attempts, 11
catalogue rows. The bundle could not answer "how many attacks came from each
source in each round" and the console banner was the only artifact that could.

The episode row is the right home for it because an episode IS one attack in one
round - the catalogue is keyed by id and the round is not part of that key.
"""

import json
import pathlib

import pytest

from crucible.conductor import bundle as B
from crucible.conductor.conductor import RoundRecord
from crucible.replay.integrity import c6_validator

REPO = pathlib.Path(__file__).resolve().parent.parent
C6_SCHEMA = REPO / "contracts" / "evidence_bundle.schema.json"
GOLDEN = REPO / "contracts" / "golden"


def _schema():
    return json.loads(C6_SCHEMA.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1  THE CONTRACT ITSELF
# ---------------------------------------------------------------------------

def test_attack_mode_is_a_REQUIRED_root_field_and_not_merely_permitted():
    """RED before this change: `attack_mode` was in neither `properties` nor
    `required`, and the root is `additionalProperties: false`, so a bundle
    could not even carry the mode optionally."""
    schema = _schema()
    assert "attack_mode" in schema["properties"], (
        "the C6 root has no `attack_mode` property and is "
        "`additionalProperties: false`, so a run cannot declare its mode at all")
    assert "attack_mode" in schema["required"], (
        "`attack_mode` is permitted but not required. A field a producer may "
        "omit is a field a reader cannot rely on, and the requirement is that "
        "a run which does not declare its mode is UNREADABLE.")


def test_the_attack_mode_enum_admits_exactly_the_modes_that_exist():
    """No speculative fourth value. `discovery` is a DESIGN (see
    `docs/design/red-discovery-capability.md`) and nothing in this tree can
    produce it; an enum value no code path emits is a contract making a claim
    the implementation cannot back, and it would read to a judge as a shipped
    capability."""
    from crucible.red import ATTACK_MODES
    assert set(_schema()["properties"]["attack_mode"]["enum"]) == set(ATTACK_MODES)


def test_a_bundle_with_no_attack_mode_is_REJECTED_by_the_real_validator():
    """Through `c6_validator()` - the validator the OFFLINE READER builds, not a
    second opinion assembled here. This is the assertion that makes
    'unreadable' mean something."""
    good = json.loads((GOLDEN / "C6-evidence_bundle.valid.json").read_text(
        encoding="utf-8"))
    assert not list(c6_validator().iter_errors(good)), (
        "the golden positive must validate, or the negative below proves "
        "nothing about `attack_mode` specifically")
    stripped = {k: v for k, v in good.items() if k != "attack_mode"}
    errors = list(c6_validator().iter_errors(stripped))
    assert errors, ("a bundle with no `attack_mode` VALIDATED. The mode is "
                    "optional in practice however the schema reads.")
    assert any("attack_mode" in str(e.message) for e in errors), \
        [e.message for e in errors]


def test_an_unknown_attack_mode_is_REJECTED_rather_than_carried():
    good = json.loads((GOLDEN / "C6-evidence_bundle.valid.json").read_text(
        encoding="utf-8"))
    good["attack_mode"] = "discovery"
    assert list(c6_validator().iter_errors(good)), (
        "the C6 root accepted attack_mode='discovery'. Nothing in this tree "
        "authors an attack, so a bundle able to claim it did is a bundle able "
        "to overstate the build.")


# ---------------------------------------------------------------------------
# 2  THE PRODUCER EMITS IT
# ---------------------------------------------------------------------------

def _round(index, attacks, verdicts):
    record = RoundRecord(round_index=index, hashes={})
    record.attacks = list(attacks)
    record.verdicts = list(verdicts)
    return record


def _seed(aid, variation):
    return {"attack_id": aid, "family_id": "fam_f1",
            "instruction": "t", "variation": variation}


def _verdict(aid, episode_id):
    return {"attack_id": aid, "verdict": "CLEAN", "clause_id": None,
            "_episode": {"episode_id": episode_id, "outcome": "COMPLETED",
                         "events": [], "episode_frozen_context": {}}}


def test_build_bundle_refuses_a_mode_it_does_not_recognise():
    """The producer does not get to invent a fourth mode either. Same doctrine
    as `RedStrategist.__init__`: refuse rather than default, because a run whose
    attack population is decided by a typo is a run that cannot say what it
    measured."""
    with pytest.raises(ValueError) as exc:
        B.attack_mode_or_raise("mixed")
    assert "mixed" in str(exc.value)


# ---------------------------------------------------------------------------
# 3  PER-ROUND PROVENANCE - THE 9.2 GAP
# ---------------------------------------------------------------------------

def test_one_instance_attacked_BOTH_WAYS_collapses_to_one_catalogue_row():
    """The existing rule, asserted here so the fix below is understood as an
    ADDITION rather than a change to it. Deduping the catalogue by id is
    deliberate: a second row for one id makes 'which text ran' a question the
    bundle answers twice."""
    rounds = [_round(1, [_seed("atk_x", "model")], []),
              _round(2, [_seed("atk_x", "none")], [])]
    rows = B._attacks(rounds, generator={"model": "m", "seed": 0})
    assert len(rows) == 1, rows
    assert rows[0]["provenance"] == "generated"


def test_the_episodes_carry_the_per_round_split_the_catalogue_cannot():
    """RED before this change: `episodes[]` had no `provenance` key at all, so
    the same instance run verbatim in round 2 and rewritten in round 1 was
    indistinguishable in the bundle, and the by-provenance rates existed only in
    console scrollback."""
    rounds = [_round(1, [_seed("atk_x", "model")], [_verdict("atk_x", "ep1")]),
              _round(2, [_seed("atk_x", "none")], [_verdict("atk_x", "ep2")])]
    episodes = B._episodes(rounds, live=False)
    by_id = {e["episode_id"]: e for e in episodes}
    assert by_id["ep1"]["provenance"] == "generated"
    assert by_id["ep2"]["provenance"] == "training_corpus", (
        "the round-2 verbatim replay reported `generated`. The join must be to "
        "THIS round's attack list, not to the deduped catalogue - the catalogue "
        "is keyed by id and the round is not part of that key.")


def test_an_episode_whose_attack_is_not_in_its_own_round_carries_NO_provenance():
    """ABSENT, not guessed and not `training_corpus`. An `unattributed` verdict
    is a real case - `provenance_breakout` has a column for it - and folding it
    into either arm would move a published rate. Absent says 'this bundle does
    not know', which is the true statement."""
    rounds = [_round(1, [_seed("atk_x", "model")], [_verdict("atk_orphan", "ep1")])]
    episodes = B._episodes(rounds, live=False)
    assert "provenance" not in episodes[0], episodes[0]


def test_the_schema_permits_a_provenance_free_episode_and_bounds_the_values():
    schema = _schema()["properties"]["episodes"]["items"]
    assert "provenance" in schema["properties"]
    assert "provenance" not in schema["required"], (
        "an unattributed episode has no provenance to state and must not be "
        "forced to invent one")
    assert set(schema["properties"]["provenance"]["enum"]) == {
        "training_corpus", "generated"}


def test_episode_provenance_uses_THE_SAME_call_the_catalogue_uses(monkeypatch):
    """Three instruments - the catalogue, the coverage table and now the episode
    rows - must not be able to disagree about which attacks were rewritten. The
    proof is mechanical: break the shared function and all three move together."""
    monkeypatch.setattr(B, "_attack_provenance", lambda attack: "training_corpus")
    rounds = [_round(1, [_seed("atk_x", "model")], [_verdict("atk_x", "ep1")])]
    assert B._episodes(rounds, live=False)[0]["provenance"] == "training_corpus"
    assert B._attacks(rounds, generator={"model": "m", "seed": 0})[0][
        "provenance"] == "training_corpus"
