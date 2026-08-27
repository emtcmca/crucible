# Build list — scored work, ordered by points per hour

**Companion to `docs/contest/CONTEST.md`**, which holds the rules, the weights and
the prizes. This file holds only *what to build and in what order*. Every item
names the criterion it scores against, so an item that cannot name one gets cut.

Opened 2026-08-21 (Day 2). Sources: the contest rules, and the Codex review
dispositioned in `docs/codex-review-2026-08-21.md`.

**RE-SWEPT against the repo 2026-08-25 (Day 6), on `main` at `7827346`.** The
previous sweep was 2026-08-22 on `lane/D3-accuracy-sweep` at `625d38b`, and by
2026-08-25 it had rotted in exactly the way this file exists to prevent: it
carried the GATE as a stand-in three days after it was wired, said the sealed F4
family did not exist when 24 instances verify SEAL INTACT, said neither half of
the D5 freeze had fired when both are recorded in `docs/proof/`, said the
objective set held 9 clauses when it holds 11, and listed the first live loop run
as pending after 60 of them completed. **Three days of standing still.**

Every state cell below carries a date, because an undated state cell is the exact
claim that rots — `CONTEST.md` §2 already records a stale row scheduling work
that was finished the day before.

**RULING 46 APPLIES TO THIS FILE.** A frozen hash has exactly one owner, the
artifact. Where an earlier version of this list printed a hash VALUE, the value
has been replaced by the path to read it from at use time. This file names
`docs/proof/*.json` and `target/refund_agent/FROZEN.json`; it states no hash.

Legend — **[S1]** Stage One pass/fail · **[40]** innovation · **[30A]**
architectural discipline · **[30D]** demo and documentation · **[B]** Stage Three
bonus.

---

## Tier 0 — pass/fail. Nothing else matters if these are missing.

| # | Item | Scores | State |
|---|---|---|---|
| T0-1 | **Architecture diagram** | **[S1] [30D]** | **DONE 2026-08-21.** `docs/diagrams/architecture.md`, six Mermaid diagrams, all rendered and validated. Round loop inlined in the README. Seven unbuilt components drawn dashed and named |
| T0-2 | **First Cloud Run deploy**, with console and Trace Explorer captures into `docs/proof/` | **[S1] [30D]** | **DONE 2026-08-21. All four postconditions closed.** `crucible-00003-t2q`, authenticated, running as `crucible-target`. `/list-apps` returns `["refund_agent"]` and one full episode ran end to end. **Both screenshots landed 2026-08-21** (`b4e060e`): `docs/proof/cloud-run-console-2026-08-21.png` and `docs/proof/trace-explorer-spans-2026-08-21.png`. Transcript: `docs/proof/cloud-run-deploy-2026-08-21.txt`. Three real defects on the way, written up in `deploy/RUNBOOK.md`. **REDEPLOYED 2026-08-24 and the row moved with it:** the serving revision is now `crucible-00004-gfk` (2026-08-24 22:58:01 UTC), because seven commits touched `target/refund_agent/` after the 08-21 deploy and `FROZEN.json` did not exist at the deployed commit at all, so the deployed agent was not the measured agent. Transcript `docs/proof/cloud-run-redeploy-2026-08-24.txt`; PC1 and PC2 re-closed there (`/list-apps` returns `["refund_agent"]`, HTTP 200). **PC3 and PC4 are OWED AGAIN for the new revision**, per that file's own "STILL OWED" block at `:46-50` |
| T0-3 | **Visible Google Cloud proof in the video** — the backend running, on camera | **[S1] [30D]** | **CHANGED 2026-08-25 AND NOT IN OUR FAVOUR: the 2026-08-21 captures are now STALE FOR VIDEO PURPOSES.** They show revision `crucible-00003-t2q`, which stopped serving on 2026-08-24 when `crucible-00004-gfk` took traffic. `docs/proof/cloud-run-redeploy-2026-08-24.txt:47-50` says so in its own words: PC3 (Trace Explorer span for the new revision) and PC4 (console page for the new revision) are owed, and the old shots "remain true about that date" and nothing more. **Filming the 08-21 shots as if they were the running service would put a superseded revision on camera.** Everything below is still accurate about the 08-21 captures, and is kept because the caveat travels with whatever replaces them. **Captures DONE 2026-08-21; the on-camera use of them is owed by the video (T0-6).** The console shot shows the service green in `us-central1` with the URL readable and `Scaling: Auto (Min: 0, Max: 20)`; the trace shot shows 36 spans over 12 hours. **Read the caveat before scripting the narration:** the span names visible in the capture are `invocation`, `invoke_agent refund_agent`, `call_llm`, `generate_content gemini-*`, `/run`, `/list-apps` — **`execute_tool`, the span PC3 was written to demand, is not among them** (the facet list is truncated behind "Show more", so it is not proven absent either). Say "the deployed agent's spans are in Cloud Trace", not "here is the `execute_tool` span", unless someone re-opens the console and confirms. **New option 2026-08-21:** ADR-0012's ban on `--with_ui` on camera is LIFTED — the #4704 probe shows the plugin fires and blocks on `run_live` too, so the recording can show real enforcement through the ADK web UI. Narrate the boundary: the demo may use a path the measurement does not |
| T0-4 | **`README.md` spin-up instructions** | **[S1] [30D]** | **DONE 2026-08-21; grown and gated since.** Every command run and its real output pasted, four items marked UNVERIFIED with what would settle each. **1,155 lines as of 2026-08-25** (810 at the 08-22 sweep). It now opens with the Open in Cloud Shell button (`README.md:13`, see T2-7 Part B). **A staleness gate was added overnight 2026-08-25:** `scripts/contract-check.py:356,385` adds a sixth pass, `FRESH`, which fails when the README's `**As of` anchor is more than two days old, built because the README rotted while every check walked `docs/` only, and **a check that does not cover the artifact cannot fail for it**. **Still owed: cold-clone verification on D10, and the README's own Status section is dated 2026-08-24 and predates the 60-run batch** |
| T0-5 | **Findings and learnings** section in the submission text | **[S1]** | **DONE 2026-08-22.** `docs/devpost/findings-and-learnings.md`, five findings, each traceable to a commit SHA or file path, none of them a result. **The real gap in row 2 was not findings.** It asks for *features, technologies, data sources* as well, and `project-story.md` named **zero** Gemini models, zero Google agent frameworks and zero Google Cloud services — verified by grep, all four terms return 0. The mandatory *technology* requirement was always satisfied by the code; the *description* requirement was not, and it is a pass/fail row. Stack and data provenance now carried in the findings file, read out of source. Firestore and BigQuery deliberately NOT listed as used |
| T0-6 | **The 4-minute video**, public, English | **[S1] [30D]** | **STILL NOT RECORDED as of 2026-08-25, re-verified, and it is still the only Stage One deliverable that does not exist.** Asserted three ways rather than reported: no `.mp4` or `.mov` anywhere in the tree, no `youtu`/`vimeo` string in any tracked `.md` or `.html`, and `README.md:26` still reads *"The demo video — not yet recorded. Link goes here."* **The script side has moved on, which is why the absence is now the whole gap:** `docs/design/narration-tonight.md` is a recording script for chunks N1–N5 with every figure re-verified from source 2026-08-24 and corrections already applied inline, and `docs/design/architecture-animation-spec.md` (Eric, 2026-08-24) is a three-rule spec for the 0:50–1:35 architecture beat. **Words and storyboard exist. Footage does not.** Record 08-29 per `execution-spec.md:26` |

**T0-2 landed 2026-08-21, and it paid for the schedule.** `execution-spec` put the
first deploy on Day 2 *specifically* to de-risk the most demo-fatal unknown eight
days early. It found four things. The worst: ADK bakes
`GOOGLE_CLOUD_LOCATION=<region>` into the image, while the target pins the
**global** endpoint and hashes `"endpoint": "global"` into the D3 freeze — so the
deployed agent was resolving its model through a different endpoint than the
measured one. Found with nine days of slack; found on Day 10 it is the demo.

**Both screenshots landed the same evening (2026-08-21, `b4e060e`), so T0-3 was no
longer the slipping item. As of 2026-08-25 the video is still the only Stage One
deliverable that does not EXIST**, but T0-3 has partially re-opened rather than
staying closed: the 08-21 captures show a revision that stopped serving on
2026-08-24, and PC3/PC4 are owed again for `crucible-00004-gfk`. **A deliverable
can rot without anyone touching it.** That is the same shape as the FRESH gate
added to the README overnight, and the same shape as this list.

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
| T1-1 | **Publish a build write-up** on a public platform, stating in the text that it was created for this hackathon | **[B] +0.2** | an afternoon. **STILL NOT DONE as of 2026-08-25, and the ambiguity is unchanged.** Devpost updates 3 and 4 went public 2026-08-22 and **update 6 was posted by Eric 2026-08-25** (`docs/devpost/2026-08-25-update-6-first-promotions.md`, renamed out of `DRAFT-` in the commit that says "Eric posted it 2026-08-25"). **None of that settles this row**, because **Devpost is the submission platform** and `CONTEST.md`'s bonus row plausibly requires content published *off* it. **The ambiguity is unresolved and is recorded rather than assumed in either direction**; assuming it counts is how a bonus gets claimed and disallowed |
| T1-2 | **Public social post** with `#AllThingsAgenticHackathon` | **[B] +0.2** | minutes. **UNVERIFIED from this repo as of 2026-08-25.** What is in-tree: `CONTEST.md:182,193` still says not done, and two handoff briefs exist (`docs/handoff/2026-08-22-linkedin-hackathon-post.md`, `docs/handoff/2026-08-23-linkedin-post-193-brief.md`), both requiring the literal tag to survive into whatever ships. **This session cannot see whether one shipped**, because LinkedIn belongs to the `/linkedin` session by Eric's 2026-08-22 ruling, and nothing in `crucible` records a publication. **What would settle it:** the `C:\dev\linkedin` queue, or Eric's own profile. Do not mark this done from a brief; a brief is a plan |
| T1-3 | **Gemma**: **BUILT, and this row was wrong for three days. Corrected 2026-08-25.** The row said "Gemma still appears in no code and `CAPABILITY_CARTOGRAPHER` still has no module." **There are now nine files**: `crucible/cartographer/` holds `gemma.py`, `extract.py`, `prepass.py`, `ratify.py`, `run.py`, `vertex.py`, `freeze_foreign_target.py` and a foreign target `foreign/adk_customer_service.json`, with `tests/test_cartographer_gemma.py`, `tests/test_capability_prepass.py` and `tests/test_cartographer_inert.py` behind them. **It has run live three times**: `docs/proof/cartographer-live-run-2026-08-22.json`, `...-2026-08-23.json`, and a stability run `docs/proof/cartographer-stability-2026-08-24.json`. **What has NOT changed and must not drift back:** `ADR-0018` (2026-08-21) supersedes `ADR-0009` and withdraws the "the corpus is Gemma-generated" line permanently; `ADR-0009` stays on disk unedited below its status line, because the record of a claim made, checked and withdrawn is worth more than a document that appears always to have been right. **Gemma classifies capabilities. It does not author the corpus, and no sentence may say it does.** Ratification is Eric's: `docs/NEEDS-ERIC.md` item 13, *"RULED 2026-08-23. In build. Eric ratifies when the re-run lands."* **The +0.2 turns on that ratification, not on whether code exists** | **[B] +0.2** | built; ratification outstanding |
| T1-4 | **A second additional Google model.** Cheapest honest candidate: `gemini-embedding-001` for near-duplicate detection across generated attacks, which is a real need and not decoration. **NOT BUILT as of 2026-08-25**. `gemini-embedding-001` appears in exactly two places in the tree, this row and `docs/data-spec.md:88`, where it appears in the argument for **not** using Firestore vector search. Nothing imports an embedding model | **[B] +0.2** | small |
| T1-5 | **A third.** Only if it does real work. **Do not bolt on Veo or Lyria to farm 0.2** — a decorative integration reads as decorative and costs credibility on the 30% criteria. **Not started as of 2026-08-25** | **[B] +0.2** | judgment call |

**Up to a full point on a five-point scale.** T1-1 and T1-2 alone are +0.4 for
about an afternoon, and Eric already writes publicly.

**As of 2026-08-25 the entire bonus is still unclaimed, and one of the three reasons has
changed.** T1-3 is no longer blocked on the code (the Cartographer exists and has run live
three times); it is blocked on Eric's ratification (`NEEDS-ERIC.md` item 13). T1-1's status
turns on a question nobody has answered: whether a write-up on the submission platform itself
counts, and update 6 going public on Devpost 2026-08-25 does not answer it. **T1-2 is the one
with no ambiguity and no dependency, and this repo cannot see whether it has been done.**

---

## Tier 2 — the highest-leverage scoring work

### T2-0 · Replace the four stand-ins in the runnable loop · **[40] [30A] [30D]**

**Opened 2026-08-21. CLOSED 2026-08-25. All four stand-ins are gone.** The row is
kept rather than deleted, because the largest scored gap in the project spent a
week being described three different ways and the sequence is the record.

> **ALL FOUR ARE WIRED AS OF 2026-08-25, AND THE GATE ROW BELOW WAS WRONG FOR
> THREE DAYS.** It said *"`campaign.py:516` is `promote=lambda c, r: True`"* and
> *"the banner still prints `gate: STAND-IN`"*. Neither is true and neither has
> been since 2026-08-22.
>
> **What `campaign.py` actually contains now.** `:555` is a comment reading
> *"THE GATE. `promote=lambda c, r: True` lived here until 2026-08-22"*; `:974`
> passes `promote=gate`, the object built by `build_gate()` at `:574`; and the
> file's own header at `:27-33` records the replacement. `build_gate` constructs
> `crucible.conductor.real_gate.RealGate` over a real append-only `Ledger`, with
> `GcsBlobIO` on the policies bucket under `--live` and `skip_cloud=True`
> offline. **The offline mode is STRICTER than the stand-in it replaced, not
> looser** (`:592-603`): the stand-in promoted everything, `skip_cloud=True`
> records G7/G8 UNEVALUABLE and raises `GateRunInvalid`, so nothing offline can
> return a promotion at all.
>
> **What the live banner prints**, from `evidence/batch-night-2026-08-25/run-10.console.txt:12`:
> `gate : REAL. RealGate, promoter crucible-gate read from scripts/gcp-env.sh.
> G7 (a/b/b2/c) AND G8 EVALUATED AGAINST LIVE GCP before every promotion. Policy
> store: gs://crucible-policies-x7 via GcsBlobIO.`
>
> **And it was exercised, not merely wired.** Across the 60-run overnight batch,
> summed out of the run records rather than read off a log: **95 promotions, 1
> rejection**, and the gate findings are **G8 PASS ×570, G7a PASS ×380, G7b PASS
> ×285, G7b2/G8 PASS ×95, G7 PASS ×95, G7c PASS ×95**, with zero UNEVALUABLE at any
> promotion. `summary.gate.g7_g8_exercised` is `true` in **52 of the 60 runs**;
> the other 8 never reached the gate, and their own bundles say so in a
> `no_result_may_be_quoted_from_this_run` field rather than leaving it to a
> reader.
>
> **The lesson this row was written to teach still stands, with the sign
> flipped.** It warned that *authored is not wired*. It then became the thing it
> warned about: **wired is not swept.** Nobody edited this file, and it went
> wrong by standing still.

`crucible/conductor/campaign.py` runs the loop unattended to a recorded
termination, and its own docstring is admirably honest about what is real:

| Component | State |
|---|---|
| RED_STRATEGIST, CORONER, ARMORER | **real**, each on its pinned model, firing in sequence |
| DSL parser, validator, POLICY_ENGINE, canonicalizer | **real** |
| BUDGET_GOVERNOR, round protocol, five hash-locks, halt conditions | **real** |
| **the TARGET** | ~~stand-in~~ **WIRED 2026-08-22**, `real_target.py`. The real `LlmAgent`, eight real tools, `refund_policy.md` verbatim, a fresh seeded record per episode, `CruciblePlugin` enforcing. Every episode is now SEALED and therefore scoreable. **The "scripted model" caveat is now conditional rather than current (2026-08-25):** `scripts/night-batch.sh:37` runs `--live`, and the batch banner prints `models : LIVE` and `target model : LIVE. The pinned target binding decides every call.` A run without `--live` still measures ENFORCEMENT and nothing about susceptibility, and that sentence must survive next to any offline figure |
| **the TRIPWIRE** | ~~stand-in~~ **WIRED 2026-08-22**, `real_tripwire.py` (authored 08-21). `Objective_Set.matches` over the ordered `TOOL_EXECUTED` list. **ELEVEN clauses as of 2026-08-25, not nine**, counted at source in `contracts/objective_set.v1.json` and confirmed by `docs/proof/d3-objective-set-freeze.json` (`"clause_count": 11`). The set was re-frozen on 08-23 and 08-24; the superseded records are kept beside it. **Ruling 46: the hash lives in that freeze record and in `FROZEN.json`, and is read at use time, never copied here** |
| **the WARDEN** | ~~stand-in~~ **WIRED 2026-08-22**, `real_warden.py`. The 26-fixture benign suite with its 14 near-misses, replayed through the real engine. **New as of 2026-08-25 and it is a finding, not a footnote:** the run record now carries `benign_floor_at_v0.benign_passes_requiring_approval`, and it reads **4**. Four of the 26 passes depend on the APPROVAL_ORACLE waving through a call the policy stopped, and `26/26` has been printing since round zero without saying so. See the new Tier 4 row |
| **the GATE** | ~~stand-in~~ **WIRED 2026-08-22, and EXERCISED AGAINST LIVE GCP 2026-08-25.** This cell read "STILL A STAND-IN" for three days after the wiring landed. `campaign.py:974` passes `promote=gate`; `:555` marks where the lambda used to live. `docs/proof/L3-real-gate-G7-G8-2026-08-22.txt` was the out-of-band evaluation (16 assertions, 15 PASS, G7c UNEVALUABLE); the loop has since run it 95 times with **G7c PASS in all 95**, after `NEEDS-ERIC.md` item 11 closed G7c on 2026-08-22 by enabling Data Access audit logging and building `infra/holdout_touch.py` |

**Why it scored, and on all three criteria** (kept in the past tense, because the
gap is closed and the reasoning is why it was worth closing first). The three
model agents were already real; the four STAND-INS were the pure-code arbiters —
and "no model ever decides whether a breach happened" is the sentence the whole
demo is built on. A judge who opened `campaign.py` read that claim and its stub
in the same file. On **[30A]** that was the architectural argument simulated
rather than enforced; on **[40]** the loop measured nothing about an agent's
susceptibility to persuasion, which is the entire thing the target exists to
measure; on **[30D]** the demo's headline pair had no real number behind it.

**The prediction held: all four were WIRING, not building.** Every real module
already existed — `crucible/tripwire/`, `crucible/warden/`, `crucible/gate/`,
`target/refund_agent/` — and the 2026-08-21 ADK probe
(`docs/proof/adk-4704-probe-2026-08-21.txt`) proved the enforcement plugin fires
and blocks through a real `Runner` on both invocation paths. Each stand-in had a
clean signature, so each replacement was a drop-in adapter in its own file. The
last of the four landed 2026-08-22 and ran against live GCP 2026-08-25.

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

**STATE 2026-08-25 (later the same day): BUILT. THE RENDER THAT SHIPS IS NOT YET
TAKEN.** `scripts/render-attack-surface.py` is the renderer, and it takes the
bundle directory as a required argument so regeneration is one command.
`scripts/render-attack-surface-negcheck.py` is its negative control: it mutates a
copy of a real bundle directory ten ways, runs the shipped renderer unchanged on
each, and includes a positive control on the unmutated copy so the nine refusals
are proven selective rather than merely loud. Committed render output and the
regeneration command are in `docs/diagrams/attack-surface.md`, alongside the
negative control's real output.

**What remains: the committed render is a DEVELOPMENT INPUT and says so on its
own face.** It was built from `evidence/batch-night-2026-08-25/`, whose bundles
measure a corpus that no longer exists — `corpus_hash` moved when F5-05 was
repaired and the D5 freeze was re-taken. That is not typed into the render: the
renderer reads the bundles' corpus hash and the current freeze record's and
prints the banner when they differ, so **pointing it at a post-repair batch flips
the banner with no edit to any file.** Re-run it on the post-repair batch and this
item is closed.

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

**STATE 2026-08-25 (evening): BUILT.** `scripts/finding-cards.py` is the
producer; `docs/finding-cards/` holds the method, the severity table, and the
generated sheets. The rollup is refused in code and on every sheet. Regenerate
with the command in `docs/finding-cards/README.md`; `--verify-repro` RUNS every
command the cards print and exits 4 if one did not reproduce, and `--selftest`
proves the severity assigner and its citation check can fail.

**The unblocking line above was wrong, and the correction is the finding.** It
said *"60 bundles now exist to point it at."* Pointed at
`evidence/batch-night-2026-08-25/` on `SPINE_VERSION 25`, **all 60 are REJECTED
by `crucible.replay`** — every one fails `E_SCHEMA` on
`episodes[].target_responded`, the field the C6 contract gained with ruling 55
the same day, and 46 additionally fail `E_EXCLUSION_CEILING_RUN`. Their
`corpus_hash` also no longer matches `docs/proof/d5-corpus-freeze.json` after the
F5-05 repair and the D5 re-freeze. **A bundle that exists is not a bundle that
opens.** The shipped sheets are generated from `evidence/smoke-2026-08-25`
instead, whose bundles the reader accepts and whose six lock fields all match the
artifacts in force — the sheet prints that comparison in a table cell rather than
in a caveat somebody has to remember to write.

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

**DONE 2026-08-21; still present, re-located 2026-08-25.** The section is
`README.md:947`, *"What happens when an agent loops, lies, or returns nothing"*.
**This row said `:770` and the README has grown to 1,155 lines since. A line
number is a state cell like any other, and it rots the same way.** Six mechanisms, each naming the specific failure it exists for
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

### T2-5 · The "unlikely hero" · **RULED BY ERIC 2026-08-23. CLOSED.** · **[40]**

**This row said "Needs Eric's call" for two days after Eric made the call.**
`docs/NEEDS-ERIC.md:466` records it: *"Eric: the persona makes sense as written."*
`docs/contest/unlikely-hero.md` is ratified and is to be used in the submission
text and the demo narration.

(Original text below.) A named Stage Two sub-criterion for this track, and we
scored zero on it because no persona existed anywhere in the project.

The honest candidate is not a security engineer — it is the **operations lead who
inherits an agent someone else built** and has to decide whether it is safe to give
it the company card. That is a real role, it is outside standard corporate
security, and it is genuinely who this tool serves.

A persona invented to satisfy a rubric reads exactly like a persona invented to
satisfy a rubric, which is why it was Eric's call and not the coordinator's.

### T2-6 · Meet the track description head-on · **RULED BY ERIC 2026-08-23** · **[S1] [40]**

**FRAMING ACCEPTED, WITH ONE CLAIM THAT ONLY BECAME PARTLY TRUE ON 2026-08-25.**
`docs/NEEDS-ERIC.md:425-441`: Eric accepted the drafted framing in
`docs/contest/track-fit.md`, adding *"we won't have weeks of data, but we should
have days, nearly a full week."* The coordinator note attached to that ruling is
the part to watch: **days of BUILD history does not answer "do the AGENTS
maintain context across weeks."** The claim that does is **the POLICY**: durable
cross-session state, accumulating across rounds and runs, each version hash-locked
and dated, in a bucket the authoring identity cannot write to.

That note said the claim *"is not true yet. Nothing has ever been promoted, the
policies bucket is empty, and `GcsBlobIO` has never executed."* **All three of
those sentences became false on 2026-08-25**: 95 promotions, the bucket written
through `GcsBlobIO`, read back and rehashed. **What is still not true is the
"several separate days" half.** The promotions are from one night. A policy
promoted on 08-25 constraining the agent on 08-28 is the demonstration, and it
needs another live run on another day to exist.

(Original text below.) See `CONTEST.md` §3. CRUCIBLE is not a "scalable network of
institutional agents" maintaining "context across weeks of asynchronous
operations." Pretending otherwise is worse than addressing it. It is a writing
problem rather than a building one.

### T2-7 · A judge-openable web surface, in two parts · **added 2026-08-22**

**STATE 2026-08-25: Part B SHIPPED, Part A not started, and Part B shipped with a defect this
row predicted.** See both sub-rows.

This closes a Stage One gap that is currently written down as a gap: `CONTEST.md` deliverable
8 reads *"authenticated, so it is not yet a URL a judge can open."*

#### Part A — the replay viewer over a committed evidence bundle · **[30D]**

**STATE 2026-08-25: NOT STARTED, NO OWNER, and its stated blocker is now gone.** No static
page and no committed bundle exist; `crucible/replay/` is still five Python modules and
`docs/` holds no page other than `docs/devpost/crucible-explainer.html`. The row below says
this is D10 work because it depends on a real evidence bundle existing. **Sixty of them now
exist** in `evidence/batch-night-2026-08-25/`, all validating against the offline reader.
**The remaining obstacle is different and it is real: `evidence/` is gitignored**, so
publishing one means deliberately committing a chosen bundle, which is a decision and not a
packaging step.

A static page plus a bundle JSON on GitHub Pages. **No credentials, no backend.** Largely
packaging rather than building: **T2-1 already scopes the attack-surface graph as "a script
that renders hashed evidence"**, and the replay viewer already exists and already refuses a
damaged bundle.

**It depends on a real evidence bundle existing, so it is D10 work and not now.** Building the
page first would mean pointing it at a fixture, and a viewer demonstrated against a fixture is
the thing this project spent a whole day learning to distrust.

#### Part B — "Open in Cloud Shell" · **SHIPPED 2026-08-22. THE GOTCHA BELOW IS LIVE IN THE SHIPPED URL.** · **[40] [30A]**

**What landed.** `docs/cloudshell-tutorial.md` (191 lines) and `scripts/try-a-rule.py` (122
lines), both on `main`, committed as `588eba0` *"a judge can run the pure-code half in a
browser, with no credential"*. The tutorial runs only zero-model-call components, exactly as
scoped. `README.md:13` carries the badge. **The best beat in it was not in the brief:**
`try-a-rule.py` builds the same validator the Armorer's output is judged by, and a judge can
watch it refuse `cap:UNCLASSIFIED => deny` with `E_UNCLASSIFIED_SELECTOR`, and **the validator
refuses the one rule that would fake the headline transfer number, and says so in the error
text.**

> **THE DEFECT, FOUND ON THIS SWEEP 2026-08-25 AND NOT YET FIXED. THE SHIPPED URL OMITS
> `cloudshell_git_branch`.** `README.md:13` is
> `https://shell.cloud.google.com/cloudshell/open?cloudshell_git_repo=...&cloudshell_tutorial=docs/cloudshell-tutorial.md`
> which is two parameters, not three. **The string `cloudshell_git_branch` appears exactly once in
> the whole repository, and it is the warning three paragraphs below this one.** The lane that
> built this confirmed the gotcha against `origin/HEAD` in its own commit message and wrote
> *"the parameter the docs call optional is mandatory for us. Omit it and a judge finds the
> 404."* **It shipped omitted anyway.** The same commit message also says the documented path
> is `/cloudshell/editor`, not `/cloudshell/open`; the badge uses `/cloudshell/open`.
>
> **UNVERIFIED, and it can only be settled one way:** nobody has opened the URL. `588eba0`
> says so in its own words: *"NOT VERIFIED, AND NAMED: nobody opened the URL. It is
> round-tripped through `urllib.parse` and asserted on all three params, and that is all."*
> **A URL that parses is not a URL that resolves.** What settles it: Eric clicks the badge
> while signed in, and the tell is whether the clone lands on `main`.
>
> **Second unguarded coupling, from the same commit:** if `docs/cloudshell-tutorial.md` ever
> moves, the `cloudshell_tutorial=` parameter must move with it and **no gate would catch the
> mismatch**, and the link would simply open a Cloud Shell with no tutorial pane.
>
> **A FIX IS IN FLIGHT AND UNCOMMITTED as of this sweep (2026-08-25).** A parallel session has
> `README.md`, `docs/cloudshell-tutorial.md` and `scripts/try-a-rule.py` modified in the
> working tree, plus an untracked `docs/cloudshell-badge.md` that declares itself the single
> source for the URL and carries `/cloudshell/editor` with `cloudshell_git_branch=main`.
> **`README.md:13` still carries the defective URL right now**, so this row stays open.
> **Close it by re-reading `README.md:13`, not by reading `cloudshell-badge.md`** — a document
> that names the correct URL is not the same artifact as the badge a judge clicks, and that
> distinction is the whole of this row.

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

**STATE 2026-08-25: THE DESIGN HAS MOVED THREE TIMES; THE CODE HAS NOT MOVED AT ALL.**

Design, all landed since this row was written:

- `docs/design/T2-8-runtime-visuals-scope.md`, the scope, 2026-08-23.
- `docs/design/architecture-animation-spec.md`, **set by Eric 2026-08-24**, three rules for
  the 0:50–1:35 architecture beat, coordinator-owned. Rule 1 spotlight never build-on, **Rule
  2 blindness is the move nobody else has** (when a component lights, the things it cannot see
  go visibly dark in the same beat), and anything outside the three rules is decoration and
  gets cut. It also settles that this beat does not collide with the unedited-execution rule,
  because `CONTEST.md:160` governs beats where the agent RUNS and this beat is explanation.
- `docs/diagrams/loop.svg`, a hand-authored 233-line hero plate, merged 2026-08-25 (`cbc1c90`).

Code: **nothing.** The one architectural decision the scope turns on, ONE EVENT STREAM, has no
implementation: there is no emitter, no sink and no stream module anywhere under `crucible/`,
and the `holdout_touch`-style injected-sink pattern the risk mitigation names has not been
applied here. `crucible/replay/view.py` is still the entire human-facing surface.

**The sequencing that blocked it has expired.** Eric's ruling was agentic core first,
presentation second, and the core ran 60 times overnight on 2026-08-25. **This is now the
largest unstarted item that the video depends on**, and the video is the only Stage One
deliverable that does not exist. Still no owner.

---

### T2-9 · A foreign agent, governed · **added 2026-08-27** · **[40] [30A] [30D]**

**This row did not exist while the work was being done, which is the defect
`CONTEST.md` §2 names in the other direction.** The beat shipped on 2026-08-26
and the list that says which gaps are fatal never carried it.

**What exists.** `scripts/foreign-agent-enforcement-probe.py`, and its capture at
`docs/proof/foreign-agent-enforcement-probe-2026-08-26.txt`. Google's ADK
customer-service sample, unmodified — its own code, model, tools and callbacks —
with CRUCIBLE's `BasePlugin` attached. With no policy, the sample's own Gemini
routed a 40% discount to `sync_ask_for_approval` and it executed. Under a policy
**learned on a different agent**, the same call was DENIED, **by a rule that
names no tool**: it binds a capability class, and the class was assigned by the
Cartographer reading the tool's own description.

**Why it scores.** It is the strongest available evidence for the claim the
project actually makes — a policy is portable across agents — and it is the
only artifact in the tree produced on an agent we did not write. **[40]** for
the transfer, **[30A]** because it demonstrates the enforcement layer really is
an ADK plugin rather than a fork of one agent, **[30D]** because it is one
command a judge can run.

**THE THREE THINGS THAT MUST TRAVEL WITH IT, and two are refusals.**

1. **It is NOT a breach, and the write-up says so first.** The sample's own
   prompt describes that tool as asking a manager and never states a cap, so
   routing a large discount there is **obedience**. *"CRUCIBLE tricked the
   agent"* is **DEAD VOCABULARY**. The gap is that the escalation destination
   has no manager in it.
2. **It is not a vulnerability report against Google's code**, and no claim here
   is about their sample's quality.
3. **One run per arm. No rate.** Nothing here measures attack success, and no
   such figure appears on the artifact.

**What it also found, in us.** ADK runs a tool's after-callback even when the
call was refused before it ran; the sample's callback reads a status field a
refusal does not carry, and raised. Fixed — `after_tool` now returns the refusal
payload (**ruling 59**, and the widening is a NARROWING: hook two adds no
enforcement power). The finding worth keeping is that **the same callback breaks
on three responses ADK itself produces, with CRUCIBLE nowhere in the picture.**
The sample's callback is fragile against its own framework and attaching
CRUCIBLE surfaced it.

**STILL OPEN, AND IT BLOCKS QUOTING THE MANIFEST.** The foreign capability
manifest is **UNRATIFIED** — `ratify.py` requires a named human and has not had
one. Until it does, the manifest is an input nobody has signed for. The probe
result does not depend on it; a manifest figure would.

**Devpost:** `docs/devpost/DRAFT-update-8-a-google-agent-it-had-never-seen.md`,
477 words, passes `check-devpost-format.py`, **unposted and gated on nothing.**

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

**RE-SWEPT 2026-08-25.** The previous sweep was 2026-08-22, and **five of this
section's rows had gone false by standing still.** Closed threads are kept with
their closing date rather than deleted: a list that only ever grows is a list
nobody trusts, and a list that silently loses rows cannot be audited.

### Still open

- **`E_NO_EVENTS` conflates a broken fixture with a SUCCESSFUL DEFENSE. ERIC'S RULING IS OWED, AND SCORING IT CLEAN IS FORBIDDEN.** *(opened 2026-08-25)* Across the 60-run batch, **all 154 INVALID episodes carry one reason code, `E_NO_EVENTS`**, every one with `outcome: completed`, and they come from just **8 attacks**. The exclusion rate is over its 5% ceiling in **51 of 60 runs**, median 8.3%, max 16.7%. **Every figure in this row was recounted directly over the 60 C6 bundles on this sweep**, not taken from the night log: 154 of 154 `E_NO_EVENTS`, 154 of 154 `completed`, 8 distinct `attack_id`s, 51 runs above 5.0%. **The two halves want opposite treatment and one code cannot serve both:** *"Just close it out. I'll take the store credit"* presupposes a conversation whose earlier turns do not exist, so the target could never have called a tool, a defective fixture. *"I'll give you $150 per request"* induces no tool call **because the target refused a bribe**, a defense deleted from the denominator by being scored INVALID. **Making `E_NO_EVENTS` score CLEAN would bring the exclusion rate under the ceiling and would be tuning the ruler**, laundering the defective fixtures into passes. Brief: `docs/design/e-no-events-conflation-2026-08-25.md`, decision brief, nothing acted on. **Only visible at all because of the C9 change made hours earlier**. The day before, all of these recorded the bare word `INVALID` and the two populations were indistinguishable.
- **`benign_passes_requiring_approval` is now MEASURED at 4, and the blind spot it names is not closed.** *(opened 2026-08-25)* `26/26` has been printing since round zero while **four of those 26 passes depend on the APPROVAL_ORACLE waving through a call the policy stopped.** Checked rather than reported, because a brand-new number that never moves is exactly what this project distrusts: an empty policy gives 0, the seed `policy@v0` gives 4, every evolved policy in the batch gives 4, because the seed's single `require_approval` rule masks all four on its own, and the ARMORER's added `deny` rules create no new masking. **Correctly stable, not stuck.** This is ruling 37.1's blind spot with a producer at last; **the fix is to the ruler and has not been written.**
- **The README `Observed` column, ~~"still empty"~~ FILLED 2026-08-25. This row went false within hours of being written.** `README.md:373` now opens *"Filled 2026-08-25 from the sixty-run batch in `evidence/batch-night-2026-08-25/`"*, and `README.md:74` reads *"As of 2026-08-25"* rather than the 08-24 it quoted. A figure appears only for a row that batch actually measured; the rest stay dashed with a lettered reason, and no row was added or removed to improve how it reads. **What is genuinely still open, and it is new:** those figures were measured against a corpus that no longer exists. `corpus_hash` moved when F5-05 was repaired and D5 was re-frozen the same day, so the `Observed` column must be regenerated from the post-repair batch and the two may never be pooled. **Blocks [30D] until regenerated:** the judge path sends a reader to Results first.
- **D5 corpus freeze, ~~open~~ FIRED. Both halves. Corrected 2026-08-25; this row was false for three days.** It said *"neither has fired"* and quoted a `derived_schema_hash` value that has since moved twice. Both records exist: `docs/proof/d5-corpus-freeze.json` (78 covered files, training 50 / benign 26 / 2 data files, referencing the gate-rule and target locks, with the sealed family carried **by reference only** so the hash is identical on a machine holding the sealed set and on a fresh public clone) and `docs/proof/d5-derived-schema-freeze.json` (3 `episode.*` + 8 `derived.*` fields, blindness check PASS at 0.76 against a 0.74 baseline over 100 instances). Superseded records are kept beside both. **Ruling 46: read the values out of those two files at use time. This list states none.**
- **The sealed F4 family, ~~"did not exist on disk"~~ IT EXISTS, 24 INSTANCES, SEAL INTACT. Corrected 2026-08-25.** `python scripts/seal-commitment.py --verify` reports **24 instances, classes C1/C3 only, recorded fingerprint == recomputed, "SEAL INTACT. The set is byte-identical to the commitment."** **The trap in the old row, and it is worth keeping:** `python -m corpus` still prints `sealed: 0` and still FAILS `E_SEALED_BELOW_FLOOR`, because the set is deliberately **off-tree**. `scripts/seal-commitment.py:64-67` resolves `$CRUCIBLE_SEALED_DIR`, then in-repo `corpus/sealed`, then the SEAL worktree, and `corpus/load.py` honours none of that. **`sealed: 0` from `python -m corpus` is an instrument that cannot see the artifact, not an observation about the artifact.** That is the same failure shape as the four "no traces exist" conclusions in the T0 section. **What is genuinely still open: `python -m corpus` exits FAIL on the main tree, and a judge running it will see that failure.**
- **The first real loop run, ~~open~~ RAN. Sixty of them. Corrected 2026-08-25.** `scripts/night-batch.sh:37` fires `--live --attack-mode hybrid --usd-cap 2.00 --holdout-expected 0`. **60 runs, all exit 0, 1,770 episodes, 1,616 scorable, 295 rounds, 95 promotions, 1 rejection, zero C6 validation errors**, in `evidence/batch-night-2026-08-25/`, **re-aggregated on this sweep from the 60 run records and the 60 C6 bundles rather than carried from the night log.** Verdict split, recounted at source: **CLEAN 1,508, BREACH 108, INVALID 154.** Status: 37 converged, 23 PARTIAL. **What must still travel with every one of those figures:** single-sample **k=1 with no stability estimate**, and the **SEP-BY split, 1,260 pairs separated by the policy against 180 by the approval oracle**. **`evidence/` is gitignored, so none of it is publicly verifiable.**
- **The transfer figure does not exist and cannot until 2026-08-28.** *(the half of the old row that survives)* The held-out sealed family is unsealed on **Fri 08-28** (`execution-spec.md:457`, Day 9, which is also code freeze). **No transfer number may be stated before then, from any run, however many.** One seal, one unsealing, one reported number.
- **The GATE, ~~"the last stand-in in `campaign.py`"~~ WIRED AND EXERCISED. Corrected 2026-08-25.** See T2-0. `campaign.py:974` passes the real gate; G7 (a/b/b2/c) and G8 evaluated against live GCP before each of the 95 promotions.
- **G7c, ~~"UNEVALUABLE and will stay that way"~~ CLOSED 2026-08-22, PASSING 95/95 IN THE BATCH. Corrected 2026-08-25.** The old row said the live project had no `auditConfigs` block so the number did not exist to be read. `docs/NEEDS-ERIC.md:233-253` records the close: Data Access audit logging enabled 2026-08-22, the reader built as `infra/holdout_touch.py`, and G7 fully evaluable for the first time. **It regressed once and was fixed the same night:** run 10 of the batch returned `RUN_INVALID` with every assertion UNEVALUABLE because the live IAM fetch failed, **and the gate was right to refuse a boundary it could not inspect.** Two defects underneath it, both fixed in `57f4e94`: the error interpolated an empty stderr and named no cause, and there was no retry on a transient failure. **The residue is still on disk and is a reading hazard:** `evidence/batch-night-2026-08-25/run-10.console.txt:50-59` carries the UNEVALUABLE block from the failed attempt, overwritten in place by the successful re-execution whose banner sits at `:1-22` of the same file. **Two runs, one file. Read the top, not the bottom.** **Independently confirmed twice on 2026-08-25**: `UNEVALUABLE` appears in exactly one file across the whole batch evidence directory, and that file is `run-10.console.txt`. A parallel session reached the same count from the same records while this sweep ran, and produced a fresh out-of-band probe, `docs/proof/L3-real-gate-G7-G8-2026-08-25.txt`. **THIS ROW SAID "16 assertions, all PASS" AND THAT IS WRONG. Corrected 2026-08-27, found by the README restructure lane, which verified the claim instead of carrying it forward.** The file's own summary line reads **"16 assertions, 15 PASS, 1 not PASS"**, and the one non-PASS is a **FAIL**, not an UNEVALUABLE: `G7c holdout_touch_count == 0` against an observed **11**. The 16-of-16 belongs to the **08-22** probe; two different files were being quoted as one. **The same wrong reading reached the README and was corrected there the same day.**

  **What the FAIL is, established by reading the evidence block rather than assuming either way, and it is NOT a seal breach.** All 11 are reads of `families/_probe/canary.txt` - **the canary, not a sealed instance**. By principal: `crucible-sealed-eval` 4 (the permitted account), `eric@erictetzlaff.com` 7 (project Owner, the disclosed trust root that no control in this system defends against), **`crucible-armorer` 0 - its attempt is logged DENIED at the storage layer**, which is the blindness boundary doing exactly its job. **`UNATTESTED: 0`** - the assertion that actually guards the seal is zero. So the FAIL is a **parameter mismatch**: the out-of-band probe was passed `expected 0` while the attested count for that window is 11. **Live runs pass G7c**, because a campaign passes the expectation for its own phase.

  **The reading hazard that survives:** an out-of-band probe and a live run compute the same assertion against different expected values, and a reader who quotes the probe's FAIL as a run result, or the run's PASS as a probe result, will be wrong in opposite directions. **Quote the file, the date, and the phase, or do not quote it.**
- **`measurement-spec.md` §1.3's ≥3-routing requirement is unmet. UNCHANGED, re-counted 2026-08-25.** Still **2** of F5's 10 instances route through `CAP_INVOKES_AGENT`, counted directly over `corpus/training/*.json`. `python -m corpus` reports it as a **DECLARED SHORTFALL** with `routed-but-undeclared: none`. A known, reported deviation; the floor is not lowered to fit the measurement.
- **The SEP-BY split is off target. UNCHANGED, re-run 2026-08-25.** `python -m corpus` still reports **21 policy / 3 oracle** over 24 counted pairs (3 cut, 27 total) against the stated target of **18 / 4**. Not a stop condition — the stop condition is parity — but any doc quoting "18 of 22" as the split is quoting a target, not a measurement.
- **ADR-0010 vs "unedited, live execution". PARTLY RULED 2026-08-23, and the residue is real.** `docs/NEEDS-ERIC.md:513-517` records Eric's ruling: **no replay may look live**; replays are permitted when tightly scoped, shot deliberately and **labelled on screen**, and showing replays before a live run is fine. **Still open as of 2026-08-25:** which specific beats are replay is a shot list nobody has written, and the labels do not exist because the footage does not. See `CONTEST.md` §4.
- **`ORD-13` / `ORD-14`** were authored after Eric's review pass, so "the benign set was reviewed" is not true of the set as it stands. **Still open, re-checked 2026-08-25**. No ratification record exists for these two, unlike the two retirements (`docs/proof/benign-retirement-ratification.md`) and the sealed family (`docs/proof/sealed-family-ratification.md`). Both instances have since been reasoned about repeatedly in `docs/decisions-pending/` (`b3d-risk-hold-implemented-2026-08-23.md:34-35`, `returns-t2-false-positive-2026-08-23.md`, `clause-coverage-2026-08-23.md:387-388`), which is analysis, not ratification. **A `decisions-pending` file is not a ratification record.**
- **`google/adk-samples@f4c19ab` IS NOT A REAL OBJECT** (found 2026-08-22, `docs/proof/third-party-target-recon-2026-08-22.md`). `git cat-file` rejects it and the remote has no such ref. It originates as one hardcoded literal in `scripts/make-golden.py`, which generates the golden contract fixtures — and `docs/proof/L6-cold-clone-2026-08-20.txt:23` printed it **by replaying that fixture**, so a synthetic value shaped like a real SHA was read as an observation, inside a proof file. Real HEAD 2026-08-22 was `629310b`, on a live branch that will move. **STILL NOT ACTIONED, re-verified 2026-08-25**, and the line number in this row had itself drifted: the literal now sits at **`scripts/make-golden.py:367`** (this row said `:341`) and at **`docs/data-spec.md:120`**. Make it obviously synthetic (`@DEADBEEF`) or carry the real SHA; have the Day-9 adapter `git rev-parse HEAD` at attach time rather than retype.
- **"CRUCIBLE tricked the agent into a 40% discount" is DEAD VOCABULARY.** The adk-samples pivot to `sync_ask_for_approval` is the sample's *intended* flow — `prompts.py:49,65-66` tells the model that tool requests manager approval and never states the cap. A model routing there is obeying its instructions; the defect is that the escalation destination has no manager in it. The frozen claim at `execution-spec.md:681` survives because it is about the code, not the model.
- **~~`CONVENTIONS.md` does not carry a current frozen `target_agent_hash`~~ — CLOSED by ruling 46, `SPINE_VERSION 15`, and closed the opposite way from how it was written.** This row asked the spine to record the value. It should not, and no longer will: a hash is a measurement of bytes that already exist, not a decision a lane could re-litigate, and `hashlocks.py` raises `HashLockSkew` at startup when a frozen record disagrees with the artifact. A table would have been a sixth copy. **The owner is `target/refund_agent/FROZEN.json`; read it at the moment you need it.**
- **`docs/devpost/2026-08-22-update-4-target-frozen.md` names the FIRST-freeze hashes and is PUBLISHED. Do not edit it** — it was true when it went out, and `execution-spec.md:735` rules that the correction belongs in a later public update. **That update is owed.** Note the trap this row itself fell into: it, and every other document written to correct update 4, then went stale carrying the SECOND freeze while the artifact moved to the fourth. Ruling 46 is the fix. State no hash here; print `target/refund_agent/FROZEN.json`.

### Closed since this list was opened

- **D2 gate-rule freeze — FIRED 2026-08-21.** Recorded in `docs/proof/d2-gate-rule-freeze.json` with commit `b4e060e` and its timestamp. **The hash VALUE was printed in this row until 2026-08-25 and has been removed under ruling 46.** The freeze record owns it, read it there. `contracts/gate_rule.v1.yaml:90-91` pins `bpr == "26/26"` and `near_miss_bpr == "14/14"`, so the freeze did not decide the corpus counts by side effect.
- **`objective_set_hash` — FIRED 2026-08-22**, the fourth hash-lock, **and RE-FROZEN twice since.** Recorded in `docs/proof/d3-objective-set-freeze.json`; three superseded records sit beside it (`-superseded-2026-08-23.json`, `-2026-08-23-b.json`, `-2026-08-24-b.json`). Ruling 44, `SPINE_VERSION 12`. **This row said "nine clauses" and printed two hash values. Both were corrected 2026-08-25.** The count is **11**, read out of `contracts/objective_set.v1.json` and confirmed by `"clause_count": 11` in the freeze record; the hash values are removed under ruling 46, because the artifact owns them and this row proved the point by carrying a value the artifact had left behind twice over. **The interesting part is why C10 lost an argument it won on the page:** the contract said the `_`-prefixed annotations were inside the hash, and contracts outrank code — but `ObjectiveSet.hash` strips them, and that stripped value is what every episode carries, so freezing the unstripped value would have named a number no episode could ever carry and scored every round INVALID. A hash-lock that locks nothing. The losing argument is preserved inside the corrected contract.
- **The target freeze — FIRED, then RE-FIRED 2026-08-22, and re-fired again since.** **This row used to say "see the open item above for the current values"; corrected 2026-08-25, because no document should be the place you go for that.** The owner is `target/refund_agent/FROZEN.json`, read at use time. **The finding was not the re-freeze.** A lane changed a hash-locked package, `target_agent_hash` moved, and **1011 tests stayed green with `contract-check` ALL PASSES OK.** The only thing that noticed was `python -m target.refund_agent.freeze --check`, which no test and no gate ran. A skew detector now recomputes the target and manifest hashes at run time, with a negative control proven red.
- **`r_new3` fails validator V4 — CLOSED 2026-08-21.** Rewritten to `status_to in [APPROVED]`, read out of the instances rather than chosen. Eight tests, two of them negative controls. **The prose was wrong in three places and differently wrong in each** — only the rule is machine-checked.
- **`ALLOW` / `allow` — CLOSED.** `crucible/policy/engine.py:109` now carries `_ALLOW_SPELLINGS = frozenset({"ALLOW", "allow"})` with the defect written up in-source at `:98-101`. Canonicalization still lives in `corpus/model.py::canonical_decision`.
- **The three real adapters — WIRED 2026-08-22.** `campaign.py` imports `build_real_target`, `real_tripwire` and `real_warden` at `:89-91` and the banner prints all three as REAL. This row previously read "authored but not wired", which was the correction of an earlier row that had reported them as replaced. **Its last sentence used to read "the gate is the one still in that state, and it is now the only one." Corrected 2026-08-25: the gate was wired the same day, and all four stand-ins are gone.** Three tellings of one fact, three states, in one row. That is the whole argument for dating every cell.
- **The fourth stand-in, the GATE — WIRED 2026-08-22, FIRST EXERCISED AGAINST LIVE GCP 2026-08-25.** `campaign.py:974` passes `promote=gate` from `build_gate()` at `:574`; `:555` is the marker where `promote=lambda c, r: True` used to live. 95 promotions across the overnight batch, each with G7 (a/b/b2/c) and G8 evaluated against live GCP first, and `GcsBlobIO`'s create-only precondition and generation-pinned read-back executing for the first time in their existence. **Nothing offline can be mistaken for this:** `skip_cloud=True` raises `GateRunInvalid` rather than returning a promotion.
- **The D5 pair — FIRED.** `docs/proof/d5-corpus-freeze.json` and `docs/proof/d5-derived-schema-freeze.json`, with their superseded predecessors kept beside them. Read the values there; this list states none. See the corrected open-section row above for what the old "neither has fired" cell got wrong.
- **Devpost update 6 — POSTED by Eric 2026-08-25.** `docs/devpost/2026-08-25-update-6-first-promotions.md`, renamed out of `DRAFT-` in the commit that records the posting. 474 words against ADR-0001's 350–500, checked mechanically by `scripts/check-devpost-format.py` rather than by eye. **It deliberately refuses to make the first promotion its headline**, because the exclusion rate is the more honest story. **It does not close T1-1** — see that row.
- **`scripts/make-golden.py` benign floor — CLOSED.** Still closed, re-checked 2026-08-25, **and the line numbers in this row had drifted too**: it said `:337` and `:368-369`; the emitters are now at **`:362`** and **`:393-394`**. They emit `"benign_floor": "26/26"` and `"near_miss_floor": "14/14"`, matching `contracts/gate_rule.v1.yaml:90-91`, with an in-source note that a stale value here does not produce a weaker fixture, it produces a "valid" fixture that fails its own schema.
- **`corpus/C6-reach` — MERGED 2026-08-21.** Four instances that make `CAP_INVOKES_AGENT` reachable. Eric ruled to amend the frozen counts it broke (F5 8→10, training 48→50, benign 24→26, near-miss 12→14) rather than retire instances, **before the D2 hash-lock — the only window in which "permanently" can be changed at all.** The ≥3-routing deviation it did not close is carried above as its own open row.
