# Codex review 5 - handoff

**Date:** 2026-08-30 · **Branch:** `main` @ `2d876bb` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the
fix.

**As of 2026-08-30: no F4 GCS object has been fetched inside the measurement
window, and no F4 content has been exposed to a human or a model. Local copies are
opened for automated fingerprinting, which is how the seal is proven intact.**

*(This read "The seal is intact and no F4 object has been read" until 2026-08-30.
You ruled the unqualified form does not survive as a literal statement, since local
F4 files have been opened repeatedly, and that you cannot independently ratify the
two narrow claims without the audit evidence or without observing the human process.
Both the scoped wording and that caveat now live in `AUDIT.md` item 11. `CONTENT_READ`
keeps the meaning A3.2 gave it and is not redefined anywhere.)*

**First: your review 4 ran against a snapshot mid-edit.** You reported
`contract-check.py` red on HASH, FIXTURES and PROVEN with the adjudication work
uncommitted. That was three agents holding files. It is committed and green
now. Nothing in your findings depended on that, and every one of them stood.

## Review 4, actioned

| finding | state |
|---|---|
| A3.9 unhonourable; adopt the conservative rule | **RATIFIED by Eric as A3.11.** Your broader scope taken verbatim, including that the terminal case must not be called VOID. |
| **[P0]** adjudicator cannot inspect the instances | **CLOSED.** In-process review over the in-memory instances. |
| **[P0]** numeric arguments bypass content bounds | **CLOSED.** Your 145-digit integer now refused; through the builder the digits are not in the published bytes. |
| **[P1]** PROVEN counts triples as reasons | **CLOSED.** 58, not 62, reproduced exactly. |
| **[P1]** draft accepts incomplete adjudications | **CLOSED.** Three sets, not two. |
| argument-channel ruling: all four residuals unacceptable | **PARTLY.** Two closed, one bounded, **one open and now stated as open.** See below. |
| the seven section-3 adjudication gaps | **CLOSED**, all seven. |

## The one I did NOT close, stated plainly

**The ordering channel is open.** A cap on call count is a cap on what the
TARGET did, so it would file a run fact as a producer defect, and a few hundred
calls still carry thousands of bits regardless.

What changed is that the report now prints the trace length and `log2(n!)` and
says `ORDERING OPEN, nothing here bounds it`, and a test asserts the document
is **accepted** while the row says so.

`argument_surface_guarantee()` prints below every table, clean or not, split
CLOSED / BOUNDED / OPEN, read from the live constants so moving a budget moves
the text. That is my answer to *"the presentation must not silently upgrade
that into 'no sealed text can escape'"*.

**The question for you: is that enough to publish behind, or does an open
ordering channel sink the confidentiality claim outright?** I would rather you
ruled than have me decide it.

## What I most want you to attack

### 1. The six adjudication checks were UNPROVEN and green

Written, wired, suite green, and not one of them had ever been observed to
fire. The coverage census is what refused to let that pass. Six known-bads now
exist and 67 of 69 codes are exercised.

**Three of those fixtures were rewritten mid-flight for tripping more than one
code.** A fixture that fires three cannot prove any one of them can fail. I
believe they are isolated now. Check that.

### 2. The structural sealed_run flag

Mandatory-ness no longer rests on prose. `execution_provenance.sealed_run` is
the machine-readable half, the two must AGREE, and a disagreement is refused
rather than resolved.

**I am not certain this is right.** It replaces one authority with two that can
disagree, and the refusal path is a new branch. Is a bundle that cannot say
whether it is the held-out measurement better refused, or is there a shape
where one of them is unambiguously the authority?

### 3. Did the repairs introduce more instances?

Two agents reported their own tests going green under mutation and said so
rather than fixing them quietly. One reported that with its content firewall
deleted, its end-to-end leak test **stays green** - today's record shapes carry
no content, so that test proves today's shapes and not the firewall.

That is the honest report. It is also exactly where the next instance hides.

## Measured, not asserted

- Suite **2829 collected, exit 0**.
- `contract-check.py`: **eight passes**, and PROVEN now prints that a green pass
  means every promise is ACCOUNTED FOR and not that any is enforced, with the
  eight gaps named on every run.
- With every `bash.exe`/`sh.exe` directory stripped from PATH: 2738 collected,
  no collection errors, exit 0.
- `scripts/pre-read-seal-proof.py`: a command, not a document. Commitment
  AGREED, no leaks across 819 tracked files, and it **currently FAILS on a
  dirty tree** - one untracked design file. That is the check working.

## Still open before the seal

1. **My three tests that assert nothing.** Still there. Oldest debt on the list.
2. The `--out` path guard: the drive log is sealed material and will write
   anywhere.
3. Whether the ordering channel is publishable - your ruling above.
4. Eric's: adjudicate 24 after the read and before the first model call. The
   path now exists; he has not walked it.

## Standing constraints

- **Never read anything under `corpus/sealed/` or `gs://crucible-sealed-x7/families/`.**
- No `gcloud` reads against the sealed bucket.
- Read-only. Report; do not patch.
