# ADR-0011 — k = 1 everywhere, disclosed with a permanent label

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:778` (the decision), `docs/execution-spec.md:84`,
`:808`, `docs/CONVENTIONS.md:303`, `docs/measurement-spec.md:21`, `:356`, `:390-398` (§2.2),
`:657`, `docs/architecture-spec.md:1216`, `docs/data-spec.md:160`, `docs/build-spec.md:504`

## Context

The measurement spec originally specified **k = 3** repetitions per attack instance plus a
stability statistic. At the corpus sizes and round counts CRUCIBLE runs, that does not fit
the **$160** spend cap (`execution-spec.md:84`). Something had to give: the corpus, the round
count, or the repetitions.

Both levers were pulled on 2026-08-20 — the corpus shrank to 48 training / 24 sealed / 24
benign / 9 known-bad **and** k went to 1 (`execution-spec.md:808`).

## Decision

**k = 1 everywhere**, at fixed temperature and fixed model version — not "k=1 in-loop, k=3 on
the runs that matter." The correction at `execution-spec.md:84` is explicit: *k=3 on the final
and held-out runs is **not** funded either.*

**The label is part of the decision, not a footnote:**

> **"single-sample, no stability estimate"** is printed next to **every** ASR figure,
> permanently — on slides, in the README, in `docs/results.md`, and spoken once on camera
> (`measurement-spec.md:390-398`). `measurement-spec.md` §10.1 permits k=1 **under exactly
> this label and no other.**

Breach semantics stay **any-of-k**, so the figure always prints as **"ASR (any-of-1)"**
(`CONVENTIONS.md:303`). `reps_k: 1` is a field in the run manifest (`data-spec.md:160`).

Two labels travel together with every ASR figure: this one and the SEP-BY split (ADR-0015,
`measurement-spec.md:657`).

## The alternative that was rejected, and why

**k = 3, the previously specified design.** Rejected on corpus math against the spend cap.
The cost is real and is stated rather than glossed: **there is no flakiness measurement this
run** (`measurement-spec.md:356`).

The second, more important rejection is of a *presentation* choice. The specs refuse the
option of **quietly dropping the stability section**. §2.2 is retitled *"Flakiness — not
measured this run, and that is stated, not hidden,"* and keeps the struck k=3 text visible so
a reader can see what was removed. `build-spec.md:504` names the shape of the concession:
a methodological weakening **requires an ADR**, because an undocumented one is
indistinguishable from an oversight.

## Consequences

- Every ASR figure in the submission is a single sample and says so. A reader can discount it
  correctly, which is the only thing that makes it worth quoting at all.
- Nothing in the analysis may lean on run-to-run stability, because none was measured.
- **If schedule recovers, restore k=3 on the final and held-out runs only** — not everywhere
  (`CONVENTIONS.md:303`). Restoring it mid-run would mean two arms measured under two
  protocols.

## What this does not decide

- The corpus sizes. Those are frozen separately in `CONVENTIONS.md` §4 and were cut in the
  same session for the same reason.
- Whether the pre-registered v0→vFinal comparison is significant. That test is run **once**,
  not per round (`measurement-spec.md:383-386`), and k has no bearing on that choice.
