# Stand-in transfer runs, F7, 2026-08-29

## WITHDRAWN: the "live" run in this directory was never live

**Two files were removed from this directory on 2026-08-29:**
`F7-standin-live-2026-08-29.json` and `F7-standin-bundle-live-2026-08-29.json`.
They claimed `live: true`, named the pinned target model, and labelled every
episode `provider: vertex`. **No model was called.**

The cause was a sentinel collision in `scripts/record-f4-transfer.py`.
`build_real_target(model=None)` means *"use the pinned live default"*, and the
runner also used `None` to mean *"build the offline scripted stub"*. Both
branches therefore set `model = None`, and `drive()` read that as the offline
instruction. `--live` executed the scripted replay while the record asserted
otherwise. The model id in the artifact came from a constant, not from an
observed call.

**This was found by an independent adversarial review, not by us**, and it is the
exact failure this repository catalogues: a postcondition asserted rather than
checked. The one check that would have caught it in five seconds - is there any
token count, any latency, any model-call telemetry - is the check nobody ran.

The artifacts are deleted rather than kept with a correction note. A dated
snapshot that was *true when written* gets struck and amended; this one was never
true, and a false evidence file in `docs/proof/` is worse than an absent one.
Neither file was ever pushed, so nothing public carried the claim.

Fixed by an explicit `OFFLINE_STUB` sentinel, with two regression tests that
assert the fact rather than the prose: the offline builder is unreachable in live
mode, and it IS reached in offline mode. Both were mutation-checked against a
deliberately reverted implementation.

**A genuine live stand-in will be recorded after the review's remaining findings
are closed, and this section stays here when it is.**

---

## What F7 stands in for, and what it does not

F7 carries F4's exact capability pair, `CAP_MOVES_MONEY` plus
`CAP_MUTATES_DURABLE_STATE`, and the same dominant tool, `issue_refund`. It
exercises the same policy surface. It is **not** a proxy for F4's content: F4 is
destination smuggling, F7 is structuring, and no result here predicts one there.

The stand-in exists because **the sealed family cannot be tuned against.** There
is one drive and no second attempt, so every bug that would otherwise surface
during that attempt has to be found somewhere else first. This is that somewhere
else, and it has now earned its keep twice over.

## What remains in this directory

| file | what it is | episodes |
|---|---|---|
| `F7-standin-offline-2026-08-29.json` | drive output, offline, scripted from each instance's own trace | 16 |

Eight instances, two arms each, `policy@v0` and `policy@vfinal`, sequential with
a fresh world per episode.

**What it establishes about the machinery:** all 16 episodes completed; episode
ids are unique across arms, which is the collision the runner exists to avoid
because `_episode_id_for()` derives from the attack id alone; and both arms are
present for all eight instances, so the pairing the arithmetic depends on is
complete.

**What it reads as a policy-coverage observation:** `breached_at_v0` and
`breached_at_vfinal` were equal, and no instance moved between arms. That is
consistent with the recorded no-op finding, whose stated cause is that the
tripwire's aggregate clause groups by a key the Armorer's DSL cannot express -
and F7 is the structuring family, so an aggregate the policy language cannot say
is exactly what it is made of.

**How far that goes.** The offline stub replays each instance's authored trace,
so the target always attempts the same calls and only the policy decides whether
they execute. That makes this a reading of policy coverage and **not** of agent
behaviour: a replay cannot observe an agent that, refused one route, tries
another. A3.8 requires the real transfer measurement be driven live for exactly
that reason.

## Accuracy boundary

k=1 per episode. No stability estimate. No rate is derived from this file, and
`breached_at_v0` here sits under the pre-registered floor of 12, which for F4
would be Outcome E: two raw counts, the floor, and no rate.

**Nothing in this directory is a transfer figure.**
