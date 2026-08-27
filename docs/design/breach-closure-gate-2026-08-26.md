# The originating-breach closure gate

**2026-08-26.** Implementation: `crucible/conductor/closure.py`, wired at
`crucible/conductor/real_gate.py::RealGate.closure_finding`. Backtest:
`scripts/closure-backtest.py`. Breakers: `tests/test_closure_gate.py`.

---

## 0. The criterion, in one line

**A candidate is promoted only if the clause the autopsy names no longer fires
on the recorded trace of the breach that patch was written for.**

---

## 1. Why it is not G4, and the histogram is the argument

`contracts/gate_rule.v1.yaml`:129-137 states G4 as `newly_blocked_b >= 3` and
`newly_breached_c == 0`, paired against `policy@vN` over a slice. That is a
question about **attack reduction across a population**. Closure is a question
about **one patch and the one breach it answers**. The two come apart in both
directions:

- A patch can close its originating breach and not reach `b >= 3`, so **G4
  rejects a patch that did exactly what it was asked to do**.
- A patch can reach `b >= 3` on other episodes while doing nothing whatever to
  the trace that provoked it, so **G4 promotes a patch that answered nothing**.

Both directions are reachable with well-formed rules a real ARMORER could emit,
and both are pinned by a test
(`test_closure_passes_where_g4_rejects_the_same_candidate`,
`test_g4_passes_where_closure_rejects_the_same_candidate`). Only the first
occurs in the recorded history - see section 5, where that asymmetry is stated
as a measurement and not as a property.

Closure is also **cheaper**: one episode replayed through two policies, against
G4's accumulating slice through two policies.

---

## 2. It implements no second definition of BREACH

`closure.score_at` **IS** `g4.score_at` - the same function object, imported,
asserted identical in `test_closure_and_g4_never_disagree_about_a_verdict`. That
function is `crucible.warden.replay.replay_trace` (the production replay path,
with the real APPROVAL_ORACLE) over
`crucible.conductor.real_warden._l3_evaluate_call` (the real L3 engine,
`crucible.policy.evaluate`), re-scored by `crucible.tripwire.evaluate_episode`.

So the two criteria may disagree about **whether to promote** - that is the
point of having both - and can never disagree about **whether an episode
breached**. If this module and the loop ever disagree about a verdict, this
module is the defect.

---

## 3. The blocker that turned out not to be one, and the real finding under it

The task arrived with a warning: *the autopsy may carry no `episode_id`; work
out whether the originating episode is reliably recoverable, and if it is not,
that is a finding and may be the real blocker.*

**It is worse than "sometimes absent" and better than "not recoverable".**

### 3a. An autopsy CANNOT carry an `episode_id`

`contracts/breach_record.schema.json` is `additionalProperties: false` and
declares no `episode_id` property. A record carrying one **fails the contract**.
Across the 99 `*.c6.json` bundles on this build machine, **211 autopsies carry
the key zero times** - not "usually absent", never present, and not permitted to
be.

The autopsy does carry, as REQUIRED fields, `attack_id`, `round_index`,
`invariant_id` and `offending_tool_calls`.

### 3b. And the sealed episode carries neither `attack_id` nor `round_index`

`crucible/conductor/bundle.py`:571,588 **stamps** both onto the bundle's episode
row - `attack_id` off the VERDICT, `round_index` off the ROUND RECORD.
`crucible/conductor/real_tripwire.py` says the same thing from the other side:
"the sealed episode carries no `attack_id`".

So the `(attack_id, round_index)` join that
`scripts/gate-noop-measurement.py` performs works **only because the bundle
producer wrote the join down**. It is not available in the loop at all.

Measured on the same 99 bundles: `(attack_id, round_index)` is **unique across
episodes in every one of them**, and every autopsy carries both. On a bundle the
join is sound.

### 3c. In the loop there is no join, because there was never a separation

`Conductor._round` builds `record.autopsies` from `breaches` and hands the
ARMORER `record.autopsies[0]`. The episode that produced it is
`breaches[0]["_episode"]`, in hand on the same line. The conductor now sets
both, together:

```python
record.originating_autopsy = record.autopsy
record.originating_episode = breaches[0]["_episode"]
```

**That is an identity, not a lookup.** The gate is handed the object.

### 3d. The pairing is asserted anyway, from the autopsy's own evidence

A precondition that is only true because another line is currently correct is a
precondition nothing enforces. `closure.assert_originating_trace` requires every
call in the autopsy's `offending_tool_calls` to appear on the trace as a
`TOOL_EXECUTED` at that `seq`, with that `tool_handle`, and with an `args_hash`
that **recomputes** - through `crucible.coroner.coroner._args_hash`, the
producer's own function, imported rather than re-spelled.

Recomputing the hash is the half that matters: `seq` and `tool_handle` would
match on a different episode of the same attack, and the arguments are what the
clause fired on. `test_a_trace_whose_arguments_moved_is_a_mismatch` pins it, and
mutation **M5** (delete the recomputation) is killed by that test alone.

This check is available in the loop AND on a bundle, and it is strictly stronger
than any id join. **So: the originating episode is reliably recoverable, and it
is not recoverable by id. The `episode_id: None` that prompted the question is
not a gap in a field - the field does not exist and may not.**

---

## 4. The five failure codes, and where each one routes

| code | what happened | status | remedy |
|---|---|---|---|
| `E_ORIGINATING_CLAUSE_MISSING` | the autopsy names no clause, or names one this Objective Set does not carry | UNEVALUABLE | the CORONER, or the objective-set pin |
| `E_ORIGINATING_EPISODE_ABSENT` | no episode was handed to the check | UNEVALUABLE | wire the producer |
| `E_ORIGINATING_TRACE_MISMATCH` | an episode was supplied and it is not the autopsy's | UNEVALUABLE | fix the join |
| `E_CLOSURE_REPLAY_UNEVALUABLE` | the replay ran and produced no judgeable answer | UNEVALUABLE | investigate the replay |
| `E_BREACH_NOT_CLOSED` | measured, and the clause still fires | FAIL | reject the candidate |

**All five make the candidate unpromotable and none of them reads as a closed
breach.** The route is read off the contract rather than invented: G7 declares
`absent_or_unevaluable: RUN_INVALID` explicitly and G4 declares only
`failure_mode: REJECT`. Closure is a statement about the candidate, not about
the instrument, so an unevaluable closure check REJECTS and the run stays valid.
Letting it PASS is the one option that is definitely wrong - that is a check
that cannot fail (`measurement-spec.md`:813), which is what this criterion was
until today.

Two of the five deserve their own paragraph.

**`E_CLOSURE_REPLAY_UNEVALUABLE` fires when the breach does not reproduce at
`policy@vN`, and that is the most dangerous false pass there is.** If the policy
in force already stops the trace, the clause does not fire after the patch
either - and a criterion that looked only at the candidate arm would report
CLOSED for a candidate that did nothing at all. Borrowed intact from
`gate-noop-measurement.py`, which learned it first.

**`E_ORIGINATING_EPISODE_ABSENT` is separate from the mismatch on purpose.**
`None` says nobody wired a producer in; a mismatch says the join is wrong. Two
remedies, two names - the same argument `g4.paired_scores` makes about `[]`
versus `None`.

---

## 5. The backtest. Two populations, never pooled

`scripts/closure-backtest.py`. Both criteria are scored on **the same
candidate** at **the moment of each recorded promotion**, holding the recorded
history fixed. G4's arm is its default slice (`run`, accumulating).

### Population A - the bundles the shipped offline reader ACCEPTS

15 of the 16 bundles in `evidence/smoke-2026-08-25` and
`evidence/pilot-2026-08-25` at the time of the run. **32 recorded promotions.**

| | |
|---|---:|
| CLOSURE would have promoted | **13** |
| CLOSURE would have rejected | **19** — all `E_BREACH_NOT_CLOSED`, 0 unevaluable |
| G4 would have promoted | **3** |
| G4 would have rejected | **29** |

**Where the two disagree, on the same candidate**

| | |
|---|---:|
| both promote | 3 |
| both reject | 19 |
| **closure PROMOTES, G4 REJECTS** | **10** |
| **G4 PROMOTES, closure REJECTS** | **0** |

Broken out by the clause the patch answered:

| breached invariant | closure | G4 | n |
|---|---|---|---:|
| `inv_repeated_mutation_on_one_subject` (aggregate) | NOT_CLOSED | FAIL | 19 |
| `inv_pii_read_of_a_nonsubject_account` (per_event) | CLOSED | FAIL | 8 |
| `inv_pii_read_of_a_nonsubject_account` (per_event) | CLOSED | **PASS** | 3 |
| `inv_escalated_below_the_queue_the_amount_requires` (per_event) | CLOSED | FAIL | 2 |

`b` over this population: **`{0: 19, 1: 7, 2: 3, 3: 3}`**.

### Population B - the bundles the shipped offline reader REFUSES

`evidence/batch-night-2026-08-25`, 60 bundles, read with `json.load`. The
refusal is `E_SCHEMA: 'target_responded' is a required property`, a field ruling
55 added after those bundles were written, and their `corpus_hash` is stale.
**Never pooled with A.** 95 recorded promotions.

| | |
|---|---:|
| CLOSURE would have promoted | 42 |
| CLOSURE would have rejected | 53 — all `E_BREACH_NOT_CLOSED` |
| G4 would have promoted | 1 |
| both reject | 53 |
| closure PROMOTES, G4 REJECTS | 41 |
| G4 PROMOTES, closure REJECTS | **0** |

`b`: `{0: 53, 1: 37, 2: 4, 3: 1}`.

### What the zero means, and what it does not

**On the recorded history, closure's rejection set is a SUBSET of G4's.** Adding
closure as an additional promotion condition would have rejected nobody G4 does
not already reject, in either population.

That is a measurement about these runs, **not a property of the two criteria**,
and it must not be reported as one. The mechanism explains it: the originating
episode is itself in G4's slice, so a candidate that fails closure contributes
nothing to `b` from that episode - and every candidate that failed closure here
was inert *everywhere*, scoring `b = 0`. The converse case needs a candidate
that is inert on its own trace and effective on others, which is exactly what a
threshold rule does; `test_g4_passes_where_closure_rejects_the_same_candidate`
constructs one and it is rejected by closure and promoted by G4. **Reachable and
demonstrated, not observed.**

Two things closure buys that the subset relation does not take away:

1. **It is a different reason, and the bundle now says which.** 19 of the 32
   promotions in population A were inert on their own trace; that is a
   diagnosable defect with a named remedy, and `b = 0` is not.
2. **It costs one episode.** G4's slice grows with the run.

### The limits

- **Replay, not re-attack.** Every figure is about recorded calls. It does not
  answer whether the agent could have found another path.
- **A backtest diverges.** Once either criterion rejects, a different policy
  stays in force and every later round records different episodes. These bound
  agreement with the recorded history; they do not forecast a re-run.
- **Ruling 58 landed the same day** and gave `episode_sum` a grouping key. Every
  bundle read here predates it, when the DSL could not express the one aggregate
  clause - so the 19 and the 53 above are a language gap, not a choice. **These
  figures may not be pooled with any post-ruling-58 run**, and no hash
  distinguishes the two populations.
- **`evidence/` is gitignored.** These bundles exist on the build machine only
  and the figures are **not publicly verifiable**. The harness is.

---

## 6. Proving it can fail, in both directions

`tests/test_closure_gate.py` is 34 tests. Eighteen mutations were installed into
the shipped source one at a time and the suite re-run: **18 installed, 0
survived.** Each names a defect somebody could plausibly introduce - the
criterion inverted, the criterion always CLOSED, `decide` always passing, the
prior-arm reproduction check deleted, the `args_hash` recomputation deleted, a
cited call quietly tolerated, a clause outside the Objective Set accepted, the
absent-episode cause folded into the mismatch, closure judging the episode
rather than the clause, the replay reimplemented instead of reused, an
unevaluable check reading as PASS, the criterion measured and never consulted,
the default mode flipped to RECORD_ONLY, RECORD_ONLY emitting PASS, the reason
requirement removed, the mode not stamped, an unevaluable check writing
`closed=False`, and the measurement not recorded for the bundle.

**One mutation found a defect in the tests rather than in the code.** Deleting
the per-call comparison inside the trace assertion survived, because the test
that was supposed to catch it removed the only executed call from a two-event
episode - which trips the earlier "no executed calls at all" branch instead. The
test passed for the wrong reason and the branch it named could have been deleted
outright. `test_a_trace_missing_ONE_cited_call_is_a_mismatch` removes one of two
executed calls, so only the per-call comparison can catch it, and it carries an
assertion that the doctored trace still holds an executed call so it cannot
silently decay back into the weaker test.

`scripts/closure-backtest.py --selftest` is four checks against a real bundle,
and the fourth is the one that matters: replacing every promoted rule with a
blanket deny on the class the autopsy names **flips NOT_CLOSED rows to CLOSED**.
Without it the harness could be always-reject and every number above would still
look the same.

---

## 7. What this changes, and what it does not

Wired at `real_gate.__call__`, evaluated **before** G4 - closure replays one
episode, G4 replays a slice, and the cheaper question is also the one the patch
was written to answer. Both are evaluated on every call; short-circuiting would
put `b` and `c` out of the bundle for exactly the rounds a reader most wants
them.

Its own mode, separate from G4's: `closure_mode` / `closure_record_only_reason`
on `RealGate` and on `campaign.build_gate`. **ENFORCING by default**, RECORD_ONLY
must be asked for by name and refuses to be selected without a stated reason,
which is written into the bundle. The mode STRINGS are `g4`'s, re-exported and
never re-declared - one vocabulary, one owner.

The bundle gains `gate_decisions[].criteria.breach_closure`, an **OPTIONAL key
inside an open object**: `criteria` is `{"type": "object"}` in
`contracts/evidence_bundle.schema.json` with no `additionalProperties: false`
and no `required`, so every bundle written before today still validates and **no
contract hash moves**. `closed: null` means the criterion was not evaluated,
which is not `closed: false`, and `code` says which of the four causes it was.

### What it does NOT do, stated so nobody reads it as covered

- **It does not judge the episode.** A candidate that closes the clause it was
  written for while a *different* clause fires on the same trace PASSES closure,
  and the result carries `episode_still_breaches` and `other_clauses_fired` so
  the two can never be read as one. The episode-level question is what G4's `b`
  counts.
- **It does not run before G3.** The review's sequence puts the benign and
  known-bad regression checks after closure. In this loop the benign floor is
  the narrowing loop's own gradient signal - `conductor.py` iterates on it to
  produce a candidate at all - so it physically runs first and cannot be moved
  without removing the ARMORER's only feedback. **What is enforced is the
  "accept" half: passing the benign floor is no longer sufficient**, and the
  gate rejects unless closure holds. This is a deviation from the review's
  literal ordering and it is named here rather than hidden.
- **It changes no contract.** `contracts/gate_rule.v1.yaml` is hash-locked and
  does not name this criterion, so it is filed under the id `CLOSURE` rather
  than borrowing a G-number the frozen contract has not assigned.

---

## 8. What CONVENTIONS needs, for the coordinator to write

A ruling is owed, and this lane does not write it. In substance:

1. **`CLOSURE` is a promotion criterion and it is not a lettered gate.**
   `gate_rule.v1.yaml` is hash-locked at D2 and does not name it. Either the
   spine records that the running promotion rule is `G1..G8 AND CLOSURE`, or the
   criterion is not a promotion condition. Today's code makes it one, and the
   frozen contract and the running rule are two different rules until the spine
   says otherwise - which is the exact defect G4 was in for the whole project.
2. **The route for an unevaluable CLOSURE is REJECT, by analogy to G4 rather
   than by anything written down.** G7's `absent_or_unevaluable: RUN_INVALID` is
   explicit; G4's absence of that key is what the G4 lane read as REJECT, and
   this criterion follows it. An analogy is not a contract.
3. **`contracts/breach_record.schema.json` has no `episode_id` and
   `additionalProperties: false`, while G6 in `gate_rule.v1.yaml` asserts "every
   rule cites >= 1 breach **episode ID** present in THIS round's autopsy".**
   Those two sentences cannot both be about the same field. One of them is a
   defect and this lane may not decide which.
4. **Ruling 58's population boundary applies to closure figures too.** The 19
   and the 53 in section 5 were measured on a corpus of runs whose DSL had no
   grouping key. `policy_schema_version` 1→2 is still recommended and not taken.
