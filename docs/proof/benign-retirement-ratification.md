# Benign fixture retirement — human ratification

**Date:** 2026-08-21 · **Ratified by:** Eric Tetzlaff

## What was retired

Two ordinary benign fixtures, deleted during corpus integration:

- `ORD-03-shoes-size-fit-partial`
- `ORD-06-lampshade-gift-card-tender`

**Both had been reviewed by the ratifier before deletion.** That is why this file
exists. Everything else in the integration pass was additive or a reconciliation;
this was the one destructive act, and destroying reviewed content silently is how
a corpus stops being the thing that was reviewed.

## Why

`CAP_ESCALATES_PRIVILEGE` benign coverage was **2 against a floor of 4**. Only
`escalate_to_human` carries that class in Part A, and `corpus.schema` validates
classes against the **scored** tool — so a fixture that merely escalates en route
earns nothing toward the floor.

The benign denominator is frozen at **24**, and all 12 near-misses are authored
counterparts of specific attacks and therefore untouchable. Closing the floor
meant re-allocating two ordinary benigns. There was no version of this that added
fixtures without removing fixtures.

Replaced by `ORD-13-no-record-of-sale-escalation` and
`ORD-14-rolling-cap-reached-escalation`, each using a **different escalation
trigger** from the two that already existed (`ORD-08` above band, `ORD-09` §8 risk
scan) — so the floor is met by four genuinely distinct cases rather than four
spellings of one.

## The selection rule, stated so it can be argued with

The two retired were **the only ordinary benigns that were both**:

1. named by **no pair record**, so no SEP-BY denominator changed; and
2. carrying **no `approval_maskable` block**, so no ruling 40.3 content was lost.

`ORD-04`, `ORD-05` and `ORD-07` carry deliberate ruling-40.3 content — they are
the fixtures authored to make `benign_passes_requiring_approval` non-zero and
visible — and were never candidates.

**Nothing was weakened to make this fit.** The benign floor, the denominator, the
near-miss floor and the same-tool floor all stand at their specified values, and
`python -m corpus` passes with no relaxed check.

## The ruling

**Ratified.** The retirement stands and the corpus was 24 benign fixtures with
`CAP_ESCALATES_PRIVILEGE` coverage at 4/4 at the time of this ratification. *(The benign total
was separately amended 24→26 later the same day by `corpus/C6-reach`, ruling 43 — a different
capability class, `CAP_INVOKES_AGENT`. This ratification's C5 coverage of 4/4 is unaffected;
see `measurement-spec.md` §3.2.)*

## What this costs, stated rather than buried

Two fixtures the ratifier had read are no longer in the corpus. The claim
permitted by ruling 40 — *"the ordinary benign set was reviewed in summary"* —
is unaffected in kind, because the two replacements were **not** reviewed by him
at the time of this ratification; he ratified the *decision*, not the
replacements' content.

**If the write-up ever says the ordinary benign set was reviewed, it must mean
the set as it stands**, and two of its members were authored after the review
pass. Reviewing `ORD-13` and `ORD-14` before D5 would close that gap and is
cheap; leaving it open is fine provided nothing claims otherwise.
