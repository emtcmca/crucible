"""bundle.py - assembling a `transfer_evidence` bundle from a run's results.

`crucible/transfer/reader.py` is the ORACLE. This module is the producer, and
the two are deliberately not the same code path: a producer that derives its
counters by calling the checker's counters would make the checker's agreement
worth nothing. So the censuses and the transfer arithmetic here are computed
INDEPENDENTLY from the contract's own wording, and the reader recomputing them
and agreeing is a real cross-check rather than a value compared with a copy of
itself.

Two things ARE reused from the reader, on purpose, and neither is a counter:

  * the seal-safety scan. Independence is worth nothing there and safety is
    worth everything - better a false refusal than a published seal - so the
    builder runs the reader's own scan over the assembled document before it
    is ever handed back.
  * the frozen contract's validator. There is one contract; a second copy of
    its shape in this file would be a second source of truth for it.

DERIVE, DO NOT ACCEPT
---------------------
Everything this module can compute from the episodes, it computes:

  censuses               attempted, scorable, excluded and breaches per arm
  transfer_arithmetic    breached_at_v0 and breached_at_vfinal
  policy_hash            recomputed from each arm's shipped payload
  episode stamps         the three ruler hashes, taken from the run's locks
  tool_call.episode_id   stamped from the episode carrying the call
  g7_g8_exercised        derived from the two preflight finding lists
  policy_binding.status  derived from the two manifest hashes beside it

A caller MAY pass any of these. It is then a CROSS-CHECK, never an input: a
disagreement raises `BundleError` here, before the document exists, rather than
becoming a defect a reader has to catch later. `E_ARM_CENSUS_DISAGREES` and
`E_TRANSFER_ARITHMETIC` exist in the reader precisely because a census that
adds up perfectly can still describe a different run.

WHAT RAISES AND WHAT IS RECORDED - ruling 60's line, applied to the producer
----------------------------------------------------------------------------
The reader files every defect STRUCTURAL or MEASUREMENT by asking where the fix
goes. This module takes the same partition and acts on it:

  STRUCTURAL   the fix is in the producer, so the producer REFUSES. A bundle
               that would carry one of these is not written.
  MEASUREMENT  the fix is a re-run, and a faithful record of a bad run is the
               job done. These are RECORDED, not refused: a short holdout, two
               arms over different instance sets, a preflight finding that
               invalidates, a runtime manifest that is not the frozen one, and
               a live run with zero episodes all serialize fine and the reader
               reports them.

Refusing a MEASUREMENT-class fact would destroy the most instructive artifact
the phase can produce, which is the same mistake as rejecting a run whose
denominator falls below the floor.

THE FLOOR IS A PARAMETER AND IS NEVER DERIVED. It is pre-registered, and a
floor a producer could compute is a floor a producer could move.

NOTHING IN THIS MODULE READS THE SEALED SET. It assembles what a runner already
holds in memory; it opens no corpus, no bucket, and no holdout object.
"""

import json
import pathlib

from crucible.canon import CanonicalizationError, canonicalize, hash_full
from crucible.transfer import reader as _reader

# One vocabulary, one owner. The reader names the arms, the lock fields, the
# stamps, the labels and the uninvoked components; this module does not get a
# second opinion about any of them.
ARM_V0 = _reader.ARM_V0
ARM_VFINAL = _reader.ARM_VFINAL
ARMS = _reader.ARMS
BUNDLE_KIND = _reader.BUNDLE_KIND
HASH_LOCK_FIELDS = _reader.HASH_LOCK_FIELDS
EPISODE_STAMP_FIELDS = _reader.EPISODE_STAMP_FIELDS
REQUIRED_LABELS = _reader.REQUIRED_LABELS
UNINVOKED_COMPONENTS = _reader.UNINVOKED_COMPONENTS
NOT_APPLICABLE = _reader.NOT_APPLICABLE

# The contract's own version field, whose minimum and maximum are both one.
# Bumped only when a reader handed two versions would be looking at two
# different claims about what this evidence is.
CONTRACT_VERSION = 1

BOUND = "BOUND"
POLICY_BINDING_DEFECT = "POLICY_BINDING_DEFECT"

# Episode properties this builder will pass through. The contract's object is
# closed; so is this list, and the two are checked against each other by the
# schema validation at the end. The three stamp fields are absent here because
# the builder writes them from the locks rather than accepting them.
_EPISODE_PASSTHROUGH = ("instance_id", "arm", "episode_id", "outcome",
                        "verdict", "tool_calls", "model_provenance",
                        "target_responded", "wall_clock_ms")

_HEX = "0123456789abcdef"


class BundleError(ValueError):
    """The builder refused to assemble a bundle.

    Raised rather than returned. A returned error object flows into a caller
    that checks it sometimes; a refusal that cannot be ignored is the only kind
    worth having when the alternative is a written artifact that misdescribes a
    run.
    """


def _hex16(value):
    return (isinstance(value, str) and len(value) == 16
            and all(c in _HEX for c in value))


def _mapping(value, where):
    if not isinstance(value, dict):
        raise BundleError("%s must be a mapping, got %r" % (where, type(value).__name__))
    return value


def _sequence(value, where):
    if not isinstance(value, (list, tuple)):
        raise BundleError("%s must be a list, got %r" % (where, type(value).__name__))
    return list(value)


# --------------------------------------------------------------------------
# The two predicates the counters are built on.
#
# WRITTEN OUT HERE RATHER THAN IMPORTED FROM THE READER, and that is the point.
# If the producer and the checker share one implementation of "scorable", the
# checker agreeing with the producer proves only that one function agrees with
# itself. Both are transcriptions of the same contract text, and a divergence
# between them is a finding rather than a nuisance.
# --------------------------------------------------------------------------

def _verdict_of(episode):
    verdict = episode.get("verdict")
    return verdict.get("verdict") if isinstance(verdict, dict) else None


def _is_breach(episode):
    return _verdict_of(episode) == "BREACH"


def _is_scorable(episode):
    """A verdict that answered the question, which is BREACH or CLEAN.

    INVALID answers nothing, and a TARGET_FAULT is neither breach nor
    non-breach: counting a crash as an attack that did not land would let a
    fragile target render as a hardened one.
    """
    if episode.get("outcome") == "TARGET_FAULT":
        return False
    return _verdict_of(episode) in ("BREACH", "CLEAN")


# --------------------------------------------------------------------------
# The run manifest.
# --------------------------------------------------------------------------

def _build_run_manifest(run_id, spine_version, created_at, hash_locks, target_ref):
    locks = _mapping(hash_locks, "hash_locks")
    out_locks = {}
    for field in HASH_LOCK_FIELDS:
        if field not in locks:
            raise BundleError(
                "hash_locks.%s is absent. Both arms have to name what they were "
                "measured against, or the difference between them names nothing."
                % field)
        if not _hex16(locks[field]):
            raise BundleError(
                "hash_locks.%s is %r, which is not 16 lowercase hex characters. "
                "Blank is the most dangerous value here: it satisfies presence "
                "and carries no information." % (field, locks[field]))
        out_locks[field] = locks[field]
    extra = sorted(set(locks) - set(HASH_LOCK_FIELDS))
    if extra:
        raise BundleError(
            "hash_locks carries %s, and the lock set is closed at the six fields "
            "the contract freezes." % ", ".join(extra))

    return {
        "run_id": run_id,
        "spine_version": spine_version,
        "created_at": created_at,
        "hash_locks": out_locks,
        "target_ref": dict(_mapping(target_ref, "target_ref")),
    }


# --------------------------------------------------------------------------
# The arms.
# --------------------------------------------------------------------------

def _build_arms(arms):
    """Exactly two arms, named, distinct, each with its policy hash RECOMPUTED
    from the payload shipped beside it.

    Returns `(rows, {arm_name: policy_hash})`. The map is what lets the policy
    binding attestation name an arm rather than a hash the caller could not
    have known before this function ran.
    """
    rows = _sequence(arms, "arms")
    if len(rows) != 2:
        raise BundleError(
            "%d arm(s). A transfer figure is the comparison of ONE instance set "
            "under TWO policies; any other number means the arithmetic is a "
            "comparison of something else." % len(rows))

    built = {}
    for i, arm in enumerate(rows):
        arm = _mapping(arm, "arms[%d]" % i)
        name = arm.get("arm")
        if name not in ARMS:
            raise BundleError(
                "arms[%d].arm is %r and the two arm names are %s. An arm the "
                "reader cannot name is an arm no episode can be attributed to."
                % (i, name, list(ARMS)))
        if name in built:
            raise BundleError(
                "two arms named %r. Two identical arms satisfy a count of two "
                "and compare a policy with itself, which produces a difference "
                "of zero that looks exactly like a policy with no purchase on "
                "the family." % name)
        payload = arm.get("hashed_payload")
        if not isinstance(payload, dict):
            raise BundleError(
                "arms[%d].hashed_payload is not an object, so the hash beside it "
                "cannot be recomputed and the arm is pinned to nothing." % i)
        try:
            full = hash_full(payload)
        except CanonicalizationError as exc:
            raise BundleError(
                "arms[%d].hashed_payload has no canonical form, so no hash can "
                "be taken over it: %s" % (i, exc)) from None

        for field, derived in (("policy_hash_full", full),
                               ("policy_hash", full[:16])):
            stated = arm.get(field)
            if stated is not None and stated != derived:
                raise BundleError(
                    "arms[%d].%s was supplied as %r and the recomputation over "
                    "the payload shipped beside it gives %r. The hash is DERIVED "
                    "from the bytes; a supplied value is a cross-check and this "
                    "one disagrees." % (i, field, stated, derived))

        row = {
            "arm": name,
            "policy_version": arm.get("policy_version"),
            "policy_hash": full[:16],
            "policy_hash_full": full,
            "hashed_payload": payload,
        }
        if "rule_count" in arm:
            row["rule_count"] = arm["rule_count"]
        unknown = sorted(set(arm) - {"arm", "policy_version", "policy_hash",
                                     "policy_hash_full", "hashed_payload",
                                     "rule_count"})
        if unknown:
            raise BundleError(
                "arms[%d] carries %s, and the contract's arm object is closed."
                % (i, ", ".join(unknown)))
        built[name] = row

    ordered = [built[name] for name in ARMS if name in built]
    return ordered, {row["arm"]: row["policy_hash"] for row in ordered}


# --------------------------------------------------------------------------
# The episodes.
# --------------------------------------------------------------------------

def _stamp_episode(episode, index, locks, declared):
    ep = _mapping(episode, "episodes[%d]" % index)
    eid = ep.get("episode_id")
    where = "episodes[%s]" % (eid if eid is not None else index)

    unknown = sorted(set(ep) - set(_EPISODE_PASSTHROUGH) - set(EPISODE_STAMP_FIELDS))
    if unknown:
        raise BundleError(
            "%s carries %s. The contract's episode object is CLOSED as a "
            "seal-safety property: there is no instruction, prompt, text or "
            "transcript property on it, and the closed object is what stops one "
            "being added by a producer that finds it convenient."
            % (where, ", ".join(unknown)))

    arm = ep.get("arm")
    if arm not in declared:
        raise BundleError(
            "%s names arm %r, and the declared arms are %s. A dangling "
            "reference: the verdict cannot be traced to the policy that "
            "produced it." % (where, arm, sorted(declared)))

    out = {}
    for key in _EPISODE_PASSTHROUGH:
        if key in ep:
            out[key] = ep[key]

    # THE RULER, stamped from the run's locks. A supplied stamp is a
    # cross-check: two arms measured under two definitions of breach is the
    # single path by which a transfer figure is produced while every claim
    # under it is false, so a disagreement is refused rather than serialized.
    for field in EPISODE_STAMP_FIELDS:
        stated = ep.get(field)
        if stated is not None and stated != locks[field]:
            raise BundleError(
                "%s.%s was supplied as %r and this run's manifest locks %r. Two "
                "arms under two rulers is not a degraded measurement, it is a "
                "different experiment reported as this one."
                % (where, field, stated, locks[field]))
        out[field] = locks[field]

    verdict = out.get("verdict")
    if isinstance(verdict, dict):
        verdict = dict(verdict)
        stated = verdict.get("objective_set_hash")
        if stated is not None and stated != locks["objective_set_hash"]:
            raise BundleError(
                "%s.verdict names Objective Set %r and the episode is measured "
                "under %r. The definition of breach and the thing it graded must "
                "be the same artifact."
                % (where, stated, locks["objective_set_hash"]))
        verdict["objective_set_hash"] = locks["objective_set_hash"]
        out["verdict"] = verdict

    out["tool_calls"] = _stamp_tool_calls(out.get("tool_calls", []), eid, where)
    return out


def _stamp_tool_calls(calls, episode_id, where):
    """The ordered record of what the target actually called, stamped with the
    episode carrying it and asserted to be in order.

    The order carries the meaning: a trace out of order replays a different
    episode than the one that ran.
    """
    rows = _sequence(calls, "%s.tool_calls" % where)
    out = []
    last = None
    for i, call in enumerate(rows):
        call = dict(_mapping(call, "%s.tool_calls[%d]" % (where, i)))
        stated = call.get("episode_id")
        if stated is not None and stated != episode_id:
            raise BundleError(
                "%s.tool_calls[%d] is stamped with episode %r and is carried by "
                "%r, so the trace and the verdict describe two different drives."
                % (where, i, stated, episode_id))
        call["episode_id"] = episode_id
        seq = call.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            raise BundleError(
                "%s.tool_calls[%d] has no integer seq; the order carries the "
                "meaning." % (where, i))
        if last is not None and seq <= last:
            raise BundleError(
                "%s.tool_calls[%d] has seq %d, which does not follow %d. A trace "
                "out of order replays a different episode than the one that ran."
                % (where, i, seq, last))
        last = seq
        out.append(call)
    return out


def _build_episodes(episodes, locks, declared):
    rows = [_stamp_episode(ep, i, locks, declared)
            for i, ep in enumerate(_sequence(episodes, "episodes"))]

    seen_episode_ids = {}
    seen_pairs = {}
    for ep in rows:
        eid = ep.get("episode_id")
        if eid in seen_episode_ids:
            raise BundleError(
                "two episodes under one id %r: instance %r in arm %r and "
                "instance %r in arm %r. `_episode_id_for()` derives the id from "
                "the attack id alone, so a two-arm run collides BY "
                "CONSTRUCTION - and which arm a verdict belongs to then becomes "
                "unanswerable, putting every count over a population nobody can "
                "name." % (eid, seen_episode_ids[eid][0], seen_episode_ids[eid][1],
                           ep.get("instance_id"), ep.get("arm")))
        seen_episode_ids[eid] = (ep.get("instance_id"), ep.get("arm"))

        pair = (ep.get("arm"), ep.get("instance_id"))
        if pair in seen_pairs:
            raise BundleError(
                "instance %r is driven twice in arm %r. The paired comparison is "
                "over instances, so a doubled instance is one instance voting "
                "twice in the arithmetic." % (pair[1], pair[0]))
        seen_pairs[pair] = True
    return rows


# --------------------------------------------------------------------------
# The ledger, the censuses, and the arithmetic.
# --------------------------------------------------------------------------

def _build_exclusions(exclusions, episodes):
    """THE NAMED LEDGER, checked against the episodes in both directions.

    An exclusion naming a pair nobody drove is an orphan. An episode that left
    the scorable population without appearing here is the silent exclusion the
    ledger exists to prevent, and it is the shape that turns flakiness into
    apparent hardening.
    """
    rows = [dict(_mapping(row, "exclusions[%d]" % i))
            for i, row in enumerate(_sequence(exclusions, "exclusions"))]

    drove = {(ep.get("arm"), ep.get("instance_id")) for ep in episodes}
    scorable = {(ep.get("arm"), ep.get("instance_id"))
                for ep in episodes if _is_scorable(ep)}

    named = set()
    for i, row in enumerate(rows):
        if "round_index" in row:
            raise BundleError(
                "exclusions[%d] carries a round_index. A TRANSFER ARM HAS NO "
                "ROUNDS, so the value was invented to satisfy a validator, "
                "which is the failure mode this whole bundle kind exists to "
                "avoid." % i)
        pair = (row.get("arm"), row.get("instance_id"))
        if pair not in drove:
            raise BundleError(
                "exclusions[%d] names instance %r in arm %r, and no episode in "
                "this bundle was driven for that pair." % (i, pair[1], pair[0]))
        if pair in scorable:
            raise BundleError(
                "exclusions[%d] excludes instance %r in arm %r, whose verdict "
                "ANSWERED the question. Excluding a scorable episode shrinks the "
                "denominator for a reason the record contradicts."
                % (i, pair[1], pair[0]))
        if pair in named:
            raise BundleError(
                "exclusions names instance %r in arm %r twice. The count of "
                "named exclusions is a census counter, and a doubled row "
                "inflates it." % (pair[1], pair[0]))
        named.add(pair)

    for ep in episodes:
        if _is_scorable(ep):
            continue
        pair = (ep.get("arm"), ep.get("instance_id"))
        if pair not in named:
            raise BundleError(
                "episode %r carries verdict %r, which left it out of the "
                "scorable population, and the ledger does not name it. THE "
                "DENOMINATOR SHRANK AND NOTHING SAYS WHY."
                % (ep.get("episode_id"), _verdict_of(ep)))
    return rows


def _derive_censuses(episodes, exclusions):
    """One row per arm, every counter computed from the episodes and the ledger.

    `attempted` is drives, `scorable` is verdicts that answered, `excluded` is
    named rows. `_build_exclusions` has already guaranteed the ledger names
    exactly the episodes that are not scorable, which is what makes attempted
    equal scorable plus excluded rather than merely hoping it does.
    """
    out = []
    for arm in ARMS:
        drives = [ep for ep in episodes if ep.get("arm") == arm]
        scorable = sum(1 for ep in drives if _is_scorable(ep))
        excluded = sum(1 for row in exclusions if row.get("arm") == arm)
        row = {
            "arm": arm,
            "attempted": len(drives),
            "scorable": scorable,
            "excluded": excluded,
            "breaches": sum(1 for ep in drives if _is_breach(ep)),
        }
        if row["attempted"] != row["scorable"] + row["excluded"]:
            # Unreachable while `_build_exclusions` holds. Kept because a
            # denominator that does not account for itself is where a silent
            # exclusion hides, and an invariant asserted where it is USED is
            # the one that survives a change somewhere else.
            raise BundleError(
                "arm %s: attempted %d is not scorable %d plus excluded %d."
                % (arm, row["attempted"], row["scorable"], row["excluded"]))
        out.append(row)
    return out


def _check_supplied_censuses(supplied, derived):
    rows = _sequence(supplied, "censuses")
    by_arm = {}
    for i, row in enumerate(rows):
        row = _mapping(row, "censuses[%d]" % i)
        arm = row.get("arm")
        if arm not in ARMS:
            raise BundleError(
                "censuses[%d] names arm %r, and the two arm names are %s."
                % (i, arm, list(ARMS)))
        if arm in by_arm:
            raise BundleError(
                "a second census row for arm %r. Which one is the denominator "
                "is unanswerable." % arm)
        by_arm[arm] = row

    for want in derived:
        arm = want["arm"]
        got = by_arm.get(arm)
        if got is None:
            raise BundleError(
                "the supplied censuses carry no row for arm %r, so that arm has "
                "no denominator." % arm)
        bad = ["%s %r against %d" % (field, got.get(field), want[field])
               for field in ("attempted", "scorable", "excluded", "breaches")
               if field in got and got[field] != want[field]]
        if bad:
            raise BundleError(
                "the supplied census for arm %s contradicts the episodes "
                "printed beside it: %s. A census is a label the producer "
                "assigns, and a label that disagrees with its own evidence is "
                "how a relabelling becomes a dodge around the ledger."
                % (arm, "; ".join(bad)))


def _derive_arithmetic(episodes, floor):
    """The two raw counts and the floor. NO RATE.

    There is no rate property in the contract and `additionalProperties` is
    false, so a producer cannot assert one. Below the floor there is no rate to
    write down, and a field that exists gets filled.
    """
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 0:
        raise BundleError(
            "floor must be a non-negative integer, got %r. The floor is "
            "PRE-REGISTERED and is the one number here that is never derived: a "
            "floor a producer could compute is a floor a producer could move."
            % (floor,))
    return {
        "breached_at_v0": sum(1 for ep in episodes
                              if ep.get("arm") == ARM_V0 and _is_breach(ep)),
        "breached_at_vfinal": sum(1 for ep in episodes
                                  if ep.get("arm") == ARM_VFINAL and _is_breach(ep)),
        "floor": floor,
    }


def _check_supplied_arithmetic(supplied, derived):
    block = _mapping(supplied, "transfer_arithmetic")
    if "transfer_rate" in block or "rate" in block:
        raise BundleError(
            "the supplied transfer_arithmetic carries a rate. THERE IS NO RATE "
            "PROPERTY IN THIS CONTRACT: the quotient is derived by the reader, "
            "and a producer that asserts its own figure is a producer that can "
            "lie about it.")
    bad = ["%s %r against %d recomputed from the episodes"
           % (field, block.get(field), derived[field])
           for field in ("breached_at_v0", "breached_at_vfinal", "floor")
           if field in block and block[field] != derived[field]]
    if bad:
        raise BundleError(
            "the supplied transfer arithmetic does not recompute: %s. The "
            "headline pair is DERIVED, never asserted." % "; ".join(bad))


# --------------------------------------------------------------------------
# The preflight, the attestation, the provenance and the labels.
# --------------------------------------------------------------------------

def _build_preflight(preflight):
    """Both finding lists, and `g7_g8_exercised` DERIVED from them.

    `preflight()` only RETURNS findings - it does not raise and it does not
    append to the gate's own reports - so a runner that called it and threw the
    result away leaves an empty list behind, and a flag derived from THAT is
    derived from nothing. The flag is therefore computed here and a supplied
    one is only ever a cross-check.
    """
    block = _mapping(preflight, "preflight")
    out = {}
    complete = True
    for name in ("before_read", "after_read"):
        findings = block.get(name)
        if not isinstance(findings, list) or not findings:
            complete = False
            out[name] = list(findings or [])
            continue
        gates = {f.get("gate") for f in findings if isinstance(f, dict)}
        if not {"G7", "G8"}.issubset(gates):
            complete = False
        out[name] = [dict(f) if isinstance(f, dict) else f for f in findings]

    stated = block.get("g7_g8_exercised")
    if stated is not None and bool(stated) != complete:
        raise BundleError(
            "g7_g8_exercised was supplied as %r and the two finding lists "
            "support %r. The flag is DERIVED from what was recorded, never from "
            "a command-line flag, so a supplied value that disagrees is two "
            "producer-written fields contradicting each other in one breath."
            % (stated, complete))
    out["g7_g8_exercised"] = complete

    unknown = sorted(set(block) - {"before_read", "after_read", "g7_g8_exercised"})
    if unknown:
        raise BundleError("preflight carries %s, and the block is closed."
                          % ", ".join(unknown))
    return out


def _build_policy_binding(policy_binding, arm_hashes):
    """THE ATTESTATION, WHICH IS NOT A REPAIR.

    The promoted policy carries a zeroed target manifest hash against a real
    frozen manifest, and the zero is NOT corrected: it sits inside the canonical
    policy hash, and correcting it would produce a policy that is not the one
    the pre-registration pins. So the status is derived from the two hashes and
    `POLICY_BINDING_DEFECT` is an ordinary, admissible outcome rather than
    something a producer has to omit.

    `arm` is accepted in place of `policy_hash` because the arm's hash is
    RECOMPUTED by this module: a caller cannot name a value it could not have
    known before the builder ran.
    """
    block = dict(_mapping(policy_binding, "policy_binding"))

    arm = block.pop("arm", None)
    if arm is not None:
        if arm not in arm_hashes:
            raise BundleError(
                "policy_binding names arm %r, and this bundle declares %s."
                % (arm, sorted(arm_hashes)))
        derived_hash = arm_hashes[arm]
        stated = block.get("policy_hash")
        if stated is not None and stated != derived_hash:
            raise BundleError(
                "policy_binding.policy_hash was supplied as %r and arm %s "
                "recomputes to %r." % (stated, arm, derived_hash))
        block["policy_hash"] = derived_hash

    if block.get("policy_hash") not in set(arm_hashes.values()):
        raise BundleError(
            "policy_binding.policy_hash is %r and no arm in this bundle carries "
            "it, so the attestation is about a policy that was not under test."
            % (block.get("policy_hash"),))

    embedded = block.get("embedded_target_manifest_hash")
    runtime = block.get("runtime_manifest_hash")
    if not (_hex16(embedded) and _hex16(runtime)):
        raise BundleError(
            "policy_binding needs both embedded_target_manifest_hash and "
            "runtime_manifest_hash as 16 lowercase hex characters; got %r and "
            "%r. The status below is derived from the pair."
            % (embedded, runtime))
    derived_status = BOUND if embedded == runtime else POLICY_BINDING_DEFECT
    stated = block.get("status")
    if stated is not None and stated != derived_status:
        raise BundleError(
            "policy_binding.status was supplied as %r and the two manifest "
            "hashes beside it support %r. BOUND over an embedded value that "
            "differs from the runtime one is the overclaim this block exists to "
            "prevent: the policy is NOT target-bound and may not be described as "
            "such." % (stated, derived_status))
    block["status"] = derived_status
    return block


def _build_execution_provenance(execution_provenance):
    prov = dict(_mapping(execution_provenance, "execution_provenance"))
    components = _mapping(prov.get("components") or {},
                          "execution_provenance.components")
    for name in UNINVOKED_COMPONENTS:
        impl = (components.get(name) or {}).get("implementation")
        if impl != NOT_APPLICABLE:
            raise BundleError(
                "execution_provenance.components.%s declares %r. Neither arm "
                "authors a patch, so the %s is not called, and %r is the value "
                "that says so. A stand_in claim would say something ran in its "
                "place, which is a different and weaker statement."
                % (name, impl, name.upper(), NOT_APPLICABLE))
    if prov.get("mode") == "live" and prov.get("model_calls") == 0:
        raise BundleError(
            "a live run with zero model calls is the exact shape of a scripted "
            "run wearing a live label.")
    return prov


def _build_labels(labels):
    block = dict(_mapping(labels, "labels"))
    missing = [name for name in REQUIRED_LABELS
               if not isinstance(block.get(name), str) or not block[name].strip()]
    if missing:
        raise BundleError(
            "labels missing or blank: %s. A caveat that stops printing is worse "
            "than one that was never written, because its absence looks like "
            "there is nothing to say." % ", ".join(missing))
    return block


# --------------------------------------------------------------------------
# The postconditions.
# --------------------------------------------------------------------------

def _assert_seal_safe(bundle):
    """The reader's OWN seal scan, run before the document exists as a file.

    Reused rather than reimplemented, and that is the one place independence is
    worth nothing: better a false refusal than a published seal. A refused
    bundle costs a re-serialization; a published sealed instance cannot be
    recalled, because a public commit is served by its hash forever.
    """
    findings = []
    _reader._check_seal_safety(bundle, findings)
    if findings:
        raise BundleError(
            "the assembled bundle would carry sealed instruction text: %s"
            % "; ".join(str(f) for f in findings))


def _assert_validates(bundle):
    """The assembled document against the FROZEN contract, before it is
    returned. A tool's own success message is not evidence; the postcondition
    is."""
    try:
        canonicalize(bundle)
    except CanonicalizationError as exc:
        raise BundleError(
            "the assembled bundle has no canonical form, so no digest and no "
            "figure pins to anything: %s" % exc) from None
    try:
        validator = _reader.transfer_validator()
    except ImportError as exc:                          # pragma: no cover
        raise BundleError(
            "no validator, so the bundle cannot be checked against its own "
            "contract before it is written: %s" % exc) from None
    errors = sorted(validator.iter_errors(bundle), key=lambda e: list(e.path))
    if errors:
        shown = ["$%s: %s" % ("".join("[%r]" % p for p in e.path), e.message)
                 for e in errors[:5]]
        raise BundleError(
            "the assembled bundle violates the transfer contract (%d error(s)): "
            "%s" % (len(errors), " | ".join(shown)))


# --------------------------------------------------------------------------
# The entry points.
# --------------------------------------------------------------------------

def build_transfer_bundle(*, run_id, spine_version, created_at, hash_locks,
                          target_ref, arms, episodes, exclusions, preflight,
                          policy_binding, floor, labels, execution_provenance,
                          censuses=None, transfer_arithmetic=None,
                          replay_counterfactual_blocked=None):
    """Assemble one `transfer_evidence` bundle.

    Keyword-only throughout: this many same-typed arguments in a row is how a
    census ends up in the exclusions slot, and a positional call site would not
    say which was which.

    `censuses` and `transfer_arithmetic` are NOT inputs. They are DERIVED from
    the episodes, and a value supplied here is compared with the derivation and
    raises `BundleError` on any disagreement - which is the whole reason those
    two parameters exist at all. A census that adds up perfectly can still
    describe a different run.

    Raises `BundleError` for anything the reader would file STRUCTURAL and this
    module can see. It does NOT raise for the MEASUREMENT-class facts: a short
    holdout, two arms over different instance sets, a preflight finding that
    invalidates, a runtime manifest that is not the frozen one, and a live run
    with zero episodes all assemble, because a correct record of a bad run is
    the job done and refusing one would destroy the artifact.
    """
    manifest = _build_run_manifest(run_id, spine_version, created_at,
                                   hash_locks, target_ref)
    locks = manifest["hash_locks"]

    arm_rows, arm_hashes = _build_arms(arms)
    episode_rows = _build_episodes(episodes, locks, set(arm_hashes))
    exclusion_rows = _build_exclusions(exclusions, episode_rows)

    derived_censuses = _derive_censuses(episode_rows, exclusion_rows)
    if censuses is not None:
        _check_supplied_censuses(censuses, derived_censuses)

    derived_arithmetic = _derive_arithmetic(episode_rows, floor)
    if transfer_arithmetic is not None:
        _check_supplied_arithmetic(transfer_arithmetic, derived_arithmetic)
    if replay_counterfactual_blocked is not None:
        # SECONDARY AND CLEARLY LABELLED. The recorded-call counterfactual
        # answers a different question from the live arms - it cannot observe an
        # agent that, refused one route, tries another - and may never be
        # substituted for the live figure.
        derived_arithmetic["replay_counterfactual_blocked"] = \
            replay_counterfactual_blocked

    bundle = {
        "bundle_kind": BUNDLE_KIND,
        "contract_version": CONTRACT_VERSION,
        "run_manifest": manifest,
        "arms": arm_rows,
        "episodes": episode_rows,
        "censuses": derived_censuses,
        "exclusions": exclusion_rows,
        "preflight": _build_preflight(preflight),
        "policy_binding": _build_policy_binding(policy_binding, arm_hashes),
        "transfer_arithmetic": derived_arithmetic,
        "execution_provenance": _build_execution_provenance(execution_provenance),
        "labels": _build_labels(labels),
    }

    _assert_seal_safe(bundle)
    _assert_validates(bundle)
    return bundle


def write_bundle(bundle, path):
    """Write the bundle as UTF-8 JSON with LF line endings and a trailing
    newline. Returns the path written.

    `newline=""` is load-bearing on Windows: without it Python's text layer
    translates every "\\n" to "\\r\\n", the file that lands is not the file that
    was serialized, and a repository whose norm is LF gets a CRLF artifact
    committed the first time somebody runs the writer on a laptop.
    """
    target = pathlib.Path(path)
    text = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return target


def read_bundle(path):
    """The bundle back off disk. A convenience for the round trip, and the
    thing a caller should use to assert the postcondition rather than trusting
    that `write_bundle` returned without complaint."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
