# Stage One audit — 2026-08-30

**Every row below was verified today against the artifact, not against
`CONTEST.md` §2's status column.** That column was last touched 2026-08-22 and
is eight days old; §2 records its own history of scheduling finished work and
inventing gaps, which is why the brief for this audit said to distrust it.

**Deadline: 2026-08-31 17:00 PT. Roughly 27 hours from this file's timestamp.**
Per the organiser's checklist, everything locks at the deadline — repo, video
and linked materials — so nothing on the fix list below can be done afterwards.

**Method.** Files opened and cited by path and line. Three read-only `gcloud`
calls against the live project (`run services list`, `run services describe`,
`run services get-iam-policy`) — no call touched `gs://crucible-sealed-x7`,
`CRUCIBLE_SEALED_DIR` was never set, no model was called, and no test suite was
run. One `git fetch` to compare against the real remote. One `WebFetch` of the
public GitHub blob for the architecture diagram, to see what a judge sees.

**Nothing in this repository was edited by this audit except this file.**

---

## The bad news first

| # | Deliverable | Verdict |
|---|---|---|
| 6 | Demo video | **NOT SATISFIED.** No video exists. Locked narration covers N1–N5 only (~1:43 of a planned 3:22); N6–N8 need figures that may not be quotable and N9 needs an unseal that has not happened. One 45-second beat of silent footage exists. |
| 7 | Video shows the backend on Google Cloud | **NOT SATISFIED — because there is no video.** The backend itself is verified live today. The two committed screenshots show a revision that stopped serving on 2026-08-24. |
| 5 | Architecture diagram | **SATISFIED as an artifact, BUT the diagram set is nine days stale and tells a judge the opposite of the truth on Cloud Run.** Fix is small and high-value. See below. |
| 3 | Public repository URL | **SATISFIED, but the public branch is 33 commits behind local `main`** as of this fetch. |
| 2 | Text description | **SATISFIED on coverage. Two stale sentences in it are wrong in the direction that understates the project.** |
| 8 | Hosted URL | Not mandatory. **Unresolvable by anyone but Eric** — the service is authenticated and the rules require credentials for a private URL. |

And one obligation that is not a deliverable at all:

> **`data-spec.md` §7.3 is headed "Teardown checklist — run immediately after the
> demo is recorded." Running it would breach the Official Rules.** Detail in
> §"The availability obligation" below. This is the most consequential finding
> in this audit.

---

# Part 1 — the three mandatory technology items

## Tech 1. Gemini 3.5 or newer, via Gemini API or Vertex AI

**Verified.** `grep` for `gemini-` and `gemma-` across `crucible/`, `target/`
and `scripts/`, restricted to `.py`:

| Role | Pin | Source |
|---|---|---|
| ARMORER | `gemini-3.7-flash` | `crucible/armorer/armorer.py:47` |
| RED_STRATEGIST | `gemini-3.6-flash` | `crucible/red/red.py:39` |
| CORONER | `gemini-3.5-flash-lite` | `crucible/coroner/coroner.py:43` |
| TARGET_AGENT | `gemini-3.5-flash-lite` | `target/refund_agent/agent.py:13,49` |
| CAPABILITY_CARTOGRAPHER | `google/gemma-4-26b-a4b-it-maas` | `crucible/cartographer/vertex.py:94` |

Every Gemini pin is 3.5 or newer. Transport is Vertex AI at the `global`
endpoint, pinned in code and hashed into the D3 target descriptor
(`deploy/RUNBOOK.md`, the `GOOGLE_CLOUD_LOCATION` finding).

**Dead-vocabulary sweep — one thing to know, and it is not a defect.** A
repo-wide search for `gemini-2.5-*`, `gemini-3.1-*` and bare `gemini-3-*`
returns hits in exactly three tracked places, and all three are legitimate:

- `target/refund_agent/agent.py:49` — the comment that *declares* those ids dead.
- `docs/proof/foreign-agent-enforcement-probe-2026-08-26.json:318` and
  `docs/proof/foreign-agent-enforcement-probe-ratified-live-2026-08-29.json:284`
  — `"model": "gemini-2.5-flash"` is the **third-party ADK sample agent's own
  pin**, recorded as an observation about an agent CRUCIBLE governs. It is not a
  CRUCIBLE component.

The remaining hits are in `.claude/worktrees/` (untracked agent worktrees) and
`deploy/.stage/` (gitignored, derived). No live CRUCIBLE component carries a
dead id.

**Verdict: SATISFIED.**

**One recommendation.** If the video or the submission text uses the foreign-agent
probe as evidence, do not let a `gemini-2.5-flash` string on screen be read as
CRUCIBLE's model. Say "the sample agent we governed runs 2.5; CRUCIBLE runs 3.5
and newer" in the same breath.

## Tech 2. At least one Google Agent Framework

**Verified from source, not from prose.** `google-adk==2.1.0` is pinned in
`requirements.txt`, and it is imported and used, not merely declared:

- `crucible/plugin/adk.py:78` — `from google.adk.plugins.base_plugin import BasePlugin`. This is the enforcement surface (ADR-0005).
- `target/refund_agent/agent.py:217,245` — `from google.adk.models import Gemini`, `from google.adk.agents import LlmAgent`.
- `crucible/conductor/real_target.py:323,521-523` — `FunctionTool`, `App`, `Runner`, `InMemorySessionService`.
- `crucible/conductor/campaign.py:396-397` — `BaseLlm`, `LlmResponse`.

The deployed Cloud Run service was produced by `adk deploy cloud_run`
(`deploy/RUNBOOK.md`). The official submission-form answer is **ADK**.

**Verdict: SATISFIED.** This is the strongest of the three — the framework is
load-bearing, not a dependency line.

## Tech 3. At least one Google Cloud infrastructure service

**Verified live today**, read-only:

```
$ gcloud run services list --project=crucible-hack-2026 --region=us-central1
NAME      URL                                       LATEST_READY_REVISION_NAME  TRAFFIC
crucible  https://crucible-vgp5owkxyq-uc.a.run.app  crucible-00004-gfk          100%

$ gcloud run services describe crucible ... --format="value(spec.template.spec.serviceAccountName)"
crucible-target@crucible-hack-2026.iam.gserviceaccount.com
```

Cloud Run is deployed, serving, and running under the named non-default identity
the design requires. GCS, IAM and Vertex AI are used throughout. Cloud Build and
Artifact Registry were used by the deploy (`deploy/RUNBOOK.md`, the 403 finding).
Cloud Trace is bound to `crucible-target`.

**Verdict: SATISFIED, several times over.**

**One finding, and it is an overclaim.**
`docs/devpost/third-party-disclosure.md:93-94` lists the Google Cloud services
used as: *"Cloud Run, Cloud Storage, Firestore, BigQuery, Cloud Build, Artifact
Registry, Cloud Trace, Cloud Logging, IAM, Vertex AI."* **BigQuery is not
created and no BigQuery client code exists** — `docs/diagrams/architecture.md:16`
and `docs/devpost/findings-and-learnings.md:44-46` both say so, the latter
explicitly choosing to say so rather than list it. Firestore exists but no code
in this repo reads or writes it. This is a submission-adjacent document claiming
two services the project's own honesty documents disclaim.

**Smallest sufficient fix:** in `third-party-disclosure.md` §5, move BigQuery
out and mark Firestore *provisioned, not wired* — matching the wording
`findings-and-learnings.md` already uses. Five minutes.

---

# Part 2 — the eight mandatory deliverables

## Row 1 — a track is selected

`docs/contest/CONTEST.md` §3 selects **The Fortified Enterprise Fleet**, and
`docs/contest/track-fit.md` exists with a requirement-by-requirement verdict.
`NEEDS-ERIC.md` item 4 records Eric's 2026-08-23 ruling accepting the drafted
answer. **SATISFIED.**

## Row 2 — text description: features, technologies, data sources, findings

**Verified by opening both files and grepping for the technology terms that were
the missing half.**

Coverage is now real:

- **Technologies.** `docs/devpost/findings-and-learnings.md:35-46` names all four
  Gemini pins with their roles, `google-adk==2.1.0` as the agent framework with
  the `before_tool_callback` enforcement point, Cloud Run as deployed and
  serving, and Cloud Storage's three buckets. `docs/devpost/project-story.md:77-85`
  carries the same as a table with source files.
- **Data sources.** `findings-and-learnings.md:54-71` — synthetic order ledger,
  a refund policy modeled from ten published retailer pages
  (`docs/refund-policy-research.md`), abuse patterns from return-fraud reporting,
  a 50-instance authored training corpus plus a sealed family, and the withdrawn
  Gemma-generation claim named as withdrawn.
- **Features.** `project-story.md` §"What it does".
- **Findings and learnings.** `findings-and-learnings.md`, five findings each
  traceable to a commit or file.

**Verdict: SATISFIED.**

**But two sentences in it are now false, and both understate the project.**

1. `findings-and-learnings.md:22-26` opens: *"CRUCIBLE has not measured anything
   yet. No attack round has run, no policy has been scored, and the README's
   results table is still every row a target with an empty observed column."*
   The header comment at `:15-18` says the same. That was true on 2026-08-22.
   Today `README.md:95-106` reports fifteen accepted bundles, 32 promoted rules,
   and the 13-closed / 19-no-op measurement. **The submission text tells a judge
   the project never ran.**
2. `findings-and-learnings.md:51-52`: *"The only third-party runtime dependencies
   are `jsonschema` and `PyYAML`."* `requirements.txt` now pins six:
   `jsonschema`, `referencing`, `PyYAML`, `google-adk`, `pytest`,
   `google-cloud-storage`.

**Smallest sufficient fix:** replace the two sentences with dated ones. Do not
rewrite the document — its value is that it is a build diary. Twenty minutes.
Note that item 1's replacement has to respect the claim boundary in
`README.md` and `RESULTS.md` (no rate from the 08-25 batch is quotable), so the
honest replacement is the *negative* measured finding, which is quotable and is
the more interesting sentence anyway.

## Row 3 — public code repository URL

`github.com/emtcmca/crucible`, public, Apache-2.0 (`LICENSE`, `NOTICE`).
Reachable — the GitHub blob for `docs/diagrams/architecture.md` was fetched
anonymously during this audit.

**Verdict: SATISFIED, with a live gap.**

```
$ git fetch origin && git rev-list --count origin/main..HEAD
33
$ git rev-list --count HEAD..origin/main
0
```

**The public repository is 33 commits behind the working tree.** `origin/main`
is at `514a50a`; local `main` is at `bdec098`. What a judge reads today does not
include the last two days of work — among it the adjudication gate, the review-5
through review-7 closures, the transfer runner, and the two architecture plates.
The judge-facing diff is small (`README.md` +9 lines, devpost update 9, three
SVGs, the loop player and its cue files), but the repository as a whole is not
what the builder thinks it is.

**Smallest sufficient fix:** push, before the lock. Five minutes, and it is
gated only on the same green-suite condition the session state already imposes.

## Row 4 — spin-up instructions in `README.md`

**Verified by reading `README.md:422-634` as a reader with a fresh clone**, and
by checking each dependency of each command against `git ls-files`.

The path is complete and ordered: requirements (§1), clone + `pip install -r
requirements.txt` (§2), `python -m pytest tests/` (§3), `python
scripts/w2-smoke.py` (§4), `python -m crucible.conductor.campaign` (§5). Real
output is pasted under each. Four more instrument sections live in
`MEASUREMENT.md` and the README says so.

**The gitignore question the brief raised, checked directly:**

- `evidence/` is gitignored and **`evidence/.gitkeep` is not tracked** —
  `git ls-files -- evidence/` returns zero, despite the `!evidence/.gitkeep`
  negation in `.gitignore:17`. So the directory does not exist in a fresh clone.
  **This does not break anything:** `crucible/conductor/campaign.py:636,1102`
  call `os.makedirs(..., exist_ok=True)` before writing. Verified by reading the
  code, not by running it.
- `corpus/sealed/` is gitignored and absent from a clone. The one command that
  notices is `python -m corpus`, and `MEASUREMENT.md:170-187` pastes its exit-1
  output and states *"Exit 1, and that is the correct result in a public clone
  … `sealed=0` is the seal working."* A judge is told before they see it.
- The judge-path replay at `README.md:158-163` points at
  `contracts/golden/C6-evidence_bundle.valid.json`, which **is tracked**
  (confirmed via `git ls-files contracts/golden/`), so the one command a
  stranger is asked to run from a clone does not depend on `evidence/`.
- A committed run bundle also exists at `docs/proof/sample-run/run-01.c6.json`,
  which is more than `BUILD-LIST.md` T2-7 Part A credits.

Cold-install was actually performed: `docs/proof/cold-install-2026-08-28.md`,
clean virtualenv, all pins resolved, suite identical to the build machine. The
README states its own caveat — Windows / Python 3.11.9 only, nothing licensed
about Linux.

**Verdict: SATISFIED.** This is the best-evidenced row in the set.

**One small inaccuracy.** `README.md:451-452` enumerates the pins as
*"`jsonschema==4.26.0`, `referencing==0.37.0`, `PyYAML==6.0.3`,
`google-adk==2.1.0`, `pytest==9.0.3`"* — five. `requirements.txt` holds six;
`google-cloud-storage==3.10.1` was added 2026-08-28 and the prose did not follow.
The install command is unaffected. **Fix: add the sixth name. Two minutes.**

## Row 5 — architecture diagram

**The artifact exists and renders. Its content is nine days stale, and the
staleness runs against us on the one thing Stage One tests.**

**What I verified.**

- `docs/diagrams/architecture.md` is 441 lines. `grep -n '^```'` returns opening
  fences at 40, 129, 164, 229, 342 and 399 — **six Mermaid blocks**, matching the
  claim. (The extra fence pair at 295/299 is a plain code block, not Mermaid.)
- **They render.** The public GitHub blob was fetched anonymously: GitHub emits
  its Mermaid render containers for every block and **no parse-error or "Unable
  to render rich display" text appears anywhere on the page.** Static review of
  the source agrees — `flowchart` headers, quoted labels with `<br/>`, `subgraph
  … [ … ]`, `classDef`/`class`, and `stroke-dasharray` are all valid Mermaid.
- `README.md:307-372` inlines diagram 1 under an `<!-- ARCHITECTURE-DIAGRAM -->`
  anchor, so a judge sees a rendered architecture diagram on first contact
  without following a link.
- The requirement is *how Gemini connects to backend, database and frontend*.
  Diagram 1 draws the model/code split across the whole loop; diagram 3 draws
  Vertex AI, the service accounts, the three GCS buckets, Firestore, the SQLite
  ledger, BigQuery and Cloud Run. **Backend and database are covered well.**

**Verdict: SATISFIED as a deliverable. But three of its statements are now
false, and one of them is fatal to the impression it creates.**

`docs/diagrams/architecture.md:11-24` is a table headed *"Named here and not yet
running, as of 2026-08-21"*, and diagram 3 renders those rows as dashed
**NOT BUILT** nodes:

| Line | What it says | What is true on 2026-08-30 |
|---|---|---|
| `:14` | *"Cloud Run services — **Zero deployed.** `gcloud run services list` returns nothing … There is no Dockerfile and no deploy script in the repo."* | **Service `crucible` is serving at revision `crucible-00004-gfk`, 100% traffic**, verified by `gcloud` today. `deploy/build-stage.py` and `deploy/RUNBOOK.md` exist. |
| `:17` | *"`CAPABILITY_CARTOGRAPHER` — **Not built.** No module under `crucible/` matches it."* | `crucible/cartographer/` holds nine modules and has run live three times (`docs/proof/cartographer-live-run-*.json`, `cartographer-stability-2026-08-24.json`). |
| `:22-23` | *"**Nothing has been measured.** No loop has been run end to end and no attack has been scored."* | Six batches have run; 32 rules promoted across the accepted bundles. |
| `:432-436` | *"`data-spec.md` §4.4 puts all eleven components on Cloud Run. **Zero Cloud Run services are deployed** … This is a mandatory submission requirement … **and it is not met.**"* | It is met. The diagram's own reconciliation section tells a judge that a Stage One requirement is failed. |

**Why this is the highest-value cheap fix in the audit.** Deliverable 7 is
*visible proof the backend runs on Google Cloud*. The architecture diagram — the
document a judge opens to understand the deployment — currently draws Cloud Run
as a dashed unbuilt box and states in prose that the requirement is not met. A
judge who reads the diagram and then watches the video sees the repository
contradicting its own submission.

**Also worth naming: as read on 2026-08-30 the diagram set said there is no
frontend.** Diagram 3 draws
`UI["Demo UI — crucible-ui\nNOT BUILT"]`. But the deployed service was built with
`adk deploy cloud_run --with_ui` (`deploy/RUNBOOK.md`), so **a web UI is running
right now** and `ADR-0012`'s ban on showing it on camera was lifted
(`BUILD-LIST.md` T0-3). Row 5's requirement explicitly names *frontend*. The
project has one and its diagram denies it.

**Smallest sufficient fix (30–45 minutes, no re-drawing):**

1. Change the *"as of 2026-08-21"* header to a dated *"corrected 2026-08-30"*
   block; strike the four rows above in place with the correction beside them,
   in the same struck-through style `ARCHITECTURE.md` and `AUDIT.md` already use.
2. In diagram 3, move `CR` (Cloud Run) and the Cartographer out of the
   `notbuilt` class into `live`, and add the ADK web UI as a live node.
3. Delete or strike reconciliation item 3 at `:432-436`.

Everything else on the page — the four structural claims, the IAM table, the
hash-lock timeline — I spot-checked and it holds.

## Row 6 — demo video, 4 minutes max, public on YouTube or Vimeo

**NOT SATISFIED. Confirmed three ways, as the repo's own convention requires:**

- `find` for `*.mp4`, `*.mov`, `*.webm` across the tree (excluding
  `.claude/` and `node_modules/`) returns exactly one file:
  `capture/out/N4.webm`, 3.7 MB.
- `git grep -lniE "youtu\.be|youtube\.com|vimeo\.com"` across all tracked `.md`
  and `.html` returns **nothing**.
- `README.md:43-45` still reads *"The demo video — not yet recorded, as of
  2026-08-26. Link goes here. It is the only Stage One deliverable that does not
  exist."*

### What IS ready, precisely

| Asset | State | Where |
|---|---|---|
| **Locked script, N1–N5** | **Locked 2026-08-27**, figures re-verified from source that day, amended 2026-08-29 for the N4 boundary wording. Covers 0:00–1:43. | `docs/design/narration-LOCKED-2026-08-27.md` |
| **Printable read-from deck** | **Rendered 2026-08-29 20:50** — six HTML + six PDF segments (`00-COVER`, `01-N1` … `05-N5`) plus `ALL-SEGMENTS.pdf`. | `docs/design/recording/` |
| **Captured footage** | **One beat.** `N4.webm`, recorded 2026-08-29T22:32Z, 49.7 s wall (2 s head pad + 45 s beat + 2 s tail), zero page errors, zero console errors, cue state advancing. | `capture/out/N4.webm`, `capture/out/N4.take.json` |
| **Capture harness** | Built and self-testing. Playwright, 1920×1080, `deviceScaleFactor 2`, eight postconditions (V1–V8) including "not a flat colour field" and "consecutive frames differ", with `npm run selftest` proving the checks can fail. Exit code 3 means *not measured*, deliberately not 0. | `capture/`, `capture/README.md` |
| **Animation source** | `docs/diagrams/loop-player.html` (1,282 lines) driven by `loop-cues.json`, with a `loop-cues.KNOWN_BAD.json` and `scripts/check-loop-cues.py`. | `docs/diagrams/` |
| **Cloud proof stills** | Two PNGs, captured 2026-08-21. | `docs/proof/cloud-run-console-2026-08-21.png`, `docs/proof/trace-explorer-spans-2026-08-21.png` |

### What is NOT ready, and it is most of the runtime

- **N1, N2 and N3 have no footage and the harness cannot produce it.**
  `capture/README.md` §"What this cannot capture" is explicit and correct: N1 is
  a UI that does not exist in this repo, N2 is a native terminal against the
  sqlite ledger, and N3 is a slide **that has not been authored**. All three need
  a screen recorder (OBS or Game Bar) at 1920×1080 with matching 2-second pads.
  The README also warns, correctly, against faking the terminal in a browser to
  make it capturable — N2's whole point is that the ledger really moved.
- **No narration audio exists anywhere in the tree.** The script is words on a
  page; nothing has been read aloud.
- **N6–N9 are marked BLOCKED** in `docs/design/narration-chunks.md:38-41`. N6 and
  N7 need a real bundle and a real `PatchSet`; N8's script reads "24/26" and *no
  run has produced it*; **N9 is blocked on the F4 unseal, which has not
  happened** — `README.md:229-235` states the 2026-08-28 date passed deliberately
  without an unseal and the family is still sealed.
- **N6–N8 are less blocked than that table says, and this is worth knowing under
  time pressure.** Bundles now exist (60 in `evidence/batch-night-2026-08-25/`,
  one committed at `docs/proof/sample-run/run-01.c6.json`). What actually gates
  them is *which figures may be spoken*, and that is governed by
  `README.md`/`RESULTS.md` — no rate from the 08-25 batch is quotable. So N6 and
  N7, which show a breach and a rule rather than a rate, are recordable today
  from the committed bundle. **N8, which is a rate, is not.**

### The 4-minute ceiling is not the constraint; the floor is

N1–N5 is ~1:43. That is a complete, honest, defensible video that satisfies
Row 6 and — if it includes the Cloud Run console — Row 7. **Recommendation: cut
the video at N5 plus a Cloud Run beat.** Do not chase N6–N9 into the deadline.
A short truthful video that ships beats a longer one that does not exist at
17:00 PT tomorrow, and every beat past N5 depends on either an unseal or a rate
the project has ruled unquotable.

## Row 7 — the video must demonstrate the backend running on Google Cloud

**NOT SATISFIED, and the only reason is Row 6.** The backend half is in better
shape than any document in the repo says.

**Verified live today:** service `crucible`, revision `crucible-00004-gfk`, 100%
traffic, `https://crucible-vgp5owkxyq-uc.a.run.app`, running as
`crucible-target@crucible-hack-2026.iam.gserviceaccount.com`. Deploy transcripts
at `docs/proof/cloud-run-deploy-2026-08-21.txt` and
`docs/proof/cloud-run-redeploy-2026-08-24.txt`.

**Two things to know before the camera rolls.**

1. **The committed screenshots are of a dead revision.** Both 08-21 PNGs show
   `crucible-00003-t2q`, which stopped serving on 2026-08-24 when
   `crucible-00004-gfk` took traffic. `BUILD-LIST.md` T0-3 says so in its own
   words and marks PC3 and PC4 owed again. **Filming those stills as if they
   were the running service puts a superseded revision on camera.** The console
   is live — open it and shoot the current page instead. That is ten minutes,
   not a rebuild.
2. **The `execute_tool` span is not in the captured trace facet list**
   (`BUILD-LIST.md` T0-3). Narrate *"the deployed agent's spans are in Cloud
   Trace"*, never *"here is the `execute_tool` span"*, unless someone reopens the
   console and confirms behind "Show more".

**Smallest sufficient fix:** open the Cloud Run console on
`crucible-00004-gfk` and the Trace Explorer, screen-record both live inside the
video, and narrate as above. This also converts a stale-screenshot liability into
the "unedited, live execution" the Stage Two Demo criterion asks for.

## Row 8 — hosted project URL for judges (highly encouraged, not mandatory)

**CANNOT VERIFY AS SATISFIABLE FROM THE REPO — it is Eric's decision, and the
official rules changed its shape.**

**What I verified.** `gcloud run services get-iam-policy crucible` returns:

```json
{ "etag": "BwZZ0usTSU0=", "version": 1 }
```

**Zero bindings of any kind — no `allUsers`, no `roles/run.invoker` for
anyone.** A judge cannot open that URL. That is the deliberate posture
(`deploy/RUNBOOK.md`: the service drives a paid model behind a $160 *alert* that
stops nothing).

**The rules now force a choice.** Per the official text relayed to this audit:
*"If Entrant's website is private, Entrant must include login credentials in its
testing instructions."* So the options are:

- **(a) Submit no hosted URL.** Row 8 is *highly encouraged*, not mandatory. This
  costs nothing at Stage One and avoids the conflict entirely.
- **(b) Open the service** with one `add-iam-policy-binding … --member=allUsers
  --role=roles/run.invoker` (the exact reversal is written in
  `deploy/RUNBOOK.md`) and accept unmetered spend against a budget with **no
  cap**, for a month of judging.
- **(c) Submit the URL with credentials** in the testing instructions — which
  means minting and publishing a credential for a service whose entire subject is
  agents holding permissions they should not.

**One fact that changes the shape of the standing "never link the Cloud Run URL
publicly" rule:** the URL is already published. `git grep` on `origin/main`
finds `crucible-vgp5owkxyq-uc.a.run.app` in six tracked files — `ARCHITECTURE.md`,
`deploy/RUNBOOK.md`, `docs/NEEDS-ERIC.md`, `docs/contest/CONTEST.md`, and both
deploy transcripts. The rule protects against spend, not against disclosure, and
disclosure already happened. **Decide on the spend question, not the secrecy one.**

**There is a fourth option that costs nothing and scores.** `README.md:29` already
ships an **Open in Cloud Shell** button that runs the pure-code parts in a judge's
own browser with no credential and no spend. That is a judge-testable surface, it
works today, and it can be named in the submission as such without opening the
service. `BUILD-LIST.md` T2-7 Part A (a static replay page over a committed
bundle) is now *less* blocked than that row says, because
`docs/proof/sample-run/run-01.c6.json` is committed — but building a GitHub Pages
viewer in the remaining hours is not a good trade against recording the video.

---

# Part 3 — the four obligations from the Official Rules text

## The availability obligation, and the teardown that would breach it

**This is the finding to act on first, because it is cheap and irreversible if
missed.**

The rules require: *"The Entrant must make the Project available free of charge
and without any restriction, for testing, evaluation and use … until the Judging
Period ends"* — **2026-10-01**, with winners around 10-08.

**`docs/data-spec.md:1368` is headed: "### 7.3 Teardown checklist — run
immediately after the demo is recorded."** The demo is recorded before
submission. Read literally, that instruction fires *tomorrow*. What it does:

- **Phase 2** — `gcloud run services delete` across ten named services and
  `gcloud run jobs delete crucible-sealed-eval`. The list is sourced from
  `CRUCIBLE_ALL_SAS`, and `crucible` is not among the ten names as written, but
  the *intent* is total and the verification line is `gcloud run services list`
  **MUST be empty**.
- **Phase 3** — `bq rm -r -f -d` on both datasets, `gcloud firestore databases
  delete`, and a lifecycle policy on the evidence bucket. A note reads:
  *"crucible-policies has a 14-day RETENTION POLICY … **Schedule bucket deletion
  for +15 days**"* — which from a 08-31 last write lands around **2026-09-15,
  squarely inside the Judging Period.**
- **Phase 4** — `gcloud iam service-accounts disable` on every crucible SA. The
  Cloud Run service runs as `crucible-target`. **Disabling that account stops the
  deployed backend**, whether or not the service resource is deleted.

**`deploy/RUNBOOK.md:299-305` says it again, shorter and more dangerous because
it is easier to follow:**

```
## Teardown
`data-spec.md` §7.3 covers teardown. Delete the service after the hackathon:
gcloud run services delete crucible --region="$CRUCIBLE_REGION"
```

*"After the hackathon"* is exactly the ambiguity. For the submitter the hackathon
does not end on 08-31; evaluation runs another month.

**Also implicated, from `CLAUDE.md`:** the reasoning for never locking the GCS
retention policy is written around *"a hackathon ending 08-31"* and *"two weeks
past the last write."* The reasoning is still correct — never lock it — but the
date it is built on is wrong by a month, and someone reading it as a schedule
rather than as a hazard note would tear down early.

**Verdict: NOT SATISFIED as documented.** Nothing has been torn down —
`gcloud run services list` proves the service is up — so this is a live
obligation, not a breach. **But it is scheduled in prose, in two files, with
"immediately" and "after the hackathon" as the triggers.**

**Smallest sufficient fix, and it must land before the repo locks (15 minutes):**

1. Re-head `data-spec.md` §7.3: *"Teardown checklist — **NOT BEFORE 2026-10-01**.
   The Official Rules require the Project to remain available for testing and
   evaluation until the Judging Period ends."* Change the `+15 days` note to name
   a date after 10-01.
2. Replace `deploy/RUNBOOK.md`'s *"after the hackathon"* with the explicit date.
3. Add a line to `docs/NEEDS-ERIC.md` so it survives the lock, since nothing else
   will be editable afterwards.
4. **Do not run any part of §7.3.** Not Phase 2, not Phase 3, not Phase 4.

The spend consequence is real and should be stated rather than waved past:
keeping Cloud Run, GCS, Firestore and eleven service accounts alive for a month
costs something, against a **$160 alert that stops nothing** (`CLAUDE.md`;
`deploy/RUNBOOK.md`). Cloud Run scales to zero (`Min: 0`), so the dominant
carrying cost is storage, which is small. **The rules do not permit turning it
off, so the exposure is a cost to accept, not a choice.** Setting a *real* budget
cap — as opposed to the current alert — before submission is the prudent move and
does not violate availability.

## Everything locks at the deadline

*"Once the deadline passes, everything locks — don't touch your repo, video, or
linked materials until after winners are announced."*

**Consequences for this audit's fix list, all of which are already reflected in
the ordering below:**

- The 33 unpushed commits must be pushed before **08-31 17:00 PT** or they are
  not part of the submission, permanently.
- Every documentation fix in this file (architecture diagram staleness, the two
  stale sentences in `findings-and-learnings.md`, the BigQuery overclaim, the
  teardown dates) is a *before the wall* item.
- The video must be uploaded and public before the wall, not merely recorded.
- **The sealed run, if it happens at all, has to complete and land before the
  wall.** As of `CLAUDE.md`'s session-state block the seal is intact, the
  adjudication of 24 instances is owed by Eric before the first model call, and
  the abort gate was *green and Codex-cleared by 08:00 on 08-30*. **This audit
  takes no position on whether to open the seal** — but it is worth saying
  plainly that the seal produces N9, N9 is the last beat of a video that is
  currently zero beats long, and the two compete for the same 27 hours.

## A private hosted URL requires credentials

Covered under Row 8 above. **Decision for Eric, with both constraints stated
there and the URL's existing publication noted.**

## The two submission-form fields

- **Which Google SDK.** The official list is ADK, GenAI SDK, Antigravity SDK,
  Genkit. **The answer is ADK**, and it is defensible from source, not just from
  `requirements.txt` — see Tech 2 above.
- **Project start date.** `git log --reverse` gives the first commit as
  **2026-08-20 10:45:12 -0400** (`fc3a612 Initialize CRUCIBLE repository`). The
  Submission Period opened 2026-08-03. **Inside the window, by seventeen days.**
  `docs/devpost/third-party-disclosure.md:105` already ships the command to
  re-derive it.

Both **SATISFIED / answerable**. Neither needs work.

---

# Cross-cutting: the status documents themselves

`docs/contest/CONTEST.md` is currently **modified and uncommitted** — another
session added the *"RE-VERIFIED 2026-08-30"* block carrying obligations A–F. That
block is good and is the source for Part 3 above. **But §2's status table below
it was not touched in the same pass**, so the file now contains a 2026-08-30
header sitting on top of a 2026-08-22 table that says the video is *"not recorded
as of 2026-08-22"*, row 5 is *"DONE 2026-08-21 … six Mermaid, all rendered"* with
no mention that the diagram now contradicts row 7, and row 8 is *"authenticated
as of 2026-08-22"*. The file's own warning at `:59-64` is about exactly this.

`docs/contest/BUILD-LIST.md`'s Tier 0 rows are dated 2026-08-25 and carry the
same shape of drift.

**Recommendation:** update §2's table in the same commit that pushes, and date
every cell. Twenty minutes. This is not cosmetic — §2 is the document that
schedules every other agent's work, and it is currently scheduling a diagram fix
nobody has been told about while reporting a diagram that is done.

---

# What only Eric can do, in priority order

Everything below has to land before **2026-08-31 17:00 PT**, after which the repo,
the video and all linked materials lock.

1. **Rule that the teardown does not run until after 2026-10-01, and get that
   ruling into the repo before it locks.** — *15 minutes.* Edit the two headers
   (`data-spec.md:1368`, `deploy/RUNBOOK.md:299`) and add a `NEEDS-ERIC.md` line.
   This is first because it is the cheapest item on the list and the only one
   whose failure mode is losing the prize a month after submitting.
2. **Decide the hosted-URL question: no URL, opened service, or credentials.** —
   *10 minutes.* Recommendation in this audit is **no URL plus the Cloud Shell
   button named in the submission text**, on the grounds that Row 8 is optional
   and the budget has an alert rather than a cap. Only Eric can make this call.
3. **Record the video.** — *4 to 5 hours* for an N1–N5 cut plus a live Cloud Run
   beat, including retakes. In order:
   a. Author the N3 slide (none exists) — *30 min*.
   b. Screen-record N1 and N2 with OBS or Game Bar at 1920×1080, 2-second pads,
      real terminal against the real sqlite ledger — *45 min with retakes*.
   c. Screen-record the **live** Cloud Run console on `crucible-00004-gfk` and
      the Trace Explorer. Do not reuse the 08-21 stills — *20 min*.
   d. Record narration for N1–N5 from `docs/design/recording/ALL-SEGMENTS.pdf`;
      60 s of room tone first, one take per chunk — *45 min*.
   e. Assemble against the existing `N4.webm` — *60–90 min*.
   f. Upload to YouTube as **public**, English, confirm under 4:00, and paste the
      link into `README.md:43` and the Devpost form — *20 min*.
   **Cut at N5.** N6–N8 need figures the project has ruled unquotable, and N9
   needs an unseal that competes with this task for the same hours.
4. **Push the 33 commits.** — *5 minutes*, gated on the green-suite condition
   already in the session state. Nothing a judge sees is current until this runs.
5. **Correct `docs/diagrams/architecture.md`.** — *30–45 minutes.* Four struck
   rows and two class reassignments in diagram 3, per Row 5 above. The document
   currently tells a judge that a Stage One requirement is not met.
6. **Fix the two stale sentences in `docs/devpost/findings-and-learnings.md`
   (:22-26 and :51-52) and the BigQuery line in `third-party-disclosure.md:93`.**
   — *25 minutes total.* Both are in the submission text; both currently
   understate or overstate in ways the project's own rules forbid.
7. **Update `CONTEST.md` §2's status table and date every cell.** — *20 minutes.*
   Do it in the same commit as the push so the table and the repo agree once.
8. **Answer the two form fields on Devpost: SDK = ADK, start date = 2026-08-20.**
   — *5 minutes.* Both verified above; no work needed beyond typing them.

**Item 3 is the only one that can fail on time.** Items 1, 2, 4, 6, 7 and 8 total
well under two hours. If the day runs short, do 1, 4 and 3 — the ruling, the push,
and the video — and let the documentation corrections go. A stale diagram costs
points at Stage Two. A missing video costs everything at Stage One.
