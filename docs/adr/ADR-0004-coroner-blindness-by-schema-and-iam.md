# ADR-0004 — the Coroner's blindness is enforced by output schema and IAM, not by prompt instruction

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:768` (the decision), `docs/execution-spec.md:352`,
`:532`, `:359`, `docs/data-spec.md:1009`, `docs/CONVENTIONS.md:95`

## Context

The Coroner reads one evidence bundle and writes a structured autopsy. The Armorer reads
structured findings and emits a policy patch. If the Coroner can hand the Armorer a fix, the
separation between *diagnosis* and *remedy* is decorative, and the loop is one model talking
to itself through two prompts.

Every architecture of this kind is tempted to enforce that with an instruction: *"do not
propose fixes."* An instruction is a request made to the component most motivated to route
around it.

## Decision

**Three independent structural barriers, none of them a sentence in a prompt**
(`execution-spec.md:352`, `:532`):

1. **The Coroner's output schema has no `fix` field.** There is no place to put one.
2. **Its free-text findings sit in a subtree the Armorer's input adapter cannot address.**
   The Armorer never sees the prose, so prose cannot smuggle a remedy across.
3. **Its service account has no write access to the policy bucket.** IAM, not intention.

The governing sentence, from `execution-spec.md:352`: *"Blindness in a prompt is a
suggestion; blindness in a schema plus an IAM policy is an architecture."*

The same discipline applies in the other direction at the gate: on a rejection the gate hands
the Armorer `{benign_failures: 2, classes: [...]}` and **never fixture IDs or contents**
(`execution-spec.md:359`). Blindness to the fixtures is load-bearing, and a demo beat that
violated it would show, on camera, the loop doing the exact thing the design prevents.

## The alternative that was rejected, and why

**A prompt instruction telling the Coroner not to propose fixes.** Named directly in the ADR
title line at `execution-spec.md:768` — "not prompt instruction."

Rejected because a prompt constraint cannot be audited by a third party and cannot fail
visibly. A judge cannot check that a model obeyed an instruction; a judge can check that a
schema has no field and that `gcloud` reports no role. This is the same argument that keeps
the Tripwire model-free (`CONVENTIONS.md:95`) and the same one that puts the Tripwire's
service account without `aiplatform.user` so that it "structurally cannot call a model"
(`data-spec.md:1009`).

## Consequences

- The Coroner can be run, re-run, and even misbehave, and the worst it produces is a bad
  autopsy — never an unreviewed policy change.
- The barrier is demonstrable in about eight seconds on camera: no field, no role.
- Cost: the Coroner's richest observations, the ones that read like a fix, are discarded by
  design. That is accepted.

## What this does not decide

- What the autopsy schema's fields actually are.
- The Armorer's own IAM posture on the policies bucket. That boundary — the author of a
  candidate is never the identity that promotes it — is gate G8 and is separate from this
  one.
