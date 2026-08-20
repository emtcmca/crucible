# L5 — LOOP

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W3 |
| **Branch** | `lane/L5-loop` |
| **Worktree** | `C:\dev\crucible-wt-L5` — created when the lane starts, not before |
| **Model calls** | Yes — CORONER, ARMORER, RED_STRATEGIST. Pinned models, `thinking_level` set explicitly on every call. |
| **Unattended** | Partially. **The blindness tests are not delegable** — they are the design. |

---

## 1. Owned paths — stage inside these and nowhere else

```
crucible/coroner/     autopsies, no fix field
crucible/armorer/     patch synthesis
crucible/red/         attack strategist
crucible/conductor/   round protocol
crucible/governor/    budget
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

CORONER, ARMORER, RED_STRATEGIST, budget governor, and the round conductor **last**.

**The CORONER is schema-locked with no fix field, a prescriptive-language lint, and
free-text findings confined to a `human_only` subtree.**

**The ARMORER's input is an ENUMERATED PROJECTION with no free-text field at all.**
That is the structural fix, and a lint is not a substitute: the spec's own
`generalization_hypothesis` example handed the Armorer rule `r019` **in English**,
passed the modal-verb lint, and — being a **named typed field** — sailed through the
"adapter reads named fields only" defence.

**Feedback on a rejected round is counts and classes, never IDs or contents:**
`{benign_failures: 2, classes: [...]}`. The §8.3 demo beat originally handed over
"the two failing fixture IDs", which would demonstrate **on camera** the loop doing
the exact thing the design exists to prevent.

**Set `thinking_level` explicitly on every call.** Defaults are not free — thinking
tokens bill at the ordinary output rate with no discount.

---

## 3. Contracts you consume

**C5** (`breach_record.schema.json`) — you produce it.
**C1**, **C3** — you consume them.
**Never L4's code.**

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

- **The adversarial blindness test:** feed the CORONER a free-text field containing a
  "recommended fix" string; assert the ARMORER's input dict **does not contain it**.
- **A second test asserting the adapter cannot address `human_only.*` AT ALL.** The
  lint alone is insufficient — **a hypothesis phrased as a description passes it.**
- **The governor aborts on a low ceiling and logs the abort as a first-class result,
  not an exception.**

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

- Both blindness tests pass.
- A campaign runs end to end unattended, producing bundles carrying **all five
  hashes**.
- **Verb usage is reported per family.** If `constrain_arg` never appears in the
  promoted policy, **say so in the same breath as the F4 number** — that sentence is
  pre-registered now, before the number exists.

---

## 6. Stop conditions — report, do not work around

- **Two consecutive gate rejections → `HALT_HUMAN`.** Do not tune to get past it.
- **If the ARMORER cannot emit valid DSL at the required rate, stop and report.**
  The remedy is a coordinator decision — raise `thinking_level`, add worked
  examples, or replace free-form emission with constrained JSON rendered
  deterministically into DSL text. **That pivot is cheap on Day 1 and impossible on
  Day 8.**

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

- **Never call fixture blindness "enforced" on camera.** The ARMORER holds
  `datastore.user` and Firestore IAM has **no per-collection granularity**, so
  nothing at the platform layer stops it reading a fixture collection. It is
  application convention plus a code check. **The sealed-family blindness IS real
  IAM** — that one may be called structural, and the 403 proves it.
- **The CORONER retains Firestore write.** Its inability to propose fixes is schema
  plus lint, and must be described as such.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
