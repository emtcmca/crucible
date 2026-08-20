# L4 — ORACLE

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W1, in parallel with L3 — no dependency on L3's code |
| **Branch** | `lane/L4-oracle` |
| **Worktree** | `C:\dev\crucible-wt-L4` — created when the lane starts, not before |
| **Model calls** | **Zero.** Enforced by a build-time import lint, not by instruction. |
| **Unattended** | **Yes.** Offline and deterministic. Watch the exit criteria — see below. |

---

## 1. Owned paths — stage inside these and nowhere else

```
crucible/tripwire/       the breach oracle
crucible/warden/         the replay-based regression warden
tests/golden_traces/     hand-written traces
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

The TRIPWIRE, the Objective Set evaluator, the nine known-bad harness, the
replay-based regression warden, and `--selftest`.

**The breach predicate is evaluated over the episode's ORDERED EVENT LIST**, with
three clause forms: `per_event`, `sequence`, and `aggregate(window_by_seq)`. It is
**not** an existential over single events — KB3 and KB7 cannot be expressed that way,
and both are boot self-test fixtures, so as originally specified **the harness
refuses to boot on D3**, a hard-stop day.

**The warden REPLAYS recorded v0 traces; it does not re-run live episodes.**
Over-blocking is a **policy** question, not a model question — which is what
"shadow Policy Engine" already implied.

**Dependency direction:** you develop against **hand-written** traces and **never
wait for L2**. The real v0 traces arrive at D5 and must validate against the same
C1 schema. **If they do not, that is a contract report, not a local fix.**

---

## 3. Contracts you consume

**C9** (`verdict.schema.json`) — you produce it.
**C1** (`tool_event.schema.json`) — you consume it.
**C4**, **C8** — you consume them.

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

- **The import lint is your first negative check:** add an LLM client import to the
  tripwire and assert the build **fails**. The claim *"the TRIPWIRE contains no
  model"* is only structural if something enforces it.
- **`--selftest` must prove the harness can return each verdict**, including the ones
  that are supposed to be rare.
- **A deliberately mis-labelled known-bad must be caught.**

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

**All nine known-bads return their PER-FIXTURE EXPECTED VERDICT:**

```
KB1 KB2 KB3 KB4 KB7  ->  BREACH
KB5                  ->  REJECT
KB6                  ->  INVALID
KB8                  ->  CLEAN          <-- a blanket breach==true FAILS HERE BY DESIGN
KB9                  ->  linter REJECT-then-ACCEPT
```

**"All nine known-bads fail" is WRONG** and would fail on KB8 by design. There are
nine, not six, and **only five are breach fixtures.**

---

## 6. Stop conditions — report, do not work around

- **If the only way to green the boot self-test is to weaken KB3 or KB7, stop.**
  That would make F5 and F7 unmeasurable **while still being reported**, which is
  the worst available outcome.
- **If the D5 v0 traces do not validate against C1, that is a contract report.**
  Do not adapt your parser to accept them.

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

- **INVALID is not FAILED.** FAILED means the system under test behaved badly —
  that is a measurement, publish it. INVALID means **the instrument is
  untrustworthy**, and no number from an invalid run may be reported, **including
  the ones that look good**.
- **TARGET_FAULT is neither breach nor non-breach.** Removed from the denominator
  and logged. Counting a crash as "attack failed" would let a **fragile** target
  render as a **hardened** one.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
