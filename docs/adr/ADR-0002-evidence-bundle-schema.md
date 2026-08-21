# ADR-0002 — components communicate only through a versioned, canonicalized evidence-bundle schema

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:766` (the decision), `docs/execution-spec.md:795`
(**a conflicting use of this same number — see below**), `docs/CONVENTIONS.md:1229`,
`docs/architecture-spec.md:660`, `:668`, `:931`, `docs/data-spec.md:114`, `:892`,
`docs/execution-spec.md:744`, `contracts/evidence_bundle.schema.json`

## Context

CRUCIBLE's components are deliberately blind to each other. The Coroner cannot propose a
fix, the Armorer cannot see a benign fixture, the Tripwire holds no model. Blindness only
means something if the thing that crosses the boundary is a fixed, inspectable shape rather
than whatever an author happened to serialize that day.

`CONVENTIONS.md:1229` states the test a contract has to pass: it exists **to freeze a data
shape that crosses a blindness boundary**, which is why every contract in `contracts/` is a
schema, a grammar, a gate rule, or a canonicalization spec, and why each is hashed.

Every downstream claim — the five hashes, the paired v0→vFinal comparison, the replay a
judge runs with no credentials — is a claim about bytes. Bytes need one serializer.

## Decision

**Cross-component communication is a versioned, canonicalized evidence-bundle document and
nothing else.** Concretely:

- The bundle carries `schema_version` (`data-spec.md:114`) and is frozen in
  `contracts/evidence_bundle.schema.json`.
- One canonicalizer, written once, with a golden-vector file of at least twelve fixtures
  covering unicode keys, nested arrays, empty arrays, large integers, and key-order
  permutations that must hash identically (`data-spec.md:892`).
- The **episode prefix is recorded in the bundle** (`architecture-spec.md:660`, `:668`,
  `:931`), which is what keeps the episode-scoped predicate forms pure and what makes replay
  exact rather than approximate.
- Diagram arrows are labeled with what flows — `evidence_bundle.json`,
  `autopsy{structured}`, `policy.dsl`, `gate_decision` — never with verbs like "analyzes"
  (`execution-spec.md:744`).

## The alternative that was rejected, and why

**The specs do not name a rejected alternative for this decision.** Recorded as a gap rather
than filled in.

The nearest named rejection is adjacent and worth citing because it draws the boundary from
the other side: `CONVENTIONS.md:1225-1233` **refused to make the ledger a contract (there is
no C10)**, on the grounds that the ledger is *code* crossing a component boundary rather than
a data shape, and "hashing it would freeze an implementation, which is the one thing a
contract must not do." That rejection tells you what this ADR is not: it is not a mandate to
hash every seam, only the ones where a shape crosses a blindness boundary.

## Consequences

- A subtly wrong canonicalizer "produces green checkmarks over meaningless comparisons"
  (`data-spec.md:892`, `:1545`), so the golden vectors are load-bearing, not hygiene.
- Replay works from a clean checkout with no credentials, because everything the replay needs
  is in the bundle.
- Every component gains a versioned surface it can be tested against in isolation, which is
  what lets six blind lanes develop in parallel.

## What this does not decide

- The internal shape of any single component's own state.
- Whether a given seam needs a hashed contract at all — that test lives in
  `CONVENTIONS.md:1229`, and the C10 ruling shows it can come back "no".

## Number collision the coordinator has to resolve

`execution-spec.md:795` (risk register, row 5) says: *"Write the freeze protocol into
**ADR-002** so the rule is external to your Day-10 self"* — the D3 target-agent freeze
protocol, an entirely different decision from the one at `:766` in the same file. **Two
decisions, one number, one document.** This ADR records the `:766` decision, because `:761`
is the enumerated ADR index. The target-freeze protocol is unrecorded and needs a number.
