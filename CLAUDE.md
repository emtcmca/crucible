# CLAUDE.md - crucible

CRUCIBLE is a pre-deployment hardening harness for AI agents that hold real
permissions. A red-team agent attacks a target agent; a pure-code tripwire records
what the target actually called; a Coroner writes autopsies but cannot propose
fixes; an Armorer emits policy patches in a three-verb DSL; a pure-code Warden and
gate promote or roll back. Built for the Google "All Things Agentic" hackathon,
track **The Fortified Enterprise Fleet**, submissions close **2026-08-31 17:00 PDT**.

## The contest — read this before planning any work meant to score

`docs/contest/CONTEST.md` is the single copy of the contest facts: dates, the
pass/fail Stage One requirements, the 40/30/30 weighting, the Stage Three
bonuses, and all nine prizes. **Do not restate a contest figure anywhere else;
link there.** `docs/contest/BUILD-LIST.md` holds the scored work in order, with
the criterion each item scores against.

This file states no contest figure and no deliverable status. **It said three
mandatory deliverables did not exist — the architecture diagram, the Cloud Run
proof and the README spin-up — and all three had been done on 2026-08-21, one of
them for a full day.** CONTEST.md names that exact failure mode: a stale row
"does not merely mislead: it schedules work that is already finished, and it
makes a finished deliverable look like a gap in the one document that exists to
say which gaps are fatal." A summary of a status file is a copy of a status
file, and ruling 46 is what copies do. **Open `docs/contest/CONTEST.md` §2 and
§5 and read the table.**

## Read this first, before any plan

`docs/CONVENTIONS.md` is the spine and is coordinator-owned. It carries the
document precedence order, the frozen numbers, the claim vocabulary, and twenty
numbered rulings. **Precedence:**

```
CONVENTIONS > contracts/ > measurement-spec > architecture-spec
            > data-spec > execution-spec > lanes-spec > build-spec
```

`build-spec.md` is an index and a narrative. It is authoritative over nothing.

When a downstream spec contradicts CONVENTIONS, CONVENTIONS wins and the
downstream document is the defect. Say so out loud rather than silently picking.

## Document set

| File | Owns |
|---|---|
| `docs/CONVENTIONS.md` | the spine: IDs, models, frozen numbers, rulings 1-20, claim vocabulary, cuts that invalidate the run |
| `docs/separability-proof.md` | the 26-pair worksheet; the `episode.*` / `derived.*` schema spec |
| `docs/refund-policy-research.md` | the target agent's modeled policy, ten sourced retailers, fourteen abuse patterns |
| `docs/measurement-spec.md` | attack taxonomy, corpus sizing, fixtures, gates G1-G8 |
| `docs/architecture-spec.md` | components, blindness boundaries, DSL grammar, round protocol |
| `docs/data-spec.md` | Firestore schemas, hashing, IAM map, BigQuery, teardown, cost |
| `docs/execution-spec.md` | the eleven-day plan, the cut line, the demo script |
| `docs/lanes-spec.md` | six lanes plus coordinator, five waves, nine contracts, the work-item loop |

## Isolation contract - this repo runs alongside other live sessions

**crucible is its own repository**, not a worktree of anything. Separate `.git`,
separate index, separate HEAD. That is the isolation boundary and it is stronger
than a worktree.

- **Run the session with cwd inside `C:\dev\crucible`.** A session rooted in
  another repo that reaches in here by absolute path resolves the wrong project,
  files vault notes in the wrong folder, and can stage a parallel session's work.
  This happened on 2026-08-20: the entire spec set was authored from a session
  rooted in `C:\dev\quartermaster`, and `/qsave` had to be re-resolved by hand.
- **Lanes get worktrees, one each, at D2.** `docs/lanes-spec.md` runs six lanes in
  parallel on branches `lane/L<N>-<slug>` with an `integration` branch. Six lanes
  in one working directory is the failure this repo cannot afford, because the
  lanes are deliberately blind to each other and a shared index breaks that
  blindness. Create them as `C:\dev\crucible-wt-L<N>` when the lane starts, not
  before.
- **Stage by explicit path, never `-A`.** Applies inside this repo too: the
  coordinator and a lane can both be live.
- **LinkedIn work belongs to the `/linkedin` session. Eric's ruling, 2026-08-22.**
  This session may PREPARE a prompt or an image brief and hand it over. It may not
  draft, renumber, render, queue, or edit a post, and it does not run `/li`.
  **Devpost is different — crucible owns those beginning to end.**
  Set after a post drafted here outside the pipeline collided with a queued post
  on id `191` and shipped without a `## First comment`, neither of which this
  session could see. Four sessions are live locally; `C:\dev\linkedin` also
  carries ~47 uncommitted status entries from an unlanded working session, so
  `git add -A` there sweeps someone else's work.

## Repo layout

```
docs/          the eight specs above. All that exists today.
spike/         GITIGNORED. Day-1 Armorer probe: grammar, policy_v0.dsl,
               breach_records/, capability_manifest.json, prompt.md,
               check.py, run_spike.py, DECISION.md
evidence/      gitignored except .gitkeep. Run bundles land here.
corpus/sealed/ gitignored. NOTE: the .gitignore entry is NOT the control.
               The real boundary is IAM - the red-team service account cannot
               read the holdout bucket.
```

## Gotchas already paid for

- **The Armorer never writes a rule ID.** A model cannot compute SHA-256. It emits
  the placeholder `r_new1`; the validator rewrites it. CONVENTIONS 2.6.
- **`episode.*` must be frozen before the first user turn and unwritable after.**
  If an in-episode turn can move `episode.account_holder_email`, the entire F4 seal
  collapses in one move. Ruling 16.
- **Counts drift between documents written the same day.** Ruling 19 said six
  schema fields against the proof's seven, hours apart. Verify on use.
- **Heredocs with typographic apostrophes plus backtick fences fail in Git Bash on
  Windows.** Use the Write tool, or a quoted-delimiter heredoc in plain ASCII.
- **A cut is not always allowed.** CONVENTIONS 9 lists cuts that INVALIDATE the
  run - collapsing services and moving the policy store to Firestore both violate
  gate G8. Struck from every cut list, permanently.

## Infrastructure names are frozen. Source them, never retype them.

`scripts/gcp-env.sh` is the single source for the project, region, suffix, bucket
names, and service-account names. Every gate script, deploy command, and
teardown step sources it. **A second copy of a bucket name is a second source of
truth**, and G7/G8 grep these literal strings, so a typo does not fail loudly. It
produces an unevaluable gate, and an unevaluable gate is a check that cannot fail
(`measurement-spec.md:813`).

Created and asserted 2026-08-20, all `us-central1`, all uniform bucket-level
access ON, all public access prevention ENFORCED:

| Bucket | Gate | Extra |
|---|---|---|
| `gs://crucible-sealed-x7` | **G7** seal integrity | |
| `gs://crucible-policies-x7` | **G8** non-self-approval | retention 14d **unlocked**, versioning ON |
| `gs://crucible-evidence-x7` | none | transcripts, final Firestore export |

`SUFFIX=x7`, `PROJECT_ID=crucible-hack-2026`. UBLA is ON everywhere on
purpose: with it off, an object ACL is a second grant path that the gates'
`get-iam-policy` grep cannot see, so the check passes while the boundary leaks.

### The grant direction on the policies bucket, which is easy to invert

```
crucible-gate     -> roles/storage.objectCreator on gs://crucible-policies-x7
                     CREATE ONLY. Not objectAdmin, not objectUser.
crucible-armorer  -> NO storage role on that bucket. Asserted == 0.
```

**The identity that AUTHORS a candidate is not the identity that PROMOTES it.**
Grant the Armorer write access there and G8's own failure text applies: *the
separation was never real*, failure mode **RUN INVALID**. This has already been
inverted once in a session prompt. The promoter is **`crucible-gate`**, never
`sa-warden`, and every service account is named `crucible-*`, never `sa-*`.

### Never lock the retention policy

A locked GCS retention policy cannot be removed or shortened by anyone, ever,
including the project owner. `data-spec.md` §7.3 tears these buckets down, and a
locked 14d policy blocks that for two weeks past the last write on a hackathon
ending 08-31. **G8 asserts the policy exists, not that it is locked.**
`infra/create-buckets.sh` refuses any argument matching `*lock-retention*` with
exit 2. Do not route around it.

<!-- VAULT:SESSION-STATE start -- autonomously maintained by /qsave, do not hand-edit -->
**Updated:** 2026-08-28 · **Branch:** main · **Digest:** `claude-vault/sessions/crucible/_master.md`

**Rebuilt from git and artifacts after a Windows Update reboot (02:34) killed the session that
did this work. Nothing was lost; nothing was narrated.** Re-verified at source 2026-08-28:
pytest **2195 passed, 1 skipped** (was 2183), contract-check **SEVEN** passes OK, tripwire and
G4 `--selftest` pass, **SPINE_VERSION 30.** No commit SHA here — ruling 46; read it with
`git log --oneline -1`.

**BOTH 20-RUN BATCHES ARE COMPLETE AND FULLY ACCEPTED.** `batch-measure-2026-08-27` (gates
ENFORCING) and its pre-registered replication `batch-replicate-2026-08-27` (identical config,
different seeds): **20 of 20 accepted by the reader in each, 0 STRUCTURAL, 0 MEASUREMENT.** They
replace the invalid `batch-gated-2026-08-27`. **The census re-record covers 50 of 50 instances,
0 powered — the "26 of 50" binding constraint is RETIRED.** Scope and headline are **LOCKED**
(`docs/contest/SCOPE-LOCK.md`): no new capability enters the submission.

**Open threads**
- **THE REPLICATION HAS NOT BEEN ANALYZED.** Nothing outside its own pre-registration
  references `batch-replicate-2026-08-27`. The first stability estimate this project has ever
  had is unread on disk, and it is what removes the k=1 caveat. Reporting rule is already
  fixed: **pooled figure, per-batch split beside it, both reported, neither dropped.**
- **Re-take `docs/design/where-we-stand-2026-08-27.md`** — its scoreboard was computed at
  **15 of 20 runs** and its own header calls it provisional.
- **Unseal F4 today (08-28)**, Outcome E pre-registered · record **08-29** · submit **08-30**.
  **The video still does not exist.**
- Update 8 (Google agent) **postable now**; Update 9 after the pooled numbers.
- Foreign manifest **UNRATIFIED** — `ratify.py` needs a named human, and no manifest figure is
  quotable until it has one.

**Watch out for**
- **A BRANCH THAT NEVER EXECUTES IS INDISTINGUISHABLE FROM ONE THAT WORKS** — four times in one
  week: the CONVERGED enum, G4, the ENFORCING null, ruling 61's empty input.
- **The exit code is not evidence — read `exit_class`.** `REJECTS` beside exit 0 is CORRECT for
  MEASUREMENT; ruling 60 removed it for STRUCTURAL.
- **A dated snapshot that names its own condition can be re-taken.** Correct a live claim;
  strike and amend a snapshot or a pre-registration, never rewrite one.
- **Orphaned agent worktree at `.claude/worktrees/agent-a23794095d002e7b9/`** carries a stale
  CLAUDE.md (SPINE_VERSION 25) and pollutes repo-wide greps — exclude it.
<!-- VAULT:SESSION-STATE end -->
