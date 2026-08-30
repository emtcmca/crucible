# DECISION NEEDED — the efficacy figures, and the scope of the no-rate rule

**Written 2026-08-30. Nothing was edited to produce it.** Every file named below
is quoted as it stood on 2026-08-30; not one of them was changed by this pass, on
purpose. Applying a partial fix now would create a fifth state, and the whole
point is that one decision gets applied to all of them at once.

**What this needs from Eric: one choice from section 4.** Section 5 turns each
choice into a mechanical edit list so the follow-up is typing, not another
investigation.

---

## 1. The inventory

Nine figures, quoted exactly, read out of the files on 2026-08-30. The four the
eligibility audit found are rows 1 to 5; rows 6 to 9 were found by sweeping
`docs/devpost/`, `docs/contest/`, `RESULTS.md`, `README.md`, `AUDIT.md` and the
design document those four all descend from.

### Row 1 — `13.3% → 3.2%`

`docs/devpost/the-contribution.md:118-119`

> **The efficacy number, with its limits attached.** Where a rule shipped, attack
> success fell from 13.3% to 3.2%.

**What it purports to describe.** Attack success at v0 versus at the final
policy, **conditional on the run having promoted at least one rule** — not the
whole batch. Its source is `docs/design/where-we-stand-2026-08-27.md:57`:

> | runs that promoted at least one rule | 7 | 12/90 = **13.3%** | 4/126 = **3.2%** |

**Population.** 7 runs of `evidence/batch-measure-2026-08-27`, read while the
batch was still writing. Denominators 90 and 126 episodes. The document carrying
those denominators says of itself, at line 3, *"provisional until the batch
completes"*, and at line 148, *"15 of 20 runs at the time of writing."*

### Row 2 — `11.3%` v0, in the same paragraph as row 1

`docs/devpost/the-contribution.md:120`

> The pre-registered v0 target was 68% and the observed v0 rate is **11.3%**

**What it purports to describe.** v0 attack success over the **whole**
measurement batch. Same mid-batch read. Source: `where-we-stand-2026-08-27.md:24`
and `:78`.

### Row 3 — `11.3% → 6.2%`

`docs/contest/SCOPE-LOCK.md:39`

> "attack success fell from 11.3% to 6.2% on one agent, single-sample" — true,
> small, and indistinguishable from every other entry claiming an improvement.

**What it purports to describe.** v0 to vFinal over the whole measurement batch.
Source: `where-we-stand-2026-08-27.md:24`, the same mid-batch read.

### Row 4 — `13.5% → 7.7%` pooled, `11.8 → 5.7` and `15.4 → 9.7` per batch

`docs/devpost/story-amendment-2026-08-28-prepared.md:107-112`

> Attack success, any-of-1, **k=1 per episode**, TARGET_FAULT episodes excluded:
> pooled **13.5 percent at v0 falling to 7.7 percent at the final policy**, and
> the two batches do not agree. The measurement batch ran 11.8 to 5.7. The
> replication ran 15.4 to 9.7.

Same figures, with denominators, at `where-we-stand-2026-08-27.md:191-193`:

> | **pooled** | 70/520 = **13.5%** | 56/725 = **7.7%** |
> | measurement batch | 33/280 = **11.8%** | 21/366 = **5.7%** |
> | replication batch | 37/240 = **15.4%** | 35/359 = **9.7%** |

**Population.** Both 2026-08-27 batches, completed at 20 runs each, reader
accepting 20 of 20 bundles in each. Verified 2026-08-28 by two independent
derivations from the C6 episodes.

### Row 5 — `16.2% → 0.0%`

`RESULTS.md:188`

> | ASR, training slice (any-of-1, single-sample, no stability estimate) | 34/50
> | 3/50 | **[14] v0 = 13/80 = 16.2%** · **final round = 0/82 = 0.0%** · pooled
> over all rounds 20/358 = 5.6% · any-of-1, k=1 · SEP-BY 294 / 42 · *[60] counts
> only: 50 breaches in 325 scorable at v0, 0 in 344 at the final round* |

**Population.** The **training slice** of the sixty-run batch of 2026-08-25, over
the `[14]` sub-population. Different batch, different slice, and a corpus that
was re-frozen afterwards. It sits under this document's own banner at
`RESULTS.md:8`.

### Row 6 — `8 of 50`

`docs/devpost/SCORECARD-DRAFT.md:62`

> | agent with **no rules at all** | **8 of 50** |

**What it purports to describe.** The frozen 50-episode offline baseline: how
many attacks succeed against the target with no policy. A count, not a rate, and
described at `:51` as *"the only ASR figure on this page."*

### Row 7 — `58.1% to 59.4%` — **not an attack-success figure**

`README.md:100` and `AUDIT.md:60`

> which took the finding from 58.1% to 59.4%, i.e. it got *worse*

**What it purports to describe.** The **no-op rate of promoted rules** — the
recount from `~~"18 of 31 promoted rules closed nothing"~~` to 19 of 32,
recorded in `AUDIT.md` row C13. It is listed here only so it is not mistaken for
a fifth efficacy rate. It measures a different thing entirely and contradicts
nothing.

### Row 8 — `9.6%`, superseded by `18.3%` in its own document

`where-we-stand-2026-08-27.md:59` reads *"11/114 = **9.6%**"*; the amendment at
`:199-201` supersedes it: *"**The correct figure is 11/60 = 18.3%**, over the 4
runs in that group."* Adjacent to row 1 in the same table, so anyone who lifts
row 1 out of that table can lift this one too.

### Row 9 — withdrawn, and correctly

`AUDIT.md:58` row C14 withdraws *"attack success falls from 8 of 50 to a median
of 2.5 across ten runs"* in full. No live file quotes it. Recorded so the sweep
is complete.

---

## 2. Which of these are the same experiment

**Group A — the 2026-08-27 measurement batch and its replication.** Rows 1, 2, 3
and 4 all come from here. Rows 1, 2 and 3 are mid-batch reads at 15 of 20 runs;
row 4 is the completed read at 20 of 20 in each of two batches.

- **Rows 3 and 4 are the same experiment reported twice, and one is wrong.**
  `11.3% → 6.2%` and `11.8% → 5.7%` are the same quantity over the same
  measurement batch: whole-batch v0 to vFinal. The first was computed at 15 of 20
  runs. The project has already adjudicated this — `where-we-stand-2026-08-27.md:195`
  says *"This supersedes the pair in §1 and §3, which read ~~v0 11.3% → final
  6.2%~~"*, and `story-amendment-2026-08-28-prepared.md:116-119` says the figure
  *"was computed over the measurement batch at 15 of 20 runs, while it was still
  writing, and is superseded."* **The adjudication exists. It is simply not
  marked at `SCOPE-LOCK.md:39`, which is where a judge would read it.**
- **Row 2 is the same defect as row 3, one number narrower.** `the-contribution.md:120`
  states the v0 rate as `11.3%`; the completed measurement batch reads `11.8%`
  and the pooled figure across both batches reads `13.5%`.
- **Row 1 is NOT a contradiction of row 4. It is a different statistic that has
  not been recomputed.** `13.3% → 3.2%` is conditional on the run having promoted
  a rule (7 runs, 90 and 126 episodes); `13.5% → 7.7%` is unconditional across
  both completed batches (520 and 725 episodes). Two different denominators
  answering two different questions. **But row 1 comes from the same mid-batch
  snapshot as rows 2 and 3, and unlike them it has no completed-batch replacement
  anywhere in the tree.** Nothing has recomputed the conditional rate at 20 of 20,
  and no document says so.
- **The sharpest problem is inside one paragraph.** `the-contribution.md:118-122`
  puts `13.3%` and `11.3%` two sentences apart with no statement that they have
  different denominators. A judge reads two v0 rates that disagree by two points,
  in the file whose job is to explain the contribution.

**Group B — the sixty-run batch of 2026-08-25.** Row 5 only. A different
population on a corpus that no longer exists: `RESULTS.md:8-27` records that
ruling 55 made `episodes[].target_responded` a required property after those
bundles were written, so the shipped offline reader refuses all sixty, and that
the corpus was re-frozen when instance F5-05 was repaired. **This is not a
contradiction of Group A. It is a separate experiment that cannot be re-derived
from its own artifacts**, which is exactly what its banner says.

**Group C — the frozen offline baseline.** Row 6 only. A count over a fixed
50-episode set with no policy. Consistent with Group A rather than in tension
with it: 8 of 50 is 16%, and Group A's pooled v0 of 13.5% is the same agent
measured a different way, over episodes a live loop actually reached.

**Group D — not efficacy at all.** Rows 7 and 8.

### The bottom line

**Four "mutually contradictory headline figures" is, read at source, one
contradiction and one gap.**

| | |
|---|---|
| genuine contradiction, same experiment | **1** — row 3 (`11.3 → 6.2`) against row 4's measurement-batch pair (`11.8 → 5.7`). Already adjudicated in two places; unmarked where it is published |
| stale by the same mechanism, no replacement computed | **1** — row 1 (`13.3 → 3.2`), the conditional rate, never recomputed at 20 of 20 |
| genuinely different experiments that only look contradictory | **3** — rows 5, 6, 7 |
| already struck or withdrawn in place | **2** — rows 8, 9 |

**What makes them read as four contradictions is that no two of the four sites
state their denominator in the same words.** Row 4 carries `70/520` and
`56/725`; rows 1, 2 and 3 carry a bare percentage.

---

## 3. The two versions of the no-rate rule

Both are live on 2026-08-30 and different documents are obeying different ones.

### Version A — blanket

`docs/devpost/findings-and-learnings.md:21-25`, inside the file's header comment:

> The scope rule that replaces it is narrower and still binding: NO RATE may be
> stated -- no attack-success rate, no benign pass rate, no transfer figure, no
> convergence result -- and no figure from RESULTS.md may be quoted at all.

**What it permits.** The gate no-op measurement with its caveats, counts,
frozen parameters, corpus sizes, acceptance counts. **No percentage describing
efficacy anywhere, from any batch.** Under version A, rows 1 to 5 are all
unquotable.

### Version B — scoped to one batch

`RESULTS.md:8-10`:

> **No rate in this document may be quoted. This document is the record of the
> sixty-run batch of 2026-08-25, and the ban is on that batch — it is not a
> blanket prohibition on the repository.** Later batches are a different
> population and are governed by their own acceptance counts

`README.md:65-66` states the same scope in the same words: *"No rate in
[`RESULTS.md`](RESULTS.md) may be quoted. The ban names a batch, not this
repository."* Version B is stated twice, consistently.

**What it permits.** Any figure from the two 2026-08-27 batches, provided it
prints its reader-acceptance count. Under version B, rows 1 to 4 are quotable
and row 5 is not.

### Version C — scoped to one command, and not in conflict

`README.md:613-615` bans ASR, BPR, transfer and convergence numbers from the
offline demo command specifically. Recorded so the count of live rules is right;
it does not conflict with either version above.

### Who is obeying which, as of 2026-08-30

| Obeying version A (no efficacy rate appears) | Obeying version B (2026-08-27 figures quoted) |
|---|---|
| `docs/devpost/findings-and-learnings.md` body | `docs/devpost/the-contribution.md:118-122` |
| `docs/devpost/SCORECARD-DRAFT.md` — states the withdrawal in place of a number | `docs/contest/SCOPE-LOCK.md:39` |
| `docs/devpost/project-story.md` — its Results section still reads *"deliberately empty as of 2026-08-20"* on 2026-08-30, and the prepared amendment has not been appended to it | `docs/devpost/story-amendment-2026-08-28-prepared.md:107-112` (prepared, not yet applied) |
| the nine numbered Devpost updates — swept 2026-08-30, no efficacy percentage in any of them | `docs/design/where-we-stand-2026-08-27.md` |

**The split runs straight through `docs/devpost/`**, which is the directory a
judge reads as the submission text. `findings-and-learnings.md` says no rate may
be stated; `the-contribution.md`, two files over, states one.

---

## 4. The options

### Option 1 — quote nothing. Version A wins everywhere.

**Buys.** One rule, stated once, obeyed by every file. Nothing a judge can catch
disagreeing with itself. It is also the position the two most careful documents
in the tree already hold, so `findings-and-learnings.md` and `SCORECARD-DRAFT.md`
need no edit at all. The submission's argument does not depend on the number:
`SCOPE-LOCK.md:38-41` already rules the efficacy sentence *"our weakest strong
material"* and bars it from leading.

**Costs.** The project throws away its only completed, reader-accepted,
replicated measurement — the one artifact that answers *"does the loop actually
reduce attack success"*. A judge scoring **impact** may read total silence on
efficacy as having nothing to show, and the replication disagreement (four points
worse at both ends) is genuinely good evidence of intellectual honesty that goes
in the bin with it. Row 6's `8 of 50` would have to go too, or the rule is
already broken on the first page it appears on.

### Option 2 — quote one figure everywhere, with its caveat. Version B wins, narrowed.

The figure is row 4, always in this shape: **pooled 13.5% at v0 to 7.7% at the
final policy, across two batches at identical configuration, the reader accepting
20 of 20 bundles in each, the two batches disagreeing (11.8→5.7 and 15.4→9.7),
k=1 per episode, one target agent.**

**Buys.** One number, one denominator, one caveat block, in every file that
mentions efficacy. It is the strongest *defensible* version of the claim, and the
disagreement between batches is a credibility asset rather than a liability —
`story-amendment:120` already frames it as *"a replication that contradicts the
first batch does not retire the first batch, it retires the claim that one batch
was enough."* It is also the only option under which the prepared story amendment
can be appended at all, and that amendment is the one artifact whose wording was
committed publicly before the seal was opened.

**Costs.** Four sites must change together, and row 1 must either be recomputed
at 20 of 20 or deleted — recomputing it is real work with a live deadline, and
deleting it loses the sharpest sentence in `the-contribution.md` (*"where it
ships a rule, it cuts attack success by about three quarters"*). It also puts the
project on record with a rate under a version-B rule while `findings-and-learnings.md`
still carries version A in its header, so that comment must be rewritten in the
same pass or the split just moves.

### Option 3 — keep the current split.

**Buys.** Zero work today. Each document's local rule is internally coherent, and
each figure is individually traceable to a source that names its own population.

**Costs.** The split is what a judge finds, not what they are told. Two v0 rates
two sentences apart in `the-contribution.md:118-122` with no denominator on
either; a superseded pair still standing at `SCOPE-LOCK.md:39` whose supersession
is recorded in two other files; and one directory carrying a blanket ban and a
quoted rate at the same time. **This is the option that most closely resembles
the defect the project has published three findings about** — a document going
stale by standing still while the thing it describes moves.

### Option 4 — silence at the top, the record kept underneath.

Version A governs everything a judge reads as submission text
(`docs/devpost/`, `docs/contest/`); the completed figures stay in
`where-we-stand-2026-08-27.md`, `RESULTS.md` and `AUDIT.md` as the internal
record, reachable by a judge who follows a link but never quoted at them.

**Buys.** No contradiction in the judged surface, and nothing is destroyed. Fewer
edits than option 2.

**Costs.** A reader who does follow the link finds a figure the submission text
declined to state, which reads as concealment rather than restraint unless the
submission text says out loud why it is silent. That extra sentence is the real
work of this option.

---

### My recommendation

**Option 2, narrowed to the pooled figure, and I would delete row 1 rather than
recompute it.** The reason is that option 1 and option 4 both spend a real,
completed, replicated, reader-accepted measurement to buy consistency that option
2 also buys — and this project's whole credibility argument is that it publishes
the number even when the number is unflattering, which is a strange argument to
make while declining to publish the one number it earned. Row 4 is already the
honest version: it prints its denominators, it prints its acceptance count, it
prints its own replication disagreement in the same sentence, and its wording was
committed before the seal opened. The conditional rate in row 1 is the one thing I
would drop without hesitation, because it is the only figure in the inventory with
no completed-batch replacement, and a conditional rate sitting two sentences from
an unconditional one is how a judge gets the impression of a contradiction that
the underlying data does not actually contain. What survives is one figure, one
denominator, one caveat, in every file — which is the same discipline the rest of
the repository already applies to hashes and counts.

---

## 5. The mechanical follow-up, per option

Every entry below is a file and line as read on 2026-08-30. Line numbers move
when a file above them is edited; re-locate by the quoted text, not by the number.

### If option 1 (quote nothing)

| File | Line | Change |
|---|---|---|
| `docs/devpost/the-contribution.md` | 118-122 | Delete the figures. Keep the surrounding argument — the v0 design target of 68% versus a far stronger agent is a finding that needs no rate |
| `docs/contest/SCOPE-LOCK.md` | 38-41 | Replace the quoted sentence with the same point made without numbers |
| `docs/devpost/story-amendment-2026-08-28-prepared.md` | 107-119 | Rewrite the paragraph, or do not append the amendment. Its own pre-registration requires that both batches be reported if either is |
| `docs/devpost/SCORECARD-DRAFT.md` | 62 | Decide whether `8 of 50` survives. It is a count over a frozen offline set, so it can be exempted explicitly — but the exemption has to be written down or the rule is broken on sight |
| `RESULTS.md` | 8-10 | Rewrite the banner to state the blanket rule, since it currently states the opposite |
| `README.md` | 65-66 | Same rewrite, same words |
| `docs/devpost/findings-and-learnings.md` | 21-25 | No change. This is the governing text under this option |

### If option 2 (one figure everywhere)

| File | Line | Change |
|---|---|---|
| `docs/devpost/the-contribution.md` | 118-122 | Replace both figures with the row-4 shape. Delete the conditional `13.3% → 3.2%`, or recompute it at 20 of 20 first and label it explicitly as conditional on promotion |
| `docs/contest/SCOPE-LOCK.md` | 39 | Replace `11.3% to 6.2%` with the pooled pair, and strike the old value in place with its date rather than overwriting it |
| `docs/devpost/findings-and-learnings.md` | 21-25 | Rewrite the header comment from version A to version B, or the split survives the fix |
| `docs/devpost/story-amendment-2026-08-28-prepared.md` | 107-119 | No change to the numbers. Fill the `[FILL: ...]` slots and append per its own steps 1-5 |
| `docs/devpost/project-story.md` | end | Append the amendment. Its Results section stays as it reads |
| `RESULTS.md`, `README.md` | 8-10, 65-66 | No change. Both already state version B |
| `docs/design/where-we-stand-2026-08-27.md` | — | No change. The body is a dated snapshot and the amendment already supersedes it in place |

### If option 3 (keep the split)

Two edits, minimum, or the option is indefensible rather than merely unresolved:

| File | Line | Change |
|---|---|---|
| `docs/contest/SCOPE-LOCK.md` | 39 | Add the supersession marker that already exists in two other files. A superseded figure standing unmarked in the scope-lock is the single most quotable defect here |
| `docs/devpost/the-contribution.md` | 118-122 | Add the denominators. `13.3%` and `11.3%` two sentences apart with neither denominator stated is the sentence a judge misreads |

### If option 4 (silence at the top, record underneath)

The option-1 edits to `docs/devpost/` and `docs/contest/`, plus one sentence in
`docs/devpost/the-contribution.md` stating that efficacy figures exist, where
they live, and why the submission text does not lead with them. Without that
sentence this option is option 1 with a hole in it.

---

## 6. What this pass did not do

- **No file carrying a figure was edited.** Rows 1 to 9 stand exactly as quoted.
- **No figure was recomputed.** The conditional rate in row 1 has no
  completed-batch value in this document because none exists in the tree on
  2026-08-30.
- **No sealed material was read**, and no batch was re-run.
