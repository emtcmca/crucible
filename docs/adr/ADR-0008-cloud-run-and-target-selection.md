# ADR-0008 — Cloud Run over Agent Runtime, Agent Gateway rejected, and the four sample targets that were turned down

**Status:** Accepted · **Date:** backfilled 2026-08-21, decisions dated 2026-08-20
**Referenced at:** `docs/execution-spec.md:775` (the decision), `docs/build-spec.md:11`,
`:173`, `:174`, `:178`, `:181`, `:410-448`, `docs/data-spec.md:22`, `:81`, `:1001`, `:1066`,
`:1094`, `:1129`, `:1359`, `:1468`, `:1574`

## Context

Two selection problems, both with a deadline: which Google runtime the components sit on, and
which shipped ADK sample becomes the target agent. Both were resolved on 2026-08-20 and both
produced rejections worth recording, because the reasons are the interesting part.

## Decision

**Runtime: everything runs on Cloud Run.** Agent Runtime and Agent Identity are **dropped**
(`build-spec.md:173-174`, `data-spec.md:1066`). Agent Gateway is **cut**
(`build-spec.md:178`).

**Target: `python/agents/customer-service`**, with `python/agents/invoice-processing` as the
fallback (`build-spec.md:434`). The framing that follows from it is *"we tested a stated
defense,"* not *"we attacked an undefended toy"* — the sample ships four of its own callbacks,
and three bypasses are already present in the shipped code and verifiable on D3
(`build-spec.md:410-424`).

## The alternatives that were rejected, and why

**Agent Runtime.** Rejected because it carried the A5 pricing unknown for the contest window,
a 10-minute canary, and a second runtime to learn (`build-spec.md:173`, `data-spec.md:81`).
Dropping it removed the $20 provisional line **and the only unmeasured price in the cost
model** (`data-spec.md:1471`).

**Agent Identity.** Rejected because it works only on Agent Runtime. What is lost is
`actor_spiffe_id`: **one BigQuery column and one sentence.** Every load-bearing separation in
CRUCIBLE is service-level, which a Cloud Run attached service account attests — and the three
components whose integrity matters most (Tripwire, Warden, Gate) are pure code and **could
never have held an agent identity anyway** (`build-spec.md:174`).

**Agent Gateway — a confirmed trap.** 20 APIs, Terraform, and org-level IAM in Google's own
codelab, ~100 minutes, 40–60 resources, and nothing visually demonstrable. Its `protocols`
enum is reportedly **MCP-only** and cannot front ADK inter-agent transport
(`build-spec.md:178`).

**The four sample targets** (`build-spec.md:432-448`):

| Rejected | Why |
|---|---|
| `travel-concierge` | **Disqualified.** Its payment layer is prompt theatre — `create_reservation`, `payment_choice`, `process_payment` are `AgentTool(agent=LlmAgent(...))` with no code behind them; the instruction literally says *"You are a Payment Gateway simulator."* **No tool boundary to intercept, so the Tripwire has nothing to judge** |
| `small-business-loan-agent` | Best tools in the repo — `finalize_loan_decision` is hardcoded to `APPROVED` with no rejection branch — but killed by setup: Vertex-only, live Firestore, a GCS bucket, and a preview model |
| `personalized-shopping` | Two tools, no guardrails, and a 5.1 GB download |
| `ambient-expense-agent` | Money-touching, but the money decision is deterministic Python **outside the model's reach**. Poor attack surface, and excellent contrast material — it makes the same argument CRUCIBLE does |

## Consequences

- One runtime to learn, one pricing model, and the A5 unknown ceases to exist
  (`data-spec.md:1574`).
- `actor_spiffe_id` is struck from the BigQuery schema (`data-spec.md:1129`).
- A naming trap has to be navigated in the docs: "Vertex AI Agent Engine" is now **Agent
  Runtime** under the **Gemini Enterprise Agent Platform**, the Vertex AI docs carry a *"no
  longer being updated"* banner, and every pre-mid-2026 tutorial uses dead names
  (`build-spec.md:181`).
- The target's `config.py` sets the model with a `GOOGLE_` prefix but **no
  `env_nested_delimiter`**, so it is not cleanly env-overridable. Edit `config.py` directly
  and commit the diff into `adapters/customer-service/` so the change is visible and
  attributable (`build-spec.md:426`).

## What this does not decide

- Where Gemma runs. That is ADR-0009 (Cloud Run + L4, `min-instances=0`).
- The D3 target freeze protocol — the hash, and the rule that after the hash the only
  legitimate change is one that re-scopes every prior result. `execution-spec.md:795` asks
  for that in an ADR and gives it a number already in use. It is unwritten.
