# ADR-0015 — the SEP-BY split is reported with every ASR and BPR figure, and parity is a stop-and-re-author

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
(`CONVENTIONS.md` ruling 17)
**Referenced at:** `docs/execution-spec.md:774` (the decision),
`docs/CONVENTIONS.md:731-741` (ruling 17), `docs/measurement-spec.md:655-658`,
`docs/separability-proof.md` (the pair worksheet that carries each pair's SEP-BY value)

## Context

Every attack/benign pair in the corpus is separated one of two ways: **by the policy**, where
the compiled predicate evaluates differently on the two sides, or **by the approval oracle**,
where the predicate is identical on both sides and the oracle decides the outcome.

The problem is that these are indistinguishable downstream:

> **A suite the oracle separates produces identical headline numbers to one the policy
> separates. Only this ratio tells them apart.** (`CONVENTIONS.md:737-739`)

A reader given an ASR figure without the split cannot tell whether the learned policy did the
work or whether an oracle the harness controls did it. Both look like a win.

## Decision

**Print the SEP-BY split next to any ASR or BPR figure.** It is one of exactly two labels
that travel with every ASR figure, permanently and in the same place — the other is
*"single-sample, no stability estimate"* (ADR-0011). **Neither is a footnote**
(`measurement-spec.md:655-658`).

**Authoring gate: if oracle-separated pairs ever reach parity with policy-separated ones,
stop and re-author.** Not a warning, not a note in the results — a halt on corpus authoring.

**The split as the specs record it: 18 policy / 4 oracle** (`CONVENTIONS.md:735`,
`measurement-spec.md:657`).

> **Verify before quoting.** The repo's own session state records **21 policy / 3 oracle**
> against a pair count that has since moved from 26 to 27. The specs and the working corpus
> disagree, which is exactly the drift `CLAUDE.md` warns about — *"counts drift between
> documents written the same day."* The ratio is a measured property of the corpus as it
> stands, so read it from the corpus, never from this file.

## The alternative that was rejected, and why

**Reporting ASR and BPR bare, as single numbers.** That is what the measurement spec did
before ruling 17, and it is the default every results table drifts toward.

Rejected because the bare number is not wrong so much as **unreadable**: it is consistent with
a strong result and with a degenerate one, and nothing else in the reporting distinguishes
them. This is the same failure shape the project names elsewhere — a check that cannot fail is
not a check, and a figure that cannot be discounted correctly is not evidence.

The specs do not name a third option (for instance, reporting only the pairs the policy
separates and dropping the oracle-separated ones). Recorded as unaddressed rather than
invented.

## Consequences

- The split has to be computed and carried, not reconstructed at write-up time. Each pair
  declares its SEP-BY value in the worksheet.
- The authoring gate can halt corpus work at an inconvenient moment. That is the intent: the
  alternative is discovering at D9 that the headline is an oracle result.
- It joins a small family of pre-registered honesty sentences that fire whether or not they
  flatter the outcome — the same pattern as *"if `constrain_arg` never appears in the
  promoted policy, that is stated in the same breath as the F4 number"*
  (`measurement-spec.md:709`).

## What this does not decide

- What the split ought to be. Only that parity is the stop line, and that whatever the ratio
  is, it is printed.
- How pairs are authored or which family they belong to. That is the separability proof.
