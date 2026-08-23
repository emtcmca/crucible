# CAPABILITY_CARTOGRAPHER against a foreign ADK agent — what was built, what was measured, what is blocked

**Lane:** GEMMA-CARTOGRAPHER (L5) · **Branch:** `lane/gemma-cartographer`, cut from
`main` at `ef851e6` · **Date:** 2026-08-22
**Brief:** `docs/decisions-pending/gemma-scope.md` (the coordinator's scoping memo,
2026-08-21). Its §7 "What we will not claim" governs every sentence here.

**One-line summary.** The pre-pass now runs against an agent we did not write, and
it resolves **0 of 12 tools** — which is the finding, and it corrects two live
documents. The Cartographer that consumes the residue is built, tested offline
against a stub, and gated behind a human. **No model call has been made**, because
managed Gemma is not reachable from `crucible-hack-2026` and enabling it is a
project change Eric supervises.

---

## 1. The foreign target, and the SHA, verified

`gemma-scope.md` §2 rules out our own agent: all eight tools in
`target/refund_agent/capability_manifest.json` are hand-classified with zero
`UNCLASSIFIED`, so the Cartographer pointed at them has nothing to do. The target
is **`google/adk-samples` → `python/agents/customer-service`**, which is also the
sample `build-spec.md` §8b and `execution-spec.md` §3 already select, and the one
`CONVENTIONS.md:1753`'s approved claim is about.

**The SHA was not retyped from any document.** `f4c19ab` is the standing scar
here: a hardcoded fixture literal in `scripts/make-golden.py` that looked like a
real upstream SHA, propagated into three golden fixtures and a proof file, and was
read back as an observation (`third-party-target-recon-2026-08-22.md` §1). So:

```
$ cd /c/dev/_sandbox/adk-samples
$ git rev-parse HEAD
629310b7b845398841c814456289a34fbc766acf
$ git cat-file -t 629310b7b845398841c814456289a34fbc766acf
commit
$ git rev-parse 629310b7b845398841c814456289a34fbc766acf^{commit}
629310b7b845398841c814456289a34fbc766acf
$ git ls-remote origin HEAD
629310b7b845398841c814456289a34fbc766acf	HEAD
```

The fourth command is the one worth keeping. The local clone is shallow and was
made yesterday by the L6 lane, so `cat-file` alone only proves the object is in
*that* clone. `ls-remote` was run against `github.com/google/adk-samples` today
and returns the same SHA, so the object resolves upstream too.

**The caveat from L6 stands unchanged: this is HEAD of a live branch and it will
move.** It has not moved between 2026-08-21 and now. Any later run re-captures the
SHA from the clone at attach time; nothing downstream reads it out of this file.

## 2. The measurement, which is the headline

`architecture-spec.md:138` scopes the Cartographer to "each tool the deterministic
pre-pass could not resolve". `crucible/cartographer/prepass.py` is that pre-pass.
Run it over all twelve tools of the foreign agent:

```
$ python -m crucible.cartographer.run --print-prompt
target        adk-samples/python/agents/customer-service
commit_sha    629310b7b845398841c814456289a34fbc766acf
fixture       12 tools, digest e9ae52b9ea5920a7e0fc46dc119a8252a96cdff5b01a7099dbde2a50aa34f5e1
pre-pass      0 resolved, 12 residue
```

**0 of 12.** Against **6 of 8** on our own refund agent
(`tests/test_capability_prepass.py`, pinned).

That gap is not a bug in either number. `prepass.py` has five rules and every one
of them keys on **our** agent's argument vocabulary: an `amount` argument beside a
`currency` argument; a `to` argument whose own description says "email address";
`status_to`; `*_agent`; `queue`. The foreign agent's tools take `phone_number`,
`discount_type`, `value`, `customer_id`, `items_to_add`, `delivery_method`. No
overlap, so no rule fires.

**Two live documents say otherwise and are now wrong:**

| Document | What it says | Status |
|---|---|---|
| `docs/proof/third-party-target-recon-2026-08-22.md:307` | "Tools 1, 5, 7, 8, 10 resolve in the **deterministic pre-pass** on arg-shape alone" | **Falsified.** Written the same day the pre-pass was built, apparently without running it. None of the five resolve. |
| `docs/decisions-pending/product-shape-2026-08-22.md:76` | "The deterministic pre-pass (`crucible/cartographer/prepass.py`) already resolves most of it" | **True of our agent, false of a foreign one** — and "it" in that sentence is the foreign-agent case. |

Neither file is owned by this lane and neither was edited. The number is pinned as
`test_prepass_resolves_nothing_on_the_foreign_agent`, so it fails loudly if it
ever changes, and the correction is flagged here for whoever owns those files.

### What the number means for whether a model is warranted

`gemma-scope.md` §6 authorises stopping if the pre-pass resolves everything. It
resolved nothing, so that stop condition does not fire. But the mirror-image
condition is the one that actually obtains, and it deserves saying plainly:

> With an empty left-hand side, the model is classifying **everything**. That is
> the exact situation §6 warns about — *"A model asked to classify everything is
> doing work a `str` comparison should have done, and its mistakes are then
> indistinguishable from its judgments."*

So the pre-pass-first architecture is real, is enforced in code
(`split_residue()`), and on **this** target is currently buying nothing. The
honest reading is: **the deterministic layer is agent-specific today.** Making it
portable — rules that key on shape rather than on our vocabulary — is real work
and it is not this lane's to do, because `tests/test_capability_prepass.py` pins
the agreement numbers on our own agent deliberately so that a rule change "shows
up as a diff a reviewer has to explain", and that file belongs to whoever owns the
pre-pass. **Adding rules until 0/12 looks better is tuning to a fixture and must
not happen.**

## 3. What was built

All new. Nothing existing was modified; `prepass.py`'s classification logic is
untouched.

| File | Job |
|---|---|
| `crucible/cartographer/extract.py` | reads a foreign agent's tool module by path and turns each registered function into a `classify_tool` spec, carrying `source_file` + `def_line`. Nothing is typed by hand except the module path and the tool-name list. |
| `crucible/cartographer/freeze_foreign_target.py` | regenerates the committed fixture. The tool-name list mirrors the sample's own `agent.py` `tools=[...]` registry. |
| `crucible/cartographer/foreign/adk_customer_service.json` | the frozen 12-tool surface, digest `e9ae52b9…`, recomputed on every load so a hand-edited fixture fails at load. |
| `crucible/cartographer/gemma.py` | the Cartographer: `split_residue` → `build_prompt` → `parse_response` → `validate_proposal_set`. The model sits behind a `complete(prompt) -> str` seam. |
| `crucible/cartographer/ratify.py` | the human gate. `to_manifest_entries()` is the only route from proposal to manifest entry and it needs a named human plus a digest that binds. |
| `crucible/cartographer/vertex.py` | Option B, and only Option B. No container, no endpoint, no deploy. |
| `crucible/cartographer/run.py` | `--print-prompt` (offline, free) and `--live` (costs money, refuses without `--project`). |
| `tests/test_cartographer_gemma.py` | 35 tests, no model call, no credential, no spend. |

### The part that carries the weight: a citation is checked, not requested

`prepass.py`'s doctrine is that *"a classification with no citable evidence is a
guess wearing a confidence number"*, and prose in a prompt does not enforce that.
So every proposed class must carry an evidence entry whose `cites` block is one of:

- `{"kind": "argument", "value": "<name>"}` — must be an argument **that tool**
  declares. A name borrowed from a sibling tool is rejected
  (`test_grounding_is_per_tool_not_a_global_argument_lookup`).
- `{"kind": "docstring", "value": "<span>"}` — must appear **verbatim** in that
  tool's docstring. A paraphrase of the same true claim is rejected
  (`test_a_docstring_citation_must_be_verbatim`).

A fabricated citation is therefore a parse failure, not something a reviewer has
to notice. Same shape as the Armorer never writing a rule ID
(`CONVENTIONS` 2.6): the model emits something code can check against ground
truth, and code checks it.

Ten rejection codes, one test each — `E_TOOL_ALREADY_RESOLVED`,
`E_TOOL_NOT_IN_RESIDUE`, `E_UNKNOWN_CLASS`, `E_UNCLASSIFIED_MIXED`,
`E_CLASS_WITHOUT_EVIDENCE`, `E_CITATION_NOT_GROUNDED`, `E_NO_CLASSES`,
`E_INCOMPLETE_COVERAGE`, `E_DUPLICATE_TOOL`, `E_NOT_JSON`. Asserting the code
rather than "it raised" is deliberate: a rejection test that only checks for an
exception passes when the wrong check fires.

The field is named `model_self_reported_confidence`, at length, because a field
called `confidence` in a JSON blob eventually gets read as accuracy. **No accuracy
figure exists** — nothing has been measured against a labelled set.

## 4. Hosting: Option B was recommended and it is NOT AVAILABLE

`gemma-scope.md` §5 recommends **Option B, Vertex Model Garden managed Gemma**,
over Option A (Cloud Run + L4), on hours-not-days and on the standing
`min-instances=0` $193 risk. That recommendation was never checked against the
project. It has been now.

Full evidence: `docs/proof/vertex-gemma-maas-probe-2026-08-22.txt`.

> **SUPERSEDED 2026-08-22. The finding below is WRONG and is kept rather than
> deleted.** Managed Gemma is reachable from this project. Every probe recorded
> here used the wrong publisher model id — the id ends `-maas` — so the four
> `404 NOT_FOUND` results below say nothing about availability. The control was
> also taken on a model this project is forbidden to run. Corrected evidence:
> `docs/proof/vertex-model-reachability-2026-08-22.txt` §3. The Cartographer has
> since run live against it: `docs/proof/cartographer-live-run-2026-08-22.json`.
> **The tell that was walked past: with the correct id, `us-central1` returns a
> 400 naming the fix, where a wrong id returns a 404 naming nothing.**

- **Control first.** `google/gemini-2.5-flash`, same URL, same OAuth token, same
  payload shape → **HTTP 200**. So the endpoint shape, the auth and the project
  path are all correct, and every 404 below is about the model rather than the
  client. A 404 proves nothing until the instrument is known good — this project's
  standing failure shape is *a check that never inspected its own instrument*.
- **Four probes, four `404 NOT_FOUND`:** `google/gemma-4-26b-a4b-it` and
  `google/gemma-3-27b-it`, each in `us-central1` and `global`. *"was not found or
  your project does not have access to it."*
- `aiplatform.googleapis.com` **is already enabled**, so no API enable is needed.

Two facts from Google's own documentation, verified the same day, that change how
§5's table should read:

1. **Gemma 3 on Vertex is a self-deploy model.** Model Garden gives you a
   GPU-backed endpoint you stand up and pay for. That is **Option A wearing Option
   B's name**, and §5's "B — per-call, no infra" row does not describe it.
2. The only Gemma published as fully managed serverless MaaS is
   **`gemma-4-26b-a4b-it`**, announced as available "over the coming days". This
   probe cannot settle whether that listing is live anywhere; it can only report
   that this project cannot reach it.

### The mutating action needed, and NOT taken

**Enable Gemma for `crucible-hack-2026` in Vertex Model Garden and accept
Google's Gemma terms of use.** That is a project change plus a licence
acceptance. Nothing was enabled, accepted, deployed, or purchased. Every `gcloud`
command run by this lane was read-only (`services list`, `auth
print-access-token`, `config get-value`).

One smaller item, also not taken: `gcloud ai model-garden models list` fails with
*"the aiplatform API requires a quota project, which is not set by default"* —
ADC has no quota project. The REST path used here routes around it (the project
is in the URL), so it blocked nothing, but `gcloud auth application-default
set-quota-project crucible-hack-2026` is what a console-side listing would need.

**Cost incurred by this lane: four 404s and one 10-token `gemini-2.5-flash`
control. USD 0.00 to the cent. No Gemma spend exists because no Gemma call was
made.**

### The fork, restated for Eric with the new facts

| | Cost | What it buys | Blocked on |
|---|---|---|---|
| **B — managed Gemma** (`gemma-4-26b-a4b-it`) | per-call, cents | pinned model id + seed, **not** the container. A third party can re-issue the same prompt against the same published id; they cannot pin the weights or the serving stack | **one console action**: enable + accept terms |
| **A — self-deploy Gemma on a Vertex/Cloud Run GPU** | ~$0.34/burst, **plus** the standing `min-instances=0` $193 risk `ADR-0009` names | full reproducibility | real deploy work, and a GPU service to tear down |
| **C — do not build it** | 0 | the split, the prompt, the validator, the gate and the tests all still exist and all still run offline | nothing |

**C is not the empty option it was in §5.** Everything except the model call is
built and green. What C costs is the proposals themselves — and therefore the
ratification artifact, which is the visible beat.

One further option this lane did **not** take and flags rather than chooses:
`gemini-2.5-flash` is reachable *right now* in this project and would produce
proposals today. It is a different claim — a hosted proprietary model, not an
open-weights one pinned by seed — and §5's whole reproducibility argument is
about the latter. **Swapping the model without swapping the sentence is how a
claim goes bad.** Eric's call.

## 5. The ratification artifact

`docs/proof/cartographer-adk-ratification.md` — **UNSIGNED, deliberately.**

There are no proposals to ratify, so the sheet carries the review contract
instead: what must be in front of the ratifier (all twelve rows, full signature
and docstring, every citation, the source line), the three verdicts (accept /
amend / reject, with `amend` stamping `classified_by: human`), and what the
signature binds to.

Written before the answers exist so the standard cannot be relaxed to fit
whatever a model returns. `sealed-family-ratification.md` records the cost of
getting that wrong from the other direction: its first draft showed mechanics
rather than material and the ratifier could not tell what he was being asked to
judge.

**One trap named explicitly in that sheet.** `third-party-target-recon-2026-08-22.md`
§3 already contains a twelve-row hand classification of this exact tool surface.
Running a human's own work through the gate as if a model produced it would be a
fabrication in the same family as `f4c19ab`. It is legitimate as a **comparison**
after a real run — and with n=12 and one rater, that comparison is an
observation, never a measurement.

## 6. What R3 can honestly claim after this, and what it still cannot

`docs/contest/track-fit.md` grades **R3 — "agents are cataloged for
cross-department use"** as **PARTIAL**, because the manifest catalogs *tools on
one agent*, hand-classified. This is Stage Two scoring; the +0.2 open-model bonus
is incidental to it.

**Can be claimed now, on evidence in this branch:**

- The cataloging pipeline runs against an agent CRUCIBLE did not write, pinned to
  a verified upstream commit, with per-tool source provenance.
- The catalog is produced by a deterministic pass plus a model-proposal stage that
  sees only what the deterministic pass could not answer, and **every proposed
  class must cite an argument the tool declares or a verbatim span of its own
  docstring** — checked in code, not asked for in a prompt.
- Nothing enters a manifest without a named human, bound by digest to the exact
  classifications reviewed.
- We measured the deterministic layer before adding a model, and **published the
  unflattering result** — 0 of 12 — rather than assuming it.

**Cannot be claimed, and this is `gemma-scope.md` §7 restated as binding:**

- Not that Gemma generated the attack corpus. Withdrawn, `ADR-0018`.
- Not that any classification is authoritative. It is a **proposal**; a human
  ratifies.
- **No accuracy figure.** Nothing has been measured against a labelled set. The
  model's self-reported confidence is not accuracy.
- Not that CRUCIBLE is a fleet-scale catalog. This classifies **one** foreign
  agent's tools.
- **Not that a Cartographer classification has actually been produced.** As of
  this commit the model has never run. The pipeline is built and tested; the
  output does not exist.

**R3 moves toward MEET. It does not reach MEET**, and it will not on twelve tools
of one sample. What changed is that the cataloging discipline now demonstrably
applies to a foreign agent instead of only to ours — which is the difference
`product-shape-2026-08-22.md` calls *"we hardened our agent"* versus *"point it at
yours."*

## 7. Verification

```
$ python -m pytest tests/test_cartographer_gemma.py; echo $?
35 passed
0

$ python -m pytest --collect-only; echo $?
1342 tests collected in 5.25s
0

$ python -m pytest; echo $?
1341 passed, 1 skipped, 1 warning in 62.57s
0

$ python scripts/contract-check.py; echo $?
ALL PASSES OK
0
```

Collected count and the full-suite exit code are read from pytest itself. `grep -c`
returns exit 1 on a zero count, so grepping pytest output for a green mark is a
heuristic that has already produced a false green in this repo.

`contract-check.py` earned its keep on this branch: its STATUS pass caught an
undated status claim in the ratification sheet ("what does not exist yet is…"),
which is precisely the sentence that goes stale by standing still. Now dated.
