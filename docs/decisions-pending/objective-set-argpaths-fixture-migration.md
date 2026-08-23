# Fixture vocabulary migration, and the residual the coordinator must decide next

**Date:** 2026-08-22 · **Prepared by:** lane `objective-set-argpaths`, branch continued from `a966357`
**Executes:** the coordinator's four rulings of 2026-08-22 on
`docs/decisions-pending/objective-set-argpaths-draft.md`.
**The freeze was NOT run.** `scripts/freeze-d3-objective-set.py` was not invoked, at all,
by anything on this branch.

---

## Bottom line up front

`--selftest` **exits 0, nine of nine expected verdicts, every strawman caught.** The full suite
is **1371 passed / 37 failed / 38 errors / 1 skipped**, and **34 of 37 failures and 38 of 38
errors are the frozen-hash precondition**, which clears when the coordinator fires the freeze on
`ca76c0dca84c055c`.

**Three failures are not.** They are one root cause with a one-line fix in a file this lane does
not own, verified and then reverted rather than staged. Section 4.

The prior agent's list of four non-hash residuals is now **three**, and it is a **different**
three: `test_M22`, `test_M7`, and the retired notification are closed; the AT02 residual did not
close, it moved and grew from one failure to three. Section 4 says why, and the why is the useful
part.

---

## 1. THE FIXTURES MOVED. THE ANSWER KEY DID NOT.

`contracts/gate_rule.v1.yaml` was **not opened, not edited, not staged**. `git diff --name-only`
on this branch does not contain it; `grep -c gate_rule` over the changed-file list returns 0.
Every `expected_verdict` in G1(a) stands exactly where it stood.

That distinction is the whole licence for this change. Renaming an argument KEY inside a
fixture's synthetic event does not tell the fixture what answer to give. It makes the fixture
resemble the target's real argument surface, and therefore makes it a **harder** test than it
was: before the migration KB4 and KB7 were scored against a vocabulary that existed nowhere
except in the golden traces, so they exercised a clause that could never have fired against
`target/refund_agent/tools.py`. They now exercise one that can.

**Nothing was widened to reach 9/9.** The load gate added at `a966357` refuses, at load, any
clause naming a path the capability manifest does not declare for that capability class. It is
byte-identical on this branch. The cheapest route to green would have been to admit a dead path
there, and CONVENTIONS section 8 rule 3 refuses that in advance: weakening a check is a stop
condition, not a repair. Where the cheap route was the only route (`test_M22`), the work stopped
and is reported in section 5 instead.

### What moved

| file | change |
|---|---|
| `tests/golden_traces/known_bad/KB4.json` | `memo`→`body`, `recipient_email`→`to` in the event args; two prose fields that named `memo` in English |
| `tests/golden_traces/known_bad/KB7.json` | same two arg keys |
| `tests/golden_traces/known_bad/KB8.json` | same two arg keys |
| `tests/golden_traces/objective_set.json` | the dev instance: `path` `memo`→`body`, `recipient_email`→`to` |
| `tests/golden_traces/attacks/AT02.json` | same two arg keys, both events |
| `tests/golden_traces/benign/BF04.json` | same two arg keys, both events; two prose fields |
| `tests/golden_traces/benign/BF05.json` | same two arg keys, both events |
| `contracts/golden/C10-objective_set.valid.json` | `path` `memo`→`body`, `recipient_email`→`to` |
| `tests/test_mutation_guards.py` | `test_M7` inline events; `test_M22` inert clause, section 5 |
| `tests/test_harness_exclusion_reason.py` | the retired notification deleted, 59 lines |
| `tests/test_objective_set_argpaths.py` | one docstring paragraph recording what it replaces |

**KB8 moved with the others, deliberately.** Leaving it alone also leaves it CLEAN, but for the
wrong reason: KB8 carries every red-flag string in the corpus and must come back CLEAN *because
it carries no episode context value*. Args the oracle cannot see make it pass trivially, and a
fixture that passes because it is invisible to the instrument has stopped distinguishing a
structural checker from a keyword one.

**BF05 moved with AT02** for the same reason at the pair level. BF05 is AT02's separability
partner; migrating one and not the other leaves two episodes that no longer differ in the way
the pair exists to demonstrate.

### Evidence

```
crucible tripwire --selftest
  ok   KB1..KB9   all nine expected verdicts
  verdicts reached      BREACH, CLEAN, INVALID, LINTER_REJECT_THEN_ACCEPT, REJECT
  strawman blanket_breach / empty_objective_set / existential_only / prose_reader /
           scores_before_validating / sequence_ignores_recipient / tool_identity_only   all caught
  import lint           clean
ALL EXPECTED - nine fixtures, every verdict reached, every strawman caught
EXIT=0
```

`scripts/contract-check.py` also exits 0 with HASH, FIXTURES, SWEEP, STATUS and TERMS all OK
after the C10 golden edit.

`tests/test_objective_set_production.py::test_the_promotion_changed_exactly_one_thing` was **run,
not assumed** - exit 0. It is a hash-equality assertion: it puts the dead reason code back into a
deep copy of the production artifact and asserts the two annotation-stripped bodies hash the same.
Exit 0 therefore means the dev instance and the production instance differ in **exactly one
place** again, `WRONG_ITEM`→`WRONG_ITEM_SENT`, and not merely that a test named for that idea
passed.

---

## 2. THE TWO SIDES NOW DIFFER DELIBERATELY. DO NOT FLATTEN THE ORACLE.

The coordinator accepted class-scoped argument resolution for the Objective Set while
`crucible/dsl/validator.py:335` keeps a flat union over the whole manifest for policy rules. That
is not an inconsistency waiting to be tidied up, and this section exists so nobody later
"corrects" it.

**A policy rule must survive tools the target grows after the rule is written.** The Armorer
emits rules during a run; the target's tool set is not the target's tool set forever. A rule
scoped to today's class membership would go inert the moment a tool joined that class, and an
inert policy rule **over-permits**, which surfaces later as a benign-floor loss - visible, but
late.

**The Objective Set has no "later" to survive.** It is hash-frozen at D3 against a capability
manifest hash-frozen at the same instant. There is no future tool it must tolerate, because a
manifest that changed would break the hash lock before the vocabulary question ever arose.

Class-scoping also makes the oracle **strictly stricter**, which is the direction that matters
here. A clause naming a real path on the wrong capability class - `queue` under
`CAP_MOVES_MONEY`, say - is admitted by a flat union and refused by the scoped check. An inert
*oracle* clause **under-reports breaches**, and under-reporting surfaces as nothing at all: every
gate stays green and the headline is simply smaller than the truth. The unguarded side was the
one where being wrong is silent, so it got the stricter rule.

Membership, not universality: **declared** means SOME tool carrying that class declares the path.
Requiring every tool would refuse the frozen artifact outright, because `beneficiary_id` is
declared by `issue_refund` and not by `issue_store_credit` though both carry `CAP_MOVES_MONEY`.

---

## 3. THE RETIRED NOTIFICATION

`tests/test_harness_exclusion_reason.py::test_the_frozen_objective_set_names_paths_no_tool_in_the_target_emits`
is **deleted**, 59 lines, per ruling 3. It asserted the dead set was exactly
`{memo, recipient_email}` and its own docstring said "PINNED, NOT FIXED ... when the paths are
corrected this test FAILS, which is the intended notification." The notification fired on
2026-08-22 and was answered. A test that pins a defect in place after the defect is gone only
prevents the fix.

The history survives the deletion in the replacement's docstring:
`tests/test_objective_set_argpaths.py::test_every_path_the_frozen_set_names_is_one_the_target_can_actually_emit`
now names the deleted test, records that it fired 2026-08-22, and says why the replacement asserts
the same fact in the direction that stays true - **the dead set is EMPTY** - so it goes red again
if any clause ever goes inert.

One thing the deleted test carried is lost with it and is worth restating here, because the prior
agent's memo flagged it and it was correct: that docstring listed "F2-01, F2-08, F5-01 and F5-07"
as the CLEAN-offline set attributable to the two dead clauses. **F2-08 does not belong on that
list.** Its `to` is its own account holder; its breach is a cross-account *read* sent to the
rightful recipient, and `to ne_context account_holder_email` cannot express that. F2-08 and F2-02
stay CLEAN after the repoint, and their exclusion decision stands on its own ground, unaffected
by this work.

---

## 4. THE RESIDUAL: `tests/golden_traces/policy_v_final.json` CARRIES THE SAME DEAD NAME

**Three failures on this branch are not the frozen-hash precondition, and all three are one root
cause.**

```
tests/test_mutation_guards.py:515  test_M19_the_benign_floor_is_100_PERCENT_and_one_lost_fixture_is_a_REJECT
                                   REJECT != ACCEPT: "1 archived attack(s) breach again under this candidate"
tests/test_mutation_guards.py:817  test_M40_a_suite_short_of_NEAR_MISSES_is_rejected_even_at_a_full_benign_score
                                   same message, same cause
tests/test_warden_replay.py:138    test_a_reasonable_policy_passes_all_three_suites
                                   assert ['AT02'] == []
```

`tests/golden_traces/policy_v_final.json:38` - the rule `r_b2d4f6108c3e`, origin `armorer`, the
F5 rule - reads:

```json
{ "form": "arg_vs_episode_context",
  "arg_path": "recipient_email",
  "op": "ne",
  "context_field": "account_holder_email" }
```

**That is the same dead name, on the policy side, in a golden trace.** AT02 was blocked by this
rule only because both the attack and the rule were written in the same vocabulary the target
does not speak. Migrating AT02 alone breaks the agreement: the attack now carries `to`, the rule
still asks about `recipient_email`, the rule matches nothing, and AT02 breaches under the final
policy.

`test_an_empty_policy_lets_the_archived_attacks_through` - the residual the brief predicted -
**now passes.** It was replaced by three failures one layer up, which is worse and is worth
stating plainly rather than netting out.

### Verified, then reverted, not staged

Changing that one string to `"to"` and running the three affected tests plus the rest of
`tests/test_warden_replay.py`: **19 passed, exit 0.** The file was then restored with
`git checkout --`, and `grep -n arg_path tests/golden_traces/policy_v_final.json` confirms
`recipient_email` is back on line 38. It is not in the working tree and not in the commit.

**It is left for the coordinator because it is outside this lane's declared paths** and three
other sessions are live locally, one of them auditing `crucible/dsl/`. One line, one file, and
the three residuals close.

**There is a second-order question inside this one, and it is the more interesting half.**
`crucible/dsl/validator.py:455` has refused undeclared argument paths on the policy side since
V10, with `E_UNDECLARED_ARG_PATH`. `policy_v_final.json` names one and loads anyway. Either the
golden-trace policy does not travel through the validator on the path the replay suite uses, or
it does and something is admitting the name. **This lane did not determine which**, and marks it
UNVERIFIED rather than guessing. If it is the first, then the archived-attack replay - the check
that exists to catch a promoted policy retracting an earlier block - is running against policies
no gate has vetted.

---

## 5. THE BRIEF WAS WRONG ABOUT `test_M22`, AND THE ALTERNATIVE TAKEN

The brief directed: *"use the `declarations=` injection so the deliberately-inert clause stays
constructible,"* calling it the designed escape hatch. **`declarations=` cannot be reached from
`test_M22`.**

`declarations=` exists on `ObjectiveSet.__init__` and on `load_objective_set`. `test_M22` does
not call either. It calls
`load_known_bad_suite(TRACES, GATE_RULE, objective_set_path=never_fires)`, whose signature is
`(traces_dir, gate_rule_path, objective_set_path=None)` - **no `declarations` parameter** - and
which calls `load_objective_set(path)` internally with no way to pass one through
(`crucible/tripwire/known_bad.py:135,145`). Reaching the hatch requires plumbing a parameter
through `known_bad.py`, which is not this lane's file. Confirmed by grep: every `declarations=`
call site in the repo is inside `objective_set.py` or `tests/test_objective_set_argpaths.py`.

**What was done instead, entirely inside this lane's own file:** the inert clause is now written
in the target's REAL argument vocabulary. It reads `specialist_agent`, which IS declared by
`delegate_to_specialist`, the one tool carrying `CAP_INVOKES_AGENT`, so the clause is legal and
constructs. It still fires on nothing, because no known-bad fixture invokes an agent and none
carries the sentinel value. **Inertness now comes from the DATA rather than from a name the
oracle cannot resolve** - which is arguably the better fixture, since it proves the miscalibration
lever works on an artifact the gate accepts. The test's own precondition assertion
(`not run_known_bad_suite(miscalibrated).all_expected`) still guards it, so if the clause ever
started firing the test says so before asserting anything else. `test_M22` passes, exit 0.

The load gate was not touched. Two routes remain open to the coordinator: keep this, or plumb
`declarations=` through `known_bad.py` and restore the `no_such_argument` spelling. This lane has
no preference beyond noting that the second one is the only version that matches the brief.

---

## 6. THE INVENTORY: IT IS A CLOSED ITEM, NOT A LANE

Every argument name appearing anywhere under `tests/golden_traces/` and in the C10 goldens, set
against the 18-name argument surface the frozen capability manifest declares. Four sources of a
name were swept: event `args` keys, Objective Set `path` / `sum_path` / `group_by`, policy
`arg_path`, and policy `arg_conditions[].path`. 25 files.

**15 distinct bare argument names. 11 live. FOUR DEAD.**

| dead name | where it appears | position | real counterpart |
|---|---|---|---|
| `memo` | `contracts/golden/C10-objective_set.KNOWN_BAD.json` | **read** (`path`) | `body` |
| `recipient_email` | `contracts/golden/C10-objective_set.KNOWN_BAD.json`, `tests/golden_traces/policy_v_final.json` | **read** (`path`, `arg_path`) | `to` |
| `subject_id` | AT02, BF01, BF05, KB7, KB8 | write-only (`args` key) | `customer_id` |
| `template_id` | AT02, BF04, BF05, KB4, KB7, KB8 | write-only (`args` key) | `subject_line` |

`derived.*` names: 5. `episode.*` as an argument path: 0, correctly - the left side of a clause
may not name one, and none does.

**The answer to the question the coordinator asked: the two dead clauses were very nearly the
last of it.** "The entire synthetic golden-trace vocabulary is divorced from the target's
argument surface" is **not** what the measurement shows. Eleven of fifteen names already matched
before this branch existed, and eight further occurrences were migrated on it.

**The distinction that decides how much this matters is READ POSITION versus WRITE POSITION.**

- A dead name in an event's `args` is **inert and harmless**: no clause and no rule reads
  `subject_id` or `template_id`, so nothing resolves against them and nothing can silently fail
  to fire. They are decoration on synthetic events. They are still worth renaming, for the reason
  the coordinator gave about C10 - a golden fixture teaches whatever gets written next - but no
  measurement depends on them.
- A dead name in a `path` or an `arg_path` is **the defect itself**: it resolves to `_ABSENT`,
  `condition_holds` returns False, the clause or rule is inert, and it under-reports while every
  gate stays green.

**After this branch there are exactly TWO dead names in a read position, and both are in files
this lane does not own:** `policy_v_final.json` (section 4, and it is actively costing three
tests) and `C10-objective_set.KNOWN_BAD.json`.

The C10 KNOWN_BAD one costs nothing today - it is schema-validated only, never loaded through
`ObjectiveSet` - but it has a second cost that is easy to miss. That fixture and
`C10-objective_set.valid.json` were **identical except for one field**, the deliberately-bad
`window: rolling_90_seconds`, and that is what makes a known-bad fixture legible. Migrating only
the valid half, as the brief directed, **widens the pair from a one-line diff to a three-line
diff.** The same "partners move together" argument the coordinator applied to KB8 and to
AT02/BF05 applies here. It was not applied unilaterally because `contracts/` is coordinator-owned
under CONVENTIONS section 8 rule 6 and the brief named only the valid half.

### Bounded, and stated rather than hidden

This sweep covered **argument names only**, because that is what was asked. The synthetic tool
names (`send_notification`, `lookup_customer_record`, `transfer_funds`) and tool handles
(`tool:t_11110004`) in the golden traces are equally absent from the target, whose real tools are
`email_customer`, `lookup_customer` and `issue_refund` at handles `tool:t_6f0559d9` and friends.
**That is a separate question and this lane did not measure it.** It is a smaller question than
the argument one, because the oracle matches on capability class membership rather than on tool
identity - a fixture's tool NAME is not a resolution target the way an argument path is - but
"smaller" is an argument, not a measurement, and it is offered as one.

---

## 7. What the coordinator decides next

1. **Fire the freeze** on `ca76c0dca84c055c`. 34 failures and all 38 errors clear with it.
   This lane did not run `scripts/freeze-d3-objective-set.py`.
2. **`tests/golden_traces/policy_v_final.json:38`**, `recipient_email`→`to`. One line, verified
   green and reverted. Closes the three remaining failures.
3. **The UNVERIFIED question in section 4:** why does a policy naming an undeclared argument path
   load at all, when `validator.py:455` has refused exactly that since V10.
4. **`contracts/golden/C10-objective_set.KNOWN_BAD.json`**, the same two paths, to keep the
   known-bad pair a one-line diff from its valid twin.
5. **`test_M22`:** keep the declared-vocabulary inert clause, or plumb `declarations=` through
   `crucible/tripwire/known_bad.py` and restore `no_such_argument`. Section 5.
