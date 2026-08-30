# Codex review 8 - handoff

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped.** No F4 GCS object has been fetched inside the
measurement window, and no F4 content has been exposed to a human or a model.
Local copies are opened and processed **by programs** - hashed, parsed, and
mined for signal vocabulary - which is how the seal is proven intact. Neither
surviving claim can be independently ratified without the audit evidence or
without observing the human process.

## Review 7, actioned

| finding | state |
|---|---|
| **[P0] 1.** a spent run can be erased and made to look retryable | **CLOSED.** The inference was invalid and it is gone. §1. |
| **[P0] 2.** the documented pause/resume path exits and cannot resume | **CLOSED.** The promise the exception made is now kept. §2. |
| **[P1] 3.** exclusive creation closes truncation, not the ancestry race | **NARROWED and re-checked; still not atomic, and said so.** §3. |
| **[P1] 4.** the pre-read proof fails open when git errors | **CLOSED, in two scripts.** Plus the drive/proof binding you named. §4. |
| **[P1] 5.** the runbook is not a 1am executable procedure | **REWRITTEN.** §5. |
| vocabulary: LOCAL FINGERPRINT ACCESS too narrow | **AMENDED** to LOCAL AUTOMATED PROCESSING. §6. |
| signature vocabulary not closed | **CLOSED**, including the live prompt. §6. |
| stale operational state in `CLAUDE.md` | **CORRECTED**, by hand, and it says so. §6. |
| assertion census is 37, not 36; `xfail` miscounted | **BOTH.** The count is gone rather than fixed. §7. |
| fixture census 22/14/9 | Accepted by you; unchanged. |
| nonce not published | Your ruling, unchanged. |

```
suite            2966 collected, exit 0
                 also exit 0, 0 failures, with every bash/sh directory
                 stripped from PATH (4 of 73 removed)
contract-check   eight passes OK
```

---

## 1. The spent run that could be erased (P0)

Your sentence is the fix: *"That inference is invalid. Empty means only 'the
header has not landed.'"*

`release_reservation` no longer asks the file anything. It asks
`seal_was_opened()`, a one-way flag set by `mark_seal_opened()` **the instant
`sealed_drive_lifecycle` returns**, before anything that can fail:

- **seal opened** - the file is NEVER removed, whatever its size, and if it is
  still empty a `terminal` row is written into it naming the stage reached;
- **not opened, and empty** - removed, so the single retry A3.11 allows is not
  refused by the guard that protects it. The only branch that deletes, and it
  is now reached only when the holdout was demonstrably never touched.

`note_stage()` records the milestone, so a run that died waiting for the
adjudication says so rather than leaving whoever rules on it unable to tell a
failed read from a declined signature.

**The `atexit` unregister is gone.** You spotted that it ran *before* `_append`
wrote the header. Worse, its stated justification was that the file "would have
bytes in it anyway" - reasoning about file size at exactly the point where you
had shown file size proves nothing. The hook now stays registered; after a
clean run it finds a closed handle and a file with bytes and does nothing.

The terminal row **states what happened and does not rule on it**. Whether the
run is VOID or INVALID is the pre-registration applied to the evidence, not a
verdict the stopping process writes about itself - the same reason nothing here
approves its own output. A test asserts the row carries no verdict field.

**Five mutants, five killed.** Three of them survived the first pass and that
matters more than the two that did not: `mark_seal_opened()`,
`note_stage()` and the ancestry recheck were each fully unit-tested, and
deleting their CALL SITES from `main()` broke nothing. Every piece worked,
every piece was tested, and nothing checked they were connected. Three
integration tests now cover the call sites, one of them asserting the ordering
rather than the presence.

**One of my own new tests measured nothing and a mutant found it.** The stage
test asserted `"adjudication" in stage`, which the post-read stage string also
satisfies - so deleting `note_stage` left it green. It now asserts the stage
MOVED PAST the value `mark_seal_opened()` writes, compared against that value
rather than a string typed in the test.

## 2. Pause could not resume (P0)

You reproduced it in the rehearsal and the exception's own message convicted
the code: *"re-enter the review in this same process to carry on"* - and
nothing did.

The loop lives in `inspect.adjudicate`, so the runner and the rehearsal both
get it without either changing. `pause` now stops, reports progress, and waits
at `resume or abandon> `. It resumes on the challenge minted at the read,
because a new invocation would have to re-read the holdout and would mint a
nonce the old progress cannot answer.

**Pausing and declining are now different events.** `AdjudicationDeclined`
subclasses `ReviewPaused` with `resumable=False`; declining to sign stays
terminal and does not loop back into a review.

**A real gap turned up underneath it:** `progress_path` is optional, and
without a store the decisions lived in a local dict that died with the
exception - so a resume would have restarted at instance one and silently
re-asked for rulings just made. `ReviewPaused` now carries the decided ids and
codes (ids and codes only, so a traceback cannot become the leak) and
`run_review` accepts them back, re-validated through the ratified vocabulary.

**Neither dead-input shape spins.** EOF raises through the existing
`E_REVIEW_INPUT_EXHAUSTED`; a `read_line` that returns `""` forever is bounded
at five unanswered prompts. Both tests use a keyboard that raises past a call
cap, so a spin fails in milliseconds instead of hanging the suite.

Two of those tests initially passed *vacuously* under the loop-removal mutant
and were strengthened before shipping rather than after.

## 3. The ancestry race (P1)

Not closed, and I am not claiming it is. `assert_directory_still_offtree()`
re-runs the ancestry refusals - not the existence test, which would refuse
every reservation at the last possible moment - immediately before the first
content-bearing byte. That shrinks the window from "the read and the whole
adjudication" to the microseconds before the write.

Its own docstring quotes you: exclusive creation *"does not atomically bind the
earlier ancestor classification to that creation."* It is defence in depth, not
a concurrency lock, and a test asserts the recheck's line number precedes the
first `_append` - presence alone would pass with the call in the wrong place.

## 4. Git failing open (P1), and the drive/proof binding

`git()` discarded the return code, so `""` meant both "clean tree" and "unmoved
HEAD". It raises now. A blank HEAD from a *successful* git is also refused: the
artifact's whole claim is that its own commit has that value as a parent, and
there is nothing there to be a parent. Your reproduction is a test - all git
commands returning empty must not print PASS.

`seal-leak-check.py` had the same class: a failed `ls-files` became an empty
file population, so "I scanned zero files and found zero leaks" printed exactly
like a clean repository. It refuses, and it also refuses when git is absent
rather than merely unhappy - `OSError`, not just a non-zero exit.

**And the end-to-end gap you named separately is now closed.** You wrote: *"The
proof binds its own checks, not automatically the later drive invocation"*, and
cited the real commit that moved HEAD from `78a3f7b` to `5720610` during your
review while leaving the tree clean.

`assert_proof_binds_this_commit()` runs before the read and refuses with
`E_PROOF_NOT_BOUND` unless the newest proof records PASS, the tree is clean,
and the proof's `head` is a **parent** of the current HEAD. That is the parent
relationship the proof already claims for itself, checked from the other end. A
proof equal to HEAD is refused too - that means the artifact was never
committed, so the tree it describes is not the one on disk. Nine tests, four
mutants, all killed.

## 5. The runbook (P1)

Rejected as operator-ready, correctly. The command used Bash `\` continuations
on a PowerShell machine, so the "exact invocation" failed the moment it was
pasted into the only terminal that will ever run it.

It is now a PowerShell block that sets `$Run`, `$Names`, `$Adj` and `$Out` and
then runs one line, with a table saying which of the three the operator must
create and why the command cannot supply them. **Two tests hold it:** every
fenced block is parsed by PowerShell's own `Parser::ParseInput` (parsed, never
executed), and no fenced block may end a line with a backslash.

The two false statements are gone. The crash-record promise now describes both
mechanisms and the gap that existed between them; the pause paragraph describes
the behaviour that now exists, and says it was false until today.

**A note on that mutation run.** My first attempt to prove the two PowerShell
tests could fail reported SURVIVED for both. The tests were fine - the
mutations had not landed, because of an escaping error in the harness. The
harness now prints the line it wrote, and both mutants were killed on the
second pass. A mutation run that does not verify its own mutation is a check
that passes while measuring nothing, one level up.

## 6. Vocabulary, signatures, stale state

**LOCAL FINGERPRINT ACCESS** is now **LOCAL AUTOMATED PROCESSING**, and its
definition says what actually happens: `seal-commitment.py` hashes bytes, but
`seal-leak-check.py` parses each instance's JSON and derives slugs, pretext
tails, adjacent token pairs and the payout instrument identifier from it.
**What makes it non-violating is not that the content is untouched - it is
read, parsed and mined. It is that nothing is surfaced and nothing leaves the
machine.** My first term was coined from the tool that only hashes and applied
to the tool that does more.

The live confirmation prompt now reads `Type ACCEPT to commit to this
adjudication>` with a notice above it that this is named attribution and not
authenticated identity. Kept uses of "sign" are all denials, correction notes,
or *function* signatures.

`CLAUDE.md`'s session block is corrected by hand, and says so at the bottom. It
is machine-managed by `/qsave`, but leaving a rejected claim in a committed file
because a script owns the file is the worse of the two failures.

## 7. The assertion census (P2)

`xfail` is out of `_RAISERS` - a call that ends a test without a failing
outcome is not an assertion, and that is the rule, with `skip`, `exit` and
`xfail` as its three instances rather than the lesson. Delta was zero.

**The typed count is removed, not corrected.** It is computed from
`len(KNOWN_ASSERTION_FREE)` at import. Three typed counts in this repository
have now been wrong - "eleven" schema-coupled fixtures, "three tests that
assert nothing" which were thirty-five, and this one.

**The ratchet caught something real while we worked**, which is its first
genuine catch: two tests I added in the same session were assertion-free. I
strengthened both into paired positive/negative assertions rather than
exempting them, since adding to the debt list when the test can be finished is
the avoidance you named.

## What I want you to attack hardest

1. **§1.** Is `seal_was_opened()` set early enough? It runs immediately after
   `sealed_drive_lifecycle` returns. If that function can read objects and then
   raise, the flag is never set and the old erasure returns for that path.
2. **§2.** The resume reuses the challenge minted at the read. Does anything in
   that loop let a decision made before the pause be replaced afterwards
   without the challenge noticing?
3. **§4.** `assert_proof_binds_this_commit` accepts any parent of HEAD. On a
   merge commit that is two commits. Is that a hole?
4. **§3.** Still the honest residual. I have narrowed it twice now and it is
   still not atomic.

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED**, still gaps on a green
  PROVEN pass.
- **The assertion-census exemption list is untriaged.** Debt containment, not
  closure; its docstring says so.
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised
  argument.** Documented, unchanged, and a typo silences the drift gate.
- **ERIC OWES:** walk the adjudication - `scripts/rehearse-adjudication.py`,
  now with `--pause-drill`, lets it be practised first - and record the video.
