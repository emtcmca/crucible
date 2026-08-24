# Pre-registration: the 2026-08-24 live batch

**Written BEFORE the first run of the batch fires, and committed before it fires, which is the
only thing that makes it a pre-registration rather than a description.**

Eric, 2026-08-24: *"if we're going to run them in batches now that compute cost isn't a concern
and we need actionable data to continue tuning the build… I want results we can analyze to make
our patches worthwhile instead of overreacting to individual runs as we may have been doing to
some degree."*

That last clause is the reason this file exists. Three runs have produced three different
diagnoses, two of which were wrong on first reading and corrected the same day. A batch fixes
that only if the questions are asked before the answers arrive.

---

## 1. What changed since the last run, and what each change predicts

Run 3 (2026-08-24, hybrid) is the baseline. Four changes have landed since:

| change | ruling | what it should do |
|---|---|---|
| the world completed behind F2-02 / F2-08 | 52 | removes the only recurring `harness_error` |
| `inv_pii_read_of_a_nonsubject_account` | 53 | two training attacks become detectable |
| the ARMORER is handed the fired invariant's predicate | — | it can bind to the real threshold |
| the narrowing loop, six attempts, breach-bound | — | a rejected patch gets another try in-round |

## 2. The predictions, and every one of them can be wrong

**P1. `constrain_arg` proposal rate goes above zero.**
It is **0 of 3 runs, 0 of 3 proposals** today. The verb requires a boundary value, and until the
invariant dereference landed the ARMORER was never given one — so the verb was structurally
unreachable rather than unpopular. **If P1 fails, the diagnosis behind the dereference is wrong
and I want to know that before anything else is built on it.**

**P2. At least one round makes more than one narrowing attempt.**
The loop is new and nothing has exercised it against a live model. A batch where every round
takes exactly one attempt means the floor is either held or missed on the first try every time,
and the loop is untested rather than working.

**P3. The pooled exclusion rate falls below the 5% ceiling in a majority of runs.**
Run 3 lost 4 of 30 across reported rounds (13.3%). Two of its six exclusions were F2-02 in two
rounds, now fixed. The other four were `invalid_verdict` on episodes that ended `completed` with
**zero tool events** — an attack that induced nothing, which `E_NO_EVENTS` cannot currently
distinguish from an instrument failure. **That is NOT fixed**, so P3 is the prediction most likely
to fail, and its failure is the argument for taking `E_NO_EVENTS` next.

**P4. At least one promotion occurs across the batch.**
Nothing has ever been promoted in this project. `GcsBlobIO` has never executed against GCS. A
promotion would be the first execution of its create-only precondition, its 412 branch and its
generation-pinned read-back, all of which are written from `data-spec.md` and covered by no test.
**A promotion is therefore a risk as well as a milestone**, and `promote`'s recompute-from-bytes
read-back is what stands behind it: a write that cannot be read back and rehashed HALTS.

## 3. What is NOT being claimed

- **No run in this batch is reproducible.** `hybrid` fixes half the attack set by `corpus_hash`
  and rewrites the other half; the target is a live sampled model either way. The batch measures
  VARIANCE across identical settings, which is a different and legitimate thing.
- **No rate from this batch may be pooled across provenance arms.** `generated` and
  `training_corpus` are reported apart, always.
- **A run whose own reader rejects it contributes no rate to anything.** INVALID means there is
  no measurement, including the numbers that look good.

## 4. The batch

Ten runs, identical settings, sequential:

```
--live --attack-mode hybrid --usd-cap 2.00 --holdout-expected 0
```

`hybrid` per Eric's ruling of 2026-08-23 — both arms in one run, broken out by provenance. Ten
because run 3 cost $0.0225 and the batch is therefore free relative to the $1,411 of credit on
the account; the constraint is wall clock, not money.

**Every run is reported, including the ones that fail.** No run is discarded, re-run, or excluded
from the summary. A batch that quietly drops its bad runs measures the person choosing.
