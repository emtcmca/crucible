# INERT — the empty capability set, said out loud

**Lane INERT (`lane/cartographer-inert`), 2026-08-23.** Implements Eric's ruling of
the same day. Nothing here is signed and this lane signed nothing.

---

## 1. What `INERT` is, stated precisely, because the record has been wrong once

**`INERT` is NOT a seventh capability class.** `CAPABILITY_CLASSES` is still six and
was not touched. The DSL validator still refuses a seventh class in a selector
(`check_selector`, and the DSL mutation audit's D3 mutation covers it), and
`manifest/load.py` still refuses the literal string `INERT` in a declared
`capability_classes` with `E_UNKNOWN_CAPABILITY_CLASS`. Both refusals are now pinned
by tests in `tests/test_cartographer_inert.py` so that "add INERT" cannot quietly
become "add a class" in a later edit.

**`INERT` is a sentinel in the *proposal* vocabulary**, exactly as `UNCLASSIFIED` is,
and it **resolves to the empty capability set `[]`** at the single point where the
proposal vocabulary meets the manifest vocabulary: `ratify._resolve_classes()`. That
function does exactly one thing — `("INERT",)` becomes `()` — and it is the whole of
the ruling in code.

**`INERT` DOES NOT REDUCE RISK.** `match_rules` binds a rule only when its class is
IN the tool's capability set, so a tool with an empty set matches **no rule**.
`cap:UNCLASSIFIED` does not parse (`E_UNCLASSIFIED_SELECTOR`), so no rule can bind
there either. **Both are equally unpoliceable by policy.** The engine's own header
says an unclassified tool is ALWAYS ALLOWED and that the engine FAILS OPEN there
deliberately, because the TRIPWIRE scores the Objective Set independently of policy.
None of that changed.

**What `INERT` buys is epistemic, not enforcement.** It separates *"a human looked
and ratified this as inert"* from *"nobody looked."* For a track about cataloging
agents, that distinction is the product. **Claiming it makes the tools safer would
be false**, and `_resolve_classes()`'s own docstring says so at the exact place
somebody would go looking for a safety property and not find one. A test,
`test_an_inert_tool_binds_no_rule_so_inert_reduces_no_risk`, asserts the no-rule-binds
property directly.

---

## 2. `UNCLASSIFIED` was kept, deliberately

If the model could only say `INERT`, the *"I cannot determine"* signal would be
destroyed and one collapsed distinction would have been traded for another. The
prompt now offers both, states the difference in a sentence — *"the difference
between 'I do not know' and 'I know, and the answer is nothing'"* — and tells the
model that if it cannot cite anything for `INERT`, the honest answer is
`UNCLASSIFIED`. The two are mutually exclusive and `E_INERT_MIXED` enforces it.

The `INERT` text sits **outside** the six-class guide, not inside it. A model shown
seven entries in a list headed *"the six capability classes"* will emit `INERT` as a
class. `test_the_prompt_still_offers_exactly_six_capability_classes` asserts the
separation by splitting the prompt.

---

## 3. The plumbing question, and the citation decision

**Does the plumbing accept an empty capability set? YES, and it already did.**
`manifest/load.py`'s module docstring sanctions it explicitly and predates this
lane: *"A tool ABSENT from the manifest and a tool present with an EMPTY capability
set mean different things. Absent is 'nobody classified this', which is an error.
Empty is 'we know it has no capabilities', which is a claim."* `_validate_part_a`
accepts `capability_classes: []`, and `capability_set()` returns `frozenset()` for
it. Verified end to end against the **real** run output, not a fixture: an
all-accept ratification produces `()` for all four `INERT` rows and the resulting
manifest loads.

**The gap was never the manifest. It was the two layers above it**, and all three
needed the token:

- `gemma._validate_one` raised `E_NO_CLASSES` on an empty list, with a message that
  had already reasoned the case out — *"an empty list would say 'this tool has no
  capabilities', which is a different and much stronger claim."* The concept was
  anticipated and refused for want of a word.
- `ratify.build_ratification` would have refused `INERT` on `amend`, so **the human
  reviewer had the same missing word the model did** and had to write `UNCLASSIFIED`
  over an answer he was certain of.
- `ratify.to_manifest_entries` passed classes straight through, so nothing resolved.

### The citation requirement: `INERT` must cite, `UNCLASSIFIED` need not

Two reasons, the second decisive.

1. **`INERT` is a positive assertion about the tool.** `prepass.py`'s doctrine binds
   positive assertions to citable evidence — *"a classification with no citable
   evidence is a guess wearing a confidence number."* `UNCLASSIFIED` is exempt
   because there is nothing to cite: the absence of evidence **is** that claim.
2. **An uncited `INERT` would be strictly cheaper to emit than `UNCLASSIFIED`**, and
   a model taking the shortest path would drift onto it — collapsing the very
   distinction this sentinel exists to create, in the opposite direction. Requiring a
   citation makes `INERT` the more expensive answer, which is correct, because it is
   the stronger claim.

**The validator was not weakened to admit anything.** `INERT` without evidence →
`E_CLASS_WITHOUT_EVIDENCE`. `INERT` with a non-verbatim span → `E_CITATION_NOT_GROUNDED`.
`INERT` mixed with anything → `E_INERT_MIXED`. Empty list → `E_NO_CLASSES`, unchanged.
Every one written **red before green**; the red run was 7 failed / 7 passed, the
7 passing being the regressions that assert nothing changed.

Gemma cited all four `INERT` rows without difficulty, so the requirement cost nothing
this run. **That is a fact about this run, not a general finding.**

---

## 4. What the re-run showed

One prompt change, one re-run, everything else held: same model id
`google/gemma-4-26b-a4b-it-maas`, `location=global`, host with no region prefix,
`seed=20260822`, `temperature=0`, same frozen fixture digest. **No proposal was
inspected and then used to adjust the prompt.**

Four of twelve rows moved. Three moved as intended (`get_product_recommendations`,
`check_product_availability`, `get_available_planting_times`: `UNCLASSIFIED` →
`INERT`, each with a validator-checked verbatim citation).

**One regressed, and it is the finding.** `generate_qr_code` moved
`CAP_MOVES_MONEY` → `INERT` **while citing the identical docstring span in both
runs**. It takes a float `discount_value` and mints an instrument that redeems it.
The earlier run and the prior hand reading both called it `MOVES_MONEY`. This run
calls it inert and this run is wrong.

**One expected row did not move.** `access_cart_information` stayed `UNCLASSIFIED`
where the prior hand classification predicted `INERT`. Worth noting on its own
terms: this project has three times believed a result because it matched what a memo
predicted. The model disagreeing with the prediction on one of four rows is evidence
this is a reading rather than an echo.

**All five known weaknesses repeat**, re-measured: confidence constant at `1.0`
(twelve of twelve), zero argument citations (0 of 11 entries), the `citation` field
byte-identical to the cited span (11 of 11), every class-set size one (twelve of
twelve), and `CAP_READS_PII` absent again (as is `CAP_INVOKES_AGENT`). None were
touched — fixing them in the same pass would have made the moved rows
unattributable.

---

## 5. What this lane is flagging to the coordinator

**a. A boundary on what the citation requirement buys, which two live documents
lean on.** `docs/narrative/prepass-and-gemma.md` §3 says the ratification gate is
carrying the load because *"every proposed capability class must cite an argument
that tool itself declares, or a span verbatim from its own docstring"*, and *"a
fabricated citation is a parse failure."* **Both statements remain true.** But
`generate_qr_code` shows that the requirement grounds the *citation* and does not
constrain the *inference from citation to class*: the same verbatim span was
accepted as evidence for `CAP_MOVES_MONEY` and, one prompt change later, for
`INERT`. Nothing in `prepass-and-gemma.md` is false and this lane changed no word of
it — **that file is coordinator-owned canon and §6 governs what may be claimed.**
The observation is offered for a ruling, not applied. It strengthens the argument
for the human gate rather than weakening it.

**b. A pre-existing behaviour this lane did NOT fix.** `to_manifest_entries` does not
resolve `UNCLASSIFIED`, so an accepted `UNCLASSIFIED` proposal produces
`capability_classes: ("UNCLASSIFIED",)`, which `manifest/load.py` then refuses by
name. It **fails closed and loudly**, so it is not dangerous, and it arguably has the
right effect — it forces a human to amend or reject a tool nobody could classify. But
it is undocumented, and in practice it means row 5 of the current sheet **cannot be
accepted as proposed and still load**. Flagged on the sheet, left alone in the code:
resolving it would invent a decision the reviewer did not make, and changing it
alongside the `INERT` delta would blur attribution.

**c. `CAP_READS_PII` has now been absent across two runs**, on a target where three
tools take a `customer_id` and handle named-customer data. It is the class the
unused argument-citation channel would most plausibly have caught. Not this lane's
to fix; worth a lane of its own.

---

## 6. Files this lane touched

Owned paths only. `contracts/MANIFEST.json` untouched, `spine_version` unbumped, no
freeze script run.

| File | Change |
|---|---|
| `crucible/cartographer/gemma.py` | `INERT` constant, prompt vocabulary, `E_INERT_MIXED`, evidence rule |
| `crucible/cartographer/ratify.py` | `_resolve_classes()`, `amend` accepts `INERT`, `E_INERT_MIXED` |
| `crucible/cartographer/run.py` | docstring: two runs, what the diff showed |
| `crucible/cartographer/__init__.py` | docstring: same |
| `tests/test_cartographer_inert.py` | **new**, 14 tests, red before green |
| `docs/proof/cartographer-adk-ratification.md` | **new sheet, UNSIGNED**, digest `24a0a3fb…f2295c` |
| `docs/proof/cartographer-adk-ratification-superseded-2026-08-23.md` | prior sheet, archived with a supersede block |
| `docs/proof/cartographer-live-run-2026-08-23.json` | **new**, the run |
| `docs/proof/cartographer-live-run-2026-08-22.json` | `_superseded` block added; **digest unmoved**, asserted |
| `docs/proof/cartographer-residue-prompt-2026-08-23.txt` | **new**, prompt bytes verbatim |

**Gates:** `pytest` exit **0**, **1520 passed / 1 skipped = 1521 collected** (baseline
1507 + 14 new, nothing else moved). `scripts/contract-check.py` exit **0**.

**Cost:** prompt 3,648 · completion 1,145 · total **4,793** tokens, read off the
response's `usage` block. **Dollars `[UNVERIFIED]`** — Google publishes no Gemma MaaS
price line this pass could source and third-party aggregators disagree, so no figure
is stated.
