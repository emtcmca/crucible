# ADR-0001 — the Devpost update format is locked to Update 2

**Status:** accepted · **Date:** 2026-08-20 · **Decided by:** Eric

## Context

`execution-spec.md` §5a governs *when* a Devpost update is posted and *what it
may claim*. It says nothing about how one is shaped. Update 2 (contracts hashed,
2026-08-20) was drafted, reviewed, and posted, and its shape is now the template
for updates 3 through 6.

Locking it matters more than it looks. The update log's whole job is to make the
pre-registration claim checkable by a reader who never opens `git log` — six
posts that read as one continuous record do that; six posts in six voices read as
marketing. **A format decided once is also one fewer thing to decide at 1am on
the day of a freeze**, which is exactly when the temptation to write a longer,
louder post is strongest.

## Decision

**Every subsequent Devpost update matches Update 2 exactly in structure and
register.** The canonical instance is
`docs/devpost/2026-08-20-update-2-contracts-hashed.md`.

**Markdown, and this is the element inventory — nothing else appears:**

| Element | Rule |
|---|---|
| Title | `##` — `Update N: <lowercase clause>, and <second clause>`. Sentence case. No colon-subtitle stacking beyond the one colon after the number |
| Section heads | `###` — sentence case, no bold, no numbering. Three to four per post |
| Body | Plain paragraphs. **Bold** only for the single load-bearing fact of a section, at most once per paragraph |
| Lists | Numbered only when the items are an ordered set (the five hash-locks). Never bulleted for emphasis |
| Code | Backticks for paths, filenames, and identifiers. **No fenced code blocks** — a Devpost update is prose, not a README |
| Links | One, at the end, the repo, as `[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)` |
| Length | 350–500 words. Update 2 is the upper bound, not the target |

**Register, which is the half a style table cannot capture:**

- **No em-dashes in drafted copy.** Update 2 has none.
- **Lead with the unglamorous fact**, then explain why it matters. Update 2
  opens by calling its own milestone unglamorous, and that is the voice.
- **Every post ends by stating what is NOT known yet**, and names what the next
  post will cover. The closing section of Update 2 is `### No results yet`; its
  successors say the equivalent for their day.
- **Report at least one thing that went wrong**, with the mechanism. Update 2's
  is the negative test that could not fail. This is not modesty — a log that only
  reports wins is the log a reader discounts.
- No adjectives that would survive being deleted. No "excited to share".

**The claim rules in `execution-spec.md` §5a are unchanged and outrank this
document.** Format never licenses a claim. In particular: **only the D8-9 post
may state a result at all**, and every figure carries its label (k=1
single-sample, the SEP-BY split).

## Consequences

- Updates 3–6 are now a fill-in rather than a decision, and each takes minutes.
- The six posts read as one record, which is what makes the timestamps evidence
  rather than a series of announcements.
- **Cost:** a genuinely unusual event may not fit the shape. That is accepted —
  the shape bends for content, but the register does not.

## What would make us reverse it

A freeze that cannot be described honestly inside 500 words, or a result whose
labels do not fit the prose form and need a table. Either is a reason to extend
the format for that post and amend this ADR, **never a reason to drop a label.**
