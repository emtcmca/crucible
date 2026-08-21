# ADR-0005 — enforcement lives at the ADK plugin layer, not in agent callbacks

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:769` (the decision), `docs/execution-spec.md:301`,
`:187`, `:532`, `:747`, `docs/architecture-spec.md:394`, `:1317-1318`,
`docs/CONVENTIONS.md:1862-1863`, `docs/build-spec.md:173`, `docs/lanes-spec.md:145`

## Context

A compiled policy has to run somewhere. ADK offers two places: a per-agent
`before_tool_callback`, configured on the agent object, and a runner-global `BasePlugin`
hook. They look interchangeable in the tutorials. They are not, and the difference is the
whole security property.

## Decision

**The policy compiles to an ADK `BasePlugin`, and `before_tool_callback` is the enforcement
point** (`execution-spec.md:301`, `architecture-spec.md:394`).

- A non-`None` return from `before_tool_callback` short-circuits the tool
  (`execution-spec.md:747`).
- Plugin callbacks run **before** any agent-level callback, and a non-`None` plugin return
  **skips object-level callbacks entirely** — so a policy cannot be talked out of by the agent
  it governs (`execution-spec.md:301`, `:532`).
- At that hook the plugin resolves `tool → handle → capability_set`, stamps the seven
  `derived.*` fields over the pending args, resolves `role` from the invoking agent name and
  records it on the event, calls the Policy Engine, and emits `TOOL_ATTEMPT` with post-stamp
  args (`architecture-spec.md:394`).

**This is verified at source, not assumed.** ADK is pinned to **2.1.0**, the version installed
on the build machine: all 13 `BasePlugin` hooks exist with matching signatures, and
`plugin_manager.run_before_tool_callback` fires at `functions.py:553`, **Step 1, before**
`agent.canonical_before_tool_callbacks` at `:564` (`execution-spec.md:187`,
`architecture-spec.md:1317-1318`, `CONVENTIONS.md:1862-1863`). Do not upgrade mid-build.

## The alternative that was rejected, and why

**Per-agent callbacks** — named in the decision line itself: "not agent callbacks."

Rejected on ordering. Agent-level callbacks run second and are skipped entirely when the
plugin short-circuits, which means a guardrail installed there is a guardrail whose execution
depends on the configuration of the agent under test. The target agent supplies the proof:
its own stock `before_tool` gates on `if "customer_id" in args:`, so the identity check never
fires on `send_call_companion_link(phone_number)`, and it carries a live `TypeError` on
`args.get("value", None)` (`build-spec.md:414`). Agent callbacks are the thing being *tested*
here. They cannot also be the thing doing the enforcing.

`after_*` hooks were rejected for the obvious reason: they **cannot block**
(`build-spec.md:173`).

## Consequences

- Enforcement is runner-global, so it covers tools added after the policy was written.
- It also covers nested `AgentTool` execution — but only if plugins propagate, which is why
  attach asserts `include_plugins is True` on every `AgentTool` (ADR-0012).
- `before_tool_callback` wraps the entire resolve-and-evaluate path in a catch-all, because
  an exception in the enforcement point must not become a silent allow
  (`architecture-spec.md:1196`).
- The ADK version pin becomes load-bearing. An upgrade could move the ordering that this
  decision rests on.

## What this does not decide

- What the policy says. This is where it runs, not what it contains.
- The live/streaming question. `before_tool_callback` is reported not to fire in
  bidirectional streaming mode (ADK #4704); the response to that is ADR-0012.
