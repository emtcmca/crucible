# Cartographer proposals, foreign ADK target — human ratification

**Status: UNSIGNED. Nothing has been ratified and nothing has entered a manifest.**

**Prepared** 2026-08-22 by lane GEMMA-CARTOGRAPHER (`lane/gemma-cartographer`)
· **Ratifier:** Eric Tetzlaff · **Signed on:** _(blank)_
· **Proposal-set digest at signature:** _(blank — filled by
`build_ratification()`, not by hand)_

**Target:** `google/adk-samples` → `python/agents/customer-service`
**Commit:** `629310b7b845398841c814456289a34fbc766acf` (verified with
`git rev-parse` in `C:\dev\_sandbox\adk-samples`; output pasted in
`docs/decisions-pending/gemma-cartographer-foreign-adk-2026-08-22.md` §1)
**Fixture digest:** `e9ae52b9ea5920a7e0fc46dc119a8252a96cdff5b01a7099dbde2a50aa34f5e1`

---

## Why this sheet exists before there is anything on it

`architecture-spec.md:138` gives the `CAPABILITY_CARTOGRAPHER` two properties
that make it defensible: its output is **never final**, and **it cannot approve
its own classification**. `gemma-scope.md` §6 says the same thing the other way
round — *"The Cartographer proposing straight into the manifest would break the
one property that makes it defensible."*

That gate is built and tested (`crucible/cartographer/ratify.py`,
`tests/test_cartographer_gemma.py`). **CHECKED 2026-08-22: no proposal set
exists to put through it**, because the managed Gemma endpoint is not
reachable from `crucible-hack-2026` — four probes, four `404 NOT_FOUND`,
against a control that returned `200` on the same URL seconds earlier
(`docs/proof/vertex-gemma-maas-probe-2026-08-22.txt`).

Enabling the model is a project change and a licence acceptance, so this lane
stopped and reported rather than clicking through.

**This file is deliberately not a placeholder to be filled in later by whoever
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
asked, not only what came back.

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

## The ruling

_(blank — no proposals exist)_

## Ratifier's words

_(blank)_
