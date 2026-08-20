# L3 — ENFORCEMENT · lane log

One line per failed iteration. `CONVENTIONS.md` §6: lane logs are
`docs/lanes/L<N>-log.md`, and they record the iterations that did **not** work —
a log of successes is a changelog, and the repo already has one of those in
`git log`.

Format: `YYYY-MM-DD · <work item> · iteration N · what failed · what it cost`.

---

## Work items

Status verified 2026-08-20 by running the suite, not by recall.

| # | Item | Status |
|---|---|---|
| WI-1 | Negative checks — **ten**, not eight: the eight the brief mandates plus N5 and N6, which `policy.ebnf` names and brief §7 requires. RED at `6db2d5f` (19 failed, 60 passed), green at `0d27d99` | done · 2 iterations |
| WI-2 | DSL lexer + parser against `contracts/policy.ebnf` | done · 1 iteration |
| WI-3 | Validator V1–V9 + N3/N5/N6 | done · 1 iteration |
| WI-4 | Policy engine — membership match, tri-state predicates, verb precedence | done · 1 iteration |
| WI-5 | `episode.*` freeze + `derived.*` stamper | done · 1 iteration |
| WI-6 | `CRUCIBLE_PLUGIN` enforcement point + ledger + ADK adapter | done · 1 iteration |
| WI-7 | ADK plugin compiler + `include_plugins` attach assertion | done · 1 iteration |

No work item reached the iteration cap of 5. WI-1 is the only one that took
more than one, and both of its extra iterations were defects in the CHECKS
rather than in the code under test — which is the outcome §8 rule 2 is
predicting when it says the negative check comes first.

---

## Iterations

*(A line lands here only when an iteration FAILED. `CONVENTIONS.md` §8 rule 9 —
log the drop. Iteration cap is 5 per work item, then stop and report.)*

- 2026-08-20 · WI-1 · iteration 1 · **INTENTIONAL RED.** All ten negative checks
  plus the strawman meta-check run against `NotImplementedError` stubs.
  `19 failed, 60 passed`. This is the red half of §8 rule 2 and it is recorded
  here rather than only in a transcript, because a test that was never red is
  not evidence and the only durable proof of the red is a dated line and a
  commit.

- 2026-08-20 · WI-1 · iteration 2 · **The placeholder guard fired on correct
  prose.** `test_no_strawman_claim_is_still_a_placeholder` matched `"PENDING"`
  case-insensitively and flagged the reason string for the
  `sum_excludes_pending` strawman, which legitimately contains *"a pending
  20000"*. Cost: nothing, because it was caught on the first run — but a guard
  that flags correct text is a guard somebody deletes, and then it guards
  nothing. Replaced with an explicit `<<UNOBSERVED>>` sentinel.

- 2026-08-20 · WI-1 · iteration 2 · **A strawman claim was written from
  expectation and was wrong — the same defect `tests/strawman_canon.py` records
  against itself.** The claim was that a schema-only validator fails N3 because
  it cannot see `match_mode`, the field ruling 22 DELETED. Observed: it
  refuses, but with
  `'crucible-armorer@…' does not match '^crucible-gate@'`, because that is
  simply the first violation the schema walker reaches. It never looks at
  `match_mode` at all. **The C4 KNOWN_BAD golden is bad in six ways, so a
  refusal on it proves only that something was wrong.** Fixed by isolating the
  variable: N3's primary assertion now uses the VALID document plus exactly one
  added `match_mode`, the KNOWN_BAD case pins the requirement that the
  deleted-field scan runs BEFORE schema validation, and the half a JSON Schema
  structurally cannot reach — a `match_mode` in the free-form `provenance`
  object — gets its own test.

---

## Reported to the coordinator — contract gaps, not lane decisions

A lane does not edit `contracts/`. Each of these was implemented one way, the
choice is named at the code site, and a ruling that goes the other way is a
one-line change.

1. **`origin` and `rule_id`.** `canonicalization.md` §1 says
   `rule_id = hash(canonical(rule_without_rule_id))`, which read literally
   includes `origin` — and `origin` carries the round number. Then the same
   paragraph says `add_rule` of an existing rule is **detectably a no-op**, "the
   per-rule half of the convergence detector." Both cannot hold: a rule
   re-proposed in round 4 would hash differently from the identical rule in
   round 2 and read as new forever. Implemented with `origin` OUTSIDE the id
   (`crucible/dsl/serialize.py`, convention 1). `policy_hash` still covers it.

2. **`deny` has no `reason_code` and C2 requires one.** `policy.ebnf`'s
   `action = "deny" | …` carries no argument; `decision.schema.json` requires
   `reason_code` on every DENY. The C4 golden's own `require_approval` rule has
   no `action` block either, so it carries none. The engine mints three fixed
   enum symbols — `POLICY_DENY`, `CONSTRAINT_VIOLATED`, `APPROVAL_REQUIRED` —
   named in `crucible/policy/decision.py`. They are constants, so the
   no-free-strings bar holds.

3. **Two hashed arrays have no construction-time sort.** Restriction 6 names
   `rules`, `capability_classes` and `arg_conditions` and stops. `predicates`
   and `tool_names` also sit inside the hashed rule body, so unsorted, the same
   rule hashes two ways depending on the order the ARMORER happened to write its
   clauses — and the ARMORER is a model, so that order is not stable. Sorted on
   a stated key (`serialize.py`, convention 3).

4. **The stored form's empty-array convention is unstated.** A present empty
   array and an absent key are different canonical bytes and therefore different
   ids. Followed `C4-policy_document.valid.json` exactly: `tool_names` and
   `arg_conditions` always present, `predicates` only when non-empty
   (`serialize.py`, convention 2).

5. **Clause form 6 has two possible homes in the stored schema.**
   `arg_path cmp_op episode.<field>` could serialize as an `arg_conditions`
   entry with `value_type: "episode_field"` **or** as a `predicates` entry with
   `form: "arg_vs_episode_context"`. Both exist in
   `policy_document.schema.json`. Two encodings for one clause is two ids for
   one rule. Implemented as `predicates`, following that field's own `$comment`,
   which names it as one of "THE THREE EPISODE-SCOPED FORMS". **`value_type:
   "episode_field"` now appears to be dead.**

6. **The golden C4 document's `rule_id`s are illustrative, not computed.**
   `r_5f2a91cc0b74` is not the content hash of its own body, so
   `validate_policy_document` deliberately does NOT verify ids against their
   bodies — doing so would reject the golden fixture. `id_of_stored_rule` exists
   for the caller that wants the check; nothing calls it in the validation path.

7. **`require_approval`'s `reason_code` has no declared enum.** V4 governs
   `enum_symbol`, and `reason_code` is a separate production in the grammar with
   no arg_path, so there is nothing for membership to resolve against. Part A
   declares `arg_enums["reason_code"]` — but those are the twelve refund reason
   codes, and `C2-decision.valid.json` uses `SEED_MONEY_FLOOR`, which is not
   among them. Two namespaces, one name. Approval reason codes are currently
   checked for shape (UPPER_SNAKE) and by V3, not for membership.
