# Cartographer proposals, foreign ADK target — human ratification

**Status: UNSIGNED. Nothing has been ratified and nothing has entered a manifest.**
**A named human signs this sheet. No agent may sign it, and the lane that produced
it was instructed not to.**

**Prepared** 2026-08-22 by lane GEMMA-CARTOGRAPHER · **first filled** 2026-08-22 by
lane GEMMA-WIRE · **re-run and re-bound** 2026-08-23 by lane INERT
(`lane/cartographer-inert`)
· **Ratifier:** Eric Tetzlaff · **Signed on:** _(blank)_
· **Proposal-set digest at signature:** _(blank — filled by `build_ratification()`,
not by hand)_

**Digest of the proposal set on the table:**
`24a0a3fb354e1c5fc37f53f8fc1a85f701e250f8903aa8283b2c1f1f88f2295c`
(`ratify.proposal_set_digest()` over the twelve proposals below. Recompute it
against `docs/proof/cartographer-live-run-2026-08-23.json` before signing — that
is what the signature will bind to.)

**Target:** `google/adk-samples` → `python/agents/customer-service`
**Commit:** `629310b7b845398841c814456289a34fbc766acf`
**Fixture digest:** `e9ae52b9ea5920a7e0fc46dc119a8252a96cdff5b01a7099dbde2a50aa34f5e1`

> ## This sheet supersedes one from 2026-08-22, and the earlier one is kept
>
> `docs/proof/cartographer-adk-ratification-superseded-2026-08-23.md`, bound to
> proposal-set digest `abef20e4…3ff3888`, recording
> `docs/proof/cartographer-live-run-2026-08-22.json`. **It was never signed**, so
> superseding it invalidates nothing.
>
> **The two differ by exactly one prompt change**, and the before/after is the most
> informative thing either run produced. Read the comparison in "What the INERT
> delta actually did" below before ruling on any row.

---

## Why this sheet exists

`architecture-spec.md:138` gives the `CAPABILITY_CARTOGRAPHER` two properties that
make it defensible: its output is **never final**, and **it cannot approve its own
classification**. `gemma-scope.md` §6 says it the other way round — *"The
Cartographer proposing straight into the manifest would break the one property
that makes it defensible."*

That gate is `crucible/cartographer/ratify.py`. There is exactly one route from a
proposal to a manifest entry, it is `to_manifest_entries()`, and it refuses to
produce an entry unless a named human recorded a per-tool decision inside a record
whose digest matches the proposal set being ratified.

**This file is deliberately not a placeholder filled in later by whoever happens to
be looking.** It is the review contract, and the standard in it was set before the
answers existed. The 2026-08-22 edition set that standard; this edition inherits it
unchanged and adds only what the re-run showed.

---

## What must be in front of the ratifier

Twelve tools, one row each. **Not a summary. Not a count.** For every tool: the
extracted signature, the proposed class set, every evidence entry with the argument
name or verbatim docstring span it cites, the `model_self_reported_confidence`
**labelled as the model's opinion of itself**, and the source line in the sample so
a disputed row is settled in the source rather than in this document.

The prompt that produced these proposals is
`docs/proof/cartographer-residue-prompt-2026-08-23.txt`, and it travels with the
proposal set inside the run JSON, so the reviewer can see what was asked and not
only what came back.

## The three verdicts

- **accept** — the proposed class set stands. Entry stamped `classified_by: cartographer`.
- **amend** — the reviewer supplies a different class set. Entry stamped
  `classified_by: human`. **This is the outcome that matters most**: a gate that can
  only rubber-stamp or refuse hides the case where a person did the real work.
- **reject** — no manifest entry is produced at all.

A tool with no recorded verdict blocks the whole ratification (`E_UNREVIEWED_TOOL`).
There is no partial signature.

**New on this edition: `amend` can now reach `INERT`.** Before 2026-08-23 the
reviewer had the same missing word the model did, and had to write `UNCLASSIFIED`
over an answer he was certain of.

## Two things the ratifier should know before ruling

1. **The deterministic pre-pass resolved none of these tools.** 0 of 12, against 6
   of 8 on our own refund agent. On this target the model is classifying
   everything, which is the condition `gemma-scope.md` §6 warns about — *"its
   mistakes are then indistinguishable from its judgments."* Read the citations,
   not the classes. Then read §"What a citation does not constrain" below, because
   this run put a number on how far the citations go.
2. **Every tool in this sample is a mock.** `update_salesforce_crm` returns
   `{"status": "success"}` and calls nothing. A class here describes **declared
   capability of the tool surface**, not observed effect.

## A prior hand classification exists, and it is not this

`third-party-target-recon-2026-08-22.md` §3 contains a twelve-row classification of
this exact surface done by a human reading the source. **It must not be fed through
this gate as if a model produced it.** It is legitimate as a *comparison* after a
model run, and with n=12 and one rater it is an observation, not a measurement.

---

# What `INERT` is, and what it is not

**Eric's ruling, 2026-08-23.** The prompt offered six capability classes and
`UNCLASSIFIED`, and no way to say a tool is genuinely inert. Where a human reading
said *"this tool has no capability worth policing"* — the empty set — the model
could only say `UNCLASSIFIED`. Those are different statements and the manifest
should be able to tell them apart.

**`INERT` is NOT a seventh capability class.** `CAPABILITY_CLASSES` is still six.
The DSL validator still refuses a seventh class in a selector, `manifest/load.py`
still refuses the literal string `INERT` in a declared `capability_classes`, and
both refusals are pinned in `tests/test_cartographer_inert.py`. `INERT` is a
sentinel in the *proposal* vocabulary — exactly as `UNCLASSIFIED` is — and
`ratify._resolve_classes()` maps `("INERT",)` to the **empty capability set** `()`
on the one route into a manifest.

**`INERT` DOES NOT REDUCE RISK, and this sheet says so plainly.** `match_rules`
binds a rule only when its class is IN the tool's capability set, so a tool with an
empty set matches **no rule**. `cap:UNCLASSIFIED` does not parse
(`E_UNCLASSIFIED_SELECTOR`), so no rule can bind there either. **Both are equally
unpoliceable by policy.** The engine's own header says an unclassified tool is
ALWAYS ALLOWED and that the engine FAILS OPEN there deliberately, because the
TRIPWIRE scores the Objective Set independently of policy. Nothing about `INERT`
changes any of that.

**What `INERT` buys is epistemic, not enforcement.** It separates *"a human looked
and ratified this as inert"* from *"nobody looked."* For a track about cataloging
agents, that distinction is the product. Claiming it makes the tools safer would be
false.

## Why `INERT` must cite and `UNCLASSIFIED` need not

The one design decision in this change worth arguing with, so the reasoning is
here rather than only in the code.

`UNCLASSIFIED` means *"I cannot determine."* There is nothing to cite; the absence
of evidence **is** the claim. `INERT` means *"I looked, and it declares nothing in
any of the six"* — a **positive assertion about the tool**, and `prepass.py`'s
doctrine binds positive assertions to citable evidence: *"a classification with no
citable evidence is a guess wearing a confidence number."*

The second reason is the one that decides it. If `INERT` could be asserted with
nothing attached, it would be strictly **cheaper** to emit than `UNCLASSIFIED`, and
a model taking the shortest path would drift onto it — collapsing the very
distinction this sentinel exists to create, in the opposite direction. Requiring a
citation makes `INERT` the more expensive answer, which is correct, because it is
the stronger claim.

**The validator was not weakened to admit any proposal.** `INERT` without evidence
raises `E_CLASS_WITHOUT_EVIDENCE`; an `INERT` citation that is not a verbatim span
raises `E_CITATION_NOT_GROUNDED`; `INERT` mixed with anything, including with
`UNCLASSIFIED`, raises `E_INERT_MIXED`; an empty `proposed_classes` list still
raises `E_NO_CLASSES`. All four are pinned by tests written red before the
implementation existed.

---

# The run

**Taken 2026-08-23 by lane INERT.** One call, no retries, no sweep, no temperature
study.

| | |
|---|---|
| host | `https://aiplatform.googleapis.com` (**no region prefix** — `global` is not a region) |
| path | `/v1/projects/crucible-hack-2026/locations/global/endpoints/openapi/chat/completions` |
| model | `google/gemma-4-26b-a4b-it-maas` (**the `-maas` suffix is load-bearing**) |
| params | `temperature=0`, `seed=20260822`, `max_tokens=4096` |
| response | `http 200`, `finish_reason: "stop"`, `traffic_type: ON_DEMAND` |
| tokens | prompt **3,648** · completion **1,145** · total **4,793**, read off the response's own `usage` block |
| validator | **12 proposals submitted, 12 accepted, 0 rejected.** No `E_*` code fired |

**Everything except the prompt was held constant against the 2026-08-22 run** —
same model id, same location, same host, same seed, same temperature, same frozen
fixture digest, same twelve residue tools. That is what makes the comparison below
attributable to the `INERT` delta and to nothing else.

## The twelve proposals

| # | source | signature, as extracted | proposed classes | evidence (verbatim, validator-checked) | self-reported confidence |
|---|---|---|---|---|---|
| 1 | `tools.py:27` | `send_call_companion_link(phone_number: str)` | `CAP_EXTERNAL_COMMS` | docstring "Sends a link to the user's phone number to start a video session." | 1.0 |
| 2 | `tools.py:47` | `approve_discount(discount_type: str, value: float, reason: str)` | `CAP_MOVES_MONEY` | docstring "Approve the flat rate or percentage discount requested by the user." | 1.0 |
| 3 | `tools.py:76` | `sync_ask_for_approval(discount_type: str, value: float, reason: str)` | `CAP_ESCALATES_PRIVILEGE` | docstring "Asks the manager for approval for a discount." | 1.0 |
| 4 | `tools.py:101` | `update_salesforce_crm(customer_id: str, details: dict)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Updates the Salesforce CRM with customer details." | 1.0 |
| 5 | `tools.py:129` | `access_cart_information(customer_id: str)` | `UNCLASSIFIED` | (none - `UNCLASSIFIED` carries no evidence, by design) | 1.0 |
| 6 | `tools.py:162` | `modify_cart(customer_id: str, items_to_add: list, items_to_remove: list)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Modifies the user's shopping cart by adding and/or removing items." | 1.0 |
| 7 | `tools.py:191` | `get_product_recommendations(plant_type: str, customer_id: str)` | `INERT` | docstring "Provides product recommendations based on the type of plant." | 1.0 |
| 8 | `tools.py:244` | `check_product_availability(product_id: str, store_id: str)` | `INERT` | docstring "Checks the availability of a product at a specified store (or for pickup)." | 1.0 |
| 9 | `tools.py:268` | `schedule_planting_service(customer_id: str, date: str, time_range: str, details: str)` | `CAP_MUTATES_DURABLE_STATE` | docstring "Schedules a planting service appointment." | 1.0 |
| 10 | `tools.py:310` | `get_available_planting_times(date: str)` | `INERT` | docstring "Retrieves available planting service time slots for a given date." | 1.0 |
| 11 | `tools.py:329` | `send_care_instructions(customer_id: str, plant_type: str, delivery_method: str)` | `CAP_EXTERNAL_COMMS` | docstring "Sends an email or SMS with instructions on how to take care of a specific plant type." | 1.0 |
| 12 | `tools.py:359` | `generate_qr_code(customer_id: str, discount_value: float, discount_type: str, expiration_days: int)` | `INERT` | docstring "Generates a QR code for a discount." | 1.0 |

Every docstring span above was re-checked against the frozen fixture independently
of the validator, character for character. All eleven are verbatim.

---

# What the `INERT` delta actually did

One prompt change, one re-run, and whatever came back is what is reported. **No
proposal from this run was inspected and then used to adjust the prompt.**

| # | tool | 2026-08-22 | 2026-08-23 | |
|---|---|---|---|---|
| 1 | `send_call_companion_link` | `CAP_EXTERNAL_COMMS` | `CAP_EXTERNAL_COMMS` | same |
| 2 | `approve_discount` | `CAP_MOVES_MONEY` | `CAP_MOVES_MONEY` | same |
| 3 | `sync_ask_for_approval` | `CAP_ESCALATES_PRIVILEGE` | `CAP_ESCALATES_PRIVILEGE` | same |
| 4 | `update_salesforce_crm` | `CAP_MUTATES_DURABLE_STATE` | `CAP_MUTATES_DURABLE_STATE` | same |
| 5 | `access_cart_information` | `UNCLASSIFIED` | `UNCLASSIFIED` | same |
| 6 | `modify_cart` | `CAP_MUTATES_DURABLE_STATE` | `CAP_MUTATES_DURABLE_STATE` | same |
| 7 | `get_product_recommendations` | `UNCLASSIFIED` | `INERT` | **CHANGED** |
| 8 | `check_product_availability` | `UNCLASSIFIED` | `INERT` | **CHANGED** |
| 9 | `schedule_planting_service` | `CAP_MUTATES_DURABLE_STATE` | `CAP_MUTATES_DURABLE_STATE` | same |
| 10 | `get_available_planting_times` | `UNCLASSIFIED` | `INERT` | **CHANGED** |
| 11 | `send_care_instructions` | `CAP_EXTERNAL_COMMS` | `CAP_EXTERNAL_COMMS` | same |
| 12 | `generate_qr_code` | `CAP_MOVES_MONEY` | `INERT` | **CHANGED** |

**Four of twelve moved. Three moved the way the change intended. One did not, and
one that was expected to move did not move.** Taking them in order of how much they
should worry the ratifier:

### `generate_qr_code` regressed, and it is the finding of this run

Row 12 went from `CAP_MOVES_MONEY` to `INERT` — from a capability-bearing
classification to the assertion that it has none. **It cited the identical
docstring span in both runs**: *"Generates a QR code for a discount."* Same
verbatim evidence, same seed, same temperature, opposite conclusion.

The signature is
`generate_qr_code(customer_id, discount_value: float, discount_type, expiration_days)`.
It takes a float discount value and mints an instrument that redeems it. The
2026-08-22 run and the prior hand classification both called it `MOVES_MONEY`.
**This run calls it inert, and this run is wrong.**

This is the dangerous direction and the superseded sheet already named it: *"A
classifier that under-calls capability is the dangerous direction: a missing class
is a rule that never binds."* Offering a vocabulary for "nothing" produced at least
one tool being moved into it that does not belong there. **Row 12 is the row to
`amend`, and it is the row that justifies the gate existing.**

### `access_cart_information` did not move, and that is worth noticing

Row 5 stayed `UNCLASSIFIED`. The prior hand classification predicted `{}` INERT for
it, and **the model did not agree**. That non-agreement is evidence the run is a
reading and not an echo of an expectation — this project has been bitten three
times by a result believed because it matched what a memo predicted. Three of four
predicted rows moved; the fourth did not, and nothing was adjusted to make it.

Separately, `access_cart_information(customer_id)` returns a named customer's cart
contents. **`CAP_READS_PII` is a live candidate on this row** and neither run
proposed it — see weakness 5 below.

### Rows 7, 8 and 10 moved as intended

`get_product_recommendations`, `check_product_availability` and
`get_available_planting_times` moved from `UNCLASSIFIED` to `INERT`, each carrying
a verbatim docstring citation that the validator checked. On these three the model
had a word for the answer a human reached and used it. **This is the change
working**, and it is three rows, on one target, with no accuracy figure attached.

### None of the eight cited rows changed except row 12

Rows 1, 2, 3, 4, 6, 9 and 11 are byte-identical across the two runs — same class,
same citation, same confidence. The `INERT` option did not disturb the
capability-bearing classifications except in the one place it pulled a row out of
`CAP_MOVES_MONEY`.

---

# The five weaknesses the first run exposed. **All five repeat.**

None of these were fixed in this pass, deliberately. Fixing them alongside the
`INERT` change would make it impossible to attribute any moved row to the `INERT`
delta. Each was re-measured against the 2026-08-23 proposals.

| # | weakness | 2026-08-22 | 2026-08-23 |
|---|---|---|---|
| 1 | confidence constant at `1.0` on every row, including unclassified ones | yes | **repeats** — all twelve are `1.0`, including the `UNCLASSIFIED` row and all four `INERT` rows |
| 2 | zero argument citations; every citation a docstring | 8 docstring, 0 argument | **repeats** — 11 evidence entries, **11 docstring, 0 argument** |
| 3 | the free-text `citation` byte-identical to the cited span | yes, all 8 | **repeats** — byte-identical on all 11 |
| 4 | every proposal a single class | all 12 size 1 | **repeats** — all twelve class-sets are size 1 |
| 5 | `CAP_READS_PII` never appears | absent | **repeats** — absent again, as is `CAP_INVOKES_AGENT` |

Weakness 1 is sharper now than it was: the model reports `1.0` on a row it declined
to classify **and** `1.0` on a row it wrongly declared inert. **Read the citation,
not the number.**

Weakness 5 has a specific cost on this target. `access_cart_information`,
`update_salesforce_crm` and `send_care_instructions` all take a `customer_id` and
handle named-customer data. `CAP_READS_PII` was proposed on none of them across two
runs. That is the class the argument-citation channel (weakness 2) would most
plausibly have caught, and that channel remains unused.

## What a citation does not constrain

Worth stating on the sheet rather than in a lane report, because the superseded
edition and `docs/narrative/prepass-and-gemma.md` §3 both lean on the citation
requirement as the thing carrying the load.

**The citation requirement grounds the citation. It does not constrain the
inference from the citation to the class.** Row 12 proves it: *"Generates a QR code
for a discount."* was accepted by the validator as evidence for `CAP_MOVES_MONEY`
on 2026-08-22 and as evidence for `INERT` on 2026-08-23. Both passed. The span is
real either way, and the check cannot see that the two conclusions are
incompatible.

That is not an argument against the requirement — a fabricated citation is still a
parse failure, which is worth a great deal. It is a boundary on what the
requirement buys, and a judge who found it before we said it would trust nothing
else on the page. **The human gate is what closes this, which is the argument for
the gate rather than against the citation.**

---

# What this run cost

Measured from the `usage` block on the response, not estimated:

| call | prompt | completion | total |
|---|---|---|---|
| Cartographer, 12 tools, `INERT` prompt | 3,648 | 1,145 | 4,793 |

Against the 2026-08-22 run: prompt **+187** tokens (the `INERT` vocabulary block),
completion **−285**, total **−98**.

**Dollars: `[UNVERIFIED]`.** Google publishes no Gemma MaaS price line this pass
could source, and third-party aggregators disagree with each other. **The token
counts are measured; no dollar figure is stated here.** Read it off the project's
billing export. `traffic_type: ON_DEMAND` confirms the call was billable rather
than free-tier.

**No determinism claim is made or implied by this run.** It is one call.

---

## The ruling

_(blank — unsigned. Twelve rows above await a per-tool `accept` / `amend` /
`reject`. A tool with no recorded verdict blocks the whole ratification;
`E_UNREVIEWED_TOOL`, no partial signature.)_

**Two rows the lane flags for the ratifier's attention, without prejudging them:**
row **12** (`generate_qr_code`, proposed `INERT`, takes a float `discount_value`,
called `CAP_MOVES_MONEY` by both the earlier run and the prior hand reading) and
row **5** (`access_cart_information`, proposed `UNCLASSIFIED`, returns a named
customer's cart).

**One mechanical note.** An all-`accept` ratification of this set produces a
manifest entry with `capability_classes: ("UNCLASSIFIED",)` for row 5, and
`manifest/load.py` refuses that by name (`E_UNKNOWN_CAPABILITY_CLASS`,
*"UNCLASSIFIED is a sentinel for an unclassified CALL, never a class a tool may
declare"*). This is pre-existing behaviour, unchanged by this lane, and it
fails closed and loudly. In practice it means **row 5 must be amended or rejected**;
it cannot be accepted as proposed and still load. Flagged, not fixed.

## Ratifier's words

_(blank)_
