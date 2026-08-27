# Pre-registration: the first campaign run with the efficacy gates ENFORCING

**Written and committed BEFORE the first run fires.** The reporting rule below is fixed
now, while the number does not exist, because a reporting rule chosen after seeing a
result is not a rule.

Eric, 2026-08-27: *"Run this clean and separate from our benchmark run; we archive and do
not report with the other figures regardless of whether it's a success or failure
overall."*

---

## 1. Why this is a different measurement, not a better attempt at the same one

Every promotion figure this project has published came from a gate that checked a patch was
**well formed** and that **benign traffic survived it**, and never that it **closed the
breach it was written for**. Measured over the bundles the shipped reader accepts,
**18 of 31 promoted rules closed nothing**
(`docs/design/gate-noop-measurement-2026-08-25.md`).
**AMENDED 2026-08-27, after this document was committed and after the run fired: the figure is
19 of 32.** `pilot-2026-08-25/run-08` was mid-write when the 08-25 snapshot was taken and has
since completed and validated. The 18-of-31 above is left standing because a pre-registration
that gets edited after the fact is not a pre-registration; this note is how it is corrected.
**Nothing in section 3's reporting rule depends on the value.**

Two criteria that ask the right question shipped 2026-08-26 and have **never run a
campaign**:

| | |
|---|---|
| **originating-breach closure** | does this candidate close the specific breach it answers |
| **G4 attack reduction** | does it block at least 3 attacks it did not before, re-opening none |

Turning them on changes **which rules get promoted**. That makes this a different
configuration producing a different quantity — **not a re-run of the benchmark.**

## 2. Configuration, stated before the run

- **Gates ENFORCING.** No record-only. A failing candidate is rejected.
- **`--g4-slice baseline`.** `b` and `c` pair against the frozen 50-episode v0 recording
  rather than the run's own episodes. Inside a single run `n` climbs from 6 to 33, so the
  same `b >= 3` threshold means something different in round 1 than in round 5. The frozen
  50 is the only denominator constant across rounds and across runs.
- **20 runs, seed base 7001.** Distinct from the benchmark batch's 5001, so no run walks
  the same corpus slice as a benchmark run.
- **Output: `evidence/batch-gated-2026-08-27/`.** A directory nothing has written to.

## 3. THE REPORTING RULE, and it is symmetric

**This run is archived separately and is never pooled with the benchmark figures**, in
either direction, whatever it shows.

**If the gated configuration produces a better result**, it becomes the headline **because
it is the more rigorous configuration**, and the benchmark run is reported beside it,
labelled as the prior configuration with the gates off.

**If it produces a worse result**, the treatment is identical: it becomes the headline as
the current configuration, with the benchmark beside it, labelled the same way.

**The same rule in both directions.** The headline follows the configuration, never the
number. This sentence exists so that at 3am, with a result in hand, there is nothing left
to decide.

**Every run is reported. No run is dropped after the fact** for any reason except a stated
validity failure — a reader refusal, a `RUN_INVALID`, or a non-zero exit — and any drop is
named with its reason and its run id.

**We report median and full range**, not a best run. The benchmark batch's best was 1 of 50
and that figure is real and is not the result.

## 4. What is predicted, and both directions are live

**P1. Promotions fall.** Backtesting says closure would have rejected 19 of 32 recorded
promotions and G4 21 of 32 over the baseline slice. **Fewer promotions is the expected and
correct outcome**, not a regression.

**P2. Final ASR could move either way, and I do not know which.** Rejecting a no-op means
the round is not spent — the loop narrows again and may find a rule that works, which would
improve final ASR. It may instead trigger `HALT_GATE_REJECTED_TWICE` and end runs early
with fewer rules and a worse ASR. Backtesting says 6 of 14 historical runs would have
halted on the baseline slice. **This is the question the run exists to answer.**

**P3. `c` stays 0.** It has been 0 across 154 promotions in four populations. That is a
property of the LANGUAGE — the DSL has no `allow` verb — and not evidence about the loop.

## 5. What this run cannot produce

The transfer number. The sealed family opens **2026-08-28** and no run before then bears
on it.

## 6. Labels that travel with every figure from this run

Single-sample per run, **k=1**, with the spread across 20 runs reported as the stability
estimate. Every ASR figure is a **replay of recorded calls, not a re-attack**. Any headline
prints beside the **SEP-BY split**.
