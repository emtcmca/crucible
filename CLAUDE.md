# CLAUDE.md - crucible

CRUCIBLE is a pre-deployment hardening harness for AI agents that hold real
permissions. A red-team agent attacks a target agent; a pure-code tripwire records
what the target actually called; a Coroner writes autopsies but cannot propose
fixes; an Armorer emits policy patches in a three-verb DSL; a pure-code Warden and
gate promote or roll back. Built for the Google "All Things Agentic" hackathon,
track **The Fortified Enterprise Fleet**, submissions close **2026-08-31 17:00 PDT**.

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

**Updated:** 2026-08-20 · **Branch:** main · **Digest:** `claude-vault/sessions/crucible/_master.md`

**W1 COMPLETE. W2 INTEGRATION I PASSES. W3 LANES RUNNING.** Rulings **1-33**,
SPINE_VERSION **4**, **TEN** contracts. `integration` at **371 tests**,
contract-check five passes OK, tripwire selftest exit 0, devpost format check
2/2, census 11 built of 36.

**W2 — the lanes run together.** `scripts/w2-smoke.py` + `tests/test_w2_integration.py`:

```
policy@v0 (EMPTY)              policy@v1 (one hand-written rule)
  ATTACK  BREACH, executed       ATTACK  CLEAN, zero executed
  BENIGN  CLEAN                  BENIGN  CLEAN, benign work still ran
```

The last cell is the G3 check: the rule **discriminates** rather than switching
the capability off. Four lanes were each green against their own reading of the
contracts; the first end-to-end run found **four seams none of them could see**:
no parser→engine bridge · the `derived.*` **arithmetic had no owner** · nothing
stamped `objective_set_hash` onto an episode · the target's tools need
`bind_backends()`. New **`crucible/harness/`** is the coordinator-owned home for
work that belongs to no lane because it sits on a seam.

**GATE — needs Eric**
- **`integration` → `main` is a WAVE BOUNDARY.** `lanes-spec` §5: the coordinator
  does not merge across one unattended. W2 is that boundary. Everything is
  pushed and green; the merge is yours.
- **Devpost Update 2** is written and ready to paste:
  `docs/devpost/2026-08-20-update-2-contracts-hashed.md`. Outward-facing.
- **W3's L2(b)** — 48 training attacks, 24 sealed (18 is the floor), 24 benign
  with 12 near-misses. **~2.5h of reading every fixture personally.** Everything
  *around* it is being built now.

**Running now (3 lanes, unattended)**
- **L5 LOOP** — coroner, armorer, red, conductor, governor. Model calls.
- **L6 EVIDENCE** — offline replay viewer + evidence bundle.
- **L2(b) VALIDATORS** — label-blindness harness, approver lint, SEP-BY split.
  **Authoring no fixtures**, deliberately.

**Ready for D2 (Fri 08-21)**
`scripts/freeze-d2-gate-rule.py` — dry run reads `834bc7113a13beea`, matches
MANIFEST. All four refusals exercised. Update 3 drafted, **not posted** — the
trigger is the artifact, never the calendar, and its hash is the literal
placeholder `HASH_PENDING`. **ADR-0001 locks the update format** (Eric's call)
and `scripts/check-devpost-format.py` enforces it, selftest 7/7.

**Deferred until L5 merges** (would conflict mid-flight): ruling 32's second half
(`origin` out of `hashed_payload`), restriction-6 sorts on
`predicates`/`tool_names`, deleting L4's `reference_engine`, ASR denominator
calling `is_scorable()`.

**Watch out for**
- **Ask every hash-lock what change it would FAIL to notice.** One of five
  locked nothing.
- **A check satisfied by the headline is not checking the closing** — the format
  checker's own selftest caught that in itself.
- Target freeze **Sat 08-22** · cut line **Tue 08-25** · submission **Mon 08-31
  17:00 PDT**.
<!-- VAULT:SESSION-STATE end -->
