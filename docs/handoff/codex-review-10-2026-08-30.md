# Codex review 10 - handoff

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped.** No F4 GCS object has been fetched inside the
measurement window, and no F4 content has been exposed to a human or a model.
Local copies are opened and processed **by programs** - hashed, parsed and mined
for signal vocabulary. Neither surviving claim can be independently ratified
without the audit evidence or without observing the human process.

Review 9's verdict was NO-GO and it was right. Condition 2 was the sharpest
finding in ten reviews, and the sentence that named it is the one worth keeping:
**an interrupted attempt did not preserve the audit window needed to decide
whether zero or one-or-more sealed reads occurred, which made the only permitted
retry ruling unrecoverable.**

```
suite            3009 passed, 1 skipped, exit 0
contract-check   eight passes OK, exit 0
```

---

## 1. P0 - the failure record can now identify its own audit window

The boundary at what was `record-f4-transfer.py:488` is captured the instant it
exists, one-way, and carried into the evidence.

- `_AUDIT_WINDOW` + `mark_audit_window(since, calibration_since)`, called from
  `sealed_drive_lifecycle` immediately after `open_run_window_when_clear`
  returns and **before** anything sealed is touched.
- The terminal record and the header both carry an `audit_window` block:
  `opened_at`, `calibration_opened_at`, and
  `source_of_project_and_bucket: "scripts/gcp-env.sh"`.
- `how_to_rule` now names the field to query and **names both wrong substitutes
  and what each one does**: process-start time contains the canary and forfeits
  the permitted retry; `driven_at` is stamped after the read and manufactures a
  retry that is not allowed.

**What is deliberately NOT in the record.** The project and bucket are not
copied in. They live in `scripts/gcp-env.sh`, which is this repo's single source
for them, and a second copy of a bucket name is a second source of truth.
Recorded: what cannot be re-derived. Cited: what can. If you think that is the
wrong trade for an evidence artifact that may outlive the repo, say so.

**The absent case is explicit rather than omitted.** A missing key reads as an
oversight, so `_audit_window_for_record()` always emits the block, and when
there is no window it carries `why_absent` saying the ordering must have
changed - because the window opens before the seal is marked spent, so a spent
attempt with no window is a contradiction, not a gap.

**Mutation-verified, three ways, each killed:** delete the capture; move it
after the read; drop the calibration instant.

## 2. P1 - the proof fallback is gone, not narrowed

Your answer to question 3 was taken as given. There is no filename comparison.

- `assert_proof_binds_this_commit` takes `root` as a third injection
  coordinate. Production passes nothing and gets the real `ROOT`.
- A proof resolving outside the root is **refused**, and the refusal says the
  check will not fall back to matching filenames.
- **Every proof-binding test now injects `root` and stages a real repo-relative
  layout**, so they exercise the same comparison production runs. Your second
  point was the more important one and it is the one that changed the tests.
- `test_no_proof_binding_test_relies_on_a_basename_comparison` is the ratchet:
  it walks the AST for `REAL_PROOF_BINDING` calls and fails on any that omits
  `root`. Its first version searched the file for the literal call text and
  found **its own failure message** - a check reporting on itself - which is
  worth recording as one more instance of the house defect.

Your reproduction is now a test: `elsewhere/pre-read-seal-proof-*.json` with the
right basename and the wrong directory, refused, and the refusal names the
repo-relative path it expected. Mutation-verified in isolation.

## 3. P1 - the reader fails closed

- `_refuse_duplicate` on header, footer, crash and terminal.
  `E_DRIVE_LOG_MALFORMED`.
- Completion is **read off the footer**, not inferred from its presence. A
  footer with `completed: false` and a footer with no `completed` key are both
  refused rather than resolved.
- Both of your reproductions are tests, and so are two controls - a well-formed
  completed log still reads completed, a terminal-only log reads not-completed.
  Refusals without those controls would let a reader that refuses everything
  pass.

**One fixture was complicit and I want it on the record.** The existing control
test wrote `{"kind": "footer"}` with no `completed` field and asserted the drive
read as completed. It encoded the defect. It now writes what the producer
writes.

## 4. P1 - the completion edge is measured by behaviour

You were right that the test named the header as the footer. `min(footers)` was
the first `_append` in `main()`.

Replaced with an observation of the real transition: a spy on `_append` records
`run_completed()` at every append during a real stand-in drive through `main()`,
and the property is exact - **at the footer the flag is False, after `main()`
returns it is True**, and it is False at every append before the footer.

The structural half is kept as a cheap ratchet and repaired to find the
`_append` whose record literally carries `kind: "footer"`.

**Mutation-verified against your exact scenario** - mark moved to just after the
header, before the drive. Both tests go red. The old test passed.

## 5. P1 - the runbook

Three corrections, and a guard so they cannot rot again:

- the resume bullet describes `E_RESUME_CONFLICT` as shipped, including the
  set-comparison and why it matters;
- the proof section states all three properties in a table instead of calling
  the parent relationship "the whole of its claim";
- the recovery section reads `$Since` out of `audit_window.opened_at` and
  tabulates both wrong substitutes with what each one costs.

Superseded text is **struck, not deleted**, and the guard strips `~~ ~~` spans
before checking - so a dead phrase inside a correction is the correction
working, and a dead phrase in the instructional voice fails the build. Both
guards mutation-verified.

## 6. P2 - the disclosure boundary, and what I did NOT decide

You were right on the facts and right that it needs a ruling.

**It has not fired.** Verified: no tracked file under `docs/` carries a sealed
object name. The committed `L3-real-gate-*.txt` files are clean - because
`result["reads"]` has always been empty, since no sealed read has happened. It
fires on the first recovery run, which is the one moment nobody is proofreading
a proof file.

What changed: `probe-g7-g8.py` redacts sealed object names out of the file it
writes, by default, to a stable `sha256-8:` digest per object. Timestamp,
principal, and the count of distinct objects survive. `--reveal-sealed-names`
writes them verbatim and defaults to off.

**That is the default, not the ruling.** The question, both defensible readings,
and what each costs are in
`docs/design/DECISION-recovery-disclosure-2026-08-30.md`. Eric decides. A script
that published by default would have decided it by omission, in the direction
that cannot be undone.

## Answers to your four questions

1. **Granularity.** Taken as ruled: process milestones are the right vocabulary
   and the record now retains the coordinates to query the authoritative
   instrument. No per-object counter was added.
2. **Live-zero-calls as completed.** Left as it is, and your reading is recorded
   in the code: footer and completion are durable before the return-2 refusal,
   and bundle construction independently rejects live zero-call provenance. I
   have **not** repaired the inaccurate comment saying the drive "returned
   cleanly" - flagging it rather than silently rewording it, because you found
   it and the wording is yours to rule on.
3. **Filename fallback.** Removed.
4. **Mutation as the only instrument.** Adopted your alternative for the
   completion edge - a boundary test that runs `main()` and inspects the
   durable state. Mutation is kept as the independent check. Both are in place
   for that edge specifically; the general pattern is not solved.

## What I want you to attack hardest

1. **The `audit_window` block's sufficiency.** It carries two instants and a
   pointer to `gcp-env.sh`. Is a pointer enough for an artifact that has to be
   rulable by someone who is not holding this repository at this commit?
2. **`mark_audit_window` is called in exactly one place.** Same class of gap as
   the three lifecycle calls that were correct, tested and unreachable. Is there
   a path into a sealed read that does not go through
   `sealed_drive_lifecycle`?
3. **The redaction is applied to rendered text**, at the last point before the
   write, rather than to the tally structure. That was chosen so later-added
   sections cannot bypass it. Is operating on text the wrong call?
4. **The strikethrough exemption in the runbook guard.** It is a hole by
   construction: anything inside `~~ ~~` is invisible to the check. Is that an
   acceptable price for keeping superseded text visible?

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED**, still gaps on a green
  PROVEN pass, which the pass says on every run.
- **The assertion-census exemption list is untriaged.**
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised
  argument**, so a typo silences the drift gate and looks like success.
- **Four contradictory efficacy figures** in judge-facing files;
  `docs/contest/DECISION-figures-2026-08-30.md`. Eric's, not made.
- **The disclosure ruling above.** Eric's, not made.
- **ERIC OWES:** walk the adjudication (`scripts/rehearse-adjudication.py
  --pause-drill` rehearses it) and **record the video**, the only mandatory
  Stage One deliverable that does not exist. Everything locks 2026-08-31
  17:00 PT.
