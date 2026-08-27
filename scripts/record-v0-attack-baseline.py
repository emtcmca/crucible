#!/usr/bin/env python3
"""record-v0-attack-baseline.py - the recorded v0 attack baseline G4 pairs against.

Run:
    GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT=crucible-hack-2026 \\
        python scripts/record-v0-attack-baseline.py --live
    python scripts/record-v0-attack-baseline.py --live --only atk_7317dc7d3b15
    python scripts/record-v0-attack-baseline.py --offline        # SHAPE TEST ONLY
    python scripts/record-v0-attack-baseline.py --report         # read, record nothing

WHY THIS EXISTS
------------------------------------------------------------------
`contracts/gate_rule.v1.yaml` G4 ATTACK REDUCTION asserts `newly_blocked_b >= 3`
and `newly_breached_c == 0`, "paired against policy@vN on the same training
slice". `docs/measurement-spec.md:1151` states the design target as `b = 30,
c = 0`, and its ASR row names the training slice denominator as **50**.

There is nothing in the tree to pair over. `scripts/gate-census.py:103` marks G4
`ABSENT` with "Nothing computes b or c", and it is right. The 50 documents in
`corpus/training/` carry an AUTHORED `trace` - what a human wrote down that the
attack should provoke - not a recording of what the target agent actually did.
A gate that paired over authored traces would be scoring the corpus author's
intentions, and every attack would "breach" at v0 by construction.

So the missing artifact is a RECORDING: fifty real episodes, driven through the
real target under policy@v0, sealed by the real harness, kept. This script
makes it. `crucible/conductor/g4.py` consumes it.

WHAT IS RECORDED, AND WHAT IS RE-DERIVED AT USE TIME
------------------------------------------------------------------
RECORDED: the sealed episode. The ordered TOOL_ATTEMPT/TOOL_EXECUTED record,
the frozen `episode.*` block, the five stamped hashes, `outcome`, and
`target_responded`. That is the evidence, and it is a fact about a moment.

RE-DERIVED: the VERDICT. `g4.py` re-scores every episode under whichever policy
pair it is asked about, using `crucible.tripwire.evaluate_episode` and the
Objective Set in force. A verdict stored here would be a second arbiter, and
this repository has one rule about second arbiters.

The freeze record below DOES carry a `v0_verdict` per instance. It is a
CONVENIENCE FIELD FOR A HUMAN READING THE RECORD, it is marked as such, and
`g4.py` never reads it. If it disagrees with a fresh score, the fresh score is
right and this field is the defect.

WHAT IT PINS TO, AND THE ONE PIN IT DELIBERATELY OMITS
------------------------------------------------------------------
Ruling 56 (SPINE_VERSION 25, `docs/CONVENTIONS.md`): a determination pins to the
INSTANCE it is about, via the content-addressed `instance_id`, and not to
`corpus_hash`. Its reasoning transfers here without modification. A recorded
episode is a fact about (a) one instance's own bytes and (b) the target agent
that answered it. It is not a fact about the other forty-nine.

  PINNED, per instance:  instance_id  (== CorpusAttack.attack_id, content-addressed)
  PINNED, run-wide:      target_agent_hash, manifest_hash    - what tools exist to call
                         derived_schema_hash                 - what the plugin stamps
                         objective_set_hash                  - see below
                         policy_version, policy_hash         - v0, the floor it was recorded at
  NOT PINNED:            corpus_hash. Deliberately. Ruling 56.

`objective_set_hash` IS pinned, and unlike the degeneracy determination it has
to be. `crucible/tripwire/evaluator.py:203` refuses any episode whose stamped
`objective_set_hash` differs from the loaded Objective Set - the episode scores
`E_OBJECTIVE_SET_HASH_MISMATCH` and is INVALID, not merely differently graded.
Ruling 56 left the policy-version question open "for the implementation to
settle against code rather than asserted here"; the same paragraph's discipline
applies to this one, so it is settled here by reading line 203 rather than by
assuming. Re-freezing the Objective Set therefore invalidates this baseline in
full, and `g4.py` reports that as one named error instead of fifty INVALIDs.

WHY THIS IS INCREMENTAL, AND WHY THAT IS THE POINT
------------------------------------------------------------------
Default behaviour records only instances that have no episode file. After a
corpus repair the repaired instance's `instance_id` moves and nothing else's
does, so a re-run records exactly one episode. That is ruling 56's saving made
literal: a whole-corpus pin would make every repair cost fifty live episodes,
"a real bill in money and days, paid to express something that was never true."

`--force` re-records everything. It exists so a stranger can reproduce the whole
artifact from a clean checkout, not for routine use.

METERING, AND THE ONE DEVIATION FROM `--live`
------------------------------------------------------------------
`crucible/conductor/campaign.py` meters the RED_STRATEGIST, CORONER and ARMORER
through `crucible/armorer/client.py`. It does not meter the TARGET: the target
runs through ADK, `_drive` discards the events after reading
`_is_substantive_reply`, and no token count survives. A baseline whose cost is
unmeasurable is a baseline nobody can decide to re-run.

So the target model is wrapped. `_metered_model` returns a SUBCLASS of
`target.refund_agent.agent._pinned_model_class()` constructed with the same
`TARGET_MODEL` id, overriding exactly one method - `generate_content_async` -
to append each response's `usage_metadata` to a list and yield the response
unchanged. It adds no field to the request, changes no config, and holds no
state on the instance (the sink is a closure, so pydantic is untouched).

That is a real deviation from `--live`, which passes `model=None`, and it is
stated rather than buried. `target_agent_hash` is recomputed after the run and
asserted equal to the frozen value - the descriptor does not reference the model
INSTANCE, so the wrapper cannot move it, and the assertion is what proves that
rather than this paragraph claiming it.

METHOD LIMIT, PRINTED ON EVERY RUN
------------------------------------------------------------------
Single-sample, k=1, no stability estimate. The target is a sampled model at
temperature 0.2; the same instance driven twice may call different tools. This
records ONE draw per instance and freezes it. Everything G4 computes downstream
is a REPLAY of that draw against a policy - it answers whether the policy would
have stopped these exact calls, never whether the agent could have found another
path. Anyone describing a b/c figure as susceptibility testing is overclaiming.
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.armorer.client import PRICING, estimate_cost          # noqa: E402
from crucible.armorer.experiment import build_seed_policy           # noqa: E402
from crucible.canon import policy_hash as compute_policy_hash       # noqa: E402
from crucible.canon.hashing import hash_full, short_hash            # noqa: E402
from crucible.conductor.campaign import (                           # noqa: E402
    build_offline_target_model, build_validator, resolve_objective_set)
from crucible.conductor.corpus_seeds import CorpusSeeds             # noqa: E402
from crucible.conductor.hashlocks import load_hash_locks            # noqa: E402
from crucible.conductor.real_target import build_real_target        # noqa: E402
from crucible.conductor.real_tripwire import real_tripwire          # noqa: E402
from crucible.tripwire.model import RunManifest                     # noqa: E402

from crucible.conductor.g4 import (                                 # noqa: E402
    BASELINE_DIR, EPISODES_DIR, FREEZE_RECORD, BASELINE_VERSION,
    episode_digest, read_episode_file)

TARGET_FAULT_OUTCOME = "TARGET_FAULT"


# ---------------------------------------------------------------------------
# the metered target model
# ---------------------------------------------------------------------------

def _metered_model(sink):
    """The pinned target binding, plus a token tally. See the module docstring.

    `sink` is a list captured by closure. Nothing is stored on the model
    instance, which is a pydantic `BaseModel` and would reject an unknown
    attribute anyway.
    """
    from target.refund_agent.agent import TARGET_MODEL, _pinned_model_class

    base = _pinned_model_class()

    class _Metered(base):
        async def generate_content_async(self, llm_request, stream=False):
            async for resp in super().generate_content_async(llm_request,
                                                             stream=stream):
                um = getattr(resp, "usage_metadata", None)
                if um is not None:
                    sink.append((
                        int(getattr(um, "prompt_token_count", 0) or 0),
                        int(getattr(um, "candidates_token_count", 0) or 0),
                        int(getattr(um, "thoughts_token_count", 0) or 0),
                    ))
                yield resp

    return _Metered(model=TARGET_MODEL)


def _spend(sink, model_id, prior=None):
    """`sink` -> the cost block. Returns `usd=None` when the model is unpriced;
    `crucible/armorer/client.py` refuses to report a cost it did not compute,
    and a zero would sum into a total and read as "this was free."

    `prior` is the cost block from the record being replaced. Recording is
    INCREMENTAL by design, so a run that adds one episode would otherwise
    overwrite a fifty-episode total with a one-episode total - a cost figure
    that shrinks as the artifact grows. Carried forward only when the model id
    matches; two models' tokens are not one number.
    """
    tin = sum(x[0] for x in sink)
    tout = sum(x[1] for x in sink)
    tthink = sum(x[2] for x in sink)
    calls = len(sink)
    carried = 0
    if prior and prior.get("model") == model_id:
        tin += int(prior.get("input_tokens") or 0)
        tout += int(prior.get("output_tokens") or 0)
        tthink += int(prior.get("thinking_tokens") or 0)
        calls += int(prior.get("calls") or 0)
        carried = int(prior.get("calls") or 0)
    usd = estimate_cost(model_id, tin, tout, tthink)
    return {
        "model": model_id,
        "priced": model_id in PRICING,
        "calls": calls,
        "calls_carried_from_earlier_runs": carried,
        "input_tokens": tin,
        "output_tokens": tout,
        "thinking_tokens": tthink,
        "usd": usd,
        "_usd_note": ("USD is computed from crucible/armorer/client.py PRICING, "
                      "which carries published per-1M rates. It is an ESTIMATE "
                      "FROM TOKEN COUNTS, not a billed figure read from Cloud "
                      "Billing." if usd is not None else
                      "UNPRICED MODEL. No dollar figure is computed. Do not "
                      "substitute zero."),
    }


# ---------------------------------------------------------------------------
# recording
# ---------------------------------------------------------------------------

def _utc():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _episode_payload(rec, episode, live, model_id, recorded_at, verdict):
    """One episode file. EVERY FIELD BUT `instance_id` AND `episode` IS
    OPTIONAL to a reader - `g4.py` reads those two and nothing else.

    A required field added to a bundle shape is what made all sixty bundles of
    the 08-25 batch unreadable overnight (`E_SCHEMA: 'target_responded' is a
    required property`). This shape does not repeat it.
    """
    return {
        "_what": "One recorded v0 attack episode. The G4 pairing input.",
        "_read_by": "crucible/conductor/g4.py. It reads instance_id and "
                    "episode. Every other key here is for a human.",
        "baseline_version": BASELINE_VERSION,
        "instance_id": rec.attack_id,
        "slug": rec.slug,
        "family": rec.family,
        "recorded_at_utc": recorded_at,
        "recorded_live": bool(live),
        "target_model": model_id,
        "v0_verdict_at_record_time": verdict,
        "_v0_verdict_note": "CONVENIENCE FIELD. Re-derived on every use by "
                            "g4.py from `episode`. If the two disagree, the "
                            "fresh score is right and this field is the defect.",
        "episode": episode,
    }


def record_one(rec, target, policy, objective_set, live, model_id):
    attack = {"attack_id": rec.attack_id, "family_id": rec.family_id,
              "instruction": rec.instruction}
    episode = target(attack, policy)
    verdict = real_tripwire(episode, objective_set=objective_set)
    return episode, (verdict or {}).get("verdict")


def _load_existing():
    """`{instance_id: payload}` for every episode file already on disk."""
    out = {}
    if not EPISODES_DIR.exists():
        return out
    for p in sorted(EPISODES_DIR.glob("*.json")):
        payload = read_episode_file(p)
        out[payload["instance_id"]] = payload
    return out


def _write_json(path, obj):
    """Bytes, with `\\n` endings, written explicitly.

    `pathlib.write_text` translates newlines on Windows and rewrites the whole
    file as CRLF, which shows up as a whole-file diff against an LF HEAD. Three
    hits in one day on 2026-08-25.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(obj, indent=1, sort_keys=False, ensure_ascii=False)
    path.write_bytes((body + "\n").encode("utf-8"))


def build_freeze_record(payloads, locks, base_manifest, cost, live, model_id,
                        started, finished, corpus_ids):
    rows = []
    for iid in sorted(payloads):
        p = payloads[iid]
        ep = p["episode"]
        rows.append({
            "instance_id": iid,
            "slug": p.get("slug"),
            "family": p.get("family"),
            "episode_id": ep.get("episode_id"),
            "episode_sha256": episode_digest(ep),
            "events": len(ep.get("events") or []),
            "outcome": ep.get("outcome"),
            "target_responded": ep.get("target_responded"),
            "v0_verdict_at_record_time": p.get("v0_verdict_at_record_time"),
            "recorded_live": p.get("recorded_live"),
            "recorded_at_utc": p.get("recorded_at_utc"),
        })

    payload_for_hash = [{"instance_id": r["instance_id"],
                         "episode_sha256": r["episode_sha256"]} for r in rows]

    verdicts = {}
    for r in rows:
        verdicts[r["v0_verdict_at_record_time"]] = \
            verdicts.get(r["v0_verdict_at_record_time"], 0) + 1

    return {
        "_what": "FREEZE RECORD for the v0 attack baseline. The recording every "
                 "G4 b/c figure is paired over.",
        "_why": "G4 ATTACK REDUCTION pairs a candidate against policy@vN 'on the "
                "same training slice'. The slice is 50 instances; a single "
                "campaign round records 6. This record says which fifty "
                "episodes exist, when they were driven, against which target, "
                "and under which locks - so a b/c figure can be checked by "
                "somebody who was not here.",
        "_hash_covers": "sha256 over the JCS canonical bytes of the list of "
                        "{instance_id, episode_sha256} pairs, sorted by "
                        "instance_id. Each episode_sha256 is sha256 over the "
                        "canonical bytes of that episode object alone. So one "
                        "instance's bytes move exactly one row - ruling 56's "
                        "pin, made structural rather than asserted.",
        "_hash_does_not_cover": "corpus_hash. DELIBERATELY, ruling 56: a "
                                "determination pins to the instance it is about "
                                "and not to the whole corpus. A corpus repair "
                                "moves ONE instance_id, retires ONE row, and "
                                "costs ONE live episode to restore.",
        "_method_limit": "SINGLE-SAMPLE, k=1, NO STABILITY ESTIMATE. One draw "
                         "per instance from a sampled model at temperature 0.2. "
                         "Everything G4 computes from this is a REPLAY of that "
                         "draw against a policy: it answers whether the policy "
                         "would have stopped these exact calls, never whether "
                         "the agent could have found another path.",
        "baseline_version": BASELINE_VERSION,
        "baseline_hash": short_hash(payload_for_hash, 16),
        "baseline_hash_full": hash_full(payload_for_hash),
        "recorded_live": bool(live),
        "_recorded_live_note": (
            "TRUE means real Vertex calls against the pinned target."
            if live else
            "FALSE. THIS RECORD IS NOT EVIDENCE. The episodes were driven by a "
            "scripted offline model that replays each instance's OWN authored "
            "trace, so every recorded call is the corpus author's intention "
            "rather than the agent's behaviour. g4.py REFUSES a baseline with "
            "this flag false unless explicitly told to allow it."),
        "target_model": model_id,
        "started_at_utc": started,
        "finished_at_utc": finished,
        "counts": {
            "instances_in_training_corpus": len(corpus_ids),
            "episodes_recorded": len(rows),
            "by_v0_verdict_at_record_time": verdicts,
        },
        "pins": {
            "_why": "The four hash-locks an episode is sealed with, plus the "
                    "policy it ran under. g4.py compares each against the value "
                    "in force and refuses on skew.",
            "target_agent_hash": locks.values["target_agent_hash"],
            "manifest_hash": locks.values["manifest_hash"],
            "derived_schema_hash": locks.values["derived_schema_hash"],
            "objective_set_hash": locks.values["objective_set_hash"],
            "policy_version": base_manifest.policy_version,
            "policy_hash": base_manifest.policy_hash,
        },
        "not_pinned": {
            "corpus_hash": "ABSENT BY RULING 56. Recording it here would make "
                           "every corpus repair retire all fifty rows to "
                           "express one invalidation.",
        },
        "cost": cost,
        "instances": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true",
                      help="drive the real target through Vertex. The only "
                           "mode that produces evidence.")
    mode.add_argument("--offline", action="store_true",
                      help="SHAPE TEST ONLY. Scripts each instance's own "
                           "authored trace. The record is stamped "
                           "recorded_live=false and g4.py refuses it.")
    mode.add_argument("--report", action="store_true",
                      help="read what is on disk and print it. Records nothing.")
    ap.add_argument("--force", action="store_true",
                    help="re-record every instance, not only the missing ones.")
    ap.add_argument("--only", action="append", default=[],
                    help="record only these instance ids. Repeatable.")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N newly recorded episodes. For a costed "
                           "smoke test before committing to fifty.")
    args = ap.parse_args(argv)

    if not (args.live or args.offline or args.report):
        ap.error("one of --live / --offline / --report is required. This "
                 "script does not guess whether you meant to spend money.")

    objective_set = resolve_objective_set()
    locks = load_hash_locks(objective_set)
    seeds = CorpusSeeds.load()
    corpus_ids = {a.attack_id for a in seeds._attacks}
    existing = _load_existing()

    print("=" * 78)
    print("V0 ATTACK BASELINE")
    print("  training instances : %d" % len(corpus_ids))
    print("  episodes on disk   : %d" % len(existing))
    print("  covered            : %d" % len(corpus_ids & set(existing)))
    missing = sorted(corpus_ids - set(existing))
    orphaned = sorted(set(existing) - corpus_ids)
    print("  missing            : %d %s" % (len(missing), missing[:4] or ""))
    print("  orphaned           : %d %s" % (len(orphaned), orphaned[:4] or ""))
    print("  objective set      : %d clauses, hash %s"
          % (len(getattr(objective_set, "clauses", ()) or ()), objective_set.hash))

    if args.report:
        if FREEZE_RECORD.exists():
            rec = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
            print("  freeze record      : %s  baseline_hash %s  live=%s"
                  % (FREEZE_RECORD.relative_to(REPO), rec.get("baseline_hash"),
                     rec.get("recorded_live")))
            print("  by v0 verdict      : %s"
                  % rec.get("counts", {}).get("by_v0_verdict_at_record_time"))
            print("  cost               : %s" % rec.get("cost"))
        else:
            print("  freeze record      : ABSENT")
        return 0

    validator, _manifest_a, _derived_b = build_validator()
    policy = build_seed_policy(validator)
    base_manifest = RunManifest(
        policy_version=(policy.get("lineage") or {}).get("version", 0),
        policy_hash=compute_policy_hash(policy.get("hashed_payload") or {}),
        manifest_hash=locks.values["manifest_hash"],
        derived_schema_hash=locks.values["derived_schema_hash"],
        objective_set_hash=locks.values["objective_set_hash"])

    from target.refund_agent.agent import TARGET_MODEL, target_descriptor
    descriptor_before = json.dumps(target_descriptor(), sort_keys=True)

    sink = []
    if args.live:
        # The same assertion `campaign.py --live` makes before the first call.
        from target.refund_agent.agent import assert_provider_matches_descriptor
        assert_provider_matches_descriptor()
        model = _metered_model(sink)
        model_id = TARGET_MODEL
        target = build_real_target(run_manifest=base_manifest, model=model,
                                   world_factory=seeds.world_for)
    else:
        model_id = "OFFLINE_SCRIPTED"
        target = None  # built per attack below; the script is per instance

    todo = [a for a in seeds._attacks
            if (args.force or a.attack_id not in existing)
            and (not args.only or a.attack_id in args.only)]
    if args.limit:
        todo = todo[:args.limit]
    print("  to record          : %d  (%s)"
          % (len(todo), "LIVE" if args.live else "OFFLINE - NOT EVIDENCE"))
    print("=" * 78)

    started = _utc()
    t0 = time.monotonic()
    for i, rec in enumerate(todo, 1):
        if args.live:
            tgt = target
        else:
            script = seeds.offline_script(rec.attack_id)
            tgt = build_real_target(run_manifest=base_manifest,
                                    model=build_offline_target_model(script),
                                    world_factory=seeds.world_for)
        episode, verdict = record_one(rec, tgt, policy, objective_set,
                                      args.live, model_id)
        payload = _episode_payload(rec, episode, args.live, model_id,
                                   _utc(), verdict)
        _write_json(EPISODES_DIR / ("%s.json" % rec.attack_id), payload)
        existing[rec.attack_id] = payload
        print("  %3d/%-3d  %-52s %-8s events=%-3d %s"
              % (i, len(todo), rec.slug[:52], verdict,
                 len(episode.get("events") or []),
                 "FAULT" if episode.get("outcome") == TARGET_FAULT_OUTCOME else ""))
    finished = _utc()

    descriptor_after = json.dumps(target_descriptor(), sort_keys=True)
    if descriptor_before != descriptor_after:
        raise SystemExit(
            "E_TARGET_DESCRIPTOR_MOVED: the frozen target descriptor changed "
            "during recording. Nothing here may be used - the episodes were not "
            "all driven against the same agent.")

    prior_cost = None
    if FREEZE_RECORD.exists() and not args.force:
        prior_cost = (json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
                      .get("cost"))
    cost = _spend(sink, model_id, prior_cost) if args.live else {
        "model": model_id, "priced": False, "calls": 0,
        "usd": None,
        "_usd_note": "OFFLINE. No model was called and no cost exists.",
    }

    record = build_freeze_record(existing, locks, base_manifest, cost,
                                 args.live, model_id, started, finished,
                                 corpus_ids)
    _write_json(FREEZE_RECORD, record)

    print("=" * 78)
    print("  wall clock         : %.1fs" % (time.monotonic() - t0))
    print("  episodes on disk   : %d of %d instances"
          % (len(existing), len(corpus_ids)))
    print("  by v0 verdict      : %s"
          % record["counts"]["by_v0_verdict_at_record_time"])
    print("  baseline_hash      : %s   (owner: %s)"
          % (record["baseline_hash"], FREEZE_RECORD.relative_to(REPO)))
    print("  cost               : %s" % json.dumps(cost))
    print("  METHOD LIMIT       : single-sample, k=1, no stability estimate. "
          "One draw per instance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
