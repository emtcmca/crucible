# ADR-0003 — DSL predicates reference trace facts and capability-manifest entries, never strings

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:767` (the decision), `docs/execution-spec.md:300`,
`:359`, `:532`, `:544`, `docs/lanes-spec.md:145`, `docs/measurement-spec.md:795-800` (G5),
`docs/measurement-spec.md:608` (KB9), `docs/build-spec.md:414-420`

## Context

The whole claim of the project is that a loop can *learn a policy*, not that it can memorize
an attack corpus. A rule that quotes the attack it was born from blocks that attack and
nothing else, and the D9 held-out family — the one falsifiable result in the build — becomes
uninterpretable, because you cannot tell generalization from a string match that happened to
fire.

The target agent supplies the concrete case. `sync_ask_for_approval` returns
`{"status": "approved"}` unconditionally while `approve_discount` rejects `value > 10`:
**two money paths to the same effect, one enforced** (`build-spec.md:414`). That is a
*capability-boundary inconsistency*. A capability-bound rule catches it. A string filter
cannot see it at all.

## Decision

**Predicates reference trace facts and capability-manifest entries. `literal` admits no free
strings — only schema-declared enum members** (`execution-spec.md:300`).

Enforcement is mechanical, not intentional:

- The validator rejects any rule containing a literal drawn from a payload
  (`execution-spec.md:300`, `lanes-spec.md:145`).
- G5 rule hygiene: every rule predicate binds at least one capability class; **zero rule
  bodies contain a banned product-lexicon token**; **zero rule bodies contain an ≥8-token
  substring of any corpus payload** (`measurement-spec.md:795-800`).
- Metadata and provenance fields are exempt from the lexicon check, which is exactly what
  KB9 exists to prove: the same token in a rule body and in
  `provenance.episode_summary` must produce REJECT then ACCEPT, and only structural parsing
  separates the two (`measurement-spec.md:608`).
- Three episode-scoped forms — `preceded_by(cap_class)`, `episode_sum(arg_path) <op>
  <literal>`, and `arg_path <cmp_op> episode.<context_field>` — extend expressiveness without
  reintroducing free text (`execution-spec.md:299`).

## The alternative that was rejected, and why

**Regex or substring matching over user text.** Named directly at `execution-spec.md:300`:
*"never regex over user text."*

Rejected on two grounds. First, it does not work on the defect actually present in the
target: a string filter has nothing to say about two tools reaching the same money effect
through different guardrails. Second, it makes the headline result unreadable — a policy full
of payload substrings scores well on the training slice by construction and tells you nothing
about F4. `execution-spec.md:544` states the demo consequence in one line: the promoted rule
contains **no phrase from the attack and no tool name**, and therefore "covers every
money-moving tool including ones added after it was written."

A related alternative, binding a rule to a **tool name**, was also rejected — the grammar
forbids it, and `execution-spec.md:359` records a demo example being corrected because it
bound to one.

## Consequences

- The Armorer's job gets harder: it must express a fix in capability terms it did not choose.
  This is the assumption the Day-1 spike existed to de-risk.
- A tool declared with untyped `**kwargs` cannot support `constrain_arg` at all; attach must
  report those tools `constraint-ineligible` rather than silently learning only `deny`
  (`architecture-spec.md:1327`).
- The "zero payload substrings" claim is machine-checked and quotable, rather than asserted.

## What this does not decide

- Which verb the Armorer should choose for a given breach — that is observed and reported per
  family, not assumed (`measurement-spec.md:709`).
- Whether a fourth predicate form is ever added. That is ADR-0014, and it is held in reserve
  pending evidence.
