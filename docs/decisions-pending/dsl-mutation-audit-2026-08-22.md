# DSL mutation audit - 2026-08-22

**Lane:** DSL-MUTATION (L4 worktree `C:\dev\crucible-wt-L4`, `lane/dsl-mutation`,
cut from `main` @ `0b32030`)
**Target:** the surface the first audit named on its way out - *"Not mutated:
`crucible/dsl/` and `policy/engine.py` - the largest untouched surface and the
obvious next audit."*
**Answer:** 62 mutations across the parser, the validator's numbered rules
V1-V10, the serializer's content-addressed rule ids, the hasher and the
POLICY_ENGINE. **49 killed, 13 survived.** Twelve survivors now have a test that
goes red under them; the thirteenth is reported and deliberately not guarded.
Nothing in `crucible/` was permanently changed.

---

## Why this surface

**The DSL is what the ARMORER writes into.** Every patch the loop will ever
produce is text in this grammar, parsed by `crucible/dsl/parser.py`, judged by
`validator.py`, hashed by `serialize.py` and executed by `policy/engine.py`.
Unlike the TRIPWIRE - which the Objective Set, the known-bads and the gate all
re-check from different angles - **nothing downstream re-checks the grammar.**
The Warden scores what a policy DOES on the benign suite; it has no opinion on
whether the policy says what its author meant, and the gate promotes bytes.

It is also where **V10 / `E_UNDECLARED_ARG_PATH`** lives - the one guard the
frozen Objective Set turned out to lack, added 2026-08-22 because the contract
had claimed it for weeks. Whether V10 itself is guarded was the specific
question this lane was sent to answer. **It is: six committed tests kill it,
including its no-emptiness-escape clause.** See rows D7 and D7b in the KILLED table.

## Method

Identical to `mutation-audit-2026-08-22.md`. For each invariant: break it at the
source in the smallest way that makes the claim false, run the WHOLE suite,
record KILLED or SURVIVED, restore, assert the bytes are identical, and confirm
`git status --short` is clean before the next one. One pytest at a time. No
mutation was committed. The only files staged are
`tests/test_dsl_mutation_guards.py` and this document.

Runner: a scratchpad script outside the repo, so it never appears in
`git status`. It reads and writes in **binary** and encodes each pattern with the
line terminator the file actually uses - see the incident below.

**Baseline before any mutation:** `1434 passed, 1 skipped`, `PYTEST_EXIT=0`,
1435 collected.

---

## Findings - survivors, ranked by blast radius

### Tier 1 - the decision on a live call. A survivor here changes what the target is allowed to do, at run time, on the enforcement path.

| # | Mutation | Falsified claim | Guard |
|---|---|---|---|
| **E3** / **E3b** | `engine.py::_effect` - `if verdict == TRUE: return None` relaxed to `!= FALSE` (E3), and separately an early `return None` when the constrained argument is absent (E3b) | **`constrain_arg` FAILS CLOSED.** Absent, null or wrong-typed counts as VIOLATED. The engine's docstring is loudest about exactly this - *"'we do not know' must not read as 'allow'"* - and **both relaxations survived the whole suite.** This is not a rule that stops working; it is a rule that stops working ON THE CALLS AN ATTACKER CONTROLS THE SHAPE OF. A learned `constrain_arg(amount_minor <= 50000)` is then defeated by sending the amount as a string or omitting it, and the Warden still sees a policy that cleared every benign fixture. Nothing covered it because every fixture and every golden trace carries a well-typed `amount_minor`. The three shapes are the ones **V8's own synthetic sweep already enumerates** - which is the tell: `check_totality` asserts the engine does not CRASH on them and nothing asserted what it DECIDES. | `test_E3_constrain_arg_FAILS_CLOSED_on_absent_null_and_wrong_typed_arguments` (kills both) |
| **E14** | `_clause` `preceded_by` - `for ev in visible: if want in (ev.get("capability_classes") or ()): return TRUE` reduced to `return TRUE` on the first visible event | **`preceded_by(X)` reads the class it NAMES.** `preceded_by` is the separating predicate of the **entire F5 family**: **eight of the ten** `corpus/training/F5-*.json` instances name it in `separable_by` (counted at source; F5-04 and F5-08 do not), and `corpus/pairs.json` names it as the discriminating feature of the composition pairs. Ignoring WHICH class preceded turns every one of those into "deny anything that follows anything" - it passes the attack half of each pair and destroys the near-miss half, which is the trivial defeat the 100% benign floor exists to catch. Every committed `preceded_by` test runs the TRUE arrangement or an empty prefix; **nobody ran a prefix carrying the WRONG class.** | `test_E14_preceded_by_reads_the_CLASS_IT_NAMES_and_not_merely_ANY_predecessor` |
| **E10** | `_compare` - ordered-op type gate returns `FALSE` instead of `UNEVALUABLE` | **A type mismatch RETAINS the rule.** The direction is the finding, and the function's own docstring names it: *"reporting a mismatch as False would silently drop the rule, which is failing OPEN through the back door - the rule stops applying because of a type, not because of a fact."* The suite covers the absent-argument road into UNEVALUABLE thoroughly and the wrong-typed road not at all, so this is a guard written on the road nobody drove. | `test_E10_a_TYPE_MISMATCH_retains_the_rule_rather_than_dropping_it` |
| **E11** | `_is_int` - `type(x) is int` relaxed to `isinstance(x, int)` | **A boolean is not an integer.** `bool` subclasses `int`, so under `isinstance` a boolean argument is swept into an `episode_sum` as one minor unit: a money total assembled partly out of flags. `crucible/canon/canonical.py` documents the identical trap for serialization and `engine.py` repeats it in a comment - *"`True < 5` is a legal comparison that means nothing here"* - and nothing tested it on either side. Guard written on the AGGREGATE road on purpose; the `_compare` road is a special case of the type gate E10 disables, so a guard there would go red under two mutations and prove neither. | `test_E11_a_BOOLEAN_is_not_an_INTEGER_when_money_is_being_summed` |

### Tier 2 - the abstraction claim. "Every terminal in this grammar is abstract or manifest-declared" is what headline result #1 rests on.

| # | Mutation | Falsified claim | Guard |
|---|---|---|---|
| **D2** | `validator.py::check_selector` - the `cap_class == UNCLASSIFIED` branch disabled | **V2 is re-asserted off the parse tree, not only at the lexer.** The validator's docstring states the exact claim: V2 is *"re-asserted here so the refusal survives someone building a rule without it"* - and that claim was unverified, because every committed test reaches the validator THROUGH the parser and the parser refuses the text first. `UNCLASSIFIED` is the fail-open sentinel: an unmapped tool is UNCLASSIFIED until the manifest maps it, so one `cap:UNCLASSIFIED => deny` blocks everything on an unseen target and reports 100% transfer, manufactured. Guarded by building the `ParsedRule` the way a second producer would. | `test_D2_the_VALIDATOR_refuses_UNCLASSIFIED_on_a_rule_the_parser_never_saw` |
| **D3** | `check_selector` - the `not in CAP_CLASSES` branch disabled | Same shape, different defect. A seventh class is one the manifest can never map, so a rule naming it **matches nothing, ever** - the silent-no-op shape `match_mode` was DELETED rather than pinned to a constant to avoid. Kept as its own row because the two branches defend different things and a single guard would let one of them rot. | `test_D3_the_VALIDATOR_refuses_a_SEVENTH_capability_class` |
| **D22** | `check_context_fields` - the `qualified not in self.declared_episode` branch disabled | **The three `episode.*` bindings resolve against PART B.** The parser's `CONTEXT_FIELDS` tuple and Part B's `episode_fields` are **two artifacts with two hashes and two freeze dates** (ruling 20): the tuple is frozen in `nodes.py`, Part B freezes at D5 with the corpus and is gated on the label-blindness check. A field admitted by the grammar and undeclared by Part B is a comparison against a fact the episode seal does not carry - and `episode.*` is frozen before the first user turn precisely so F4 can rest on it (ruling 16). | `test_D22_an_UNDECLARED_episode_context_field_is_refused_by_the_validator` |
| **P7** | `parser.py` - the explicit `preceded_by(UNCLASSIFIED)` branch removed | **The refusal carries its OWN error code.** With the branch gone the token falls through to the six-class check and is still refused - with `E_UNKNOWN_CAP_CLASS`. That is precisely the failure the parser's docstring predicts for the *selector* form and which `l3_checks.py` guards **there and only there**: *"a generic 'unknown capability class' error would fire today and stop firing the moment somebody added UNCLASSIFIED to a list for an unrelated reason."* The composition predicate had the argument written down and no test. The ARMORER also gets ONE repair attempt with this code as its sole feedback, and the two codes point at different repairs. | `test_P7_preceded_by_UNCLASSIFIED_is_refused_BY_ITS_OWN_NAME` |

### Tier 3 - the canonical form. A survivor here gives one policy two hashes, which breaks convergence-by-hash-equality and the resume key together.

| # | Mutation | Falsified claim | Guard |
|---|---|---|---|
| **S6** | `serialize.py::rule_body` - `arg_conditions` no longer sorted at construction | **Canonicalization restriction 6 NAMES `arg_conditions`, and it is the one array of the three with no test.** `test_convention_3_clause_order_does_not_move_the_id` looks like this guard and is not: it writes exactly ONE `arg_condition`, and a one-element list is sorted in every order. It covers `predicates` and `tool_names` - the two arrays restriction 6 does **not** name - and leaves uncovered the one it does. `rule_id` is content-addressed, so unsorted means THE SAME SEMANTIC RULE GETS TWO IDS depending on the order the ARMORER happened to write its clauses, and the ARMORER is a model, so that order is not stable. `add_rule` of an existing rule then stops being detectably a no-op: the per-rule half of the convergence detector. | `test_S6_TWO_CLAUSE_ORDERS_are_one_rule_and_therefore_one_rule_id` |
| **S8** | `sort_rules` reduced to `list(rules)` | `validate_patch`'s output then carries rules in **dict-insertion order** - the pre-existing policy first, the new rule after it. | `test_S8_a_validated_patch_emits_its_rules_SORTED_whatever_order_they_arrived` |
| **D17** | `validate_policy_document` - the `E_RULES_NOT_SORTED` check disabled | **`E_RULES_NOT_SORTED` appears in no test in the repo.** Paired with S8 this is the whole hole: **S8 writes the unsorted document and D17 is the only thing that would refuse it, and both survived**, so a policy could be written out of canonical order and read straight back without complaint. Sorting AT CONSTRUCTION rather than at hash time is what makes the canonical form unambiguous; `serialize.py` argues sorting at hash time *"would look lossless and be destructive"*. | `test_D17_a_policy_document_whose_rules_are_OUT_OF_ORDER_is_refused` |

### Tier 4 - survived, and NOT a finding. Reported so the next audit does not re-run it and so the near-miss is on the record.

| # | Mutation | Why it survived | Guard |
|---|---|---|---|
| **P3a** | `selector()` returns a default class when `cap` is absent | **V1 IS GUARDED. This cut was too weak and would have been filed as a finding.** With the early return in place, the very next `expect("OP", "=>")` trips on the `tool` token, so `rule r_new1: tool:t_9f2c1b77 => deny` **still fails to parse, with the same `E_UNEXPECTED_TOKEN` code the committed test asserts.** The mutation did not change the observable. Re-cut properly as **P3b** - cap selector genuinely optional, the qualifier list parsed on its own - and P3b is **KILLED** by `tests/test_dsl_parser.py::test_cap_selector_is_required_and_first`. No guard written: a duplicate of a working test closes nothing. Same shape as the first audit's M2a, and the same lesson - **a mutation that survives has to be checked for WHY before it is called a gap.** | none - deliberately |

---

## Findings - the 49 that were KILLED

A killed mutation is evidence the guard works, and worth recording so the next
audit does not re-run it. "Killed by" names the first or most specific test.

### `crucible/dsl/validator.py`

| # | Mutation | Killed by |
|---|---|---|
| D1 | V9 - `assert_model_did_not_forge_a_rule_id` disabled | `test_dsl_validator.py::test_V9_a_hash_shaped_id_on_add_rule_is_rejected`, `test_armorer_patch.py::test_a_hash_shaped_id_on_an_add_is_rejected` |
| D4 | V5 - tool handle need not be in the manifest | `test_dsl_validator.py::test_V5_a_tool_handle_must_be_in_the_manifest` (2 tests) |
| D5 | N6 - `derived.*` no longer resolved against Part B | `test_l3_negative_checks.py::test_negative_check[N6]` (2) |
| D6 | `episode.*` admitted as a call argument | `test_dsl_validator.py::test_an_episode_fact_may_not_be_a_call_argument` (2) |
| D7 | **V10 - `E_UNDECLARED_ARG_PATH` disabled entirely** | **6 tests**, incl. `test_V10_an_arg_path_must_be_declared_by_some_tool`, `test_V10_is_the_check_that_would_have_caught_r_new6`, `test_V10s_repair_message_survives_the_leak_gate` |
| D7b | **V10's NO-EMPTINESS-ESCAPE clause - an empty `arg_paths` declaration admits everything** | `test_V10_CANNOT_BE_SWITCHED_OFF_BY_A_MANIFEST_THAT_DECLARES_NOTHING` |
| D8 | V4 - enum declared for ANY path rather than **that exact path** | `test_V4_an_enum_symbol_must_be_declared_for_its_exact_path` |
| D9 | V4 - the symbol-membership half | 4 tests, incl. `test_p03_r_new3_status_to_enum.py::test_negative_control_V4_still_refuses_a_freshly_invented_status_to_symbol` |
| D10 | V3 - product-lexicon denylist disabled | 3, incl. `test_V3_a_product_identifier_in_a_rule_body_is_rejected` |
| D11 | V7 - payload-substring lint disabled | `test_V7_a_rule_reproducing_a_payload_run_is_rejected` |
| D12 | V8 - the totality sweep swallows its own exceptions | `test_V8_the_totality_sweep_can_actually_fail` |
| D13 | V6 - seed rules become retractable | `test_V6_the_armorer_may_not_retract_a_seed_rule` |
| D14 | retracting a rule not in the policy is accepted | `test_retracting_a_rule_that_is_not_there_is_refused` |
| D15 | N3 - `match_mode` accepted | `test_l3_negative_checks.py::test_negative_check[N3]` (2) |  <!-- sweep-ok: D15/D16 name the deleted token as what the MUTATION makes the validator accept; the row is the refusal, not a use -->
| D16 | N3 - `match_mode` looked for only at the TOP LEVEL, not "at any depth" | same (2) |  <!-- sweep-ok: D15/D16 name the deleted token as what the MUTATION makes the validator accept; the row is the refusal, not a use -->
| D18 | **check order** - V10 moved ABOVE V3, so `E_PRODUCT_IDENTIFIER` becomes nearly unreachable | 3, incl. `test_V10_does_not_swallow_V3` |
| D19 | **check order** - V4 moved above V10, so a bad path is diagnosed as a bad enum | `test_V10_an_arg_path_must_be_declared_by_some_tool` |
| D20 | `_paths` stops yielding the ACTION path, so V10 misses `constrain_arg`'s target | `test_V10_reaches_the_action_and_the_episode_scoped_clause_forms` |
| D21 | V3 runs over `source_text`, dropping the KB9 metadata exemption | `test_V3_exempts_metadata_and_provenance` |

### `crucible/policy/engine.py`

| # | Mutation | Killed by |
|---|---|---|
| E1 | **STRICTNESS inverted** - `deny` 3→1, `constrain_arg` 1→3 | `test_l3_negative_checks.py::test_negative_check[N4]` |
| E1b | `deny` and `require_approval` swapped only | same |
| E2 | tie-break takes the **highest** rule id instead of the lowest | same |
| E2b | tie-break by `max`'s stability - i.e. **file order wearing a different name** | same |
| E4 | STEP 2 - `UNEVALUABLE` in a `when` drops the rule instead of retaining it | `test_dsl_is_present.py::test_without_the_guard_the_same_rule_still_over_blocks` |
| E5 | STEP 1 - membership replaced by **set equality** | **15 tests**, incl. `test_l3_negative_checks.py::test_negative_check[N1]`, `test_real_warden.py`, `test_w2_integration.py` |
| E6 | `E_DECISION_VOCABULARY` - an undeclared spelling reads as non-ALLOW instead of raising | `test_engine_decision_spelling.py::test_an_undeclared_spelling_raises_rather_than_dropping_the_event` |
| E7 | `visible_prefix` drops the ALLOW filter - a blocked call satisfies `preceded_by` | 5, incl. `test_a_refused_predecessor_is_invisible_in_every_declared_spelling[*]` |
| E8 | `visible_prefix` drops the `TOOL_EXECUTED` filter | `test_l3_negative_checks.py::test_negative_check[S1]` (2) |
| E9 | `episode_sum` EXCLUDES the pending call - the rule fires one call late | `test_l3_negative_checks.py::test_negative_check[S2]` (2) |
| E12 | **default is DENY** instead of ALLOW - the instrument stops being subtractive | 72 failures across 18 files |
| E13 | `_lookup` traverses before trying the flat key, so `derived.approval_tier` reads absent | 11, incl. `test_seed_policy_benign_floor.py` (5) |
| E15 | `tool_names` narrowing ignored - a tool-scoped rule fires on every tool in its class | `test_armorer_manifest_alignment.py::test_on_the_OLD_wiring_the_same_rule_was_unwritable_and_its_alternative_inert` |

### `crucible/dsl/serialize.py` and `crucible/canon/hashing.py`

| # | Mutation | Killed by |
|---|---|---|
| S1 | **the VERB is dropped from the rule id** - `deny` and `constrain_arg` collide | 111 failures across 12 files |
| S2 | the `constrain_arg` ACTION block is dropped from the id | `test_armorer_patch.py::test_render_parse_round_trip_lands_on_the_same_rule_id[...constrain_arg...]` |
| S3 | `arg_conditions` dropped from the id - **every `when` collides** | 24, incl. `test_dsl_is_present.py::test_the_two_polarities_are_different_rules` |
| S4 | `predicates` dropped from the id | 6, incl. `test_engine_decision_spelling.py` |
| S5 | `enum_list` not sorted - `x in [A,B]` and `x in [B,A]` become two ids | `test_an_enum_list_hashes_the_same_in_either_order` |
| S7 | **convention 1 reversed** - `origin` back inside the id, so a re-proposal is a new rule | `test_convention_1_origin_is_outside_the_rule_id` |
| S9 | `tool_names` not sorted | `test_convention_3_clause_order_does_not_move_the_id` |
| S10 | ruling 38 reversed - the whole `armorer:4` stored as origin, not the class | `test_convention_1_origin_is_outside_the_rule_id`, `test_plugin_enforcement.py::test_handwritten_patch_compiles_and_the_blocked_tool_never_runs` |
| H1 | `hashing.rule_id` hashes only `match`, dropping verb and action | 7 in `test_hashing.py` |
| H2 | a hash-shaped id from the model is accepted | `test_hashing.py::test_a_hash_shaped_id_from_the_model_is_rejected` (2) |

### `crucible/dsl/parser.py`

| # | Mutation | Killed by |
|---|---|---|
| P1 | N2 - `\|` accepted at the lexer | `test_l3_negative_checks.py::test_negative_check[N2]` |
| P2 | operator table no longer longest-first, so `=>` lexes as `>` then `=` | 115 failures |
| P3b | **V1 - cap_selector genuinely optional; a tool-only rule PARSES** | `test_dsl_parser.py::test_cap_selector_is_required_and_first` |
| P4 | tool handles no longer opaque `t_` + 8 hex | `test_dsl_parser.py::test_tool_handles_must_be_opaque` |
| P5 | KB9 - `body_text` widened to the whole statement, so the rule id and origin reach V3 | `test_dsl_validator.py::test_V3_exempts_metadata_and_provenance` |
| P6 | a rule id that is neither placeholder nor real is accepted | `test_dsl_parser.py::test_both_id_forms_parse_and_nothing_else_does` |
| P8 | an unknown `context_field` accepted at the parser | `test_dsl_parser.py::test_an_unknown_context_field_is_named` |

**Where the coverage is genuinely strong.** V4, V5, V6, V7, V8, V9, V10, N3 and
N6 all died on the first mutation, several to tests written specifically for
them; **the three ORDERING mutations (D18, D19, D20) all died too**, which is
worth saying out loud, because check order in this validator is a behaviour and
is argued for at length in the module docstring. The engine's STEP 1 and STEP 3
- membership matching and precedence-by-verb - are the best-guarded code in the
file set: four separate precedence inversions all died on `negative_check[N4]`
and set-equality took fifteen tests down. **The survivors cluster in STEP 2**,
the tri-state predicate layer, where the suite tests the ABSENT road into
UNEVALUABLE and never the WRONG-TYPED one.

---

## What was NOT mutated, and why

* **`crucible/dsl/errors.py` and `nodes.py` as data.** Renaming a clause
  discriminant or an error code is a mutation of a name, not of an invariant;
  the codes are asserted by the tests that assert the behaviour, and D2/D3/P7
  above already cover the case where the CODE is the claim.
* **`crucible/policy/episode.py` and `decision.py`.** The episode seal was the
  first audit's Tier 1 and Tier 3 territory (M11-M14, M34) and `decision.py` is
  a value object with no branch worth breaking.
* **`crucible/armorer/`, `crucible/red/`, `crucible/coroner/`.** Unchanged from
  the first audit's reasoning: model-driven, and every output is re-checked
  downstream by exactly the code this pass went after.
* **Contract and golden DATA.** Mutating a fixture is not mutating an
  invariant, and the first audit already answered the one question worth asking
  there (M45: an edit to a hash-locked contract is caught on every pytest).
* **Whole-suite mutation coverage.** Not attempted, per the brief. Depth on
  five surfaces beats breadth across `crucible/`.

## What could not be closed from this lane's file set

**Nothing.** All twelve real survivors were closable with a test and **none
required a source change.** Three observations belong to the coordinator, and
**no source file was edited for any of them:**

1. **`check_context_fields` carries an emptiness escape that V10 refused one
   check over.** `if self.declared_episode and qualified not in ...` means a
   Part B declaring no `episode_fields` switches the check off in silence.
   V10's own comment states the argument against exactly this shape - *"a
   manifest that declares no arg_paths would switch V10 off in silence, which
   is the shape `UNCLASSIFIED` already has one layer down"* - and then
   `check_context_fields` and `check_product_lexicon` both keep it. For the
   lexicon it is defensible (V3 is a backstop). For the three episode bindings
   that F4's seal rests on it is the same defect V10 was written to remove. A
   one-word change; **not made here**, because it is a behaviour change to a
   validator on a frozen contract path and belongs to a ruling.
2. **`arg_conditions` is the one array restriction 6 NAMES and the one with no
   sort test** (S6). The two arrays it does not name are both covered. Worth a
   line in `canonicalization.md` or in `test_convention_3`'s docstring saying
   which arrays each test actually reaches, because the current pairing reads
   as if the named one were covered.
3. **`E_RULES_NOT_SORTED` and `sort_rules` are a matched pair with no test on
   either end** (D17 + S8), which is why the pair could fail together
   invisibly. Both now have one. Whether `validate_policy_document` should also
   be called on `validate_patch`'s OUTPUT - closing the loop rather than
   trusting the writer - is a coordinator call, not a lane's.

## One incident, recorded

**The runner's first pattern encoding was half-working, and only the failure
count showed it.** The working tree here is CRLF. Encoding each mutation pattern
as UTF-8 with bare `\n` matched every SINGLE-LINE pattern and silently matched
ZERO multi-line ones - 15 of the first 53 reported "pattern occurs 0 times". A
runner that half-works is worse than one that fails, because the half that
works looks like a complete run.

Caught by a **dry pass that asserted every pattern occurs exactly once before
any pytest was launched**, not by a mutation appearing to survive. Had that dry
pass been skipped, fifteen mutations would have been recorded as SURVIVED - and
a survivor is a finding, so the audit would have manufactured fifteen of them
and written fifteen guards that could never go red. Fixed by encoding each
pattern with the terminator the FILE actually uses.

This is the same family as the first audit's `pathlib.write_text` CRLF incident,
one step earlier in the pipeline: **on Windows, line endings are a property of
the file, and any tool that assumes otherwise is wrong silently.**

**A second near-miss, and it is the more important one.** The V1 mutation (P3a)
survived, and V1 is the mechanism behind headline result #1 - the most alarming
possible survivor in this file set. It was **not** a gap. The mutation had not
changed the observable: the text still failed to parse one production later
with the same error code, and `test_dsl_parser.py::test_cap_selector_is_required_
and_first` still passed for the right reason. Re-cut properly, the mutation
died. **A survivor is a finding only after you have checked WHY it survived**,
and the check is to make the mutation stronger, not to write the guard.

---

## Verification

Every number below is a pasted exit code or a pasted summary line, never a grep
of pytest output (`grep -c` returns exit 1 on a zero count, which has produced a
false green in this repo before).

```
BASELINE, before any mutation
  python -m pytest ; echo $?
  1434 passed, 1 skipped, 1 warning in 53.81s
  PYTEST_EXIT=0
  python -m pytest --collect-only  ->  1435 tests collected

AFTER, with the guard file in place
  python -m pytest ; echo $?
  1446 passed, 1 skipped, 1 warning in 40.39s
  PYTEST_EXIT=0
  python -m pytest --collect-only  ->  1447 tests collected   (1435 + 12 guards)

  python scripts/contract-check.py ; echo $?
  CONTRACT_CHECK_EXIT=0

  git status --short  ->  ?? tests/test_dsl_mutation_guards.py   (nothing else)
```

**Every one of the 62 mutations reported `restored_byte_identical: True` and
`git_status: ''`** (the guard file is the only entry after it was written).

### The replay - proof the guards are specific rather than a blanket

All 62 mutations were replayed against `tests/test_dsl_mutation_guards.py`
**alone**, recording which tests go red. **Each of the twelve guarded survivors
turns red on exactly its own test and no other:**

```
D2    red=[test_D2_the_VALIDATOR_refuses_UNCLASSIFIED_on_a_rule_the_parser_never_saw]
D3    red=[test_D3_the_VALIDATOR_refuses_a_SEVENTH_capability_class]
D17   red=[test_D17_a_policy_document_whose_rules_are_OUT_OF_ORDER_is_refused]
D22   red=[test_D22_an_UNDECLARED_episode_context_field_is_refused_by_the_validator]
E3    red=[test_E3_constrain_arg_FAILS_CLOSED_on_absent_null_and_wrong_typed_arguments]
E3b   red=[test_E3_constrain_arg_FAILS_CLOSED_on_absent_null_and_wrong_typed_arguments]
E10   red=[test_E10_a_TYPE_MISMATCH_retains_the_rule_rather_than_dropping_it]
E11   red=[test_E11_a_BOOLEAN_is_not_an_INTEGER_when_money_is_being_summed]
E14   red=[test_E14_preceded_by_reads_the_CLASS_IT_NAMES_and_not_merely_ANY_predecessor]
S6    red=[test_S6_TWO_CLAUSE_ORDERS_are_one_rule_and_therefore_one_rule_id]
S8    red=[test_S8_a_validated_patch_emits_its_rules_SORTED_whatever_order_they_arrived]
P7    red=[test_P7_preceded_by_UNCLASSIFIED_is_refused_BY_ITS_OWN_NAME]
```

E3 and E3b share one guard **by design** - two cuts at one claim, the way the
first audit's M19/M19b did. P3a and P3b both come back `red=-`, which is correct:
P3a has no guard, and P3b's killer lives in `test_dsl_parser.py`.

**Four KILLED mutations also trip a guard, and all four are honest collateral
rather than a specificity failure.** Reported rather than tuned away:

| Mutation | Guards it trips | Why, and why it is fine |
|---|---|---|
| **E4** | E10's | E4 is the same fail-open claim one level up - `UNEVALUABLE` dropping the rule in `_when`. E10's arrangement IS an unevaluable `when`, so the broader mutation trips the narrower guard. E4 is killed by `test_dsl_is_present.py`. |
| **E12** | E3's, E10's, E11's, E14's | default DENY. Every ALLOW assertion in the file fails, along with 72 tests elsewhere. |
| **S3** | S6's | `arg_conditions` dropped from the id, so S6's **POSITIVE CONTROL** fires: two genuinely different rules collide on one id. The control doing its job. |
| **P2** | S6's, the id-agreement test | the operator table no longer longest-first; 115 tests fail. |

Of the twelve guards, all twelve are red-guards; each carries its positive
control **inside the same function**, so a guard that rejects everything - or
one watching a clause that never fires - is caught by its own body. The
thirteenth test in the file, `test_the_compiled_form_and_the_validated_form_
agree_on_the_id`, is an invariant three of the guards lean on, asserted rather
than assumed.
