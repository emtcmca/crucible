# ADR-0014 — no fourth predicate form; the identity question stays in the identity layer

**Status:** Accepted. **The mechanism named in the referencing prose was superseded on
2026-08-20 by `CONVENTIONS.md` ruling 23** — see below. The decision itself stands.
**Date:** backfilled 2026-08-21, decision dated 2026-08-20 (ruling 8), mechanism superseded
the same day (ruling 23)
**Referenced at:** `docs/execution-spec.md:773` (the decision, **carrying the superseded
mechanism**), `docs/CONVENTIONS.md:550-586` (ruling 8, with its own correction note),
`:1029-1070` (ruling 23), `:1966`, `docs/architecture-spec.md:52-53`, `:728-736`,
`docs/data-spec.md:55`

## Context

The F6 near-miss pits a genuine supervisor authorization against a forged one. Expressing that
in the DSL appeared to need a **fourth predicate form**: `not in` against a trusted-verifier
set. The grammar has `in`, has no `not in`, and its literals must be schema-declared enum
members (`CONVENTIONS.md:1966`).

## Decision

**No fourth predicate form.** Rejected because **a named reference set lives outside the rule
and is mutable — change the set and the policy's meaning changes without the policy hash
changing.** That is the same defect class as `origin` living outside the hashed payload
(`CONVENTIONS.md:552-554`).

The principle underneath it, and the reason this ADR survives its own mechanism:

> **Whether an approver is legitimate is an identity question, not a policy question.** The
> policy's job is *"require verified approval."* The identity system's job is *"is this
> approver real."* Putting that in the DSL blurs a boundary that should stay sharp — the same
> argument that keeps the Tripwire model-free (`CONVENTIONS.md:583-586`).

**The fourth form is held in reserve.** If the separability proof finds pairs that nothing
else covers, add it then, on evidence.

**What separates the pairs instead** (ruling 23): the mandated F6 pair (P15) is separated by
the **`APPROVAL_ORACLE` with zero new fields**, and the harder pair (P16, a real approver who
is under-authorised) by **`derived.approval_tier`** — an enum, not a boolean, because
authority is a dollar ladder.

## The alternative that was rejected, and why

Two, and the second one is this ADR's own first answer.

**1. `not in` against a trusted-verifier set** — rejected above, on hash integrity.

**2. `approval_record.verified`, a harness-computed boolean: attack → `false`, benign →
`true`.** This is the mechanism `execution-spec.md:773` still names. **It is deleted**
(ruling 23), and the reason is worth keeping in full because it is the sharpest thing in the
spec set:

> Read the struck sentence again: *attack → `false`, benign → `true`.* **That is a
> specification written as the mapping from label to value.** Ruling 19.3 mandates removing
> any field that perfectly predicts attack-vs-benign. This field did not risk failing that
> check — **it is the object the check exists to catch, written into the spine as if it were a
> design.** (`CONVENTIONS.md:560-567`)

The dilemma, stated cleanly: **the field is redundant when it is legal and illegal when it is
load-bearing.** There is no corpus in which it both survives the blindness check and does any
separating. You could rescue it by authoring attacks carrying genuine approvers — P16 already
is one — but on those instances `verified` is `true`, the rule does not fire, and
`derived.approval_tier` does the separating anyway.

`data-spec.md` §1.15.2 had already refused this exact shape by name on
`derived.refunds_in_trailing_90_days`: *legal, unnecessary, and likely to correlate with the
label.* Second instance, and **this one got further because it arrived early wearing a ruling
number.**

## Consequences

- `derived.*` stays at **seven** fields.
- **`r041` is deleted from the worked examples.** Two worked examples have now been dissolved
  by later analysis, which is a pattern worth naming once: **a worked example is the first
  artifact to go stale, because it encodes a MECHANISM rather than a RULE.**
- Ruling 18's oracle default becomes a frozen run-manifest parameter,
  `approval_oracle_default: "deny_unless_fixture_declares"`, hash-locked at D2 in C7 — **no
  sixth hash-lock**, because two hashes are two things to forget.
- **The approver identity is declared by the fixture and read by the identity layer. It is
  never a call argument and never an `arg_path`.** What the policy engine sees is
  `derived.approval_tier` and nothing else about the approver. Without this, the forgeable
  channel returns through a different door in two weeks.
- The approver field is **required** on every corpus instance and must be the sentinel string
  `"NONE"` when none is declared — **not `null`**, which `contracts/canonicalization.md`
  restriction 5 forbids anywhere in a hashed payload. Absent is a validation error, not a
  default.

## What this does not decide

- Whether a fourth form is ever added. Held in reserve, on evidence, under the same rule as
  the fourth DSL verb.
- **A documentation defect the coordinator should fix:** `execution-spec.md:773` still states
  the deleted `verified` boolean as this ADR's decision. Under the precedence order,
  CONVENTIONS wins and `execution-spec.md` is the defect.
