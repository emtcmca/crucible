# Ruling 55's guard: why it is run-scoped, and why it cannot be computed from a run

**Status: BUILT, 2026-08-25.** Implements ruling 55 (`docs/CONVENTIONS.md`,
SPINE_VERSION 24). Predecessors: `docs/design/e-no-events-conflation-2026-08-25.md`
(the finding) and `docs/design/e-no-events-split-design-2026-08-25.md` (the split).

Ruling 55 promotes `E_NO_EVENTS_TEXT_ONLY` to CLEAN, **conditionally**. This
document records the one judgement the ruling left to the implementation: where
the condition is checked, and what happens when it cannot be.

---

## The measurement that decided it

DEGENERATE is `scripts/no-events-census.py`'s condition: no events in
essentially every episode, over a denominator large enough to mean something.
Made arithmetic, rate >= 0.95 over total >= 30.

The obvious implementation is a run-scope check that recomputes that from the
run's own episodes. **It was measured before it was written, and it does not
work.** Read off the 60 bundles of `evidence/batch-night-2026-08-25/`:

| quantity | value |
|---|---|
| episodes per run | 18 to 36, median 30 |
| distinct corpus instances per run | 16 to 27, median 22 |
| **largest episode count any single instance receives inside one run** | **3** |
| modal per-instance denominator inside one run | 1 |

Against a minimum denominator of 30, a within-run recomputation returns
UNDERPOWERED for **every instance of every run this project has ever produced**.
It could not have returned DEGENERATE once.

**So that guard would be a check that cannot fail** - the exact shape ruling 55
says this project has now met five times, arriving inside the mechanism written
to prevent it. It is refused, and the refusal is recorded here rather than
discovered later.

The mirror option is as bad. A guard that treated every UNDERPOWERED instance as
grounds for refusal would fire on **every** run, since every run is underpowered
at instance scope. A guard that always fires and a guard that never fires are
the same instrument with the wires crossed.

## What is checked instead

Degeneracy is a property of the **frozen corpus**, not of a run. That is the
finding's own argument turned around: a fixture with no resolvable premise
cannot sometimes work, which is precisely why one run cannot see it and a batch
can. So:

1. The determination is made **once, at batch scope**, by
   `python scripts/no-events-census.py --record`, and written to
   `docs/proof/no-events-degeneracy-census.json`.
2. It is **pinned to the `corpus_hash` it was measured over**, which every C6
   bundle already carries as a lock field. No contract move, no new bundle
   field.
3. The run-scope guard, `crucible/replay/integrity.py::_check_no_event_promotion`,
   checks four things against bytes:
   - a determination exists at all;
   - it names **this run's** `corpus_hash`;
   - it was written at **this build's thresholds**, so a record produced with
     `--degenerate-rate 1.01` cannot license a promotion nothing cleared;
   - every instance the run drew is covered, and none is DEGENERATE.

It fails the RUN, in the same shape and with the same verdict as
`E_EXCLUSION_CEILING_RUN`: **the run is INVALID and no rate may be quoted from
it.** Two codes, `E_DEGENERATE_INSTANCE_RUN` and `E_DEGENERACY_CENSUS_MISSING`,
because "an instance is broken" and "nothing checked" are different findings.

**The flag is RECOMPUTED from the record's counts, never read off its `flag`
field.** A stored flag compared to itself passes on a truncated write, a hand
edit and a corrupted read, which is the distinction `integrity.py` opens with.

### It engages only when the promotion was used

A run that put no no-event episode into its denominator laundered nothing, so
there is nothing for a determination to license, and the row says
`not engaged` rather than going quiet. That is scoping, not an escape hatch:
the guard exists to keep a broken fixture out of a denominator, and a run with
no promoted refusal has no such denominator to protect.

### "Not enough data" is not "not degenerate"

An instance the census cannot rule on has **no determination**, so the
promotion is unlicensed and the run is refused. But a small denominator alone is
not a gap: a fixture with no resolvable premise cannot produce a tool call at
all, so **one event-producing episode refutes degeneracy however few episodes
there were.** 25 of 28 is a finding. What cannot be ruled on is an instance that
has essentially never produced an event over too few tries to say whether that
is the fixture or the run - which is exactly the census's own UNDERPOWERED
bucket, reused rather than redefined.

## The cost, stated rather than discovered

**The pin is whole-corpus, so any corpus repair retires the determination for
every instance at once**, and a fresh batch must be censused before any run may
promote again. That is coarse, and on 2026-08-25 it bit immediately: the F5-05
repair landed the same day and moved `corpus_hash`, so the shipped
determination - measured over the pre-repair suite - no longer covers the corpus
in force. **Until a post-repair batch is censused, every run that scores a
refusal is refused with `E_DEGENERACY_CENSUS_MISSING`.**

That is the ruling's own consequence, not a design choice: the alternative is to
promote on an unchecked precondition, which ruling 55 forbids in the same
sentence that grants the promotion. The failure direction is REFUSE, and being
coarse in that direction is the correct way to be wrong.

**A finer pin is possible and is NOT taken here.** Per-instance content digests
would survive a repair to a different instance. They would require the reader to
hash corpus files, which couples the judge-reproduction path to the corpus tree,
and they would need a coordinator ruling on what the record pins to. Flagged,
not built.

## Two things this does not do

- **It does not read prose.** The split's refusal holds one layer out: the
  attack instruction never reaches the tripwire and `Episode.transcript` is
  never read. The guard reads counts and a hash.
- **It does not separate Cause A from Cause B inside an episode.** Nothing can,
  at episode scope. `E_NO_EVENTS_TEXT_ONLY` still covers both, and the guard's
  whole job is to make sure that when a Cause A instance is present, the run is
  thrown out rather than the fixture being read as a defense.

## Verification

`tests/test_ruling55_promotion_guard.py`, plus the ruling-55 sections of
`tests/test_no_events_split.py`, `tests/test_target_responded_stamp.py` and
`tests/test_no_events_census.py`. Both guard branches were exercised on a bundle
a real offline campaign wrote, at $0.0000 billed.

**Accuracy boundary.** The shipped determination was measured over
`evidence/batch-night-2026-08-25/`, and `evidence/` is gitignored, so **that
batch is not publicly verifiable.** The record states its source and its
denominators; a reader can regenerate it from a batch of their own, and the
record carries no clock so the regeneration is diffable.
