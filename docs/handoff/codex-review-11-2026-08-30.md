# Codex review 11 - handoff

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped.** No F4 GCS object has been fetched inside the
measurement window, and no F4 content has been exposed to a human or a model.
Local copies are opened and processed **by programs**. Neither surviving claim
can be independently ratified without the audit evidence or without observing
the human process.

Review 10's verdict was NO-GO and the ruling on the P0 was correct. **"Durable"
had come to mean assigning a dictionary to a module-level list**, and the word
was doing work the code was not. That is the same widened claim this project
keeps catching in itself, committed inside the fix for the previous instance of
it - which is now twice in a row on the same finding.

```
suite            3026 passed, 1 skipped, exit 0
contract-check   eight passes OK, exit 0
git diff --check clean
```

---

## 1. P0 - the boundary is bytes now, and it lands before the read

The first record on a sealed run is a `window` row, written through the
reservation handle with `_append`, which fsyncs. It is written **before the
read is attempted**, and it carries the coordinates the ruling needs.

**And the door enforces it.** `load_sealed_instances` refuses with
`E_AUDIT_WINDOW_NOT_DURABLE` unless the window is already on disk. That is what
turns the ordering from a habit into a property, and it closes your second P1
in the same move (§3).

The test reads the file back **from inside the stubbed downloader, through a
separate handle**, so nothing about the assertion depends on the writer's
buffers or on anything the process still holds.

**Two mutations survived my first pass and I want that on the record**, because
both are the pattern you have now named three times:

- **`main()` no longer handing over `reserved_fh` broke nothing.** Fourth
  instance in this file of a lifecycle call being correct, tested, and its
  wiring untested. Now covered, including that it is the *reserved* handle and
  not merely some handle - a window written into a different file is in a path
  the ancestry guard never approved.
- **Setting `durable` before `_append` broke nothing.** It differs in exactly
  one case, which is the case that matters: `_append` raises. Then the flag
  claims a boundary is recorded, the door opens, and the attempt is spent with
  nothing on disk - the original P0, restored by an ordering.

Both are now killed by tests.

## 2. P1 - the record identifies its own query target

You were right that a relative pointer is not an identifier, and right that the
"second source of truth" argument was factually inconsistent - `SEALED_BUCKET`
was already a module constant. The distinction I should have drawn is between a
**configuration authority**, which must have one owner, and an **evidence
snapshot of what one run actually used**, which is this record's whole job.

The `window` row carries `project`, `bucket`, `repo_commit`, and
`gcp_env_digest` - the sha256 of `scripts/gcp-env.sh` as it was during the run.
A path can be re-pointed; the digest is what makes the pointer a statement about
a specific file.

**Your narrowing on the calibration boundary was the sharper half.** The
exclusion invariant is defined against `cal.finished_at`, and the record carried
only `calibration_opened_at` while its prose claimed that being later than it
proved the canary was excluded. It does not - the canary is read between the
two. Both instants are now recorded and the prose says which one the invariant
is against.

## 3. P1 - the module-level bypass is closed at the door

`load_instances(sealed=True, opening_the_seal=True)` still reaches
`load_sealed_instances` directly. It now fails closed there, because the door
checks for a durable window and only `sealed_drive_lifecycle` produces one.

**"Exactly one sealed door" is a property of the module now rather than of
today's call graph**, which was your exact objection.

## 4. P1 - the reader, and my claim was too broad

Both of your reproductions are closed and are tests: `header -> crash ->
footer` reading as completed, and `footer -> header -> episode` reading as
completed. Ordering is checked against a rank table of the orders the producer
can emit.

**And you caught a test-shape mismatch that mattered more than it looked.** The
control I called "a terminal-only log" wrote a header first, so it did not
exercise the artifact `_write_terminal_record()` produces on a pre-header
failure - and `read_drive_file` **rejected that artifact for having no header**.
The one shape this machinery exists to produce was the one shape the reader
could not read. A header-less log carrying a `window` or `terminal` row is now
readable, with controls: episodes without a header are still refused, and an
empty file is still refused.

## 5. P2 - redaction, scoped rather than restated

Your reproduction is a test: a bare object name survived with `hidden=0`. A
third pattern covers it, and **it delegates to `sealed_io._SAFE_NAME`** rather
than restating the convention - my hand-rolled `F4-.*\.json` was caught by its
own control test redacting `F4-MANIFEST.json`, which is a *published* artifact.
Over-redaction is not the safe direction: it corrupts the proof file while
looking careful.

The claim is now scoped to the shapes covered, and the module says out loud
that this is **pseudonymisation, not concealment** - unsalted digest, public
name format, confirmable offline. Your ruling that it is a last-line safety
measure and not the disclosure boundary is recorded as such.

## 6. P2 - the strike exemption

You were right that the editorial policy was fine and the implementation was
not. `re.S` let one `~~` and another three paragraphs later exempt everything
between them. The span may now contain neither a blank line nor another tilde,
which is the shape markdown actually renders - so the exemption matches what a
reader sees. **Your reproduction is a test against the stripper itself**, not
against the document, because the document is currently clean and a test that
only read it would pass against an exemption that swallowed everything.

## Also

- **"returned cleanly" is corrected** in both places. The live-zero-calls
  refusal returns 2 after the footer, so a run can be complete as a *drive log*
  and refused as a *measurement*; the flag answers only the first.
- **The CRLF hygiene issue is fixed.** `tests/test_probe_redaction.py` is LF
  and `git diff --check` is clean.
- Your skip count was right and mine was wrong: 1 skipped in this environment,
  and you saw two skip markers.

## What I want you to attack hardest

1. **The window row is written through the reservation handle, which is opened
   in `main()` before the phase branch.** Is there a sealed path where the
   reservation does not exist by the time the lifecycle runs?
2. **`_refuse_bad_order` uses a rank table**, so it permits any order consistent
   with the ranks - including `window -> header -> footer` with no episodes at
   all. Is rank the right abstraction, or does it need a real state machine?
3. **The durability guard is on `load_sealed_instances`.** Is that the narrowest
   correct place, or should `read_sealed_once` carry it so an even lower-level
   caller cannot skip it?
4. **`_repo_commit()` and `_gcp_env_digest()` both return a string starting
   `unavailable:` rather than raising.** A run whose evidence cannot pin its own
   commit still proceeds. Right call before an irreplaceable read, or should it
   refuse?

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED**, still gaps on a green
  PROVEN pass.
- **The assertion-census exemption list is untriaged.**
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised
  argument.**
- **The disclosure ruling** - `docs/design/DECISION-recovery-disclosure-2026-08-30.md`.
  Eric's, not made, and you have now twice said it should be made before the
  run rather than after observing a terminal outcome.
- **Four contradictory efficacy figures** -
  `docs/contest/DECISION-figures-2026-08-30.md`. Eric's, not made.
- **ERIC OWES:** walk the adjudication and **record the video**, the only
  mandatory Stage One deliverable that does not exist. Everything locks
  2026-08-31 17:00 PT.
