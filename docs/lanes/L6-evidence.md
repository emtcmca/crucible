# L6 — EVIDENCE + PRESENTATION

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W3 viewer · W5 presentation |
| **Branch** | `lane/L6-evidence` |
| **Worktree** | `C:\dev\crucible-wt-L6` — created when the lane starts, not before |
| **Model calls** | None. |
| **Unattended** | Yes for the viewer. Presentation needs Eric. |

---

## 1. Owned paths — stage inside these and nowhere else

```
crucible/replay/   the replay viewer
docs/proof/        captured proofs
docs/adr/          COORDINATOR ONLY -- NOT this lane's. Corrected 2026-08-20
                   on L6's report (F-3): this line contradicted
                   lanes-spec.md section 4, which reserves ADRs for the
                   coordinator because they record CROSS-lane decisions and
                   a blind lane cannot see across. L6 touched nothing there
                   and wrote no ADR, which was the right call under a brief
                   that told it otherwise.
README.md
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

The replay viewer, the architecture diagram, the README with the Judge-path block,
the ADRs, proof captures, and video assets.

**The viewer reads only from disk and needs no credentials.** It is not a nicety —
it is **the demo instrument and the judge's free reproduction path**, and it is why
the demo can say *"the bundles are in the repo, replay them yourself"* instead of
running a multi-minute live loop on camera.

**The repo is PUBLIC**, so the reproduction path actually works for a stranger. The
README's Judge-path block is the highest-leverage paragraph in the project.

---

## 3. Contracts you consume

**C6** (`evidence_bundle.schema.json`) — you consume it. A hand-written bundle is in `contracts/golden/`.

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

- **Replay from a clean checkout with NO credentials in the environment.** If it
  needs a credential, the judge cannot run it and the claim is untestable.
- **A bundle with a missing hash must be rejected by the viewer**, not rendered with
  a blank field.

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

- Replay runs from a clean checkout with **no credentials in the environment**.
- **A cold reader spins the project up following only the README.**
- The diagram is legible at 1080p.
- Every figure on screen carries its label: **`k=1`, single-sample, no stability
  estimate**; **the 18/4 SEP-BY split**; **the ~11.5% upper bound on unobserved
  regression**.

---

## 6. Stop conditions — report, do not work around

- **If a number cannot be stated with its label in the space available, cut the
  number, not the label.**

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

- **Never say "no legitimate behavior was lost."** Say **"upper bound ~11.5% on
  unobserved regression"** — 0/26 bounds the true rate at ≈11.5%, and that exact
  number is spoken on camera and printed in the README. **Read the figure off
  `python -m crucible.replay`, never off a page** — it is computed there from the
  denominator, which is why it was right on the day four documents said ≈12.5%
  *(bound amended with the denominator, ruling 43 / SPINE_VERSION 14, 2026-08-22)*.
- **Never say "found a vulnerability in Google's agent framework."** You found a
  **defect in a sample application's stubbed tools**, marked in-source
  `# MOCK API RESPONSE`.
- **The trust root is the builder**, who holds project Owner. Say it once, plainly,
  in the README and on camera. **No control here defends against him**, and implying
  otherwise is the overclaim most likely to be caught.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
