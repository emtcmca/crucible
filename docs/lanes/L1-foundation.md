# L1 — FOUNDATION

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | W1 — FIRST AND ALONE in W1's first hours |
| **Branch** | `lane/L1-foundation` |
| **Worktree** | `C:\dev\crucible-wt-L1` — created when the lane starts, not before |
| **Model calls** | None. Pure code. |
| **Unattended** | Delegate the canonicalizer and golden vectors. **Do NOT delegate the IAM bindings unattended** — a wrong binding on the policies bucket silently destroys G8. |

---

## 1. Owned paths — stage inside these and nowhere else

```
crucible/canon/      canonicalizer + golden vectors
crucible/ledger/     the SQLite run ledger
crucible/gate/       the promotion gate with read-back
crucible/manifest/   manifest loading and hash derivation
infra/               Terraform, IAM, buckets
scripts/verify-chain.py
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

**You are the critical path. Everything that gets hashed waits on the canonicalizer.**

The canonicalizer implements `contracts/canonicalization.md` — RFC 8785 JCS with
seven project restrictions. Then: hash derivation, the ledger, the promotion gate
with read-back, and the GCS/IAM layer including **the Armorer 403 proof** captured
to `docs/proof/armorer-403.txt`.

**`scripts/gcp-env.sh` and `infra/create-buckets.sh` ALREADY EXIST. You inherit
them. Do not re-author them and do not pick a different suffix.** `SUFFIX=x7`,
project `crucible-hack-2026`, three buckets live with UBLA on and PAP enforced.
G7 and G8 grep these literal strings, so a retyped bucket name does not fail
loudly — **it produces an unevaluable gate, and an unevaluable gate is a check
that cannot fail.**

**You also own the `corpus/sealed/` pre-commit hook, and it must exist before D5.**
A hook that exits non-zero on any staged path under `corpus/sealed/`. Not a
convention, not a comment. The repo is PUBLIC: an accidental `git add -f` on the
sealed corpus used to be an internal mistake fixable by rewriting history. Public,
it is permanent, cloneable, and **it invalidates the sealed-family claim outright**
— the single headline number this project produces.

---

## 3. Contracts you consume

**C7** (`run_manifest.schema.json` + `canonicalization.md`) — you produce it.
**C8** (`gate_rule.v1.yaml`) — you produce it; it hash-locks at D2 and is not editable after.
**C4** — you own canonicalization of policy documents.

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

- **Golden vectors 10, 11, 12 in `canonicalization.md` §3 are the negative half:** a
  payload with a BOM must be **rejected**, not silently stripped; a payload
  containing a float must be **rejected**; a payload containing `null` must be
  **rejected**. A canonicalizer that quietly coerces will pass all nine positive
  vectors and be wrong in production.
- A **key-order permutation** of one object must produce an **identical** hash.
- A **non-BMP key** must sort by UTF-16 code unit, not by byte order. They differ
  only here, which is why a `sorted()` on raw bytes passes every other test.
- A **deliberately corrupted read-back** must be caught by the gate.

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

- Golden vectors green, **including the key-order-sensitivity case and the
  float-formatting case**.
- The **Armorer 403 captured** to `docs/proof/armorer-403.txt` — a live 403 from an
  impersonation probe, not a policy grep. The grep is necessary and not sufficient.
- A **deliberately corrupted read-back is caught**.
- **G7(b2) and G8's basic-role assertion implemented** (`CONVENTIONS.md` §10a): no
  CRUCIBLE service account holds a project-level basic role. `G7(b)` alone cannot
  catch this — its filter tests `role =~ "storage|bigquery"`, which a basic role
  never matches.
- `python scripts/contract-check.py` passes.

---

## 6. Stop conditions — report, do not work around

- **The retention policy is never locked.** `infra/create-buckets.sh` exits 2 on any
  argument matching `*lock-retention*`. Do not route around it. A locked GCS
  retention policy cannot be removed or shortened by anyone including the project
  owner, and would block the §7.3 teardown for 14 days past the last write.
- **The G8 grant direction inverts easily and has already been proposed backwards
  once.** `crucible-gate` gets `objectCreator` on the policies bucket;
  `crucible-armorer` gets **no storage role at all**. Author is not promoter.

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

- **A tool's success message is not evidence.** Assert the postcondition: query the
  artifact, re-read the file, check the ledger row. `Register-ScheduledTask` has
  printed success while throwing, and a `gcloud` exit 0 has hidden a COM exception.
- **Never lock the retention policy.** Unrecoverable by anyone.
- **`gcloud ai agents` does not exist** at SDK 581.0.0 — re-checked across GA, beta,
  and alpha on 2026-08-20. `data-spec.md` §7.3's teardown calls it twice; rewrite
  against the Vertex AI SDK/REST or drop it.

---

*Brief written 2026-08-20 by the coordinator. Lane definitions: `lanes-spec.md` §3.*
