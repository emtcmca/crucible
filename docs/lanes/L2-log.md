# L2 — lane log

**Lane:** L2 TARGET + CORPUS · **Branch:** `lane/L2-target-corpus` ·
**Worktree:** `C:\dev\crucible-wt-L2`

**Authorized scope on this run: (a) only.** The refund agent, its seven
bare-function tools, the written refund policy, capability manifest **Part A**,
three demo conversations. Scope (b) — the 48 training attacks, the sealed family,
the 24 benign fixtures, the 9 known-bads — is **not started** and nothing below
touches it. **This lane does not perform the D3 freeze.** It prepares the freeze so
that running it is one command; the project owner runs it.

One line per **failed** iteration. A green run is not an entry; a red one is.
`CONVENTIONS.md` §8 rule 2 — a check that cannot fail is not measuring anything —
is the reason this file has content at all. Entries are appended as they happen,
never written ahead of the run that produced them.

---

## Work item 1 — the three scope-(a) negative checks

| # | Check | Proves absent |
|---|---|---|
| N1 | `tests/test_target_episode_freeze.py` | that an in-episode turn can move `episode.account_holder_email` |
| N2 | `tests/test_manifest_completeness.py` | that a tool the agent exposes but the manifest omits defaults silently to an empty capability set |
| N3 | `tests/test_manifest_unclassified.py` | that `UNCLASSIFIED` and the empty set share an encoding |

**2026-08-20 · N1/N2/N3 iteration 1 — RED, and committed red.** All three modules
were collected and all three failed at import:

```
tests\test_manifest_completeness.py:34: in <module>
    from target.refund_agent import tools
E   ModuleNotFoundError: No module named 'target'
ERROR tests/test_target_episode_freeze.py
ERROR tests/test_manifest_completeness.py
ERROR tests/test_manifest_unclassified.py
3 errors in 0.61s
```

A collection error is the weakest possible red — it proves the module is absent,
not that the behaviour is. Two of the three therefore carry a permanent strawman
(`tests/strawman_target.py`) so the check keeps its ability to fail after the
implementation lands. N1 does not: its four vectors each assert a specific refusal
raising a specific exception type, and a permissive implementation fails them
directly rather than agreeing with itself.
