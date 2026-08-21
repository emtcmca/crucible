# ADR-0010 — the demo replays stored evidence bundles rather than running the loop live

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:777` (the decision), `docs/execution-spec.md:510-521`
(the beat-by-beat table), `:538`, `:393`, `:402`, `:481`, `:713-715`, `:792`,
`docs/build-spec.md:164`, `docs/lanes-spec.md:65`, `:174`

## Context

Four of the seven demo beats are multi-minute model workloads. Vertex runs on **dynamic
shared quota** with no per-project RPM to raise (`execution-spec.md:792`), so a live
convergence run on camera is an outcome nobody controls. A `429 RESOURCE_EXHAUSTED` during
the loop beat does not just cost twenty seconds; it costs the beat that carries the whole
result.

## Decision

**Run the full convergence offline, store the evidence bundles, and replay them on camera.**
Decided before recording and **stated on camera**, not discovered by a viewer
(`build-spec.md:164`, `execution-spec.md:510`).

| Beat | Mode |
|---|---|
| Refund agent doing real work | **LIVE** — one or two calls; must feel real |
| Single attack landing a breach | **LIVE** — short enough to survive a 429; stored backup cued |
| The full loop to termination | **REPLAY** |
| Gate refusing a patch | **REPLAY** (the Day-6 stored bundle) |
| Held-out test | **REPLAY** — it is a sealed artifact, and replaying is more honest than rerunning |
| Third-party breach | **REPLAY** (Day-9) |
| Cloud Run + Trace console | **LIVE** — loads fast, proves GCP |

Every live beat uses the non-streaming `/run` path (ADR-0012).

The honesty beat is scripted verbatim at `execution-spec.md:538`: *"Everything from here is
replayed from stored evidence bundles recorded offline. … The bundles are in the repo —
replay them yourself, no credentials needed."*

## The alternative that was rejected, and why

**Running the loop live on camera.** Rejected as an unforced risk: dynamic shared quota, no
lever to raise, and a multi-minute exposure window (`execution-spec.md:513`, `:792`).

The rejection is narrow and worth stating precisely, because the specs are careful about it:
replay is not chosen to hide a weak result. It is chosen because the artifact being shown —
a sealed held-out test — **is already a recording**, and re-running it would be the less
honest option, not the more honest one (`execution-spec.md:518`).

The mitigation that makes the rejection safe: **replay from a clean checkout with no
credentials in the environment. If it needs a key, it isn't a replay**
(`execution-spec.md:402`).

## Consequences

- The replay viewer becomes a deliverable: reads only from disk, needs no credentials, and is
  how a judge reproduces the result for free (`execution-spec.md:393`, `lanes-spec.md:174`).
- The judge path in the README is a single command over a committed directory:
  `python -m crucible.replay evidence/runs/2026-08-28-holdout` (`execution-spec.md:713-715`).
- Quota failures can now only cost the two short live beats, both with stored backups cued —
  and the script includes rehearsing a 429 once so the response is not improvised
  (`execution-spec.md:792`).
- L6 can develop the viewer against a hand-written evidence bundle and never wait on a run
  (`lanes-spec.md:65`).
- If the viewer is cut, the fallback is `cat`-ing JSON on screen, losing ~20s of legibility:
  *"a judge reading a clean evidence bundle in a terminal is not a bad look for a security
  tool"* (`execution-spec.md:481`).

## What this does not decide

- The contents of the bundles, or the schema they conform to (ADR-0002).
- Which invocation path the live beats use, and why (ADR-0012).
