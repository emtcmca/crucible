# Build list — scored work, ordered by points per hour

**Companion to `docs/contest/CONTEST.md`**, which holds the rules, the weights and
the prizes. This file holds only *what to build and in what order*. Every item
names the criterion it scores against, so an item that cannot name one gets cut.

Opened 2026-08-21 (Day 2). Sources: the contest rules, and the Codex review
dispositioned in `docs/codex-review-2026-08-21.md`.

Legend — **[S1]** Stage One pass/fail · **[40]** innovation · **[30A]**
architectural discipline · **[30D]** demo and documentation · **[B]** Stage Three
bonus.

---

## Tier 0 — pass/fail. Nothing else matters if these are missing.

| # | Item | Scores | State |
|---|---|---|---|
| T0-1 | **Architecture diagram** in the repo — Gemini → backend → database → frontend, plus the blindness boundaries | **[S1] [30D]** | does not exist |
| T0-2 | **First Cloud Run deploy**, with console and Trace Explorer captures into `docs/proof/` | **[S1] [30D]** | Day 2 item, not done |
| T0-3 | **Visible Google Cloud proof in the video** — the backend running, on camera | **[S1] [30D]** | blocked on T0-2 |
| T0-4 | **`README.md` spin-up instructions**, verified by a cold clone on D10 | **[S1] [30D]** | not written |
| T0-5 | **Findings and learnings** section in the submission text | **[S1]** | Project Story posted; findings owed |
| T0-6 | **The 4-minute video**, public, English | **[S1] [30D]** | script exists, not recorded |

**T0-2 is the one that is slipping.** `execution-spec` put the first deploy on Day
2 *specifically* to de-risk the most demo-fatal unknown eight days early.
Deferring it re-arms exactly the risk the schedule moved it to defuse — and it now
also blocks a pass/fail requirement.

---

## Tier 1 — free points. None of these depend on the loop working.

| # | Item | Scores | Cost |
|---|---|---|---|
| T1-1 | **Publish a build write-up** on a public platform, stating in the text that it was created for this hackathon | **[B] +0.2** | an afternoon |
| T1-2 | **Public social post** with `#AllThingsAgenticHackathon` | **[B] +0.2** | minutes |
| T1-3 | **Gemma**, already planned for corpus generation (ADR-0009) — make sure it actually ships and is named in the submission | **[B] +0.2** | already scheduled |
| T1-4 | **A second additional Google model.** Cheapest honest candidate: `gemini-embedding-001` for near-duplicate detection across generated attacks, which is a real need and not decoration | **[B] +0.2** | small |
| T1-5 | **A third.** Only if it does real work. **Do not bolt on Veo or Lyria to farm 0.2** — a decorative integration reads as decorative and costs credibility on the 30% criteria | **[B] +0.2** | judgment call |

**Up to a full point on a five-point scale.** T1-1 and T1-2 alone are +0.4 for
about an afternoon, and Eric already writes publicly.

---

## Tier 2 — the highest-leverage scoring work

### T2-1 · The attack surface graph, as a render over frozen data · **[30A] [30D] [40]**

Adopted from the Codex review; the reasoning is in
`docs/codex-review-2026-08-21.md` §Adopted.

Both halves already exist and were never drawn. **Nodes** are the frozen
capability manifest: eight tools, six capability classes, the `UNCLASSIFIED`
sentinel. **Edges** are the tripwire's recorded call sequences and the `episode.*`
context — which tool followed which, carrying which class, and where an approval
gate sat.

So this is a **script that renders hashed evidence**, not a new component, and it
touches no hash-lock: a view over a frozen input does not change the input.

It also solves the single hardest thing to convey in four minutes — that the
learned rules are **class-bound rather than string-matched**. Colour edges by
`policy@v0` versus `policy@vFinal`; **the edges that changed are the run's result.**

Build D10, off the evidence bundle. **Refused:** live model-driven discovery of the
graph. There is nothing to discover, deliberately, and replacing a frozen checkable
input with a probabilistic one in the exact place a silent miss is invisible would
trade the strongest thing the project has for a demo flourish.

### T2-2 · Finding cards with reproduce commands · **[30D] [40]**

Adopted from the Codex review, without its rollup number. Every deduction points
to a reproducible trace: attack path, expected, observed, result, severity,
**reproduce command**, remediation.

**The single Crucible Score is refused.** `measurement-spec.md` §8.1 is an
eleven-row board and several rows exist precisely to stop a good-looking summary
from hiding a bad run — the SEP-BY split, benign capability retained per attack
blocked, the k=1 label, verb usage per family. Collapsing them into "63/100"
deletes the information the project exists to preserve. If a single figure is
needed for a thumbnail, use the one honest pair we will have:
**`breached_at_v0` vs `breached_at_vFinal` on the sealed family**, labels attached.

### T2-3 · Relabel the 27-pair worksheet as a hypothesis ledger · **[30A]**

Free. We already report "21 pairs separated by the policy, 3 by the oracle, 3
cut." That **is** "hypotheses tested, falsified, confirmed" — we just never called
it that, so the most rigorous artifact in the project is invisible to a judge
reading for ninety seconds.

### T2-4 · Answer the failure-tolerance criterion out loud · **[30A]**

The track's own words: *"how does the system recover if a worker agent loops or
returns a hallucination?"*

That is the tripwire (a pure-code witness rather than the agent's own account),
the Warden, the promotion gate's read-back-from-bytes, the two-rejections halt,
and `TARGET_FAULT` being removed from the denominator. **Every part exists and
none of it is written down as an answer to this question.** One README section.

### T2-5 · The "unlikely hero" · **[40]**

A named Stage Two sub-criterion for this track, and we currently score zero on it
because no persona exists anywhere in the project.

The honest candidate is not a security engineer — it is the **operations lead who
inherits an agent someone else built** and has to decide whether it is safe to give
it the company card. That is a real role, it is outside standard corporate
security, and it is genuinely who this tool serves.

**Needs Eric's call.** A persona invented to satisfy a rubric reads exactly like a
persona invented to satisfy a rubric.

### T2-6 · Meet the track description head-on · **[S1] [40]**

See `CONTEST.md` §3. CRUCIBLE is not a "scalable network of institutional agents"
maintaining "context across weeks of asynchronous operations." Pretending otherwise
is worse than addressing it. **Eric's call**, and it is a writing problem rather
than a building one.

---

## Tier 3 — refused, and worth saying why

Refusing these deliberately is itself a **[30A]** point, and one README paragraph
turns them from absences into decisions.

| Codex proposal | Why refused |
|---|---|
| Mutating attacks / adversarial evolution | The corpus is frozen and hashed at D5. A corpus that mutates mid-run has no hash; with no hash there is no pre-registration; without pre-registration the transfer number is an anecdote. Note the conflation in the proposal: attacks **are** generated live, six per round. What is frozen is the *measurement instrument*, not the pressure |
| Attack novelty scores | A score against a reference population we froze on purpose, computed by a model, with no independent check |
| An LLM "Arbiter" | Ours is the tripwire and it is **pure code**. A model that adjudicates hallucinates a verdict the same way the attacker hallucinates a success. Swapping one fallible judge for another is not a separation of powers |
| Live attack-surface discovery | Nothing to discover, deliberately — see T2-1 |
| A rolled-up Crucible Score | See T2-2 |
| Attack genome / harvested corpus | Post-hackathon. Ours is authored rather than harvested so it is reproducible and hashable |

---

## Tier 4 — open threads that are not scored but block scored work

- **D5 corpus freeze** — hash the corpus and Part B, upload sealed to GCS, hash into the D5 post. **Must land before the first patch is written.**
- **The first real loop run.** Compute-heavy, and it produces every number.
- **D2 gate-rule freeze** — held pending GX5; GX5 is now landed, so this is unblocked.
- **`corpus/C6-reach` branch** — four instances that make `CAP_INVOKES_AGENT` reachable, parked because they break two frozen counts. Needs a ruling: retire two F5 attacks and two benigns, or amend the counts.
- **`r_new3` fails validator V4** — names `status_to` values Part A does not declare. Both P03 instances are already inside the declared enum, so it is a rule rewrite with no corpus change.
- **`ALLOW` / `allow`** — `engine.py:165` compares `!= "ALLOW"`; all 269 authored trace events spell `"allow"`. Any prefix reaching the engine without `corpus/model.py::canonical_decision` makes every `preceded_by` read false and takes P11 through P14 with it.
- **ADR-0010 vs "unedited, live execution"** — see `CONTEST.md` §4.
- **`ORD-13` / `ORD-14`** were authored after Eric's review pass, so "the benign set was reviewed" is not true of the set as it stands.
