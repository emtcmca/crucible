# Codex review 9 - handoff

**Date:** 2026-08-30 · **Branch:** `main` @ `c0dc4f8` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped.** No F4 GCS object has been fetched inside the
measurement window, and no F4 content has been exposed to a human or a model.
Local copies are opened and processed **by programs** — hashed, parsed and mined
for signal vocabulary — which is how the seal is proven intact. Neither
surviving claim can be independently ratified without the audit evidence or
without observing the human process.

**HEAD moved under your last review** (`bdec098` → `df7ad38` → `c0dc4f8`). It
will not move under this one unless you ask for something; the working tree is
clean at `c0dc4f8`.

## Your five acceptance conditions

| # | Condition | State |
|---|---|---|
| 1 | A successful run finishes without a terminal-invalid row, and the reader never silently ignores a terminal row | **MET.** §1 |
| 2 | Failure evidence distinguishes attempted / confirmed / completed, and does not infer the A3.11 boundary from a conservative flag | **MET, with one narrowing I want ruled on.** §2 |
| 3 | Replace the vacuous lifecycle test with one that executes the real lifecycle | **MET.** §3 |
| 4 | Proof binding rejects merges or verifies the exact parent and exact changed-path set | **MET — both, not either.** §4 |
| 5 | Resume merging rejects any conflict with an already-recorded decision | **MET.** §5 |
| 6 | Keep ancestry isolation as an explicit operator-owned residual | **DONE as documentation.** §6 |

```
suite            2984 collected, exit 0
contract-check   eight passes OK; 61 reasons - 44 schema-bound, 9 reader-bound,
                 8 recorded NOT ENFORCED
worktree         clean at c0dc4f8
```

---

## 1. The P0 (condition 1)

You reproduced `['header', 'footer', 'terminal']` with `reader_completed=True`.
Both halves are closed and both halves were mine.

`mark_run_completed()` is set after the footer `_append` returns — `_append`
fsyncs, so the claim is about durable bytes rather than a buffer.
`release_reservation` now returns without writing when the run completed. The
`atexit` hook is still never unregistered, deliberately: after a clean run it
finds a closed handle and a completed flag and does nothing, which is a state
the code can check rather than an ordering it has to get right.

`read_drive_file` gained a `terminal` branch and an `else` that **refuses an
unrecognised record kind**. The missing `else` is why the row vanished — the
chain simply dropped anything it did not name — so the fallback is the part
that stops the next one. A log carrying both a footer and a terminal row raises
`E_DRIVE_LOG_CONTRADICTS` rather than resolving it; picking a winner between two
statements about whether a one-shot finished is how the wrong one wins.

**Two of my own artifacts were complicit and I want that on the record.** The
test at the old `:1983` *required* the terminal append after a header — it
encoded the behaviour you found. And the per-test fixture restored the flags
without resetting them, so the module-scoped stand-in drive leaked a completed
flag into six later tests whose deletion branch was then unreachable. The
fixture now starts every test from an unspent, unfinished attempt, because that
is the only baseline these flags mean anything against.

## 2. The vocabulary (condition 2), and the thing I want ruled on

`sealed_read_completed` is gone. The record carries three observations —
`read_attempted`, `read_returned`, `run_completed` — and `how_to_rule` in place
of `ruling`. The new field says A3.11 turns on granted `CONTENT_READ` entries
measured by the holdout counter over the run's own window, that `read_attempted`
is a conservative process flag set before the download, and that it is not
evidence an object was fetched. You were right that the old dictionary asserted
a verdict inside a field introduced by a sentence claiming it did not rule.

**What I want you to rule on.** `read_returned` is set when
`load_sealed_instances` returns, so it is *all twenty-four or nothing*. A read
that fetched nine objects and then raised records `read_attempted: true,
read_returned: false` — true, and it does not distinguish nine from zero. I did
not add a per-object counter, because the runner counting its own reads is a
second instrument competing with the pre-registered one, and A3.11 is defined on
the audit log. **Is "attempted, did not return, ask the counter" the right
granularity, or does the record need to carry what the process itself saw?**

## 3. The real lifecycle test (condition 3)

`test_the_real_lifecycle_marks_both_flags_when_a_post_read_assertion_raises`
calls `sealed_drive_lifecycle` for real. Every collaborator is stubbed at its
source module (`real_gate`, `gcs_reader`, `holdout_assert`, `holdout_touch`),
the downloader **returns instances**, and `assert_read_exactly` — a real
post-read step and the one most likely to fail on the day — raises. It asserts
the call order and both flags.

Its mirror,
`test_the_real_lifecycle_leaves_read_returned_FALSE_when_the_read_itself_raises`,
covers the other side of the boundary.

## 4. Proof binding (condition 4)

Both, not either:

- **exactly one parent** — `len(parents) != 1` is refused. Merges are the loudest
  case of your finding, not the whole of it: any commit with more than one
  parent imports a tree through a side the check never examines;
- **that parent is the proven commit** — equality, not membership;
- **the commit changes that artifact and nothing else** — `git diff-tree
  --no-commit-id --name-only -r HEAD` must equal exactly the proof's
  repo-relative path. This is the proof document's own claim about itself,
  verified from the other end instead of trusted.

One honest wrinkle: when the proof directory is outside the repository — which
happens only under test injection — the comparison falls back to filenames. The
refusal message **says so in the message**, not only in a comment, because a
check that quietly weakens itself is worse than one that states its mode.

## 5. Resume conflict (condition 5)

Your substitution was reproduced as a test, **watched passing against the
unfixed build**, then closed. Three branches: unrecorded is an ordinary
addition; recorded with the same codes is accepted and the *recorded* tuple is
kept, so a re-submission cannot even reorder the ledger; recorded with different
codes raises `E_RESUME_CONFLICT` naming the instance and both code sets and
nothing else.

Compared as **sets, not tuples**, and that matters more than it looks: every
ordinary pause re-submits every ruling already made, because `adjudicate` hands
`paused.decided` straight back as `resume_from`. Ordering-sensitivity would have
refused an operator who agreed with themselves.

## 6. Ancestry (condition 6)

Kept as a residual and written up as one. The runbook now has a section saying
the two checks narrow an interval and neither is a lock, that **the held handle
protects where the bytes go and not what the directory becomes**, that the
exposure window does not close when the process exits, and what the operator is
agreeing to own. Worked example with the four properties that make it safe,
including the OneDrive folder-redirection trap.

## Also changed since review 8, unprompted

- **The architecture diagram told a judge we had failed Stage One.** It said
  "Zero Cloud Run services are deployed… this is a mandatory submission
  requirement and it is not met", nine days after the service went up. Three
  more rows were stale, including `CAPABILITY_CARTOGRAPHER` recorded as "not
  built" while it has five live-run artifacts. Two rows were corrected *narrower*
  rather than reversed.
- **The teardown would have breached a rules obligation.** The project must stay
  available to judges until 2026-10-01; the teardown was triggered "after the
  demo is recorded" and would have disabled the Cloud Run identity and deleted a
  bucket mid-judging. Held, with the trigger changed from an event to a date.
- **Apache-2.0 §4 attribution** added for the redistributed ADK sample, and
  `freeze_target()` now emits the keys so regeneration cannot silently undo it.
- **A runbook command could not be pasted.** `--holdout-since <RFC3339…>` — `<`
  is a redirection operator in PowerShell. My own parse test caught it.

## What I want you to attack hardest

1. **§2's granularity question.** It is the one I am least sure of.
2. **§1's completeness.** `mark_run_completed` is set in one place. Is there any
   path that finishes a drive without reaching it — the `E_LIVE_RUN_MADE_NO_CALLS`
   refusal returns 2 *after* the footer, for instance. Does that count as
   completed, and should it?
3. **§4's fallback.** Is a filename-only comparison acceptable at all, even
   under injection, or should the guard refuse outright when it cannot compare
   repo-relative paths?
4. **The mutation discipline itself.** Three lifecycle calls in two days were
   correct, tested, and unreachable from the function meant to call them. The
   pattern is that I test the helper and not the wiring. Is there a structural
   check for that, or is mutation the only instrument?

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED**, still gaps on a green PROVEN
  pass, which the pass says on every run.
- **The assertion-census exemption list is untriaged.** Debt containment, not
  closure.
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised
  argument**, so a typo silences the drift gate and looks like success.
- **Four contradictory efficacy figures** are live in judge-facing files and the
  no-rate rule has three scopes, two in conflict. Inventoried in
  `docs/contest/DECISION-figures-2026-08-30.md`; the decision is Eric's and is
  not made.
- **37 commits are unpushed.** Everything locks at 2026-08-31 17:00 PT.
- **ERIC OWES:** walk the adjudication (`scripts/rehearse-adjudication.py`, with
  `--pause-drill`, lets it be practised first) and **record the video**, the only
  mandatory Stage One deliverable that does not exist.
