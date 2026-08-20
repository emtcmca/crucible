# L4 — ORACLE · lane log

One line per failed iteration (`CONVENTIONS.md` §6). Lane-written; the brief at
`docs/lanes/L4-oracle.md` is coordinator-owned and is never edited from here.

**Scope:** the TRIPWIRE, the `OBJECTIVE_EVALUATOR`, the nine known-bad harness,
the replay-based `REGRESSION_WARDEN`, and `--selftest`.

**Model calls: zero.** Enforced by a build-time import lint over
`crucible/tripwire/` and `crucible/warden/`, proven by adding an offending import
and watching the build fail — not by instruction.

---

## Iterations

| # | Work item | What failed | Why it mattered |
|---|---|---|---|
| 1 | negative checks first | Whole suite RED at collection: `ModuleNotFoundError: No module named 'crucible.tripwire'` x5, pytest exit 2 | The five test files were written and run BEFORE any implementation existed. A test written after the code, that has never been red, is not evidence. |
| 2 | import lint | Planted `import google.genai` in `crucible/tripwire/import_lint.py`; 3 tests went red, including `test_the_real_packages_are_clean`. Removed, green again. | The claim "the TRIPWIRE contains no model" is only structural if something enforces it. The lint was watched failing on a real offence inside the real package, not only on a synthetic file in a temp directory - a correct denylist aimed at the wrong root passes forever. |
| 3 | tripwire core | All three hand-written trace fixtures returned INVALID: `E_EVENT_FAILS_C1: 'ep_0000000000t1' does not match '^ep_[0-9a-f]{12}$'`. | My own fixture was malformed and the C1 validity pass caught it before anything was scored. That is the check doing its job on its author. Episode IDs are now hex. |
| 4 | warden replay | Against an empty policy the replay suite reported ZERO successes where both archived attacks should breach. The attack fixtures still carried the unbound `BIND_AT_LOAD` sentinel, so every replayed episode came back INVALID. | A replay gate that under-reports reads exactly like evidence that a hole is closed. The sentinel binder now lives in one place and binds ONLY the sentinel, never a real stamp, so G1(b) survives. |
| 5 | warden replay | `AT02` breached under a policy that denies it. Both calls in the episode shared one `invocation_id`, so the DENIED send inherited the LOOKUP's permitted attempt. | The same shortcut in production would let a blocked call be scored as executed. Attempts and executions now pair on `(invocation_id, tool_handle)` and each call carries its own invocation id. |
| 6 | tripwire core | `test_non_monotonic_seq_is_INVALID` was inert: it ran on a SINGLE-EVENT episode, where "not in order" is not a state that exists. | A check that cannot fail, found only because the implementation made it go green for the wrong reason. It now runs on a two-event trace and asserts `len(events) >= 2` so it cannot go inert again. |
