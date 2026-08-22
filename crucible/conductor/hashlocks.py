"""hashlocks.py - where the five hash-locks come from, and what to do when one
does not exist yet.

WHAT THIS REPLACES, AND WHY IT IS NOT A REFACTOR
------------------------------------------------
`campaign.py` used to build the five like this:

    hashes = {name: "%016x" % (0xC0FFEE00 + i)
              for i, name in enumerate(REQUIRED_HASHES)}

Every episode the campaign sealed would have carried those bytes. That is fine
for a loop whose target is a stand-in and whose bundle says so in four places,
and it is NOT fine the moment the real target, the real TRIPWIRE and the real
WARDEN are wired in - because the stamp is the only thing that says which ruler
a number was measured with, and a fabricated stamp says something FALSE rather
than saying nothing. `crucible/harness/episode.py` puts it plainly: an episode
without a hash is "unscoreable rather than clean". An episode with an INVENTED
one is scoreable and wrong, which is strictly worse.

So: every value here is READ from an artifact. Nothing is defaulted, nothing
falls back to zeros, and `_assert_shape` refuses the old `c0ffee` placeholders
by name so they cannot come back through a copy-paste.

THE TWO KINDS OF SOURCE, AND WHY THE DIFFERENCE IS REPORTED RATHER THAN HIDDEN
-------------------------------------------------------------------------------
A hash-lock is a claim about a MOMENT: *this artifact was pinned before the
first measurement was taken*, and the public commit timestamp is what makes the
claim checkable by a stranger (`scripts/freeze-d2-gate-rule.py`'s docstring
says exactly this). Two of the five have such a record on disk today:

    gate_rule_hash      docs/proof/d2-gate-rule-freeze.json      D2, dated
    target_agent_hash   target/refund_agent/FROZEN.json          D3, dated
    manifest_hash       target/refund_agent/FROZEN.json          D3, dated

The other two do not:

    objective_set_hash  no D3 freeze record exists yet
    derived_schema_hash no D5 freeze record exists yet (D5 is the corpus freeze)

For those two this module hashes THE ARTIFACT ACTUALLY IN FORCE FOR THIS RUN -
the Objective Set the TRIPWIRE loaded, and the Part B document the harness
stamps `derived.*` from - and labels the value `IN_FORCE` rather than `FROZEN`.
That is a real hash of a real artifact, not a placeholder, and it is the ONLY
value that can possibly be correct: G1(b) compares the episode's stamp against
the Objective Set the evaluator actually loaded, so any other number makes every
episode INVALID. What it is NOT is a dated pre-registration, and the campaign
banner and the bundle both say so per-lock rather than letting five hashes sit
in a row looking equally load-bearing.

When the freeze records land (another lane is authoring the D3 Objective Set
freeze now), drop them at the paths below and they are picked up with no edit
here - AND cross-checked against the artifact in force, which is the point.
A freeze record that disagrees with the file it froze is `HashLockSkew`, loud,
at startup, before a single episode runs.

WHY NOT JUST TAKE THE HASH FROM THE FREEZE RECORD AND SKIP THE CROSS-CHECK
---------------------------------------------------------------------------
`crucible/tripwire/model.py::RunManifest` already answers this: "KB6 is only
catchable because there are two. A single-source implementation compares a
value to itself, passes version skew happily, and attributes results to policies
that were never active." The freeze record and the live artifact are the two
independent sources. Reading only one of them re-creates the single-source bug
one layer up.

`corpus_hash`, AND WHY IT IS A STARTUP PRECONDITION RATHER THAN A GATE
-----------------------------------------------------------------------
This module loaded FIVE FIELDS until 2026-08-22 and `corpus_hash` was not one of
them. The corpus was frozen at D5 - `docs/proof/d5-corpus-freeze.json`, a dated
record with a head commit - and nothing in the running system ever opened it.
Four of the six fields were asserted at run time; the sixth was written down and
never read. `contracts/gate_rule.v1.yaml` does not mention `corpus_hash` either
(`grep -c` returns 0), so the loop would happily run against a corpus that moved
after D5 and print a number nobody could compare to any other number.

**It is fixed HERE and not with a G-numbered gate, deliberately.** A gate decides
promote-or-reject on a candidate; this decides whether the RUN MAY BEGIN, which
is what every other raise in this file already does and why none of them carries
a G number either. The stronger reason is that `gate_rule.v1.yaml` is itself
hash-locked at `cff9f52929397efb` and is the one lock untouched since D2. Adding
a gate for this would mean re-freezing it, which trades a pre-registration that
predates every patch for one that does not - a worse artifact bought with a
better-sounding word.

**The recompute reads the WORKING TREE, not HEAD**, and the difference is the
point. `scripts/freeze-d5-corpus.py --check` reads HEAD because it is auditing
what was committed. This reads what the corpus loader will actually load, which
is the disk - an uncommitted edit to a training instance is exactly the tamper a
startup precondition exists to catch, and HEAD cannot see it. Both go through
`corpus.freeze.corpus_hash_full`; there is no second implementation of the hash.

**It does not need `corpus/sealed/`.** The sealed family is inside `corpus_hash`
BY REFERENCE - content-addressed instance ids in `corpus/F4-MANIFEST.json` plus
the published fingerprint in `docs/proof/sealed-family-commitment.json` - so the
value is identical on a machine holding the held-out set and on a fresh clone
that does not. A precondition that only fires on one machine is not a
precondition. What this therefore does NOT assert is that the sealed BYTES still
match their commitment; that is `scripts/seal-commitment.py --verify` and it
needs the sealed set.
"""

import json
import os
import pathlib

from ..manifest import load_part_b

_HERE = pathlib.Path(__file__).resolve().parent
REPO = _HERE.parent.parent

# -- artifacts, all relative to the repo root ------------------------------
D2_GATE_RULE_FREEZE = REPO / "docs" / "proof" / "d2-gate-rule-freeze.json"
D3_TARGET_FREEZE = REPO / "target" / "refund_agent" / "FROZEN.json"
PART_B_IN_FORCE = REPO / "contracts" / "golden" / "C3b-derived_schema.valid.json"

# Not present yet. Named here so that landing one is a file drop rather than a
# code change, and so that the name this module looks for is discoverable by the
# lane authoring it. Both are overridable by env var for the same reason
# `real_tripwire.py` exposes CRUCIBLE_OBJECTIVE_SET.
D3_OBJECTIVE_SET_FREEZE = REPO / "docs" / "proof" / "d3-objective-set-freeze.json"
D5_DERIVED_SCHEMA_FREEZE = REPO / "docs" / "proof" / "d5-derived-schema-freeze.json"

# THIS ONE DOES EXIST. `scripts/freeze-d5-corpus.py --write` landed it, and until
# 2026-08-22 nothing at run time opened it - see the `corpus_hash` block in
# `load_hash_locks` for what that cost.
D5_CORPUS_FREEZE = REPO / "docs" / "proof" / "d5-corpus-freeze.json"

ENV_OBJECTIVE_SET_FREEZE = "CRUCIBLE_OBJECTIVE_SET_FREEZE"
ENV_DERIVED_SCHEMA_FREEZE = "CRUCIBLE_DERIVED_SCHEMA_FREEZE"
ENV_CORPUS_FREEZE = "CRUCIBLE_CORPUS_FREEZE"

# THE SIX FIELDS THE FIVE LOCKS OCCUPY. Ruling 20 split the fifth lock into two
# artifacts frozen together at D5 - the corpus and Part B - so "five locks" and
# "six fields" are both true and neither one is the other.
#
# This is NOT `conductor.REQUIRED_HASHES`, which names the five the CONDUCTOR
# refuses to start without and deliberately stays at five. It is the tuple
# `crucible/replay/integrity.py::HASH_LOCK_FIELDS` uses to decide whether a C6
# bundle is evidence, typed here rather than imported for the reason that module
# gives for its own copy of `BENIGN_DENOMINATOR`: the replay package's documented
# property is that it needs nothing, and `crucible.conductor` reaching into it
# would create a coupling `offline_lint` does not walk far enough to see. The
# copy is pinned to its owner by
# `tests/test_corpus_precondition.py::test_the_six_lock_fields_agree_with_their_owner`,
# which is a mechanical check rather than a second statement of the value.
LOCK_FIELDS = ("gate_rule_hash", "target_agent_hash", "manifest_hash",
               "objective_set_hash", "corpus_hash", "derived_schema_hash")

# The two provenance kinds. Reported per lock; never averaged into one word.
FROZEN = "FROZEN"      # a dated freeze record on disk names this value
IN_FORCE = "IN_FORCE"  # hashed from the artifact this run actually used

# Placeholders that have really been in this repo's bundles. Refused BY NAME so
# that a copy-paste of an old evidence file cannot re-enter through the loader.
_KNOWN_PLACEHOLDERS = {
    "0" * 16: "all zeros",
    "0000000000000000": "all zeros",
}
_PLACEHOLDER_PREFIX = "00000000c0ffee"   # campaign.py's old 0xC0FFEE00 + i


class HashLockError(RuntimeError):
    """Setup-time refusal. The campaign has not started."""


class MissingFreeze(HashLockError):
    """A hash-lock has no artifact to read. Never falls back to a placeholder."""


class HashLockSkew(HashLockError):
    """A freeze record and the artifact it froze disagree. That IS the check."""


class HashLocks:
    """The six values plus, for each, where it came from and how strong that is.

    `values` is what the conductor and the run manifest consume. `provenance` is
    what the banner and the bundle print, and it exists so that "five hashes
    present" - which `campaign.py` has printed since day one - stops being able
    to mean five fabricated ones.
    """

    __slots__ = ("values", "provenance")

    def __init__(self, values, provenance):
        self.values = dict(values)
        self.provenance = dict(provenance)

    @property
    def unfrozen(self):
        """Lock names carrying a real hash but NO dated freeze record. The
        campaign says this out loud; it is the honest half of the claim."""
        return sorted(name for name, p in self.provenance.items()
                      if p["kind"] != FROZEN)

    def as_dict(self):
        return {"values": dict(self.values),
                "provenance": {k: dict(v) for k, v in self.provenance.items()},
                "unfrozen": self.unfrozen}


def _assert_shape(name, value, source):
    if not isinstance(value, str) or len(value) != 16 or \
            any(c not in "0123456789abcdef" for c in value):
        raise HashLockError(
            "%s read %r from %s. A hash-lock is 16 lowercase hex characters "
            "(canonicalization.md); anything else is not a hash and must not be "
            "stamped on an episode." % (name, value, source))
    if value in _KNOWN_PLACEHOLDERS:
        raise HashLockError(
            "%s read %s (%s) from %s. That is a placeholder, and an episode "
            "stamped with a placeholder is scoreable and WRONG - strictly worse "
            "than one that refuses to be scored."
            % (name, value, _KNOWN_PLACEHOLDERS[value], source))
    if value.startswith(_PLACEHOLDER_PREFIX):
        raise HashLockError(
            "%s read %s from %s. That is campaign.py's retired 0xC0FFEE00+i "
            "placeholder. It is refused by name so it cannot return through a "
            "copied evidence bundle." % (name, value, source))
    return value


def _read_json(path, lock_name, what_produces_it):
    path = pathlib.Path(path)
    if not path.exists():
        raise MissingFreeze(
            "%s has no artifact to read: %s does not exist. It is produced by "
            "%s. This loader does not invent a hash and does not fall back to "
            "zeros - run the freeze, or point this at the artifact."
            % (lock_name, _rel(path), what_produces_it))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise HashLockError("%s: %s is not readable JSON: %s"
                            % (lock_name, _rel(path), exc))


def _field(doc, key, path, lock_name):
    value = doc.get(key)
    if not value:
        raise MissingFreeze(
            "%s: %s exists but carries no %r. A freeze record without the hash "
            "it froze is not a freeze record." % (lock_name, _rel(path), key))
    return value


def _rel(path):
    try:
        return str(pathlib.Path(path).relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path)


def _optional_freeze_path(default_path, env_var):
    override = os.environ.get(env_var)
    return pathlib.Path(override) if override else pathlib.Path(default_path)


def load_hash_locks(objective_set, *, part_b_path=None, corpus_root=None):
    """The five hash-locks across six fields, every one read from an artifact.

    `objective_set`: REQUIRED. The `ObjectiveSet` the TRIPWIRE will actually
        score with. Its `.hash` is the objective_set_hash unless a D3 freeze
        record exists, in which case the two must AGREE - which is the only
        version of this check that catches anything (see the module docstring).
        Passing the loaded instance rather than a path is deliberate: it makes
        it impossible for the campaign to hash one Objective Set and score with
        another.
    `part_b_path`: the derived-schema (Part B) document in force. Defaults to
        the one `crucible.conductor.real_target` hands `DerivedStamper`.
    `corpus_root`: the repository root the CORPUS is read from when
        `corpus_hash` is recomputed. Defaults to this repo, which is where
        `corpus.load` resolves it. A parameter rather than a constant for the
        same reason `part_b_path` is one: a check whose subject cannot be varied
        cannot be shown to fail.
    """
    if objective_set is None or not getattr(objective_set, "hash", None):
        raise HashLockError(
            "load_hash_locks() needs the Objective Set the TRIPWIRE will score "
            "with. objective_set_hash cannot be sourced from anywhere else: "
            "G1(b) compares the episode's stamp against the set the evaluator "
            "loaded, so a value taken from any other place makes every episode "
            "INVALID while looking like a stamped run.")

    values, provenance = {}, {}

    # -- gate_rule_hash. D2, dated. ---------------------------------------
    doc = _read_json(D2_GATE_RULE_FREEZE, "gate_rule_hash",
                     "scripts/freeze-d2-gate-rule.py --write")
    values["gate_rule_hash"] = _assert_shape(
        "gate_rule_hash",
        _field(doc, "gate_rule_hash", D2_GATE_RULE_FREEZE, "gate_rule_hash"),
        _rel(D2_GATE_RULE_FREEZE))
    provenance["gate_rule_hash"] = {
        "kind": FROZEN, "source": _rel(D2_GATE_RULE_FREEZE), "freeze": "D2",
        "frozen_at": doc.get("file_committed_at"),
        "head_commit": doc.get("head_commit")}

    # -- target_agent_hash + manifest_hash. D3, dated, one record. --------
    frozen = _read_json(D3_TARGET_FREEZE, "target_agent_hash",
                        "python -m target.refund_agent.freeze --write")
    for lock in ("target_agent_hash", "manifest_hash"):
        values[lock] = _assert_shape(
            lock, _field(frozen, lock, D3_TARGET_FREEZE, lock),
            _rel(D3_TARGET_FREEZE))
        provenance[lock] = {"kind": FROZEN, "source": _rel(D3_TARGET_FREEZE),
                            "freeze": "D3", "target_id": frozen.get("target_id")}

    # THE D3 TARGET FREEZE HAD NO SKEW DETECTOR UNTIL 2026-08-22, and it was the
    # only lock pair without one. `objective_set_hash` below and
    # `derived_schema_hash` further down are both recomputed from the artifact in
    # force and compared. These two were READ FROM THE RECORD AND TRUSTED.
    #
    # HOW THAT WAS FOUND, which is the part worth keeping: a lane repaired
    # `delegate_to_specialist` - a real change to a hash-locked package, moving
    # `target_agent_hash` to a different value - and the ENTIRE SUITE STAYED
    # GREEN. 1009 tests reported exactly what they reported before. The only
    # thing on the machine that noticed was `python -m target.refund_agent.freeze
    # --check`, which no test and no gate ever runs.
    #
    # So the two locks covering THE THING BEING ATTACKED were the two nobody
    # re-verified at run time. `tests/test_target_freeze.py` exercises the
    # COMPUTATION - determinism, CRLF-blindness, that a body edit moves the hash -
    # and never reads FROZEN.json, so it cannot see a record that has gone stale.
    # A test of the hasher is not a test of the freeze.
    try:
        from target.refund_agent import freeze as _target_freeze
        recomputed = _target_freeze.compute()
    except Exception as exc:                      # pragma: no cover - defensive
        raise HashLockError(
            "the D3 target freeze could not be recomputed, so its record cannot "
            "be verified: %r. A lock that cannot be re-derived is a lock nobody "
            "is checking." % (exc,))
    for lock in ("target_agent_hash", "manifest_hash"):
        live_value = recomputed.get(lock)
        if live_value != values[lock]:
            raise HashLockSkew(
                "%s: %s records %s, and the target package in force hashes to "
                "%s. THE TARGET MOVED AFTER IT WAS FROZEN. Every episode this "
                "run scores would be measured against an agent that is not the "
                "one the freeze names, so it stops here rather than being "
                "absorbed. Re-freeze deliberately (python -m "
                "target.refund_agent.freeze --write) or revert the target."
                % (lock, _rel(D3_TARGET_FREEZE), values[lock], live_value))

    # -- objective_set_hash. D3 in the plan; no record on disk yet. -------
    live = _assert_shape("objective_set_hash", objective_set.hash,
                         "the Objective Set the TRIPWIRE loaded")
    os_freeze = _optional_freeze_path(D3_OBJECTIVE_SET_FREEZE,
                                      ENV_OBJECTIVE_SET_FREEZE)
    if os_freeze.exists():
        doc = _read_json(os_freeze, "objective_set_hash", "the D3 freeze")
        recorded = _assert_shape(
            "objective_set_hash",
            _field(doc, "objective_set_hash", os_freeze, "objective_set_hash"),
            _rel(os_freeze))
        if recorded != live:
            raise HashLockSkew(
                "objective_set_hash: %s records %s, and the Objective Set this "
                "run loaded hashes to %s. THE DEFINITION OF BREACH MOVED AFTER "
                "IT WAS FROZEN. That is G1(b) at run level: no number from this "
                "run would be comparable to any other, so it stops here rather "
                "than being absorbed." % (_rel(os_freeze), recorded, live))
        values["objective_set_hash"] = recorded
        provenance["objective_set_hash"] = {
            "kind": FROZEN, "source": _rel(os_freeze), "freeze": "D3",
            "cross_checked_against": "the Objective Set loaded by the TRIPWIRE"}
    else:
        values["objective_set_hash"] = live
        provenance["objective_set_hash"] = {
            "kind": IN_FORCE,
            "source": getattr(objective_set, "path", None) or "the loaded Objective Set",
            "freeze": "D3 (NOT YET RECORDED)",
            "note": "hashed from the Objective Set in force for this run. No "
                    "dated D3 freeze record exists at %s, so this value pins "
                    "WHAT was measured and does not evidence WHEN it was pinned."
                    % _rel(D3_OBJECTIVE_SET_FREEZE)}

    # -- corpus_hash. D5, dated. THE FIFTH LOCK'S FIRST HALF. -------------
    #
    # THE RUN STOPS HERE, AND IT IS THE ONLY PLACE IT CAN. `corpus_hash` was
    # frozen at D5 with a dated record and a head commit, and then nothing
    # opened it: `EPISODE_STAMP_FIELDS` is three fields and this is not one,
    # `grep -c corpus_hash contracts/gate_rule.v1.yaml` is 0, and this loader
    # did not know the name. A corpus edited after D5 moved no assertion in the
    # entire system - and BUILD-LIST Tier 4 makes the D5 freeze land before the
    # first patch precisely because a corpus that can move after that is a
    # corpus the patch can be fitted to.
    #
    # Recomputed from the WORKING TREE. `corpus.load` resolves the corpus at
    # `REPO/corpus` and nowhere else, so the disk is the suite this run will
    # actually score against; `scripts/freeze-d5-corpus.py --check` reads HEAD
    # instead because it is auditing what was committed, which cannot see an
    # uncommitted edit. Same hasher either way - `corpus.freeze.corpus_hash_full`
    # is the only implementation and this does not add a second one.
    corpus_freeze = _optional_freeze_path(D5_CORPUS_FREEZE, ENV_CORPUS_FREEZE)
    try:
        from corpus.freeze import DiskSource, corpus_hash_full
        recomputed_corpus = corpus_hash_full(
            DiskSource(corpus_root or REPO))[:16]
    except Exception as exc:
        # A corpus that will not hash is not a corpus to measure against, and
        # this is the cheapest moment to learn it - before a model client is
        # constructed and before a cent is spent.
        raise HashLockError(
            "corpus_hash could not be recomputed from the corpus in force, so "
            "the D5 freeze record cannot be verified: %s: %s. A lock that "
            "cannot be re-derived is a lock nobody is checking."
            % (type(exc).__name__, exc))
    recomputed_corpus = _assert_shape(
        "corpus_hash", recomputed_corpus,
        "the corpus in force for this run (%s)" % _rel(
            pathlib.Path(corpus_root or REPO) / "corpus"))
    if corpus_freeze.exists():
        doc = _read_json(corpus_freeze, "corpus_hash",
                         "scripts/freeze-d5-corpus.py --write")
        recorded = _assert_shape(
            "corpus_hash",
            _field(doc, "corpus_hash", corpus_freeze, "corpus_hash"),
            _rel(corpus_freeze))
        if recorded != recomputed_corpus:
            raise HashLockSkew(
                "corpus_hash: %s records %s, and the corpus in force hashes to "
                "%s. THE SUITE MOVED AFTER IT WAS FROZEN. Every ASR and BPR "
                "this run would print has a denominator and a set of instances "
                "that the D5 record does not describe, so no number from it "
                "would be comparable to any number taken before or after - "
                "which is the whole reason the corpus is frozen before the "
                "first patch is written. It stops here rather than being "
                "absorbed. Re-freeze deliberately (python "
                "scripts/freeze-d5-corpus.py --write, which is a coordinator "
                "ruling with a written statement of what it invalidates) or "
                "revert the corpus. To see WHICH files moved: python "
                "scripts/freeze-d5-corpus.py --check."
                % (_rel(corpus_freeze), recorded, recomputed_corpus))
        values["corpus_hash"] = recorded
        provenance["corpus_hash"] = {
            "kind": FROZEN, "source": _rel(corpus_freeze), "freeze": "D5",
            "cross_checked_against": "the corpus in force, recomputed from the "
                                     "working tree",
            "head_commit": doc.get("head_commit"),
            "sealed_family": "BY REFERENCE ONLY - this check reads no file "
                             "under corpus/sealed/ and passes identically on a "
                             "clone that has none. It therefore does NOT "
                             "re-verify the sealed bytes; that is "
                             "scripts/seal-commitment.py --verify."}
    else:
        values["corpus_hash"] = recomputed_corpus
        provenance["corpus_hash"] = {
            "kind": IN_FORCE,
            "source": _rel(pathlib.Path(corpus_root or REPO) / "corpus"),
            "freeze": "D5 (NOT YET RECORDED)",
            "note": "hashed from the corpus in force for this run. No dated D5 "
                    "freeze record exists at %s, so this value pins WHICH "
                    "suite was measured and does not evidence WHEN it was "
                    "pinned." % _rel(D5_CORPUS_FREEZE)}

    # -- derived_schema_hash. D5, with the corpus. No record on disk yet. -
    part_b = pathlib.Path(part_b_path or PART_B_IN_FORCE)
    if not part_b.exists():
        raise MissingFreeze(
            "derived_schema_hash: Part B (%s) does not exist. It is the "
            "document the harness stamps every `derived.*` field from; without "
            "it there is nothing to hash and nothing to stamp." % _rel(part_b))
    _schema, computed = load_part_b(part_b)
    computed = _assert_shape("derived_schema_hash", computed, _rel(part_b))
    ds_freeze = _optional_freeze_path(D5_DERIVED_SCHEMA_FREEZE,
                                      ENV_DERIVED_SCHEMA_FREEZE)
    if ds_freeze.exists():
        doc = _read_json(ds_freeze, "derived_schema_hash", "the D5 corpus freeze")
        recorded = _assert_shape(
            "derived_schema_hash",
            _field(doc, "derived_schema_hash", ds_freeze, "derived_schema_hash"),
            _rel(ds_freeze))
        if recorded != computed:
            raise HashLockSkew(
                "derived_schema_hash: %s records %s, and Part B in force (%s) "
                "hashes to %s. The derived fields moved after the corpus was "
                "frozen, so the corpus and the harness are describing different "
                "documents." % (_rel(ds_freeze), recorded, _rel(part_b), computed))
        values["derived_schema_hash"] = recorded
        provenance["derived_schema_hash"] = {
            "kind": FROZEN, "source": _rel(ds_freeze), "freeze": "D5",
            "cross_checked_against": _rel(part_b)}
    else:
        values["derived_schema_hash"] = computed
        provenance["derived_schema_hash"] = {
            "kind": IN_FORCE, "source": _rel(part_b),
            "freeze": "D5 (NOT YET RECORDED)",
            "note": "hashed from the Part B document in force for this run. The "
                    "D5 corpus freeze has not landed, so this pins WHAT the "
                    "derived fields were and does not evidence WHEN."}

    return HashLocks(values, provenance)
