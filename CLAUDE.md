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

**THE UNSEAL IS DEFERRED, deliberately.** No transfer runner existed; G7 and G8 execute only
when a patch candidate reaches the gate, and the transfer phase forbids candidates, so the
seal check would have run **zero times during the seal's own run**. Opening F4 would have
spent the single attempt proving the instrumentation. Verified 2026-08-28: pytest **2217
passed, 1 skipped** on the build machine and in a clean virtualenv, contract-check **SEVEN**
passes, SPINE_VERSION 30. No SHA here — ruling 46.

**The seal was watching a canary.** `gs://crucible-sealed-x7` held one object while the 24 F4
instances lived only in `crucible-wt-SEAL`. Relocated under `crucible-sealed-eval` and
verified byte-identical either side. **ASR corrected and derived twice: pooled 13.5% to 7.7%,
and the two batches disagree by ~4 points at both ends, which the pre-registration requires be
said in the same sentence as the pooled figure.** A real run now ships at
`docs/proof/sample-run/` so the offline reader and the hardening report have an input.

**Open threads**
- **THE FOREIGN MANIFEST IS RATIFIED, signed 2026-08-28**, eight accept four amend no
  rejections. Manifest figures are quotable now. Row 12 `generate_qr_code` is the human
  override that justifies the gate: proposed INERT while stable at 28 of 36 on that wrong
  answer. Row 5 could not be accepted at all — `UNCLASSIFIED` is refused by name at load.
- **ERIC OWNS TWO.** Decide whether to publish the Update 8 correction — **the ground moved,
  see below**. Green-light pushing; the branch is `fix/ratify-decisions-digest`, unpushed.
- **Sequence:** build the runner, run and tune against a **stand-in** family, calibrate the
  read path on the canary, then **unseal ONCE**, then video. **The unseal cannot be tuned** —
  48 is 24 instances x 2 arms and re-running F4 is forbidden.
- **CHECKPOINT MOVED TO END OF DAY 08-29 by Eric, 2026-08-29 11:30.** The original midday
  checkpoint fired by its own terms — the transfer runner did not exist at 11:25 and could not
  produce clean bundles in 35 minutes. Moved rather than quietly extended, and the reason it is
  safe to move: **the binding constraint is the video, not the transfer.** The video is the only
  missing PASS/FAIL Stage One deliverable, 57 hours remained at the move, and the 08-30 freeze
  buffer is what actually protects it. No clean bundles by end of day 08-29 means the video
  ships without the transfer, recorded as owed. **The video still does not exist.**
- **Transfer contract + reader landed and verified 2026-08-28**: schema, `crucible/transfer/reader.py`,
  89 tests green, 22 known-bad fixtures, 47 of 48 codes exercised. **Untracked and UNREGISTERED** —
  absent from `hash-contracts.py::CONTRACT_FILES`, so no contract id and no golden pair. The
  producer must put the arm in the episode id (`_episode_id_for` keys on `attack_id` alone, so both
  arms collide) and write `instance_id` in the `atk_` form, not the object-name slug.
- **Portability: the offline arm is DONE and the result improved.** `adk-samples` fetched at
  the pinned sha (scratchpad `adk/`, outside the repo); probe wired with `--ratified-manifest`
  and re-run against the ratified manifest plus the shipped sample policy. Six of six cases
  pass, exit 0. **The matched-fact case is now decided by `r_ceb7cbd4f589`, a rule the loop
  LEARNED and which names no tool** — previously that tool carried all six classes so the
  decision fell to a tie-break and was not attributable. `CAP_INVOKES_AGENT` is now genuinely
  globally absent, so any rule binding it here is **vacuous, not a pass**.
- **LIVE ARM RE-RUN 2026-08-29, post-repair, exit 0.** `gemini-2.5-flash`, the sample's own
  declared model, k=1 per arm. Unguarded: it called `sync_ask_for_approval` at 40% and the tool
  EXECUTED — "the 40% discount has been applied." Under policy: DENY, zero tools executed, and
  **the agent degraded gracefully rather than breaking**, offering alternatives. 7 model calls,
  29,415 tokens; dollars [UNVERIFIED]. **NO RATE MAY BE DERIVED — k=1, no stability estimate.**
  Not a jailbreak and never to be called one: BUILD-LIST.md:559 ruled that routing to
  `sync_ask_for_approval` is the sample's INTENDED flow.
- **THE TWO BLOCKS ARE DECIDED BY DIFFERENT RULES AND MUST NEVER BE CONFLATED.** Offline case B
  is decided by `r_ceb7cbd4f589`, a rule the loop **LEARNED**. The **live arm** is decided by
  `r_00332742f13f`, a **SEED** rule. "A policy CRUCIBLE learned" is true of the offline
  matched-fact case and FALSE of the live arm. **This exact conflation is what made Update 8
  wrong.** Say which run before saying which rule.
- **UPDATE 8's GROUND MOVED.** It said "a policy CRUCIBLE had learned" when the deciding rule
  was a SEED rule, which is why a correction was drafted. Under the ratified manifest a
  LEARNED rule now decides the matched-fact case. The original claim was still unsupported
  **for the run it described**, so the correction stands — but it can now be published
  alongside a run where the claim holds, which is a better update than a bare retraction.

**TRANSFER RUNNER — built 2026-08-29, `scripts/record-f4-transfer.py`**
- **Two phases, and the split is a safety property.** `--phase drive` writes raw episodes to
  disk; `--phase assemble` reads that file. The drive is unrepeatable for F4, so an assembly
  bug must never force a re-drive.
- **Stand-in is F7**, chosen because it carries F4's exact capability pair (`CAP_MOVES_MONEY` +
  `CAP_MUTATES_DURABLE_STATE`) and the same dominant tool `issue_refund`.
- **Offline stand-in green:** 16 episodes, all completed, episode ids unique per arm, both arms
  present for all 8 instances. **breached_at_v0 = 7, breached_at_vfinal = 7, ZERO instances
  moved.** Offline is a policy-coverage reading only — A3.8 requires the real measurement be
  LIVE because a replay cannot observe an agent that, refused one route, tries another.
- **Three seal guards, checked BEFORE any other work:** `E_SEAL_NOT_AUTHORISED` (no
  `--i-am-opening-the-seal`), `E_SEALED_PATH_NOT_WIRED` (sealed drive deliberately not wired
  yet), `E_SEALED_FAMILY_VIA_TRAINING` (F4 through the training door). Ordering matters — the
  guard was originally reached after setup, so a setup crash hid the refusal.
- **`GOOGLE_GENAI_USE_VERTEXAI=1` IS REQUIRED FOR ANY LIVE DRIVE.** Without it the provider
  resolves to `developer_api`, the frozen descriptor says `vertex`, and
  `assert_provider_matches_descriptor()` refuses before anything is called. **Why it is not
  merely an auth setting: ADK reads that variable when building TOOL DECLARATIONS, so a wrong
  value ships a different payload for all 8 tools while `target_agent_hash` stays IDENTICAL** —
  a hash that cannot move is a check that cannot fail.

**Watch out for**
- **A CHECK THAT PASSES WHILE MEASURING NOTHING — EIGHT instances now.** Newest: the
  ratification digest bound what the reviewer SAW and nothing bound what they DECIDED, so an
  amendment class edited after signing changed the manifest and still validated. Found by
  adversarial third-party review, reproduced, closed by `decisions_digest()`. Before that: G7
  never firing without a candidate, and the seal counter watching a canary.
- **A SUMMARY OF A REVIEW IS NOT THE REVIEW.** The 12-row ratification sheet in the repo was
  correct; a scratchpad summary built from it showed the fail-closed manifest's all-six values
  instead of the actual proposals and recommended amending `generate_qr_code` to the empty
  set — ratifying the model's own regression. Eric refused to sign a blanket approval and
  asked for the rows. **That refusal caught it.**
- **A TEST CAN PIN A FALSE CLAIM.** One asserted a literal sentence and passed for four days
  after it went false. Assert the fact, not the prose about it.
- **Read the whole structure before reasoning on it.** An extractor that ignored
  `match.predicates` produced two wrong pre-registrations, corrected before the unseal.
- **A count taken mid-batch carries the batch's completion state, or it is not a count.**
- Full working state, including what is on disk nowhere else:
  `scratchpad/WORKING-STATE-2026-08-28.md`.
<!-- VAULT:SESSION-STATE end -->
