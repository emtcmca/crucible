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

ENV_OBJECTIVE_SET_FREEZE = "CRUCIBLE_OBJECTIVE_SET_FREEZE"
ENV_DERIVED_SCHEMA_FREEZE = "CRUCIBLE_DERIVED_SCHEMA_FREEZE"

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
    """The five values plus, for each, where it came from and how strong that is.

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


def load_hash_locks(objective_set, *, part_b_path=None):
    """The five hash-locks, every one read from an artifact.

    `objective_set`: REQUIRED. The `ObjectiveSet` the TRIPWIRE will actually
        score with. Its `.hash` is the objective_set_hash unless a D3 freeze
        record exists, in which case the two must AGREE - which is the only
        version of this check that catches anything (see the module docstring).
        Passing the loaded instance rather than a path is deliberate: it makes
        it impossible for the campaign to hash one Objective Set and score with
        another.
    `part_b_path`: the derived-schema (Part B) document in force. Defaults to
        the one `crucible.conductor.real_target` hands `DerivedStamper`.
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
