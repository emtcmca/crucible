# Codex review 3 — handoff

**Date:** 2026-08-29 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.
That seam is deliberate and it is not a capacity decision — a reviewer with a pen
grades its own work on the next pass, in a submission whose headline claim is that
an agent is structurally barred from approving its own output.

**As of 2026-08-30: no F4 GCS object has been fetched inside the measurement window,
and no F4 content has been exposed to a human or a model.** Local copies are opened
for automated fingerprinting, which is how the seal is proven intact. Everything
below happened with the holdout shut.

*(This line read "The seal is intact. No F4 object has been read." until 2026-08-30.
The unqualified form is false about local reads — `AUDIT.md` item 11.)*

## State

- Suite: 2614 collected, 2613 passed, 1 skipped, exit 0.
- `python scripts/contract-check.py`: seven contracts pass.
- Two prior verdicts from you: NO-GO (ten findings) and NO-GO (four P0s).
  **All fourteen of the ten-finding set and the four P0s are now closed**, except
  the two carried below under "still open".
- Hard abort gate: **if this is not green and cleared by 08:00 on 2026-08-30, the
  seal does not open.** A time, not a feeling.

## What changed since review 2

| commit | what |
|---|---|
| `a3af765` | V1/V2 reason-code vocabulary ratified by the human before any instance was adjudicated; adjudication ledger landed |
| `14d1356` | paired breach arithmetic; `args` grammar; removed a filter that silenced its own alarm |
| `5fe0a75` | holdout counter wired; transfer contract registered as C11 |

Full diff: `git diff a0c9971..HEAD`.

### The finding I want you to weigh, because it flatters us

Your P0 on breach arithmetic reproduced exactly. A document that read `ACCEPTS`
with zero defect codes published **10 of 15 = 66.7%** where the paired truth was
**9 of 14 = 64.3%**. The transfer number was wrong and nothing said so.

### The twelfth instance of the signature defect, and it was mine

My own `_tool_calls` filter silently dropped every unrecognised argument name.
That made the reader's `E_TOOL_ARG_NOT_ALLOWLISTED` and the builder's raise
**unreachable for any normally produced bundle**. A smuggled argument name
vanished with nothing recording that it had existed. I wrote that filter to
satisfy the allowlist — it silenced the alarm it was installed to feed. Found by
a worker agent, not by me.

## Three questions, in priority order

### 1. Is Outcome B reachable at all, or is it a dead row?

This is a **pre-registration** question and so it has to be settled while the seal
is shut. Under the paired exclusion ceiling, a per-arm breach also breaches the
union ceiling. If that is right, Outcome B can never be entered and the outcome
table advertises a branch that cannot occur — which is a different defect from a
wrong branch, and arguably worse, because it reads as coverage.

Read: `docs/proof/f4-unseal-preregistration-2026-08-25.md` (outcome table A–E, and
the A3.9 amendment appended today), `crucible/transfer/reader.py` (`exit_class`,
`partition`, `transfer_figure`, `complete_pairs`).

### 2. Adjudicate the adjudication DESIGN, not just its code

`crucible/transfer/adjudication.py` (77 tests, 34/34 mutations caught). The rule
it implements: **a V1/V2 failure is REPORTED, never subtracted.** Every sealed
instance is still driven and the denominator stays whole; the failure must NOT
enter the bundle's `exclusions[]`, because the schema would then remove it from
the denominator.

The agent that built it caught itself one step from the opposite behaviour.

**What I want:** is "report, never filter" actually what the pre-registration
requires, or is it what we would prefer it to require? If it is wrong, it is wrong
in the direction that improves our number, which is the direction I trust myself
least on. Ratified vocabulary: `docs/proof/v1-v2-reason-codes-ratified-2026-08-29.json`
(six codes, closed set, fixed before any instance was seen).

Related and unbuilt: the bundle schema has **no home for the adjudication counts**
that Outcomes B and C both require. Design review welcome on where it belongs.

### 3. Is there a thirteenth instance in what was written today?

Two of the last twelve were authored *during repair* of the other ten. The base
rate on repair-introduced defects in this repo is not encouraging.

Target the files in the table above, and ask of each new check: **what change
would this fail to notice?**

## Still open, and known — do not spend time rediscovering these

- `validate_instance()` is not run on the sealed path (`scripts/record-f4-transfer.py`,
  `_adapt_sealed`). Shallow checks only. This is a CORRECTNESS gap, not robustness.
  **In flight as you read this.**
- The sealed experiment locks are dispatched *after* `--phase assemble` returns, so
  assemble does not see them. **In flight.**
- P1s, acknowledged, not yet done: sealed bundles hardcode the stand-in label; the
  raw JSONL drive log is sealed material and `--out` has no path guard; three tests
  of mine assert nothing and need rewriting end-to-end.
- Deferred by agreement: the missing metadata comparison in `hash-contracts.py`.
  Changing a live gate this close to an unrepeatable run is worse than documenting
  it, provided the claim stays narrowed to "registered file digests match".

## Standing constraints

- **Never read** anything under `corpus/sealed/` or `gs://crucible-sealed-x7/families/`.
  Reading a sealed object as an unattested principal marks the run INVALID.
- Do not run `gcloud` reads against the sealed bucket.
- Read-only. Report; do not patch.
