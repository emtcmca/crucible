# L5 — LOOP · lane log

**Branch:** `lane/L5-loop` · **Worktree:** `C:\dev\crucible-wt-L5`
**Brief:** `docs/lanes/L5-loop.md` (coordinator-written; this lane does not edit it)
**Opened:** 2026-08-20

One line per failed iteration (`CONVENTIONS.md` §6). A green run that was green
on the first attempt is not interesting and is not recorded here.

---

## Work item 1 — the negative checks, RED before anything exists

`CONVENTIONS.md` §8 rule 2. Written and watched fail before a line of
implementation. The failing output is pasted into the commit that carries them.

| # | Check | What it catches |
|---|---|---|
| B1 | A `human_only` free-text field carrying a "recommended fix" string must not appear anywhere in the ARMORER's input — neither in the projected dict nor in the assembled prompt text | the CORONER writing the patch and the ARMORER transcribing it |
| B2 | The adapter must be structurally unable to address `human_only.*` **at all** | the lint-only defence, which a hypothesis phrased as a description passes |
| B3 | A free string riding in `offending_tool_calls[].args_redacted` must not reach the ARMORER | C5 leaves `args_redacted` an open object with no value-type restriction — B1's whitelist alone does not close it |
| G1 | The BUDGET_GOVERNOR aborts on a low ceiling and returns the abort as a **first-class result**, never as an exception | an abort that arrives as a traceback is not a round outcome and cannot be written to the ledger |

---

## Iterations

*(appended as they happen)*
