# Correction: which rule stopped the foreign agent, and what class it binds

**2026-08-28.** Found by an adversarial third-party review of
`docs/proof/foreign-agent-enforcement-probe-2026-08-26.json`, not by us.

## What was claimed

Devpost Update 8, **already posted**, says the call was refused *"with a policy CRUCIBLE had
learned on a completely different agent."* `docs/devpost/SCORECARD-DRAFT.md` said the deciding
rule *"binds to what the tool can do, move money."*

## What the artifact says

| | value | source path |
|---|---|---|
| rule that denied the LIVE call | **`r_00332742f13f`** | `live.arms[1].tool_attempts[0].rule` |
| its origin | **`seed`** | `policy.rules[0].origin` |
| its capability class | **`CAP_ESCALATES_PRIVILEGE`** | `policy.rules[0].match.capability_class` |
| learned rule in the same policy | `r_ceb7cbd4f589`, `CAP_READS_PII`, `origin: armorer` | `policy.rules[4]` |
| where the learned rule denies | offline case matrix, `cases[1]`, as `expected_deciding_rule` | `cases[1]` |

**Two errors, then.** The class is privilege escalation, not money movement. And the rule that
refused the live call was **seeded by hand, not learned by the loop**. The policy it travelled
in was built against the refund agent and carries both kinds; the probe's policy also carries
two armorer rules (`r_610372f46137`, `r_61d9f5990373`) that appear in none of the 40 bundles of
the two 20-run batches, so it came from an earlier, richer run.

## What survives, and it is the whole point

**A rule that names no tool, binding a capability class assigned by a classifier reading the
tool's own description, refused a call inside Google's unmodified ADK sample before the tool
body ran.** That is portability of class-bound enforcement, and **it does not depend on the
deciding rule having been learned.** The demonstration is intact. Only the sentence describing
why it matched was wrong.

The existing accuracy boundary is unchanged and still travels with it: one run per arm, no
rate, not a breach, the sample obeyed its own prompt, and the policy-side host recorded a
`KeyError: 'status'` afterward.

## What was changed, and what deliberately was not

- **`SCORECARD-DRAFT.md`: corrected**, including the seed-versus-learned distinction.
- **`story-amendment-2026-08-28-prepared.md`: corrected**, same.
- **Update 8: NOT edited.** It is a dated, posted artifact, and this repository's rule is to
  strike and amend a snapshot rather than rewrite one. A correction was drafted for append and
  **withdrawn because it pushed the file to 698 words against ADR-0001's 350 to 500 ceiling**,
  and routing around a gate to publish a correction would be its own defect.

**The open question is therefore a publishing decision, not a technical one.** The precedent
exists: Update 7 was itself a correction to Update 6, published as its own update. This
correction plausibly wants the same treatment. That is the author's call and is recorded here
as owed rather than made.
