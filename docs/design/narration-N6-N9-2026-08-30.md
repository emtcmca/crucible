# RECORDING SCRIPT — N6 to N9

**Written 2026-08-30, to be read after `narration-LOCKED-2026-08-27.md` N1–N5.**
Same recording rules: one take per chunk, two seconds of silence head and tail,
sixty seconds of room tone before you start.

**These four beats replace the blocked N6–N9.** The old N6–N8 were gated on
figures that had no settled scope, and the old N9 was gated on the unseal. The
seal is NOT opened and this script does not depend on it. **Nothing here needs
the holdout.**

## The figures ruling this script is written against

**Option 2 from `docs/contest/DECISION-figures-2026-08-30.md`**, narrowed to the
pooled figure. One number, one denominator, one caveat, and the replication
disagreement travels in the same breath.

**Re-verified from source 2026-08-30 before this file was written:**

| claim | verified against |
|---|---|
| 20 runs, reader ACCEPTS 20 of 20, zero REJECTS, zero exit/verdict contradictions, all exits 0 | `evidence/batch-measure-2026-08-27/BATCH-DONE` |
| the same, independently, in the replication | `evidence/batch-replicate-2026-08-27/BATCH-DONE` |
| pooled 70/520 = 13.5% → 56/725 = 7.7%; measurement 33/280 → 21/366; replication 37/240 → 35/359 | `docs/design/where-we-stand-2026-08-27.md:189-193` |
| 32 rules promoted, 13 CLOSES, 19 NO_OP, over 15 accepted bundles | `AUDIT.md` C13, `README.md:95-106` |
| Cloud Run `crucible` serving, revision `crucible-00004-gfk`, SA `crucible-target` | `gcloud run services describe`, read 2026-08-30 |

**Re-verify before recording. Do not recall.** Three typed counts in this repo
have been wrong.

**Do NOT say** the conditional rate (`13.3% → 3.2%`). It was computed mid-batch
at 15 of 20 and has no completed-batch replacement. It is the one figure in the
inventory being dropped rather than restated.

---

## N6 · ~0:25 · it ran, and it ran on Google Cloud

**ON SCREEN:** terminal. Run these two live — they are read-only and fast:

```
gcloud run services list --project=crucible-hack-2026 --region=us-central1
cat evidence/batch-measure-2026-08-27/BATCH-DONE
```

Then the Cloud Console on the `crucible` service, so a revision id and the
service account are on screen.

**SAY:**

```
The loop runs on Vertex, deployed to Cloud Run, under its own service account.

Two batches. Twenty runs each, identical configuration, one of them
pre-registered as a replication of the other before it ran.

The offline reader accepts twenty of twenty bundles in both.
```

*(beat)*

```
That reader takes no credentials and no cloud project. It re-derives every
frozen lock from the bundle bytes. You can run it against these bundles on your
own machine.
```

---

## N7 · ~0:30 · the efficacy figure, with its disagreement attached

**ON SCREEN:** the pooled table from `where-we-stand-2026-08-27.md:189-193`, all
three rows visible at once. **Do not crop to the pooled row.**

**SAY:**

```
Pooled across both batches, attack success falls from thirteen and a half
percent against the bare agent to seven point seven at the final policy.
Seventy breaches in five hundred and twenty episodes, down to fifty six in
seven hundred and twenty five.
```

*(beat — the two batch rows are on screen)*

```
And the two batches disagree. One ran eleven point eight down to five point
seven. The other ran fifteen point four down to nine point seven.

A replication that contradicts the first batch does not retire the first batch.
It retires the claim that one batch was enough.

One target agent. One sample per episode. No stability estimate.
```

---

## N8 · ~0:35 · the finding that is negative, and is the point

**ON SCREEN:** `README.md:95-106` on screen, or the gate-noop measurement table.

**SAY:**

```
The most substantive thing this project measured is negative, and it is about
the harness rather than about the agent.

Thirty two rules were promoted across the bundles the reader accepts. Thirteen
of them closed the breach they were written for. Nineteen were no-ops on it.
```

*(beat)*

```
The gate promoted every one of those nineteen, because it checked that the
patch was well formed and that benign traffic survived it. It never checked
that the patch closed the breach it was written for.

And a rule that over-blocks passes every gate. It stops the attacks, the
approval oracle rubber-stamps the benign cases, benign pass rate reads perfect,
the gate promotes it — and the agent has been made useless.

That is a measurement finding, not an agent finding. It is the one I would
expect to transfer.
```

*(beat)*

```
We found it by recounting a number that had already been published. It got
worse: fifty eight point one percent to fifty nine point four. A recount that
only ever runs when the number would improve is not a check.
```

---

## N9 · ~0:20 · what this is not, and the close

**ON SCREEN:** the README's *"what is not defensible today"* section.

**SAY:**

```
What this is not.

Eleven days, one person, one target agent. No users. Not reviewed or endorsed
by Google. A held-out attack family exists and is still sealed — the sealed
measurement has not been run, and I am not going to describe a result I do not
have.
```

*(beat)*

```
The repository says all of that on its own front page, in a section called
what is not defensible today.

The thing I would want you to take from this is the shape. Every boundary in
here is a component deliberately blind to something. The coroner cannot propose
a fix. The armorer has no allow verb. The gate reads the bytes back off disk
before it promotes.

None of that is a prompt. It is a schema, an IAM policy, and a grammar.
```

---

## STOP

Do not improvise a result from the sealed family. It has not been run.

**If the seal is opened later and this video is already recorded, the video does
not change** — nothing in N1–N9 claims a sealed result, and that was the point
of writing it this way.
