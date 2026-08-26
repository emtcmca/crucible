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


def test_the_thresholds_are_read_from_the_hash_locked_contract():
    """Not restated here either. The assertion is that this module READS them -
    the values it should read are in `contracts/gate_rule.v1.yaml`, which is
    hash-locked, and duplicating them in a test would recreate the drift site
    the reading exists to remove."""
    import yaml
    doc = yaml.safe_load(g4.GATE_RULE.read_text(encoding="utf-8"))
    want = {}
    for a in doc["gates"]["G4"]["assertions"]:
        want.update(a)
    got = g4.contract_g4()
    assert got["failure_mode"] == doc["gates"]["G4"]["failure_mode"]
    assert got["bounds"]["newly_blocked_b"] == g4._parse_threshold(
        want["newly_blocked_b"])
    assert got["bounds"]["newly_breached_c"] == g4._parse_threshold(
        want["newly_breached_c"])


def test_an_unparseable_threshold_refuses_rather_than_defaulting(tmp_path):
    """A threshold this module could not parse must not become a default. A
    default is a number invented by the file that was told not to invent one."""
    doc = {"gates": {"G4": {"failure_mode": "REJECT", "assertions": [
        {"newly_blocked_b": "roughly three"}, {"newly_breached_c": "== 0"}]}}}
    import yaml
    p = tmp_path / "gate_rule.yaml"
    p.write_bytes(yaml.safe_dump(doc).encode("utf-8"))
    with pytest.raises(g4.G4BaselineUnavailable) as exc:
        g4.contract_g4(p)
    assert exc.value.code == "E_G4_CONTRACT_UNREADABLE"


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


def test_the_seven_negative_controls_pass():
    ok, rows = g4.selftest()
    failed = [r for r in rows if not r[1]]
    assert ok, "\n".join("%s -- %s" % (r[0], r[2]) for r in failed)
    assert len(rows) == 7
