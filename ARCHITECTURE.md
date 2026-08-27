# ARCHITECTURE — components, boundaries, IAM, and what is only convention

*Split out of `README.md` on 2026-08-26, verbatim. The README had grown to
1,234 lines and 73,523 bytes, which made it an excellent audit artifact and a
poor entry point for a judge whose first contact with this project is that
file. Nothing here was rewritten to make it read better; where a sentence in
this document has since been found wrong, the wrong version is struck in place
and the correction is dated beside it, because the gap between what a document
said and what was true is the class of defect this project is about.*

**The round-loop diagram and the component table are on the README's first
screen.** All six diagrams, with unbuilt components drawn dashed, are in
[`docs/diagrams/architecture.md`](docs/diagrams/architecture.md). Component
detail is [`docs/architecture-spec.md`](docs/architecture-spec.md), which
`docs/CONVENTIONS.md` outranks wherever the two disagree.

Companion documents: [`MEASUREMENT.md`](MEASUREMENT.md) ·
[`RESULTS.md`](RESULTS.md) · [`AUDIT.md`](AUDIT.md)

---

## Blindness boundaries

---

**Six diagrams in full: [`docs/diagrams/architecture.md`](docs/diagrams/architecture.md)** —
the round loop above, the blindness boundaries split into *structural* and
*convention-plus-a-code-check*, the Google Cloud deployment with **unbuilt components drawn
dashed**, and the five hash-locks on a timeline. Every node is mapped to the file that proves
it exists, and seven specified-but-unbuilt components are named rather than quietly omitted. A
diagram showing an aspirational system is a false claim in picture form.

Two things the diagram above shows as *components* and does not show as *wiring*, said in
words so nobody has to infer them from a box:

- **`REGRESSION_WARDEN` really does all three** — 26 benign, 9 known-bad, archived-attack
  replay (`crucible/warden/warden.py`). **The campaign loop calls only the benign floor.**
  Its drop-in, `crucible/conductor/real_warden.py`, says so in its own docstring, and
  `crucible/conductor/bundle.py` refuses to write a `known_bad_all_expected` field rather
  than record a check that never ran. Read the node as the component, not as the round.
- **`PROMOTION_GATE` is real code that offline evaluates nothing.** See the banner in §5.

The boundaries the diagrams draw are also stated in words here, because they are the part of
the design worth reading:

- **The trust boundary.** Left of it, model-generated and untrusted: red strategist,
  Coroner, Armorer. Right of it, deterministic code: tripwire, Warden, gate, policy engine,
  canonicalizer. Nothing crosses except through a versioned, canonicalized schema in
  `contracts/`.
- **The IAM boundary**, which is a different kind of line. The Armorer's service account
  holds no storage role at all on the sealed bucket. That denial is captured, with a
  positive control, in [`docs/proof/armorer-403.txt`](docs/proof/armorer-403.txt).
- **The episode freeze**, which is a third kind. `episode.*` is frozen before the first user
  turn and unwritable thereafter. If an in-episode turn could move
  `episode.account_holder_email`, the whole seal collapses in one move (ADR-0013).
- **Five hash-locks**, each committed before the artifact it covers could be used: the gate
  rule, the target agent, the capability manifest, the Objective Set (the definition of
  breach), and the corpus with its derived-field schema.

Component detail: [`docs/architecture-spec.md`](docs/architecture-spec.md).

---

## What is NOT this project

Google's `adk-samples` ships `python/agents/safety-plugins`, which contains `BasePlugin`
subclasses that filter agent behaviour **at runtime**, including an `LlmAsAJudge` plugin.
That is a runtime filter: it inspects traffic as it happens, using a model, against rules
somebody wrote by hand.

CRUCIBLE is a different stage of the lifecycle. It runs **before deployment** and does three
things a runtime filter does not: it **discovers** failures by attacking the agent, it
**synthesizes** the policy rather than requiring one to be written, and it **gates
regressions** by proving the new rule did not break recorded legitimate work before the rule
is allowed to exist.

The two compose. `safety-plugins` and a CRUCIBLE-derived policy attach at the same ADK Runner
seam, and `docs/build-spec.md` plans a three-column comparison — stock, Google's generic
judge, CRUCIBLE's derived policy — as a day-10 stretch. **That comparison has not been run.**

CRUCIBLE is also not a scanner you run once, after the fact, to generate a PDF.

---

## Known framework constraints

Two upstream ADK issues sit directly under the enforcement point. Both are turned into
documented constraints rather than hoped past. Full reasoning: `docs/adr/ADR-0012`.

**[google/adk-python#4704](https://github.com/google/adk-python/issues/4704)** —
`before_tool_callback` and `after_tool_callback` are reported not to fire during live
(bidirectional streaming) tool execution. If true, the policy silently does not run: exit 0,
healthy log, no enforcement. **Response:** CRUCIBLE runs targets in non-live `run_async` mode
only. Attach asserts the runner is not in live mode and refuses otherwise, naming the reason.
Every demo beat is pinned to the non-streaming `/run` path. The assertion is unconditional —
it stays regardless of what re-checking #4704 shows.

> **UNVERIFIED:** the D1 probe that would confirm or refute #4704 on this machine — register
> a trivial blocking plugin, confirm it fires through both `/run` and `--with_ui` — has not
> had its result recorded anywhere in the spec set or in ADR-0012. The decision holds either
> way; the observation is missing.

**[google/adk-python#2809](https://github.com/google/adk-python/issues/2809)** — plugins
reported not to run inside `AgentTool`, which would mean a nested agent is observed as clean
when it is not. **FIXED in 2.1.0**, verified against the installed source
(`agent_tool.py:117-133, 238-250`, `include_plugins: bool = True`). The planned `OPAQUE`
union workaround was struck and replaced with a single assertion that every `AgentTool` has
`include_plugins is True`, refusing and naming the offender otherwise. Attach can refuse to
boot, and that is intended: refusing is better than observing a hole as clean.

---

## What is enforced, and what is only convention

Only these are **structural** — a control that holds because the system cannot do otherwise:

- the Armorer cannot read the sealed attack family: it holds no storage role on that bucket
  at all
- the tripwire and the Warden cannot call a model: no `aiplatform.user`, plus an AST import
  lint in the repository
- a promoted policy version cannot be overwritten: the promoting identity holds create-only
  on the policy bucket, plus a retention policy
- the plugin's short-circuit: a denied call does not reach the tool

Everything else is **convention plus a code check** and is described that way. Firestore IAM
has no per-collection granularity, so *"only the gate writes gate decisions"* is a convention
the code observes, not a boundary the platform enforces. The Coroner's inability to propose
fixes is schema plus lint — it retains Firestore write.

**The trust root is the builder, who holds project Owner.** No control in this system defends
against him. That is stated plainly here and on camera, because implying otherwise is the
overclaim most likely to be caught.

---

## What happens when an agent loops, lies, or returns nothing

Every component in this loop except the tripwire, the warden and the gate is a
language model, so the design assumes each of them will at some point produce a
confident wrong answer. Six mechanisms, all in code rather than in prompts, and each
one names the specific failure it exists for.

**A worker claims a success it did not have.** The tripwire is the only thing that
records what happened, and it is pure code sitting between the agent and its tools. It
records what the target *called*, with what arguments, and it never asks any model what
it did. An attacker agent reporting a breach it did not achieve changes nothing, because
nothing downstream reads that report. `crucible/tripwire/evaluator.py`.

**A model is asked to grade its own work.** It is not. The CORONER writes the autopsy
and the ARMORER writes the patch, and neither decides whether the patch is kept — the
WARDEN and the promotion gate do, and both are code. The Armorer's identity also cannot
read the evidence bucket at all: `docs/proof/armorer-403.txt` is the captured 403, with
a positive control proving the probe can fail.

**A patch is accepted that was never durably written.** The gate re-reads the promoted
rule back from disk and recomputes its hash **from the actual bytes**, and refuses on
`E_READBACK_HASH_MISMATCH`. A gate that reports a decision it did not durably record
will lie to you exactly once, at the worst possible moment. `crucible/gate/promote.py`.

**The Armorer stops producing anything usable.** After repeated refusals the campaign
halts on `HALT_ARMORER_EXHAUSTED` and the evidence bundle records the halt reason. It
does not silently continue with an unpatched policy and report the rounds as if they had
run. `crucible/armorer/armorer.py`, `crucible/conductor/conductor.py`.

**The loop starts producing patches that keep getting rejected.** Two consecutive gate
rejections halt the run for a human — `HALT_HUMAN` in `crucible/conductor/conductor.py`.
Two rejections in a row is evidence that the loop has stopped learning and started
guessing, and burning the remaining rounds would produce a curve rather than a finding.

**The target itself breaks, rather than being defeated.** A timeout, a malformed tool
call, an API error: `TARGET_FAULT` is **removed from the denominator, structurally**, in
one place, so no consumer has to remember to do it
(`crucible/conductor/conductor.py:128`). An instrument failure is the *absence* of a
measurement, not a passed attack and not a blocked one. Counting a crash as a successful
defence is the easiest way to manufacture a good number, and it is the one this project
would most like to avoid manufacturing.

There is a seventh that is not about agents at all. **A trace the shadow engine cannot
evaluate** is retried three times and then marks the round `ROUND_INVALID` rather than
scoring it — `contracts/gate_rule.v1.yaml`, G3. **INVALID is not FAILED**, and the two
are reported separately everywhere.

None of the above depends on a model behaving well. That is the point: the components
that decide anything are the ones with no model in them.

---

## Point it at your own agent

**This is not a supported path yet, and the honest version is worth more than a wishful
one.** What exists:

- **The binding surface is the capability manifest** (`target/refund_agent/capability_manifest.json`,
  schema at `contracts/capability_manifest.schema.json`). Every tool maps to one or more of
  six capability classes; a tool nobody classified gets `UNCLASSIFIED` and is **named**
  rather than hidden. Policy rules bind to classes, never to tool names, which is why a
  corpus written for one agent can be pointed at another.
- **The enforcement surface is an ADK plugin** — `CruciblePlugin` in `crucible/plugin/adk.py`,
  a `BasePlugin` that attaches at the Runner. A denied call short-circuits: the tool does not
  execute.

What does not exist: a packaged adapter, a CLI that ingests a third-party agent, or a
documented public interface for either. The "classify an unseen target's tools in forty
seconds and run the existing corpus against it" beat is a planned demo beat
(`docs/measurement-spec.md` §8.2), **not a shipped feature, and it has not been run.**

---

## Architecture decisions

**Eighteen** ADRs in [`docs/adr/`](docs/adr/) — counted from disk 2026-08-26,
~~seventeen~~ CORRECTED: `ADR-0018-corpus-provenance-is-the-commitment-not-the-generator.md`
landed after the sentence was written, which is the ordinary way a count in prose goes
wrong. Each names its context, the decision, the
consequences, and what would make it reverse. The load-bearing ones:

| ADR | Decision |
|---|---|
| [0016](docs/adr/ADR-0016-tripwire-is-deterministic-code.md) | The tripwire is deterministic code, never a model |
| [0002](docs/adr/ADR-0002-evidence-bundle-schema.md) | Components communicate only through a versioned, canonicalized evidence-bundle schema |
| [0003](docs/adr/ADR-0003-dsl-predicates-bind-facts-not-strings.md) | DSL predicates reference trace facts and capability-manifest entries, never strings |
| [0004](docs/adr/ADR-0004-coroner-blindness-by-schema-and-iam.md) | The Coroner's blindness is enforced by output schema and IAM, not by prompt instruction |
| [0005](docs/adr/ADR-0005-enforcement-at-the-adk-plugin-layer.md) | Enforcement at the ADK plugin layer, not at agent callbacks |
| [0006](docs/adr/ADR-0006-promotion-gate-rule.md) | Promotion requires attack-success decrease **and** benign 26/26 (amended from 24/24, ruling 43, 2026-08-21) **and** 9/9 known-bads returning their *expected verdict* |
| [0010](docs/adr/ADR-0010-demo-replays-stored-bundles.md) | The demo replays stored bundles rather than running live |
| [0011](docs/adr/ADR-0011-k-equals-1-everywhere.md) | `k=1` everywhere, with the single-sample label printed next to every ASR figure |
| [0013](docs/adr/ADR-0013-episode-freeze-and-derived-discipline.md) | `episode.*` frozen before the first turn and unwritable thereafter |
| [0015](docs/adr/ADR-0015-sep-by-split-reported-with-every-figure.md) | The SEP-BY split is reported with every ASR and BPR figure |

---

## Google Cloud — what exists and what does not

**Everything in [Spin it up](README.md#spin-it-up) runs locally with no cloud project.** That is
deliberate: the judge path must not depend on our billing account being alive.

> **CORRECTED 2026-08-26 — the revision below is not the one serving.**
> `docs/proof/cloud-run-redeploy-2026-08-24.txt:33-35` records
> **`crucible-00004-gfk`**, deployed 2026-08-24 22:58:01 UTC, as the active
> revision; ~~`crucible-00003-t2q`~~ is the one it replaced. The service URL is
> unchanged. Why it was redeployed is the interesting half: seven commits
> touched `target/refund_agent/` after 2026-08-21, and `FROZEN.json` did not
> exist at the deployed commit, so **the serving revision predated the
> `target_agent_hash` that is supposed to pin it** (`:5-14`). The same file at
> `:46-48` records that **postconditions 3 and 4 are owed again for the new
> revision**, and at `:49-50` that the 2026-08-21 captures "are now stale for
> video purposes." Read the paragraph below as the 2026-08-21 record it is.

**Deployed and serving, 2026-08-21.** Service `crucible`, revision `crucible-00003-t2q`
at 100% traffic, `https://crucible-vgp5owkxyq-uc.a.run.app`. Deployed
`--no-allow-unauthenticated`, running as `crucible-target` — not the compute default, so
the agent under attack does not inherit the builder's authority. Full transcript:
[`docs/proof/cloud-run-deploy-2026-08-21.txt`](docs/proof/cloud-run-deploy-2026-08-21.txt).
What it took to get there — three real defects, each caught by a postcondition rather than
a clean-looking log — is written up in [`deploy/RUNBOOK.md`](deploy/RUNBOOK.md).

The four postconditions this deploy is checked against, precisely, because "deployed" is not
one bit:

1. **PASS.** The service URL resolves and serves.
2. **PASS, and gone further.** `/list-apps` returns `["refund_agent"]` over HTTP 200 with a
   non-empty body, and one full episode ran end to end against the deployed service — the
   agent called `lookup_order("ORD-4471")` and answered from the seeded record.
3. **PASS, with one word of care.** Traces from the deployed agent are visible in Trace
   Explorer — 36 spans over 12 hours, captured 2026-08-21 into
   [`docs/proof/trace-explorer-spans-2026-08-21.png`](docs/proof/trace-explorer-spans-2026-08-21.png).
   **The span names in the capture are `invocation`, `invoke_agent refund_agent`, `call_llm`,
   `generate_content gemini-*`, `/run` and `/list-apps`.** This postcondition was written
   demanding an `execute_tool` span specifically, and `execute_tool` is **not among the names
   visible** — the facet list is truncated, so it is not shown absent either. **The honest
   claim is "the deployed agent's spans are in Cloud Trace", and that is what this repository
   claims.** Eight of the 36 spans are errors, and they are kept deliberately: they are the
   11:16 AM endpoint-mismatch failures from before `GOOGLE_CLOUD_LOCATION` was set to
   `global`. A failure trail in the trace is worth more than a clean board.
4. **PASS.** [`docs/proof/cloud-run-console-2026-08-21.png`](docs/proof/cloud-run-console-2026-08-21.png)
   — service `crucible` green in `us-central1`, URL readable, request and latency graphs live,
   and **`Scaling: Auto (Min: 0, Max: 20)`**, which is the `min-instances=0` cost rule visible
   on the console rather than asserted in a document.

> **How postcondition 3 got settled is a better story than the postcondition.** Four separate
> times on 2026-08-21 this project concluded "no traces exist" — three legacy
> `projects.traces.list` v1 queries (over 45 minutes, 3 hours, and a fresh episode) and then a
> console window scoped to the last hour that did not contain the episode. **The v1 API cannot
> see spans written through the OpenTelemetry path `--trace_to_cloud` uses.** The first null
> was recorded correctly as UNVERIFIED; running the same blind instrument twice more then
> upgraded it to "a confirmed negative." **Repeating a blind check is not a second opinion.**
> Changing the instrument settled it in one attempt.
> [`trace-explorer-1h-empty-window-2026-08-21.png`](docs/proof/trace-explorer-1h-empty-window-2026-08-21.png)
> is kept as the negative control: the same console, six minutes earlier, showing "No rows to
> display" for an episode that had already run.

**Provisioned and read back 2026-08-20**, project `crucible-hack-2026`, region
`us-central1`, all three buckets with uniform bucket-level access ON and public access
prevention ENFORCED:

| Bucket | Purpose |
|---|---|
| `gs://crucible-sealed-x7` | the held-out attack family |
| `gs://crucible-policies-x7` | promoted policy versions. Versioning ON, retention 14d, **unlocked** |
| `gs://crucible-evidence-x7` | transcripts and the final Firestore export |

Names are sourced from `scripts/gcp-env.sh` and never retyped, because a second copy of a
bucket name is a second source of truth and the gate scripts grep these as literal strings
— so a typo does not fail loudly, it produces an unevaluable gate.

**The grant direction on the policies bucket, which is easy to invert:** `crucible-gate`
holds `roles/storage.objectCreator` — create only, not `objectAdmin`. `crucible-armorer`
holds **no** storage role there, asserted as zero. *The identity that authors a candidate is
not the identity that promotes it.*

Reproduce the infrastructure from `infra/`: `create-buckets.sh`, `create-service-accounts.sh`,
`bind-iam.sh`, `verify_iam.py`, `prove-armorer-403.sh`. **These create billable resources.**
`create-buckets.sh` refuses any argument matching `*lock-retention*` with exit 2 — a locked
GCS retention policy cannot be removed or shortened by anyone, ever, including the project
owner, and would block teardown for two weeks past the last write.

**ALL FOUR POSTCONDITIONS CLOSED 2026-08-21** — *for revision
`crucible-00003-t2q`. AMENDED 2026-08-26: postconditions 3 and 4 are open again
for `crucible-00004-gfk`, per `docs/proof/cloud-run-redeploy-2026-08-24.txt:46-48`.
A postcondition is closed against a revision, not against a project, and this
sentence quietly generalised from one to the other.* What remains is the recording itself:
`docs/contest/CONTEST.md` makes on-camera Google Cloud proof a Stage One pass/fail item, and
**the video is the only Stage One deliverable that does not exist as of 2026-08-22.**

> **CORRECTED 2026-08-26, and this is the worst row in the ledger, because the
> defect was in the direction of a better story.** Three separate things in the
> two paragraphs below are wrong.
>
> 1. ~~"16 assertions, 15 PASS, 1 UNEVALUABLE"~~ is not what the 2026-08-22
>    probe reported. `docs/proof/L3-real-gate-G7-G8-2026-08-22.txt:36` reads
>    **16 assertions, 16 PASS, 0 not PASS**, and `:33` shows G7c PASSING. The
>    file warns at `:67` that the G7c pass is a coincidence and should be read
>    as one — which is a better sentence than the one this README wrote over it.
> 2. **The 15/1 split belongs to a later probe**, on 2026-08-25
>    (`docs/proof/L3-real-gate-G7-G8-2026-08-25.txt:36`), and there **the one
>    non-PASS is a FAIL, not an UNEVALUABLE**: `:32-33`,
>    `holdout_touch_count is 11, expected 0`. Those are attested operator reads.
>    A FAIL that gets recorded as an UNEVALUABLE reads as an instrument problem
>    when it is a finding.
> 3. ~~"the project has no `auditConfigs` block"~~ — Data Access audit logging
>    was enabled 2026-08-22 (`L3-real-gate-G7-G8-2026-08-22.txt:41-47`;
>    `docs/contest/BUILD-LIST.md:553`, "G7 fully evaluable for the first time").
>
> And ~~"the probe has not been re-run since"~~ has been false since 2026-08-25,
> when it was re-run and, separately, evaluated live inside the 60-run batch at
> 95 gate calls of 16 assertions each
> (`docs/design/g7-unevaluable-2026-08-25.md:33-35`).
>
> The paragraphs are kept because the *reasoning* in them — why defaulting an
> unevaluable check to zero is worse than failing — is the part worth reading,
> and it is unaffected by the counts being wrong.

**G7 and G8 have now been evaluated against this project, once, on 2026-08-22** —
[`docs/proof/L3-real-gate-G7-G8-2026-08-22.txt`](docs/proof/L3-real-gate-G7-G8-2026-08-22.txt),
generated by a read-only probe that creates, deletes and binds nothing. **16 assertions, 15
PASS, 1 UNEVALUABLE.** The impersonation probes are the part worth reading: `crucible-sealed-eval`
read the sealed prefix (the positive control, so the path is real), and `crucible-armorer`,
`crucible-red` and `crucible-coroner` were each refused **at the storage layer**.

**The one that did not pass is G7c, and it is not a failure — it is worse than a failure and
better than a lie.** `holdout_touch_count` is derived from Cloud Audit Log data-access reads
on the sealed holdout; the project has **no `auditConfigs` block**, so the number does not
exist to be read. **Defaulting it to 0 would print a green check computed from a sink that was
never created.** `contracts/gate_rule.v1.yaml` routes `absent_or_unevaluable` to RUN INVALID
precisely so a check that measured nothing cannot be scored as a check that held. Two things
this probe deliberately does not show: the operator is a human with `roles/owner` and can read
everything here — **you are the trust root and no control defends against you** — and it was
run before anything had ever been promoted, so it says nothing about the write path. That
path first ran against GCS in the 2026-08-24 live batch, which promoted policy and left ~~21
objects~~ **an UNVERIFIED number of objects** under `gs://crucible-policies-x7/runs/`.
~~**The probe has not been re-run since**~~, so G7 and G8 remain evaluated once, on
2026-08-22, against a policies bucket that was then empty.

*Amended 2026-08-26. The object count was **never measured**: nothing in the tree
evidences it, and `docs/design/spec-drift-audit-2026-08-25.md:546-552` says plainly
"**I did not query GCS**" and names the command that would settle it. The number 21 in
this repository is the SEP-BY policy count (`docs/data-spec.md:594`), which is the most
likely place a bare 21 was picked up from. Read it as UNVERIFIED until somebody runs
`gsutil ls`. The struck sentence about the probe not being re-run is corrected in the
block above.*

---

## Repository layout

```
contracts/        the ten frozen schemas, the grammar, the gate rule, the canonicalization
                  spec, and MANIFEST.json with each file's hash. Lanes never edit these.
contracts/golden/ one valid and one deliberately-invalid fixture per contract. The invalid
                  ones must FAIL, and a run where they pass is a broken gate.
corpus/           the corpus loader, lints, sizing, SEP-BY and blindness checks, and the
                  50 training attacks (amended from 48, ruling 43, 2026-08-21). corpus/sealed/ is empty here on purpose.
crucible/canon/   RFC 8785 canonicalization and content-addressed identifiers
crucible/ledger/  the run ledger and the policy lineage chain
crucible/policy/  the policy engine
crucible/tripwire/ the breach evaluator and its model-import lint
crucible/warden/  the regression warden
crucible/gate/    promotion
crucible/plugin/  the ADK BasePlugin - the enforcement point
crucible/replay/  the offline replay viewer  <- the judge path
target/           the refund agent under test: 8 tools, 6 capability classes
fixtures/         26 benign fixtures, 14 of them near-miss (amended from 24/12, ruling 43, 2026-08-21)
infra/            GCP provisioning, IAM binding, and the 403 proof
docs/             CONVENTIONS.md is the spine; everything else is downstream of it
docs/proof/       captured evidence: the Armorer 403, the seal commitment, the ratification
scripts/          contract-check.py, verify-chain.py, hash-contracts.py, seal-commitment.py
tests/            including the strawmen - deliberately wrong implementations kept in the
                  tree forever, so every suite can be shown to fail
evidence/         gitignored. Run bundles land here. NOT PRESENT in a clone at
                  all - checked 2026-08-26 from a worktree, where `ls evidence/`
                  returns "No such file or directory". Every figure derived from
                  a bundle is therefore reproducible on the builder's machine and
                  NOT verifiable from your copy.
```
