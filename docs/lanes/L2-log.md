# L2 — lane log

**Lane:** L2 TARGET + CORPUS · **Branch:** `lane/L2-target-corpus` ·
**Worktree:** `C:\dev\crucible-wt-L2`

**Run 1 scope: (a) only.** The refund agent, its seven bare-function tools, the
written refund policy, capability manifest **Part A**, three demo conversations.
**This lane does not perform the D3 freeze.** It prepares the freeze so that
running it is one command; the project owner runs it.

**Run 2 scope (2026-08-20): (b), VALIDATORS ONLY.** Everything AROUND the
fixtures — the label-blindness harness, the three authoring lints, the SEP-BY
split machinery, the instance schema, the sizing and class-coverage checks, and
the C3 Part B builder. **No corpus attack, benign fixture, or sealed instance
was authored, and none may be.** A benign fixture nobody read is an assumption
rather than a fixture, and the project owner reads all 24 personally. The
synthetic objects the checks are exercised against live in
`tests/corpus_synthetic.py`, are named `SYNTH-*`, and never enter `corpus/` or
`fixtures/`.

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

---

# RUN 2 — scope (b), validators only. 2026-08-20

## Work item 4 — the label-blindness harness, and the weakest possible red

**2026-08-20 · iteration 1 — RED, and honestly the weakest red available.** All
six new modules were collected and all six failed at import:

```
tests\test_sepby_split.py:31: in <module>
    from corpus.errors import CorpusError
E   ModuleNotFoundError: No module named 'corpus'
ERROR tests/test_blindness_harness.py
ERROR tests/test_corpus_lints.py
ERROR tests/test_corpus_schema.py
ERROR tests/test_corpus_sizing.py
ERROR tests/test_sepby_split.py
ERROR tests/test_corpus_part_b.py
6 errors in 0.26s
```

Same defect class as run 1's N1/N2/N3: **a collection error proves the module is
absent, not that the behaviour is.** So each of the five checks was hand
falsified after it went green, and the output is below. Two permanent strawmen
(`tests/strawman_corpus.py`) keep the suite's ability to fail after this session
ends, on the two checks where the wrong implementation is the *obvious* one.

**PROBE 1 — `BlindInstance` downgraded to the promise version** (`if key not in
VISIBLE` becomes `if False`), i.e. a "blind" view that is a dict with a docstring:

```
FAILED test_blind_view_raises_on_every_withheld_key[kind]
FAILED test_blind_view_raises_on_every_withheld_key[family]
FAILED test_blind_view_raises_on_every_withheld_key[sealed]
FAILED test_blind_view_raises_on_every_withheld_key[near_miss]
FAILED test_blind_view_raises_on_every_withheld_key[slug]
FAILED test_blind_view_raises_on_every_withheld_key[input_turns]
FAILED test_blind_view_raises_on_every_withheld_key[expected_verdict]
FAILED test_blind_view_raises_on_every_withheld_key[smuggled_arg_path]
FAILED test_a_computer_that_reaches_for_the_label_is_stopped_at_the_view
```

**PROBE 2 — the approver lint switched to `doc.get("approver")`**, which is what
the obvious implementation uses and which makes "declared none" and "the author
forgot" the same bytes:

```
FAILED tests/test_corpus_lints.py::test_an_absent_approver_is_an_error_not_a_default
```

**PROBE 3 — the sealed free-text lint switched from the manifest's declared
structured args to a hardcoded `{"memo", "note"}` denylist:**

```
FAILED test_every_free_text_arg_is_refused_not_just_the_two_obvious_ones[body]
FAILED test_every_free_text_arg_is_refused_not_just_the_two_obvious_ones[subject_line]
```

`body` and `subject_line` are the two largest free-text fields the target
actually exposes. The denylist reports CLEAN on both, and would keep reporting
clean as tools are added — its coverage shrinks while its output does not change.

**PROBE 5 — the Part B freeze gate removed** (the `result != "PASS"` branch made
unreachable):

```
FAILED tests/test_corpus_part_b.py::test_a_failing_report_refuses_to_produce_a_document
E   Failed: DID NOT RAISE <class 'corpus.errors.CorpusError'>
```

**PROBE 4 — the SEP-BY empty-set refusal, and this one did NOT fire on the first
attempt.** Removing the `if not pairs` guard left the suite green, because a
second guard (`pol == 0 and orc == 0`) catches the same input further down.
Removing both produced the red — with a *different code*:

```
        split([])
>       assert e.value.code == "E_NO_PAIRS"
E       AssertionError: assert 'E_ORACLE_PARITY' == 'E_NO_PAIRS'
```

Worth recording rather than tidying away. With both refusals gone, an empty pair
set falls through to the parity stop condition and the author is told to
**re-author a corpus that does not exist**. The check still refuses, so nothing
is unsafe — but the message would send someone to fix the wrong thing, and the
first probe attempt looked exactly like a check that could not fail. The
difference between "defence in depth" and "a redundant guard I can delete" is
only visible if you break both.

Full suite after restore: **485 passed**, `python -m pytest tests/`.

## Work item 5 — the check runner, and its refusal to report a pass

`python -m corpus` on the repository as it stands:

```
load                    NOT-RUN  on disk: {'training': 0, 'sealed': 0, 'benign': 0, 'known_bad': 0}
pairs resolve           NOT-RUN  corpus/pairs.json absent
fault reason_code lint  NOT-RUN  no pairs authored
sealed-set lints        NOT-RUN  no sealed instances on disk
sizing                  NOT-RUN  no instances on disk
class coverage          NOT-RUN  needs both attacks and benign fixtures
SEP-BY split            NOT-RUN  no pairs authored
label blindness         NOT-RUN  no instances on disk
Part B buildable        NOT-RUN  blindness check did not run
RESULT: NOT-RUN - the corpus is not authored yet. This is not a pass.
EXIT=2
```

Nine `NOT-RUN` rows and **exit 2, not 0**. A sweep that prints nine greens on an
empty repository is the object every negative check in this project exists to
prevent, and it is the shape `measurement-spec.md:813` names: an unevaluable
gate is a check that cannot fail.

---

## Conflicts found and NOT worked around — run 2

| Conflict | Higher document | Taken |
|---|---|---|
| The approver sentinel: `CONVENTIONS.md` ruling 23.4 says *"explicitly `null`"*; this lane's brief §4 and the kickoff prompt say the string `"NONE"` | **`contracts/canonicalization.md` §2**, which had already found and resolved this collision on 2026-08-20 | `"NONE"`. Canonicalization restriction 5 forbids `null` in a hashed payload and the corpus **is** hash-locked at D5, so `null` is not a preference that lost — it is **unrepresentable**. Asserted, not quoted: `tests/test_corpus_lints.py::test_the_declared_none_sentinel_canonicalizes` |

**The residual defect, reported not fixed: `CONVENTIONS.md` ruling 23.4 still
reads `null` and carries no correction note.** The resolution lives one rank
DOWN the precedence order, in `contracts/canonicalization.md` §2. A reader
applying §1 literally — CONVENTIONS wins, the downstream document is the defect —
gets the wrong answer and writes `null` into an artifact that cannot be hashed.
The spine is the file that exists *so there is exactly one place a fact lives*;
here it is the stale copy. Coordinator's to correct.

## Observations, not stop conditions — run 2

- **The `corpus/sealed/` pre-commit hook is NOT armed as of 2026-08-20.**
  `C:\dev\crucible\.git\hooks\` holds only the `.sample` files. L1 owes it
  before D5; recorded here because the loader's `sealed_present` flag is a
  report, not a control, and the `.gitignore` line is not one either.
- **Two implementations of the ten field definitions now exist**: the reference
  computers in `corpus/blindness.py`, which run over static instances at D5, and
  L3's plugin, which stamps them live in `before_tool`. Same shape ruling 33.3
  ruled on for L4's `reference_engine.py`. Labelled as reference, and **if the
  two ever disagree on an instance, that is a contract report, not a bug in
  whichever one you trust less.**
- **Ruling 13 condition 2 is half-enforceable.** The seal side — sealed
  instances span `CAP_MOVES_MONEY` and `CAP_MUTATES_DURABLE_STATE` only — is a
  lint. The train side — that the `arg cmp episode.<field>` shape is actually
  exercised on `CAP_EXTERNAL_COMMS` and `CAP_READS_PII` in training — is a
  property of what gets authored and of which rules the ARMORER emits, and no
  check in this lane can see it. §8 rule 9: logging the drop rather than letting
  a green run imply coverage it does not have.
- **A 1.0 in the blindness report is not automatically a label mirror.** On a
  small corpus a many-valued field can reach 1.0 by accident. The report carries
  `distinct_values` and the `separating_rule` beside the number so a human can
  tell which kind it is. The threshold was **not** softened to avoid that
  conversation — 1.0 fails, and the remedy is to remove the field and re-freeze,
  which is a pre-run repair and therefore ordinary.
- **No Part B document was written to disk.** The schema requires a real
  `result` and a real `max_predictive_accuracy`, and there is no corpus to run
  the check over. Writing it now means fabricating a verdict or a measurement.
  The builder exists and is tested; the file lands at D5 from a real run.
