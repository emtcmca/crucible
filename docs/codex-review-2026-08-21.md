# The Codex review, mapped against what CRUCIBLE actually is

**Date:** 2026-08-21 (Day 2)
**Source:** an outside model given a 60-second verbal description of CRUCIBLE and asked what
to add to impress the judges. It had not seen the repo, the specs, or a single ruling.
**Status:** coordinator's disposition. Three items adopted, one adopted with a hard
constraint, the rest already exist or are refused with a reason.

---

## The one-paragraph verdict

The review is good, and most of it describes CRUCIBLE back to itself. Sixteen distinct
suggestions: **nine already exist**, several in a stronger form than proposed; **three would
break a hash-lock** and cost the pre-registration claim, which is the strongest thing the
project has; **four are genuinely additive**, and three of those four are free.

The single most useful thing in the review is not a feature. It is that the reviewer had read
the judging rubric, and we had not written our submission against it.

---

## Already there, and stronger

### The Arbiter — separate offense from judgment

Proposed: a dedicated agent that watches raw telemetry and independently rules on whether a
claimed exploit really happened, so the attacker cannot grade its own homework.

CRUCIBLE already has this, and it is **not an agent**. The TRIPWIRE is pure code. It records
what the target actually called, and it scores the Objective Set independently of the policy.

That difference is the whole point. Codex's Arbiter is another language model, and a language
model that adjudicates can hallucinate a verdict exactly the way the attacker it is checking
can hallucinate a success. Swapping one fallible judge for another is not separation of
powers. Ours is deterministic, and the blindness is enforced in **IAM**, not in a prompt: the
Armorer's service account cannot read the evidence bucket, and the 403 is captured in
`docs/proof/armorer-403.txt` with a positive control that proves the probe can fail.

There is a second layer Codex did not reach for. The CORONER writes autopsies and **cannot
propose fixes**, because the ARMORER's input is an enumerated projection with no free-text
field. Detection and remediation are split structurally, not by instruction.

**Disposition: no change. Say it louder in the README.**

### Chain Hunter — attack the composition, not the step

Proposed: hunt for chains where no single step violates policy but the composition does.

That is attack families **F5** (chained-call escalation) and **F7** (quantitative
decomposition), and the grammar was grown to hold them: three episode-scoped predicate forms
(`preceded_by`, `episode_sum`, `arg <cmp> episode.<field>`) exist for no other reason.
`episode.*` is frozen before the first user turn and unwritable after, so an in-episode turn
cannot move the ground the predicate stands on.

**Disposition: already built.**

### The target fights back / Crucible attacks its own fix / patch-then-re-attack

Proposed as three separate additions. All three are the loop:

    attack -> tripwire records -> Coroner autopsies -> Armorer patches
      -> Warden and gate promote or roll back -> next round

Round cap 6, six attacks per round, convergence at three consecutive dry rounds. The
adversary faces a target whose policy is tighter than it was last round, every round.

**Disposition: already built. This is the product.**

### Attack budgets

Proposed: constrain the run so the orchestrator has to choose between exploring and
exploiting.

`BUDGET_GOVERNOR` (`architecture-spec.md:242`), a $160 hard **spend cap** rather than a
billing alert, a round cap of 6, and six attacks per round.

**Disposition: already built.**

### Measure the fix rather than declaring victory

Proposed: run benign control tasks before and after so the security/usability tradeoff is
visible, e.g. attack success 39.5% to 3.9% against legitimate task success 97% to 94%.

CRUCIBLE has the benign floor (24/24), the near-miss floor (12/12, which is what proves 24/24
is not vacuous), and nine known-bad fixtures the suite must always fail.

**And this is where the review's own metric fails a test we already ran.** Ruling 37, our
headline finding: an over-blocking `require_approval` rule passes **every** gate. It blocks 6
of 7 emissions, the oracle approves, the benign pass rate reads 24/24, and G3 promotes it.
Under Codex's table that rule scores "legitimate task success 97% to 94%" and looks like a
clean win. It is not a clean win; it is the degenerate case, and we only caught it by fixing
the ruler: BPR now permanently carries `benign_passes_requiring_approval`, so a benign task
that only passed because a human was made to rubber-stamp it can never again be counted as
having passed cleanly.

**Disposition: already built, and the proposed version would have scored our own worst
finding as a pass.**

### CI/CD for agents — the adversarial quality gate

Proposed as a roadmap item.

It is the current positioning. CRUCIBLE is a **pre-deployment hardening harness**; the WARDEN
and the promotion gate are the quality gate, and they are pure code.

**Disposition: already built — but see "Adopted" below, because the *words* are better than
ours.**

---

## Refused, with the reason

These are refused because of what CRUCIBLE is measuring, not because they are bad ideas. Each
would be defensible in a different project.

### Adversarial evolution — attacks that mutate across generations

The corpus is **frozen and hashed at D5**, together with `derived_schema_hash`. That freeze is
one of five hash-locks and it is the reason any number this project prints is worth reading:
the held-out attacks demonstrably existed before the first patch was written, and the sealed
family's commitment (`2cde0250de00e692`) is already public so a stranger can check it after
the reveal.

A corpus that mutates during the run has no hash. With no hash there is no pre-registration,
and without pre-registration the transfer number is an anecdote.

Note the conflation in the proposal. CRUCIBLE **does** generate attacks live — six per round,
authored by the red agent against a target whose policy is moving. What is frozen is the
**measurement instrument**, not the pressure. Those are different objects and the review
treats them as one.

**Disposition: refused. One sentence in the README's "what this does not do", because
refusing it deliberately is more interesting than not having thought of it.**

### Attack Novelty Score and attack lineage

Same objection, one level down: a novelty score is a number computed against a reference
population, and our reference population is frozen on purpose. It would also be a
model-produced score with no independent check, in a project whose entire thesis is that a
check which cannot fail is not a check.

**Disposition: refused.**

### Live attack-surface discovery ("Crucible has never seen this agent, watch it discover")

There is nothing to discover, and that is deliberate. The capability manifest maps every tool
the target exposes to one of six capability classes plus an `UNCLASSIFIED` sentinel, and
`manifest_hash` is frozen at D3. A tool nobody classified is **always allowed** by the policy
(no rule can select `UNCLASSIFIED`), the engine fails open there on purpose, and the run
reports partial coverage **with the unmapped tools named**.

Discovery-by-model would replace a frozen, checkable input with a probabilistic one, in the
exact place where a silent miss is invisible.

The unseen-target beat we ship instead is Day 9 and it is honest about its own weakness: hand
CRUCIBLE a third-party agent, classify its tools on camera in about 40 seconds, show one tool
coming back `UNCLASSIFIED` and name it, then run the existing corpus against it. The number
on screen is **"attacks written for this agent: 0."**

**Disposition: refused as proposed. The frozen-manifest version is stronger and already
scheduled.**

---

## Adopted

### 1. The attack surface graph — as a render over frozen data, not as live discovery

**This is the best idea in the review** and it is nearly free, because we already hold both
halves of the graph and never drew it.

- **Nodes** are already in the frozen capability manifest: eight tools, six capability
  classes, plus `UNCLASSIFIED`.
- **Edges** are already in the tripwire's recorded call sequences and the `episode.*` context:
  which tool followed which, which capability class a call carried, where an approval gate
  sat.

So the artifact is a **script that renders frozen evidence**, not a new component. It touches
no hash-lock, because a view over a hashed input does not change the input.

What it buys: the single hardest thing to convey about this project in four minutes is that
the learned rules are **class-bound** rather than string-matched. A picture where the same
rule edge lights up across three tools that share a capability class shows that in two seconds
and no paragraph does.

**Build it D10, off the evidence bundle. Colour by policy@v0 versus policy@vFinal: the edges
that changed are the run's result.**

### 2. The rubric check

The review states the judging split as 40% Innovation and Operational Utility, 30%
Architectural Discipline, 30% Demo and Production Readiness, plus a separate $5K Best
Architectural Design prize.

We have never written the submission against those weights. **Verify the numbers against the
live hackathon page before acting on them** — they come from a model summarising a web page
and this project does not take counts on trust. If they hold, the 30% architectural-discipline
criterion and the separate architecture prize are where CRUCIBLE is disproportionately strong
and where the current README does not lead.

**Action: verify the rubric, then structure the README and the demo around it.**

### 3. The framing — "the adversarial quality gate every autonomous agent has to survive
before production"

This is better external copy than anything currently in the repo, and it costs nothing. It
also correctly puts the emphasis on **pre-deployment**, which is what separates CRUCIBLE from
a scanner someone runs once after the fact.

Keep the discipline that comes with it: it is a *harness*, and the honest claim is about one
target, one corpus, k=1, with the SEP-BY split attached.

**Action: adopt into the README opening and the Devpost tagline.**

### 4. Demo staging — show the failures before the success

Free, and correct. The current 4-minute script should visibly run attacks that **fail** before
one lands. A reel where everything works reads as a scripted tour; a reel where attacks 14 and
15 fail and 16 gets through reads as a system under real pressure.

**Action: fold into the D10 recording, no code change.**

---

## Adopted with a hard constraint: the Crucible Score

Proposed: a single 0-100 score with per-domain breakdown, where every deduction points to a
reproducible attack trace, plus a machine-readable manifest and a before/after diff (63 to
91).

The evidence-backed part is right and we already do it: every number in the evidence bundle
links to its run directory, and the run manifest is machine-readable and hashed.

**The single number is the problem.** `measurement-spec.md` §8.1 is a headline board of
eleven rows, and several of them exist specifically to stop a good-looking summary from hiding
a bad run:

- the **SEP-BY split**, printed next to every ASR and BPR figure permanently, because a suite
  the approval oracle separates produces *identical* headline numbers to one the policy
  separates, and that row is the only thing that tells them apart;
- **benign capability retained per attack blocked**, which is the real falsifier for the
  claim that the rules generalise;
- the **k=1 single-sample label**, which says out loud that there is no stability estimate;
- **verb usage per family**, which forces us to say so if `constrain_arg` never appears.

Collapsing those into "CRUCIBLE SCORE: 63" deletes exactly the information the project exists
to preserve. It is the same failure as a confidence number with no per-dimension breakdown.

**Disposition: adopt the *evidence-backed deduction* format — a finding card with attack path,
expected, observed, result, severity, reproduce command, remediation. Refuse the rollup
number.** If a single figure is needed for a thumbnail, use the one honest pair we will
actually have: **breached_at_v0 versus breached_at_vFinal on the sealed family**, with its
labels attached.

---

## Partly there: the hypothesis ledger

Proposed: Observation, Hypothesis, Experiment, Evidence, Conclusion — and a report line like
"14 hypotheses generated, 9 falsified, 3 inconclusive, 2 confirmed."

We have this and call it something else. The separability worksheet is **27 pairs**, and each
pair is a written hypothesis in real grammar: *this exact rule blocks this attack and passes
this near-miss.* A pair with no such rule is declared **unlearnable** and cut. The SEP-BY
split then reports how each surviving pair actually separates: **21 by the policy, 3 by the
approval oracle, 3 cut.**

That is a falsification ledger. It is just not presented as one.

**Action: relabel in the README. Free, and it makes the most rigorous thing in the project
legible to someone reading for 90 seconds.**

---

## Not for this hackathon

**The Crucible Corpus / Attack Genome** — harvesting engagements into a growing proprietary
corpus. Real idea, wrong direction for us right now: our corpus is authored rather than
harvested precisely so it is reproducible and hashable. Post-hackathon.

---

## Scoreboard

| # | Codex proposal | Disposition |
|---|---|---|
| 1 | Autonomous attack lifecycle | Exists; ours mutates the defense, not the attack |
| 2 | Agent attack surface graph | **ADOPT** as a render over frozen data (D10) |
| 3 | Adversarial evolution / mutating attacks | **REFUSED** — breaks `corpus_hash` |
| 4 | Crucible Score | **ADOPT the finding cards, REFUSE the rollup number** |
| 5 | Unknown-agent demo | Exists as D9, and ours is hash-backed rather than asserted |
| 6 | Separate offense from judgment | Exists, in pure code and in IAM |
| 7 | Chain Hunter | Exists as F5 and F7 |
| 8 | Adversarial memory | Partly — round-over-round feedback exists, belief state is implicit |
| 9 | Attack novelty score | **REFUSED** — scored against a deliberately frozen population |
| 10 | Scientific method / hypotheses | Exists as the 27-pair worksheet. **Relabel** |
| 11 | Attack budgets | Exists — `BUDGET_GOVERNOR`, $160 cap, round cap 6 |
| 12 | Target fights back | Exists; it is the loop |
| 13 | Propose patches, attack the fix | Exists; it is the loop |
| 14 | Measure the fix | Exists, and stronger — see ruling 37 |
| 15 | Attack genome corpus | Post-hackathon |
| 16 | CI/CD framing | **ADOPT the words** |

**Net new build work: one render script.** Everything else adopted is copy, staging, or a
relabel.
