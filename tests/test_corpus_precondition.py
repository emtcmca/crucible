"""test_corpus_precondition.py - does the loop refuse to start on a corpus that
moved after D5?

WHAT WAS WRONG, WHICH IS THE ONLY REASON THIS FILE EXISTS
----------------------------------------------------------
All five hash-locks were frozen. FOUR of the six fields were asserted at run
time. `corpus_hash` was frozen at D5 with a dated record and a head commit -
`docs/proof/d5-corpus-freeze.json` - and then nothing in the running system ever
opened it:

    crucible/replay/integrity.py    EPISODE_STAMP_FIELDS is three fields, and
                                    corpus_hash is not one of them.
    contracts/gate_rule.v1.yaml     `grep -c corpus_hash` returns 0. No gate.
    crucible/conductor/hashlocks.py did not know the name at all.

So the loop would run happily against an edited corpus and print an ASR and a
BPR whose denominator and instance set the D5 record does not describe. That is
the exact failure `docs/measurement-spec.md` line 697 names - *"denominator drift
(countered by freezing `corpus_id` and asserting slice-membership hash per
round)"* - and the counter it names was half-built: the freezing was done, the
asserting was not.

THIS FILE'S FIRST TEST IS RED ON THE TREE AS IT STOOD AN HOUR AGO. Before the
`corpus_hash` block landed in `hashlocks.py`, `test_a_tampered_corpus_file_stops_the_run`
passed `load_hash_locks` a corpus with a mutated training instance and got a
clean HashLocks object back.

WHAT IS STUB-ONLY HERE, STATED UP FRONT
-----------------------------------------
No model is called anywhere in this file and no episode is run. These tests
prove that the PRECONDITION fires and what it fires on. They prove nothing about
whether the corpus is any good, nothing about the sealed family's bytes (see
`test_the_precondition_needs_no_sealed_set`, which proves the opposite on
purpose), and nothing about per-episode or per-round assertion - `corpus_hash`
is still absent from `EPISODE_STAMP_FIELDS` and that is deliberate and reported,
not an oversight this file closes.
"""

import json
import pathlib
import shutil

import pytest

from crucible.conductor.hashlocks import (
    ENV_CORPUS_FREEZE,
    FROZEN,
    IN_FORCE,
    LOCK_FIELDS,
    HashLockError,
    HashLockSkew,
    MissingFreeze,
    load_hash_locks,
)
from crucible.conductor.real_tripwire import resolve_objective_set

REPO = pathlib.Path(__file__).resolve().parent.parent
RECORD = REPO / "docs" / "proof" / "d5-corpus-freeze.json"

# The covered set, from `corpus/freeze.py`. Named here rather than imported as a
# glob so that a test tree which quietly lost a member is a test failure and not
# a smaller corpus that hashes to something valid-looking.
COVERED_DIRS = ("corpus/training", "fixtures/benign")
COVERED_FILES = ("corpus/pairs.json", "corpus/F4-MANIFEST.json",
                 "docs/proof/sealed-family-commitment.json")


@pytest.fixture(scope="module")
def objective_set():
    """ONE Objective Set for the whole file, exactly as `campaign.run` uses one:
    two loads of the same path are two objects that agree today."""
    return resolve_objective_set()


def _clean_tree(dest):
    """A repo root holding ONLY the files inside `corpus_hash`.

    Deliberately NOT a copy of the repository. It has no `corpus/sealed/`, no
    `.git`, no `*.py` and no `*.md` under `corpus/`, which is what makes it a
    stand-in for a judge's fresh public clone rather than for this machine.
    """
    dest = pathlib.Path(dest)
    for d in COVERED_DIRS:
        (dest / d).mkdir(parents=True, exist_ok=True)
        for src in sorted((REPO / d).glob("*.json")):
            shutil.copy2(src, dest / d / src.name)
    for f in COVERED_FILES:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / f, dest / f)
    assert not (dest / "corpus" / "sealed").exists()
    return dest


def _record_naming(tmp_path, value, name="fake-freeze.json"):
    """A D5 freeze record carrying `value` and nothing else that matters."""
    p = pathlib.Path(tmp_path) / name
    p.write_text(json.dumps({"corpus_hash": value,
                             "head_commit": "0" * 40}) + "\n",
                 encoding="utf-8")
    return p


def _frozen_value():
    return json.loads(RECORD.read_text(encoding="utf-8"))["corpus_hash"]


# ---------------------------------------------------------------------------
# 1. The claim. A corpus that moved after D5 stops the run.
# ---------------------------------------------------------------------------

def test_a_tampered_corpus_file_stops_the_run(objective_set, tmp_path):
    """RED ON THE TREE AS IT STOOD BEFORE THIS LANE. One byte of one training
    instance, and the loop must not start.

    The tamper is a real one rather than a truncation: the file stays valid
    JSON, still canonicalizes, and still loads - which is the shape that gets
    past everything except a hash.
    """
    tree = _clean_tree(tmp_path / "repo")
    victim = sorted((tree / "corpus" / "training").glob("*.json"))[0]
    doc = json.loads(victim.read_text(encoding="utf-8"))
    doc["_tampered"] = "one field, added after the freeze"
    victim.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(HashLockSkew) as exc:
        load_hash_locks(objective_set, corpus_root=tree)

    msg = str(exc.value)
    assert "corpus_hash" in msg
    assert "THE SUITE MOVED AFTER IT WAS FROZEN" in msg
    # Names what moved, why the run stops, and that no number survives it.
    assert _frozen_value() in msg          # what the record says
    assert "comparable" in msg             # why it stops
    assert "freeze-d5-corpus.py --check" in msg   # how to see which files


def test_an_added_instance_stops_the_run_too(objective_set, tmp_path):
    """Coverage is over the SET, not only over the bytes of known members. A
    51st training instance is a different corpus and every rate computed against
    it has a different denominator."""
    tree = _clean_tree(tmp_path / "repo")
    sibling = sorted((tree / "corpus" / "training").glob("*.json"))[0]
    (tree / "corpus" / "training" / "ZZ-99.json").write_text(
        sibling.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(HashLockSkew):
        load_hash_locks(objective_set, corpus_root=tree)


def test_a_removed_instance_stops_the_run(objective_set, tmp_path):
    """The other direction. Silent exclusion turns flakiness into apparent
    hardening (`measurement-spec.md` 5.1), and it is invisible to any check that
    only compares the files that are still there."""
    tree = _clean_tree(tmp_path / "repo")
    sorted((tree / "fixtures" / "benign").glob("*.json"))[0].unlink()

    with pytest.raises(HashLockSkew):
        load_hash_locks(objective_set, corpus_root=tree)


# ---------------------------------------------------------------------------
# 2. And a clean corpus starts. Without this, test 1 passes because
#    EVERYTHING refuses, which is a check that cannot distinguish.
# ---------------------------------------------------------------------------

def test_a_clean_corpus_starts_normally(objective_set, tmp_path):
    """The same tree, untouched. If this fails, the tamper tests above prove
    nothing at all."""
    tree = _clean_tree(tmp_path / "repo")
    locks = load_hash_locks(objective_set, corpus_root=tree)
    assert locks.values["corpus_hash"] == _frozen_value()
    assert locks.provenance["corpus_hash"]["kind"] == FROZEN


def test_the_repository_as_it_stands_starts_normally(objective_set):
    """The default path, with no `corpus_root` override - what `campaign.run`
    actually calls. `main` must be startable."""
    locks = load_hash_locks(objective_set)
    assert locks.values["corpus_hash"] == _frozen_value()
    assert locks.provenance["corpus_hash"]["kind"] == FROZEN
    assert locks.provenance["corpus_hash"]["source"].endswith(
        "d5-corpus-freeze.json")


# ---------------------------------------------------------------------------
# 3. It works with NO SEALED SET, which is the normal case in a worktree and
#    the only case in a judge's clone.
# ---------------------------------------------------------------------------

def test_the_precondition_needs_no_sealed_set(objective_set, tmp_path):
    """`corpus/sealed/` is gitignored and absent from every worktree and clone.
    The sealed family is inside `corpus_hash` BY REFERENCE - content-addressed
    ids in F4-MANIFEST.json plus the published commitment fingerprint - so this
    check must pass identically without it.

    Asserted on a tree that PROVABLY has none, rather than on the repo: a
    developer machine holding the sealed set would make the repo version of this
    test vacuous and it would still be green.
    """
    tree = _clean_tree(tmp_path / "repo")
    assert not (tree / "corpus" / "sealed").exists()
    assert not list(tree.rglob("sealed"))

    locks = load_hash_locks(objective_set, corpus_root=tree)
    assert locks.values["corpus_hash"] == _frozen_value()
    # Says out loud what it did NOT check, so the claim cannot be read wider.
    assert "seal-commitment.py --verify" in \
        locks.provenance["corpus_hash"]["sealed_family"]


def test_adding_a_sealed_directory_changes_nothing(objective_set, tmp_path):
    """The by-reference design's whole payoff, asserted from this side of the
    boundary: a machine holding the held-out set and a clone that does not
    compute the SAME value. If they differed, the frozen number would be the one
    only the build machine could reproduce."""
    tree = _clean_tree(tmp_path / "repo")
    before = load_hash_locks(objective_set, corpus_root=tree).values["corpus_hash"]

    sealed = tree / "corpus" / "sealed"
    sealed.mkdir(parents=True)
    (sealed / "F4-sealed-01.json").write_text(
        json.dumps({"instance_id": "held out", "attack": "never read"}),
        encoding="utf-8")

    after = load_hash_locks(objective_set, corpus_root=tree).values["corpus_hash"]
    assert after == before


# ---------------------------------------------------------------------------
# 4. Negative controls. What must NOT trip it, and what must not be compared
#    to itself.
# ---------------------------------------------------------------------------

def test_editing_something_outside_the_covered_set_does_not_trip_it(
        objective_set, tmp_path):
    """NEGATIVE CONTROL. A precondition that fires on any change at all is not
    measuring the corpus, it is measuring the mtime of the working tree - and it
    would be re-frozen until nobody believed it. `corpus/freeze.py` puts every
    `.py` and `.md` under `corpus/` outside the payload on purpose."""
    tree = _clean_tree(tmp_path / "repo")
    (tree / "corpus" / "README.md").write_text(
        "prose, reworded after the freeze\n", encoding="utf-8")
    (tree / "corpus" / "lints.py").write_text("# a comment\n", encoding="utf-8")
    (tree / "corpus" / "training" / "notes.txt").write_text(
        "not a .json\n", encoding="utf-8")

    locks = load_hash_locks(objective_set, corpus_root=tree)
    assert locks.values["corpus_hash"] == _frozen_value()


def test_the_record_and_the_recompute_are_two_sources(
        objective_set, tmp_path, monkeypatch):
    """NEGATIVE CONTROL on the check itself. A clean corpus against a record
    naming a DIFFERENT hash must still stop the run.

    Without this, an implementation that read the record and compared it to
    itself - the single-source bug `crucible/tripwire/model.py::RunManifest`
    names, "passes version skew happily" - would pass every test above.
    """
    tree = _clean_tree(tmp_path / "repo")
    monkeypatch.setenv(
        ENV_CORPUS_FREEZE,
        str(_record_naming(tmp_path, "deadbeefdeadbeef")))

    with pytest.raises(HashLockSkew) as exc:
        load_hash_locks(objective_set, corpus_root=tree)
    assert "deadbeefdeadbeef" in str(exc.value)


def test_a_record_with_no_corpus_hash_is_not_a_freeze_record(
        objective_set, tmp_path, monkeypatch):
    """A freeze record without the hash it froze is not a freeze record - and it
    must not degrade to IN_FORCE, which would silently convert a missing
    assertion into a passing run."""
    empty = pathlib.Path(tmp_path) / "empty.json"
    empty.write_text(json.dumps({"head_commit": "0" * 40}) + "\n",
                     encoding="utf-8")
    monkeypatch.setenv(ENV_CORPUS_FREEZE, str(empty))

    with pytest.raises(MissingFreeze) as exc:
        load_hash_locks(objective_set)
    assert "corpus_hash" in str(exc.value)


def test_a_placeholder_in_the_record_is_refused_by_name(
        objective_set, tmp_path, monkeypatch):
    """Sixteen zeros is a well-formed hash and a lie. It is refused before it
    can be compared to anything, the same as the other five fields."""
    monkeypatch.setenv(ENV_CORPUS_FREEZE,
                       str(_record_naming(tmp_path, "0" * 16)))
    with pytest.raises(HashLockError) as exc:
        load_hash_locks(objective_set)
    assert "placeholder" in str(exc.value)


def test_a_corpus_that_will_not_hash_stops_the_run(objective_set, tmp_path):
    """An empty corpus hashes to a perfectly valid-looking 16 hex characters
    over a suite with nothing in it. `corpus/freeze.py` refuses it; this asserts
    the refusal survives the trip through the lock loader instead of arriving as
    an unhandled traceback."""
    tree = _clean_tree(tmp_path / "repo")
    for p in (tree / "corpus" / "training").glob("*.json"):
        p.unlink()
    for p in (tree / "fixtures" / "benign").glob("*.json"):
        p.unlink()

    with pytest.raises(HashLockError) as exc:
        load_hash_locks(objective_set, corpus_root=tree)
    assert "corpus_hash could not be recomputed" in str(exc.value)


# ---------------------------------------------------------------------------
# 5. The value is published, not merely checked - and the six-field tuple is
#    pinned to its owner rather than restated.
# ---------------------------------------------------------------------------

def test_corpus_hash_is_one_of_the_six_lock_fields(objective_set):
    """Five locks, six fields (ruling 20). The loader returned five values until
    2026-08-22, so a bundle could not say WHICH SUITE its numbers were measured
    against - and `crucible/ledger/store.py:122` was already reaching for
    `hash_locks.get("corpus_hash")` and storing NULL."""
    locks = load_hash_locks(objective_set)
    assert set(locks.values) == set(LOCK_FIELDS)
    assert set(locks.provenance) == set(LOCK_FIELDS)
    assert set(locks.as_dict()["values"]) == set(LOCK_FIELDS)


def test_the_six_lock_fields_agree_with_their_owner():
    """`crucible/replay/integrity.py::HASH_LOCK_FIELDS` decides whether a C6
    bundle is evidence. `hashlocks.LOCK_FIELDS` is a typed copy - the same
    trade `integrity.py` documents for `BENIGN_DENOMINATOR`, made for the same
    reason (the replay package must import nothing). A copy nobody compares is
    how `BENIGN_DENOMINATOR` carried 24 for a day after ruling 43 moved it while
    the whole suite stayed green."""
    from crucible.replay.integrity import HASH_LOCK_FIELDS
    assert LOCK_FIELDS == HASH_LOCK_FIELDS


def test_the_provenance_distinguishes_frozen_from_in_force(
        objective_set, tmp_path, monkeypatch):
    """With no record on disk the value is still a real hash of the artifact in
    force - never a placeholder, never absent - and it is labelled IN_FORCE so
    the banner cannot present it as a dated pre-registration."""
    monkeypatch.setenv(ENV_CORPUS_FREEZE,
                       str(pathlib.Path(tmp_path) / "does-not-exist.json"))
    locks = load_hash_locks(objective_set)
    assert locks.values["corpus_hash"] == _frozen_value()   # same bytes
    assert locks.provenance["corpus_hash"]["kind"] == IN_FORCE
    assert "corpus_hash" in locks.unfrozen
