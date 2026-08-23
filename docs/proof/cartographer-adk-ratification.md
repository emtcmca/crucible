# Cartographer proposals, foreign ADK target — human ratification

**Status: UNSIGNED. Nothing has been ratified and nothing has entered a manifest.**

**Prepared** 2026-08-22 by lane GEMMA-CARTOGRAPHER (`lane/gemma-cartographer`),
**filled with real proposals** 2026-08-22 by lane GEMMA-WIRE (`lane/gemma-wire`)
· **Ratifier:** Eric Tetzlaff · **Signed on:** _(blank)_
· **Proposal-set digest at signature:** _(blank — filled by
`build_ratification()`, not by hand)_

**Digest of the proposal set on the table:**
`abef20e46f37609f46bfbef0c68c7ba1497ca5f5e9aaafecb5b9ca8703ff3888`
(`ratify.proposal_set_digest()` over the twelve proposals below. Recompute it
against `docs/proof/cartographer-live-run-2026-08-22.json` before signing —
that is what the signature will bind to.)

**Target:** `google/adk-samples` → `python/agents/customer-service`
**Commit:** `629310b7b845398841c814456289a34fbc766acf` (verified with
`git rev-parse` in `C:\dev\_sandbox\adk-samples`; output pasted in
`docs/decisions-pending/gemma-cartographer-foreign-adk-2026-08-22.md` §1)
**Fixture digest:** `e9ae52b9ea5920a7e0fc46dc119a8252a96cdff5b01a7099dbde2a50aa34f5e1`

---

## Why this sheet existed before there was anything on it

`architecture-spec.md:138` gives the `CAPABILITY_CARTOGRAPHER` two properties
that make it defensible: its output is **never final**, and **it cannot approve
its own classification**. `gemma-scope.md` §6 says the same thing the other way
round — *"The Cartographer proposing straight into the manifest would break the
one property that makes it defensible."*

That gate is built and tested (`crucible/cartographer/ratify.py`,
`tests/test_cartographer_gemma.py`). It now has something to gate.

**CORRECTED 2026-08-22.** This section previously read *"no proposal set exists
to put through it, because the managed Gemma endpoint is not reachable from
`crucible-hack-2026`."* **The endpoint was always reachable. Every probe that
said otherwise asked for a model id that does not exist (probed 2026-08-22)** —
the publisher id ends `-maas`, and `gemma-4-26b-a4b-it`, `gemma-3-27b-it`,
`gemma-3-12b-it` and `gemma-2-27b-it` all returned 404 for that reason on
2026-08-22. `google/gemma-4-26b-a4b-it-maas` at `location=global` returned 200
the same day and needs no Model Garden enablement, no licence acceptance and no
GPU. A published model id is verify-on-use like any other identifier; re-probe
before quoting either result. Full record:
`docs/proof/vertex-model-reachability-2026-08-22.txt` §3.

The lesson is worth keeping next to the rows below, because it is the same
failure the gate exists to prevent: **a negative result was accepted three times
because it agreed with what a memo predicted, and nobody checked the
identifier.** With the correct id, `us-central1` returns a `400
FAILED_PRECONDITION` that names the fix in plain text; a wrong id returns a 404
that names nothing. Two different errors, trivially distinguishable, and the
difference went unread.

**This file is deliberately not a placeholder filled in later by whoever
happens to be looking.** It is the review contract, written down before the
answers exist, so the standard cannot be relaxed to fit whatever the model
returns. `sealed-family-ratification.md` records the opposite lesson from the
same project: the first draft of that review presented mechanics rather than the
material, and the ratifier could not tell what he was being asked to judge. What
gets shown to the reviewer is decided here, in advance.

---

## What must be in front of the ratifier

Twelve tools, one row each. **Not a summary. Not a count.** For every tool:

| Shown | Why |
|---|---|
| the tool's full signature and docstring, as extracted | the reviewer is checking a claim about a declaration, so the declaration is on the page |
| the proposed class set | the thing being ruled on |
| every evidence entry, with the argument name or the verbatim docstring span it cites | a classification with no citable evidence is a guess wearing a confidence number (`prepass.py`) |
| `model_self_reported_confidence` | **labelled as the model's opinion of itself.** It is not an accuracy figure; nothing has been measured against a labelled set |
| the source line in the sample (`tools.py:NNN`) | so a disputed row can be settled in the source, not in this document |

The prompt that produced the proposals is `docs/proof/cartographer-residue-prompt-2026-08-22.txt`.
It travels with the proposal set (`Cartographer.propose()` returns the prompt and
the raw response alongside the parsed proposals) so the reviewer can see what was
asked, not only what came back. Both are also written verbatim into
`docs/proof/cartographer-live-run-2026-08-22.json`, together with the endpoint,
the request parameters and the token usage.

## The three verdicts

Per tool, one of:

- **accept** — the proposed class set stands. The manifest entry is stamped
  `classified_by: cartographer`.
- **amend** — the reviewer supplies a different class set. The entry is stamped
  `classified_by: human`. **This is the outcome that matters most**: it records
  that a person changed the answer rather than approved it, and a gate that can
  only rubber-stamp or refuse hides exactly that case.
- **reject** — no manifest entry is produced at all.

A tool with no recorded verdict blocks the whole ratification
(`E_UNREVIEWED_TOOL`). There is no partial signature.

## What the signature binds to

`build_ratification()` hashes the classifications themselves — tool names,
proposed classes, evidence — and stores that digest in the record. Change one
proposed class after signing and `to_manifest_entries()` raises
`E_DIGEST_MISMATCH`. **The ratifier is bound to the bytes he read, not to a list
of tool names.** The prompt and the raw response are deliberately outside the
digest: re-running the model moves both without changing a single
classification, and a signature that expires on whitespace is one people route
around.

## Two things the ratifier should know before ruling

1. **The deterministic pre-pass resolved none of these tools.** 0 of 12, against
   6 of 8 on our own refund agent. So on this target the model is classifying
   everything, which is the condition `gemma-scope.md` §6 warns about —
   *"its mistakes are then indistinguishable from its judgments."* The evidence
   requirement is what carries the weight here, and it is worth reading the
   citations rather than the classes.
2. **Every tool in this sample is a mock** (`third-party-target-recon-2026-08-22.md`
   §3). `update_salesforce_crm` returns `{"status": "success"}` and calls
   nothing. So a class here describes **declared capability of the tool surface**,
   not observed effect — which is the right thing to classify, and the wrong
   thing to narrate as "we watched it move money".

## A prior hand classification exists, and it is not this

`third-party-target-recon-2026-08-22.md` §3 already contains a twelve-row
classification of this exact tool surface, done by a human reading the source.
**It must not be fed through this gate as if a model produced it.** Ratifying a
human's own work as a Cartographer proposal would make the artifact a fabrication
in the same family as `f4c19ab`. It is legitimate to use as a *comparison* after
a model run — and that comparison is the closest thing to a quality signal
available, though with n=12 and one rater it is an observation, not a measurement.

---

# The run

**Taken 2026-08-22 by lane GEMMA-WIRE.** One call, no retries, no sweep, no
temperature study.

| | |
|---|---|
| host | `https://aiplatform.googleapis.com` (**no region prefix** — `global` is not a region) |
| path | `/v1/projects/crucible-hack-2026/locations/global/endpoints/openapi/chat/completions` |
| model | `google/gemma-4-26b-a4b-it-maas` |
| params | `temperature=0`, `seed=20260822`, `max_tokens=4096` |
| response | `http 200`, `finish_reason: "stop"`, `traffic_type: ON_DEMAND` |
| tokens | prompt **3,461** · completion **1,430** · total **4,891**, read off the response's own `usage` block |
| validator | **12 proposals submitted, 12 accepted, 0 rejected.** No `E_*` code fired |

`finish_reason: "stop"` matters: the answer ended because the model finished, not
because it hit the token ceiling. A truncated JSON body would have failed
`E_NOT_JSON` rather than silently dropping tools, but a full stop is the cleaner
statement.

## The twelve proposals

Full docstrings, arguments and per-argument documentation are in
`docs/proof/cartographer-live-run-2026-08-22.json` under `prompt` — the reviewer
should read a disputed row there, or in the sample at the line named, rather than
from this table.

| # | source | signature, as extracted | proposed classes | evidence (verbatim, validator-checked) | self-reported confidence |
|---|---|---|---|---|---|
| 1 | `tools.py:27` | `send_call_companion_link(phone_number: str)` | `CAP_EXTERNAL_COMMS` | docstring "Sends a link to the user's phone number to start a video session." | 1.0 |
| 2 | `tools.py:47` | `approve_discount(discount_type: str, value: float, reason: str)` | `CAP_MOVES_MONEY` | docstring "Approve the flat rate or percentage discount requested by the user." | 1.0 |
| 3 | `tools.py:76` | `sync_ask_for_approval(discount_type: str, value: float, reason: str)` | `CAP_ESCALATES_PRIVILEGE` | docstring "Asks the manager for approval for a discount." | 1.0 |
| 4 | `tools.py:101` | `update_salesforce_crm(customer_id: str, details: dict)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Updates the Salesforce CRM with customer details." | 1.0 |
| 5 | `tools.py:129` | `access_cart_information(customer_id: str)` | `UNCLASSIFIED` | (none — `UNCLASSIFIED` carries no evidence, by design) | 1.0 |
| 6 | `tools.py:162` | `modify_cart(customer_id: str, items_to_add: list, items_to_remove: list)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Modifies the user's shopping cart by adding and/or removing items." | 1.0 |
| 7 | `tools.py:191` | `get_product_recommendations(plant_type: str, customer_id: str)` | `UNCLASSIFIED` | (none) | 1.0 |
| 8 | `tools.py:244` | `check_product_availability(product_id: str, store_id: str)` | `UNCLASSIFIED` | (none) | 1.0 |
| 9 | `tools.py:268` | `schedule_planting_service(customer_id: str, date: str, time_range: str, details: str)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Schedules a planting service appointment." | 1.0 |
| 10 | `tools.py:310` | `get_available_planting_times(date: str)` | `UNCLASSIFIED` | (none) | 1.0 |
| 11 | `tools.py:329` | `send_care_instructions(customer_id: str, plant_type: str, delivery_method: str)` | `CAP_EXTERNAL_COMMS` | docstring "Sends an email or SMS with instructions on how to take care of a specific plant type." | 1.0 |
| 12 | `tools.py:359` | `generate_qr_code(customer_id: str, discount_value: float, discount_type: str, expiration_days: int)` | `CAP_MOVES_MONEY` | docstring "Generates a QR code for a discount." | 1.0 |

Every docstring span above was re-checked against the frozen fixture
independently of the validator, character for character. All eight are verbatim.

---

# Five things the run showed, none of them flattering

These are properties of **this one run, on these twelve tools**. Nothing has been
measured against a labelled set and **no accuracy figure exists or may be
stated** (`gemma-scope.md` §7).

### 1. The confidence field is constant and therefore carries no information

`1.0` on all twelve rows — including the four the model declined to classify. A
number that says "certain" on `UNCLASSIFIED` is not reporting certainty about
anything. **Read the citation, not the number.** The field is named
`model_self_reported_confidence` precisely so nobody mistakes it for a
measurement, and this run is the argument for that name.

### 2. Every citation is a docstring. Not one argument was cited.

Twelve tools, eight evidence entries, **eight `kind: "docstring"` and zero
`kind: "argument"`**. The citation channel that would have caught the finding
this project already made by hand — `send_call_companion_link(phone_number)`
taking no `customer_id`, so the guard gated on a key the tool does not take
(`CONVENTIONS.md:1753`) — went unused. The model read prose and classified prose.

### 3. The free-text reason is a copy of the citation

The prompt asks for *"one sentence on why that argument implies that class."* In
all eight entries the `citation` string is **byte-identical to the cited
docstring span**. The model satisfied the field without using it, so there is no
independent reasoning on the page. This is a prompt defect, not a model defect,
and it is left as it stands rather than tuned after seeing the answer.

### 4. Every proposal is a single class. Two classes were never proposed at all.

Twelve proposals, twelve class-sets of size one. `CAP_READS_PII` and
`CAP_INVOKES_AGENT` appear nowhere. `CAP_INVOKES_AGENT` is correct —
`third-party-target-recon-2026-08-22.md` §3 establishes this is a single-agent
target with no `AgentTool` anywhere. `CAP_READS_PII` is a different story; see
the comparison below.

### 5. `UNCLASSIFIED` is standing in for `INERT`, and they are not the same thing

The prompt offers six classes plus `UNCLASSIFIED`. **It offers no way to say "I
read this and it has no capabilities."** `gemma.py`'s own `E_NO_CLASSES` message
spells out why an empty list is refused — it would be a much stronger claim than
"I do not know". So on tools 5, 7, 8 and 10 the model had no vocabulary for the
answer a human reached, and said `UNCLASSIFIED` instead.

**That gap has downstream teeth.** `UNCLASSIFIED` is always ALLOWED, so it turns
the policy off for that tool without saying so; `INERT` is a positive statement
that there is nothing to enforce. Those are different, and the Cartographer's
output vocabulary cannot currently express the difference.

**Left unchanged, deliberately.** Adding `INERT` to the prompt after seeing which
rows would move is tuning the instrument to the reading. It is a real gap, it is
named here, and it is Eric's to rule on.

---

# The comparison, and what it is worth

`third-party-target-recon-2026-08-22.md` §3 holds a twelve-row classification of
this exact surface, produced by a human reading the source **before** any model
ran. It is used here only as a comparison, exactly as this sheet's contract
allows. **With n=12 and one rater it is an observation, not a measurement, and no
number derived from it may be presented as accuracy.**

| # | tool | prior hand classification | Gemma proposal | relation |
|---|---|---|---|---|
| 1 | `send_call_companion_link` | `{EXTERNAL_COMMS}` | `{EXTERNAL_COMMS}` | same |
| 2 | `approve_discount` | `{MOVES_MONEY, ESCALATES_PRIVILEGE}` | `{MOVES_MONEY}` | **narrower** — dropped the escalation |
| 3 | `sync_ask_for_approval` | `{MOVES_MONEY, ESCALATES_PRIVILEGE}` | `{ESCALATES_PRIVILEGE}` | **narrower** — dropped the money |
| 4 | `update_salesforce_crm` | `{MUTATES_DURABLE_STATE, READS_PII}` | `{MUTATES_DURABLE_STATE}` | **narrower** — dropped the PII |
| 5 | `access_cart_information` | `{}` INERT | `UNCLASSIFIED` | vocabulary gap, §5 above |
| 6 | `modify_cart` | `{MUTATES_DURABLE_STATE}` | `{MUTATES_DURABLE_STATE}` | same |
| 7 | `get_product_recommendations` | `{}` INERT | `UNCLASSIFIED` | vocabulary gap |
| 8 | `check_product_availability` | `{}` INERT | `UNCLASSIFIED` | vocabulary gap |
| 9 | `schedule_planting_service` | `{MUTATES_DURABLE_STATE}` | `{MUTATES_DURABLE_STATE}` | same |
| 10 | `get_available_planting_times` | `{}` INERT | `UNCLASSIFIED` | vocabulary gap |
| 11 | `send_care_instructions` | `{EXTERNAL_COMMS}` | `{EXTERNAL_COMMS}` | same |
| 12 | `generate_qr_code` | `{MOVES_MONEY}` | `{MOVES_MONEY}` | same |

**The shape of the divergence is the useful part, and it points one way.** Where
the two differ on a capability-bearing tool, the model is **always the narrower
one**. It never proposed a class the human did not; it three times omitted one
the human did. A classifier that under-calls capability is the dangerous
direction: a missing class is a rule that never binds.

**Rows 2 and 3 are the ones to read closely.** The prior classification gives
them an *identical* set, and says so — *"that identity is the whole finding. Same
capability, same args, one enforces and one does not."* Gemma split them,
assigning `MOVES_MONEY` to one and `ESCALATES_PRIVILEGE` to the other, because it
classified each tool's docstring in isolation. **The frozen approved claim at
`CONVENTIONS.md:1754` rests on those two sets being the same.** Accepting rows 2
and 3 as proposed would put a manifest on record that contradicts it.

---

# What this run cost

Measured from the `usage` block on each response, not estimated:

| call | prompt | completion | total |
|---|---|---|---|
| reachability check (`"ok"`) | 20 | 2 | 22 |
| reachability check with `seed` | 20 | 2 | 22 |
| Cartographer, 12 tools | 3,461 | 1,430 | 4,891 |
| Cartographer, repeat (see below) | 3,461 | 1,430 | 4,891 |
| **total** | **6,962** | **2,864** | **9,826** |

**Dollars: under one cent, and the rate is not sourced.** Google's own generative
AI pricing page did not yield a Gemma MaaS line in this pass, and third-party
aggregators disagree with each other ($0.07/$0.34 vs $0.15/$0.60 per million
in/out). At the higher of those the run is ≈ **$0.003**; at four times the higher
it is still under a cent. **The token counts are measured; the dollar figure is
`[UNVERIFIED]` and should be read off the project's billing export rather than
from this document.** `traffic_type: ON_DEMAND` on every response confirms the
calls were billable rather than free-tier.

## The repeat call, and what it does and does not show

The Cartographer prompt was sent a second time with the same model id, the same
`seed=20260822` and `temperature=0`. The raw response came back **byte-identical**,
and `proposal_set_digest()` over both runs returns the same
`abef20e4…3ff3888`.

**This is not a determinism claim and must not be reported as one.** It is n=2,
minutes apart, on one serving stack, and `vertex.py` says why that is all it can
be: Google operates the weights, the container and the decoding stack and may
change any of them without changing the model id. What the observation does
support is the narrower claim `gemma-scope.md` §5 actually makes — *"same model
id, same seed, same prompt"* is a call a third party can re-issue.

---

## The ruling

_(blank — unsigned. Twelve rows above await a per-tool `accept` / `amend` /
`reject`. A tool with no recorded verdict blocks the whole ratification;
`E_UNREVIEWED_TOOL`, no partial signature.)_

## Ratifier's words

_(blank)_
