# L3 — ENFORCEMENT · lane log

One line per failed iteration. `CONVENTIONS.md` §6: lane logs are
`docs/lanes/L<N>-log.md`, and they record the iterations that did **not** work —
a log of successes is a changelog, and the repo already has one of those in
`git log`.

Format: `YYYY-MM-DD · <work item> · iteration N · what failed · what it cost`.

---

## Work items

| # | Item | Status |
|---|---|---|
| WI-1 | Negative checks, all eight, RED before implementation | see below |
| WI-2 | DSL lexer + parser against `contracts/policy.ebnf` | |
| WI-3 | Validator V1–V9 + N3/N5/N6 | |
| WI-4 | Policy engine — membership match, tri-state predicates, verb precedence | |
| WI-5 | `episode.*` freeze + `derived.*` stamper | |
| WI-6 | `CRUCIBLE_PLUGIN` enforcement point + ledger | |
| WI-7 | ADK plugin compiler + `include_plugins` attach assertion | |

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
  it cannot see `match_mode`. Observed: it refuses, but with
  `'crucible-armorer@…' does not match '^crucible-gate@'`, because that is
  simply the first violation the schema walker reaches. It never looks at
  `match_mode` at all. **The C4 KNOWN_BAD golden is bad in six ways, so a
  refusal on it proves only that something was wrong.** Fixed by isolating the
  variable: N3's primary assertion now uses the VALID document plus exactly one
  added `match_mode`, the KNOWN_BAD case pins the requirement that the
  deleted-field scan runs BEFORE schema validation, and the half a JSON Schema
  structurally cannot reach — a `match_mode` in the free-form `provenance`
  object — gets its own test.
