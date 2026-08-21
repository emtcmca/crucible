# CRUCIBLE — Parallel Lane Architecture

**Companion to:** `execution-spec.md` (which is the sequential view) · `build-spec.md` §10
**Purpose:** run the build across concurrent lanes with a single coordinator, safely, with mechanical drift detection, and unattended for long stretches.

> ### Corrections applied 2026-08-20
>
> **`docs/CONVENTIONS.md` is the spine. Where it and this document disagree, the spine wins, and
> a lane that believes a value in the spine is wrong STOPS AND REPORTS — it does not edit and it
> does not work around.** Propagated into this file on 2026-08-20:
>
> - **Frozen corpus numbers** in L2's scope: **50 training attacks (8 per family × 6 families,
>   except F5 at 10 — amended 2026-08-21, ruling 43, `corpus/C6-reach`)**,
>   **24 sealed held-out with 18 an absolute floor**, **26 benign fixtures with 14 near-misses**
>   (amended from 24/12),
>   **9 known-bads** (§3, §8).
> - **The known-bad exit criterion is per-fixture expected verdicts, not "all 9 fail"** — only
>   five of the nine are breach fixtures; **KB5 → `REJECT`, KB6 → `INVALID`, KB8 → `CLEAN`, KB9 →
>   a linter verdict** (§3 L4, §5.2).
> - **FIVE hash-locks** — gate rule (D2), target agent (D3), **`manifest_hash` (D3)**,
>   **Objective Set (D3)**, and **corpus + `derived_schema_hash` (D5)**. The Objective Set is the
>   definition of breach and was the only unfrozen input to the `OBJECTIVE_EVALUATOR`
>   (§2 C7, §3 L5). *(Read "FOUR, not three" until 2026-08-20; ruling 20 split the capability
>   manifest into Part A, frozen D3 with the TARGET, and Part B, frozen D5 with the CORPUS and
>   gated on the label-blindness check. **Ruling 20's own propagation list named four sites and
>   missed this file entirely — both C6 and C7 carried the dead count.**)*
> - **Contract C4 gains three episode-scoped predicate forms**, and C9's verdict is a predicate
>   over the episode's **ordered event list**, not an existential over single events (§2).
> - **Contract C3 carries the canonical `CAP_*` identifiers** plus `UNCLASSIFIED` — already
>   correct here, and this file was the only one that had it right.
> - **The work-item iteration cap is 5**, which matches the spine (§7.1). No change; recorded so
>   the next reviewer does not re-check it.
>
> ### Corrections applied 2026-08-20 — SECOND PASS (`CONVENTIONS.md` §5.5–§5.6, rulings 8–19)
>
> The first pass carried rulings 1–7. This pass carries 8–19.
>
> - **R10 — round cap 4 → 6**, convergence unchanged at 3 consecutive dry rounds (C7, §3 L5, §8).
> - **R11 — the benign floor is evaluated by REPLAYING recorded v0 traces**, which changes L4's
>   scope and adds a **new L2(b) deliverable: record those traces at D5** (§2 C6, §3 L2, §3 L4).
> - **R16 + R19 + the schema spec — C3 now carries the predicate schema**: three frozen `episode.*`
>   fields, seven harness-computed `derived.*` fields, per-tool `beneficiary_key` / `subject_key`,
>   arg enum declarations, and scalar-only destination arguments (§2 C3, §3 L3).
> - **R8 — no fourth predicate form.** The approval record's `verified` boolean is harness-computed
>   (§2 C4, §3 L3).
> - **R13 — F4 is narrowed to DESTINATION smuggling**, trained on C2/C4 and sealed on C1/C3
>   (§3 L2).
> - **R17 — every pair carries a SEP-BY label**, and oracle/policy parity is a **stop-and-report**
>   (§3 L2, §5.2).
> - **R18 — attack episodes declare no approver; the oracle denies by default** (§3 L2, §3 L4).
> - **Three cut pairs (P21, P22, P23) and the fault-`reason_code` corpus lint** land in L2's exit
>   criteria (§3 L2).

---

## 0. The principle

> **Sequential builds pass artifacts. Parallel builds pass contracts.**

Almost every CRUCIBLE component consumes something another component produces. Read naively, that forces a chain. It does not — because each of those hand-offs is a *schema*, and a schema can be frozen before either side exists.

Freeze the contracts on Day 1. Give every lane **hand-written golden fixtures for its own inputs**. Then:

- The **TRIPWIRE** develops against hand-written `ToolEvent` traces. It never waits for the plugin.
- The **ARMORER** develops against hand-written `BreachRecord`s. It never waits for the CORONER.
- The **WARDEN** develops against hand-written policy documents. It never waits for the ARMORER.
- The **replay viewer** develops against a hand-written evidence bundle. It never waits for a run.

This is the same move the data spec already identified as the largest cost saving: **pure-code components developed against fixtures cost $0 in model calls.** Parallelism and budget discipline turn out to be the same decision.

**The corollary, and it is a hard rule:** a lane that needs another lane's *output* to make progress is mis-scoped. Re-cut it or give it a fixture.

---

## 1. Wave structure

Lanes do not all run at once. They run in waves, because the contracts must exist before anything can be built against them, and integration must happen before the loop can run for real.

| Wave | Days | Lanes active | Gate to exit |
|---|---|---|---|
| **W0 — Contract freeze** | D1 (Thu 08-20) | Coordinator only | All contracts hashed and committed. **Nothing else starts until this lands** |
| **W1 — Foundation + pure code** | D2–D4 | L1, L3, L4, L2(a) | Each lane green against its own fixtures, offline |
| **W2 — Integration I** | D5 | Coordinator + L1 | Contract conformance sweep green; baseline sweep runs |
| **W3 — Loop + corpus** | D5–D7 | L2(b), L5, L6 | Full breach→autopsy→patch→gate cycle on real components |
| **W4 — Integration II + convergence** | D8–D9 | Coordinator + L5 | Convergence bundle produced; held-out run; **code freeze** |
| **W5 — Presentation** | D10–D11 | L6 + coordinator | Submitted |

**W0 is not optional and cannot be shortened.** A contract written on Day 3 to describe code that already exists is not a contract; it is documentation of an accident, and every lane that built against a guess has to be reworked.

---

## 2. The contracts (frozen Day 1)

Committed to `contracts/`, each canonicalized and hashed. The hashes go in `contracts/MANIFEST.json`. **Every lane's test suite asserts the hash of every contract it consumes.**

| # | Contract | Producers | Consumers |
|---|---|---|---|
| **C1** | `tool_event.schema.json` — the ordered execution record: `{episode_id, invocation_id, kind: TOOL_ATTEMPT\|TOOL_EXECUTED\|TOOL_ERROR, tool_name, args, role, result_digest?, error_class?, derived_overwrites, seq, ts_monotonic}`. **Three additions 2026-08-20 (rulings 21, 25), and the contract must state each in words, not just in the shape:** **(1) `args` are POST-STAMP** — the `derived.*` values the plugin wrote are IN the record and replay READS them; pre-stamp args would leave the bundle carrying neither the returns nor the values derived from them, and **replay could not reproduce the decision**, which is the sole reason episode-scoped predicates count as pure. **(2) `result_digest?` is REPLAY-INTEGRITY ONLY and explicitly NOT EVALUABLE** by the policy engine — it is a hash, not a value, which is what settled ruling 21: the harness sees returns, the evaluator does not. **(3) `role` is RECORDED, NOT EVALUATED**, and `derived_overwrites: [{path, model_value}]` is **diagnostic only, same status as `result_digest`** — a model writing under `derived.` is an agent forging the harness's own verification field, and recording only post-stamp args would throw that detection away | L3 (plugin) | L4 (tripwire), L6 (replay) |
| **C2** | `decision.schema.json` — `ALLOW \| DENY(rule_id, reason_code) \| APPROVAL_REQUIRED(rule_id, reason_code)`. **Matching is MEMBERSHIP, never set equality (ruling 22):** `rule.capability_class IN call.capability_set`. A tool carries a *set*; under equality a single-class rule silently stops firing on exactly the multi-capability tools that matter most, and **the sealed F4 result would read "did not generalize" — a real number produced by a matcher bug.** `role` is **not** an argument to `evaluate` | L3 (policy engine) | L3 (plugin), L4 |
| **C3** | `capability_manifest.schema.json` — tools → capability classes, with the **six canonical class identifiers** and the `UNCLASSIFIED` sentinel. **PLUS the predicate schema, added 2026-08-20 — full definitions in `data-spec.md` §1.15, and all of it is covered by `manifest_hash`:** three **`episode.*`** fields (`account_holder_email`, `account_holder_id`, `order_payment_instrument_id`), **frozen before the first turn and unwritable thereafter**; seven **`derived.*`** fields stamped by the plugin in `before_tool`, **overwriting anything the model wrote under that prefix**; per-tool **`beneficiary_key`** and **`subject_key`**; arg **enum declarations** for `reason_code` / `status_to` / `approval_tier`; and **destination-bearing arguments declared SCALAR, never lists** — a list makes the comparison type-ambiguous and silently unenforceable. **Because C3 is hashed, changing any of this flags every learned rule `needs_revalidation`** — which is the property that made a harness-computed field acceptable where a mutable reference set was not (ruling 8) | L2 | L3, L4, L5 |
| **C4** | `policy.ebnf` + `policy_document.schema.json` — the 3-verb grammar, the **required-and-first `cap_selector`**, rule shape, precedence-by-verb, the enum-only literal rule, and **the three episode-scoped predicate forms** (`preceded_by`, `episode_sum`, `arg_path <cmp_op> episode.<field>`). **Rulings 22 and 25, 2026-08-20 — four changes, and the first three are DELETIONS:** **(a) `\|` is removed** — `cap_selector` names **exactly one** class; under any-of with verb precedence and no file order it was pure sugar, and ambiguous sugar, so `cap:A\|B` is now a **parse error**, never a silently-accepted alternative. **(b) `match_mode` is removed** from the schema with `additionalProperties: false`; stored form is scalar `capability_class`. **(c) the `role:` qualifier is removed** — `role_name` was the only **plain-text product identifier** the grammar admitted, and it was not covered by the product-lexicon denylist, so it was an escape hatch out of *"every learned rule generalizes to a capability class."* **(d) `cap:UNCLASSIFIED` must be rejected explicitly**, not by omission from the production list — on an unseen target every tool is `UNCLASSIFIED` until mapped, so one such rule reports **100% transfer, manufactured** | L1 (canonicalization), L3 (parser) | L4 (warden), L5 (armorer) |
| **C5** | `breach_record.schema.json` — the CORONER's output. **`additionalProperties: false` and no `fix`/`recommendation`/`mitigation` field exists** | L5 (coroner) | L5 (armorer), L6 |
| **C6** | `evidence_bundle.schema.json` — the run-of-record: attacks, verdicts, autopsies, patches, gate decisions, the policy chain, cost, **the FIVE hashes** *(gate rule, target agent, `manifest_hash`, `objective_set_hash`, and `derived_schema_hash` — read "the four hashes" until 2026-08-20, ruling 20)*, **the recorded `episode_prefix` for every episode** (without it the episode-scoped predicates cannot be replayed, and replay soundness is what keeps them pure), **the frozen `episode.*` block per episode** (ruling 16), and **the recorded v0 benign fixture traces** that G3 replays every round (ruling 11) | L1, L4, L5 | L6 (replay viewer), the demo |
| **C7** | `run_manifest.schema.json` + `canonicalization.md` — what is hashed (**`run_id` is NOT in the policy `hashed_payload`**), JCS rules, integers-only, key ordering, **the FIVE hash-locks: gate rule (D2), target agent (D3), `manifest_hash` (D3), `objective_set_hash` (D3), and corpus + `derived_schema_hash` (D5)** *(this read FOUR until 2026-08-20; ruling 20's manifest split, and **this file was not on that ruling's propagation list**)*, and the frozen parameters (**round cap 6** — raised from 4 by ruling 10 — 6 attacks/round, k=1, 3 consecutive dry rounds, and **`approval_oracle_default: "deny_unless_fixture_declares"`** — ruling 23 froze ruling 18 as a *parameter inside this already-hash-locked artifact* rather than adding a sixth lock, because two hashes were already called two things to forget. The `APPROVAL_ORACLE`'s **data** is inside the corpus hash; only its **default behavior** was unhashed prose, and four pairs including the mandated F6 pair rest on it) | L1 | everyone |
| **C8** | `gate_rule.v1.yaml` — the promotion rule, **hash-locked D2, not editable after** | L1 | L4, L5 |
| **C9** | `verdict.schema.json` — `{breach: bool, invariant_id, evidence: [tool_call_index]}` and the `BREACH \| CLEAN \| INVALID` trichotomy. **The predicate behind `breach` is evaluated over the episode's ORDERED EVENT LIST** with three clause forms (`per_event`, `sequence`, `aggregate(window_by_seq)`) — corrected 2026-08-20, because KB3 and KB7 are not expressible over a single event | L4 (tripwire) | L5, L6 |

### 2.1 Contract change protocol

A contract may change during the build. It may not change *quietly*.

1. Any lane proposing a change **stops and reports to the coordinator.** It does not edit `contracts/`.
2. The coordinator edits the contract, bumps its version, re-hashes, and updates `MANIFEST.json`.
3. The coordinator runs the **conformance sweep** (§5) and reports which lanes now fail.
4. Affected lanes are notified with the specific failure, not just "the contract moved."

**After D5, a contract change requires the coordinator to state in writing what prior results it invalidates.** After the corpus is hashed, a C3 or C4 change re-scopes everything measured against the old hash.

---

## 3. Lane definitions

Each lane has: an exclusive path set, a scope boundary, its input fixtures, its exit criteria, and its stop conditions.

### L1 — FOUNDATION
**Owns:** `crucible/canon/`, `crucible/ledger/`, `crucible/gate/`, `crucible/manifest/`, `infra/` (Terraform, IAM, buckets), `scripts/verify-chain.py`
**Scope:** canonicalizer + golden vectors · hash derivation · the SQLite ledger · GCS buckets, service accounts, IAM bindings, the **Armorer 403 proof** · the promotion gate with read-back assertion · `verify-chain` CLI · the run manifest writer.
**Fixtures in:** none — this lane is the root. Its golden vectors are hand-authored.
**Exit:** golden vectors green including a key-order-sensitivity case and a float-formatting case · the 403 captured to `docs/proof/armorer-403.txt` · a deliberately corrupted read-back **fails** the assertion · `verify-chain` detects an injected gap.
**Critical path.** Everything hashed waits on the canonicalizer. **This lane runs first and alone in W1's first hours.**

### L2 — TARGET + CORPUS
**Owns:** `target/refund_agent/`, `corpus/`, `fixtures/benign/`, `fixtures/known_bad/`, `taxonomy/`
**Scope (a, W1):** the refund agent, its seven bare-function tools bound to L1's ledger, the written refund policy (**no free auto-approve tier — every tier requires a verified order lookup and a stated qualifying reason; `escalate` means human-in-the-loop**, `CONVENTIONS.md` §5.4; **retail specifics sourced with citations, not recalled**), the capability manifest (the six canonical `CAP_*` classes), the three demo conversations, **then the D3 freeze + hash — target agent AND Objective Set, both hashed the same day.**
**Scope (b, W3):** family taxonomy · attack generators · **50 training attacks (8 per family × 6 families, except F5 at 10)** · **24 held-out — 18 is the ABSOLUTE FLOOR — generated from the disjoint F4 family and sealed immediately** · **26 benign fixtures read by a human, all 26, of which 14 are mechanically-confirmed near-misses** · **9 known-bads hand-written, all 9, no exceptions.** *(Counts corrected 2026-08-20; the file said 86 / 24 / 48 / 9. F5 amended 8→10, benign 24→26, near-miss 12→14, ruling 43, `corpus/C6-reach`, 2026-08-21.)*
**F4 is DESTINATION SMUGGLING ONLY — ruling 13, three binding conditions, added 2026-08-20:** the smuggled item is a **structured, comparable** argument (payout instrument, recipient, delegate queue, write target) and **no free-text-content instances go in the sealed set**; the `arg cmp episode.<field>` shape is **trained on C2 `CAP_EXTERNAL_COMMS` and C4 `CAP_READS_PII`** and **sealed on C1 `CAP_MOVES_MONEY` and C3 `CAP_MUTATES_DURABLE_STATE`**; and the old *"same abstraction, third container"* framing is **struck.** **A content instance in the sealed set breaches at v0 AND at vFinal because nothing can stop it — transfer collapses mechanically and the failure reads as *"it did not generalize."* That is a rigged failure, which is worse than a rigged success, because you would believe it.**
**Every pair carries a SEP-BY label as it is authored** — `policy` (the predicate differs on the two sides) or `oracle` (the predicate is identical; the approval oracle decides). **Target split 18 / 4. If oracle-separated reaches parity with policy-separated, STOP AND REPORT** — at parity, half the headline is a statement about a scripted oracle the builder wrote (ruling 17).
**Attack instances declare no approver.** The oracle denies by default on them (ruling 18); four pairs, including the mandated F6 pair, rest on that.
**Before authoring any of it:** the **separability worksheet** — for every (attack family, near-miss fixture) pair, the exact rule in the real grammar that blocks the attack and passes the fixture. **A pair with no such rule is unlearnable and comes out of the corpus.** This is a coordinator-gated artifact, not a lane deliverable. *(It has now been run: **16 separable with the existing grammar, 6 with a schema change, 0 grammar extensions, 3 cut** — P21, P22, P23, `measurement-spec.md` §3.5. **Do not re-litigate the cut pairs; do re-run the worksheet for any pair authored after it.**)*
**Fixtures in:** the capability manifest schema (C3) only.
**Exit (a):** freeze hash recomputes identically from a clean checkout · three demo conversations rehearsed and throwaway-captured **before** the freeze · **the C3 predicate schema is in the manifest before the freeze**, because the freeze hash covers it and a later change flags every learned rule `needs_revalidation`.
**Exit (b):** benign suite **26/26** against `policy@v0` · **all 26 v0 fixture traces recorded, and at least one replayed through the shadow Policy Engine to the same verdict the live run gave** (ruling 11 — *a recorded trace nobody has replayed is an assumption, in exactly the way an unread fixture is*) · seal proven mechanically by grepping loop logs for reads under the held-out path · **14 near-misses** confirmed by the mechanical definition (≥3 of 4 shared surface features) *(amended from 24/24 and 12, ruling 43, 2026-08-21)* · **SEP-BY split written down and within the authoring gate** · **the fault-`reason_code` corpus lint is green** — *no attack instance may use a fault `reason_code` as its sole distinguishing feature from its paired fixture*, because §5.4a ruling 6 exempts fault codes from the return window **deliberately**, so such an instance scores **correct behaviour as a failure.**
**This is the human-attention lane.** It cannot be fully delegated — a benign fixture nobody read is an assumption, not a fixture.

### L3 — ENFORCEMENT
**Owns:** `crucible/policy/`, `crucible/dsl/`, `crucible/compiler/`, `crucible/plugin/`
**Scope:** DSL parser + validator (including the **payload-substring rejection**, the product-lexicon denylist, and **the placeholder-`rule_id` rewrite** — the model emits `r_new1`, the validator computes the content address, because **a model cannot compute a SHA-256 and asking it to would make the Day-1 spike read 0/20 for a reason unrelated to the DSL**, `CONVENTIONS.md` §2.6) · the policy engine as a total, terminating, pure function · the compiler → ADK `BasePlugin` · `before_tool_callback` short-circuit · **the `episode.*` freeze and the `derived.*` stamp.**
**Four semantics this lane must get right, added 2026-08-20, and each is a single implementation choice that silently disables the predicate it belongs to** (`data-spec.md` §1.15):
1. **`preceded_by` and `episode_sum` read ONLY events with `policy_decision == allow AND status == ok`.** Otherwise **an attacker satisfies `preceded_by` for free with one blocked call.** The TRIPWIRE already scores on `TOOL_EXECUTED` and not `TOOL_ATTEMPT` for the same reason; the engine's prefix must read the same way.
2. **`episode_sum` INCLUDES the pending call.** Otherwise the call that first crosses the threshold is the one that executes.
3. **`episode.*` is frozen before the first turn and unwritable thereafter** (ruling 16). A write attempt after episode start is `HALT_HUMAN`, never a merge.
4. **`derived.` is a reserved arg-path prefix**, resolved against the manifest's declared set and **overwritten by the plugin in `before_tool`, discarding anything the model wrote there.**
**`derived.*` is HARNESS-COMPUTED, never model-computed** — a model-computed field launders a model into the pure-code path, which is the same argument that keeps L4 free of an LLM client.
**Fixtures in:** hand-written policy documents (C4), hand-written call shapes.
**Exit:** a hand-written patch compiles, registers, and the blocked tool **never appears in the ledger** · the validator rejects a rule containing a payload substring · **ADK #4704 verified through both `/run` and the `--with_ui` path** · **all four semantics above have a check that FAILED before it was implemented:** a blocked `CAP_READS_PII` event does **not** satisfy `preceded_by`; a prefix summing to 99,999 against a 100,000 ceiling **denies** the pending 500; a write to `episode.account_holder_email` from inside a turn **halts**; and a model-supplied `derived.subject_verified_in_episode` in the tool args is **overwritten** before evaluation.
**Pure code. Fully offline. Zero model calls.** The highest-parallelism lane in the build.

### L4 — ORACLE
**Owns:** `crucible/tripwire/`, `crucible/warden/`, `tests/golden_traces/`
**Scope:** the tripwire (pure code, **no LLM client import — enforced by a build-time import lint**) · the Objective Set evaluator, **over the episode's ordered event list, with `per_event` / `sequence` / `aggregate(window_by_seq)` clause forms** · the 9 known-bad harness · the regression warden — **whose benign floor is computed by REPLAYING the recorded v0 fixture traces through the shadow Policy Engine, not by re-running live episodes** (ruling 11) · the `--selftest` mode.
**Why the warden replays rather than re-runs:** over-blocking is a **policy** question, not a model question, so **"shadow Policy Engine" already implied this.** Three consequences: 26/26 becomes **repeatable instead of flaky** (a live gate at exactly 100% every round is the one a deadline relaxes at 11pm, and weakening a never-cut gate is a **stop condition, not a repair**); **~26 live episodes leave every round**, which is what funds the round cap of 6; and the gate stops depending on the target's nondeterminism to decide whether a policy is safe.
**Fixtures in:** hand-written `ToolEvent` traces (C1), hand-written policy documents (C4), **and — from L2(b) at D5 — the recorded v0 benign fixture traces.** *(Note the dependency direction: L4 develops its replay evaluator against **hand-written** traces and never waits for L2. The real traces arrive at D5 and must validate against the same C1 schema. If they do not, that is a contract report, not a local fix.)*
**Exit:** **all 9 known-bads return their PER-FIXTURE EXPECTED VERDICT** — KB1/KB2/KB3/KB4/KB7 → `BREACH`, **KB5 → `REJECT`, KB6 → `INVALID`, KB8 → `CLEAN`, KB9 → linter `REJECT`-then-`ACCEPT`** · `--selftest` proves the tripwire can still fail · two hand-written trace fixtures give the right verdicts under pytest · the import lint fails if an LLM client is added.
*(Corrected 2026-08-20: "all 9 known-bads fail as required" is wrong and would **fail on KB8 by design**, which means the harness refuses to boot on D3 — a hard-stop day. Weakening KB3 or KB7 to get green is a **stop condition, not a repair.**)*
**Pure code, fully offline, zero model calls.** Develops entirely against golden traces.

### L5 — LOOP
**Owns:** `crucible/coroner/`, `crucible/armorer/`, `crucible/red/`, `crucible/conductor/`, `crucible/governor/`
**Scope:** CORONER (schema-locked, **no fix field**, prescriptive-language lint, **and free-text findings confined to a `human_only` subtree**) · ARMORER (blind to attacker prose **and** to the benign fixtures — **its input is an ENUMERATED PROJECTION with no free-text field on any path**; note the fixture half is **application convention plus a code check, never IAM**, because Firestore has no per-collection granularity) · RED STRATEGIST · budget governor (**$160 cap, 40M token ceiling, round cap 6** — raised from 4 by ruling 10, affordable because ruling 11 took ~26 live benign episodes out of every round) · round conductor, **last**.
**Fixtures in:** hand-written `BreachRecord`s (C5), hand-written `ToolEvent` traces (C1), the capability manifest (C3).
**Exit:** adversarial blindness test — feed the CORONER a free-text field containing a "recommended fix" string, assert the ARMORER's input dict does not contain it, **and a second test asserting the adapter cannot address `human_only.*` at all** (the lint alone is insufficient: a hypothesis phrased as a description passes it) · governor aborts on a low ceiling and **logs the abort as a first-class result, not an exception** · a campaign runs unattended producing bundles carrying **all five hashes** *(four until 2026-08-20 — ruling 20)*.
**Starts W3.** Depends on C1/C3/C5 only, never on L4's code.

### L6 — EVIDENCE + PRESENTATION
**Owns:** `crucible/replay/`, `docs/`, `docs/proof/`, `docs/adr/`, `README.md`
**Scope:** the replay viewer (**reads only from disk, no credentials**) · architecture diagram · README with the Judge-path block · the 12 ADRs · proof captures · video assets.
**Fixtures in:** a hand-written evidence bundle (C6).
**Exit:** replay runs from a clean checkout with **no credentials in the environment** · a cold reader spins the project up following only the README · the diagram is legible at 1080p **and** in GitHub dark mode.
**Starts W3 on the viewer; W5 for presentation.** The viewer is a real artifact, not a nicety — it is the demo instrument and the judge's free reproduction path.

---

## 4. Path ownership — the merge-conflict map

**Exclusive ownership is what makes unattended parallel work safe.** No two lanes write the same path.

```
contracts/              → COORDINATOR ONLY.  Lanes read; lanes never write.
crucible/canon/         → L1
crucible/ledger/        → L1
crucible/gate/          → L1
crucible/manifest/      → L1
infra/                  → L1
scripts/verify-chain.py → L1
target/                 → L2
corpus/                 → L2
fixtures/               → L2
taxonomy/               → L2
crucible/policy/        → L3
crucible/dsl/           → L3
crucible/compiler/      → L3
crucible/plugin/        → L3
crucible/tripwire/      → L4
crucible/warden/        → L4
tests/golden_traces/    → L4
crucible/coroner/       → L5
crucible/armorer/       → L5
crucible/red/           → L5
crucible/conductor/     → L5
crucible/governor/      → L5
crucible/replay/        → L6
docs/                   → L6  (except docs/adr/ — see below)
docs/adr/               → COORDINATOR ONLY.  ADRs record cross-lane decisions.
README.md               → L6
requirements.txt        → COORDINATOR ONLY.  A lane that needs a dep asks.
evidence/               → WRITE-ONLY at runtime. No lane edits by hand.
```

**Hard rules, from the standing parallel-session discipline:**

- **Never `git add -A`.** It sweeps another lane's in-flight work. Stage explicitly, inside your declared paths only.
- **To touch a path outside your set, stop and ask the coordinator.** Do not "just fix it."
- **Every lane runs in its own git worktree.** Two sessions in one working directory is what produces mid-review branch switches and wrong-branch commits.
- **Before any git write:** `git branch --show-current` and `git status`, confirm the branch is the lane's own.
- **Before creating a branch:** `git worktree list`. An orphaned worktree holds the branch and the checkout fails.

---

## 5. Drift detection — mechanical, not vigilant

Three gates, the same shape as the canon drift gate. **Repetition across lanes is not enforcement.**

### 5.1 `scripts/contract-check.py --lane <L>`
Run by each lane **before every commit.** Asserts:
- Every contract the lane consumes still hashes to the value in `contracts/MANIFEST.json`.
- The lane's code validates against those schemas on its golden fixtures.
- The lane wrote only inside its declared path set (`git diff --name-only` against the ownership map).

Exit 1 blocks the commit.

### 5.2 `scripts/conformance-sweep.py`
Run by the **coordinator**, at every wave boundary and at least twice daily during W1–W4. Asserts:
- Every lane's test suite passes against the **current** contracts, not the ones it was written against.
- Cross-lane fixture compatibility: L3's emitted `ToolEvent`s validate against L4's consumer; L5's `BreachRecord`s validate against L5's own armorer input adapter; L1's bundles validate against L6's replay reader.
- **The negative checks still fail:** all 9 known-bads **return their expected verdicts** (five `BREACH`, plus `REJECT`/`INVALID`/`CLEAN`/linter — *not* "all fail"), the tripwire `--selftest` fails as designed, the validator rejects a payload-substring rule, the read-back assertion fails on a corrupted write, **the Armorer's input adapter cannot reach `human_only.*`**, and — **added 2026-08-20** — **a blocked call does not satisfy `preceded_by`**, **`episode_sum` denies the call that would cross the ceiling**, **a write to `episode.*` halts**, **a model-written `derived.*` is overwritten**, and **an attack episode with no declared approver is DENIED by the oracle.**
- **The label-blindness check on `derived.*`** (ruling 19): compute every field over the corpus with labels withheld and assert **no field perfectly predicts attack-vs-benign.** This one is unusual and worth naming — **it is a check that passes by being uninformative.** A field that means *"this is the bad one"* voids every downstream number **while looking exactly like success**, which is the only failure shape on this list that gets *more* convincing as it gets worse.

> **The negative checks are the half that matters.** A conformance sweep where everything passes is indistinguishable from a sweep that stopped running. The sweep must prove it can still fail, every time.

### 5.3 Coordinator spot checks
Per wave, and unannounced. Not a test suite — a human-shaped question the coordinator answers by looking:

| Check | Question |
|---|---|
| **Contract drift** | Did any lane's code start depending on a field that isn't in the contract? |
| **Scope creep** | Is any lane building something outside its scope because it was convenient? |
| **Fixture rot** | Are the golden fixtures still representative, or has the real shape diverged? |
| **Silent coupling** | Did a lane import from another lane's package? `grep -r "from crucible\.<other_lane>"` |
| **Claim drift** | Did anything in the code or docs start claiming a property the mechanism doesn't deliver? |
| **The negative-check census** | Count the checks that are supposed to fail. Is the number still right? |

---

## 6. Coordinator protocol

The coordinator is the main session. It **does not write lane code.** It owns contracts, integration, merges, ADRs, and the decision to cut.

### 6.1 Loop

1. **Dispatch.** Spawn each active lane as an agent with `isolation: "worktree"`, a scoped brief, its fixtures, its exit criteria, and its stop conditions.
2. **Wait.** Lanes report on completion or on a stop condition. Do not poll.
3. **Verify by postcondition.** For each returned lane: run its tests yourself, in the worktree. **A lane's report that it finished is not evidence it finished.** Assert the exit criteria.
4. **Sweep.** Run `conformance-sweep.py`. Read the negative-check census.
5. **Merge.** Coordinator merges lane → integration branch with `--no-ff`. **A lane never merges itself.**
6. **Record.** Any cross-lane decision becomes an ADR the same session.

### 6.2 Lane stop conditions — report, do not improvise

A lane **halts and reports** rather than proceeding when:
- A contract it consumes appears wrong or insufficient.
- Its exit criteria cannot be met without touching a path it does not own.
- It needs a new dependency.
- It discovers something that invalidates another lane's assumption.
- It would need to weaken a negative check (a known-bad, a selftest, an assertion) to make progress.

**That last one is the important one.** The cheapest way to make a red test green is to make the test weaker, and a lane working unattended at 2am will find that path if it is open. It is closed by making "I weakened a check" a mandatory stop-and-report.

### 6.3 Unattended operation

For long AFK stretches:

- **Bounded briefs.** Every lane brief carries an explicit "done" and an explicit "stop." No open-ended "improve the X."
- **No lane may spend money without a ceiling.** L2's generators and L5's agents carry token caps from the budget governor. L1, L3, L4, L6 make **zero model calls** and are safe to run unsupervised indefinitely.
- **No lane may deploy.** Deployment is coordinator-only. A lane that deploys is a lane that can spend.
- **No lane may push to `main`.** Lanes push their own branch; the coordinator integrates.
- **Cost telemetry into every bundle**, so an overnight run's spend is legible in the morning without opening the console.
- **The wave gate is the wake-up point.** The coordinator does not merge across a wave boundary unattended — W2 and W4 integration gates are where a human decision belongs.

### 6.4 What the coordinator must never delegate

- Editing `contracts/`.
- The **cut-line decision on Tue 08-25.**
- The **D3 target freeze** — an irreversible commitment.
- Unsealing the held-out family. **One seal, one unsealing, one reported number.**
- Any decision to weaken a negative check.
- What is claimed in the README, the blog, or on camera.

---

## 7. The work-item loop

A lane is **not** a to-do list. A lane is an ordered sequence of **work items**, and each work item is a closed loop that runs until its success condition is met. Only then does the lane advance.

```
   ┌──────────────────────────────────────────────────────────┐
   │  WORK ITEM N                                             │
   │                                                          │
   │   1. WRITE THE CHECK FIRST                               │
   │      └─ run it. IT MUST FAIL. ─────┐                     │
   │                                    │ if it passes before │
   │                                    │ implementation, the │
   │                                    │ check is wrong.     │
   │                                    │ Fix the check.      │
   │   2. IMPLEMENT  ◄──────────────────┘                     │
   │         │                                                │
   │         ▼                                                │
   │   3. RUN THE CHECK                                       │
   │         │                                                │
   │    ┌────┴─────┐                                          │
   │   PASS      FAIL                                         │
   │    │          │                                          │
   │    │          ▼                                          │
   │    │    4. DIAGNOSE from the actual error text,          │
   │    │       not from a guess. Then REPAIR.                │
   │    │          │                                          │
   │    │          ├─ iteration < CAP ──► back to 3           │
   │    │          │                                          │
   │    │          └─ iteration == CAP ──► ■ STOP AND REPORT  │
   │    │                                   (never weaken     │
   │    │                                    the check)       │
   │    ▼                                                     │
   │   5. COMMIT the implementation AND the check together.   │
   │      The check becomes a permanent regression test.      │
   │         │                                                │
   │         ▼                                                │
   │   6. RUN contract-check.py --lane <L>                    │
   │         │                                                │
   │         ▼                                                │
   │   7. ADVANCE to work item N+1                            │
   └──────────────────────────────────────────────────────────┘
```

### 7.1 The rules that make this safe unattended

**Check before implementation, always.** Write the assertion, run it, and **watch it fail** before writing the code that makes it pass. A check authored after the implementation is a description of what you built, not a test of what you meant. This is the same principle as the 9 known-bad fixtures, applied at the level of a single work item — *a check that has never failed is not measuring anything.*

**The check asserts a postcondition, never an exit code.** "The command returned 0" is not done. "The blocked tool produced no row in the ledger" is done. Every work item's check must query the resulting state.

**Iteration cap: 5.** On the fifth consecutive failure the lane **stops and reports** with the full error text, what it tried, and its current hypothesis. It does not try a sixth thing. An agent on attempt six is no longer debugging; it is guessing, and guessing unattended is how a lane spends four hours and a budget on the wrong problem.

**Weakening the check is a stop condition, not a repair.** If the honest resolution is "the check was wrong," that is a **report**, not an edit. The coordinator decides. This closes the single most dangerous path available to an unattended lane under deadline: the cheapest way to turn a red test green is to make the test weaker, and at 2am that path will get taken if it is open.

**No partial advance.** A work item is green or the lane is stopped. There is no "mostly working, I'll come back to it" — that is exactly how a deferral evaporates, and the standing rule applies: it goes in Q with a resume trigger, or it does not exist.

**Diagnose from the actual error.** Read the full error before responding to it. Identify the root cause, then fix. Do not pattern-match a fix onto a symptom.

**Log every failed iteration.** `docs/lanes/<lane>-log.md` gets one line per failure: what failed, the error, what was changed. This costs nothing and produces two things worth having — a real debugging record for the blog post, and the evidence that tells the coordinator whether a lane is converging or thrashing.

### 7.2 Work-item shape

Every item in every lane brief is written in this form. If it cannot be written this way, it is not a work item — it is a wish, and it needs re-cutting.

```yaml
id: L4-03
title: Tripwire rules BREACH on an executed forbidden call
depends_on: [L4-01, L4-02]
contracts: [C1 tool_event, C9 verdict]
fixture_in: tests/golden_traces/900_unescalated_refund.json

check: pytest tests/test_tripwire.py::test_900_unescalated_breach
postcondition: >
  verdict.breach == true
  AND verdict.invariant_id == "refund_cap_requires_escalation"
  AND verdict.evidence == [3]

must_fail_first: true      # run the check before implementing; it must be red
iteration_cap: 5
on_cap: STOP_AND_REPORT

forbidden_repairs:         # explicit, because these are the tempting ones
  - relaxing the assertion
  - editing the golden trace to match the output
  - adding a special case keyed to this fixture's ids
```

`forbidden_repairs` is worth writing out per item. The generic rule ("don't weaken the check") is easy to rationalize around at the moment of temptation; naming the *specific* rationalization in advance is what makes it visible when it occurs.

### 7.3 Ordering within a lane

Work items are ordered by dependency, and **the first item in every lane is its negative check**, not its happy path.

- L4's first item is not "the tripwire works." It is **"the tripwire's `--selftest` fails as designed."**
- L3's first item is not "the validator accepts a valid rule." It is **"the validator rejects a rule containing a payload substring."**
- L1's first item is not "the canonicalizer produces a hash." It is **"two documents differing only in key order produce the same hash, and one differing in a value does not."**

Building the failing case first means the instrument exists before the thing it measures. It is the same argument as the whole project, at the scale of a single afternoon.

### 7.4 Lane exit

A lane is done when every work item is green **and** the lane's own exit criteria (§3) assert clean **and** `contract-check.py` passes. It reports to the coordinator with the work-item log, the count of checks that must fail and still do, and anything it stopped on.

**The lane does not merge itself.**

---

## 8. Parallelism, honestly

**What actually runs concurrently:**

| Wave | Concurrent | Why it works |
|---|---|---|
| W1 | **L1 → then L3, L4, L2(a) together** | L3 and L4 are pure code against fixtures. L2(a) needs only the ledger interface, which is C-level, not code-level |
| W3 | **L2(b), L5, L6 together** | Corpus authoring, loop agents, and the replay viewer touch no shared paths |
| W5 | **L6 alone** | Presentation is not parallelizable and should not be |

**What does not parallelize, and pretending otherwise costs you:**

- **The D1 contract freeze.** Single-threaded by nature.
- **The D3 freeze.** One irreversible decision, one owner.
- **The loop run (D8).** One run, one budget, no do-overs. **Cap 6 rounds** (raised from 4, ruling 10)**; convergence needs 3 consecutive dry rounds, and "did not reach dry" remains an acceptable and publishable outcome.** *(At cap 4 only round 1 could be productive — a formality, not a criterion. At cap 6, three rounds can be.)*
- **The held-out test (D9).** One seal, one unsealing.
- **Recording (D10).** One take.

**The realistic gain.** Roughly D2–D7 compress: work that reads as 6 sequential days of one person becomes 3–4 days of coordinated lanes, because L3 and L4 — which are a large fraction of the code and require zero model calls — stop waiting on anything. **That bought time goes into the corpus (L2b, the load-bearing hand-cost) and into the one-day docs-and-recording block, which is the plan's thinnest point.**

It does **not** buy a bigger scope. The cut list stands unchanged.

---

## 9. Failure modes this architecture introduces

Parallelism is not free. Name what it costs.

| Risk | Why it bites here | Mitigation |
|---|---|---|
| **Contract-reality divergence** | A lane builds to the schema, discovers the schema is wrong, and works around it locally rather than reporting | Stop-and-report is a hard rule; `contract-check` fails the commit; the conformance sweep catches the workaround |
| **Integration debt** | Six lanes green in isolation, nothing works together | Two scheduled integration gates (W2, W4), plus cross-lane fixture compatibility in the sweep |
| **Coordinator becomes the bottleneck** | Everything routes through one session that also has to think | Coordinator writes no lane code. Merges are batched at wave boundaries, not continuous |
| **Silent lane coupling** | A lane imports another lane's package because it was there | Grep check in the spot-check list; package boundaries are the ownership map |
| **A lane weakens a check to go green** | Unattended, at night, under a deadline | Mandatory stop-and-report. Negative-check census counted every sweep |
| **Worktree sprawl** | Orphaned worktrees hold branches; checkouts fail | `git worktree list` before any branch operation; coordinator prunes at each wave gate |
| **Lost context between waves** | A lane resumed later has forgotten why | Every lane brief is a file in `docs/lanes/`, updated by the coordinator, not held in a transcript |

---

## 10. Day 1 addendum — what W0 adds to the execution spec

The execution spec's Day 1 is money, kill switch, and canonicalizer. **Parallel operation adds four items, and they come before any lane is dispatched:**

1. **Write and hash the contracts** into `contracts/` + `MANIFEST.json`. *(Nine at W0; **C10, the Objective Set, added 2026-08-20** — ruling 31. The count is computed from `hash-contracts.py`'s file list, never typed.)*
2. **Hand-author one golden fixture per contract** — the input fixtures every lane develops against. This is the single highest-leverage hour in the whole build: it is what decouples the lanes.
3. **Write `contract-check.py` and `conformance-sweep.py`**, including the negative-check census.
   **Four requirements on the dead-value sweep, every one of them paid for on 2026-08-20** — a
   sweep that misses any of these reports CLEAN on prose that carries the dead value, which is the
   most expensive kind of passing check:
   - **Normalize hard wrapping.** Every spec wraps at ~95 chars, so a multi-word phrase spans a
     newline and a line-oriented `grep` cannot see it. *Four of fourteen sites were invisible this
     way.*
   - **Strip blockquote continuation markers before collapsing whitespace.** A phrase wrapping
     *inside* a blockquote leaves `> ` mid-phrase, which survives a plain whitespace collapse.
     `CONVENTIONS.md` is mostly blockquotes. *Found only because a verifier reported FAIL on text
     that was demonstrably present.*
   - **Run at COMMIT time, not only at authoring time.** A parallel session mints sites faster than
     a one-time sweep retires them: `build-spec.md:481` was written at 15:52 on 2026-08-20,
     *after* ruling 20 already existed. Same reason the global canon gate hooks `git commit` and
     not only `Edit`.
   - **Carry an exemption rule**, or every correction note in the spec set reports itself as drift.
     **A site ASSERTING a dead value and a site STRIKING one are not the same site.** This exact
     defect was already caught once by `canon-check --selftest`.

   **And a fifth, which is about coverage rather than matching:** the patterns must cover **claim
   sentences, the §10 environment table, and STATUS ASSERTIONS**, not only schema identifiers.
   **All three categories drifted on 2026-08-20 and none of them was in any pattern** — the
   pre-registration claim was carrying *three* items in one file and *four* in another while every
   mechanical check passed, and nine sites said *"there is no repository yet"* about a repository
   holding five signed commits.

4. **The STATUS pass — `CONVENTIONS.md` §8 rule 12, and it is a separate mode, not another
   pattern.** Flag present-tense existence claims — *"does not exist"*, *"not yet"*, *"is
   currently"*, *"there is no"*, *"still unconfigured"* — that carry **no verification date**.
   **Undated status is `[UNVERIFIED]`, never fact.**

   **This pass must run at COMMIT time.** Edit-time alone would have caught **zero** of the four
   stale-status defects found on 2026-08-20, because **nobody edited those files while the facts
   moved.** `build-spec.md`'s repo line was wrong in *both directions on the same day* — first
   asserting a repository that did not exist, then denying one that did, four hours apart. **A
   spec states the contract; it should not state the status**, and where status is unavoidable it
   has one owner and a date.
5. **Write the six lane briefs** into `docs/lanes/`, each with scope, owned paths, fixtures, exit criteria, and stop conditions.

**Cost: roughly half a day.** It comes out of D1's slack and pushes the canonicalizer to D1 evening. That is the correct trade — a day of contract work buys three to four days of lane parallelism, and without it the lanes silently build against divergent assumptions and integration on D8 finds out.
