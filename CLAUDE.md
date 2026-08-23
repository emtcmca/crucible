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
## Session State (auto-maintained)

**Updated:** 2026-08-23 (Day 4 of 11) · **Branch:** main · **Digest:** `claude-vault/sessions/crucible/_master.md`

**READ `docs/contest/CONTEST.md` AND `docs/NEEDS-ERIC.md` BEFORE PLANNING ANYTHING.**

`main` verified BY EXIT CODE: pytest 0, contract-check 0, tripwire selftest 0,
`crucible.coverage` 0, **1812 collected**. Rulings **1-49**, SPINE_VERSION **18**.
**NO HASH VALUE APPEARS IN THIS BLOCK - ruling 46. Read a lock off its own record
in `docs/proof/`.**

**THE LIVE RUN IS UNBLOCKED. Every NEEDS-ERIC item that gated it is closed.**
Ruling 48 repointed two Objective Set clauses that named arguments no tool emits.
Ruling 49 fixed an oracle that scored CORRECT CONDUCT as a breach: five verdicts
moved, four of them false positives removed, one real attack lost and priced.
`objective_set_hash`, `derived_schema_hash` and C3 all moved; both prior freeze
records are ARCHIVED, not deleted. **Nothing has been PROMOTED**, so there is
still no transfer number and `GcsBlobIO` has never executed.

**Open threads**
- **THE LIVE RUN.** Checklist `docs/ops/dry-run-preflight.md`. Eric picks
  `--usd-cap`; `--holdout-expected 0`. **Then promote on SEPARATE DAYS before
  08-31** - a policy accumulating day 1 to day 5 is the honest answer to the
  track's asynchronous-operations language, and it is FALSE until something is
  promoted.
- **50 pre-registered Cartographer runs AFTER the live run**
  (`docs/design/cartographer-stability-preregistration.md`, committed before any
  call). 25 same-seed, 25 different-seed. **Decision rule is fixed; do not edit
  the pre-reg.** Then the Gemma sheet is signed ONCE. Row 12 is wrong
  (`generate_qr_code` INERT while declaring a float discount) and row 5 cannot
  load as proposed.
- **T2-8 runtime visuals**, scoped in `docs/design/`, blocked behind the run by
  Eric's sequencing. ONE EVENT STREAM, TWO RENDERERS; emitter is an injected
  no-op-default sink.
- Owed: Devpost update 5 (drafted, states no hash on purpose), story canvas
  appends (written, GitHub-linked), submission write-up, the demo video.

**Watch out for**
- **A CHECK THAT CANNOT FAIL IS THE HOUSE DEFECT.** Today: a strawman that had
  become verdict-identical to another on 18 of 18 traces while the self-test
  still called it caught. 21 pairwise guards now, falsified before trusting.
- **ARTIFACTS WRITTEN IN A PRIVATE LANGUAGE AGREE WITH EACH OTHER AND NEVER MEET
  THE TARGET.** Four so far: the clauses, the calibration fixtures,
  `policy_v_final.json`, and the golden traces' TOOL names and handles.
- **A GREP THAT FINDS NOTHING IS NOT A PROOF.** `separates_pair` was called
  unenforced by two documents; the check tests a VALUE, not a name.
- **`scripts/hash-contracts.py --help` WRITES THE MANIFEST.**
- **`pathlib.glob` on a MISSING directory returns empty rather than raising.**
- **`grep -c` returns exit 1 on a zero count.** Use a real tool's exit code.
- Backticks in `git commit -m` get command-substituted; use `-F`.
- **ONE pytest at a time**; `git add <dir>` is as bad as `-A`.
- **Merging from inside a lane worktree prints "Already up to date".**
<!-- VAULT:SESSION-STATE end -->
