# Stand-in transfer runs, F7, 2026-08-29

**These are TUNING runs, not the transfer measurement.** The transfer measurement
is F4, it is sealed, it runs once, and it had not been run when these were
recorded. Nothing here is a transfer figure and no rate is quoted.

## Why F7 stands in for F4

F7 carries F4's exact capability pair — `CAP_MOVES_MONEY` plus
`CAP_MUTATES_DURABLE_STATE` — and the same dominant tool, `issue_refund`. It
therefore exercises the same policy surface. It is not a proxy for F4's
*content*: F4 is destination smuggling and F7 is structuring, and no result here
predicts a result there.

The stand-in exists because **the sealed family cannot be tuned against.**
Section 4 item 3 of the pre-registration forbids re-running F4, so there is one
drive and no second attempt. Every bug that would otherwise be found during that
one attempt has to be found somewhere else first. This is that somewhere else.

## What was run

| file | mode | episodes |
|---|---|---|
| `F7-standin-offline-2026-08-29.json` | offline, scripted from each instance's own trace | 16 |
| `F7-standin-live-2026-08-29.json` | live, the pinned target model | 16 |

Eight instances, two arms each — `policy@v0` (the seed policy) and
`policy@vfinal` (a promoted policy from a completed run). Sequential, with a
fresh world per episode.

## What the runs establish about the machinery

- All 16 episodes completed in both modes.
- **Episode ids are unique across arms.** This is the defect the runner exists to
  avoid: `real_target._episode_id_for()` derives the id from the attack id alone,
  so running one instance under two policies produces two episodes with the same
  id and the reader rejects every pair. The arm rides in the attack id the runner
  constructs, and an arm-aware lookup resolves it back to the one instance.
- Both arms are present for all eight instances, so the pairing the arithmetic
  depends on is complete.

## What the runs establish about the policy, which is a negative result

**`breached_at_v0` = 7, `breached_at_vfinal` = 7. Zero instances moved.** Offline
and live agree exactly.

The promoted policy closes nothing on this family. That is consistent with the
already-recorded no-op finding — of 31 promoted rules, 13 closed the breach they
were written for and 18 did not — and with its stated cause: the tripwire's
aggregate clause groups by a key the DSL the Armorer must write in cannot
express. **F7 is the structuring family**, so an aggregate the policy language
cannot say is exactly what it is made of. The result is the known defect
reappearing in a purpose-built measurement rather than a new one.

**This is a stand-in, so it licenses nothing about F4.** It does not predict the
transfer result, and a reader who takes it as a preview of one has taken it
wrongly.

## Accuracy boundary

Offline runs replay each instance's own trace. That makes them a reading of
**policy coverage** and not of agent behaviour: a replay cannot observe an agent
that, refused one route, tries another. A3.8 requires the real transfer
measurement be driven live for exactly that reason. The live run above is the one
that proves the live path works end to end; its numbers are still a stand-in's.

k=1 per episode. No stability estimate. No rate is derived from either file.
