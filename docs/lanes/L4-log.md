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
