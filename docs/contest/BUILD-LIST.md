# Build list — scored work, ordered by points per hour

**Companion to `docs/contest/CONTEST.md`**, which holds the rules, the weights and
the prizes. This file holds only *what to build and in what order*. Every item
names the criterion it scores against, so an item that cannot name one gets cut.

Opened 2026-08-21 (Day 2). Sources: the contest rules, and the Codex review
dispositioned in `docs/codex-review-2026-08-21.md`.

**Swept against the repo 2026-08-22 (Day 3), on `lane/D3-accuracy-sweep` at
`625d38b`.** Every state cell below carries a date, because an undated state cell
is the exact claim that rots — `CONTEST.md` §2 already records a stale row
scheduling work that was finished the day before.

Legend — **[S1]** Stage One pass/fail · **[40]** innovation · **[30A]**
architectural discipline · **[30D]** demo and documentation · **[B]** Stage Three
bonus.

---

## Tier 0 — pass/fail. Nothing else matters if these are missing.

| # | Item | Scores | State |
|---|---|---|---|
| T0-1 | **Architecture diagram** | **[S1] [30D]** | **DONE 2026-08-21.** `docs/diagrams/architecture.md`, six Mermaid diagrams, all rendered and validated. Round loop inlined in the README. Seven unbuilt components drawn dashed and named |
| T0-2 | **First Cloud Run deploy**, with console and Trace Explorer captures into `docs/proof/` | **[S1] [30D]** | **DONE 2026-08-21. All four postconditions closed.** `crucible-00003-t2q`, authenticated, running as `crucible-target`. `/list-apps` returns `["refund_agent"]` and one full episode ran end to end. **Both screenshots landed 2026-08-21** (`b4e060e`): `docs/proof/cloud-run-console-2026-08-21.png` and `docs/proof/trace-explorer-spans-2026-08-21.png`. Transcript: `docs/proof/cloud-run-deploy-2026-08-21.txt`. Three real defects on the way, written up in `deploy/RUNBOOK.md` |
| T0-3 | **Visible Google Cloud proof in the video** — the backend running, on camera | **[S1] [30D]** | **Captures DONE 2026-08-21; the on-camera use of them is owed by the video (T0-6).** The console shot shows the service green in `us-central1` with the URL readable and `Scaling: Auto (Min: 0, Max: 20)`; the trace shot shows 36 spans over 12 hours. **Read the caveat before scripting the narration:** the span names visible in the capture are `invocation`, `invoke_agent refund_agent`, `call_llm`, `generate_content gemini-*`, `/run`, `/list-apps` — **`execute_tool`, the span PC3 was written to demand, is not among them** (the facet list is truncated behind "Show more", so it is not proven absent either). Say "the deployed agent's spans are in Cloud Trace", not "here is the `execute_tool` span", unless someone re-opens the console and confirms. **New option 2026-08-21:** ADR-0012's ban on `--with_ui` on camera is LIFTED — the #4704 probe shows the plugin fires and blocks on `run_live` too, so the recording can show real enforcement through the ADK web UI. Narrate the boundary: the demo may use a path the measurement does not |
| T0-4 | **`README.md` spin-up instructions** | **[S1] [30D]** | **DONE 2026-08-21.** 810 lines, every command run and its real output pasted, four items marked UNVERIFIED with what would settle each. Cold-clone verification still owed on D10 |
| T0-5 | **Findings and learnings** section in the submission text | **[S1]** | **DONE 2026-08-22.** `docs/devpost/findings-and-learnings.md`, five findings, each traceable to a commit SHA or file path, none of them a result. **The real gap in row 2 was not findings.** It asks for *features, technologies, data sources* as well, and `project-story.md` named **zero** Gemini models, zero Google agent frameworks and zero Google Cloud services — verified by grep, all four terms return 0. The mandatory *technology* requirement was always satisfied by the code; the *description* requirement was not, and it is a pass/fail row. Stack and data provenance now carried in the findings file, read out of source. Firestore and BigQuery deliberately NOT listed as used |
| T0-6 | **The 4-minute video**, public, English | **[S1] [30D]** | script exists, **not recorded as of 2026-08-22 — the only Stage One deliverable still missing** |

**T0-2 landed 2026-08-21, and it paid for the schedule.** `execution-spec` put the
first deploy on Day 2 *specifically* to de-risk the most demo-fatal unknown eight
days early. It found four things. The worst: ADK bakes
`GOOGLE_CLOUD_LOCATION=<region>` into the image, while the target pins the
**global** endpoint and hashes `"endpoint": "global"` into the D3 freeze — so the
deployed agent was resolving its model through a different endpoint than the
measured one. Found with nine days of slack; found on Day 10 it is the demo.

**Both screenshots landed the same evening (2026-08-21, `b4e060e`), so T0-3 is no
longer the slipping item. As of 2026-08-22 the video is the only Stage One
deliverable that does not exist.**

The way the screenshots were finally obtained is itself a finding worth keeping:
**four separate times that day this project concluded "no traces exist" from an
instrument that could not see them** — three legacy `projects.traces.list` v1
queries and one console window that did not contain the episode. Repeating a
blind check is not a second opinion. Changing the instrument settled it.
`trace-explorer-1h-empty-window-2026-08-21.png` is kept on purpose as the
negative control.

---

## Tier 1 — free points. None of these depend on the loop working.

| # | Item | Scores | Cost |
|---|---|---|---|
| T1-1 | **Publish a build write-up** on a public platform, stating in the text that it was created for this hackathon | **[B] +0.2** | an afternoon. **NOT DONE, and NOT to be marked done by the Devpost updates.** Updates 3 and 4 went public 2026-08-22 — but **Devpost is the submission platform**, and `CONTEST.md`'s bonus row plausibly requires content published *off* it. **The ambiguity is unresolved and is recorded rather than assumed in either direction**; assuming it counts is how a bonus gets claimed and disallowed |
| T1-2 | **Public social post** with `#AllThingsAgenticHackathon` | **[B] +0.2** | minutes. **Still unclaimed as of 2026-08-22 — nothing has been published carrying the tag** |
| T1-3 | **Gemma** — **NOT built. The false claim is withdrawn; whether Gemma gets a real job is still open.** `ADR-0018` (2026-08-21) supersedes `ADR-0009` and withdraws the "the corpus is Gemma-generated" line; `ADR-0009` stays on disk unedited below its status line, because the record of a claim made, checked and withdrawn is worth more than a document that appears always to have been right. Gemma still appears in no code and `CAPABILITY_CARTOGRAPHER` still has no module. **The +0.2 is therefore NOT currently claimable.** See `docs/NEEDS-ERIC.md` item 10 | **[B] +0.2** | real work, and the on-camera line has already been changed |
| T1-4 | **A second additional Google model.** Cheapest honest candidate: `gemini-embedding-001` for near-duplicate detection across generated attacks, which is a real need and not decoration | **[B] +0.2** | small |
| T1-5 | **A third.** Only if it does real work. **Do not bolt on Veo or Lyria to farm 0.2** — a decorative integration reads as decorative and costs credibility on the 30% criteria | **[B] +0.2** | judgment call |

**Up to a full point on a five-point scale.** T1-1 and T1-2 alone are +0.4 for
about an afternoon, and Eric already writes publicly.

**As of 2026-08-22 the entire bonus is unclaimed.** T1-3's +0.2 is not currently claimable at
all — `ADR-0018` withdrew the Gemma claim. T1-1's status turns on a question nobody has
answered: whether a write-up on the submission platform itself counts. **T1-2 is the one with
no ambiguity and no dependency, and it is still not done.**

---

## Tier 2 — the highest-leverage scoring work

### T2-0 · Replace the four stand-ins in the runnable loop · **[40] [30A] [30D]**

**Opened 2026-08-21. This is the largest scored gap in the project and it was
living in a source-file header rather than on this list.**

> **THREE OF THE FOUR ARE WIRED AS OF 2026-08-22.** The target, the tripwire and
> the warden are driven by `campaign.py` — verified by running it, not by reading
> it: the banner prints `target: REAL`, `tripwire: REAL … 9 clauses, hash
> 19493e53a6d79d0b`, `warden: REAL. The 26-fixture benign suite, 14 near-misses.
> policy@v0 scores 26/26 (near-miss 14/14)`.
>
> **The GATE is the one that is left, and the distinction matters.**
> `crucible/conductor/real_gate.py` is authored and tested, and G7/G8 were
> evaluated against the live project for the first time on 2026-08-22
> (`docs/proof/L3-real-gate-G7-G8-2026-08-22.txt`, 16 assertions, **15 PASS, G7c
> UNEVALUABLE**). But `campaign.py:516` still reads `promote=lambda c, r: True`
> and the banner still prints `gate: STAND-IN`. **Authored is not wired** — this
> list already made that mistake once, in the Tier 4 entry below, and reported
> three adapters as replaced when `campaign.py` imported none of them.

`crucible/conductor/campaign.py` runs the loop unattended to a recorded
termination, and its own docstring is admirably honest about what is real:

| Component | State |
|---|---|
| RED_STRATEGIST, CORONER, ARMORER | **real**, each on its pinned model, firing in sequence |
| DSL parser, validator, POLICY_ENGINE, canonicalizer | **real** |
| BUDGET_GOVERNOR, round protocol, five hash-locks, halt conditions | **real** |
| **the TARGET** | ~~stand-in~~ **WIRED 2026-08-22**, `real_target.py`. The real `LlmAgent`, eight real tools, `refund_policy.md` verbatim, a fresh seeded record per episode, `CruciblePlugin` enforcing. Every episode is now SEALED and therefore scoreable. **Its model is still scripted without `--live`** — everything downstream of the model is real, but a scripted model is not persuadable, so an offline run measures ENFORCEMENT and nothing about susceptibility |
| **the TRIPWIRE** | ~~stand-in~~ **WIRED 2026-08-22**, `real_tripwire.py` (authored 08-21). `Objective_Set.matches` over the ordered `TOOL_EXECUTED` list, 9 clauses, `objective_set_hash 19493e53a6d79d0b` |
| **the WARDEN** | ~~stand-in~~ **WIRED 2026-08-22**, `real_warden.py`. The 26-fixture benign suite with its 14 near-misses, replayed through the real engine |
| **the GATE** | **STILL A STAND-IN as of 2026-08-22.** `campaign.py:516` is `promote=lambda c, r: True`. `real_gate.py` is authored and tested against a local blob store; it has never run against GCS and is not imported by `campaign.py`. G7/G8 have now been *evaluated* out-of-band (15/16, G7c UNEVALUABLE) but are still not *exercised by the loop* |

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

**Known integration gap, found while wiring the tripwire — CLOSED 2026-08-22 by
the target replacement, exactly where it was predicted to land.** `campaign.py`
called `seal_episode` **zero** times, and `harness/episode.py::seal_episode`
refuses an episode whose run manifest lacks `objective_set_hash`,
`manifest_hash` and `derived_schema_hash` — "unscoreable rather than clean,
G1(b)" — so the real tripwire against the stand-in target scored every episode
INVALID. `real_target.py` now owns the seal (`real_target.py:29-31`: "sealing is
the target adapter's job"), and an offline campaign run reports `invalid 0`.

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

### T2-7 · A judge-openable web surface, in two parts · **added 2026-08-22**

**Nobody is assigned to either part.** Part B is **in progress as of 2026-08-22**, no owner
named.

This closes a Stage One gap that is currently written down as a gap: `CONTEST.md` deliverable
8 reads *"authenticated, so it is not yet a URL a judge can open."*

#### Part A — the replay viewer over a committed evidence bundle · **[30D]**

A static page plus a bundle JSON on GitHub Pages. **No credentials, no backend.** Largely
packaging rather than building: **T2-1 already scopes the attack-surface graph as "a script
that renders hashed evidence"**, and the replay viewer already exists and already refuses a
damaged bundle.

**It depends on a real evidence bundle existing, so it is D10 work and not now.** Building the
page first would mean pointing it at a fixture, and a viewer demonstrated against a fixture is
the thing this project spent a whole day learning to distrust.

#### Part B — "Open in Cloud Shell" · **[40] [30A]**

A one-click button that opens the repo in the judge's own Cloud Shell with a guided tutorial
pane. Verified against Google's documentation on 2026-08-22
(`docs.cloud.google.com/shell/docs/open-in-cloud-shell` and `.../shell/docs/quotas-limits`).

- Base `shell.cloud.google.com`; **`cloudshell_git_repo` is required**;
  **`cloudshell_tutorial`** launches a Markdown file as the guided pane. Also available:
  `cloudshell_workspace`, `cloudshell_open_in_editor`, `cloudshell_print`, `cloudshell_image`,
  `ephemeral`, `show`.
- Free tier **50 hours/week**, **5 GB** persistent `$HOME`, terminates after **40 minutes
  idle**, **12-hour** session cap.

> **THE GOTCHA, RECORDED BEFORE IT COSTS ANYTHING: `cloudshell_git_branch` DEFAULTS TO
> `master` WHEN OMITTED, AND OUR DEFAULT BRANCH IS `main`.** Omit it and the button 404s —
> and **the judge finds that, not us.** Google's docs call the parameter optional; for this
> repo it is mandatory. **Verify the assembled URL by OPENING it, not by reading it.** A URL
> that parses is not a URL that resolves, and this repo's standing rule is that a tool's own
> success message is not evidence.

**Why Cloud Shell rather than StackBlitz, in order of weight:**

1. **The judge authenticates as themselves, so no credential is shipped.** That was the entire
   objection to a browser sandbox, and it is the objection a hardening harness cannot afford to
   wave away.
2. **It runs the real modules on a real VM**, not a WASM port that could diverge from what the
   measurement ran.
3. **`cloudshell_tutorial` turns Stage One deliverable 4 from DESCRIBED into DEMONSTRATED.**

**The tutorial runs ONLY zero-model-call components** — the tripwire selftest, the nine
known-bads returning their per-fixture verdicts, the validator refusing a rule containing a
payload string, and a render over a committed bundle. **It must NOT attempt the full loop**,
which needs the judge's own billing.

**Pyodide stays as a later fallback**, with one real advantage over Cloud Shell: **no login at
all.**

---

### T2-8 · The run has to LOOK like something · **RULED BY ERIC 2026-08-23** · **[40] [30D]**

**Eric's directive, verbatim, because the paraphrase loses it:** *"Preparing smooth,
interesting, runtime visuals will be a key factor in the judges' impression of crucible... We
need to create a presentation like atmosphere that leaves a judge or user with actionable
information, slick visuals, and a sense of real accomplishment upon the completion of a run."*

**Sequencing is part of the ruling: the agentic core first, the presentation layer second.**
Not a licence to start now at the expense of the loop.

**The problem, stated plainly.** The entire human-facing surface today is
`crucible/replay/view.py`, a text render. It is honest, it is derived rather than restated, and
**it is not a demo.** Judging is a four-minute video. What is on screen for those four minutes
is a scrolling terminal.

**What this is not.** Not a dashboard, not a web app, not a second product. The evidence bundle
is already the product and it already validates against a schema. **This is a second RENDERER
over the same C6 bundle** — the data does not move, the presentation does. That keeps it
honest: anything the render shows, the bundle can be checked for.

**Two candidate shapes, both reading the same bundle:**

1. **A live run view.** The campaign currently prints a banner and then rounds. A run that
   reveals progressively — the attack going in, the tripwire's verdict landing, the gate
   accepting or rejecting — is the same information paced for a viewer. Cheapest by far, and it
   is what the video actually films.
2. **An HTML evidence report** generated from the bundle, self-contained, openable by a judge.
   Overlaps T2-7 Part A, and there is precedent in `docs/devpost/crucible-explainer.html`.

**The honesty constraint that must survive the polish**, and it is the one to watch: the render
already carries claims corrected during the overclaim sweep because they asserted things the
code never computed. **A prettier renderer is a larger surface for exactly that defect.** Every
figure it shows must be derived from the bundle at render time, never authored into a template.
`tests/test_readme_claims.py` is the pattern — derive the expectation from the producer.

**SCOPED 2026-08-23 at Eric's instruction — `docs/design/T2-8-runtime-visuals-scope.md`.**
Eric's vision is a split screen: a scrolling terminal matched second-for-second with a
flowchart showing which agents are active, what they are doing, what they are communicating and
to whom.

**The scope doc settles one architectural decision and everything follows from it: ONE EVENT
STREAM, TWO RENDERERS.** The terminal and the flowchart are two views of the same emitted
events, never two descriptions of the same run. Second-for-second sync then stops being a
production problem and becomes a property, and — the reason it is the only version this project
may ship — **the flowchart can only draw what the stream carries**, so an overclaim becomes
structurally hard rather than a matter of discipline. The overclaim sweep found ten such claims
in the existing text render; a richer renderer is a larger surface for the same defect.

The stream is **also evidence**: an append-only timestamped record of what happened when is the
audit trail Eric ruled mandatory on 2026-08-23, not just a demo asset. Three modes over one
file — live, replay at recorded pace (labelled, per item 7), and post-hoc from the C6 bundle.

**Risk and its mitigation, because emitting the stream means touching the loop right before the
run every number depends on:** the emitter is an **injected sink with a no-op default**, the
pattern `holdout_touch` already uses. With no sink passed the run path is byte-for-byte
unchanged, which makes it provably inert on the measurement path.

**Not started. No owner. Blocked behind the live run by Eric's own sequencing.** The scope
exists so the design is settled before there is time pressure, not so the work starts early.

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
| **Running the real loop in a browser** *(refused 2026-08-22, with T2-7)* | Four reasons and the last one settles it. The loop is **Python**, and WebContainers run Node. It needs **Vertex, GCS, IAM and Firestore** — none of which exist in a browser sandbox. It is roughly **500 episodes and ~6M tokens**, which is not a page load. And it would mean **shipping a credential into a browser** — for a harness whose entire subject is agents holding permissions they should not, that is the failure it exists to warn about |
| **A sandbox that replays canned output while appearing live** *(refused 2026-08-22, with T2-7)* | `ADR-0010` already names *"a replay looking like live"* as the one version that could actually cost us. A replay clearly labelled as a replay is fine and is what Part A is. The refusal is of the unlabelled kind |

---

## Tier 4 — open threads that are not scored but block scored work

**Swept 2026-08-22.** Closed threads are kept with their closing date rather than
deleted: a list that only ever grows is a list nobody trusts, and a list that
silently loses rows cannot be audited.

### Still open

- **D5 corpus freeze** — hash the corpus and Part B, upload sealed to GCS, hash into the D5 post. **Must land before the first patch is written.** Two halves are now in different states: `corpus/freeze.py` implements `corpus_hash` (it had no implementation before 2026-08-22) and `derived_schema_hash` computes to `ab65499038b0d7c7` from Part B in force — but **neither has fired**, and both are being held so the D5 pair lands together.
- **The sealed F4 family did not exist on disk as of 2026-08-22.** `python -m corpus` returned `sealed: 0` that day and FAILS on `E_SEALED_BELOW_FLOOR` — the floor is 18, the target 24. That failure is the check working, and it is the single largest gap between the current tree and a scoreable run.
- **The first real loop run.** Compute-heavy, and it produces every number. An offline `python -m crucible.conductor.campaign` now runs the real target, tripwire and warden to a recorded termination, but a scripted model is not persuadable — **no ASR, BPR, transfer or convergence figure from an offline run may be reported.**
- **The GATE is the last stand-in in `campaign.py`** — see T2-0 above. G7/G8 have been evaluated out-of-band, never by the loop.
- **G7c is UNEVALUABLE and will stay that way until an audit sink exists.** `holdout_touch_count` is derived from Cloud Audit Log DATA_ACCESS reads on the sealed holdout (`measurement-spec.md:946`); the live project has **no `auditConfigs` block**, so the number does not exist to be read. **Defaulting it to 0 would print a green G7c computed from a sink that was never created** — `gate_rule.v1.yaml` routes `absent_or_unevaluable` to RUN INVALID precisely to stop that.
- **`measurement-spec.md` §1.3's ≥3-routing requirement is unmet** — only 2 of F5's 10 instances route through `CAP_INVOKES_AGENT` (F5-09, F5-10). A known, reported deviation; the floor is not lowered to fit the measurement.
- **The SEP-BY split is off target.** `python -m corpus` reports **21 policy / 3 oracle** over 24 counted pairs (3 cut, 27 total) against the stated target of **18 / 4**. Not a stop condition — the stop condition is parity — but any doc quoting "18 of 22" as the split is quoting a target, not a measurement.
- **ADR-0010 vs "unedited, live execution"** — see `CONTEST.md` §4. Eric's call.
- **`ORD-13` / `ORD-14`** were authored after Eric's review pass, so "the benign set was reviewed" is not true of the set as it stands. **Still open as of 2026-08-22** — no ratification record exists for these two, unlike the two retirements (`docs/proof/benign-retirement-ratification.md`) and the sealed family.
- **`google/adk-samples@f4c19ab` IS NOT A REAL OBJECT** (found 2026-08-22, `docs/proof/third-party-target-recon-2026-08-22.md`). `git cat-file` rejects it and the remote has no such ref. It originates as one hardcoded literal at `scripts/make-golden.py:341`, which generates the golden contract fixtures — and `docs/proof/L6-cold-clone-2026-08-20.txt:23` printed it **by replaying that fixture**, so a synthetic value shaped like a real SHA was read as an observation, inside a proof file. Real HEAD 2026-08-22 is `629310b`, on a live branch that will move. **Not yet actioned:** the literal is still `f4c19ab` at `make-golden.py:341` and still illustrative in `docs/data-spec.md`. Make it obviously synthetic (`@DEADBEEF`) or carry the real SHA; have the Day-9 adapter `git rev-parse HEAD` at attach time rather than retype.
- **"CRUCIBLE tricked the agent into a 40% discount" is DEAD VOCABULARY.** The adk-samples pivot to `sync_ask_for_approval` is the sample's *intended* flow — `prompts.py:49,65-66` tells the model that tool requests manager approval and never states the cap. A model routing there is obeying its instructions; the defect is that the escalation destination has no manager in it. The frozen claim at `execution-spec.md:681` survives because it is about the code, not the model.
- **~~`CONVENTIONS.md` does not carry a current frozen `target_agent_hash`~~ — CLOSED by ruling 46, `SPINE_VERSION 15`, and closed the opposite way from how it was written.** This row asked the spine to record the value. It should not, and no longer will: a hash is a measurement of bytes that already exist, not a decision a lane could re-litigate, and `hashlocks.py` raises `HashLockSkew` at startup when a frozen record disagrees with the artifact. A table would have been a sixth copy. **The owner is `target/refund_agent/FROZEN.json`; read it at the moment you need it.**
- **`docs/devpost/2026-08-22-update-4-target-frozen.md` names the FIRST-freeze hashes and is PUBLISHED. Do not edit it** — it was true when it went out, and `execution-spec.md:735` rules that the correction belongs in a later public update. **That update is owed.** Note the trap this row itself fell into: it, and every other document written to correct update 4, then went stale carrying the SECOND freeze while the artifact moved to the fourth. Ruling 46 is the fix. State no hash here; print `target/refund_agent/FROZEN.json`.

### Closed since this list was opened

- **D2 gate-rule freeze — FIRED 2026-08-21.** `gate_rule_hash cff9f52929397efb`, recorded in `docs/proof/d2-gate-rule-freeze.json` with commit `b4e060e` and its timestamp. `contracts/gate_rule.v1.yaml:90-91` pins `bpr == "26/26"` and `near_miss_bpr == "14/14"`, so the freeze did not decide the corpus counts by side effect.
- **`objective_set_hash` — FIRED 2026-08-22**, the fourth hash-lock. `contracts/objective_set.v1.json`, nine clauses each with a `clause_id`, frozen at **`19493e53a6d79d0b`**, recorded in `docs/proof/d3-objective-set-freeze.json`. Ruling 44, `SPINE_VERSION 12`. **The interesting part is why C10 lost an argument it won on the page:** the contract said the `_`-prefixed annotations were inside the hash, and contracts outrank code — but `ObjectiveSet.hash` strips them, and that stripped value is what every episode carries, so freezing the unstripped `569c5198d7e731d9` would have named a number no episode could ever carry and scored every round INVALID. A hash-lock that locks nothing. The losing argument is preserved inside the corrected contract.
- **The target freeze — FIRED, then RE-FIRED 2026-08-22.** See the open item above for the current values. **The finding was not the re-freeze.** A lane changed a hash-locked package, `target_agent_hash` moved, and **1011 tests stayed green with `contract-check` ALL PASSES OK.** The only thing that noticed was `python -m target.refund_agent.freeze --check`, which no test and no gate ran. A skew detector now recomputes the target and manifest hashes at run time, with a negative control proven red.
- **`r_new3` fails validator V4 — CLOSED 2026-08-21.** Rewritten to `status_to in [APPROVED]`, read out of the instances rather than chosen. Eight tests, two of them negative controls. **The prose was wrong in three places and differently wrong in each** — only the rule is machine-checked.
- **`ALLOW` / `allow` — CLOSED.** `crucible/policy/engine.py:109` now carries `_ALLOW_SPELLINGS = frozenset({"ALLOW", "allow"})` with the defect written up in-source at `:98-101`. Canonicalization still lives in `corpus/model.py::canonical_decision`.
- **The three real adapters — WIRED 2026-08-22.** `campaign.py` imports `build_real_target`, `real_tripwire` and `real_warden` at `:89-91` and the banner prints all three as REAL. This row previously read "authored but not wired", which was the correction of an earlier row that had reported them as replaced. **The gate is the one still in that state, and it is now the only one.**
- **`scripts/make-golden.py` benign floor — CLOSED.** `:337` and `:368-369` now emit `"benign_floor": "26/26"` and `"near_miss_floor": "14/14"`, matching `contracts/gate_rule.v1.yaml:90-91`, with an in-source note that a stale value here does not produce a weaker fixture, it produces a "valid" fixture that fails its own schema.
- **`corpus/C6-reach` — MERGED 2026-08-21.** Four instances that make `CAP_INVOKES_AGENT` reachable. Eric ruled to amend the frozen counts it broke (F5 8→10, training 48→50, benign 24→26, near-miss 12→14) rather than retire instances, **before the D2 hash-lock — the only window in which "permanently" can be changed at all.** The ≥3-routing deviation it did not close is carried above as its own open row.
