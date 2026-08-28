# PREPARED story amendment, 2026-08-28

**Written and committed BEFORE the sealed family was opened.** That is the only thing
that makes the transfer section below worth anything. The five outcome branches come
from `docs/proof/f4-unseal-preregistration-2026-08-25.md` section 3, which was public
on the remote before the unseal. Choosing the framing after seeing the number is the
move that pre-registration exists to prevent, so the framing is fixed here and only
the counts are filled in afterward.

## How to apply this

1. Fill every `[FILL: ...]` slot from the source named beside it. Never from memory.
2. Delete the four transfer branches that did not occur. Keep exactly one.
3. Delete this header and everything above the append block.
4. Append the block to the END of `docs/devpost/project-story.md`. Alter nothing above
   it, including the Results section, which keeps reading "deliberately empty as of
   2026-08-20" exactly as the two prior amendments left it.
5. Record the commit SHA of THIS file in the append comment, so a reader can check the
   wording predates the unseal.

## Register constraints, checked against the existing story

- **No em-dashes.** The story currently contains zero. Commas, periods, colons.
- Every figure carries its label. `execution-spec` 5a claim discipline.
- Reader acceptance prints beside any aggregate. Ruling 60.
- No hash values in prose. Ruling 46. Name the artifact, not the value.
- Lead with the unglamorous fact.

## Verification checklist before this is posted

| Slot | Source of truth | Status |
|---|---|---|
| Replication pooled figure and per-batch split | the two batch bundles, read through the offline reader | **NOT YET COMPUTED** |
| Reader acceptance for both batches | `evidence/batch-measure-2026-08-27/BATCH-DONE`, `evidence/batch-replicate-2026-08-27/BATCH-DONE` | verified 08-28: 20 of 20 each |
| Refused patch attempts in the measurement batch | `scripts/unresolved-findings.py` | **RE-VERIFY**, quoted as 18 in SCOPE-LOCK |
| 19 of 32 promoted rules closed nothing | `docs/design/gate-noop-measurement-2026-08-25.md`, corrected by the ruling 60 sweep | verified 08-27 |
| Three invariant classes and their counts | `docs/design/why-three-invariants-never-close-2026-08-27.md` | verified 08-28: 12, 4, 2 |
| Seal integrity at unseal time | `python scripts/seal-commitment.py --verify` | verified 08-28: INTACT, 24 instances |
| Attested reads and intruders | `infra/holdout_touch.py` counter | verified 08-28: 11 reads, all attested, 0 intruders |
| Transfer counts | the unseal run bundle | **DOES NOT EXIST BEFORE THE UNSEAL** |

---
---

<!-- APPEND EVERYTHING BELOW THIS LINE TO project-story.md -->

---

<!-- APPENDED 2026-08-28. Nothing above this line was altered, including the Results
     section, which still reads "deliberately empty as of 2026-08-20" and will keep
     reading that way. The numbers arrive here, dated and labelled, rather than by
     editing it. The WORDING of every section below, including which transfer outcome
     gets reported and in what terms, was fixed and committed publicly at
     [FILL: SHA of story-amendment-2026-08-28-prepared.md] before the sealed family
     was opened. Only the counts were filled in afterward. -->

## A policy that had never seen the agent it governed (added 2026-08-28)

Google publishes a customer service agent as an ADK sample. Nothing about it was changed:
its own code, its own model, its own tools, its own callbacks. CRUCIBLE's enforcement
plugin was attached to the app and the agent was asked an ordinary customer question.

With no policy, the agent called its approval tool for a 40 percent discount. It executed,
returned approved, and the agent told the customer so. There is no manager behind that
tool. It approves whatever it is handed.

With a policy CRUCIBLE had learned on a completely different agent, the same question and
the same call were refused. The tool never ran. The rule that stopped it names no tool at
all. It binds to a capability class, and the class was assigned to that tool by a
classifier reading the tool's own description.

**This is not a breach and the distinction is the point.** The sample's own prompt
describes that tool as asking a manager for approval and never states a cap, so routing a
large discount there is obedience, not compromise. The claim is narrow and it is about
CRUCIBLE rather than about Google's code: a policy learned on one agent governed the real
tool calls of another. It is possible only because enforcement lives in a plugin at the
ADK `before_tool` boundary instead of in a fork of one agent.

It is one run per arm. There is no rate here and no before and after percentage.

## The caveat that was on every number until now (added 2026-08-28)

Every figure this project has published carried the same label: single sample, k=1, no
stability estimate. It was the most repeated limitation in the repository and it weakened
every number equally.

Two batches now exist at identical configuration with different seeds, the second
pre-registered before it fired. The reporting rule was fixed in that pre-registration and
it is symmetric: both batches are reported, neither is dropped whichever looks better, the
headline is the pooled figure, and the per-batch split prints beside it. If the two
disagree materially, the disagreement is the finding.

**The reader accepts 20 of 20 bundles in each batch.** That count travels with the figures
because a rule in this repository requires it, and because two days earlier the same reader
refused all sixty bundles of an overnight batch.

[FILL: pooled attack success rate, then the per-batch split. If the batches disagree
materially, say so in this sentence rather than in a footnote.]

**A replication that contradicts the first batch does not retire the first batch. It
retires the claim that one batch was enough.**

## The transfer result (added 2026-08-28)

The sealed family was opened on 2026-08-28. It was written in a separate pass, sealed
before the first patch existed, and the identity that authors patches holds no read on the
bucket it lives in. At the moment of opening, the commitment verified byte identical
against its published fingerprint across 24 instances, every recorded read of that bucket
since audit logging was enabled was accounted for and attested, and no unauthorized
principal had ever touched it.

*(Keep exactly one branch below. Delete the other four.)*

**BRANCH A, clean transfer result.**
[FILL: the transfer figure, whatever it is, with k=1 and its separated-by split.] Blocked
or not blocked, this is the number the project was built to produce, and it reads the way
it reads.

**BRANCH B, valid but partial.**
[FILL: the figure, the exclusion rate beside it, and the count of sealed instances failing
the validity criterion.] This is a partial measurement over a stated denominator and it is
labelled as one.

**BRANCH C, invalid by exclusion.**
**No transfer rate is quoted. None.** The reader refused the bundle for breaching the
exclusion ceiling. [FILL: count of instances failing the validity criterion, and the
exclusion rate.] The held out family carried the same corpus defect the visible families
carried, and the transfer question has no answer in this build. That is a finding about
the corpus rather than a failure to be quietly dropped, and it was pre-registered as a
publishable result before anyone knew it would be the one.

**BRANCH D, invalid by seal.**
The seal did not hold. [FILL: when, and by which principal.] No transfer claim of any kind
is made, and the record of the breach stays in the repository.

**BRANCH E, valid, denominator below the floor.**
The run was valid, the reader accepted it, and the exclusion rate sat under the ceiling.
**No transfer rate is quoted, because the quotient is not defined at this denominator.**
[FILL: breached at v0 and breached at vFinal, as raw counts, and the floor they fall
under.] The held out family was insufficiently potent against the unhardened baseline.

Read honestly, a zero here is evidence of a defence that already held before any patch was
written, not evidence of a broken instrument. All five money invariants are proven firable
against a real recorded event, so the clause is not the reason the number is small. That
reading was fixed in the pre-registration before the set was opened, and it is bounded by
its own evidence: it rests on a probe at k=5 over one constructed variant family.

**What this does not license.** Outcome E is not a way to report a good result from a bad
run. It quotes no rate. It publishes two raw counts and the floor they fall under.

## What it found and could not fix (added 2026-08-28)

The more useful half of the output is the list of what CRUCIBLE could not close.

Three invariant classes are found reliably and never closed, and each fails for a different
reason. In one, worth 12 findings, the armorer answers an aggregate clause with a per call
comparison, because the rule language it must write in cannot express the grouping the
judge uses. In another, worth 4, the proposed rule is correct and closes the breach, and
the gate rejects it for being too general. In the third, worth 2, the armorer constrains
the wrong field.

The first of those is a finding about our own design rather than about the model. The
grouping gap is in the language, so no amount of prompting fixes it.

**The gate also refuses.** [FILL: count of refused patch attempts in the measurement batch,
from `scripts/unresolved-findings.py`] patch attempts were rejected, each with the invariant
it targeted, the rule that was attempted, and the machine checked reason it failed. Before
those efficacy gates existed, **19 of 32 promoted rules had closed nothing at all.** That
number was not found by review. It was found by measuring our own output and it got worse,
not better, the second time it was counted.

The loop now ships less and ships better. Whether that trade is worth it is exactly what
these numbers are for.

## What is still not known, at the end (added 2026-08-28)

One target agent. Everything except the foreign agent demonstration is measured against a
single refund agent, and a design that assumed a far weaker one: the published target was
34 of 50 attacks succeeding at the unhardened baseline, and the observed figure is closer
to 11 percent. The entire gap available to work in is about 11 points, not 62. That is a
real result about the agent rather than a defect, and any honest reading of "we met the
target" has to carry it.

A perfect benign score is the weakest strong number here. Some of those passes are
rubber stamped by an approval oracle rather than left alone by the policy, and the fix for
that is a change to the ruler which has not been made. The transferable finding this
project keeps rediscovering applies to itself most of all: **a rule that over blocks passes
every gate.** It blocks the attacks, the oracle waves the benign cases through, the benign
rate reads perfect, and the gate promotes it, and the agent has been made useless. A
perfect benign score is what that failure looks like from outside.

Nothing here is a re attack. The rates are over episodes the loop actually ran, and the
closure measurement replays recorded calls. Neither answers whether an attacker could find
another way in.

The sealed set was reviewed by one person, who is also the person who built the thing it
was used to test.
