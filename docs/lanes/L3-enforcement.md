# L3 — ENFORCEMENT

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W1, once L1's canonicalizer lands |
| **Branch** | `lane/L3-enforcement` |
| **Worktree** | `C:\dev\crucible-wt-L3` — created when the lane starts, not before |
| **Model calls** | **Zero.** Pure code, fully offline. |
| **Unattended** | **Yes — the safest lane to run unattended in a loop.** Offline, deterministic, and its exit criteria require a check that FAILED before implementation. |

---

## 1. Owned paths — stage inside these and nowhere else

```
crucible/policy/     the policy engine
crucible/dsl/        parser + validator
crucible/compiler/   ADK plugin compiler
crucible/plugin/     CRUCIBLE_PLUGIN, the enforcement point
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

DSL parser and validator, the policy engine, the ADK plugin compiler, the
`episode.*` freeze and the `derived.*` stamp.

**The enforcement point is `before_tool_callback`**, and it is verified real:
`plugin_manager.run_before_tool_callback` fires at `functions.py:553`, **Step 1,
before** `agent.canonical_before_tool_callbacks` at `:564`.

**ADK 2.1.0 is pinned.** Issue #2809 is FIXED in it — `include_plugins: bool = True`
propagates the parent's plugins into a nested Runner, so **the whole `OPAQUE` union
mechanism is obsolete.** Replace it with a one-line attach assertion that every
`AgentTool` has `include_plugins is True`, and refuse otherwise.

---

## 3. Contracts you consume

**C4** (`policy.ebnf` + `policy_document.schema.json`) — parser and validator.
**C2** (`decision.schema.json`) — you produce it.
**C1** (`tool_event.schema.json`) — you produce it, from the plugin.
**C3** — you consume both parts.

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

**Four semantics, each of which SILENTLY DISABLES the predicate it belongs to if
wrong. All four need a check that failed first:**

1. **`preceded_by` and `episode_sum` read ONLY events with `policy_decision == allow`
   AND `status == ok`.** Otherwise **an attacker satisfies `preceded_by` for free
   with one blocked call.**
2. **`episode_sum` INCLUDES the pending call.** Otherwise the call that first crosses
   the threshold is the one that executes.
3. **`episode.*` is frozen before the first turn and unwritable after.** A write
   attempt after episode start is `HALT_HUMAN`, **never a merge**.
4. **`derived.` is reserved**, resolved against Part B's declared set, and
   **overwritten in `before_tool`, discarding anything the model wrote** — and
   recording the attempt in `derived_overwrites`.

**Plus the four from C4's negative-check list:**
`{CAP_MOVES_MONEY, CAP_READS_PII}` vs `cap:CAP_READS_PII => deny` **must match** ·
`cap:A|B` **must be a parse error** · a document containing `match_mode` **must be
rejected** · two rules with different verbs on one multi-class call → **`deny` wins,
file order not consulted**.

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

- A hand-written patch compiles, registers, and **the blocked tool never appears in
  the ledger**.
- The validator **rejects a rule containing a payload substring**.
- A model-supplied `derived.subject_verified_in_episode` is **discarded before
  evaluation AND recorded** in `derived_overwrites`.
- All four semantics have a test that **failed before implementation existed**.
- `python scripts/contract-check.py` passes.

---

## 6. Stop conditions — report, do not work around

- **If a corpus pair appears to need a fourth verb or a fourth predicate form,
  stop.** The fourth form is held in reserve and gets added **on evidence, never on
  anticipation** — and the answer to nearly every hard pair was *add a field the
  harness computes, not extend the language.*

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

- **`derived.*` is HARNESS-computed, never model-computed.** A model-computed input
  argument launders a model into the pure-code path without touching the component.
- **The ARMORER never writes a `rule_id`.** It emits `r_new1`; **you** rewrite it.
  Reject any patch where the model emitted a hash-shaped ID on `add_rule`.
- **`cap:UNCLASSIFIED` must be rejected explicitly**, not by omission from the
  production list.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
