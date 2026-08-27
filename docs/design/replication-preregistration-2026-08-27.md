# Pre-registration: replicating the measurement batch

**Written and committed BEFORE the batch fires.** It is a REPLICATION, not a new
measurement: identical configuration, different seeds.

## Why

Every figure this project has ever published carries the same caveat:
**single-sample, k=1, no stability estimate.** It is the most-repeated limitation
in the repository and it weakens every number equally. One replication at
identical config is the cheapest thing that removes it.

## Configuration, identical to `evidence/batch-measure-2026-08-27` except seeds

- Gates ENFORCING, `--g4-slice baseline`, `--attack-mode hybrid`.
- The degeneracy census re-recorded 2026-08-27 (50 of 50 instances) in force.
- **20 runs, seed base 13001.** Distinct from 11001, so no run repeats a walk.
- Phase-two attacker memory **OFF**, as it was in the first batch.
- Output: `evidence/batch-replicate-2026-08-27/`, a directory nothing has written to.

## THE REPORTING RULE, fixed now

**Both batches are reported. Neither is dropped, whichever looks better.**

The headline becomes the **pooled figure across both**, with the **per-batch
split printed beside it** so a reader can see the spread. If the two disagree
materially, **that disagreement is the finding** and it is stated in the same
sentence as the pooled number, not in a footnote.

**A replication that contradicts the first batch does not retire the first
batch.** It retires the claim that one batch was enough.

## What is predicted

**P1. Run outcomes move.** The first batch was 9 promoting / 4 halted / 4 clean
(of 17 at the time of counting; 20 completed). Expect a similar shape, not
identical counts.

**P2. Acceptance stays at or near 20 of 20.** The first fully clean batch
followed the census re-record. If acceptance falls, the census fix is less
durable than it looked and that is worth more than the ASR figure.

**P3. The invariant split holds.** One invariant class promotes
(`inv_pii_read_of_a_nonsubject_account`); three are found and never closed. **If
a fix lands for any of the three, the §1 diagnosis in
`why-three-invariants-never-close-2026-08-27.md` is wrong and must be corrected.**

## What this cannot produce

The transfer number. F4 opens 2026-08-28 and no run before then bears on it.
