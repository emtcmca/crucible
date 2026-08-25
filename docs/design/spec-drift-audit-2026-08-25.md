# Spec and plan drift audit, 2026-08-25

**Read-and-report only. No spec, contract, `README.md` or `BUILD-LIST.md` was edited by this
pass.** Every finding below names a file and a line so the coordinator can act on it. Nothing
here is a ruling.

**Scope.** `docs/CONVENTIONS.md`, `docs/measurement-spec.md`, `docs/architecture-spec.md`,
`docs/data-spec.md`, `docs/execution-spec.md`, `docs/lanes-spec.md`, `docs/build-spec.md`,
`docs/separability-proof.md`, `docs/NEEDS-ERIC.md`, `docs/contest/CONTEST.md`. Two source files
are included where they carry a state claim in the same shape.

**Deliberately excluded.** `README.md` and `docs/contest/BUILD-LIST.md` are owned by two other
lanes that are editing them right now. `BUILD-LIST.md:102-107` was seen in passing and does carry
the stale GATE stand-in claim; it belongs to that lane, not to this report.

**Concurrency, stated because it changes how to read section (d).** Other lanes landed work
**while this audit was running**. Re-checked at the end of the pass rather than assumed:

- `docs/design/e-no-events-split-design-2026-08-25.md` now exists and its header reads
  *"Status: DESIGN, ruled by Eric 2026-08-25."* **Eric has ruled on `E_NO_EVENTS`.** Section d.1
  item 1 is amended in place below.
- `docs/proof/f4-unseal-preregistration-2026-08-25.md` now exists, written before the 08-28
  unseal. That is the lock d.3 item 5 wanted.
- `docs/design/g7-unevaluable-2026-08-25.md` now exists and **corrects a premise this audit did
  not test**: G7 does not report `UNEVALUABLE` on all 60 runs.
- `scripts/no-events-census.py`, `tests/test_no_events_census.py` and
  `tests/test_no_events_split.py` are new and untracked.

**Re-verified after those landed, because a moving tree is exactly when a status goes false:**
`docs/results.md`, `targets/design-targets.yaml` and `adapters/` are all **still absent**, and
`E_NO_EVENTS` still appears **zero** times in `docs/NEEDS-ERIC.md`. Findings A6, A8 and d.2 item 1
stand.

**Ground truth used.** Everything in section (b) was read out of an artifact in this working
tree, not out of a document. The batch figures were recomputed from the 60 bundles in
`evidence/batch-night-2026-08-25/`, not taken from `docs/NIGHT-LOG-2026-08-25.md`.

| Quantity | Value | Read from |
|---|---|---|
| Runs in the overnight batch | 60, all exit 0 | 60 `*.exitcode` files, 60 `run-NN.json` bundles |
| Episodes | 1,770 | sum of `rounds[].attacks` across 60 bundles |
| Scorable | **1,614** | sum of `rounds[].scorable`; also 1,770 minus 154 INVALID minus 2 TARGET_FAULT |
| INVALID | 154, from **8** distinct attack instances | `excluded[]` with `reason: invalid_verdict` |
| TARGET_FAULT | 2, from 2 instances | `excluded[]` |
| Breaches | 108 | sum of `rounds[].breaches` |
| Promotions | 95 | sum of `summary.promotions` |
| Rounds | 295, always 6 attacks each | `rounds[]` |
| Run outcomes | 37 `converged`, 23 `PARTIAL` | `summary.status` |
| Exclusion over the 5% ceiling | **51 of 60** runs, median 8.33% | `excluded[]` over `episodes[]` |
| Execution mode | `live`, `g7_g8_exercised: true` | `run-NN.c6.json` `execution_provenance` |
| Gate implementation | `real_gate.RealGate` (LIVE), `gs://crucible-policies-x7` via `GcsBlobIO` | same |
| pytest | **exit 0** | run at `0ee05ee`, this pass |
| contract-check | **exit 0, six passes** (HASH, FIXTURES, SWEEP, STATUS, TERMS, FRESH) | run this pass |

---

## (a) State claims that are now false

The world moved on 2026-08-24/25. Sixty live campaigns ran, `GcsBlobIO` executed against GCS at
every one of 95 promotions, and the policies bucket is not empty. The claims below are sorted by
whether correcting them would be a repair or a defect.

### a.1 LIVE DRIFT. These documents assert, in the present tense, something that is no longer true.

| # | Site | The claim | Why it is drift |
|---|---|---|---|
| **A1** | `docs/measurement-spec.md:7` | *"Every number in §8 of this document is a DESIGN TARGET. **No run has occurred.**"* | Sixty have. This is the document header of the highest-ranked measurement spec, it is present tense, and it is the first thing a reader meets. **The design-target guard must survive the edit; only the second sentence is false.** |
| **A2** | `docs/measurement-spec.md:1135` | *"**DESIGN TARGETS. No run has occurred.** See the header warning and §7.9."* | Same sentence, on §8.1 itself, immediately above the headline board a reader would compare against. |
| **A3** | `docs/build-spec.md:359` | *"Every number in its §8 is a DESIGN TARGET. **No run has occurred.**"* | Same. `build-spec.md` is authoritative over nothing, but it is still read, and it is the third copy of a sentence that now has to be corrected in three places. |
| **A4** | `docs/NEEDS-ERIC.md:438-440` | *"That claim is not true yet. **Nothing has ever been promoted, the policies bucket is empty, and `GcsBlobIO` has never executed.** To make it true, the loop has to run and promote on several separate days between now and submission."* | This is a **live coordinator note on an open obligation** (item 4, track fit), not a dated record. All three facts are now false. The obligation is **partly discharged**: promotions exist on 2026-08-25. The remaining half, *promoting on several separate days*, is now a three-day question and needs restating rather than deleting. |
| **A5** | `docs/NEEDS-ERIC.md:9-14` | *"**Updated 2026-08-23 (Day 4).** ... Item 13 is now the only one holding anything up, and it is deliberately parked: the Gemma sheet is signed ONCE, after the 50 pre-registered stability runs, which themselves run after the live run."* | The 50 stability runs **completed** (`docs/proof/cartographer-stability-2026-08-24.json`: `planned_runs: 50`, `executed_runs: 50`, 36 OK / 14 REJECTED) and the live runs completed. Item 13 is **no longer parked; it is ready for Eric's signature.** The header is two days stale on a file that calls itself *"the only list."* |
| **A6** | `docs/NEEDS-ERIC.md` (whole file) | The single largest open owner decision of 2026-08-25, the `E_NO_EVENTS` conflation, **is not in this file at all.** Grep for `E_NO_EVENTS` in `docs/NEEDS-ERIC.md` and `docs/CONVENTIONS.md` returns nothing; it lives only in `docs/design/e-no-events-conflation-2026-08-25.md` and `docs/NIGHT-LOG-2026-08-25.md`. | The file's own opening line is *"This file is the only list. A decision that lives only in a transcript is gone at the next `/clear`."* A decision that lives only in a design brief is one `/clear` better off and still not on the list. **This is the highest-severity item in section (a)**, because it is an omission and no grep for a stale value will ever find it. |
| **A7** | `crucible/conductor/campaign.py:64-71` | *"`real_gate.GcsBlobIO` ... **HAS NEVER RUN AGAINST GCS.** Its create-only precondition, its 412 branch and its generation-pinned read-back are written from `data-spec.md` 3.1/3.2 and no test covers them ... The first `--live` run is therefore the first execution of that code, **and the banner says so**."* | It has now run 95 times through a live gate whose findings record G7 and G8 evaluated against live GCP. This is source, not spec, but it is a present-tense state assertion and **the run banner is generated from it**, so it prints a false warning on every run. The *"no test covers them"* half is still true and should survive. |
| **A8** | `docs/measurement-spec.md:8` and `:1121` | *"Targets live in `targets/design-targets.yaml`, which the reporting pipeline cannot read (§7.9)"* and guard 9, *"Target-value quarantine. All §8 design targets live in `targets/design-targets.yaml`."* | **`targets/design-targets.yaml` does not exist anywhere in the tree.** `find . -name "design-targets*"` returns nothing; the only two occurrences of the string are these two spec lines. The quarantine that separates design targets from results is a **phantom control**: a check that cannot fire, named twice as though it does. This is the project's own signature failure shape sitting inside the measurement spec, and it matters most in the week the Results table gains an `Observed` column. |
| **A9** | `docs/measurement-spec.md:4` | *"**MUST be hash-locked before the first run.** See §6.1."* | No freeze record for `measurement-spec.md` exists in `docs/proof/`, and none of the six hash-lock fields covers it. **In substance the obligation was met a different way** and the specs say so: the gate rule extracted from this file was frozen at D2 (`docs/proof/d2-gate-rule-freeze.json`) and `contracts/gate_rule.v1.yaml` outranks this file on precedence (`docs/NEEDS-ERIC.md:279-282`, `docs/measurement-spec.md:992-995`). **Reported as a wording defect, not as a claim that the runs are invalid.** That call is Eric's. |

### a.2 NOT DRIFT. Deliberate historical record. Correcting these would be the defect.

Every hit below sits inside a **dated ruling block** whose job is to state what that ruling
invalidated **on the date it was made**. Rewriting them would destroy the audit trail the project
exists to demonstrate, and would break the freeze scripts, which refuse to re-run over a record
naming a different value.

| Site | Container | Verbatim shape |
|---|---|---|
| `docs/CONVENTIONS.md:64-67` | ruling 53, `SPINE_VERSION 22`, 2026-08-24 | *"**WHAT IT DOES NOT INVALIDATE:** no published figure, because there are none; no promoted policy, because nothing has ever been promoted and `GcsBlobIO` has never executed."* Dated invalidation statement. |
| `docs/CONVENTIONS.md:123-128` | ruling 52, `SPINE_VERSION 21`, 2026-08-24 | *"No published figure is affected, because there are none ... **Nothing has ever been PROMOTED.** `GcsBlobIO` has still never executed against GCS, the policies bucket is empty."* The freeze script demanded this statement; it is the record. |
| `docs/CONVENTIONS.md:469` | ruling 47, 2026-08-22 | *"No number has ever been measured against this corpus."* True of that corpus on that date. |
| `docs/CONVENTIONS.md:576, 613, 649, 687, 691, 696, 2342` | rulings 23.4, 29-33, 26-28, 42 | *"Invalidates nothing measured. Nothing has been measured."* Seven dated instances. All are the ruling pricing its own cost at the time. `:2342` adds *"This is the cheapest it will ever be"*, which is the argument, not a status. |
| `docs/CONVENTIONS.md:348, 418-456, 500` | rulings 48, 49 and the clause-coverage correction, 2026-08-23 | *"Two of the nine clauses"*, *"8 of 9 clauses are exercised"*, *"§8.3 appears in none of the Objective Set's nine clauses"*. Nine was the count on those dates. **One exception is carried into (b) below**: `:456` is a standing publication rule, not a record. |
| `docs/execution-spec.md:255-266` | *"**DAY 3 STATUS, recorded 2026-08-22, the day itself.**"* | *"nine clauses, each with a `clause_id`"*, *"the nine known-bads"*, *"eight tools"*. Explicitly a dated status block. The eight tools and nine known-bads are still correct; the nine clauses were correct that day. |
| `docs/NEEDS-ERIC.md:113-125` | item 14, header reads **RULED, BUILT, FROZEN AND CLOSED 2026-08-23** | *"`derived.account_risk_flag_open` scores 0.6579"*, *"pins `derived_fields` at exactly seven"*, *"the 26-pair proof"*, *"nothing promoted is invalidated, because nothing has ever been promoted."* This is the **pre-ruling options analysis**, preserved. All four values are dead; none is a live claim. Low-severity note only: `derived.account_risk_flag_open` is a **field name that never existed** (the field that shipped is `derived.risk_hold_open`), so it is quotable-looking dead vocabulary sitting in the tap list. |
| `docs/ops/dry-run-preflight.md:121` | *"§5 Known unknowns **going in** ... say these out loud before the run"* | *"`GcsBlobIO` has never executed and the policies bucket is empty."* A pre-run document. Correct as of the moment it was written and worthless if edited. |
| `docs/design/batch-2026-08-24-preregistration.md:49` | a preregistration | Same sentence. A preregistration that moves after the run is not a preregistration. |
| `docs/proof/d3-*-superseded-*.json`, `docs/proof/d5-*-superseded-*.json` | archived freeze records | `what_it_does_NOT_invalidate` fields carrying the same sentence. **These are the artifacts.** Ruling 46's logic applies in reverse: the record owns its own value. |
| `docs/proof/L3-real-gate-G7-G8-2026-08-22.txt:105` | dated gate probe output | *"against a local blob store, and has NEVER run against GCS."* Tool output from 08-22. There is a newer one beside it, `L3-real-gate-G7-G8-2026-08-25.txt`. |

### a.3 The two claims the task listed that turned out NOT to be drift anywhere

- **The GATE as a stand-in.** `promote=lambda c, r: True` survives in the tree only as a
  **named dead value in a guard**: `crucible/conductor/bundle.py:227` (*"this guard exists
  because ... sat in `campaign.py` for"*), `crucible/conductor/campaign.py:555` (*"lived here
  until 2026-08-22"*), `:637` (`"replaces": "promote=lambda c, r: True"`), and
  `crucible/conductor/real_gate.py:611` (*"Same shape as ..., so it drops straight into"*).
  All four are correct and load-bearing. No in-scope spec claims the gate is a stand-in.
- **The sealed F4 family described as not existing on disk.** No spec says this. It **does**
  exist: 24 files under `corpus/sealed/` in the `C:\dev\crucible-wt-SEAL` worktree on branch
  `freeze/D5-corpus`, matching `corpus/F4-MANIFEST.json` (`instances: 24`, `floor: 18`). It is
  correctly absent from the primary checkout, and `docs/CONVENTIONS.md:145-150` records the freeze
  script refusing to run here with `E_SEALED_BELOW_FLOOR` for exactly that reason. **Nothing to
  fix.** Counted, not read: no instance content was opened by this audit.

---

## (b) Counts that disagree between documents

Ruling 19 recorded two documents written hours apart disagreeing on a field count. Three counts
have done it again. For each: the true value, the artifact it was read out of, and every document
carrying something else.

### B1. `derived.*` fields: the true value is EIGHT. Six live spec sites still say seven.

**True: 8.** Read two ways, and they agree:

- `corpus/derived_schema.json` gives `derived_fields` **8** entries: `approval_tier`,
  `subject_verified_in_episode`, `episode_sum_amount_minor_same_beneficiary`,
  `episode_count_same_subject`, `account_age_days`, `delivery_confirmed`, `days_since_delivery`,
  `risk_hold_open`.
- `contracts/derived_schema.schema.json` pins `derived_fields` at `minItems: 8, maxItems: 8`.

The contract says so in its own words at `contracts/derived_schema.schema.json:5`: *"THREE
episode.\* fields and EIGHT derived.\* fields ... The eighth derived field, derived.risk_hold_open,
was added 2026-08-23: the count read SEVEN until then and this description is the fourth home that
had to move with it."* And at `:107`: *"the count lives in FOUR places ... All four move together
or Part B and the goldens diverge."*

**This matters more than an ordinary count.** `derived_schema_hash` is one of the six hash-lock
fields, it freezes at D5 gated on the label-blindness check, and `contracts/MANIFEST.json` C3
carries the schema. A document that says seven is describing a different hash-locked artifact.

Sites still carrying **seven**:

| File:line | Context | Kind |
|---|---|---|
| `docs/architecture-spec.md:394` | `before_tool_callback` row: *"stamp the seven `derived.*` fields over the pending args"*. This is the enforcement point's own description. | **LIVE** |
| `docs/build-spec.md:335` | *"seven `derived.*` fields stamped by the plugin"* | **LIVE** |
| `docs/data-spec.md:43` | amendment header: *"NEW section 1.15 ... Three `episode.*` fields, seven `derived.*` fields"* | **LIVE** |
| `docs/data-spec.md:438` | *"the seven derived.\* fields, so replay reads the stamped values instead of recomputing"* | **LIVE** |
| `docs/data-spec.md:1617` | *"two of the seven `derived.*` fields become unnecessary"* | **LIVE** |
| `docs/lanes-spec.md:108` | contract **C3**'s own row: *"seven `derived.*` fields stamped by the plugin in `before_tool`"*. The contract table describing the contract that says eight. | **LIVE** |
| `docs/measurement-spec.md:1437` | *"folds them into the seven `derived.*` fields"* | **LIVE** |
| `docs/CONVENTIONS.md:1522` | ruling 19's own correction note, which names its dead value on purpose | historical |
| `docs/NEEDS-ERIC.md:94, 96, 118` | inside CLOSED item 14's pre-ruling options analysis | historical |

**Seven live sites across five documents. Three are dated records and must not be touched.**

**Note the shape.** `contracts/derived_schema.schema.json:107` says the count lives in four places
and names all four, and all four are correct. It did not name the prose sites, and the prose sites
went stale by standing still. **The registry listed the code homes and not the document homes.**

### B2. Hash-locks: the spine contradicts itself. FIVE in seventeen places, SIX in one, six fields in the bundle.

**True: 6 hash-lock FIELDS.** Read from `evidence/batch-night-2026-08-25/run-01.json` at
`summary.hash_locks.values`: `gate_rule_hash`, `target_agent_hash`, `manifest_hash`,
`objective_set_hash`, `corpus_hash`, `derived_schema_hash`. Six values, six provenance records.

**The disagreement is inside `docs/CONVENTIONS.md` itself**, which is the spine:

- `docs/CONVENTIONS.md:159` (ruling 51, 2026-08-24, the **newest** statement): *"**NONE OF THE SIX
  HASH-LOCKS MOVED.** `gate_rule`, `target_agent`, `manifest`, `objective_set`, `corpus` and
  `derived_schema` are byte-identical."* Enumerates six and calls them hash-locks.
- `docs/CONVENTIONS.md:1481-1483` (ruling 20, 2026-08-20): *"The run manifest's four hash-locks
  become **FIVE** ... Update every place that says 'four hash-locks.'"*
- `docs/CONVENTIONS.md:1945` (ruling 30): *"`target_hash` is one of the **five** hash-locks."*
- `docs/CONVENTIONS.md:2476`: *"'four hash-locks' - fourteen sites | **Five**, since ruling 20."*

**The reconciliation, which no document currently states:** the FIVE formulation counts *locks*
and bundles the last as *"corpus + `derived_schema_hash` (D5)"*, which is two fields under one
lock. The SIX formulation counts *fields*. **Both readings are defensible and neither is written
down as the convention**, which is why the number keeps moving. This is the fourth telling
(three, four, five, six) and `docs/execution-spec.md:541` already says *"Three tellings, three
numbers"* about the first three.

Sites carrying **FIVE**: `docs/execution-spec.md:35`, `:161`, `:428`, `:541`, `:587`, `:810`,
`:833` · `docs/lanes-spec.md:20`, `:111`, `:112`, `:179` · `docs/build-spec.md:44`, `:489` ·
`docs/measurement-spec.md:953`, `:998-1002` · `docs/data-spec.md:139` ·
`docs/NEEDS-ERIC.md:609` · `docs/contest/CONTEST.md:216` · plus `crucible/conductor/campaign.py:73`
(*"THE FIVE HASH-LOCKS ARE READ FROM ARTIFACTS NOW"*, source, with code below it reading six).

**Per precedence, `CONVENTIONS.md` wins and every downstream FIVE is the defect. But CONVENTIONS
carries both numbers, so precedence cannot settle it and Eric has to.** Saying it out loud rather
than picking: the newest spine statement says six fields; the ruling that set five is older, sits
three sections down, and has not been retracted.

### B3. SEP-BY split: `CONVENTIONS.md` still carries the exact wording `measurement-spec.md` diagnosed as the defect.

**True: 21 policy-separated / 3 oracle-separated, over 24 counted pairs, out of 27.**
Read from `corpus/pairs.json`: 27 entries, `sep_by` counts `POL: 21, ORC: 3, CUT: 3`.

- `docs/measurement-spec.md:568-575` is **correct and explicit**: *"**THIS ROW READ 'Current
  split' AND IT WAS NOT CURRENT. Corrected 2026-08-22.** 18 / 4 is the **target**; the
  **measured** split is **21 policy / 3 oracle**, over 24 counted pairs with 3 cut, out of 27
  pairs in `corpus/pairs.json`. Read it out of the tool rather than out of this page."*
- `docs/CONVENTIONS.md:1373-1376` (ruling 17) **still reads**: *"**Current split: 18 policy,
  4 oracle.**"*

**This is a precedence inversion and it is the clearest one in the set.** The correction landed in
the downstream document and never propagated up to the spine, so a lane obeying the precedence
order takes the number the downstream document had already identified as stale. The dangerous half
is the word *"Current"*, which `measurement-spec.md:575` names as the thing that made it stale
rather than aspirational.

Other sites carrying 18/4 as though current: `docs/measurement-spec.md:1150` and `:1154`,
`docs/execution-spec.md:375`, `:810`. In section 8 those sit inside a design-target table, so
labelling them targets is defensible. The row at `:1154` prints **18 policy / 4 oracle in both the
v0 and vFinal columns** and is described as *"printed next to every ASR and BPR figure above,
permanently"*, which reads as a current reporting value rather than a target.

`docs/data-spec.md:572` shows `"sep_by_split": { "policy": 21, "oracle": 3 }` in a schema example,
which happens to be the true measured value.

**Live-run note, so the units are not conflated.** The batch prints two different SEP-BY things:
per-run **21 policy / 3 oracle** (the pair worksheet, `run-NN.c6.json` at `labels.sep_by_split`)
and an aggregate **1,260 policy / 180 oracle** over episodes. **Different denominators.** Any
write-up must say which one it is quoting.

### B4. Pair count: 27, not 26.

**True: 27** entries in `corpus/pairs.json`. `docs/separability-proof.md:309` states it correctly:
*"`corpus/pairs.json` holds **27** pairs total; **28** rows now print in section 2 (27 pairs +
P24)."* `docs/codex-review-2026-08-21.md:264` also says 27.

Carrying **26**: `docs/CONVENTIONS.md:1742` (*"a change to the 26-pair"*), `docs/NEEDS-ERIC.md:121`
(historical, inside closed item 14), and **`CLAUDE.md:49`**, whose document table describes
`separability-proof.md` as *"the 26-pair worksheet"*. The `CLAUDE.md` entry is the one that
propagates: it is what a session reads first, and this audit's own task brief inherited "26-pair"
from it.

### B5. Objective Set clauses: 11, and the count did NOT rot into live prose. One standing rule did.

**True: 11.** `contracts/objective_set.v1.json` has 11 clauses, ending
`inv_pii_read_of_a_nonsubject_account` (ruling 53, `SPINE_VERSION 22`, 2026-08-24). Every live
bundle's `clause_coverage.clauses` has 11 rows.

**Good news, reported because a clean grep is worth reporting:** every *"nine clauses"* in the
spec set sits inside a dated ruling or a dated status block, all listed in a.2. There is no live
spec sentence asserting the Objective Set has nine clauses today. I checked this two ways, by
phrase and by numeral, because a single grep returning the answer I wanted would not be evidence.

**One exception, and it is a standing rule rather than a record.** `docs/CONVENTIONS.md:456`:
*"A per-clause coverage matrix ... ships with the evidence bundle. A published breach rate without
it is an overclaim by omission, **because a reader assumes all nine clauses were in play.**"* This
sentence governs what may be published **this week**, and the matrix it mandates now has eleven
rows. The rule is right; the number in its rationale is dead.

**And that matrix says something no document has caught up with.** Aggregated over all 60 live
runs, only **3 of the 11 clauses ever fired**: `inv_repeated_mutation_on_one_subject` (fired in 44
runs), `inv_pii_read_of_a_nonsubject_account` (43), and
`inv_escalated_below_the_queue_the_amount_requires` (5). The other eight are `NEVER_TRUE` or
`UNREACHED` in every one of the 60 runs. The specs' current coverage story is *"8 of 9 exercised,
1 dark"* (`docs/CONVENTIONS.md:436`), taken 2026-08-23 over offline sources. **On the live batch
the picture is materially worse and it is written down nowhere.** Ruling 17 and
`CONVENTIONS.md:456` both require this to travel beside any rate, which makes it a publication
blocker rather than a footnote.

### B6. `scorable` is 1,614, and 1,616 is already in a Devpost draft.

**True: 1,614.** `RoundRecord.scorable` at `crucible/conductor/conductor.py:222-229` removes
**both** TARGET_FAULT and INVALID: *"TARGET_FAULT and INVALID are removed here, once, so no
consumer has to remember to (ruling 33.4)."* Summing `rounds[].scorable` across the 60 bundles
gives 1,614. So does 1,770 minus 154 INVALID minus 2 TARGET_FAULT.

**1,616 is 1,770 minus the INVALID only.** It drops the two target faults.

Carrying 1,616: `docs/NIGHT-LOG-2026-08-25.md:236`, `CLAUDE.md`'s session-state block, and, the
one that matters, `docs/devpost/2026-08-25-update-6-first-promotions.md:6` (*"1,770 episodes of
which 1,616 were scorable"*), which is **drafted for publication**. Two out of 1,770 is immaterial
to any rate and entirely material to a project whose pitch is that its numbers mean something.
**Fix before the post goes out.**

### B7. Counts checked and CORRECT everywhere, so the next pass does not redo them.

| Quantity | True value | Read from | Status |
|---|---|---|---|
| Benign fixtures | **26** | 26 JSON files in `fixtures/benign/` plus `FORMAT.md` | consistent: `CONVENTIONS:942, 952`, `measurement-spec:364, 468, 485, 533`, `execution-spec`, `lanes-spec` |
| Near-miss fixtures | **14** | `near_miss: true` in 14 of the 26 | consistent |
| Known-bad fixtures | **9** | `tests/golden_traces/known_bad/KB1..KB9` | consistent. `fixtures/known_bad/` holds only `.gitkeep`, which is expected. `data-spec.md:408`'s *"Only 5 of 9 are breach"* is about the known-bads and is correct |
| Benign golden traces | 6 | `tests/golden_traces/benign/BF01..BF06` | not contested anywhere |
| Training corpus | **50** | 50 files in `corpus/training/` | consistent, `CONVENTIONS:938` |
| Sealed F4 | **24, floor 18** | `corpus/F4-MANIFEST.json`, and 24 files present in the SEAL worktree | consistent. `CONVENTIONS:941` still says *"Supersedes the '9' in `data-spec.md`"* but `data-spec.md:30` was corrected and no longer says 9. Harmless stale pointer |
| Capability classes | **6** plus the `UNCLASSIFIED` sentinel | 6 distinct in `target/refund_agent/capability_manifest.json` | consistent: `CONVENTIONS:743, 937`, `lanes-spec:108`. `NEEDS-ERIC.md:181` correctly notes `INERT` is not a seventh |
| Tools | **8** | `capability_manifest.json` `tools` has 8 | consistent |
| Contracts | **10** (C1..C10) | `contracts/MANIFEST.json` `contract_count: 10` | consistent. `execution-spec:709`'s *"Nine contracts hashed"* carries its own *"(a tenth, C10 ... was added D1 evening)"* and is a correct dated record |
| ADRs | **18** | `docs/adr/` holds ADR-0001 through ADR-0018 | `CONTEST.md:216` says eighteen and shows its recount note |
| `episode.*` fields | **3** | `corpus/derived_schema.json`, `minItems/maxItems: 3` | consistent |
| Attacks per round | **6** | all 295 rounds carry exactly 6 | consistent |
| Round cap | **6** | `CONVENTIONS:945`, `contracts/gate_rule.v1.yaml` | consistent. `measurement-spec:27` and `data-spec:28` say 4 inside amendment blocks recording the change |
| DSL verbs | **3**, no `allow` | `CONVENTIONS:756` | consistent |
| Narrowing attempts | not a frozen spec number | nothing in the spec set fixes a narrowing-depth count | **no drift to report.** The 96 / 41 / 6 in `NIGHT-LOG` is an observation, not a spec value |

---

## (c) Ruling 46 violations: hash VALUES copied into documents

> **Ruling 46: a frozen hash has exactly one owner, the artifact.** Record the path, read the value
> at use time.

**No hash value is reproduced below.** Each row names the file, the line, and which lock the
literal belongs to, so the coordinator can replace it with a path. All were found with
`grep -nE "\b[0-9a-f]{16}\b"` over the ten in-scope documents.

### c.1 LIVE values. These name a hash that is in force right now. Highest severity.

A live value copied into prose is the case ruling 46 was written for: it looks correct today,
which is exactly why nobody re-checks it, and it goes stale silently the next time a freeze fires.

| File:line | Which lock | Note |
|---|---|---|
| `docs/CONVENTIONS.md:56` | `objective_set_hash`, current | Inside ruling 53. Names both the superseded and the **in-force** value in one sentence |
| `docs/CONVENTIONS.md:612` | `gate_rule_hash`, current | *"... is untouched"* |
| `docs/measurement-spec.md:994` | `gate_rule_hash`, current | *"frozen at ... on 2026-08-21 before anything was measured"*. Replace with `docs/proof/d2-gate-rule-freeze.json` |
| `docs/execution-spec.md:220` | `gate_rule_hash`, current | Day 2 status block. It already names `docs/proof/d2-gate-rule-freeze.json` in the same sentence, so the value adds nothing |
| `docs/NEEDS-ERIC.md:282` | `gate_rule_hash`, current | |
| `docs/NEEDS-ERIC.md:418` | `gate_rule_hash`, current | Already names the proof file beside it |
| `docs/NEEDS-ERIC.md:606` | `gate_rule_hash`, current | |

**Seven sites, two distinct in-force values.** The gate-rule value appears six times, which is the
shape ruling 46 exists to stop: six places to correct when D2 is ever re-frozen, and no mechanism
that would notice five of them.

`docs/execution-spec.md:220` is the instructive one. It names the value **and** the artifact path
in the same sentence, so the fix is subtraction and costs nothing.

### c.2 SUPERSEDED values named inside dated rulings.

These are dead values in historical records. Several are named **on purpose**, because the ruling
is about the move. **Coordinator judgement, not a mechanical fix.** Flagged so the decision is
made once rather than per file.

| File:line | Which lock | Character |
|---|---|---|
| `docs/CONVENTIONS.md:55` | `objective_set_hash`, superseded | ruling 53, *"Every verdict taken under ..."* |
| `docs/CONVENTIONS.md:120` | `corpus_hash`, superseded | ruling 52, *"the 50-instance training corpus at ..."* |
| `docs/CONVENTIONS.md:460` | `corpus_hash`, both old and new | ruling 47, an explicit `old -> new` in a heading |
| `docs/CONVENTIONS.md:522, 524-525` | `target_agent_hash` and `manifest_hash`, first and second of four freezes | the ruling is **about** which freeze a document carried, so the values are its evidence |
| `docs/CONVENTIONS.md:633` | a deliberately-not-used variant | *"naming the unstripped ... would name a number no episode can ever carry"*. Names it to forbid it |
| `docs/CONVENTIONS.md:689, 1938, 1951-1952` | `target_agent_hash`, ruling 30's before and after | the ruling is that the lock did not cover a tool body; the two values ARE the proof |
| `docs/execution-spec.md:259` | `objective_set_hash`, first of several | **the strongest candidate for removal.** The very next sentence reads *"Ruling 46 forbids naming a current hash in prose: read `target/refund_agent/FROZEN.json`"* and then *"This sentence named the second of four and was stale within hours."* The document states the rule and breaks it two clauses later |
| `docs/execution-spec.md:728-729` | `target_agent_hash`, `manifest_hash`, superseded | *"STATED RATHER THAN RECONCILED"* |
| `docs/lanes-spec.md:99` | `objective_set_hash`, superseded | plain restatement, no ruling around it. **Removable.** |
| `docs/NEEDS-ERIC.md:419` | a dry-run gate-rule value, explicitly dead | *"That value is now ..."* |
| `docs/NEEDS-ERIC.md:610` | `objective_set_hash`, superseded | plain restatement. **Removable.** |

**Recommendation, for the coordinator to accept or refuse:** keep the values where the ruling's
subject is the move itself (`CONVENTIONS:460, 522-525, 633, 689, 1938, 1951-1952`), and strike the
plain restatements (`execution-spec:259`, `lanes-spec:99`, `NEEDS-ERIC:610`) in favour of the
artifact path.

### c.3 SYNTHETIC example values in schema illustrations.

`docs/data-spec.md` carries roughly **35** sixteen-hex literals across its `jsonc` payload
examples, at `:122-126`, `:130`, `:144-149`, `:183-188`, `:198`, `:202`, `:216`, `:244-246`,
`:331`, `:373`, `:398-399`, `:430`, `:453`, `:524-525`, `:582-586`, `:624`, `:990-991`. None
matches a value in force; they are illustrative.

**Ruling 46 is not violated in the letter and there is one exposure worth naming.** At `:126` a
synthetic value sits on the key `"objective_set_hash"` with the comment *"FROZEN at D3. The
definition of breach."*, and at `:130` another sits on `"derived_schema_hash"`. A reader skimming
for the frozen values could take either as real. **Cheapest fix if the coordinator wants one:** a
sentinel prefix or an all-zeros form, as `:125` already does for `policy_seed_hash`.

### c.4 Instruments used, and their limits

The `[0-9a-f]{16}` pattern **cannot see** a hash printed with different casing, a truncated
eight-character form, or a full SHA-256. I checked `CONVENTIONS.md` for truncated forms by eye and
found one pair at `:157`, the old and new C6 manifest entries inside ruling 51, which is the same
class as c.2. `contracts/MANIFEST.json` stores full SHA-256 values and IS the artifact, so it is
not in scope. **This report reproduces no hash value, whole or truncated.**

---

## (d) What is left before 2026-08-30

Today is **2026-08-25**, day 6 of 11. **Held-out unseal 08-28. Code freeze 08-28. Submit 08-30.**
Three working days.

### d.0 The eleven-day plan against reality. Blunt.

`docs/execution-spec.md:174-508`.

| Day | Planned | Actual |
|---|---|---|
| **D1 Thu 08-20** | Money, kill switch, canonicalizer; nine contracts hashed | **DONE**, and a tenth contract added the same evening |
| **D2 Fri 08-21** | Trust boundary, gate, hash-lock, first GCP deploy | **DONE.** `docs/proof/d2-gate-rule-freeze.json`, `cloud-run-deploy-2026-08-21.txt`, `armorer-403.txt` |
| **D3 Sat 08-22** | Tripwire, 9 known-bads, the freeze | **DONE**, with its own dated status block |
| **D4 Sun 08-23** | Policy engine, DSL, validator, plugin | **DONE** |
| **D5 Mon 08-24** | Corpus, warden, baseline | **DONE.** `docs/proof/d5-corpus-freeze.json`, `d5-derived-schema-freeze.json` |
| **D6 Tue 08-25, THE CUT LINE** | Coroner, Armorer, first breach-to-autopsy-to-patch-to-gate cycle, run the cut-line test and **cut today, in writing** | **OVERSHOT, not missed.** Coroner and Armorer are built (`crucible/coroner/`, `crucible/armorer/`), and the loop did not merely complete one cycle: it completed 295 rounds across 60 live campaigns and promoted 95 times. **The cut-line test at `execution-spec.md:514` passes on its own terms:** benign 26/26, near-miss 14/14, all 9 known-bads returning expected verdicts, one command end to end. **What has NOT happened is the written cut.** The spec says *"Fail: cut immediately, today, in writing"*, and is silent on recording a PASS. **Record the pass in writing today anyway**, because a cut line nobody wrote down is one that can be re-litigated on day 9 |
| **D7 Wed 08-26** | Red Strategist, Gemma corpus gen, governor, conductor | **Three of four DONE early** (`crucible/red/`, `crucible/governor/`, `crucible/conductor/`). Gemma corpus generation is **WITHDRAWN by ADR-0018**, not pending |
| **D8 Thu 08-27** | Convergence run, replay viewer, production deploy, Model Armor floor settings, numbers into `docs/results.md` | **Convergence run DONE EARLY** (60 of them). **Replay viewer DONE** (`crucible/replay/`). **Redeploy DONE** (`docs/proof/cloud-run-redeploy-2026-08-24.txt`). **Model Armor floor settings: NO PROOF IN THE TREE.** `grep -ri "floorsetting" docs/proof/ infra/ scripts/` finds nothing. **`docs/results.md` DOES NOT EXIST** |
| **D9 Fri 08-28** | Unseal held-out, third-party target adapter, CODE FREEZE | Unseal on schedule. **Third-party target NOT STARTED: there is no `adapters/` directory.** See d.3 |
| **D10 Sat 08-29** | Diagram, README, ADRs, **record the video** | Diagram **DONE** (`docs/diagrams/architecture.md`, `loop.svg`). ADRs **DONE**, 18 of them. README owned by another lane. **Video not started** |
| **D11 Sun 08-30** | Submit | ahead of it |

**The honest summary: the build is ahead of the plan and the paperwork is behind it.** Days 7 and
8 landed on day 5 and 6. What is missing is not code. It is `docs/results.md`, the written cut,
the coverage matrix that has to travel beside every rate, and one owner ruling that decides
whether any rate is quotable at all.

### d.1 What ERIC must decide. Nothing below can be built around.

1. **`E_NO_EVENTS`. RULED 2026-08-25, DURING THIS AUDIT. Amended rather than deleted, because
   what is still owed changed shape.** The finding is
   `docs/design/e-no-events-conflation-2026-08-25.md`: one reason code covers both a fixture whose
   world could not produce a tool call and **a target that refused a bribe, which is a successful
   defense being deleted from the denominator.** All 154 INVALID episodes carry it, from 8 attack
   instances, and exclusion sits over the 5% ceiling in **51 of 60 runs**, median 8.33%.
   `docs/design/e-no-events-split-design-2026-08-25.md` records Eric approving the order: split
   the reason code first, then repair the Cause A instances.
   **Three things are still owed and none is closed by the ruling:**
   (i) `E_NO_EVENTS` appears **zero** times in `docs/NEEDS-ERIC.md`, re-checked after the ruling
   landed, so the file that calls itself *"the only list"* still does not carry the decision;
   (ii) repairing Cause A instances is a **corpus change**, which moves `corpus_hash` and needs its
   own ruling with a written invalidation statement, and the 60-run batch is measured against the
   current corpus, see d.3 item 3;
   (iii) **until the split ships and is re-measured, no rate from this batch is quotable**, because
   the denominator still contains the conflation.
2. **Hash-locks: five or six.** Section B2. The spine says both. Every external surface (README,
   `CONTEST.md:216`, the video script at `execution-spec.md:587`, the Devpost posts) prints
   whichever it picked. **One ruling, then one sweep.**
3. **Item 13, the Cartographer ratification sheet.** Its stated precondition is met: 50 of 50
   pre-registered runs executed, 36 OK and 14 REJECTED
   (`docs/proof/cartographer-stability-2026-08-24.json`). It needs Eric's signature, and
   `docs/NEEDS-ERIC.md` still describes it as parked.
4. **Item 9, `ORD-13` / `ORD-14`.** Two benign fixtures authored after the review pass, open since
   2026-08-22, with no ratification record while the two they replaced and the sealed family both
   have one. `docs/NEEDS-ERIC.md:559-568`: *"It is two fixtures, and it stands between the corpus
   and a true sentence about it."*
5. **Devpost Update 6.** `docs/devpost/2026-08-25-update-6-first-promotions.md` is written and
   unposted. **Correct 1,616 to 1,614 first** (B6). Post or hold is Eric's call.
6. **Track fit, `docs/NEEDS-ERIC.md:438`.** The obligation *"promote on several separate days"* is
   now partly discharged. 08-26, 08-27 and 08-28 are the days available. Decide what the write-up
   claims before the write-up is written.
7. **A9, `measurement-spec.md:4`.** *"MUST be hash-locked before the first run."* Sixty runs have
   occurred and that file carries no freeze record. The substance is arguably met by the D2
   gate-rule freeze. **Confirm that reading in writing or fix the sentence.** Do not leave it as a
   self-declared MUST that a judge can check and find unmet.

### d.2 What must be BUILT or WRITTEN. Ordered by what blocks what.

1. **`docs/results.md`.** Does not exist. `execution-spec.md:432` requires numbers land in it, and
   `:495` makes it the video gate: *"Every number spoken traces to a file in `docs/results.md`."*
   **This blocks the video, which blocks day 10.** Build it from
   `evidence/batch-night-2026-08-25/` with `k=1` and the SEP-BY split beside every figure.
2. **The per-clause coverage matrix beside every rate.** `CONVENTIONS.md:456` and ruling 17 both
   require it, and the live picture is **3 of 11 clauses fired across all 60 runs** (B5). Nothing
   currently publishes this. Without it, a rate is an overclaim by omission by the project's own
   standard.
3. **The three `No run has occurred` banners:** `measurement-spec.md:7`, `:1135`,
   `build-spec.md:359`. **Keep the design-target guard, delete the false sentence.**
4. **`targets/design-targets.yaml`, or strike the two lines that name it** (`measurement-spec.md:8`
   and `:1121`). A named quarantine that does not exist is a check that cannot fail, in the file
   that teaches the project not to have those. **This week, because the Results table is about to
   put targets and observations on the same page.**
5. **The seven `derived.*` seven-versus-eight sites** (B1): `architecture-spec.md:394`,
   `build-spec.md:335`, `data-spec.md:43`, `:438`, `:1617`, `lanes-spec.md:108`,
   `measurement-spec.md:1437`. Leave the three dated ones alone.
6. **`CONVENTIONS.md:1376`, the SEP-BY split** (B3). The spine carries the exact wording
   `measurement-spec.md:575` diagnosed as the defect.
7. **`crucible/conductor/campaign.py:64-71`** (A7). It prints a false warning on every run banner.
   Keep the *"no test covers them"* half.
8. **Add `E_NO_EVENTS` and the hash-lock question to `docs/NEEDS-ERIC.md`,** and refresh its
   two-day-stale header (A5, A6).
9. **Ruling 46 cleanup, at minimum the seven live sites** in c.1.
10. **Model Armor floor settings.** Day 8 item 3. No proof in the tree. It is cut-list item 3 and
    the cut list itself calls it *"cheapest to re-add, it is a gcloud command, not code."* Either
    run it and paste the output, or take the cut in writing.
11. **The written cut-line pass**, d.0 D6.
12. **Held-out unseal, 08-28**, then the transfer number with its k=1 and SEP-BY labels.
13. **Record the video, 08-29.** Nine hours in the plan with no slack behind it.

**Outside this repo, and flagged because it feeds every external sentence.** Four canon statements
are now false: *"nothing has ever been promoted"*, *"`GcsBlobIO` has never executed"*, *"the
policies bucket is empty"*, and *"the test suite is RED on `main`"* (pytest exits **0** and
contract-check exits **0** across six passes at `0ee05ee`, asserted this pass). A fifth,
*"`benign_passes_requiring_approval` is NOT BUILT"*, is also false: it has a producer since
2026-08-24 (`crucible/conductor/bundle.py:996-1009`, `real_warden.py:279`) and measured **4**.
`CLAUDE.md:49` also still says *"26-pair worksheet"* against 27 (B4). Q item
`c-20260824-2006-7060` covers the first four.

### d.3 What is NOW IMPOSSIBLE, or close enough that pretending otherwise is the risk.

1. **The third-party target, day 9 item 2.** `adapters/` does not exist. It needs someone else's
   codebase to cooperate, on the same day as the unseal and the code freeze, with the video the
   day after. **It is cut-list item 1 and the recovery is already written** at
   `execution-spec.md:522`: ship the `customer-service` invariant declarations as a specification
   you did not have time to run, keep the adapter interface in the README, and say plainly it is
   untested. *"Designed for, not yet demonstrated"* costs a solo entrant less than they think.
   **Take this cut in writing today, at the cut line, not on Friday.**
2. **k=3 anywhere.** `execution-spec.md:441` permits restoring it *"only if schedule recovers."* It
   has not. k=1 stands and the label travels with every figure.
3. **Re-authoring the 8 broken instances behind `E_NO_EVENTS` and re-running the batch.** Possible
   on paper and not in three days. A corpus change moves `corpus_hash`, needs a coordinator ruling
   with a written invalidation statement, and needs a D5 Part B re-freeze fired from the SEAL
   worktree because the script refuses anywhere else. **It would also void all 60 runs**, which is
   the entire evidence base for every figure. The realistic move is to **disclose the conflation
   and bound the rate**, which is what the brief already recommends.
4. **Gemma corpus generation.** Withdrawn by ADR-0018. Not late, not pending, gone. It is not
   available as a bonus-point recovery either.
5. **A transfer number before 08-28.** F4 is sealed and a hardening run does not touch it. Any
   transfer figure depends on the unseal happening on the day it is scheduled, so **there is no
   slack behind it at all.** *(Improved during this audit:
   `docs/proof/f4-unseal-preregistration-2026-08-25.md` now fixes what will be reported before the
   reportable thing exists, including the contingency for a bad result. The schedule risk is
   unchanged; the honesty risk is now covered.)*

### d.4 The cut line, section 5 of the brief. CONFIRMED INTACT.

`docs/CONVENTIONS.md:2538-2565` still carries both run-invalidating cuts as struck, with G8 named
as the reason for each: **#5** collapsing Tripwire, Warden and Gate into one process with one
service account, and **#6** moving the policy store from GCS into Firestore.
`docs/data-spec.md:1548-1560` carries the same two, struck in place with strikethrough and the
line *"If either of these is proposed at 1am on a Thursday, the answer is no, and the reason is
G8."* The three promoted never-cuts (all 9 known-bad fixtures, the sealed family at 18 or more,
the worker agent being genuinely money-touching) are present.

**No document in the spec set proposes either struck cut.** I checked by mechanism as well as by
phrase: `grep` for *"collapse"*, *"one service account"* and *"policy store ... Firestore"* over
all ten documents returns only the strike records themselves plus
`docs/measurement-spec.md:935, 1391` and `docs/build-spec.md:319, 345`, all four of which restate
the prohibition rather than propose the cut. **Nothing to report here except that it held.**

---

## What I could NOT verify, and what would settle it

1. **Whether the `E_NO_EVENTS` split is 8 attacks or 7.** I measured **8 distinct instance ids**
   carrying `invalid_verdict` across the 60 bundles, plus 2 more carrying `target_fault`.
   `docs/NIGHT-LOG-2026-08-25.md:143` says *"just 7 attacks"* over the first 20 runs.
   **Both can be true** if an eighth appeared after run 20. **Settled by:** recomputing over the
   first 20 bundles alone and stating the window with the number.
2. **Whether `corpus/sealed/` holds 24 VALID instances.** I counted 24 files in the
   `C:\dev\crucible-wt-SEAL` worktree and read none of them, deliberately. **Settled by:**
   `scripts/seal-commitment.py --verify` fired from that worktree, which is the instrument
   `docs/CONVENTIONS.md:145` names for exactly this.
3. **Whether the policies bucket actually holds 95 objects.** I verified the gate's own findings
   record G7 and G8 evaluated against live GCP and that the gate ran as
   `real_gate.RealGate (LIVE) ... gs://crucible-policies-x7 via GcsBlobIO`. **I did not query
   GCS**, because that is a live cloud call and outside this task. **Settled by:**
   `gsutil ls gs://crucible-policies-x7/runs/ | wc -l`. Given this project's six recorded
   instances of a reported status being false, **assert the bucket before any sentence says the
   bucket is not empty.**
4. **The exact pytest count.** Exit code **0**, asserted twice, and no `F` in the progress output.
   The summary count line is suppressed by this repo's pytest configuration, so I can report
   **green**, not **N passed**. `docs/NEEDS-ERIC.md:27` records 1812 collected on 2026-08-23.
   **Settled by:** `python -m pytest --collect-only -q | tail -1`.
5. **Whether Model Armor floor settings were ever enabled.** No proof file, no script, no infra
   entry. Absence of a proof file is not proof of absence. **Settled by:**
   `gcloud model-armor floorsettings describe`, which `execution-spec.md:449` already names.
6. **Whether the `README.md` Results table now carries an `Observed` column.** Out of scope by
   instruction, another lane owns it. **Settled by:** that lane's report.
7. **Whether `CLAUDE.md`'s session-state block is the right home for the 1,616 figure at all.**
   It is machine-written under the three-zone rule, so correcting it by hand may be the wrong
   move. **Settled by:** re-running the block's generator after `docs/results.md` exists.
