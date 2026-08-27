# What this project actually contributes

**The hardening result is not the contribution. The apparatus that decides
whether the hardening result may be believed is.** This document says so
plainly, because a submission that leads with a modest efficacy number and
buries the measurement work has led with its weakest material.

---

## 1. The thesis, in one sentence

**A hardening tool that cannot tell you which of its own fixes worked is worth
much less than one that can.**

We built that check, pointed it at our own output, and **19 of 32 promoted rules
had closed nothing.** They were well-formed, they passed a benign-traffic
check, they shipped — and replayed against the very calls that caused the
breach, they left the breach in place. Nobody would have known.

That finding is not about our agent. It is about the shape of the tooling:
**the gate was asking whether a rule was well-formed and harmless, and never
whether it was a fix.** A rule that blocks nothing passes both of those easily.

---

## 2. What had to exist before that sentence could be said

Answering "did the fix work" is not a feature. It is a chain of decisions, and
each link is a place the answer can be silently faked.

**Record what the agent did, not what it said.** The component that decides
whether a breach occurred is pure code with no model in it, and it watches tool
events. A model asked to grade its own transcript is not evidence.

**Replay the fix against the calls that caused the breach.** Two criteria, and
they ask different questions: *originating-breach closure* asks whether this
candidate closes the one breach it was written for; *attack reduction* asks
whether it blocks at least three attacks it did not block before, re-opening
none. A rule can pass either and fail the other, and both are recorded.

**Make the policy language incapable of widening the blast radius.** Three
verbs — `deny`, `require_approval`, `constrain_arg`. **There is no `allow`
verb**, so no sequence of patches can grant a permission. Monotonicity by
construction rather than by review.

**Decide what may be quoted, mechanically.** An offline reader validates every
evidence bundle and refuses the ones that are not readable. **A figure from a
refused bundle is not reported.** Every aggregate prints its acceptance count
beside the number: not *"median across ten runs"* but *"median across ten runs,
of which the reader accepts four."*

**Put the reader itself under test.** Nine deliberately damaged bundles plus a
control, each asserting both the defect code and its class, with proofs that
the suite catches a reader that accepts everything **and** one that rejects
everything. Coverage is printed every run and never asserted complete.

**Publish targets before running.** The v0 and vFinal targets are in a spec
written before any run existed, so "we met the target" is checkable rather than
retrofitted.

**Publish the corrections too.** `AUDIT.md` carries every withdrawn claim,
including a headline attack-success figure withdrawn on 2026-08-27 because it
was computed over ten bundles the reader refuses.

---

## 3. The finding that generalizes past this project

**A check that cannot fail on empty input is not measuring anything.**

We hit that defect **four times in one week**, and treated the first three as
separate bugs before seeing the shape:

| | what it looked like |
|---|---|
| an enum value | a gate decision the schema could not express, so the branch never ran |
| an efficacy gate | sat ABSENT while the contract said it was binding |
| a `null` in one field | voided a twenty-run batch, silently, all exiting 0 |
| **an empty run** | **the reader returned ACCEPTS with 18 of 18 checks OK** — a run that halted before its first episode, reported `RUN_INVALID`, and exited 2 |

The last one is the cleanest: no check was broken. A run with zero episodes has
no exclusions to breach a ceiling, no breaches to miss an autopsy, nothing for
any per-episode check to object to. **Eighteen checks passed and not one of them
ran.**

The rule that came out of it: **ask every check what it returns on empty input,
and if the answer is "passes", give it a floor.** `offenders == []` is satisfied
just as well by looking nowhere.

---

## 4. What this build measured, including what it could not do

Reader accepts **17 of 17** bundles in this pool.

**It reliably finds breaches, and it can only fix one kind.**

| | |
|---|---|
| invariants where a fix was accepted | **1** — `inv_pii_read_of_a_nonsubject_account`, 9 promotions |
| invariants where every fix was refused | **3** — 18 refused patch attempts |
| runs that found breaches and shipped a rule | 9 |
| runs that found breaches and shipped nothing | 4 |
| runs that attacked and found nothing | 4 |

The three it cannot close are named, glossed in plain English, and shipped to
the user as open findings by `scripts/unresolved-findings.py` — **repeated
mutation on one subject** (12 refusals), **escalation below the required queue**
(4), and **an account identifier leaving the boundary** (2).

**The refusals are diagnostic, not mysterious.** Eleven of the twelve
repeated-mutation refusals are the same shape: the proposed rule tests
`derived.episode_count_same_subject >= 4` against traces that never reach 4, so
**the rule can never fire.** It passes a benign check trivially, for the same
reason. That is a specific, fixable defect in how the patch author picks
thresholds, and it is on the record instead of hidden inside an aggregate.

**The efficacy number, with its limits attached.** Where a rule shipped, attack
success fell from 13.3% to 3.2%. The pre-registered v0 target was 68% and the
observed v0 rate is **11.3%** — the design assumed a far weaker agent than the
one we built, so the entire gap available to demonstrate in is about eleven
points, not sixty-two. Single-sample, k=1, one target agent.

---

## 5. Why the negative results are the deliverable

A person hardening their own agent needs three things from a run, and only one
of them is "here is your policy":

1. **What it found and fixed.** A policy file.
2. **What it found and could NOT fix.** A work item, with the breach, the
   attempted rule, and the machine-checked reason the gate refused it.
3. **Where it attacked and found nothing.** Evidence of coverage. Four runs
   swept three rounds each and crossed no invariant; a dry sweep is a result,
   not an absence of one.

**Most tooling reports only the first.** That hands you a policy and an unearned
feeling of safety. The second is the actionable half and it is the half this
project makes a first-class artifact.

---

## 6. What this is the foundation for

Everything above is infrastructure that outlives the eleven days it was built
in. The obvious next steps are already named by the findings themselves:

- **Close the three invariant classes the patch language cannot express.** The
  threshold-selection defect is specific and diagnosed; the grouping-key work
  already landed and was necessary but not sufficient.
- **Power the degeneracy census.** It covers all 50 corpus instances but no
  instance reaches the denominator that would let a regression be caught.
- **Fix the ruler, not the number.** `benign_passes_requiring_approval` is not
  built, so a perfect benign score cannot yet be distinguished from a rule that
  over-blocks and is rubber-stamped by an approval oracle. **A rule that
  over-blocks passes every gate we have.**
- **Give C6 a field for `RUN_INVALID`.** The evidence bundle cannot currently
  record that its own run was invalid; emptiness is a proxy for it.
- **More than one target agent, and k > 1.** Everything except the foreign-agent
  probe is one agent, single-sample.

---

## 7. The boundary

Eleven days, one person, one target agent. No users, no downloads, no adoption.
Not reviewed, endorsed, or responded to by Google in any way. Not
production-ready. Live-run evidence is gitignored, so it is reproducible from
the harness rather than publicly verifiable. Every rate here is a replay of
recorded calls: it answers *would this rule have stopped these calls*, never
*could an attacker find another way in*.
