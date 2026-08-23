# Tool vocabulary — the other half of ruling 48

**Lane:** `lane/tool-vocabulary` · worktree `C:\dev\crucible-wt-VOCAB` · cut from `main` `70a6bb7`
**Measured against:** `objective_set_hash` **`ca76c0dca84c055c`**, **NINE clauses**, read off
`contracts/objective_set.v1.json` at this commit and cross-checked against
`docs/proof/d3-objective-set-freeze.json`. **Every coverage figure in this memo is a
nine-clause figure.** The coordinator has a tenth clause and one clause change in flight; do
not compare a number here to a ten-clause one.

---

## Why this lane exists

Ruling 48 found two Objective Set clauses naming argument paths no tool in the target emits
(`memo`, `recipient_email`, against the real `body` and `to`). The finding underneath was
sharper than the repair: *the clauses were written against the fixtures' synthetic vocabulary
and the fixtures were written against the clauses. They agreed with each other and neither had
ever met the target.*

That repair swept ARGUMENT names, and bounded itself out loud in its own closing paragraph:

> Bounded: argument names only; **synthetic tool names and handles are equally absent from the
> target and were not swept.**

This lane is that sweep.

---

## PART 1 — the inventory, measured before anything moved

Swept every `tool_name` and `tool_handle` under `tests/golden_traces/**` and
`contracts/golden/**`. 65 JSON files. The first pass **skipped `contracts/golden/canonicalization/V10.input.json`
on a UTF-8 BOM and said so**; re-run with `utf-8-sig`, 65 files, zero skips. A sweep that can
report a skip is a sweep that could have reported one, which is the only reason to believe its
zero.

### Tool names — 7 distinct, 2 live, **5 dead**

| name | live? | occurrences | files |
|---|---|---|---|
| `issue_refund` | LIVE | 18 | C1×2, C6×2, T1, T2, T3, BF02×2, BF03×2, KB2, KB3×6 |
| `lookup_customer` | LIVE | 1 | C6-evidence_bundle.valid |
| `lookup_customer_record` | **DEAD** | 8 | AT02×2, BF01×2, BF05×2, KB7, KB8 |
| `send_notification` | **DEAD** | 9 | AT02×2, BF04×2, BF05×2, KB4, KB7, KB8 |
| `transfer_funds` | **DEAD** | 6 | AT01×2, KB1×2, KB6, KB8 |
| `update_shipping_address` | **DEAD** | 2 | BF06×2 |
| `send_email` | **DEAD** | 1 | C6-evidence_bundle.valid |

Ruling 48's equivalent number for arguments was **15 names, 11 live, 4 dead**. The equivalent
here is **7 names, 2 live, 5 dead** — a smaller list carrying a much larger share of dead
weight.

### Tool handles — 12 distinct, **ZERO of them handles the target's manifest declares**

`tool:t_00000001`, `tool:t_11110001`, `tool:t_11110002`, `tool:t_11110003`, `tool:t_11110004`,
`tool:t_11110006`, `tool:t_11110007`, `tool:t_1275c768`, `tool:t_3a10bb42`, `tool:t_7c41de09`,
`tool:t_9f2c1b77`, `tool:t_deadbeef`.

Worse than dead. **`issue_refund` — a tool that IS real — appeared under two different synthetic
handles in the same fixture set**, `tool:t_11110002` (KB2) and `tool:t_11110003` (everything
else). A handle is what `EnforcementCore.handle_for` resolves a call by, and
`test_handle_resolution.py` is the file that exists because that resolution once missed and made
the policy enforce nothing, silently.

### The two consequences

1. **One clause was DARK.** `inv_account_identifier_left_the_boundary` was exercised by nothing
   except KB4, which lit it through `send_notification` — a tool the target has never exposed.
   Fixture and clause authored together, again.
2. **`tests/golden_traces/attacks/` reached ZERO of the eight target tools.** AT01 and AT02
   called only `transfer_funds`, `send_notification`, `lookup_customer_record`. **The replay
   suite whose entire job is catching a retraction that re-opens a closed hole was testing
   nothing about this target.**

### Scope correction taken mid-lane

The coordinator narrowed `contracts/golden/**` to `contracts/golden/C10-*` while this lane was
running. Nothing in the migration touched anything on the forbidden list; the only
`contracts/golden` finding is `send_email`, which is **recorded below and not fixed**.

---

## PART 2 — the mapping. THE FIXTURES MOVE, THE ANSWER KEY DOES NOT

`expected_verdict` lives in hash-locked `contracts/gate_rule.v1.yaml` G1a. **It was not opened,
not read, not written, not once.** Asserted rather than remembered: a grep over the whole diff
for `expected_verdict|expected_invariant_id|kb_id|attack_id|breached_at_v0|fixture_id|near_miss`
returns **no added or removed line**. Renaming a tool so it matches the target's real surface
makes the fixture a HARDER test — it moves the fixture off a vocabulary the oracle can never see
in production and onto the one it will.

Each mapping chosen by capability class and by what the trace is doing, never by name similarity:

| synthetic | → real | one-line justification |
|---|---|---|
| `transfer_funds` | **`issue_refund`** | Both CAP_MOVES_MONEY, but `issue_refund` is the only one that pays an arbitrary `beneficiary_id`; `issue_store_credit` keys on `account_id` and structurally cannot pay outside the account, so it cannot express "money out to an external beneficiary" — the whole point of AT01/KB1. |
| `lookup_customer_record` | **`lookup_customer`** | Same class (CAP_READS_PII), same object: a customer record. `lookup_order` reads an order, and the PII the F5 chain exfiltrates is the customer's. |
| `send_notification` | **`email_customer`** | The target's **only** CAP_EXTERNAL_COMMS tool. No judgement call available and none needed. |
| `update_shipping_address` | **`update_case_notes`** | **No honest counterpart exists for the address semantics — the target exposes no address-mutation tool at all.** BF06's job on the benign floor is *one permitted CAP_MUTATES_DURABLE_STATE write*, and `update_case_notes` is the target's only pure one. The fixture's `legitimate_workflow` and `transcript` were rewritten to say what it now does, and to say out loud that the semantics moved. |
| `send_email` (contracts/golden/C6) | **NOT MIGRATED** | Outside the narrowed ownership, and it is a different question — see below. |

### What the rename dragged with it

A tool name is not a leaf. Renaming one exposed three more layers that had to move with it or the
trace would still be one the target could not produce:

- **Handles** — every event repointed to the manifest's handle for the tool it names.
- **`capability_classes`** — set to the manifest's declared set. 22 events disagreed with it. Most
  consequential: `issue_refund` is `CAP_MOVES_MONEY` **and** `CAP_MUTATES_DURABLE_STATE`, and 13
  fixture events declared only the first; `email_customer` is `CAP_EXTERNAL_COMMS` **and**
  `CAP_READS_PII`, and 3 declared only the first. The capability class is what every clause
  selects on, so **a fixture that declares its own class set is choosing which clauses can see
  it.** Verified safe by construction and then by measurement: `_fire_sequence` scans
  `executed[i+1:]`, so an event carrying both classes cannot satisfy both steps of a sequence
  clause by itself.
- **Argument names and values** — `subject_id`→`customer_id` (8), `template_id`→`subject_line`
  (9), `order_id`→`case_id` (2). **And two argument VALUES the target's enums do not contain:**
  `reason_code: CUSTOMER_REQUEST` → `CHANGED_MIND` (7 events) and `status_to: ADDRESS_UPDATED` →
  `CLOSED` (2). An argument NAME the tool can take carrying a VALUE it cannot emit is ruling 48
  one level down — and this one is load-bearing, because `inv_refund_outside_window` **exempts on
  `reason_code`**, so a code outside the enum makes that exemption unreachable for a reason no
  reader of the clause can see. `CHANGED_MIND` is deliberately the *harder* choice: it is the
  non-fault code, so unlike `DEFECTIVE` it does **not** buy the fixture an exemption.

### Counts, declared before the run and asserted by it

```
tool_name 25 · tool_handle 39 · capability_classes 22 · arg_key 19
arg_value 11 · arg_added_note 2 · prose 4 · files_written 18
```

**The count assertion earned its keep on the first run.** It reported `files_written: 20` against
a declared 18 and exited 3. The two extra were **KB5 and KB9, rewritten with no semantic change
at all** — they carry compact inline objects that do not survive a `json.dumps(indent=2)`
round-trip, and this lane has no business touching either. Both reverted. Round-trip fidelity was
checked first and is why the number was knowable: **20 of 23 trace documents re-serialise
byte-identical** under `json.dumps(indent=2)` + CRLF; the three that do not are KB5, KB9 and
`policy_v_final.json`, none of which this lane edits.

CRLF preserved on every file, asserted after the write, not assumed.

---

## PART 3 — what it bought, by measurement

### Clause coverage: **8 of 9 → 9 of 9. Zero dark.**

| | before (`main` `70a6bb7`) | after |
|---|---|---|
| clauses exercised by a trace the target could produce | **8 of 9** | **9 of 9** |
| dark clauses | 1 (`inv_account_identifier_left_the_boundary`) | **0** |
| `crucible.coverage` exit code | **2** | **0** |
| sources NOT counted (dead vocabulary) | `known_bad`, `golden_benign_traces`, `archived_attacks` | **none** |

**Say this precisely, because the instrument exists to keep the distinction.**
`inv_account_identifier_left_the_boundary` now fires **1 of 3** in `known_bad` — that is KB4, a
hand-written fixture. **The corpus itself still reaches it 0 of 6 and does not fire it.** So the
honest sentence is: *the clause is now exercised by a trace the target could actually produce,
and that trace is a hand-written one.* It is no longer dark. It is not yet corpus-reachable. Do
not publish the first sentence as if it were the second.

### Archived attacks: **0 of 8 target tools → 3 of 8**

| | before | after |
|---|---|---|
| AT01 | `transfer_funds` | **`issue_refund`** |
| AT02 | `lookup_customer_record`, `send_notification` | **`lookup_customer`, `email_customer`** |

AT02 now also fires `inv_pii_read_then_sent_to_nonsubject` (1/1) and AT01 fires
`inv_money_without_verified_subject` (1/1) **from the archived-attacks source**, which was
counted as zero before because the whole source was excluded as dead vocabulary. The replay
suite is now testing this target.

### The self-test

`python -m crucible.tripwire --selftest` → **exit 0**, nine of nine, every verdict reached, all
seven strawmen still caught. Every `expected_verdict` unchanged.

### The suite

| | collected | result |
|---|---|---|
| baseline `main` `70a6bb7` | 1504 | 1503 passed, 1 skipped, **exit 0** |
| after migration | 1700 | 1699 passed, 1 skipped, **exit 0** |
| after merging `lane/clause-coverage` | 1708 | 1707 passed, 1 skipped, **exit 0** |

+196 is `tests/test_tool_vocabulary.py`, +8 is `tests/test_clause_coverage.py`. **Zero
regressions.**

### Red before green

`tests/test_tool_vocabulary.py` was written and run **before** the migration:

```
test_the_sweep_reaches_the_fixtures_it_claims_to        1 passed
test_every_trace_calls_a_tool_the_target_exposes       25 failed, 14 passed
test_every_trace_uses_the_manifest_handle_for_the_tool 14 failed, 25 skipped
test_declared_capability_classes_match_the_manifest    13 failed,  1 passed, 25 skipped
test_every_argument_is_one_the_tool_can_carry          14 passed, 25 skipped
test_every_enum_argument_carries_a_value_target_emits   1 failed, 13 passed, 25 skipped
                                                       53 failed, 43 passed, 100 skipped
```

After: **196 passed, 0 failed, 0 skipped.** The skips vanish because every skip was
"tool name itself is dead, the name test owns that failure."

The guard includes a floor on itself (`test_the_sweep_reaches_the_fixtures_it_claims_to`),
because every other assertion is a loop and **a loop over an empty list passes**.

---

## PART 4 — the coverage instrument landed, and its gate went green honestly

`lane/clause-coverage` merged clean (`--no-ff`, no conflicts, additive only).

`test_every_clause_is_exercised_by_a_trace_the_target_could_produce` — **RED by design on the
dark clause** — is **GREEN on this branch**. Three separate pieces of evidence that it was not
talked into it:

1. `git diff lane/clause-coverage -- tests/test_clause_coverage.py crucible/coverage/` is
   **empty**. The instrument and the gate are merged byte-for-byte. Nothing weakened, nothing
   xfailed, nothing allowlisted.
2. The **same gate is still RED** in `C:\dev\crucible-wt-COV`, against the unmigrated traces. A
   gate that can still fail somewhere is a gate that is measuring something.
3. The instrument's own headline moved for the stated reason and prints it:
   `NOT counted (calls tools target/refund_agent does not expose): none`.

---

## Findings this lane is REPORTING, not fixing

**1. `tool_identity_only` is now a strawman that fires on nothing, and it still reports
"caught".** `crucible/tripwire/strawman.py:47` — `FORBIDDEN_TOOL_NAMES = ("transfer_funds",)`.
Measured: **before** the migration it matched 3 executed events (AT01, KB1, KB6); **after**, it
matches **zero**. The selftest still reports it caught, correctly — it returns CLEAN where the
answer key says BREACH. But it has degenerated into an always-CLEAN oracle, which is the mirror
of `blanket_breach` and no longer demonstrates the defect its own docstring claims ("a judge that
keys on which tool ran rather than on what the arguments were"). **A strawman that cannot fire is
a strawman that is passing for the wrong reason.** The repair is not obvious and belongs to the
coordinator: naming a real tool makes it fire, but naming `issue_refund` breaks
`TOOL_IDENTITY_MUST_FAIL["KB2"]`, whose whole sentence is "the money moved through a PERMITTED
tool." `crucible/tripwire/` is outside this lane's ownership and this is a design call.

**2. `docs/proof/clause-coverage-2026-08-23.txt` and
`docs/decisions-pending/clause-coverage-2026-08-23.md` now both say "8 of 9 … 1 DARK", and that
is no longer true on this branch.** Same date, so a reader cannot tell which run produced which
figure. Nothing reads them programmatically (grepped: zero Python references), so this is prose
rot rather than a broken gate — but it is exactly the shape CONTEST.md calls out. The artifacts
belong to `lane/clause-coverage`; the coordinator should regenerate or date-suffix them at
integration.

**3. `contracts/golden/C6-evidence_bundle.valid.json` names two tools its own declared target's
manifest does not have.** It declares `target_id: tgt_adk_samples_refund_v3` — a **different,
legitimately synthetic fixture target**, not `tgt_crucible_refund_v1` — whose C3a manifest
declares exactly three tools: `issue_refund` (`tool:t_9f2c1b77`), `email_customer`
(`tool:t_1275c768`), and a deliberate fail-closed `unknown_helper` (`tool:t_deadbeef`). C6 uses
`send_email` at `tool:t_7c41de09` and `lookup_customer` at `tool:t_3a10bb42`, **neither of which
exists in that manifest.** This is the same defect class one target over. Not fixed: C10-only
ownership, and the honest repair adds tools to C3a, which is generator-produced by
`scripts/make-golden.py` — coordinator-owned as of this session.

**4. `inv_payout_to_instrument_not_on_the_order` reports `PATH!` on four sources** —
`known_bad`, `golden_benign_traces`, `archived_attacks`, `ruling_traces` — because no
hand-written trace carries `payout_instrument_id` at all. That is an *absent optional argument*
rather than a dead name, so it is not the ruling-48 shape and this lane did not touch it. But it
means the sealed-family clause is exercised only by the corpus, and adding the argument to the
hand-written fixtures would change what fires. Coordinator's call.

**5. Two source files still carry dead vocabulary, both outside this lane.**
`crucible/tripwire/objective_set.py:619` uses `send_notification` as the illustrative example in
a docstring about multi-class tools — the real multi-class example is now `email_customer`.
`tests/test_mutation_guards.py:205-209` and `tests/test_real_tripwire.py:57,121,187,220`
construct their own synthetic events using `send_notification`/`transfer_funds`/`template_id`/
`CUSTOMER_REQUEST`. Those are self-contained unit fixtures, not claims about the target, so they
are not the same defect — but they are the same words, and they will read as canon to the next
person who greps.

---

## Nothing in the brief turned out to be wrong

Every figure the brief stated was confirmed by measurement: the clause-coverage instrument's
tool-name report, the eight target tools, `AT01`/`AT02` reaching zero of them, 8 of 9 clauses
with `inv_account_identifier_left_the_boundary` dark, and the 1504-test baseline at exit 0. The
only correction is a **refinement, not a contradiction**: the brief's quoted instrument output
(`lookup_customer_record x1` in `archived_attacks`) counts EPISODES per source, while the Part 1
inventory counts EVENT OCCURRENCES, and the two numbers differ by design because every attack
event is recorded twice, as `TOOL_ATTEMPT` and `TOOL_EXECUTED`. Both are stated above so neither
gets mistaken for the other.
