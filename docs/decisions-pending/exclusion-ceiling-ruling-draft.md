# The exclusion ceiling gets a floor, and a second denominator

**Drafted 2026-08-22 by LANE EXCLUSION-CEILING, on `lane/exclusion-ceiling`, for the
coordinator to land as a numbered ruling and bump `SPINE_VERSION`.** Nothing in
`docs/CONVENTIONS.md` was edited by this lane.

**Implemented in:** `crucible/replay/integrity.py`, `crucible/conductor/conductor.py`.
**Tests:** `tests/test_exclusion_ceiling.py` (28 cases).
**Suite:** `python -m pytest` → **1231 passed, 1 skipped**, 1232 collected, exit **0**.
`python scripts/contract-check.py` → **ALL PASSES OK**, exit **0**.

---

## 1. The defect

`docs/measurement-spec.md` §5.1: *"Exclusions above **5%** make the round INCOMPLETE and
it must be re-run, not reported."* Implemented per round as
`excluded * 100 > attempted * 5`.

**`attacks_per_round` is frozen at 6** (CONVENTIONS §4). The smallest non-zero exclusion
share a round can express is therefore **1/6 = 16.7%**, which is **3.3× the ceiling**. The
per-round rate test was satisfiable **only at exactly zero exclusions**: one target crash
marked the round INCOMPLETE and demanded a re-run of the whole round.

That is not a threshold. It is a tripwire on any imperfection, and this repository already
carries the rule that names it — *a check that cannot fail is not measuring anything*
(`measurement-spec.md:813`, CONVENTIONS §8 rule 2). A check that can only fail is the same
instrument with the wires crossed. Both are the absence of a measurement wearing the
costume of one.

Two consequences were already visible in the tree before this lane opened:

- `RoundRecord.outcome` in `crucible/conductor/conductor.py` has carried `INCOMPLETE` as a
  legal value since the file was written, **and no code path could produce it** — the
  ceiling that creates it had no denominator it could be computed against.
- A live run on 2026-08-22 recorded 36 target faults. Under the old rule every round
  containing one was INCOMPLETE, i.e. unreportable, i.e. the run had no quotable figures
  at all.

---

## 2. The rule as implemented

### 2.1 Two ceiling tests, because they catch different things

**Per round, piecewise across a floor.**

| denominator | test | at the frozen n=6 |
|---|---|---|
| `attempted >= 20` | `excluded * 100 > attempted * 5` | — |
| `attempted < 20` | `excluded > 1` | **this is the live rule** |

**Pooled across the run.** The same 5% rate over `sum(attempted)` and `sum(excluded)`
across the rounds a number is actually quoted from. Applicable only at or above the same
floor. A full six-round run pools to **36 attempted**, where the resolution is 2.8%: **one
exclusion passes, two fail.**

The pooled test is the binding one on a full run, and it is the half that re-tightens what
the floor loosened. Five rounds losing one instance each clear every per-round test
individually and pool to **5/30 = 16.7%**, which the run-level test rejects.

### 2.2 The pooled denominator is the *reported* denominator

Rounds recorded `UNSCORED`, `INCOMPLETE` or `INVALID` contribute no figure to anything a
reader may quote, so they contribute no denominator either. They are still named in the
census and in the named `excluded[]` ledger, and the report row prints how many were
withheld.

Two reasons, and the second is not hypothetical: pooling an unreported round in computes a
rate over a population nobody is quoting, and it turns an **all-crash run — which this
build has already produced once — into a bundle the viewer refuses to open**, destroying
the most instructive artifact the project has.

### 2.3 The exemption is not purchasable with a label

An outcome that is not `SCORED` exempts a round from the ceiling and removes it from the
pooled denominator. That creates an incentive to relabel, so the census row must not be
able to say two things at once. New check, same function:

- `SCORED` with **0** scorable episodes → refused. That is what `UNSCORED` means.
- `UNSCORED` with **>0** scorable episodes → refused. A round that *has* scorable episodes
  and still is not reported is `INCOMPLETE`, and the two are not interchangeable —
  INCOMPLETE carries an obligation to **re-run**.

### 2.4 `ceiling_applicable` is derived, never declared

It is a pure function of `attempted` and the constant
(`crucible.replay.integrity.exclusion_rate_applicable`). It was **not** added to
`contracts/evidence_bundle.schema.json`: a producer that asserts its own applicability is a
producer that can lie about it, and the assertion would be believed on exactly the same
authority as the number it exempts. The contract file was not edited by this lane.

### 2.5 Inapplicability is printed, never silently skipped

The `EXCLUSIONS` row states both halves and the count each covers. On the C6 golden bundle
today:

```
3 round(s), 2 exclusion(s) named with instance ids, 1 marked INCOMPLETE;
per-round rate test applies to 0 of 3 round(s); INAPPLICABLE below n=20 on the other 3,
where the ceiling is at most 1 exclusion(s); run pooled 0/12 over 2 reported round(s),
rate test INAPPLICABLE below n=20 - counts may be quoted from this run, a rate may not
```

A check that quietly stops running is how a boundary rots.

---

## 3. The two constants and how each was derived

Both live in `crucible/replay/integrity.py`. Neither is typed; both are computed from the
ceiling, so moving the ceiling moves them.

| constant | value | derivation |
|---|---|---|
| `EXCLUSION_CEILING_PCT` | **5** | `measurement-spec.md` §5.1. Unchanged. |
| `EXCLUSION_RATE_MIN_N` | **20** | `ceil(100 / PCT)` — the smallest denominator at which **one** exclusion is not already past the ceiling. At n=19 one exclusion is 5.26% and trips; at n=20 it is exactly 5% and does not. |
| `EXCLUSION_SUBFLOOR_ALLOWANCE` | **1** | `floor(MIN_N * PCT / 100)` — the number of exclusions **the rate test itself permits at the floor.** |

The allowance is derived that way on purpose: it makes the piecewise rule **continuous at
the join.** At exactly `n = 20` the rate test fails at `excluded >= 2` and so does the count
substitute, for every count. Asserted, not asserted-in-prose:
`test_the_subfloor_allowance_is_the_ceilings_own_value_at_the_floor`.

**Why a substitute below the floor rather than a bare INAPPLICABLE.** Declaring the
per-round test inapplicable at n=6 and stopping would swap a check that could only fail for
one that could never fire — the same sin wearing the other mask, and **permanent**, because
`attacks_per_round` is frozen *below* the floor and can never reach it. "More than one
instance was lost from this round" is not a rate, but it is resolvable at n=6 and it can
come out either way.

---

## 4. Defect codes

| code | scope | fires when |
|---|---|---|
| `E_EXCLUSION_CEILING` | per round | the round is `SCORED` and is past the ceiling on **its own** denominator. **Semantics changed.** The message now names which denominator it fired on and whether the rate test or the sub-floor substitute produced the verdict. |
| `E_EXCLUSION_CEILING_RUN` | run | the pooled reported denominator is at or above the floor and past the ceiling. **New.** The message says explicitly that no round need be past the ceiling on its own for this to fire. |
| `E_CENSUS_OUTCOME_DISAGREES` | per round | the recorded outcome and the scorable count contradict each other (§2.3). **New.** |

`E_EXCLUSION_LEDGER_MISSING`, `E_EXCLUSION_LEDGER_SHORT`, `E_EXCLUSION_ORPHAN`,
`E_CENSUS_ARITHMETIC` and `E_CENSUS_DUPLICATED` are unchanged. They were not what was
broken, and `test_the_old_checks_still_bite` holds them in place.

---

## 5. `INCOMPLETE` is now reachable at the producer

`crucible/conductor/conductor.py` **imports** `exclusion_ceiling_exceeded` rather than
restating it. One copy of the rule is the whole point: an outcome whose defining test lives
in another file, unevaluated, is exactly how `INCOMPLETE` became a value that existed
everywhere and happened nowhere.

- `RoundRecord` gains `attempted`, `excluded` and `ceiling_exceeded`.
- Outcome precedence in `_round`: **`UNSCORED` → `INCOMPLETE` → `SCORED`.** `UNSCORED` wins
  when nothing survived because it is the *stronger* statement about the same fact —
  `INCOMPLETE` says "there are figures here and you may not report them", and a round with
  nothing scorable has no figures to withhold. This also keeps
  `test_target_fault_leaves_the_denominator_and_the_round_is_UNSCORED` (ruling 33.4) exactly
  as it was.
- **An `INCOMPLETE` round is not `dry`**, so it cannot count toward the three consecutive
  dry rounds that declare convergence. Otherwise flakiness *ends* the campaign — the
  strongest available form of "turns flakiness into apparent hardening", and one step past
  the case the `dry` docstring already guarded.
- **An `INCOMPLETE` round still goes to the Coroner and the Armorer.** What the ceiling
  withdraws is the round's *numbers*; a breach that actually happened is not a number.
  Refusing to patch a real breach because two other instances crashed would let target
  flakiness stop the hardening loop.

---

## 6. What may and may not be quoted

| the run | quotable | not quotable |
|---|---|---|
| pooled reported denominator **≥ 20**, ceiling **not** tripped | ASR and every rate, with the exclusion count printed beside it as §5.1 already requires | — |
| pooled reported denominator **≥ 20**, `E_EXCLUSION_CEILING_RUN` fired | nothing. **The RUN is INCOMPLETE**: it must be re-run, not reported. The bundle is refused by the reader, not rendered with a caveat | any rate, any ASR, any transfer number |
| pooled reported denominator **< 20** (a run that halted early) | **counts only** — attempted, excluded by name and reason, breaches | **any rate.** A denominator below 20 cannot resolve a 5% ceiling, so a percentage taken from it is a number with no test behind it |
| an individual round with `E_EXCLUSION_CEILING` | nothing from that round | that round's ASR, and the run's, until it is re-run |
| a round recorded `UNSCORED`, `INCOMPLETE` or `INVALID` | its presence, its exclusion names and reasons | any figure computed over it, including a **zero** breach count |

The last cell is the one most likely to be got wrong on camera. `INVALID` and `INCOMPLETE`
are the *absence* of a measurement, and "we saw zero breaches in that round" is a
measurement.

---

## 7. Where this lane departed from the coordinator's stated design, and why

The brief specified a run-level ceiling that is **"always applicable, and the binding
one"**, plus a minimum-n floor on the per-round test only. Two parts of that did not
survive contact and were changed deliberately rather than quietly.

### 7.1 The floor had to apply to the run-level test as well

An always-applicable pooled test reproduces the original defect one level up. A run that
halts early — and **`PARTIAL` and `halted` are explicitly publishable outcomes in this
build** (`conductor.py:18-20`) — pools to 6, 12 or 18 attempted, where one exclusion is
16.7%, 8.3% or 5.6%. All three are above a 5% ceiling. The run-level test would then have
been satisfiable only at exactly zero exclusions **on precisely the runs that get
reported.**

A second, independent confirmation lands on the *other* half of the brief — the instruction
to pool **"across every census row."** The **C6 golden fixture** carries 3 rounds, 18
attempted, 2 excluded, both exclusions in the round it correctly marks INCOMPLETE. Pooled
across every row that is **2/18 = 11.1%**, and an always-applicable pooled test rejects the
fixture, failing `test_real_reader_accepts_the_untouched_bundle` in
`tests/test_bundle_reader.py` — a file this lane does not own. Pooled over the *reported*
rows (§2.2) it is **0/12**, and passes. Measured both ways, this date, from the fixture on
disk. So the reported-denominator rule and the floor are each doing work here, for
different reasons.

**This is the place the rule is loosest, and the coordinator may want to look at it
directly.** A short run can now carry up to one exclusion per round with no ceiling verdict
at all — 3 reported rounds could carry 3 of 18 = 16.7% excluded and trip nothing.
What stops that being silent is that the row prints the pooled figure next to the word
INAPPLICABLE and the phrase *"counts may be quoted from this run, a rate may not"*. If the
coordinator wants that closed rather than declared, the fix is to apply the sub-floor
substitute at the run level too — and the golden fixture then has to change, which is not
this lane's file.

### 7.2 "Pooling does not launder anything because it is stricter" is backwards

The brief said the run-level test is *stricter* than a per-round test at n=6 would
practically be. **It is not**, and the reasoning should not be relied on as written:

- Per-round at n=6 under the **old** rule: fails at **1** exclusion in a round.
- Pooled at n=36: fails at **2** exclusions in the whole run.

Pooling is strictly *more permissive per instance* than the rule it replaces — which is the
entire point of the fix, not a flaw in it. The correct statement is the other one:

> Pooling is stricter than the **repaired** per-round test. The per-round substitute
> tolerates one exclusion **per round** (up to 6 across a full run); the pooled test
> tolerates one **in the run**. It exists to re-tighten what the floor loosened.

A related fact worth recording, because it bounds what the pooled test can be credited
with: **the pooled rate test cannot catch anything the old per-round rate test missed.**
A pooled rate is a weighted average of the per-round rates, so if the pool is above 5% then
some round was above 5%, and the old rule fired on it (unless that round was
INCOMPLETE-exempt, in which case it is out of the pool). Its value is entirely relative to
the *new*, looser per-round test. Claiming it as a new class of detection would overclaim.

---

## 8. Follow-ups this lane could not land — files it does not own

1. **`crucible/replay/view.py:457-462`** (the `_round_section` footer) prints the old rule in prose: *"A round whose
   exclusions pass 5% of what it attempted is INCOMPLETE."* That sentence is now wrong at
   the frozen round size and contradicts the `EXCLUSIONS` row printed above it in the same
   viewer.
2. **`docs/measurement-spec.md` §5.1** is the source sentence and needs the floor and the
   run-level denominator, or the spec and the implementation disagree — with the spec
   higher in the precedence order.
3. **`contracts/evidence_bundle.schema.json`** `$comment` strings on `round_census`,
   `excluded` and `outcome` restate the per-round-5%-only rule, including the note that
   INCOMPLETE is a value nothing can produce. That is no longer true. **The file is
   hash-checked by `scripts/contract-check.py`**, so editing even a comment is a
   coordinator action with a hash consequence, not a tidy-up.
4. **`docs/CONVENTIONS.md` §4** carries `Attacks per round = 6` with no note that the
   number sits below the exclusion-rate floor. The floor is derived from the ceiling, not
   from 6, so nothing breaks if 6 moves — but a reader of the frozen-numbers table
   currently cannot see that the two interact.
