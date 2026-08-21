# ADR-0012 — no streaming or live invocation path, plus the `AgentTool` attach assertion

**Status:** Accepted, **with one verification outstanding** — see below
**Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:779` (the decision), `docs/execution-spec.md:19`,
`:187`, `:221`, `:521`, `:791`, `docs/architecture-spec.md:31`, `:415-432` (§3.4a),
`:440-450` (§3.4b), `:1256`, `:1320-1327`, `docs/CONVENTIONS.md:1861-1864`,
`docs/build-spec.md:282`

## Context

Two upstream ADK issues sit directly under the enforcement point chosen in ADR-0005.

**[#4704](https://github.com/google/adk-python/issues/4704):** `before_tool_callback` and
`after_tool_callback` are reported **not to fire during live (bidirectional streaming) tool
execution.** If that is true and CRUCIBLE runs a demo beat through a streaming path, the
policy silently does not run — exit 0, healthy log, no enforcement — and the recording shows
the policy **failing to block** (`execution-spec.md:791`). It is risk #1 in the register.

**[#2809](https://github.com/google/adk-python/issues/2809):** plugins were reported not to
run inside `AgentTool`, which would mean a nested agent is observed as clean when it is not.

## Decision

**1. CRUCIBLE runs targets in non-live `run_async` mode only.** Attach asserts the runner is
not in live mode and **refuses otherwise, with a message naming the reason**
(`architecture-spec.md:440-444`). Every demo beat is pinned to the non-streaming `/run` path,
including the live ones (`execution-spec.md:521`).

**2. Attach asserts `agent_tool.include_plugins is True` for every `AgentTool`, and refuses
otherwise, naming the offender** (`architecture-spec.md:427`).

**3. ADK is pinned at 2.1.0** — the version installed and verified on the build machine — and
is not upgraded mid-build (`execution-spec.md:187`).

## The alternative that was rejected, and why

**The `OPAQUE` union mechanism is struck** (`architecture-spec.md:31`, `:415`, `:432`). The
original design marked `AgentTool` tools `OPAQUE` and computed a static union of the nested
agent's reachable capabilities, on the assumption that plugins could not observe inside them.
**#2809 is FIXED in 2.1.0**, verified against the installed source at
`agent_tool.py:117-133, 238-250` (`include_plugins: bool = True`), so the anticipated
relaxation to real nested observation is what shipped. The union walk is replaced by one
assertion — about four hours saved and one failure mode deleted
(`CONVENTIONS.md:1864`).

It stays on the critical-assertions list even so, because the failure it prevents is
unchanged: an `AgentTool` whose plugins do not propagate is observed as clean, and **a
confident wrong answer about a real hole is worse than a red result**
(`architecture-spec.md:1256`).

Also rejected: **using the ADK web UI (`--with_ui`) on camera**, unless the D1 probe shows
enforcement fires through that path (`execution-spec.md:221`).

## Consequences

- Streaming is off the table for the entire build, not only for the demo. Two upstream bugs
  become two documented constraints, which is the "failure-tolerant design" the rubric names
  (`execution-spec.md:781`).
- The non-live assertion is kept **regardless** of what re-checking #4704 shows
  (`architecture-spec.md:449`).
- Attach can refuse to boot. That is intended: refusing is better than observing a hole as
  clean.

## What this does not decide, and one thing that is not yet verified

**#4704 is a single-source open issue, read 2026-08-19** (`architecture-spec.md:447`,
`:1323`). `execution-spec.md:221` directs a D1 probe — register a trivial blocking plugin,
confirm it fires through **both** `/run` and the `--with_ui` path — and says *"write the
answer into ADR-012 today."*

**That answer is not recorded anywhere in the spec set, and it is therefore not recorded
here.** The decision above holds either way, because the non-live assertion is unconditional.
What is missing is the observed result of the probe, and whether the ADK web UI is safe on
camera. Re-check before the Day-10 rehearsal (`architecture-spec.md:448`).
