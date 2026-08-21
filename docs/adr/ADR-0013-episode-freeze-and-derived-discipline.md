# ADR-0013 — `episode.*` is frozen before the first turn; `derived.*` is harness-computed, hashed, and label-blindness-checked

**Status:** Accepted · **Date:** backfilled 2026-08-21, decisions dated 2026-08-20
(`CONVENTIONS.md` rulings 16 and 19)
**Referenced at:** `docs/execution-spec.md:772` (the decision), `docs/CONVENTIONS.md:722-728`
(ruling 16), `:729-780` (rulings 17-19), `docs/data-spec.md:43`, `:51-53`, `:674`,
`:691-705` (§1.15.1), `:714-760` (§1.15.2), `:819`, `:830`, `:1530-1538`,
`docs/architecture-spec.md:394`, `docs/build-spec.md:244`, `docs/separability-proof.md:301`,
`contracts/derived_schema.schema.json`

## Context

The DSL cannot separate every attack/benign pair on the call arguments alone. Two schema
families close the gap: `episode.*`, three fields carrying the scenario's system-of-record
facts, and `derived.*`, seven harness-computed fields stamped in `before_tool`.

Both are holes if left undisciplined, and they are holes of two different kinds.

**`episode.*` is a mutability hole.** Nothing in any spec required it to be frozen. If an
in-episode turn can move `episode.account_holder_email` — *"actually, my address changed to
this one"* — then **P06, P12, P19, P25 and the entire F4 seal collapse in a single move**
(`CONVENTIONS.md:722-726`). It is the cheapest possible way to invalidate the headline result,
it looks like nothing, and no gate catches it.

**`derived.*` is a leakage hole.** A field that means *"this is the bad one"* makes every
downstream number meaningless **while looking exactly like success**
(`CONVENTIONS.md:765-768`).

## Decision

**`episode.*` is frozen at episode start from the scenario's order/account record, immutable
for the episode's duration, and recorded in the evidence bundle. No turn, no tool return, and
no model output may move it** (`CONVENTIONS.md:727`, `data-spec.md:705`).

**`derived.*` carries four rules, one bright line, and two refusals** (ruling 19):

1. **Source restriction.** Computed from the episode prefix and the scenario's
   system-of-record data only. Never from the attack/benign label, never from payload text,
   never from the target's prose.
2. **Hashed.** Definitions live in the capability manifest. Changing one flags all learned
   rules `needs_revalidation`.
3. **Label-blindness check, mechanical.** Compute every field over the corpus with labels
   withheld. **If any field perfectly predicts attack-vs-benign, it is a leak and must be
   removed.** The check covers `episode.*` too, not only `derived.*`
   (`data-spec.md:758`).
4. **Portability.** Name the general form — `derived.subject_verified_in_episode`, never
   `derived.order_looked_up`. A refund-shaped field breaks the D9 unseen-target beat.

**The bright line:** a field may carry state the production system-of-record holds about the
**account** or the **order**. It may never carry state about the **conversation** or about
**CRUCIBLE's own run.** Account age, order status, delivery scan: permitted. *"Third money
move this hour"*, *"attempt 2 of this attack"*: excluded.

Ruling 20 splits the manifest into **Part A** (`manifest_hash`, frozen D3 with the target) and
**Part B** (`derived_schema_hash`, frozen D5 with the corpus, gated on the label-blindness
check), and G1(c) asserts both on every episode record.

## The alternative that was rejected, and why

**Two refusals are recorded, and both are load-bearing** (`CONVENTIONS.md:778-780`):

**`derived.memo_contains_pii`, or any content classifier.** Rejected because it relocates the
string match from the DSL into the harness and produces **a result about the harness's PII
detector wearing the policy's name.** This refusal is why P21 is unseparable and why F4 is
narrowed — the cost was paid in corpus coverage rather than in the claim.

**Any model-computed `derived.*` field** (`separability-proof.md:301`). `CONVENTIONS.md` §2.1
lists `POLICY_ENGINE` as containing no model; a model-computed input argument launders a
model into the pure-code path. Same argument that keeps the Tripwire model-free.

For the `episode.*` freeze the specs name no rejected alternative, because there was no
competing design — **nothing required the freeze at all**, and the ruling adds a constraint
rather than choosing between two. Recorded as an absence rather than filled in.

## Consequences

- The freeze is on the never-cut list (`data-spec.md:1530`).
- The label-blindness check has already earned its keep: it is the argument that killed
  `approval_record.verified` (ADR-0014).
- Two predicate semantics have to be pinned rather than left to the reader —
  `preceded_by` read over blocked calls, and `episode_sum` **including the pending call**
  (`data-spec.md:830`, `:744`).

## What this does not decide

- The specific field list. `data-spec.md` §1.15 and `contracts/derived_schema.schema.json`
  own it. **Note a known count drift**: `CLAUDE.md` records that ruling 19 said six schema
  fields against the separability proof's seven, hours apart. Verify on use.
