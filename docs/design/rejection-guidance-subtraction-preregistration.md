# Pre-registration: does ANY rejection guidance suppress the grouped rule?

**Written and committed BEFORE the run. 2026-08-26.** If you are reading this
after the result, check `git log` and confirm the order. That ordering is the
entire reason this file exists: it is what separates a stated prediction from a
number explained afterwards, and this repository has now paid for the
distinction twice.

Probe: `scripts/probes/narrowing-loop-probe.py`.
The finding that motivated it: `docs/proof/narrowing-loop-live-2026-08-26.md` §5
and §8.

---

## 1. The question, in one sentence

The grouped rule appears in **9 of 19** of a round's FIRST draws and in **0 of
68** draws made after a rejection, in both of the two guidance paragraphs tested
so far. **Is the guidance what suppresses it, or is it the rejection itself?**

---

## 2. The two arms

| arm | what the model is sent |
|---|---|
| **(a) CURRENT** | the rejection block exactly as `crucible/armorer/prompt.py` now holds it |
| **(b) FACTS ONLY** | the same block with the CLOSING GUIDANCE REMOVED - counts, classes, and the "that is all the information you get" paragraph, and nothing after it |

**(b) is a strict subtraction.** No new sentence is written for it. That is what
makes the comparison readable: any difference is attributable to the removed
text rather than to something introduced in its place.

**Arm (a) is re-drawn and the 0-of-68 is NOT reused as its baseline.** That
figure was measured across two templates, neither of which is the one now in
force - the retired paragraph plus one repaired clause. Comparing against it
would compare against a template that never shipped.

---

## 3. THE SIZING, STATED BEFORE THE NUMBER

**This design is sized for an effect of roughly 20 percent or larger. It would
miss a real 5 percent effect.**

Against a current post-rejection rate of 0, 24 draws in arm (b) detect a true
rate of 20% or more comfortably and a true rate near 5% not at all. **A 5%
recovery is not worth acting on**, which is why the design is sized here rather
than larger.

**Therefore: a null in arm (b) is evidence of no LARGE effect. It is not proof
of absence, and it may not be reported as one.**

That sentence is written now, before the data, precisely so it cannot be added
afterwards as a hedge or dropped afterwards as an inconvenience.

---

## 4. What each outcome means, decided in advance

**IF ARM (b) RECOVERS GROUPED EMISSIONS** - the guidance is the suppressor, and
the direction of the repair is to say LESS rather than to say something better.

> **Nothing is designed in the same pass.** The wording change becomes its own
> decision with its own measurement. The reverted rewrite is the lesson: a
> well-argued edit with no measured effect still does not ship.

**IF ARM (b) IS ALSO ZERO** - the guidance is not the suppressor, and the
sentence to write plainly is:

> **No wording change to that paragraph fixes this, and every remaining edit to
> it is off the table.**

That is the more valuable outcome, and it is worth more than a positive result
because it closes a category of cheap-looking work that has already consumed one
full rewrite. It does NOT say the loop is unfixable - it says the fix is not in
that paragraph. The candidate that survives is a subtraction one layer up
(§8.4 of the findings document), and the gate-side reading of finding 2 (G4)
survives too.

**IF THE TWO ARMS DIFFER IN A DIRECTION NOBODY PREDICTED** - report it as
observed and do not retrofit a mechanism.

---

## 5. Scope, cost, and the stopping rule

| | arm (a) | arm (b) | calls |
|---|---:|---:|---:|
| scenario A (smoke run-02 r3) | 14 | 14 | 28 |
| scenario B (pilot run-02 r2) | 10 | 10 | 20 |
| **total** | | | **48** |

One model call per run - the probe seeds from a recorded rejection, so each run
is a single post-rejection draw. Scenario C is excluded: it is a `per_event`
clause, it has nothing to group, and it already returned a clean null in both
previously tested arms.

**Ceiling $1.80, checked BEFORE each call.** Rates measured in the previous run
and not recalled: post-rejection calls mean **$0.0136**, median $0.0128, range
$0.0079-$0.0306; first draws that emitted the grouped rule mean **$0.0556**; the
widest single call seen anywhere in this work about **$0.11**. Expected
**$0.65-$1.30**. Arm (b) succeeding is the EXPENSIVE outcome, because the spread
is thinking tokens.

**If the ceiling is reached, stop and report what is in hand.** A truncated arm
(b) that is already producing grouped rules has answered the question.

---

## 6. What is recorded regardless of outcome

- Every emission verbatim, and the shape classification beside it.
- Benign and near-miss floors, and the CLOSES/NO_OP verdict, from the same
  instrument as the 18-of-31 measurement.
- **Thinking tokens per call**, against the §8.1 baseline: first draws on the
  aggregate clause ran ~17-20k, post-rejection ~7.4-8k, and the `per_event`
  clause showed no collapse at all. If arm (b) restores the token count without
  restoring the rule, or the reverse, that is a finding either way.
- Actual spend from `crucible.armorer.client.estimate_cost`, stated as **a
  token-count estimate and not a billed figure**.

## 7. What this cannot answer

- **The previous-patch arm is deliberately out.** Eric's question is live and it
  is not first: it is the only candidate needing a ruling, §5 is evidence
  against it, and it confounds two variables this probe separates first.
- One clause, one target agent, one model, two rounds that share a clause and a
  policy state. **The two aggregate scenarios are a replication, not two
  independent observations.**
- Every verdict is a REPLAY of recorded calls, never a re-attack.
