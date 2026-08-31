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

## N6a · ~0:20 · LIVE TERMINAL · the Google Cloud proof

**SHOOT THIS LIVE. Do not use a card for it.** It is the contest's *"visible
proof your backend runs on Google Cloud"*, and a live terminal is the only
unambiguous form of that. Everything the script runs is read-only.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\gcp-proof.ps1 -Pause 2.0
```

**Set the terminal to 1920x1080 and the font to 18–20pt before you roll.**
Default console text is illegible after YouTube's compression, and a proof
nobody can read is not a proof. Run `gcloud auth list` first, off camera, so an
auth prompt cannot land inside the take.

The script types each command for the camera and shows its real output, in four
frames: Cloud Run serving under its own service account · the enabled APIs ·
the three buckets including the sealed one · Gemma's pin and a live-run
artifact returning **http 200** against Vertex Model Garden.

**SAY, over the four frames:**

```
Cloud Run, serving, under its own service account - not the default one. The
whole design rests on identities that differ from each other.

Vertex AI, where every model call in the loop goes.

Three buckets. Evidence, policies, and the sealed holdout - which is listed
here and which the attacking identity cannot read.
```

*(the Gemma frames land)*

```
And Gemma, on Vertex Model Garden, as a managed endpoint. It is the capability
cartographer: it classifies every tool the target agent holds into a capability
class, before any attack runs.
```

**GEMMA'S SCOPE, AND IT IS NARROW.** Classification. That is the whole claim.
`ADR-0018` withdrew the claim that Gemma generated the attack corpus and says
that sentence *"may not be written or spoken anywhere"* — the corpus was
authored by lane agents. **Do not widen it on camera.**

**The Cloud Run URL appears on screen and that is fine.** It is already public
in six tracked files, and the service holds zero IAM bindings, so it is not a
spend risk (`docs/contest/AUDIT-stage-one-2026-08-30.md`, Row 8).

---

## N6b · ~0:18 · what that infrastructure produced

**ON SCREEN:** the run view — `tools/capture/cards/03-run.html`, a real bundle
replayed. Or the terminal again for `cat evidence/batch-measure-2026-08-27/BATCH-DONE`.

**SAY:**

```
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

**STATE CHECK BEFORE THE TAKE — the line below is true as of 2026-08-30 and it
is a claim about machine state, so it expires.** Re-verify the seal is unopened
immediately before recording:

```
python scripts/pre-read-seal-proof.py     # must print VERDICT PASS
```

If the seal has been opened between now and the take, **this beat is rewritten,
not re-read**. That is why the date is here rather than in the spoken line: a
sentence Eric says aloud cannot carry a verification stamp, so the stamp sits
next to it where the person holding the script will see it.

**SAY:**

```
What this is not.

Eleven days, one person, one target agent. No users. Not reviewed or endorsed
by Google. A held-out attack family exists and is still sealed. I am not going
to describe a result I do not have.
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
