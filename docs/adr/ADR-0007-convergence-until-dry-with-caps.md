# ADR-0007 — convergence-until-dry, with a hard round cap of 6 and 3 consecutive dry rounds

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
(cap raised from 4 to 6 the same day, `CONVENTIONS.md` ruling 10)
**Referenced at:** `docs/execution-spec.md:771` (the decision), `docs/execution-spec.md:479`,
`docs/CONVENTIONS.md:307`, `:597-605`, `docs/architecture-spec.md:57`, `:1098`, `:1205`,
`:1276`, `docs/measurement-spec.md:1210`

## Context

The loop has to stop. *How* it stops is a claim about the system: a loop that runs a fixed
number of rounds is a script, and a loop that stops when it has nothing left to find is a
system that knows something about its own state.

The specs carried **five different round caps** (12/10/8/5/4) before the reconciliation
(`architecture-spec.md:1098`), which is its own argument for writing the number down once and
hashing it.

## Decision

**Convergence-until-dry, bounded by hard iteration and cost caps.**

- **Round cap: 6.** Hard. Written into the immutable run manifest at D2, content-hashed
  before round 1, **never moved, and not a cut lever in either direction**
  (`architecture-spec.md:1205`, `:1276`).
- **Convergence: 3 consecutive dry rounds** (`CONVENTIONS.md:307`, ruling 10). This supersedes
  the earlier `dry_rounds_required: 2`.
- **Cost caps sit alongside**: $160 spend cap as a cap and not an alert, 40M token ceiling
  with the cut list auto-triggering at 32M, and a governor that aborts and logs the abort as
  a first-class result (`execution-spec.md:793`).
- *"Did not reach dry"* is an acceptable and publishable **outcome**.

## The alternative that was rejected, and why

**Two rejections, one of them a rejection of an earlier version of this same decision.**

**1. A fixed 3-round loop.** This is cut candidate 4 on the cut list
(`execution-spec.md:479`), reachable only if Day 6 failed badly. The stated cost is *"the
termination story"*, and the one-line argument is: **"A fixed loop is a script; a convergence
criterion is a system."** Recovery, if it is ever taken, is to state the criterion in this ADR
as designed-and-specified with the fixed cap as a deliberate demo-time bound — not to pretend
the criterion was never there.

**2. A round cap of 4** — which is what the first reconciliation pass landed on, and what
`CONVENTIONS.md:307` still describes in its own row. Rejected by ruling 10, on arithmetic:
**a cap of 4 against a 3-dry convergence rule means only round 1 could be productive. That is
a formality, not a criterion** (`architecture-spec.md:1098`). Cost was the binding constraint
and ruling 11 unbound it — with benign fixtures replayed rather than re-driven, a round is ~6
attack episodes plus one Coroner call plus one Armorer call, and the Day-1 spike measured
**$0.015/call**. Three more rounds cost about a dollar against a $160 cap.

## Consequences

- The cap is hash-locked at D2, so it is decided before anyone knows whether the loop is
  going well. That is the point.
- Termination is reportable either way: dry, or capped. Both are results.
- Two supporting mechanisms become load-bearing rather than optional: archived-attack replay
  in the Warden (silent un-fixing would otherwise make the convergence claim false in a way
  no other gate catches, `architecture-spec.md:1258`) and DLQ drain with `PARTIAL` reporting,
  which protects "the integrity of the word DRY" (`:1259`).

## What this does not decide

- What "dry" means at the rule level. `CONVENTIONS.md:1356-1381` records that
  convergence-by-hash-equality was specified at the **policy** level while being fixed at the
  **rule** level, and that "half a convergence detector detects convergence half the time."
  That is an open defect in a contract, not something this ADR resolves.
