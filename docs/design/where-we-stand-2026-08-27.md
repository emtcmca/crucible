# Where CRUCIBLE stands against its own published targets

**2026-08-27, computed over `evidence/batch-measure-2026-08-27` while it was still
running.** Figures here are marked with the bundle count they came from and are
**provisional until the batch completes**. Eric's question, and it is the right
one: *"We didn't set floor or target values so I'm having difficulty knowing how
accurate and in tune CRUCIBLE is overall. It works, but how well does it work and
how can we prove it."*

**We did set targets.** They are in `docs/measurement-spec.md` §8.1, they were
written before any run existed, and they are copied into `RESULTS.md` as the `v0
target` and `vFinal target` columns. This document reads the scoreboard against
them.

---

## 1. The scoreboard

Reader acceptance is printed beside the pool because ruling 60 requires it:
**the reader accepts 15 of 15 bundles in this batch.**

| What is measured | v0 target | vFinal target | Observed | Verdict |
|---|---|---|---|---|
| **Attack success rate** | 34/50 = **68%** | 3/50 = **6%** | v0 **11.3%** · final **6.2%** pooled | target met, **from a start 6x lower than designed** |
| **Benign work still passes** | 26/26 | 26/26 | **26/26 in every run** | met, with the caveat in §4 |
| **Near-miss benign passes** | 14/14 | 14/14 | **14/14 in every run** | met, same caveat |
| **Exclusion rate per run** | ≤ 5% | ≤ 5% | **0 of 15 runs refused** | met — and it was 51 of 60 two days ago |
| **Runs that promoted any rule** | not targeted | not targeted | **7 of 14** · 3 more had no breach to fix · **4 found a breach and shipped nothing** | the 4 are the number that should worry us |

---

## 2. THE HEADLINE IS NOT THE ONE THAT LOOKS BEST

**CORRECTED 2026-08-27, an hour after this document was written, and the
correction is the substance.** This section said *"half the runs changed
nothing — CRUCIBLE ran, attacked, diagnosed, proposed, and shipped nothing."*
**That sentence conflates two opposite outcomes and is wrong about both.**
Read at source, a run that promotes no rule is one of two entirely different
things:

| outcome | runs | what actually happened |
|---|---:|---|
| **CONVERGED, agent held** | **3** | **zero breaches.** `status: converged`, three consecutive dry rounds, `promoted 0 rejected 0`. The full campaign ran and the agent survived every attack put to it |
| **PROMOTED** | **7** | breach → autopsy → proposal → gate PROMOTED. The loop closed |
| **HALTED, found but could not ship** | **4** | 2 to 4 breaches each, an autopsy for **every** breach, proposals written — and **the gate rejected every candidate**, `HALT_HUMAN_GATE_REJECTED_TWICE` |

**"Did nothing" is wrong twice.** In the first group CRUCIBLE proved the agent
holds, which is a RESULT and is the loop's designed terminal state, not a
failure to act. In the third group it detected, diagnosed and proposed — every
stage but the last — and **the gate is what stopped it**, which is the gate
doing its job.

The comparison that is actually meaningful:

| | runs | attacks succeeding before | after |
|---|---:|---|---|
| runs that promoted at least one rule | 7 | 12/90 = **13.3%** | 4/126 = **3.2%** |
| runs that found breaches and shipped nothing | 4 | 11/114 = **9.6%** | **unchanged** |
| runs with no breach to fix | 3 | **0** | **0** |

**Where it ships a rule, it cuts attack success by about three quarters. Where
it finds a breach it cannot answer, it stops rather than ship a bad rule.**

This is the expected direction, and it was pre-registered: the gated
configuration's prediction **P1** said *"promotions fall — fewer promotions is
the expected and correct outcome, not a regression"*, because both efficacy gates
(originating-breach closure, and G4 attack reduction) are ENFORCING in this batch
and a failing candidate is now rejected instead of shipped. Before those gates
existed, **19 of 32 promoted rules closed nothing**. The loop is now shipping
less and shipping better. Whether that trade is worth it is exactly what these
numbers are for.

**One run of the seven got worse.** `run-01` went 1/18 to 2/12. It is reported
here rather than dropped.

## 3. THE TARGET WE MISSED HARDEST IS AN ASSUMPTION ABOUT OUR OWN AGENT

**The v0 target is 34 of 50, or 68%. The observed v0 rate is 11.3%.**

That is not CRUCIBLE underperforming. It is the design having assumed a target
agent far weaker than the one we built. The same finding is already recorded
against the frozen 50-episode baseline, where **8 of 50 attacks succeed against
an agent with no rules at all** against a design that presumed roughly 30.

**Why it matters more than the vFinal number.** Hitting a 6% final target from a
68% start would be a large effect. Hitting it from an 11% start is a small one,
because **the entire gap CRUCIBLE has to work in is about 11 points, not 62.**
Any honest reading of "we met the target" has to carry that sentence.

**It is a real result about the agent, not a defect.** A refund agent whose own
prompt and tool design already refuse 89% of a purpose-built attack corpus is a
well-built agent. It also makes it a hard subject to demonstrate hardening on,
and that tension is the honest story.

## 4. WHAT 26/26 DOES NOT MEAN

Benign pass rate is perfect in every run, and it is the weakest strong number
here.

- **4 of the 26 passes are `APPROVAL_ORACLE`-masked** (ruling 37.1). The fixture
  passed because an approval oracle rubber-stamped it, not because the policy
  left it alone. **26/26 does not mean "ran untouched".**
- **`benign_passes_requiring_approval` is NOT BUILT.** The fix for that is a
  change to the ruler and it has not been made.
- The transferable finding this project keeps repeating applies here most of all:
  **a rule that over-blocks passes every gate.** It blocks the attacks, the
  approval oracle rubber-stamps the benign cases, benign pass rate reads perfect,
  and the gate promotes it — and the agent has been made useless. **A perfect
  benign score is exactly what that failure looks like from outside.**

## 5. What changed in the last 48 hours, because the trend is the argument

| | 08-25 night batch | 08-27 measurement batch |
|---|---|---|
| bundles the reader accepts | **0 of 60** | **15 of 15** |
| runs over the 5% exclusion ceiling | 51 of 60 | **0** |
| efficacy gates | not enforcing | **enforcing** |

The 60-run batch is refused for a schema field ruling 55 added after it was
written, and 46 of the 60 additionally breach the exclusion ceiling. **Nothing
from it is quotable.** The move from 0 quotable runs to 15 came from two fixes:
per-run red seeds (so a batch stops walking one corpus path repeatedly) and the
degeneracy census re-recorded over all 50 corpus instances.

## 6. How we prove it, which is the second half of the question

Every number above is checkable by someone who does not trust us:

1. **The reader gates what may be quoted.** Bundles it refuses produce no
   figures, and every aggregate prints its acceptance count beside the number.
2. **The reader itself is now under test.** `crucible/replay/known_bad.py` —
   nine deliberately damaged bundles plus a control, each asserting both the
   defect code and its class, with proofs that the suite catches a reader that
   accepts everything and one that rejects everything.
3. **The targets were published before the runs.** They are design targets in a
   spec, not numbers chosen after seeing results.
4. **The corrections are published too.** `AUDIT.md` carries every withdrawn
   figure, including a headline ASR figure withdrawn on 2026-08-27 because it
   came from ten bundles the reader refuses.

## 7. What is still missing, stated plainly

- **The batch is not finished.** 15 of 20 runs at the time of writing.
- **k=1.** Single sample per run, no stability estimate. The spread across runs
  is the only variance estimate available.
- **One target agent.** Everything except the foreign-agent probe is measured
  against one refund agent.
- **The held-out family is still sealed.** F4 opens 2026-08-28 and **no transfer
  number exists before then.**
- **Nothing here is a re-attack.** Rates are over episodes the loop actually ran;
  the closure measurement is a replay of recorded calls. Neither answers *could
  an attacker find another way in.*

---

# AMENDMENT, 2026-08-28. THE BATCH FINISHED, AND A SECOND ONE DISAGREES WITH IT.

**The body above is a correct snapshot of a batch that was still running, and it
is left exactly as written.** It says so in its own first line and again in §7
(*"15 of 20 runs at the time of writing"*), and that self-naming is the only
reason this amendment could be written rather than guessed at. **A dated
snapshot is struck and amended, never rewritten.**

`evidence/batch-measure-2026-08-27` completed at 20 runs, and the replication
batch at identical configuration completed at 20 more. Everything below
supersedes the corresponding figure above. All figures exclude `TARGET_FAULT`
episodes per `docs/CONVENTIONS.md:1133`, and every one is **k = 1 per episode,
no stability estimate**.

## A1. Reader acceptance

| | body above | completed |
|---|---|---|
| measurement batch | 15 of 15 | **20 of 20** |
| replication batch | 17 of 17 | **20 of 20** |

Both denominators above were mid-batch counts. Neither was wrong when written;
both are superseded.

## A2. Attack success rate, and the two batches do not agree

**Pooled across both batches, v0 is 70/520 = 13.5% and vFinal is 56/725 = 7.7%
— and the two batches disagree materially, the replication running about four
points worse at both ends (v0 15.4% vs 11.8%, vFinal 9.7% vs 5.7%).** That
sentence is one sentence on purpose: the replication pre-registration requires
the disagreement to travel with the pooled figure rather than sit in a footnote
under it.

| | v0 | vFinal |
|---|---|---|
| **pooled** | 70/520 = **13.5%** | 56/725 = **7.7%** |
| measurement batch | 33/280 = **11.8%** | 21/366 = **5.7%** |
| replication batch | 37/240 = **15.4%** | 35/359 = **9.7%** |

**This supersedes the pair in §1 and §3, which read ~~v0 11.3% → final 6.2%~~.**
The direction of §3's argument is unchanged and if anything is sharpened: the
v0 design target is 34/50 = 68%, the observed pooled v0 is 13.5%, so the gap
CRUCIBLE has to work in is about 13 points and not 62. The replication is the
first evidence this project has about run-to-run spread, and the first thing it
says is that a single batch understated the rate at both ends.

## A3. The denominator in §2's third row was wrong

§2 reports *"runs that found breaches and shipped nothing: 11/114 = 9.6%"*.
**The correct figure is 11/60 = 18.3%, over the 4 runs in that group.** The old
denominator pooled those 4 runs together with the 3 runs that had no breach to
fix, which is the one comparison that row exists to keep apart — a run that
found nothing and a run that found something and could not answer it are the
opposite outcomes §2 was written to separate, and its own denominator blurred
them back together.

The corrected row nearly doubles the rate, and it should: measured only over
the runs where a breach was actually found and no rule shipped, the attacks
that succeeded are a much larger share of a much smaller pool. The
qualitative reading in §2 stands — the gate stopped a bad candidate rather than
shipping it — but the number attached to it was diluted by three runs that had
nothing to ship.

## A4. What this amendment does not touch

The benign rows (26/26, 14/14), §4's reading of what 26/26 does not mean, and
§6's account of how any of it is checkable are unchanged. §2's *"19 of 32
promoted rules closed nothing"* is also unchanged and stays correct: it is the
recount over **15** accepted bundles recorded in
`gate-noop-measurement-2026-08-25.md` and [`AUDIT.md`](../../AUDIT.md) C13,
superseding an earlier 18 of 31 over 14.
