# AUDIT — corrections, withdrawn claims, disclosed leaks, and the trust root

*This document is the point of the project. Everything a reader would use to
argue that CRUCIBLE overstates itself is collected here on purpose, because a
harness whose entire thesis is "a system that grades its own work is not
measuring anything" cannot then grade its own README.*

Split out of `README.md` on 2026-08-26 with the correction ledger added. The
sections below the ledger are the README's own limitation and correction text,
moved verbatim.

Companion documents: [`MEASUREMENT.md`](MEASUREMENT.md) ·
[`RESULTS.md`](RESULTS.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Correction ledger, 2026-08-26

**Every row was found by re-verifying a README sentence against the file that
owns it, during the restructure of 2026-08-26.** The wrong version is quoted
rather than deleted, because a correction that hides what it corrected is
worth less than the mistake it fixes. The rows are in the order they were
found.

| # | The README said | Verified at source | Where it now stands |
|---|---|---|---|
| C1 | ~~`757 passed, 1 skipped in 10.15s`~~ | 2,041 tests collected, **2,038 passed, 3 skipped, 0 failed**, 62.9s — JUnit XML from `python -m pytest tests/ -p no:cacheprovider` on 2026-08-26 | Corrected in the README's test section |
| C2 | ~~"Seventeen ADRs in `docs/adr/`"~~ | **18** files in `docs/adr/`; `ADR-0018-corpus-provenance-is-the-commitment-not-the-generator.md` landed after the sentence was written | Corrected in `ARCHITECTURE.md` |
| C3 | ~~"revision `crucible-00003-t2q` at 100% traffic"~~ | `docs/proof/cloud-run-redeploy-2026-08-24.txt:33-35` — the serving revision is **`crucible-00004-gfk`**, deployed 2026-08-24 22:58:01 UTC. The URL is unchanged. The same file at `:46-48` records that **postconditions 3 and 4 are owed again for the new revision**, and at `:49-50` that the 2026-08-21 captures "are now stale for video purposes" | Struck in place in `ARCHITECTURE.md` |
| C4 | ~~"16 assertions, 15 PASS, 1 UNEVALUABLE" on 2026-08-22~~ | `docs/proof/L3-real-gate-G7-G8-2026-08-22.txt:36` reads **16 assertions, 16 PASS, 0 not PASS**. The 15/1 split belongs to the **2026-08-25** re-run, and its one non-PASS is a **FAIL, not an UNEVALUABLE**: `L3-real-gate-G7-G8-2026-08-25.txt:32-33`, `holdout_touch_count is 11, expected 0` | Struck in place in `ARCHITECTURE.md` |
| C5 | ~~"the project has no `auditConfigs` block, so the number does not exist to be read"~~ | Contradicted. Data Access audit logging was enabled 2026-08-22 — `L3-real-gate-G7-G8-2026-08-22.txt:41-47` counts granted object-content reads, and `docs/contest/BUILD-LIST.md:553` records "G7 fully evaluable for the first time" | Struck in place in `ARCHITECTURE.md` |
| C6 | ~~"The probe has not been re-run since [2026-08-22]"~~ | False since 2026-08-25. It was re-run that day (`docs/proof/L3-real-gate-G7-G8-2026-08-25.txt:6`), and `docs/design/g7-unevaluable-2026-08-25.md:33-35` records G7/G8 evaluated inside the 60-run batch at 95 gate calls, 16 assertions each | Struck in place in `ARCHITECTURE.md` |
| C7 | ~~"left 21 objects under `gs://crucible-policies-x7/runs/`"~~ | **UNVERIFIED, and probably a transplant.** No file in the tree evidences any object count for that bucket. `docs/design/spec-drift-audit-2026-08-25.md:546-552` says the bucket was never queried and names the command that would settle it. `21` in this repository is the SEP-BY policy count (`docs/data-spec.md:594`) | Removed and replaced with the unverified marker, `ARCHITECTURE.md` |
| C8 | ~~"Ten live runs on 2026-08-24 scored 288 episodes ... Every figure in the Results table is still empty"~~ | Stale twice over. The batch was **9 bundles**, 288 episodes (`crucible/conductor/bundle.py:1253`, `crucible/tripwire/verdict.py:71`), and three further batches ran after it — smoke and pilot on 2026-08-25 and the 60-run night batch, which filled the column the sentence says is empty | Struck in place in this document |
| C9 | ~~"in the ten-run live batch of 2026-08-24"~~ (Cost) | Same stale batch, same wrong count. And **no artifact in the tree records actual billed spend**: `docs/ops/billing.md:203-207` is still UNVERIFIED on its own postcondition, dated 2026-08-21 and untouched since | Struck in place in this document |
| C10 | ~~"the D5 corpus freeze that must land before the first patch is written"~~ (open-work list) | D5 was frozen, superseded three times, and re-frozen on 2026-08-25 after the F5-05 repair — `docs/proof/d5-corpus-freeze.json`, superseded records beside it | Struck in place in this document |
| C11 | The seal fingerprint was printed as a 64-hex literal in the measurement section | **Ruling 46**, `docs/CONVENTIONS.md:729-734`: *"No prose document states a current hash value, including this one. Prose names the owner and the command that reads it."* | The prose block now names `docs/proof/sealed-family-commitment.json` and the command. Pasted command transcripts are left alone: a transcript is a dated capture of what a program printed, which ruling 46 treats as historical rather than as prose asserting a current value |
| C12 | `evidence/` — ~~"Empty today"~~ | It does not exist at all in a fresh clone or in a worktree; it is gitignored, and this restructure was carried out in a worktree where `ls evidence/` returns "No such file or directory" (checked 2026-08-26) | Corrected in `ARCHITECTURE.md` |

**Two things the ledger above should not be read as.** It is not a list of
everything wrong with this repository, and it is not evidence that the
remaining sentences are right. It is what one pass over one file on one day
found, and the reason twelve rows exist is that this was the first time
anything checked the claims in `README.md` against their sources rather than
against each other.

## Correction ledger, 2026-08-27

**Two rows. What makes the first worth its own section is how it was found: a check
found it, not a person. The second is a headline figure we withdrew in full.** Ruling 60 shipped an acceptance banner on every script
that aggregates a batch. Its first sweep over all 123 bundles on disk disagreed
with a figure that had already been hand-verified and published.

| # | The claim said | Verified at source | Where it now stands |
|---|---|---|---|
| C13 | ~~"18 of 31 promoted rules closed nothing"~~ | **19 of 32.** `docs/design/gate-noop-measurement-2026-08-25.md` section 4 records that the `pilot-2026-08-25` batch "was still writing when these bundles were copied" — `run-08` was mid-write, was refused by the reader, and was assigned to the refused population. It has since completed and the reader ACCEPTS it. Recounted 2026-08-27 with `scripts/gate-noop-measurement.py`: 15 bundles, 32 rules, **CLOSES 13, NO_OP 19**. The other 14 bundles are unchanged at 13 and 18, so the whole delta is `run-08`, whose single promoted rule is a NO_OP of the same aggregate-clause shape | Corrected in `docs/CONVENTIONS.md` ruling 58 and in `docs/devpost/SCORECARD-DRAFT.md`. **`RESULTS.md` carries a standing notice**: its `[14]` marker is defined as "the bundles the C6 reader accepts", which is this same population, so every `[14]` rate in the results table is pending one recompute pass over fifteen bundles. No `[14]` cell is withdrawn — each was computed correctly over the population as it stood — and none is restated until that pass lands. The 08-25 measurement document keeps its snapshot figures and carries a dated amendment; the gated-run pre-registration keeps its text and carries an amendment note, because a pre-registration edited after the fact is not one |

| C14 | ~~"attack success falls from 8 of 50 to a median of 2.5 across ten runs", and the generalization split ~~"44 to 12 on attacks a run drew, 36 to 16 on attacks it never drew"~~ | **WITHDRAWN 2026-08-27, in full, in both directions.** The figures were computed over ten bundles of `evidence/batch-grammar-2026-08-26/`. **The offline reader refuses all ten** — `slice_is_blind_to` written as `null` on the default slice, and canonicalization restriction 5 refuses nulls because an absent fact must be an absent key. Six of the ten additionally breach the 5% exclusion ceiling. **The headline was computed without once asking whether the reader accepted the bundles it came from** — on a project whose own `docs/HOW-TO-READ-A-RUN.md` §7 says the exit code is not evidence, in a section its author wrote | Removed from `docs/devpost/SCORECARD-DRAFT.md`, which now states the withdrawal and the reason in place of a number. **No replacement figure is quoted anywhere until a re-run in the corrected configuration produces one with an acceptance count beside it.** `RESULTS.md` never carried these figures — it measures ASR per round over episodes, a different quantity |

**The direction this moved is the reason to trust the row.** 58.1% to 59.4% —
**the negative finding about our own gate got worse.** A recount that only ever
ran when the number would improve would not be a check.

**What it also says about the 08-25 document, which was not wrong.** That
document named its own limitation in the sentence directly above the population
list, and the recount was possible only because it did. A snapshot that states
the condition it was taken under can be re-taken. One that does not, cannot.

---

### The register of things marked UNVERIFIED rather than dropped

- **`pip install -r requirements.txt` into an empty virtualenv has not been
  executed** (recorded in the README's install section since 2026-08-21). What
  is verified is that the pinned versions are the ones everything else ran
  against, not that a cold resolve succeeds.
- **The `--live` campaign path.** `python -m crucible.conductor.campaign --live`
  calls Vertex and costs money; it is not part of any command a judge is asked
  to run, and the README has never claimed a result from it.
- **The ADK issue #4704 probe.** The D1 probe that would confirm or refute the
  upstream report on this machine has not had its result recorded anywhere in
  the spec set or in ADR-0012. The decision holds either way; the observation
  is missing.
- **Total billed spend.** Per-run cost is written into every evidence bundle
  and `evidence/` is gitignored, so the figure exists only on the builder's
  machine. No dollar total appears anywhere in this repository, and the only
  spend sentence in the tree is unsourced prose in a design document.
- **The demo video.** Recorded as the one Stage One deliverable that does not
  exist, `docs/contest/CONTEST.md:66` as of 2026-08-22 and still true when this
  document was written on 2026-08-26.

---

## What this does not prove

This section is the one that decides whether anything above is worth reading.

**1. What has been measured is a handful of batches, and no rate from any of them may be
quoted today.** *(REWRITTEN 2026-08-26. The struck version is kept underneath because how it
went wrong is more useful than the fact that it did.)*

Six live batches exist. Two single runs on 2026-08-23 and one on 2026-08-24 are **INVALID**
and are not evidence for anything. A 9-bundle batch on 2026-08-24 recorded 288 episodes
(`crucible/conductor/bundle.py:1253`). A smoke set and a pilot set ran on 2026-08-25. The
sixty-run night batch of 2026-08-25 is the one every figure in [`RESULTS.md`](RESULTS.md)
came from — and **the shipped offline reader now refuses all sixty of its bundles**, because
ruling 55 made `episodes[].target_responded` required after they were written
(`docs/design/gate-noop-measurement-2026-08-25.md:161-171`). A seventh batch, the post-repair
one that would regenerate the column, is pre-registered at
`docs/design/batch-2026-08-25-post-repair-preregistration.md` and **has not been run**.

So the honest state on 2026-08-26 is worse than "unlabelled": the bundles are gitignored, so a
reader cannot check them against this file, **and neither can the reader this repository
ships**. The counts stand; the rates do not.

> ~~**1. What has been measured is one batch, and it is unlabelled.** Ten live runs on 2026-08-24
> scored 288 episodes and promoted policy for the first time. Every figure in the Results table
> is still empty and every target there is still a target, because those episode counts have
> not been through the labelling pass or the policy / approval-oracle split. Until they have,
> this repository contains raw counts about how one agent behaved under attack and **no rate
> that may be quoted as a result.** The bundles are gitignored, so a reader cannot check them
> against this file.~~
>
> **Two defects, and they are different in kind.** "Ten live runs" was never right — the batch
> was nine bundles. And "every figure in the Results table is still empty" went stale within a
> day, while the same file three screens earlier announced a filled column. **A document long
> enough to contradict itself is a document nobody reads end to end**, which is the argument
> for the split this correction was made during.

**2. `k = 1`, single sample, no stability estimate.** When numbers exist they will be from
one run each. Nothing here will support a claim about variance, and stability will be
reported as *unmeasured* rather than quietly omitted.

**3. One target agent, one modelled policy domain.** A refund agent with 8 tools, built for
this harness. The cross-target transfer beat is planned and unrun, and we expect transfer to
be worse against an agent nobody wrote attacks for — that expectation is on record before the
run, not after it.

**4. The SEP-BY split is off target.** The corpus separates **21 pairs by the policy and 3 by
the approval oracle**, against a design target of 18 / 4. That deviation is reported by
`python -m corpus` on every run rather than absorbed. It is not a stop condition — parity
between the two would be — but it is a real deviation between what was specified and what was
authored, and it changes how much of any future headline number is attributable to the policy.

**5. Cross-episode state and dataflow taint are out of scope, by construction.** Policy
predicates are episode-scoped: no clock, no counter surviving the episode, no rate limit
spanning sessions. Velocity attacks and anything requiring memory across sessions are not
measurable here and are not claimed to be. `episode.*` is frozen before turn one specifically
so that the seal cannot be moved mid-episode — which also means CRUCIBLE says nothing about
agents that legitimately maintain context across weeks.

**6. The benign floor is a bound, not a proof.** A clean 26/26 bounds the unobserved
regression rate at roughly 11.5% (amended from 24/24 and ~12.5%, ruling 43, 2026-08-21). It bounds that rate; it does not show the rate is zero, and the two are not the same sentence.

**7. A clean review by the author is evidence about the author's attention, not an
independent check.** All 24 sealed instances were read in full by the builder before the set
was frozen ([`docs/proof/sealed-family-ratification.md`](docs/proof/sealed-family-ratification.md)).
One person read them, and that person built the thing. Four specific hazards were *raised and
cleared* rather than *discovered*, and finding no problems is a weaker signal than finding
some.

**8. One sealed instance has leaked, permanently, and it is not being tidied away.** On
2026-08-21 the ratification document named the order instrument and the smuggled instrument
of one instance of twenty-four verbatim, and that text was committed and pushed to a public
repository. Both occurrences are redacted going forward and **neither redaction undoes the
publication** — a public commit is cloneable and served by SHA long after a rewrite. What it
costs, precisely: a reader who fetched those commits can reconstruct the destination pair of
one instance. It does not move the commitment hash, does not touch the other twenty-three,
and does not change whether the family was sealed before the first patch. What it does affect
is that one instance is no longer blind to a reader who looked, and **if its result is ever
singled out, the leak must be stated in the same breath.** The instance was deliberately not
replaced: swapping it to tidy a leak would break a published commitment in order to hide a
disclosed mistake. It was found by the leak checker written *after* the fact, on its first
real run, against the file its own author had written.

**9. The commitment binds forward, not backward.** Publishing the fingerprint says nothing
about what happened before it was published. The controls for that window are different ones:
the IAM boundary the Armorer's service account cannot cross, and the public commit history of
everything else.

**10. The bundle's confidentiality claim is narrow, and call ORDER sits outside it.**
*(Added 2026-08-30, after an outside reviewer refused to let the broad version stand.)*

A published transfer bundle carries every tool call the target agent made, in the order it
made them. Argument VALUES are bounded or redacted — that work is real, it is checked on
every run, and the reader names which channels are closed, which are bounded and which are
open. **Call order is none of those. It is open, and a permutation carries information.** For
a trace of a couple of hundred calls the ordering alone has room for something on the order
of a thousand bits; the reader prints the actual trace length and `log2(n!)` beside every
report rather than leaving anyone to work it out, and marks the row **ORDERING OPEN**.

**Disclosure is not confidentiality, and this project had been treating them as the same
thing.** The reader annotates the channel accurately and then ACCEPTS the document with zero
defects — a regression test requires exactly that. Saying "the order got out" is honest; it
does not stop the order getting out. The producer still chose to publish it.

**So the claim is narrowed rather than defended.** What may be said is: *selected argument
values are bounded or redacted, and call-order confidentiality is not provided.* What may
**not** be said, in the README, a demo, a submission, or a post, is anything of the shape
*"sealed content cannot escape the published evidence."* That sentence is false and it is now
named as false here so it cannot be reached for later.

**Why the channel is not simply capped.** A cap on trace length is a cap on what the TARGET
AGENT did. The target called what it called; that is the measurement. Refusing to publish a
run because the agent under test was talkative would file a run FACT as a producer DEFECT,
and the resulting number would describe the agent's brevity as much as its behaviour. The
trade is stated rather than taken quietly: **the bundle is publishable because the claim is
small, not because the channel is closed.**

**11. "No F4 object has been read" is three different claims, and only two of them are
true.** *(Added 2026-08-30, after an outside reviewer declined to let the unqualified
sentence stand.)*

That sentence had been the standing shorthand in the handoffs. It does not survive as a
literal statement, because **local copies of the F4 instances have been opened repeatedly** —
by the fingerprint recompute, by the leak checker, and by the pre-read proof that runs both.
Three distinct events were being carried under one word:

| | |
|---|---|
| `CONTENT_READ` | Defined by **A3.2** of [`docs/proof/f4-unseal-preregistration-2026-08-25.md`](docs/proof/f4-unseal-preregistration-2026-08-25.md). That document owns the definition and it is not restated here. It is the unit the holdout counter measures and the one that marks a run INVALID. |
| **LOCAL AUTOMATED PROCESSING** | A local copy opened and processed **by a program only**. It covers more than hashing: `scripts/seal-commitment.py` hashes bytes, but `scripts/seal-leak-check.py` parses each instance's JSON and derives a signal vocabulary from its content — instance slugs, pretext tails, adjacent pretext token pairs, and the smuggled payout instrument identifier (`scripts/seal-leak-check.py:125-178`). **What makes it non-violating is not that the content is untouched — it is read, parsed and mined.** It is that nothing is surfaced to a human or a model and nothing leaves the machine. This is how the seal is PROVEN intact; forbidding it would forbid the proof. |
| **HUMAN-OR-MODEL EXPOSURE** | Sealed text reaching a person's eyes or a model's context. This is what the single attempt is spent on, and what the adjudication gate exists to sequence. |

**What may be said:** no F4 GCS object has been fetched inside the measurement window, and no
F4 content has been exposed to a human or a model. Local copies are opened, parsed, and mined
for signal by local programs. **What may not be said** is the unqualified form, which reads as
a claim about all three and is false about the third.

*(Middle term renamed 2026-08-30, second attempt at this vocabulary. It read **LOCAL
FINGERPRINT ACCESS**, and the same reviewer rejected that too: "the leak checker parses JSON
and extracts slugs, pretext tokens, and instrument identifiers; that is automated local
content processing, not merely 'opened and hashed.'" He is right, and the error is worth
keeping visible — the name was taken from `seal-commitment.py`, which really does only hash
bytes, and then applied to a second tool that does considerably more. **A term coined from one
of the two things it covers will under-describe the other.** Replacing one
under-description with another is the failure this rename is trying not to repeat, so the
definition above names the parsing and the derived fields explicitly and puts the
non-violating property where it actually sits: in the fact that nothing is surfaced and
nothing leaves the machine, not in a claim that the content is untouched.)*

**And the reviewer cannot ratify the first two, which is part of the claim rather than a
footnote to it.** His words, 2026-08-30: *"I cannot independently ratify the first two
without the audit evidence or observing the human process."* The bucket-fetch statement rests
on Cloud Audit Logs that are not in this repository, and the no-exposure statement rests on
what one person did at a keyboard with nobody watching. Both are **attested, not
demonstrated** — the same standing as item 7, and for the same reason.

One consequence landed in the suite the same day. `tests/test_seal_leak_check_refuses.py`
had been searching for the local held-out set and, where it found one, running the real
scanner against it with no override — so on the build machine an ordinary `pytest` performed
LOCAL AUTOMATED PROCESSING on every held-out instance. That is category two and not a
violation, but it is why the reviewer twice declined to run the suite at all, and a claim a
reviewer cannot verify without breaking his own rule is worth less than one he can. Both that
module and `tests/test_pre_read_seal_proof.py` now run against invented fixtures.

**12. Work is open and it is written down.** `docs/contest/BUILD-LIST.md` Tier 4 lists the
threads that block scored work — ~~the D5 corpus freeze that must land before the first patch
is written~~ *(CORRECTED 2026-08-26: D5 was frozen, superseded three times, and re-frozen on
2026-08-25 after the F5-05 repair — `docs/proof/d5-corpus-freeze.json` and the superseded
records beside it)*, ~~the first real loop run~~ *(six live batches have run; see item 1)*,
an unresolved `ALLOW`/`allow` enum spelling that would
make `preceded_by` read false everywhere if a prefix reached the engine uncanonicalized, a
rule that fails validator V4, a parked corpus branch that breaks two frozen counts, and two
benign fixtures authored after the reviewer's pass — so *"the ordinary benign set was
reviewed"* is not true of the set as it stands.

**13. Not reviewed, endorsed, or responded to by Google in any way.** Not production-ready.
Not enterprise-grade. Eleven days, one person, one target agent. There are no users, no
downloads, and no adoption of any kind.

---

## Cost

**$160 is an ALERT, not a cap. Nothing stops at $160.** Corrected 2026-08-24 against the
live billing configuration, which carries `notificationsRule` with project-level email
recipients and three `thresholdRules` at 50%, 90% and 100% of spend. There is no usage
pause, no billing-disable trigger, and no automated stop of any kind. An overrun would
arrive as email after the fact.

This section previously read *"a cap, not an alert, so an overrun is a deliberate decision
rather than a discovery"*, which is the opposite of what is deployed. `docs/data-spec.md`
§15 specified a Spend Cap Budget with usage pause enabled; that is the plan, and it is not
what exists. The wrong version is quoted rather than deleted because the gap between a spec
and its deployment is exactly the class of defect this project is about.

The $160 figure is a frozen parameter. Token ceiling 40M, with the cut list auto-triggering
at 32M.

**Billed runs have now occurred, in the ~~ten-run~~ live batch of 2026-08-24, and no dollar
total is stated here.** Per-run cost is written into every evidence bundle, so this section fills
itself in from the bundles rather than being estimated by hand, and a figure typed in by hand
would be exactly the kind of number this file refuses.

*AMENDED 2026-08-26, three ways. The batch was nine bundles, not ten. Five further live
batches have run since, so "the batch of 2026-08-24" is no longer the last one. And the
sentence "this section fills itself in from the bundles" describes an intention rather than a
mechanism — **nothing fills it in, and no artifact in this repository records billed spend at
all.** `docs/ops/billing.md:203-207` is dated 2026-08-21 and is still UNVERIFIED on its own
postcondition: it asks for a charge line to be read out of the console, and that never
happened. The one spend sentence anywhere in the tree is unsourced prose in a design document.
**Do not quote a dollar figure for this project from any source.***

---

## License

**Apache License 2.0.** See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Chosen 2026-08-20 by
the repository owner.

*This section read "Not yet chosen" until that date, and the reason it did is worth keeping.*
A lane writing this README first drafted "Licensed under Apache-2.0" from habit, because that
is what the author's other public work uses. **Nothing in the repository said so.** It checked
before shipping the sentence, found no `LICENSE`, and wrote what was true instead — which is
how anyone found out that a public repository whose entire value proposition is *"replay the
evidence yourself"* granted a stranger no right to run it.

The most confident sentences are the ones nobody thinks to verify.
