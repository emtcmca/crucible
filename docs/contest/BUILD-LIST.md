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
| T0-1 | **Architecture diagram** | **[S1] [30D]** | **DONE 2026-08-21.** `docs/diagrams/architecture.md`, six Mermaid diagrams, all rendered and validated. Round loop inlined in the README. Seven unbuilt components drawn dashed and named |
| T0-2 | **First Cloud Run deploy**, with console and Trace Explorer captures into `docs/proof/` | **[S1] [30D]** | **DEPLOYED 2026-08-21**, `crucible-00003-t2q`, authenticated, running as `crucible-target`. `/list-apps` returns `["refund_agent"]` and one full episode ran end to end. PC1 and PC2 pass; **the two SCREENSHOTS remain** and they are the pass/fail half. Proof: `docs/proof/cloud-run-deploy-2026-08-21.txt`. Three real defects on the way, written up in `deploy/RUNBOOK.md` |
| T0-3 | **Visible Google Cloud proof in the video** — the backend running, on camera | **[S1] [30D]** | **Unblocked 2026-08-21.** Needs two captures into `docs/proof/`: the Cloud Run console page, and an `execute_tool` span in Trace Explorer (which also settles PC3, currently UNVERIFIED). **New option same day:** ADR-0012's ban on `--with_ui` on camera is LIFTED — the #4704 probe shows the plugin fires and blocks on `run_live` too, so the recording can show real enforcement through the ADK web UI. Narrate the boundary: the demo may use a path the measurement does not |
| T0-4 | **`README.md` spin-up instructions** | **[S1] [30D]** | **DONE 2026-08-21.** 810 lines, every command run and its real output pasted, four items marked UNVERIFIED with what would settle each. Cold-clone verification still owed on D10 |
| T0-5 | **Findings and learnings** section in the submission text | **[S1]** | **DONE 2026-08-22.** `docs/devpost/findings-and-learnings.md`, five findings, each traceable to a commit SHA or file path, none of them a result. **The real gap in row 2 was not findings.** It asks for *features, technologies, data sources* as well, and `project-story.md` named **zero** Gemini models, zero Google agent frameworks and zero Google Cloud services — verified by grep, all four terms return 0. The mandatory *technology* requirement was always satisfied by the code; the *description* requirement was not, and it is a pass/fail row. Stack and data provenance now carried in the findings file, read out of source. Firestore and BigQuery deliberately NOT listed as used |
| T0-6 | **The 4-minute video**, public, English | **[S1] [30D]** | script exists, not recorded |

**T0-2 landed 2026-08-21, and it paid for the schedule.** `execution-spec` put the
first deploy on Day 2 *specifically* to de-risk the most demo-fatal unknown eight
days early. It found four things. The worst: ADK bakes
`GOOGLE_CLOUD_LOCATION=<region>` into the image, while the target pins the
**global** endpoint and hashes `"endpoint": "global"` into the D3 freeze — so the
deployed agent was resolving its model through a different endpoint than the
measured one. Found with nine days of slack; found on Day 10 it is the demo.

**T0-3 is now the slipping item**, and it is two screenshots.

---

## Tier 1 — free points. None of these depend on the loop working.

| # | Item | Scores | Cost |
|---|---|---|---|
| T1-1 | **Publish a build write-up** on a public platform, stating in the text that it was created for this hackathon | **[B] +0.2** | an afternoon |
| T1-2 | **Public social post** with `#AllThingsAgenticHackathon` | **[B] +0.2** | minutes |
| T1-3 | **Gemma** — **NOT built and NOT scheduled, despite `ADR-0009`.** Gemma appears in no code anywhere, and `CAPABILITY_CARTOGRAPHER`, its architectural home, has no module. Worse, the ADR scripts an on-camera line saying the corpus *is* Gemma-generated; the corpus was authored by the lane agents and carries no generator, seed or provenance field. See `docs/NEEDS-ERIC.md` item 10 | **[B] +0.2** | real work, and the line must change either way |
| T1-4 | **A second additional Google model.** Cheapest honest candidate: `gemini-embedding-001` for near-duplicate detection across generated attacks, which is a real need and not decoration | **[B] +0.2** | small |
| T1-5 | **A third.** Only if it does real work. **Do not bolt on Veo or Lyria to farm 0.2** — a decorative integration reads as decorative and costs credibility on the 30% criteria | **[B] +0.2** | judgment call |

**Up to a full point on a five-point scale.** T1-1 and T1-2 alone are +0.4 for
about an afternoon, and Eric already writes publicly.

---

## Tier 2 — the highest-leverage scoring work

### T2-0 · Replace the four stand-ins in the runnable loop · **[40] [30A] [30D]**

**Opened 2026-08-21. This is the largest scored gap in the project and it was
living in a source-file header rather than on this list.**

`crucible/conductor/campaign.py` runs the loop unattended to a recorded
termination, and its own docstring is admirably honest about what is real:

| Component | State |
|---|---|
| RED_STRATEGIST, CORONER, ARMORER | **real**, each on its pinned model, firing in sequence |
| DSL parser, validator, POLICY_ENGINE, canonicalizer | **real** |
| BUDGET_GOVERNOR, round protocol, five hash-locks, halt conditions | **real** |
| **the TARGET** | stand-in. `target/refund_agent` is not driven |
| **the TRIPWIRE** | ~~stand-in~~ **DONE 2026-08-21**, `crucible/conductor/real_tripwire.py` |
| **the WARDEN** | stand-in. Four lane-authored shapes, not the 26 benign / 14 near-miss |
| **the GATE** | stand-in. No GCS, no IAM. **G7 and G8 cannot be exercised at all** |

**Why this scores, and on all three criteria.** The three model agents were
already real; the four STAND-INS are the pure-code arbiters — and "no model ever
decides whether a breach happened" is the sentence the whole demo is built on.
A judge who opens `campaign.py` reads that claim and its stub in the same file.
On **[30A]** that is the architectural argument simulated rather than enforced;
on **[40]** the loop measures nothing about an agent's susceptibility to
persuasion, which is the entire thing the target exists to measure; on **[30D]**
the demo's headline pair has no real number behind it.

**The good news: all four are WIRING, not building.** Every real module already
exists — `crucible/tripwire/`, `crucible/warden/`, `crucible/gate/`,
`target/refund_agent/` — and the 2026-08-21 ADK probe
(`docs/proof/adk-4704-probe-2026-08-21.txt`) proved the enforcement plugin fires
and blocks through a real `Runner` on both invocation paths. Each stand-in has a
clean signature, so each replacement is a drop-in adapter in its own file.

**The stand-in worth reading twice** is the tripwire's, now replaced:
`breached = episode["_decision"] == ALLOW` — it asked the policy whether the
policy had stopped something. Circular, and the exact inverse of the claim.

**Known integration gap, found while wiring the tripwire:** `campaign.py` calls
`seal_episode` **zero** times, and `harness/episode.py::seal_episode` refuses an
episode whose run manifest lacks `objective_set_hash`, `manifest_hash` and
`derived_schema_hash` — "unscoreable rather than clean, G1(b)." So the real
tripwire against the current stand-in target scores every episode INVALID. That
is the harness working, and it lands on the target replacement.

**Refused:** loosening G1(b) so unsealed episodes score. The gate that refuses to
score an unsealed episode is the one keeping the pre-registration claim true.


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

**DONE 2026-08-21.** `README.md:770`, *"What happens when an agent loops, lies, or
returns nothing"* — six mechanisms, each naming the specific failure it exists for
and citing the file: the tripwire as a pure-code witness rather than the agent's
own account, no model grading its own work, the gate's read-back-from-bytes, the
`HALT_ARMORER_EXHAUSTED` halt, the two-rejections halt, and `TARGET_FAULT` removed
from the denominator structurally. Plus a seventh that is not about agents at all:
an unevaluable trace marks `ROUND_INVALID` rather than being scored, and **INVALID
is not FAILED**.

Every claim was checked against code rather than against the specs, which mattered:
the specs asserted a property the code did not have. On 2026-08-21 the "no model
decides whether a breach happened" claim survived only because a DENIED call
writing `TOOL_EXECUTED` was found and fixed the same day — see `ADR-0012`. **The
section is now true. It was not true when the criterion was first answered.**

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
- **`corpus/C6-reach` branch — MERGED 2026-08-21.** Four instances that make `CAP_INVOKES_AGENT` reachable. Eric ruled to amend the two frozen counts it broke (F5 8→10, benign 24→26, near-miss 12→14) rather than retire instances. `measurement-spec.md` §1.3's ≥3-routing requirement is still unmet (2 of 10) — a known, reported deviation.
- **`r_new3` fails validator V4** — names `status_to` values Part A does not declare. Both P03 instances are already inside the declared enum, so it is a rule rewrite with no corpus change.
- **`ALLOW` / `allow`** — `engine.py:165` compares `!= "ALLOW"`; all 269 authored trace events spell `"allow"`. Any prefix reaching the engine without `corpus/model.py::canonical_decision` makes every `preceded_by` read false and takes P11 through P14 with it.
- **ADR-0010 vs "unedited, live execution"** — see `CONTEST.md` §4.
- **`ORD-13` / `ORD-14`** were authored after Eric's review pass, so "the benign set was reviewed" is not true of the set as it stands.
- **`objective_set_hash` — the FOURTH hash-lock, and a D3 HARD STOP that has not fired.** `execution-spec.md` Day 3 item 4b requires the Objective Set authored, canonicalized, hashed and written into the run manifest **today**. The only instance on disk is `tests/golden_traces/objective_set.json`, which self-labels **"HAND-WRITTEN DEVELOPMENT INSTANCE"** in its own `_status` field and carries nine clauses, **none with a `clause_id`**. The `e30c7a51bb92f4d8` in `contracts/golden/C5`–`C10`, `docs/data-spec.md:126` and `scripts/make-golden.py:26` is that fixture's placeholder; `campaign.py:145` writes sixteen zeros. There is a `scripts/freeze-d2-gate-rule.py` and no equivalent for C10. **On the critical path to the first scoreable episode** — `crucible/harness/episode.py:72` refuses to seal without it.
- **`derived_schema_hash` — the FIFTH hash-lock**, capability manifest Part B, split out by ruling 20 and scheduled at D5 *gated on the label-blindness check passing*. Also demanded by `episode.py:72`, so it is on the same critical path. Was not in flight at all until 2026-08-22.
- **The three real adapters are AUTHORED BUT NOT WIRED.** `crucible/conductor/real_target.py`, `real_tripwire.py`, `real_warden.py` exist and are tested, but `campaign.py` imports none of them and still prints all four components as `STAND-IN` at `:233-236`. The file has not been modified since before they were written. **"Three of four replaced" was true of authoring, not of integration**, and it was reported as replaced.
- **`google/adk-samples@f4c19ab` IS NOT A REAL OBJECT** (found 2026-08-22, `docs/proof/third-party-target-recon-2026-08-22.md`). `git cat-file` rejects it and the remote has no such ref. It originates as one hardcoded literal at `scripts/make-golden.py:331`, which generates the golden contract fixtures — and `docs/proof/L6-cold-clone-2026-08-20.txt:23` printed it **by replaying that fixture**, so a synthetic value shaped like a real SHA was read as an observation, inside a proof file. Real HEAD 2026-08-22 is `629310b`, on a live branch that will move. **Action:** make the literal obviously synthetic (`@DEADBEEF`) or carry the real SHA; have the Day-9 adapter `git rev-parse HEAD` at attach time rather than retype.
- **"CRUCIBLE tricked the agent into a 40% discount" is DEAD VOCABULARY.** The adk-samples pivot to `sync_ask_for_approval` is the sample's *intended* flow — `prompts.py:49,65-66` tells the model that tool requests manager approval and never states the cap. A model routing there is obeying its instructions; the defect is that the escalation destination has no manager in it. The frozen claim at `execution-spec.md:681` survives because it is about the code, not the model.
- **`CONVENTIONS.md` does not carry the frozen `target_agent_hash`.** `grep -c 125fe7e9e54a419e docs/CONVENTIONS.md` returns **0**, while `:54` and `:1316` both carry `74116412b733db47`. Both of those are in historical/illustrative context and are defensible as history, but the spine records no current value for a hash-lock it owns. `ADR-0017:232` already flagged the collision.
- **`scripts/make-golden.py:326-327` still emits `"benign_floor": "24/24"` and `"near_miss_floor": "12/12"`** into generated golden run-manifest fixtures, against `contracts/gate_rule.v1.yaml:90-91` which now pins `26/26` and `14/14` after ruling 43. Deliberate frozen history or missed propagation — **under investigation, do not mass-edit.** Most other `24/24` hits in the repo are prose about the benign gate and are not drift.
