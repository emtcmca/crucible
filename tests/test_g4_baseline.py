"""The v0 attack baseline, and G4 paired over it.

The seven negative controls live in `crucible.conductor.g4.selftest` rather than
here, and this file drives them. That is deliberate: the controls have to be
runnable by a stranger with `python -m crucible.conductor.g4 --selftest` from a
clean checkout, without pytest, the same way `--selftest` works everywhere else
in this repository. A copy of them in a test file would be a second set that
could quietly disagree with the shipped one.
"""

import json
import pathlib

import pytest

from crucible.conductor import g4
from crucible.conductor.campaign import resolve_objective_set
from crucible.conductor.corpus_seeds import CorpusSeeds
from crucible.conductor.hashlocks import load_hash_locks


@pytest.fixture(scope="module")
def env():
    objective_set = resolve_objective_set()
    return objective_set, load_hash_locks(objective_set)


def test_the_baseline_covers_every_training_instance(env):
    """A shrinking denominator is the failure this asserts against.

    `b >= 3` is calibrated against a slice of fifty. If an instance quietly has
    no recorded episode, the gate keeps the threshold and loses the
    denominator, which makes it strictly harsher for a reason nobody printed.
    """
    objective_set, locks = env
    ids = {a.attack_id for a in CorpusSeeds.load()._attacks}
    base = g4.load_baseline(objective_set=objective_set, locks=locks,
                            corpus_ids=ids)
    assert set(base.episodes) == ids


def test_the_baseline_is_live_evidence(env):
    """An offline recording replays each instance's OWN authored trace, so every
    call in it is the corpus author's intention. Pairing over that would produce
    a b figure about a document."""
    objective_set, locks = env
    base = g4.load_baseline(objective_set=objective_set, locks=locks)
    assert base.recorded_live is True
    assert base.record["target_model"] != "OFFLINE_SCRIPTED"


def test_the_reader_actually_reads_and_a_hardcoded_literal_could_not_pass(
        tmp_path):
    """THE REPLACEMENT FOR A CONTROL THE READER MADE VACUOUS, AND IT IS STRONGER.

    `tests/test_g4.py::test_the_thresholds_are_the_ones_the_frozen_contract_
    states` used to compare the yaml with `g4.B_MIN`, and it caught a
    hand-edited literal. Once `B_MIN` is READ from that same yaml, that
    comparison is the file against itself: "a check that derives its expectation
    the same way as the claim cannot catch it."

    So the reader is pointed at a DIFFERENT contract and the bounds must move.
    `B_MIN = 3` hardcoded cannot pass this, and neither can a reader that
    swallows an unreadable file and falls back to a default.
    """
    import yaml
    doc = yaml.safe_load(g4.GATE_RULE.read_text(encoding="utf-8"))
    doc["gates"]["G4"]["assertions"] = [
        {"newly_blocked_b": ">= 7"}, {"newly_breached_c": "<= 2"}]
    p = tmp_path / "other_gate_rule.yaml"
    p.write_bytes(yaml.safe_dump(doc).encode("utf-8"))

    got = g4.contract_g4(p)
    assert got["bounds"]["newly_blocked_b"] == ("gte", 7)
    assert got["bounds"]["newly_breached_c"] == ("lte", 2)
    # And the real contract is untouched by having read another one.
    assert (g4.B_OP, g4.B_MIN) == g4.contract_g4()["bounds"]["newly_blocked_b"]


def test_decide_honours_the_comparison_operator_and_not_just_the_bound():
    """`decide` tested `b < B_MIN` literally, which is only correct while the
    contract says `>=`. Half a threshold is not a threshold: a contract that
    said `> 3` would be read as `>= 3` and three would pass a gate demanding
    four."""
    assert g4._compare("gt", 3, 3) is False
    assert g4._compare("gte", 3, 3) is True
    assert g4._compare("eq", 0, 0) is True
    assert g4._compare("eq", 1, 0) is False


def test_an_unparseable_threshold_refuses_rather_than_defaulting(tmp_path):
    """A threshold this module could not parse must not become a default. A
    default is a number invented by the file that was told not to invent one.

    `G4ContractUnreadable`, NOT `G4BaselineUnavailable`: a defect in the frozen
    contract is not a defect in the recording, and routing both to one exception
    would let a caller repair the wrong artifact.
    """
    doc = {"gates": {"G4": {"failure_mode": "REJECT", "assertions": [
        {"newly_blocked_b": "roughly three"}, {"newly_breached_c": "== 0"}]}}}
    import yaml
    p = tmp_path / "gate_rule.yaml"
    p.write_bytes(yaml.safe_dump(doc).encode("utf-8"))
    with pytest.raises(g4.G4ContractUnreadable) as exc:
        g4.contract_g4(p)
    assert "E_G4_CONTRACT_UNREADABLE" in str(exc.value)


def test_a_missing_baseline_raises_and_is_not_a_gate_verdict(tmp_path):
    """G4 declares `failure_mode: REJECT` and, unlike G7, no
    `absent_or_unevaluable`. REJECT means "the candidate was not good enough",
    which a missing baseline is not a fact about; two of them HALT the run. So
    the absence raises before a round rather than resolving to either outcome."""
    with pytest.raises(g4.G4BaselineUnavailable) as exc:
        g4.load_baseline(root=tmp_path / "nope",
                         freeze_path=tmp_path / "nothing.json")
    assert exc.value.code == "E_G4_BASELINE_MISSING"
    assert exc.value.fix                       # every refusal names its repair


def test_the_freeze_record_does_not_pin_to_corpus_hash():
    """Ruling 56. A whole-corpus pin makes every corpus repair retire all fifty
    rows to express one instance's invalidation."""
    rec = json.loads(g4.FREEZE_RECORD.read_text(encoding="utf-8"))
    assert "corpus_hash" not in (rec.get("pins") or {})
    assert "corpus_hash" in (rec.get("not_pinned") or {})


def test_the_default_slice_is_the_run_and_the_baseline_must_be_asked_for():
    """THE LANE THAT BUILT THE ARTIFACT DID NOT RE-POINT THE CRITERION AT IT.

    Changing which slice gates changes what the loop promotes. The evidence for
    moving the default is in
    `docs/design/g4-v0-attack-baseline-2026-08-26.md` and the switch is one
    argument; it is a decision a person takes, not a side effect of this lane
    landing. If someone flips `DEFAULT_SLICE`, this fails and they have to say
    so in a commit message.
    """
    assert g4.DEFAULT_SLICE == g4.SLICE_RUN
    assert set(g4.SLICES) == {"run", "baseline"}
    episodes, prov = g4.resolve_slice(None, run_slice=[{"marker": 1}])
    assert episodes == [{"marker": 1}]
    assert prov["slice"] == "run"
    assert prov["covers_generated_attacks"] is True


def test_a_misspelled_slice_falls_back_to_neither_slice():
    """Falling back to `run` would silently measure a different denominator
    than the caller asked for; falling back to `baseline` would do the same in
    the other direction. Same argument as `resolve_mode`."""
    with pytest.raises(g4.G4SliceError):
        g4.resolve_slice("baselnie", run_slice=[])


def test_asking_for_the_baseline_gets_fifty_and_not_the_run_slice(env):
    """The control that proves the selector is real.

    A `resolve_slice` that ignored its argument and always returned the run
    slice would pass every test above. This one hands it a one-element run slice
    and asks for the baseline; getting one element back is the failure.
    """
    objective_set, locks = env
    episodes, prov = g4.resolve_slice(
        "baseline", run_slice=[{"marker": 1}], objective_set=objective_set,
        locks=locks)
    assert prov["slice"] == "baseline"
    assert prov["covers_generated_attacks"] is False
    assert len(episodes) == prov["n"] > 1
    assert {"marker": 1} not in episodes


def test_the_two_slices_score_different_denominators(env):
    """b and c are computed by ONE scorer over TWO inputs, and the outputs must
    differ in `n`. If they did not, the slice argument would be decorative and
    every figure labelled `slice=baseline` would be a mislabel."""
    from crucible.armorer.experiment import build_seed_policy
    from crucible.conductor.campaign import build_validator
    objective_set, locks = env
    validator, _a, _b = build_validator()
    seed = build_seed_policy(validator)
    base = g4.load_baseline(objective_set=objective_set, locks=locks)

    full = g4.paired_scores(base.slice(), seed, seed, objective_set)
    one = g4.paired_scores(base.slice()[:1], seed, seed, objective_set)
    assert full["slice_n"] == len(base) > one["slice_n"] == 1


def test_the_gate_refuses_to_be_built_on_a_baseline_that_is_not_there(
        tmp_path, monkeypatch):
    """A PRECONDITION, CHECKED AT CONSTRUCTION, NOT IN ROUND THREE.

    `--g4-slice baseline` with no baseline on disk must fail before a model
    token is spent. `campaign.py` makes the same argument about the benign
    floor: "a precondition checked after six rounds of model spend is a
    precondition checked too late."

    It is also NOT a REJECT. A rejection is a statement about the candidate, and
    two of them halt the run - a human summoned by a measurement nobody took.
    """
    import tests.test_real_gate as trg
    from crucible.ledger import Ledger
    monkeypatch.setattr(g4, "FREEZE_RECORD", tmp_path / "absent.json")
    monkeypatch.setattr(g4, "EPISODES_DIR", tmp_path / "absent")
    with Ledger(":memory:") as led:
        led.open_run(trg.RUN, trg.NOW, trg.LOCKS)
        with pytest.raises(g4.G4BaselineUnavailable) as exc:
            trg.build(tmp_path, led, g4_slice="baseline")
    assert exc.value.code == "E_G4_BASELINE_MISSING"


def test_the_gate_pairs_over_fifty_when_told_to_and_says_so(tmp_path):
    """THE WIRING CONTROL. A `g4_slice` argument the gate accepted and ignored
    would pass every unit test above.

    The gate is handed a ONE-EPISODE run slice and asked for the baseline. If
    the finding comes back paired over one episode, the argument is decorative.
    The slice name is asserted on the finding and on the record too, because a b
    figure whose denominator has no provenance is not auditable.
    """
    import tests.test_g4 as tg4
    import tests.test_real_gate as trg
    from crucible.armorer.experiment import build_seed_policy
    from crucible.conductor.campaign import build_validator
    from crucible.ledger import Ledger

    validator, _a, _b = build_validator()
    seed = build_seed_policy(validator)
    with Ledger(":memory:") as led:
        led.open_run(trg.RUN, trg.NOW, trg.LOCKS)
        gate = trg.build(tmp_path, led, g4_slice="baseline")
        rec = tg4.Rec(seed, [{"marker": "the run slice, deliberately tiny"}])
        finding = gate.g4_finding(seed, rec)

    assert gate.g4_slice == "baseline"
    assert rec.g4_slice == "baseline"
    assert rec.g4_paired_n > 1, (
        "the gate paired over the run slice it was handed, not the baseline it "
        "was asked for")
    assert "baseline" in finding["check"]
    assert "slice=baseline" in finding["detail"]


def test_the_seven_negative_controls_pass():
    ok, rows = g4.selftest()
    failed = [r for r in rows if not r[1]]
    assert ok, "\n".join("%s -- %s" % (r[0], r[2]) for r in failed)
    assert len(rows) == 7
