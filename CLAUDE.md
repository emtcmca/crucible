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

**W0 HAS EXITED. W1 IS APPROVED AND OPEN.** Nine contracts authored, hashed, and
committed to `contracts/` (12 files / 9 IDs) with `MANIFEST.json`, 18 golden fixtures,
six lane briefs, and a five-pass `contract-check.py` that is green and whose
`--selftest` proves each pass can fail. Rulings **1-25**, SPINE_VERSION 2. HEAD
`fbb00fa`, tree clean, remote at parity, all commits signed. No application code, no
service accounts, no IAM bindings yet.

**Open threads**
- **W1 sequence, ruled by Eric 2026-08-20:** **L1 FOUNDATION first and alone** — the
  canonicalizer gates everything that gets hashed. **Then L3 + L4 in parallel** once
  the canonicalizer is in place and active, with **L2(a) alongside them.**
- **L1's first deliverables:** the canonicalizer against
  `contracts/canonicalization.md` §3 golden vectors (10/11/12 are the negative half —
  BOM, float, and `null` must be **rejected**), then service accounts and IAM
  bindings, including the Armorer 403 to `docs/proof/armorer-403.txt`.
  **Do not delegate the IAM bindings unattended** — a wrong binding on the policies
  bucket silently destroys G8.
- **L1 owes the `corpus/sealed/` pre-commit hook before D5** — public repo makes an
  accidental `git add -f` permanent and voids the sealed-family claim.
- **D1 Devpost post** — trigger (contracts hashed) is met. Outward-facing, needs
  approval. A pre-hash post already went up, so this is the **second**.
- `data-spec.md` §7.3 teardown still calls `gcloud ai agents`, which does not exist at
  SDK 581.0.0 in GA, beta, or alpha.
- Census: **35 required negative checks, 0 built.** A lane turns its own green.

**Watch out for**
- **A search that reports CLEAN may be unable to see it.** Phrase greps miss
  hard-wrapped prose, and fixing that still misses phrases wrapping inside
  blockquotes. One string swept 4 → 9 → 14.
- **§8 rule 12: a spec states the contract, not the status.** Status assertions carry a
  date; undated is `[UNVERIFIED]`.
- **G8 grant direction inverts easily** — `crucible-gate` → `objectCreator`;
  `crucible-armorer` → no storage role. **Never lock the retention policy.**
- **`episode.*` freezes before the first user turn.** One turn moving
  `episode.account_holder_email` collapses the F4 seal.
<!-- VAULT:SESSION-STATE end -->
