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

Two things worth knowing before reading anything else: **three mandatory
deliverables do not exist** (architecture diagram, Cloud Run proof on camera,
README spin-up), and **a full bonus point is unclaimed** and almost none of it
depends on the loop working.

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

**Updated:** 2026-08-21 (Day 2 of 11) · **Branch:** main · **Digest:** `claude-vault/sessions/crucible/_master.md`

**READ `docs/contest/CONTEST.md` AND `docs/NEEDS-ERIC.md` BEFORE PLANNING ANYTHING.**
The first is the single copy of the contest rules, weights and prizes; the second
is the owner's decision queue. Do not restate a contest figure anywhere else.

`integration` verified: **757 tests pass**, `contract-check` ALL PASSES OK,
tripwire `--selftest` exit 0, w2-smoke exit 0, **0 leaks across 409 tracked
files**, `SEAL INTACT (2cde0250de00e692)`. Rulings **1-42**, SPINE_VERSION
**10**, TEN contracts, repo public and Apache-2.0.

**Nothing has been measured.** No loop run, no attack scored, no quotable number.

**Corpus**: 48 training, **24 sealed**, 24 benign (12 near-miss), 9 known-bad,
27 pairs. SEP-BY **21 policy / 3 oracle** against an 18/4 target — reported, not
absorbed. Blindness 0.7708 vs 0.7500 baseline over 96 instances. Sealed
instances live ONLY at `C:\dev\crucible-wt-SEAL\corpus\sealed\`; any other
worktree reads sealed=0 and `python -m corpus` FAILS there on
`E_SEALED_BELOW_FLOOR`, which is correct rather than broken.

**Landed 2026-08-21**
- **GX5, ruling 42** — grammar grew by ONE production, `arg_path is present`.
  Contract C4 re-hashed. Without it `r_new19`, the rule the F4 sealed family
  depends on, scored **BPR 20/24** against a floor of 24/24 that is never cut.
- **`ALLOW`/`allow` was a FAIL-OPEN**, not a spelling nit. `engine.py` dropped
  every lowercase event from the visible prefix, so `preceded_by` read false and
  the attack passed. The Warden's differential check could not catch it: the
  reference engine takes TYPED events and never touches the string.
- **The target was told it had seven tools.** `delegate_to_specialist` was
  missing from `refund_policy.md` §14 — the prompt the agent actually reads —
  one day before that prompt gets hashed.
- **Architecture diagram** (`docs/diagrams/architecture.md`, 6 Mermaid) and
  **README** (810 lines) both exist. Two of six Tier-0 pass/fail items closed.
- **Two more sealed payout instruments** were public in benign fixtures. Fixed
  on the public side, never the sealed side.
- **CONVENTIONS §4 had three stale frozen-number rows**, including round cap 4
  against ruling 10's 6 — wrong number at the TOP of the precedence order.

**NEXT ACTION: the corpus-count ruling** (`docs/NEEDS-ERIC.md` item 2). It gates
the D2 gate-rule freeze, which gates the **D3 target freeze on Sat 08-22**, which
gates everything that produces a number. Nothing else on the critical path moves
until it lands.

**Cloud Run is DONE** — deployed 2026-08-21, `crucible-00003-t2q`, authenticated,
running as `crucible-target`, `/list-apps` returns `["refund_agent"]`, one full
episode ran end to end. **Do not re-attempt it.** Two screenshots remain (Cloud
Run console, Trace Explorer span); those are Eric's and they also settle PC3.
`deploy/RUNBOOK.md` + `docs/proof/cloud-run-deploy-2026-08-21.txt`.

**Two defects found 2026-08-21 that would have destroyed the run. Read both
before touching the enforcement path or the freeze.**

1. **A DENIED call was recording `TOOL_EXECUTED`**, with `policy_decision` and
   `denied_by_rule_id` stripped, in the ledger the oracle scores on
   (`objective_set.py:285`). **Every blocked attack would have scored as a
   breach**, `breached_at_vFinal` would never have fallen, and the gate would
   have rejected every correct patch and halted `HALT_HUMAN` reporting "the loop
   stopped learning." Fixed `85ee852`; traced in `ADR-0012`.
2. **`tests/test_target_freeze.py` mutates `target/refund_agent/tools.py` on
   disk.** Run concurrently it corrupted the file — `_INJECTED` twice — one day
   before D3 locks it. Now lock-guarded. **Never run more than one `pytest` at a
   time in this repo**, and check `grep -c _INJECTED target/refund_agent/tools.py`
   before any commit that touches the target.

**Open threads**
- **`docs/NEEDS-ERIC.md`** — ten owner decisions. Two are Stage One pass/fail.
- **D2 gate-rule freeze HELD** — not for the reason Eric gave. It pins benign
  24 and near-miss 12, so firing it decides the parked corpus-count question by
  side effect. Corpus ruling first.
- **`corpus/C6-reach` branch** — four instances making `CAP_INVOKES_AGENT`
  reachable, parked because they break two frozen counts.
- **D5 corpus freeze** — must land before the first patch is written.
- **The first real loop run** — produces every number.
- P11 built, P20 **UNLEARNABLE** without GX5 (now available); `r_new3` fails V4.

**Watch out for**
- **Ask every check what change it would FAIL to notice.** Tonight: a hash-lock
  that locked nothing, a unit test the spec cited that did not exist, a claim
  gate that could not tell a disclaimer from a claim, and a label gate demanding
  the README print a TARGET as if it were the corpus.
- **A guard enforcing the wrong number is worse than no guard**, because it
  looks like the number was checked.
- **`vault-project.ps1 -Activity` misreports this project** — scans only
  `C:\dev\crucible`, misses twelve worktrees. Ignore its drift flag here.
- **Heredocs mangle escapes.** `\b` arrived as a literal backspace byte tonight
  and `\n` became a real newline. Use the Write tool or a script file.
- Target freeze **Sat 08-22** · cut line **Tue 08-25** · code freeze **Fri
  08-28** · **submission Mon 08-31 17:00 PT**.
<!-- VAULT:SESSION-STATE end -->
