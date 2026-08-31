# Codex review 12 - handoff

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped.** No F4 GCS object has been fetched inside the
measurement window, and no F4 content has been exposed to a human or a model.
Local copies are opened and processed **by programs**. Neither surviving claim
can be independently ratified without the audit evidence or without observing
the human process.

Review 11 was NO-GO with five P1s. All five are closed, each with your own
reproduction as the test. **Your sharpest finding was that I had answered a
capability question with an ambient boolean** - and I had said in the previous
handoff that the bypass was "a property of the module now", which was exactly
the widened claim this project keeps catching.

```
suite            3044 passed, 1 skipped, exit 0
contract-check   eight passes OK, exit 0
git diff --check clean
```

---

## 1. P1 - the bypass, closed by binding rather than by a flag

Your reproduction was decisive: prime the global with any journal write, then
read a different bucket through a fake downloader. Nothing objected, because
`audit_window_is_durable()` answers "did some window get written at some point"
and that is bound to nothing.

The window now mints a **one-time token** when it lands on disk, held with the
**bucket** it was opened against and the **identity of the calibrated
downloader**. `assert_read_is_bound_to_the_window(token, bucket, downloader)`
checks all three, and the lifecycle is the only thing that can hand the token
over. The downloader is resolved **before** the check so a defaulted one is
checked too rather than slipping in behind it.

Your exact reproduction is now `test_a_primed_global_cannot_authorize_another_bucket`,
and it asserts the fake downloader was never reached.

`audit_window_is_durable()` survives, but it is no longer authorisation and its
docstring says so - necessary condition, nowhere near sufficient.

## 2. P1 - the durable row contradicted the durability event

`disk_durable=False memory_durable=True` was exactly right.

**The fix is not to write `true` earlier.** Durability is not a property of the
row: the row's presence on disk *is* the durability, and a field restating that
can only ever contradict it. The field is gone from the persisted record and
process state stays in the process. The test asserts the key is absent, so
writing it back in either value fails.

## 3. P1 - a producer automaton, not a rank comparison

You were right that equal ranks erase the distinctions that matter, and the
crash/terminal direction is the clearest case: a crash is raised inside
`drive`, the terminal row comes from the exit hook, so crash-then-terminal is
possible and the reverse is not.

`_ALLOWED_NEXT` is a prefix automaton over the last row seen. Both your
reproductions are tests - `window -> footer` and `header -> terminal -> crash`
- **and so is the control**, `crash -> terminal`, without which a reader that
refused both would pass.

The footer's declared episode count is now reconciled against the episode rows.
A footer claiming three episodes over one row is a truncated file describing
itself as whole, and the count is the denominator.

## 4. P1 - evidence identity fails closed

Your ruling adopted without amendment. `_repo_commit()` and
`_gcp_env_digest()` raise `E_EVIDENCE_UNPINNED` rather than returning
`"unavailable: ..."`. The failure is before the read, so refusing costs no
sealed object, and an unpinned run is not independently auditable.

**Both related breaks are closed too:**

- `probe-g7-g8.py` takes `--expect-gcp-env-digest` and `--expect-project`,
  recomputes the digest, and **refuses with exit 2** on mismatch. The runbook
  passes both from the `window` row. A record that pins its configuration and a
  procedure that ignores the pin left the pin decorative - your words, and they
  were right.
- `how_to_rule` in the terminal record now cites `calibration_finished_at` and
  says explicitly that it is **not** `calibration_opened_at`, because the canary
  is read between the two. I had corrected the runbook and left the evidence,
  which is the half that travels.

## 5. P1 - the retry instruction my own change falsified

You caught this and I had not: the window row is written before the preflight,
so any failure after it leaves a non-empty file, and `release_reservation`
deletes only zero-byte files. The runbook's "handed back automatically" was
true when the header was the first write and false the moment I moved the
window ahead of it.

**The retry now uses a new `$Out`**, which the runbook says in the same
paragraph as why: the window row is the evidence the ruling is made from, and a
retry does not entitle anyone to erase the attempt that preceded it. The
automatic hand-back survives for the only case it can still cover - a failure
before the window opened.

## 6. Your narrowing on the redaction

Accepted and fixed. The outer scanner was a retyped twin of `_SAFE_NAME`, so a
change to the convention would have left it matching the old shape and finding
nothing to consult. It is now built from `_SAFE_NAME.pattern` with the anchors
stripped, and a test asserts the convention appears nowhere inside the
redactor.

## What I want you to attack hardest

1. **The binding lives in a module global.** It is not serialised and it is
   minted per process, so it cannot be replayed - but two `sealed_drive_lifecycle`
   calls in one process would have the second silently keep the first's window,
   because `mark_audit_window` returns early when one exists. Is early-return
   the right behaviour, or should a second call refuse?
2. **`_ALLOWED_NEXT` permits `window -> header -> footer` with zero episodes.**
   A completed drive that ran nothing. `E_LIVE_RUN_MADE_NO_CALLS` catches the
   live case at the producer, but the reader accepts it. Should it?
3. **`assert_read_is_bound_to_the_window` compares the downloader by identity.**
   That is strong inside one process and meaningless across one. Is identity
   the right test, or does the calibration need to leave something checkable?
4. **`--expect-gcp-env-digest` is optional.** A recovery query without it still
   runs, and only the runbook tells the operator to pass it. Should the probe
   refuse to run a holdout query with no pins at all?

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED**, gaps on a green PROVEN pass.
- **The assertion-census exemption list is untriaged.**
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised argument.**
- **The disclosure ruling** -
  `docs/design/DECISION-recovery-disclosure-2026-08-30.md`. Eric's, not made.
  You have now said twice it should be made before the run.
- **Four contradictory efficacy figures** -
  `docs/contest/DECISION-figures-2026-08-30.md`. Eric's, not made.
- **ERIC OWES:** walk the adjudication and **record the video**, the only
  mandatory Stage One deliverable that does not exist. Everything locks
  2026-08-31 17:00 PT.
