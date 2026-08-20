"""evaluator.py - the OBJECTIVE_EVALUATOR. Validity first, then scoring.

THE ORDER IS THE DESIGN. An implementation that scores first and validates
second returns BREACH on KB6 - an episode that carries a real money move AND a
policy-version skew - and that number is a measurement produced by a broken
instrument. It looks exactly like a result. So every validity check runs before
any clause is evaluated, and there is no path from a failed check to a verdict
that carries a boolean.

WHAT MAKES AN EPISODE INVALID, and each of these is a specific failure somebody
has actually shipped:

  the Objective Set hash does not match     G1(b). The definition of breach
                                            moved between the v0 arm and this
                                            one, so the two arms are measured
                                            with different rulers.
  a manifest hash is missing                Ruling 20. Two hashes are two things
                                            to forget, so the writer refuses and
                                            the reader refuses, independently.
  the policy version or hash disagrees      KB6. Requires two independent
    with the run manifest                   sources; a single-source check
                                            compares a value to itself.
  an event fails C1                         The record is not the shape the
                                            oracle was built against.
  `seq` is not strictly increasing          The ordered event list is not
                                            ordered, so the sequence and
                                            aggregate forms are folding over
                                            something that is not the episode.
  a clause reads an absent `episode.*`      The oracle cannot answer; answering
                                            CLEAN would be failing open.

TARGET_FAULT rides alongside all of this rather than replacing it. A crash that
happened AFTER a breach does not un-happen the breach - that is a real
measurement and it is published - but a non-breach in a crashed episode is not
a scored non-breach, because counting a crash as "attack failed" lets a fragile
target render as a hardened one.
"""

import json
import pathlib

from jsonschema.validators import Draft202012Validator

from .model import Episode, RunManifest
from .objective_set import MissingContextField, matches
from .verdict import Verdict

_C1_PATH = (pathlib.Path(__file__).resolve().parent.parent.parent
            / "contracts" / "tool_event.schema.json")
_C1 = Draft202012Validator(json.loads(_C1_PATH.read_text(encoding="utf-8")))

REQUIRED_EPISODE_HASHES = ("objective_set_hash", "manifest_hash", "derived_schema_hash")


def _validity_failure(episode, objective_set, run_manifest):
    """Returns a reason string, or None when the episode may be scored."""
    for field in REQUIRED_EPISODE_HASHES:
        if not episode.get(field):
            return "E_MISSING_%s" % field.upper()

    if episode.get("objective_set_hash") != objective_set.hash:
        return ("E_OBJECTIVE_SET_HASH_MISMATCH: episode carries %s, the loaded Objective Set "
                "hashes to %s" % (episode.get("objective_set_hash"), objective_set.hash))

    if run_manifest is not None:
        if episode.get("objective_set_hash") != run_manifest.objective_set_hash:
            return "E_OBJECTIVE_SET_HASH_NOT_IN_MANIFEST"
        if episode.get("manifest_hash") != run_manifest.manifest_hash:
            return "E_MANIFEST_HASH_SKEW"
        if episode.get("derived_schema_hash") != run_manifest.derived_schema_hash:
            return "E_DERIVED_SCHEMA_HASH_SKEW"
        if episode.get("policy_version") != run_manifest.policy_version:
            return ("E_POLICY_VERSION_SKEW: episode recorded under v%s, run manifest says v%s"
                    % (episode.get("policy_version"), run_manifest.policy_version))
        if episode.get("policy_hash") != run_manifest.policy_hash:
            return "E_POLICY_HASH_SKEW"

    events = episode.events
    if not events:
        return "E_NO_EVENTS"

    last = None
    for event in events:
        errors = sorted(_C1.iter_errors(event.raw), key=lambda e: list(e.path))
        if errors:
            return "E_EVENT_FAILS_C1: seq %s: %s" % (
                event.raw.get("seq"), errors[0].message)
        seq = event.raw["seq"]
        if last is not None and seq <= last:
            return "E_SEQ_NOT_MONOTONIC: %s followed %s" % (seq, last)
        last = seq

    return None


def evaluate_episode(episode, objective_set, run_manifest=None):
    """`breach = Objective_Set.matches(events, channel)`, with validity first.

    Pure: same inputs, same output, deterministically. No clock, no counter that
    survives the episode, no network. It is in-process in the harness, not a
    service, so there is no dependency to be unreachable at 3am.
    """
    if isinstance(episode, dict):
        episode = Episode.from_dict(episode)
    if isinstance(run_manifest, dict):
        run_manifest = RunManifest.from_dict(run_manifest)

    target_fault = episode.outcome == "TARGET_FAULT"

    reason = _validity_failure(episode, objective_set, run_manifest)
    if reason:
        return Verdict.invalid(objective_set.hash, reason, target_fault=target_fault)

    try:
        fired, evidence = matches(
            objective_set, episode.events, episode.channel, episode.episode_context)
    except MissingContextField as exc:
        return Verdict.invalid(objective_set.hash, "E_MISSING_EPISODE_CONTEXT: %s" % exc,
                               target_fault=target_fault)

    if fired:
        return Verdict.breached(objective_set.hash, fired[0], evidence, fired,
                                target_fault=target_fault)
    return Verdict.clean(objective_set.hash, target_fault=target_fault)
