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

## Work item 2 — the agent, its seven tools, and the ledger seam

**2026-08-20 · freeze iteration 1 — RED, and this one was a real defect.**
`freeze.py` hashed `refund_policy.md`'s raw bytes. Verified the same day: this
repository runs `core.autocrlf=true` and `.gitattributes` covers `contracts/**` and
the canonicalization vectors but **not** `target/**` —
`git check-attr text eol -- target/refund_agent/refund_policy.md` returns
`unspecified` for both. So this working copy holds LF and a fresh clone on Windows
receives CRLF, and the raw-bytes hash differs:

```
working copy LF   : ae3cb4c93f86ad8a
as CRLF checkout  : 2060b712f63a6e6c
normalized        : ae3cb4c93f86ad8a
```

That breaks the scope-(a) exit criterion — *the freeze hash recomputes identically
from a clean checkout* — and it breaks it in the worst direction: the freeze looks
correct on the machine that produced it and fails for the judge who clones it.
Fixed by normalizing CRLF to LF before hashing, which is the convention this repo
already set for `contracts/**`. **A BOM is refused rather than stripped**, matching
canonicalization restriction 1. Not fixed by editing `.gitattributes` — that is
shared configuration outside this lane's owned paths, and a lane editing it changes
something five other lanes depend on. Reported to the coordinator, who may want the
attribute anyway.

**2026-08-20 · manifest writer iteration 1 — same defect, second door.**
`pathlib.write_text` applies the platform's newline translation, so
`capability_manifest.json` landed with **141 CRLF endings** while every hand-written
file in the repo holds LF — counted from the bytes, not assumed. It did not move
any hash, because the freeze hashes the manifest OBJECT rather than the file. It
would still have produced a whole-file diff the first time anyone regenerated it on
Linux, and it is the same class of defect as hashing the policy's raw bytes: an
artifact whose bytes depend on which machine last touched it. `newline="
"` added
to both writers. **Found only because a `git add` warning listed every new file
except that one** — the absence was the signal, which is a reminder that a clean
report can mean the check could not see the thing.

## Work item 3 — the demos, and a claim that was not true

**2026-08-20 · demo suite — GREEN ON FIRST RUN, which is a weak signal.**
`tests/test_target_demo.py` passed 18/18 the first time it ran. A suite nobody has
seen fail is a suite nobody has established *can* fail, so it was falsified by hand
before being trusted:

```
PROBE 1  postcondition 3400 -> 3401
         E  assert 3400 == 3401
         FAILED test_demo_replays_to_its_declared_postconditions[D1-cold-open]
PROBE 2  demo mails attacker@example.invalid instead of the order's email
         FAILED test_every_outbound_email_goes_to_the_order_email_of_record[D1-cold-open]
```

Both restored, both re-run green, file verified byte-intact afterwards.

**2026-08-20 · a false claim written and withdrawn the same hour.** The first
version of that file's docstring said the replay *"caught two argument-name errors
that a reader would not have."* It caught nothing — it passed on its first run.
The sentence was written from what the exercise is usually worth rather than from
what this run produced. Corrected to state the first-run pass and the hand
falsification. Recorded because a lane that quietly deletes its own overclaim
teaches nobody anything.

---

## Conflicts found and NOT worked around

Reported rather than resolved. `CONVENTIONS.md` §1: say the conflict out loud, do
not silently pick.

| Conflict | Higher document | Taken |
|---|---|---|
| `amount_cents` in `execution-spec.md`'s demo script (lines 524 and 526) vs. `amount_minor` | `CONVENTIONS.md` §6 — money is INT64 minor units plus an ISO-4217 `currency`, and no bare "amount" | `amount_minor` + `currency`. `execution-spec.md:546` already calls a bare "amount" a defect in an adjacent correction, so the two sites look like survivors of that pass |
| T1 unilateral authority: *"Above $500, or past 60 days, it must escalate"* (`execution-spec.md:242`) vs. the sourced ladder's **T1 ≤ $150 per order, ≤ $300 lifetime per customer account** | `CONVENTIONS.md` §5.4a rulings 4 and 5 adopt the researched ladder explicitly, including its two caps | the sourced ladder. Ruling 3 also says the retail specifics are sourced rather than invented, and $500/60d predates the research |

## Contract gap, reported not closed

**No contract covers the ledger interface.** `lanes-spec.md` sequences W1 on the
basis that *"L2(a) needs only the ledger interface, which is C-level, not
code-level"*, but C1–C9 carry no ledger contract. This lane declared the shape it
needs in `target/refund_agent/ledger_interface.py`, bound to that, and shipped a
labelled fake. **It did not invent a C-number**, because a lane authoring a
contract for another lane's component produces a second source of truth rather than
a contract.

## Observations, not stop conditions

- `capability_manifest.schema.json` sets `capability_classes` to `minItems: 1`, so
  the **empty set — which `CONVENTIONS.md` §2.2 defines as *inert*** — has no
  encoding in Part A. None of this target's seven tools is inert, so scope (a) is
  unaffected and no contract change is requested. It would bite the first time an
  unseen target exposes a pure read of non-personal data, which is D9's shape.
- `arg_enums` members must match `^[A-Z][A-Z0-9_]*$`, so the sourced escalation
  queue labels (`RETURNS-T2`, `RISK-REVIEW`, `IDENT-REVIEW`, `DUTY MANAGER`) cannot
  be enum symbols. The machine symbols are `RETURNS_T2`, `RISK_REVIEW`,
  `IDENT_REVIEW`, `DUTY_MANAGER`, and **both spellings appear together in
  `refund_policy.md`** so a reader cannot mistake one for a second queue set.
- `status_to` carries `OPEN, PENDING, APPROVED, REJECTED, CLOSED`. The middle three
  are model policy §11 verbatim — *"there is no fourth state and there is no
  timeout-to-approve"* — and refer to ESCALATION state. `OPEN` and `CLOSED` are the
  case record's own bookends and are **synthesis**, flagged here because they are
  the only values in Part A that are not sourced.
