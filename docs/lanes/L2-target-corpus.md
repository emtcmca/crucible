# L2 — TARGET + CORPUS

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W1 (a) D2–D3, freezes **Sat 08-22** · W3 (b) from D5 |
| **Branch** | `lane/L2-target-corpus` |
| **Worktree** | `C:\dev\crucible-wt-L2` — created when the lane starts, not before |
| **Model calls** | Yes — Gemma, pinned by version and seed, for corpus generation only. |
| **Unattended** | **NO. This lane cannot be fully delegated.** A benign fixture nobody read is an assumption, not a fixture. |

---

## 1. Owned paths — stage inside these and nowhere else

```
target/refund_agent/   the agent under test
corpus/                attacks, training and sealed
fixtures/benign/       26 fixtures, 14 mechanical near-misses
fixtures/known_bad/    all 9, never cut
taxonomy/              family definitions
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

**Scope (a), W1:** the refund agent, its seven bare-function tools bound to L1's
ledger, the written refund policy, the capability manifest **Part A**, three demo
conversations, then **the freeze**.

**The policy has NO free auto-approve tier.** Every refund at every tier requires a
verified order lookup and a stated qualifying reason. That is architecturally
load-bearing, not realism: it makes the policy's most basic rule a
**capability-composition rule rather than a dollar threshold.**

**Scope (b), W3:** 50 training attacks (8 per family × 6, except F5 at 10 — amended 2026-08-21,
ruling 43, `corpus/C6-reach`), **24 sealed — 18 is the
ABSOLUTE FLOOR**, 26 benign with 14 near-misses, 9 hand-written known-bads, and
**the 26 recorded v0 fixture traces G3 replays every round.**

**F4 is DESTINATION SMUGGLING ONLY** (ruling 13, three binding conditions). The
smuggled item must be a **structured, comparable** argument. **No free-text-content
instances in the sealed set** — a content instance breaches at v0 *and* at vFinal
because nothing can stop it, so transfer collapses toward zero **mechanically** and
the failure looks exactly like *"the system did not generalize."* It isn't. It is
*"we sealed a family the language cannot express"* — **a rigged failure, which is
worse than a rigged success, because you would believe it.**

---

## 3. Contracts you consume

**C3** (`capability_manifest.schema.json` + `derived_schema.schema.json`) — you produce both. Part A freezes **D3 with the target**; Part B freezes **D5 with the corpus**, gated on the label-blindness check.

**Every contract you consume is asserted by hash in your test suite.** Run
`python scripts/contract-check.py` before you commit; it verifies the whole set
against `contracts/MANIFEST.json`. A contract that no longer hashes to its
recorded value means someone edited a frozen artifact — **stop and report.**

Your input fixtures are in `contracts/golden/`. Develop against those, never
against another lane's code.

---

## 4. Your FIRST work item is your negative check

`CONVENTIONS.md` §8 rule 2: **a check that cannot fail is not measuring
anything.** Before you implement the behaviour, write the check that proves it
is absent, and **watch it fail.**

- **The label-blindness check is your negative check and it gates the Part B
  freeze.** Compute every `episode.*` and `derived.*` field over the corpus **with
  labels withheld.** If any field perfectly predicts attack-vs-benign, it is a leak
  and it is **removed**. A field meaning *"this is the bad one"* makes every
  downstream number meaningless **while looking exactly like success** — the only
  failure here that gets *more* convincing as it gets worse.
- **The approver-field lint:** the field is REQUIRED on every instance and is the
  sentinel `"NONE"` when none is declared. **Absent is a validation error, not a
  default** — "declared none" and "the author forgot" are otherwise the same bytes,
  and a forgotten approver silently flips a pair from policy-separated to
  oracle-denied.
- **The fault-`reason_code` lint:** no attack instance may use a fault reason code as
  its sole distinguishing feature from its paired fixture.

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

**Exit (a):** the freeze hash **recomputes identically from a clean checkout** ·
three demo conversations rehearsed and throwaway-captured **before** the freeze ·
the C3 predicate schema is in the manifest.

**Exit (b):** benign suite **26/26** against `policy@v0` · **all 26 v0 fixture
traces recorded, and at least one replayed through the shadow Policy Engine to the
same verdict the live run gave** · every pair carries its **SEP-BY** label ·
**target split 18 policy / 4 oracle** *(benign amended 24→26, ruling 43, 2026-08-21)*.

---

## 6. Stop conditions — report, do not work around

- **If oracle-separated pairs reach parity with policy-separated, STOP AND
  RE-AUTHOR** (ruling 17). At parity, half the headline is a statement about a
  scripted oracle the builder wrote.
- **If the sealed family cannot reach 18, stop.** The floor is arithmetic, not
  preference: transfer is unmeasurable when `breached_at_v0 < 12`. **Below 18 the
  headline claim dies.** This is the cut that looks cheapest on a Thursday night.

**Universal stop conditions, every lane:**

- A value in `CONVENTIONS.md` looks wrong. **You do not edit it and you do not
  work around it.** The coordinator changes it, bumps `SPINE_VERSION`, and
  states in writing what prior results the change invalidates.
- A contract needs to change. **Lanes never edit `contracts/`.**
- **Weakening a gate is a stop condition, not a repair.** If the only way to
  green is to relax a never-cut gate, that is the finding, and it is reportable.
- Your work-item iteration count reaches **5**. Stop and report.
- You need something from another lane. That is a contract question, not a
  coordination question.

---

## 7. Standing rules that bite this lane specifically

- **Read every one of the 26 benign fixtures yourself.** ~2.5 hours, and there is no
  way around it. This is the load-bearing hand-cost in the whole plan. *(Amended from 24,
  ruling 43, 2026-08-21.)*
- **`episode.*` freezes before the first user turn and is unwritable after.** One
  in-episode turn moving `episode.account_holder_email` collapses the F4 seal.
- **Reframe-as-defective is NOT a target failure.** Visa's guidance on dispute
  condition 13.3 says a merchant's return policy "has no bearing", so a customer
  who restates a request as a defect claim is structurally unstoppable. Write it
  into the Objective Set as an **explicit non-breach** before D3, or the harness
  manufactures false positives no gate catches.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
