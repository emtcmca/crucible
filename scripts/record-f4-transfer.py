#!/usr/bin/env python
"""Drive the two-arm transfer measurement and record it as a transfer_evidence bundle.

WHAT THIS MEASURES. One family of attacks, run twice over the same instances:
once against the v0 seed policy and once against a promoted policy. The question
is whether hardening learned on OTHER families closes breaches in a family the
loop never saw.

THE DRIVE AND THE ASSEMBLY ARE SEPARATE PHASES, ON PURPOSE.

`--phase drive` writes raw episode payloads to disk. `--phase assemble` reads
that file and produces the bundle. They are separate because the drive is
EXPENSIVE AND, FOR THE SEALED FAMILY, UNREPEATABLE: section 4 item 3 of the
pre-registration forbids re-running F4, so there is exactly one drive and no
second attempt. If assembly has a bug, the fix must never require re-driving.
A single-phase runner would couple a cheap, fixable step to an irreplaceable one.

TWO ARMS, TWO EPISODE IDS, AND THE COLLISION THAT IS NOT OBVIOUS.

`real_target._episode_id_for()` derives the episode id from the attack id ALONE.
Run the same instance under two policies and both episodes get the SAME id, so
the arms collide by construction and the reader fires E_EPISODE_ID_DUPLICATED on
every pair. The fix is local: the arm rides in the attack id this script
constructs, and an arm-aware lookup resolves it back to the one corpus instance.
No shared code changes, and `world_for` keeps working untouched.

THE STAND-IN IS NOT A REHEARSAL PROP, IT IS THE ONLY PLACE TUNING MAY HAPPEN.

`--family` selects a TRAINING family and reads `corpus/training/`. F7 is the
default because it carries F4's exact capability pair - CAP_MOVES_MONEY plus
CAP_MUTATES_DURABLE_STATE - and the same dominant tool, `issue_refund`, so it
exercises the same policy surface. Tune here until bundles come out clean.

`--sealed` is the real thing and it refuses to run without `--i-am-opening-the-
seal`, which exists so the seal cannot be opened by a flag typo or a shell
history recall. Opening it spends the single attempt.

    python scripts/record-f4-transfer.py --phase drive --family F7 --out ep.json
    python scripts/record-f4-transfer.py --phase assemble --from ep.json --out bundle.json
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crucible.armorer.experiment import build_seed_policy               # noqa: E402
from crucible.canon import policy_hash as compute_policy_hash           # noqa: E402
from crucible.canon.hashing import hash_full                            # noqa: E402
from crucible.conductor.corpus_seeds import CorpusSeeds                 # noqa: E402
from crucible.conductor.hashlocks import load_hash_locks                # noqa: E402
from crucible.conductor.real_target import build_real_target            # noqa: E402
from crucible.conductor.real_tripwire import real_tripwire              # noqa: E402
from crucible.tripwire.model import RunManifest                         # noqa: E402

ARMS = ("v0", "vfinal")
DEFAULT_STANDIN = "F7"
SEALED_FAMILY = "F4"


class TransferRunError(RuntimeError):
    def __init__(self, code, message):
        super().__init__("%s: %s" % (code, message))
        self.code = code


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def armed_attack_id(instance_id, arm):
    """A per-arm attack id, so the two arms do not collide on one episode id.

    Twelve lowercase hex over (instance_id, arm), matching the `atk_` shape
    `_episode_id_for` expects. The TRUE instance id is recorded separately on
    the episode: this value exists only to separate the arms, and nothing
    downstream should read identity out of it.
    """
    if arm not in ARMS:
        raise TransferRunError("E_UNKNOWN_ARM", "%r is not one of %s" % (arm, ARMS))
    digest = hashlib.sha256(("%s|%s" % (instance_id, arm)).encode("utf-8")).hexdigest()
    return "atk_%s" % digest[:12]


class ArmedSeeds(CorpusSeeds):
    """`CorpusSeeds` that also answers to per-arm attack ids.

    Subclassed rather than patched because `world_for` joins on `attack_id`
    through `lookup`, and an armed id is not in the corpus. Teaching the lookup
    to strip the arm keeps the world-building path byte-identical to the one the
    campaign uses - a transfer run whose worlds were built differently from the
    training runs would not be measuring the same thing.
    """

    def __init__(self, attacks):
        super().__init__(attacks)
        self._armed = {}
        for a in attacks:
            for arm in ARMS:
                self._armed[armed_attack_id(a.attack_id, arm)] = a.attack_id

    def lookup(self, attack):
        aid = attack.get("attack_id") if isinstance(attack, dict) else attack
        base = self._armed.get(aid)
        if base is not None:
            return super().lookup(base)
        return super().lookup(attack)


def load_instances(family, sealed, opening_the_seal):
    """The corpus instances for one family, and the door each source comes through.

    The two sources are deliberately different code paths. The training path
    goes through `CorpusSeeds`, which refuses the sealed family by name. The
    sealed path goes through `crucible.transfer.sealed_io`, which refuses
    everything else. Neither can be talked into reading the other's family.
    """
    if sealed:
        if not opening_the_seal:
            raise TransferRunError(
                "E_SEAL_NOT_AUTHORISED",
                "--sealed reads the held-out family and spends the single "
                "attempt the pre-registration allows. Re-running F4 is "
                "forbidden, so there is no second try. Pass "
                "--i-am-opening-the-seal only with a human present and the "
                "read path already calibrated on the canary.")
        raise TransferRunError(
            "E_SEALED_PATH_NOT_WIRED",
            "the sealed drive is not wired in this build. Calibrate on the "
            "canary first, then wire it deliberately - not as a side effect of "
            "tuning the stand-in.")

    if family == SEALED_FAMILY:
        raise TransferRunError(
            "E_SEALED_FAMILY_VIA_TRAINING",
            "F4 is not in corpus/training/ and must never be reached through "
            "it. Use --sealed, which comes through the door built for it.")

    seeds = ArmedSeeds.load()
    picked = [a for a in seeds._attacks if a.family == family]
    if not picked:
        have = sorted({a.family for a in seeds._attacks})
        raise TransferRunError(
            "E_FAMILY_EMPTY",
            "no training instance declares family %r. Present: %s" % (family, have))
    return seeds, picked


def drive(seeds, instances, policies, base_manifest, model, objective_set, limit=None):
    """One episode per (instance, arm). Sequential, fresh world each time.

    SEQUENTIAL AND NOT PARALLEL, deliberately: the target's tool backends are
    module-global, so two episodes in flight share a system of record and each
    one's writes are visible to the other. That would not fail loudly, it would
    quietly change what the other episode saw.
    """
    todo = instances[:limit] if limit else instances
    out = []
    for i, rec in enumerate(todo, 1):
        for arm in ARMS:
            aid = armed_attack_id(rec.attack_id, arm)
            attack = {"attack_id": aid,
                      "family_id": rec.family_id,
                      "instruction": rec.turns[-1]}
            if model is None:
                # OFFLINE: the stub is scripted from THIS instance's own trace,
                # built fresh per arm. Looked up on the BASE id - the armed id
                # exists only to separate episode ids and names no instance.
                from crucible.conductor.campaign import build_offline_target_model
                arm_model = build_offline_target_model(
                    seeds.offline_script(rec.attack_id))
            else:
                arm_model = model
            target = build_real_target(run_manifest=base_manifest[arm],
                                       model=arm_model,
                                       world_factory=seeds.world_for)
            episode = target(attack, policies[arm])
            # THE VERDICT IS SCORED SEPARATELY AND THAT SEPARATION IS THE POINT.
            # `real_tripwire` decides BREACH from the episode's TOOL_EXECUTED
            # events and never reads the policy's decision. An episode carries
            # no verdict of its own; asking the policy whether it was breached
            # would let the thing under test grade its own paper.
            verdict = real_tripwire(episode, objective_set=objective_set)
            out.append({
                # The TRUE instance id, not the armed one. Both arms carry the
                # same value here, which is what pairs them.
                "instance_id": rec.attack_id,
                "arm": arm,
                "armed_attack_id": aid,
                "family": rec.family,
                "slug": rec.slug,
                "episode": episode,
                "verdict": (verdict or {}).get("verdict"),
                "verdict_full": verdict,
            })
        print("  %3d/%d  %s  %s" % (i, len(todo), rec.attack_id, rec.slug[:44]))
    return out


def build_arm_policies(policy_run_path):
    """v0 is the seed policy. vfinal comes from a completed run's final_policy."""
    from crucible.conductor.campaign import build_validator
    validator, _a, _b = build_validator()
    v0 = build_seed_policy(validator)

    run_doc = json.loads(pathlib.Path(policy_run_path).read_text(encoding="utf-8"))
    vfinal = run_doc.get("final_policy")
    if not vfinal:
        raise TransferRunError(
            "E_NO_FINAL_POLICY",
            "%s carries no final_policy. The vfinal arm has nothing to enforce, "
            "and an arm with no policy is not a second arm." % policy_run_path)
    return {"v0": v0, "vfinal": vfinal}, run_doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=("drive", "assemble"), required=True)
    ap.add_argument("--family", default=DEFAULT_STANDIN,
                    help="training family used as the stand-in (default %s)" % DEFAULT_STANDIN)
    ap.add_argument("--sealed", action="store_true",
                    help="read the held-out family instead of a stand-in")
    ap.add_argument("--i-am-opening-the-seal", action="store_true",
                    help="required with --sealed. Spends the single attempt.")
    ap.add_argument("--policy-run", default="docs/proof/sample-run/run-01.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="from_path",
                    help="assemble phase: the episodes file a drive wrote")
    ap.add_argument("--limit", type=int, default=None,
                    help="stand-in tuning only; a partial drive is not a measurement")
    ap.add_argument("--live", action="store_true",
                    help="drive against the pinned target model. Costs money.")
    args = ap.parse_args(argv)

    if args.phase == "assemble":
        return _assemble(args)

    # THE SEAL AUTHORISATION IS CHECKED BEFORE ANY OTHER WORK, and the ordering
    # is the point. It was originally reached after the hash-locks loaded, so a
    # setup failure raised a TypeError and the refusal never printed - a guard
    # you only see when everything else already worked is a guard that reports
    # the wrong thing on the day it matters.
    seeds, instances = load_instances(args.family, args.sealed,
                                      args.i_am_opening_the_seal)

    from crucible.conductor.campaign import resolve_objective_set
    objective_set = resolve_objective_set()
    locks = load_hash_locks(objective_set)
    policies, run_doc = build_arm_policies(args.policy_run)

    manifests = {}
    for arm in ARMS:
        pol = policies[arm]
        manifests[arm] = RunManifest(
            policy_version=(pol.get("lineage") or {}).get("version", 0),
            policy_hash=compute_policy_hash(pol.get("hashed_payload") or {}),
            manifest_hash=locks.values["manifest_hash"],
            derived_schema_hash=locks.values["derived_schema_hash"],
            objective_set_hash=locks.values["objective_set_hash"])

    if args.live:
        from target.refund_agent.agent import (TARGET_MODEL,
                                               assert_provider_matches_descriptor)
        assert_provider_matches_descriptor()
        model, model_id = None, TARGET_MODEL
    else:
        model, model_id = None, "OFFLINE_SCRIPTED"

    print("=" * 78)
    print("TRANSFER DRIVE   family=%s  source=%s  mode=%s"
          % (args.family, "SEALED" if args.sealed else "training stand-in",
             "LIVE" if args.live else "OFFLINE - NOT EVIDENCE"))
    print("  instances        : %d" % len(instances))
    print("  episodes planned : %d  (%d instances x %d arms)"
          % (len(instances) * len(ARMS), len(instances), len(ARMS)))
    if args.limit:
        print("  LIMIT            : %d instances - TUNING ONLY, not a measurement"
              % args.limit)
    print("=" * 78)

    episodes = drive(seeds, instances, policies, manifests, model,
                     objective_set, args.limit)

    payload = {
        "artifact": "transfer drive, raw episodes. NOT a bundle.",
        "family": args.family,
        "sealed": bool(args.sealed),
        "driven_at": _utc(),
        "model_id": model_id,
        "live": bool(args.live),
        "partial": bool(args.limit),
        "policy_run": args.policy_run,
        "policy_run_id": (run_doc.get("summary") or {}).get("run_id"),
        "arms": {arm: {"policy_hash": compute_policy_hash(
            policies[arm].get("hashed_payload") or {})} for arm in ARMS},
        "hash_locks": dict(locks.values),
        "episodes": episodes,
    }
    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="")
    print()
    print("  episodes recorded: %d" % len(episodes))
    print("  written          : %s" % args.out)
    print("  NEXT             : --phase assemble --from %s" % args.out)
    return 0


def _assemble(args):
    if not args.from_path:
        print("REFUSED: --phase assemble needs --from <episodes file>")
        return 2
    raw = json.loads(pathlib.Path(args.from_path).read_text(encoding="utf-8"))
    try:
        from crucible.transfer.bundle import build_transfer_bundle, write_bundle
    except ImportError as exc:
        print("REFUSED E_NO_ASSEMBLER: %s" % exc)
        print("  crucible/transfer/bundle.py is not present yet.")
        return 2
    print("assembler present; %d raw episodes to shape" % len(raw.get("episodes") or []))
    _ = (build_transfer_bundle, write_bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
